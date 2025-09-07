from .models import ArtPiece, Comment, SentArtPiece
from django.shortcuts import get_object_or_404, render
from django.db.models import Q, Count
from django.http import Http404
from django.http import JsonResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from .forms import RegisterForm, ArtPieceForm, CommentForm, AccountInfoForm, ArtDeliveryForm, EmailPreferencesForm, CustomPasswordChangeForm, CustomSetPasswordForm
from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash, authenticate, views as auth_views
from django.contrib.auth.decorators import login_required
from django.utils.html import strip_tags
from django.core.mail import send_mail
from django.urls import reverse, reverse_lazy
from django.db import IntegrityError, transaction
import random
from collections import defaultdict
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.core.signing import BadSignature, SignatureExpired
from django.utils import timezone
from datetime import timedelta
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from .models import ArtPiece, SentArtPiece, CustomUser, Comment, Like, Notification, ReciprocalGrant, WelcomeGrant
from main.utils.email_unsub import load_unsub_token
import json
from zoneinfo import ZoneInfo


def home(request):
    if request.user.is_authenticated:
        return redirect('my_received_art')
    # Unauthed: show marketing/landing content
    return render(request, 'main/home.html')


def sign_up(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect(reverse('welcome_page'))
    else:
        form = RegisterForm()

    return render(request, 'registration/sign_up.html', {"form": form})


@login_required
def welcome_page(request):
    """
    GET-only: ensure the user has exactly one welcome gift (idempotent),
    then show it. Safe to refresh; OneToOne + select_for_update prevents duplicates.
    """
    user = request.user

    # Give (or fetch existing) welcome piece; None if no eligible piece
    welcome_piece = ensure_welcome_gift(user)

    # Optional: banner if the user has paused delivery (copy-only; we still give the welcome)
    paused = getattr(user, "receive_art_paused", False)

    return render(request, "main/welcome.html", {
        "welcome_piece": welcome_piece,
        "paused": paused,
    })


def choose_welcome_piece_weighted(user):
    qs = ArtPiece.active.filter(
        approved_status=True,
        welcome_eligible=True,
    ).exclude(
        user=user
    ).exclude(
        id__in=SentArtPiece.objects.filter(
            user=user).values_list('art_piece_id', flat=True)
    ).values('id', 'welcome_weight')

    items = list(qs)
    if not items:
        return None

    # Build a weighted bag (small pools of 5–10 keep this trivial)
    weighted = []
    for it in items:
        weighted.extend([it['id']] * max(1, it['welcome_weight']))

    chosen_id = random.choice(weighted)
    return ArtPiece.objects.select_related('user').get(pk=chosen_id)


def ensure_welcome_gift(user):
    """
    Give exactly one welcome piece (idempotent via WelcomeGrant).
    """
    with transaction.atomic():
        grant, created = WelcomeGrant.objects.select_for_update().get_or_create(
            user=user,
            defaults={},
        )

        if grant.sent_art_piece:
            return grant.sent_art_piece

        piece = choose_welcome_piece_weighted(user)  # <-- curated pool
        if not piece:
            return None

        grant.sent_art_piece = piece
        grant.save(update_fields=["sent_art_piece"])

        # silent add; your signal skips notifications for source='welcome'
        mark_art_piece_as_sent(user, piece, source="welcome")
        return piece


@login_required(login_url="/login")
def share_art(request):
    user = request.user

    if request.method == 'POST':
        form = ArtPieceForm(request.POST)
        if not form.is_valid():
            return render(request, 'main/share_art.html', {"form": form})

        # 1) Save the submitted art
        new_piece = form.save(commit=False)
        new_piece.user = user
        new_piece.save()

        # 2) If paused, skip reciprocal and redirect to Thank You (no gift)
        if getattr(user, "receive_art_paused", False):
            return redirect(reverse("thanks_for_sharing") + "?paused=1")

        # 3) Idempotent grant: only create once per submitted piece
        with transaction.atomic():
            grant, created = ReciprocalGrant.objects.select_for_update().get_or_create(
                trigger_art_piece=new_piece,
                defaults={"user": user},  # <-- no sent_art_piece here
            )

            if created:
                reciprocal = choose_art_piece(user)
                if reciprocal:
                    grant.sent_art_piece = reciprocal
                    grant.save(update_fields=["sent_art_piece"])

                    # Add to My Received Art silently
                    mark_art_piece_as_sent(
                        user, reciprocal, source="reciprocal")
                else:
                    # Leave sent_art_piece as NULL; still save the grant (already saved by create)
                    reciprocal = None
            else:
                reciprocal = grant.sent_art_piece  # reuse if it exists

        # 4) Redirect (PRG). Pass piece id (if any) to Thank-You GET view
        if reciprocal:
            return redirect(reverse("thanks_for_sharing") + f"?p={reciprocal.id}")
        else:
            return redirect(reverse("thanks_for_sharing"))

    # GET -> render form
    form = ArtPieceForm()
    return render(request, 'main/share_art.html', {"form": form})


@login_required
def thanks_for_sharing(request):
    user = request.user
    paused = request.GET.get("paused") == "1"
    piece_id = request.GET.get("p")

    reciprocal_piece = None
    if piece_id:
        # Security: ensure the piece was actually sent to THIS user as reciprocal
        sent = SentArtPiece.objects.filter(
            user=user, art_piece_id=piece_id, source="reciprocal"
        ).select_related("art_piece", "art_piece__user").first()
        if sent:
            reciprocal_piece = sent.art_piece
        else:
            # fall through silently (no gift), rather than 404ing user
            reciprocal_piece = None

    return render(request, "main/thanks_for_sharing.html", {
        "reciprocal_piece": reciprocal_piece,
        "paused": paused,
    })


@login_required(login_url="/login")
def edit_art_piece(request, public_id):
    # Only the owner can edit, 404 otherwise
    art_piece = get_object_or_404(
        ArtPiece, public_id=public_id, user=request.user)

    if request.method == "POST":
        form = ArtPieceForm(request.POST, instance=art_piece)
        if form.is_valid():
            form.save()
            return redirect("my_shared_art")
    else:
        form = ArtPieceForm(instance=art_piece)

    return render(request, "main/edit_art_piece.html", {"form": form, "piece": art_piece})


@login_required(login_url="/login")
@require_POST
def delete_art_piece(request, public_id):
    piece = get_object_or_404(ArtPiece, public_id=public_id, user=request.user)
    piece.soft_delete(user=request.user, reason='user-initiated')
    piece.approved_status = False
    piece.save(update_fields=['approved_status'])
    messages.success(
        request, "Your piece was deleted. Past recipients will see it as removed.")
    return redirect("my_shared_art")


@login_required(login_url="/login")
def my_shared_art(request):
    """
    Owner’s list: show piece cards + conversation summary:
      - conv_count        : number of distinct 1:1 threads
      - unread_msg_count  : total unread comment notifications
      - new_convo_count   : threads opened since last visit (no owner reply, all unread)
    """
    user = request.user
    my_pieces = ArtPiece.objects.filter(user=user).order_by('-created_at')
    piece_ids = list(my_pieces.values_list('id', flat=True))

    # Legacy support: mark read if older links still point here with ?n=
    n_id = request.GET.get("n")
    if n_id:
        Notification.objects.filter(
            id=n_id, recipient=user, is_read=False
        ).update(is_read=True)

    # ---------- Build conversation basics (conv_count, last) ----------
    comments_qs = (
        Comment.objects
        .filter(art_piece_id__in=piece_ids)
        .select_related('sender', 'recipient', 'art_piece')
        .order_by('created_at')  # chronological for "last" picking
    )

    conv_set_by_piece = defaultdict(set)   # piece_id -> set(other_user_id)
    last_comment_by_piece = {}             # piece_id -> latest Comment

    for c in comments_qs:
        # "other" relative to owner
        other = c.recipient if c.sender_id == user.id else c.sender
        pid = c.art_piece_id
        conv_set_by_piece[pid].add(other.id)
        prev = last_comment_by_piece.get(pid)
        if prev is None or c.created_at > prev.created_at:
            last_comment_by_piece[pid] = c

    # ---------- Unread messages & NEW conversation logic ----------
    # Aggregate comment notifications by (piece, sender, is_read)
    notif_rows = (
        Notification.objects
        .filter(
            recipient=user,
            notification_type='comment',
            art_piece_id__in=piece_ids,
        )
        .values('art_piece_id', 'sender_id', 'is_read')
        .annotate(cnt=Count('id'))
    )

    # piece_id -> total unread message count
    new_msg_counts = defaultdict(int)
    # (piece_id, other_id) -> counts
    pair_counts = defaultdict(lambda: {'unread': 0, 'read': 0})

    for r in notif_rows:
        pid = r['art_piece_id']
        sender_id = r['sender_id']
        if r['is_read']:
            pair_counts[(pid, sender_id)]['read'] = r['cnt']
        else:
            pair_counts[(pid, sender_id)]['unread'] = r['cnt']
            new_msg_counts[pid] += r['cnt']

    # Has owner replied in a given (piece, other) thread?
    # (Owners can't start threads; any owner message will be a reply = parent_comment not null)
    owner_reply_pairs = set(
        Comment.objects
        .filter(art_piece_id__in=piece_ids, sender=user, parent_comment__isnull=False)
        .values_list('art_piece_id', 'recipient_id')
        .distinct()
    )

    # Count NEW conversations: unread>0 AND read==0 AND owner hasn't replied yet
    new_conv_counts = defaultdict(int)
    for (pid, other_id), counts in pair_counts.items():
        if counts['unread'] > 0 and counts['read'] == 0 and (pid, other_id) not in owner_reply_pairs:
            new_conv_counts[pid] += 1

    # ---------- Likes (unchanged) ----------
    likes_by_piece = defaultdict(list)
    likes = (
        Like.objects
        .filter(art_piece_id__in=piece_ids)
        .select_related('user', 'art_piece')
        .order_by('-created_at')
    )
    for like in likes:
        likes_by_piece[like.art_piece].append(like.user)  # newest→oldest

    # ---------- Summaries per piece ----------
    summaries = {}
    for piece in my_pieces:
        pid = piece.id
        summaries[pid] = {
            'conv_count': len(conv_set_by_piece.get(pid, set())),
            'new_msg_count': new_msg_counts.get(pid, 0),
            'new_conv_count': new_conv_counts.get(pid, 0),
            # kept for possible future use
            'last': last_comment_by_piece.get(pid),
        }

    context = {
        'pieces': my_pieces,
        'summaries': summaries,
        'likes_dict': dict(likes_by_piece),
    }
    return render(request, 'main/my_shared_art.html', context)


@never_cache
@login_required(login_url="/login")
def my_received_art(request):
    """
    Recipient’s home: show received pieces in reverse-chronological order,
    with a compact conversation preview per piece (if any).
    """
    user = request.user
    received_qs = (
        SentArtPiece.objects
        .filter(user=user)
        .select_related('art_piece__user')
        .order_by('-sent_time')
    )

    # Legacy support: mark read if older links still point here with ?n=
    n_id = request.GET.get("n")
    if n_id:
        Notification.objects.filter(
            id=n_id, recipient=user, is_read=False
        ).update(is_read=True)

    pieces = [sap.art_piece for sap in received_qs]
    piece_ids = [p.id for p in pieces]
    sharer_ids_by_piece = {p.id: p.user_id for p in pieces}

    # 1:1 threads (recipient <-> sharer), chronological
    thread_qs = (
        Comment.objects
        .filter(art_piece_id__in=piece_ids)
        .filter(
            Q(sender=user, recipient__in=[p.user_id for p in pieces]) |
            Q(recipient=user, sender__in=[p.user_id for p in pieces])
        )
        .select_related("sender", "recipient", "art_piece")
        .order_by("created_at")
    )

    threads_by_piece = defaultdict(list)
    for c in thread_qs:
        sharer_id = sharer_ids_by_piece.get(c.art_piece_id)
        if sharer_id and {c.sender_id, c.recipient_id} == {user.id, sharer_id}:
            threads_by_piece[c.art_piece_id].append(c)

    unread_by_piece = dict(
        Notification.objects
        .filter(
            recipient=user,
            is_read=False,
            notification_type="comment",
            art_piece_id__in=piece_ids,
        )
        .values_list("art_piece_id")
        .annotate(cnt=Count("id"))
        .values_list("art_piece_id", "cnt")
    )

    previews = {}
    for p in pieces:
        t = threads_by_piece.get(p.id, [])
        previews[p.id] = {
            "thread_exists": bool(t),
            "last": t[-1] if t else None,
            "unread_count": unread_by_piece.get(p.id, 0),
        }

    liked_pieces = set(
        Like.objects.filter(user=user, art_piece_id__in=piece_ids)
        .values_list('art_piece_id', flat=True)
    )

    context = {
        'received_pieces': received_qs,   # keep SentArtPiece rows for "New" badge
        'previews': previews,
        'liked_pieces': liked_pieces,
    }
    return render(request, 'main/my_received_art.html', context)


@login_required(login_url="/login")
def art_piece_detail(request, public_id):
    """
    Read-only detail page that:
      - marks relevant notifications read on GET,
      - marks SentArtPiece.seen_at for recipients,
      - shows likes,
      - shows either:
          * recipient view: single thread (chronological),
          * owner view: many threads, ordered by most recent activity DESC,
            with each thread’s messages chronological.
    """
    piece = get_object_or_404(ArtPiece, public_id=public_id)
    user = request.user

    n_id = request.GET.get("n")
    if n_id:
        Notification.objects.filter(
            id=n_id,
            recipient=user,
            is_read=False,
        ).update(is_read=True)

    is_owner = (piece.user_id == user.id)
    has_received = SentArtPiece.objects.filter(
        user=user, art_piece=piece).exists()

    if not (is_owner or has_received):
        raise Http404("Not found")

    # Mark notifications for this piece as read (GET only)
    if request.method == "GET":
        # 1) Everyone: likes are considered "seen" when you view the piece
        Notification.objects.filter(
            recipient=user,
            art_piece=piece,
            is_read=False,
            notification_type="like",
        ).update(is_read=True)

        # 2) Recipients only: comments & the shared_art ping are read on open
        if not is_owner:
            Notification.objects.filter(
                recipient=user,
                art_piece=piece,
                is_read=False,
                notification_type__in=["comment", "shared_art"],
            ).update(is_read=True)

    # Mark the SentArtPiece as seen (recipients only; GET)
    if request.method == "GET" and has_received and not is_owner:
        SentArtPiece.objects.filter(
            user=user, art_piece=piece, seen_at__isnull=True
        ).update(seen_at=timezone.now())

    # Likes (for both modes; you use it differently in template)
    likes_dict = {}
    likes = (
        Like.objects
        .filter(art_piece=piece)
        .select_related('user')
        .order_by('-created_at')  # 👈 force recency
    )
    likes_dict[piece] = [like.user for like in likes]  # newest→oldest

    focus = request.GET.get("focus")            # "piece" | "thread" | None
    focus_other = request.GET.get("other")      # user id as str or None

    if is_owner:
        # Fetch *all* comments where owner is a participant, chronological
        qs = (
            Comment.objects
            .filter(art_piece=piece)
            .filter(Q(sender=user) | Q(recipient=user))
            .select_related("sender", "recipient")
            .order_by("created_at")
        )

        # Group by the "other" participant
        conversations = defaultdict(list)   # other_user -> [comments...]
        last_ts = {}                        # other_user -> latest created_at
        for c in qs:
            other = c.recipient if c.sender_id == user.id else c.sender
            conversations[other].append(c)        # messages oldest→newest
            # ends up as latest per thread
            last_ts[other] = c.created_at

        # Order threads by most recent activity (DESC)
        conversations_list = sorted(
            conversations.items(),               # (other_user, [comments...])
            key=lambda kv: last_ts[kv[0]],
            reverse=True,
        )

        # map[other_user_id] -> unread count (comments sent by `other` to `user`)
        unread_by_other = dict(
            Notification.objects.filter(
                recipient=user,
                art_piece=piece,
                notification_type="comment",
                is_read=False,
            )
            .values_list("sender_id")
            .annotate(cnt=Count("id"))
            .values_list("sender_id", "cnt")
        )

        context = {
            "piece": piece,
            "mode": "owner",
            "conversations": conversations_list,   # list, not dict
            "unread_by_other": unread_by_other,
            "is_liked": False,
            "likes_dict": likes_dict,
            "focus": focus,
            "focus_other": focus_other,
        }
        return render(request, "main/art_piece_detail.html", context)

    # Recipient view: single 1:1 thread (chronological)
    qs = (
        Comment.objects
        .filter(art_piece=piece)
        .filter(Q(sender=user, recipient=piece.user) | Q(sender=piece.user, recipient=user))
        .select_related("sender", "recipient")
        .order_by("created_at")
    )
    context = {
        "piece": piece,
        "mode": "recipient",
        "thread": list(qs),
        "is_liked": Like.objects.filter(user=user, art_piece=piece).exists(),
        "likes_dict": likes_dict,  # not used in recipient view, but harmless
        "autofocus_reply": (focus != "piece"),
    }
    return render(request, "main/art_piece_detail.html", context)


@require_POST
@login_required(login_url="/login")
def comments_create(request):
    """
    Unified endpoint for creating a Comment.
    Accepts:
      - art_piece_id (required)
      - text (required)
      - top_level_comment_id (optional)  -> when present, create a reply in that thread
    Rules:
      - Only the piece owner OR a recipient of that piece may post here.
      - Only RECIPIENTS can start a new thread (no top_level_comment_id).
      - Enforce "one thread per pair": coalesce new first message into existing top-level if it exists.
    Returns the rendered 'main/comment_text.html' for HTMX swap.
    """
    user = request.user
    art_piece_id = request.POST.get("art_piece_id")
    text = (request.POST.get("text") or "").strip()
    top_id = request.POST.get("top_level_comment_id")

    if not art_piece_id or not text:
        return JsonResponse({"ok": False, "error": "Missing fields"}, status=400)

    piece = get_object_or_404(
        ArtPiece.objects.select_related("user"), id=art_piece_id)
    owner = piece.user

    # Participant check
    is_owner = (owner_id := owner.id) == user.id
    has_received = SentArtPiece.objects.filter(
        user=user, art_piece=piece).exists()
    if not (is_owner or has_received):
        return JsonResponse({"ok": False, "error": "Not allowed"}, status=403)

    # If replying to an existing thread
    if top_id:
        top = get_object_or_404(
            Comment.objects.select_related("sender", "recipient", "art_piece"),
            id=top_id,
            art_piece=piece,
            parent_comment__isnull=True,
        )
        # Must be a participant in that 1:1
        if user.id not in {top.sender_id, top.recipient_id}:
            return JsonResponse({"ok": False, "error": "Not allowed"}, status=403)

        # Determine recipient: reply goes to the "other" participant
        recipient = top.sender if top.sender_id != user.id else top.recipient

        form = CommentForm(request.POST)
        if not form.is_valid():
            return JsonResponse({"ok": False, "errors": form.errors}, status=400)

        reply = form.save(commit=False)
        reply.sender = user
        reply.recipient = recipient
        reply.art_piece = piece
        reply.parent_comment = top
        reply.save()

        html = render_to_string("main/comment_text.html",
                                {"comment": reply}, request=request)
        return HttpResponse(html)

    # Else: starting (or adding to) a top-level thread
    # Only recipients can start; owners must reply to an existing thread
    if is_owner:
        return JsonResponse({"ok": False, "error": "Owners can only reply to existing threads."}, status=403)

    # Coalesce into existing top-level if present (one thread per pair)
    top = (
        Comment.objects
        .filter(
            art_piece=piece,
            sender=user,
            recipient=owner,
            parent_comment__isnull=True,
        )
        .first()
    )

    form = CommentForm(request.POST)
    if not form.is_valid():
        return JsonResponse({"ok": False, "errors": form.errors}, status=400)

    try:
        with transaction.atomic():
            c = form.save(commit=False)
            c.sender = user
            c.recipient = owner
            c.art_piece = piece
            if top:
                c.parent_comment = top  # fold into existing thread
            c.save()
    except IntegrityError:
        # Race against the unique partial index for top-level. Re-fetch and attach.
        top = (
            Comment.objects
            .filter(
                art_piece=piece,
                sender=user,
                recipient=owner,
                parent_comment__isnull=True,
            )
            .first()
        )
        c = Comment(
            sender=user,
            recipient=owner,
            art_piece=piece,
            text=text,
            parent_comment=top if top else None,
        )
        c.save()

    html = render_to_string("main/comment_text.html",
                            {"comment": c}, request=request)
    return HttpResponse(html)


@require_POST
@login_required
def mark_thread_read(request):
    """
    Owner opens a thread with 'other' for a given piece: mark only those
    comment notifications as read. Respond with how many were cleared and
    the user's remaining unread total (all notification types).
    """
    piece_public = request.POST.get("piece")
    other_id = request.POST.get("other")

    if not piece_public or not other_id:
        return JsonResponse({"ok": False, "error": "missing params"}, status=400)

    piece = get_object_or_404(ArtPiece, public_id=piece_public)

    # Only the owner should hit this; recipients get auto-read on open.
    if piece.user_id != request.user.id:
        return JsonResponse({"ok": False, "error": "forbidden"}, status=403)

    qs = Notification.objects.filter(
        recipient=request.user,
        art_piece=piece,
        sender_id=other_id,
        notification_type="comment",
        is_read=False,
    )
    cleared = qs.count()
    if cleared:
        qs.update(is_read=True)

    # Remaining unread (all types) for the bell
    unread_total = Notification.objects.filter(
        recipient=request.user,
        is_read=False,
    ).count()

    return JsonResponse({"ok": True, "cleared": cleared, "unread_total": unread_total})


@login_required
@require_POST
def toggle_like_api(request, art_piece_id):
    art_piece = get_object_or_404(ArtPiece, id=art_piece_id)
    user = request.user

    # toggle
    like, created = Like.objects.get_or_create(user=user, art_piece=art_piece)
    if not created:
        like.delete()
        liked = False
    else:
        liked = True
        # If you create Notification/email via a Like signal (see below),
        # do nothing else here. The request returns immediately.

    # Optional: return current like count (if you show it in UI)
    likes_count = Like.objects.filter(art_piece=art_piece).count()

    # Ensure any on_commit hooks run after the DB write, but we still return ASAP
    transaction.on_commit(lambda: None)

    return JsonResponse({"ok": True, "liked": liked, "likes_count": likes_count})


# Notifications
@login_required
def notifications_view(request):
    user = request.user
    now = timezone.now()
    two_weeks_ago = now - timedelta(days=14)
    unread_notifications = Notification.objects.filter(
        recipient=user, is_read=False).order_by('-timestamp')
    read_notifications = Notification.objects.filter(
        recipient=request.user, is_read=True, timestamp__gte=two_weeks_ago)

    return render(request, 'main/notifications.html', {
        'unread_notifications': unread_notifications,
        'read_notifications': read_notifications,
    })


def notification_redirect(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id)

    # Mark as read
    if not notification.is_read:
        notification.is_read = True
        notification.save()

    return redirect(notification.get_redirect_url())


@login_required
def mark_all_notifications_read(request):
    Notification.objects.filter(
        recipient=request.user, is_read=False).update(is_read=True)
    return redirect('notifications')


def LogOut(request):
    logout(request)
    return redirect("/login/")


def choose_art_piece(user):
    # Get all approved art pieces that the user did not submit and have not been sent to them
    art_pieces = ArtPiece.active.filter(
        approved_status=True
    ).exclude(
        user=user
    ).exclude(
        id__in=SentArtPiece.active.filter(
            user=user).values_list('art_piece_id', flat=True)
    )

    # Select a random art piece from the filtered queryset
    if art_pieces.exists():
        return random.choice(art_pieces)
    else:
        return None


def mark_art_piece_as_sent(user, art_piece, *, source="weekly"):
    # Create a record in the SentArtPiece model
    return SentArtPiece.objects.create(user=user, art_piece=art_piece, source=source)


def share_art_piece(user: CustomUser, dry_run=False):
    if user.receive_art_paused:
        return None

    art_piece = choose_art_piece(user)
    if not art_piece:
        return None

    if not dry_run:
        mark_art_piece_as_sent(user, art_piece, source="weekly")

    return art_piece


def custom_404(request, exception):
    return render(request, 'main/404.html', status=404)


def custom_500(request):
    return render(request, 'main/500.html', status=500)


class CustomPasswordResetView(auth_views.PasswordResetView):
    email_template_name = 'registration/password_reset_email.html'

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Gentle UX hints
        form.fields['email'].widget.attrs.update({
            'autofocus': 'autofocus',
            'autocomplete': 'email',
            'placeholder': 'you@example.com',
        })
        return form

    def send_mail(self, subject_template_name, email_template_name,
                  context, from_email, to_email, html_email_template_name=None):
        """
        Send a django.core.mail.EmailMultiAlternatives to `to_email`.
        """
        subject = render_to_string(subject_template_name, context)
        # Email subject *must not* contain newlines
        subject = ''.join(subject.splitlines())
        body = render_to_string(email_template_name, context)
        plain_body = strip_tags(body)
        send_mail(subject, plain_body, from_email,
                  [to_email], html_message=body)

    # Override the method to use custom email subject and content
    def form_valid(self, form):
        opts = {
            'use_https': self.request.is_secure(),
            'token_generator': self.token_generator,
            'from_email': 'Omnivore Arts <support@omnivorearts.com>',
            'email_template_name': self.email_template_name,
            'subject_template_name': 'registration/password_reset_subject.txt',
            'request': self.request,
            'html_email_template_name': self.email_template_name,
        }
        form.save(**opts)
        return super(auth_views.PasswordResetView, self).form_valid(form)


class CustomPasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    form_class = CustomSetPasswordForm
    template_name = "registration/password_reset_confirm.html"
    success_url = reverse_lazy("password_reset_complete")


@login_required
def account_info_settings(request):
    if request.method == 'POST':
        form = AccountInfoForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'message': 'Account information updated.'})
            messages.success(
                request, "Account information updated.", extra_tags="account")
            return redirect(reverse('account_info_settings') + '#account-info')
    else:
        form = AccountInfoForm(instance=request.user)

    art_delivery_form = ArtDeliveryForm(instance=request.user)
    email_form = EmailPreferencesForm(instance=request.user)
    password_form = CustomPasswordChangeForm(user=request.user)

    return render(request, 'main/account_settings.html', {
        'account_form': form,
        'art_delivery_form': art_delivery_form,
        'email_form': email_form,
        'password_form': password_form
    })


@login_required
def art_delivery_settings(request):
    """
    Handles the single toggle 'receive_art_paused' with the same AJAX pattern:
    - On AJAX: return JSON { message: ... }
    - On non-AJAX: use messages framework and redirect to #art-delivery
    """
    if request.method == 'POST':
        form = ArtDeliveryForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                paused = form.cleaned_data.get("receive_art_paused")
                msg = "Art delivery paused." if paused else "Art delivery resumed."
                return JsonResponse({"message": msg, "paused": paused})
            messages.success(
                request, "Art delivery preference updated.", extra_tags="artdelivery")
            return redirect(reverse('art_delivery_settings') + '#art-delivery')

    # GET or invalid POST (non-AJAX): render full page with all sections
    account_form = AccountInfoForm(instance=request.user)
    art_delivery_form = ArtDeliveryForm(instance=request.user)
    email_form = EmailPreferencesForm(instance=request.user)
    password_form = CustomPasswordChangeForm(user=request.user)

    return render(request, 'main/account_settings.html', {
        'account_form': account_form,
        'email_form': email_form,
        'password_form': password_form,
        'art_delivery_form': art_delivery_form,
    })


@login_required
def email_pref_settings(request):
    if request.method == 'POST':
        form = EmailPreferencesForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({
                    "message": "Email preferences updated."
                })
            messages.success(
                request, "Email preferences updated.", extra_tags="email")
            return redirect(reverse('email_pref_settings') + '#email-prefs')
    else:
        form = EmailPreferencesForm(instance=request.user)

    account_form = AccountInfoForm(instance=request.user)
    art_delivery_form = ArtDeliveryForm(instance=request.user)
    password_form = CustomPasswordChangeForm(user=request.user)

    return render(request, 'main/account_settings.html', {
        'account_form': account_form,
        'art_delivery_form': art_delivery_form,
        'email_form': form,
        'password_form': password_form
    })


@login_required
def password_settings(request):
    if request.method == 'POST':
        form = CustomPasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"message": "Password successfully updated."})
            else:
                messages.success(
                    request, "Password successfully updated.", extra_tags="password")
                return redirect(reverse('password_settings') + '#password')
        else:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({
                    "errors": form.errors.as_json()
                }, status=400)

    # fallback for GET or non-AJAX
    form = CustomPasswordChangeForm(user=request.user)
    account_form = AccountInfoForm(instance=request.user)
    art_delivery_form = ArtDeliveryForm(instance=request.user)
    email_form = EmailPreferencesForm(instance=request.user)

    return render(request, 'main/account_settings.html', {
        'account_form': account_form,
        'art_delivery_form': art_delivery_form,
        'email_form': email_form,
        'password_form': form
    })


# map token kinds -> CustomUser boolean fields
KIND_TO_FIELD = {
    "art": "email_on_art_shared",
    "comment": "email_on_comment",
    "like": "email_on_like",
}

KIND_LABELS = {
    "art": "new art shared",
    "comment": "comments & replies",
    "like": "likes",
}


def unsubscribe_email(request, token: str):
    try:
        # raises SignatureExpired/BadSignature as needed
        payload = load_unsub_token(token)
    except SignatureExpired:
        return render(
            request,
            "main/unsubscribe_result.html",
            {"ok": False, "error": "This unsubscribe link has expired."},
            status=400,
        )
    except BadSignature:
        return render(
            request,
            "main/unsubscribe_result.html",
            {"ok": False, "error": "Invalid unsubscribe link."},
            status=400,
        )

    uid = payload.get("uid")
    kind = payload.get("kind")
    field_name = KIND_TO_FIELD.get(kind)

    if not uid or not field_name:
        return HttpResponseBadRequest("Invalid unsubscribe data.")

    try:
        user = CustomUser.objects.get(pk=uid)
    except CustomUser.DoesNotExist:
        return render(
            request,
            "main/unsubscribe_result.html",
            {"ok": False, "error": "User not found."},
            status=404,
        )

    setattr(user, field_name, False)
    user.save(update_fields=[field_name])

    return render(
        request,
        "main/unsubscribe_result.html",
        {"ok": True, "category_label": KIND_LABELS.get(kind, "these emails")},
    )


@login_required
@require_POST
def set_timezone(request):
    try:
        payload = json.loads(request.body or "{}")
        tz = payload.get("timezone")
        ZoneInfo(tz)  # validate
    except Exception:
        return HttpResponseBadRequest("Invalid timezone")

    request.user.timezone = tz
    request.user.save(update_fields=["timezone"])
    return JsonResponse({"ok": True})


def tz_debug(request):
    return JsonResponse({
        "cookie_tz": request.COOKIES.get("tz"),
        "user_tz": getattr(getattr(request.user, "profile", None), "timezone", None) or getattr(request.user, "timezone", None),
        "current_tz": str(timezone.get_current_timezone()),
    })
