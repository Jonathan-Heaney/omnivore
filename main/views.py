from django.shortcuts import render, redirect, get_object_or_404
from .forms import RegisterForm, ArtPieceForm, CommentForm, AccountInfoForm, EmailPreferencesForm, CustomPasswordChangeForm
from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash, authenticate, views as auth_views
from django.contrib.auth.decorators import login_required
from django.utils.html import strip_tags
from django.core.mail import send_mail
from django.urls import reverse
import random
from collections import defaultdict
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from datetime import timedelta
from django.views.decorators.http import require_POST
from .models import ArtPiece, SentArtPiece, CustomUser, Comment, Like, Notification


def home(request):
    return render(request, 'main/home.html')


def sign_up(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('/home')
    else:
        form = RegisterForm()

    return render(request, 'registration/sign_up.html', {"form": form})


@login_required(login_url="/login")
def share_art(request):
    today = timezone.now().date()
    first_day_of_month = timezone.make_aware(
        timezone.datetime(today.year, today.month, 1))
    user = request.user
    already_submitted = ArtPiece.objects.filter(
        user=user).filter(created_at__gte=first_day_of_month)

    if already_submitted:
        return render(request, 'main/already_submitted.html')

    if request.method == 'POST':
        form = ArtPieceForm(request.POST)
        if form.is_valid():
            art_piece = form.save(commit=False)
            art_piece.user = request.user
            art_piece.save()
            piece_to_share = choose_art_piece(user)
            mark_art_piece_as_sent(user, piece_to_share)
            return render(request, 'main/thanks_for_sharing.html')
    else:
        form = ArtPieceForm()

    return render(request, 'main/share_art.html', {"form": form})


@login_required(login_url="/login")
def edit_art_piece(request, pk):
    art_piece = get_object_or_404(ArtPiece, pk=pk)

    if request.method == 'POST':
        form = ArtPieceForm(request.POST, instance=art_piece)
        if form.is_valid():
            form.save()
            return redirect("/my-shared-art")
    else:
        form = ArtPieceForm(instance=art_piece)

    return render(request, 'main/edit_art_piece.html', {'form': form})


@login_required(login_url="/login")
def delete_art_piece(request, pk):
    art_piece = get_object_or_404(ArtPiece, pk=pk)
    if request.method == 'POST':
        art_piece.delete()
        return redirect('my_shared_art')

    return redirect('my_shared_art')


@login_required(login_url="/login")
def my_shared_art(request):
    user = request.user
    my_pieces = ArtPiece.objects.filter(user=user).order_by('-created_at')

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


@require_POST
def toggle_like(request, art_piece_id):
    art_piece = get_object_or_404(ArtPiece, id=art_piece_id)
    user = request.user

    like, created = Like.objects.get_or_create(user=user, art_piece=art_piece)
    if not created:
        like.delete()
        liked = False
    else:
        liked = True

    heart_html = render_to_string(
        'main/heart_button.html', {'piece': art_piece, 'liked': liked}, request=request)

    return HttpResponse(heart_html)


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


def mark_art_piece_as_sent(user, art_piece):
    # Create a record in the SentArtPiece model
    SentArtPiece.objects.create(
        user=user, art_piece=art_piece)


def send_art_piece_email(user):
    art_piece = choose_art_piece(user)

    if not art_piece:
        return

    # Mark the art piece as sent
    mark_art_piece_as_sent(user, art_piece)

    sender = f'{art_piece.user.first_name} {art_piece.user.last_name}'

    art_page_link = 'https://omnivorearts.com/my-received-art'

    # Define the context to be used in the template
    context = {
        'username': user.first_name,
        'sender': sender,
        'link': art_page_link
    }

    # Render the HTML content with the context
    html_content = render_to_string('emails/plain_email.html', context)

    subject = f"You have new art from {sender}!"
    from_email = 'Omnivore Arts <oliver@omnivorearts.com>'
    to = [user.email]

    msg = EmailMultiAlternatives(subject, '', from_email, to)
    msg.attach_alternative(html_content, "text/html")
    msg.send()


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

    email_form = EmailPreferencesForm(instance=request.user)
    password_form = CustomPasswordChangeForm(user=request.user)

    return render(request, 'main/account_settings.html', {
        'account_form': form,
        'email_form': email_form,
        'password_form': password_form
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
    password_form = CustomPasswordChangeForm(user=request.user)

    return render(request, 'main/account_settings.html', {
        'account_form': account_form,
        'email_form': form,
        'password_form': password_form
    })


@login_required
def password_settings(request):
    if request.method == 'POST':
        form = CustomPasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Prevent logout
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({
                    "message": "Password successfully updated."
                })
            messages.success(
                request, "Password successfully updated.", extra_tags="password")
            return redirect(reverse('password_settings') + '#password')
    else:
        form = CustomPasswordChangeForm(user=request.user)

    account_form = AccountInfoForm(instance=request.user)
    email_form = EmailPreferencesForm(instance=request.user)

    return render(request, 'main/account_settings.html', {
        'account_form': account_form,
        'email_form': email_form,
        'password_form': form
    })
