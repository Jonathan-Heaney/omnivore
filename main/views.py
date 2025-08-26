from .models import ArtPiece, Comment, SentArtPiece
from django.shortcuts import get_object_or_404, render
from django.db.models import Q
from django.http import Http404
from django.http import JsonResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from .forms import RegisterForm, ArtPieceForm, CommentForm, AccountInfoForm, ArtDeliveryForm, EmailPreferencesForm, CustomPasswordChangeForm
from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash, authenticate, views as auth_views
from django.contrib.auth.decorators import login_required
from django.utils.html import strip_tags
from django.core.mail import send_mail
from django.urls import reverse
from django.db import transaction
import random
from collections import defaultdict
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest
from django.core.signing import BadSignature, SignatureExpired
from django.utils import timezone
from datetime import timedelta
from django.views.decorators.http import require_POST
from .models import ArtPiece, SentArtPiece, CustomUser, Comment, Like, Notification, ReciprocalGrant, WelcomeGrant
from main.utils.email_unsub import load_unsub_token


def home(request):
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
    qs = ArtPiece.objects.filter(
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
    art_piece = get_object_or_404(
        ArtPiece, public_id=public_id, user=request.user)
    art_piece.delete()
    return redirect("my_shared_art")


@login_required(login_url="/login")
def my_shared_art(request):
    user = request.user
    my_pieces = ArtPiece.objects.filter(user=user).order_by('-created_at')

    n_id = request.GET.get("n")
    if n_id:
        Notification.objects.filter(
            id=n_id, recipient=request.user, is_read=False
        ).update(is_read=True)

    # Dictionary to hold conversations by art piece
    conversations = defaultdict(lambda: defaultdict(list))
    likes_dict = {}

    for piece in my_pieces:
        comments = Comment.objects.filter(art_piece=piece).select_related(
            'sender', 'recipient').order_by('created_at')
        for comment in comments:
            recipient = comment.recipient if comment.sender == user else comment.sender
            conversations[piece][recipient].append(comment)

        # Fetch likes for each piece
        likes = Like.objects.filter(art_piece=piece).select_related('user')
        users = [like.user for like in likes]
        likes_dict[piece] = users

    # Convert defaultdict to regular dict for template
    conversations_dict = {piece: dict(convo)
                          for piece, convo in conversations.items()}

    if 'hx-request' in request.headers:
        comment_id = request.POST.get('comment_id')
        current_comment = get_object_or_404(Comment, id=comment_id)

        # Traverse to the top-level parent comment
        while current_comment.parent_comment:
            current_comment = current_comment.parent_comment
        top_level_comment = current_comment

        form = CommentForm(request.POST)
        if form.is_valid():
            reply = form.save(commit=False)
            reply.sender = request.user
            reply.recipient = top_level_comment.sender
            reply.art_piece = top_level_comment.art_piece
            reply.parent_comment = top_level_comment
            reply.save()

            context = {
                'comment': reply,
            }

            html = render_to_string(
                'main/comment_text.html', context, request=request)
            return HttpResponse(html)

    context = {
        'pieces': my_pieces,
        'conversations': conversations_dict,
        'likes_dict': likes_dict
    }

    return render(request, 'main/my_shared_art.html', context)


@login_required(login_url="/login")
def my_received_art(request):
    user = request.user
    received_pieces = SentArtPiece.objects.filter(
        user=user).select_related('art_piece__user').order_by('-sent_time')

    n_id = request.GET.get("n")
    if n_id:
        Notification.objects.filter(
            id=n_id, recipient=request.user, is_read=False
        ).update(is_read=True)

    pieces = [received_piece.art_piece for received_piece in received_pieces]
    comments = Comment.objects.filter(art_piece__in=pieces, sender=user) | Comment.objects.filter(
        art_piece__in=pieces, recipient=user)

    # Fetch liked pieces by the current user
    liked_pieces = set(Like.objects.filter(
        user=user).values_list('art_piece_id', flat=True))

    if 'hx-request' in request.headers:
        form = CommentForm(request.POST)
        if form.is_valid():
            new_comment = form.save(commit=False)
            new_comment.sender = request.user
            art_piece_id = request.POST.get('art_piece_id')
            new_comment.art_piece = get_object_or_404(
                ArtPiece, id=art_piece_id)
            new_comment.recipient = new_comment.art_piece.user
            new_comment.save()

            context = {
                'comment': new_comment,
            }

            html = render_to_string(
                'main/comment_text.html', context, request=request)
            return HttpResponse(html)

    context = {
        'pieces': pieces,
        'comments': comments,
        'liked_pieces': liked_pieces
    }

    return render(request, 'main/my_received_art.html', context)


# views.py

@login_required(login_url="/login")
def art_piece_detail(request, public_id):
    piece = get_object_or_404(ArtPiece, public_id=public_id)
    user = request.user

    # Viewer must be the owner OR someone who actually received this piece.
    is_owner = (piece.user_id == user.id)
    has_received = SentArtPiece.objects.filter(
        user=user, art_piece=piece).exists()

    if not (is_owner or has_received):
        # 404 so people can't probe others' art
        from django.http import Http404
        raise Http404("Not found")

    if is_owner:
        # OWNER MODE: group all messages by the *other participant*
        qs = (Comment.objects
              .filter(art_piece=piece)
              .filter(Q(sender=user) | Q(recipient=user))
              .select_related("sender", "recipient")
              .order_by("created_at"))

        # key = other_user, value = [comments...]
        conversations = defaultdict(list)
        for c in qs:
            other = c.recipient if c.sender_id == user.id else c.sender
            conversations[other].append(c)

        context = {
            "piece": piece,
            "mode": "owner",
            # dict(other_user -> list[Comment])
            "conversations": dict(conversations),
        }
        return render(request, "main/art_piece_detail.html", context)

    else:
        # RECIPIENT MODE: only the 1:1 thread between viewer and the sharer
        qs = (Comment.objects
              .filter(art_piece=piece)
              .filter(
                  Q(sender=user, recipient=piece.user) |
                  Q(sender=piece.user, recipient=user)
              )
              .select_related("sender", "recipient")
              .order_by("created_at"))

        context = {
            "piece": piece,
            "mode": "recipient",
            "thread": list(qs),
        }
        return render(request, "main/art_piece_detail.html", context)


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
    art_pieces = ArtPiece.objects.filter(
        approved_status=True
    ).exclude(
        user=user
    ).exclude(
        id__in=SentArtPiece.objects.filter(
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
    return render(request, 'main/404.html', status=500)


class CustomPasswordResetView(auth_views.PasswordResetView):
    email_template_name = 'registration/password_reset_email.html'

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
