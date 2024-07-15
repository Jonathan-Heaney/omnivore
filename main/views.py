from django.shortcuts import render, redirect, get_object_or_404
from .forms import RegisterForm, ArtPieceForm, CommentForm
from django.contrib.auth import login, logout, authenticate, views as auth_views
from django.contrib.auth.decorators import login_required
from django.utils.html import strip_tags
from django.core.mail import send_mail
import os
import random
import logging
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.conf import settings
from django.utils import timezone
from .models import ArtPiece, SentArtPiece, CustomUser, Comment


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
    comments = Comment.objects.filter(art_piece__user=user).select_related(
        'art_piece', 'sender', 'recipient', 'parent_comment')

    # Creates all the conversations on an art piece, by setting up the top-level comments that start each conversation
    conversations = {}
    for comment in comments:
        if comment.art_piece not in conversations:
            conversations[comment.art_piece] = []
        if not comment.parent_comment:
            conversations[comment.art_piece].append(comment)

    # Handle reply submission
    if request.method == 'POST' and 'reply_comment' in request.POST:
        comment_id = request.POST.get('comment_id')
        parent_comment = get_object_or_404(Comment, id=comment_id)
        # Traverse to the top-level parent comment
        while parent_comment.parent_comment:
            parent_comment = parent_comment.parent_comment
        form = CommentForm(request.POST)
        if form.is_valid():
            reply = form.save(commit=False)
            reply.sender = request.user
            reply.recipient = parent_comment.sender if parent_comment.sender != request.user else parent_comment.recipient
            reply.art_piece = parent_comment.art_piece
            reply.parent_comment = parent_comment
            reply.save()
            return redirect('my_shared_art')

    context = {
        'pieces': my_pieces,
        'conversations': conversations,
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

    conversations = {}
    for comment in comments:
        if comment.art_piece not in conversations:
            conversations[comment.art_piece] = []
        conversations[comment.art_piece].append(comment)

    print(conversations)

    # Handle new comment submission
    if request.method == 'POST' and 'add_comment' in request.POST:
        art_piece_id = request.POST.get('art_piece_id')
        art_piece = get_object_or_404(ArtPiece, id=art_piece_id)

        # Check if the user already has a parent comment for this piece
        parent_comment = Comment.objects.filter(
            art_piece=art_piece, recipient=user, parent_comment__isnull=True).first()

        form = CommentForm(request.POST)
        if form.is_valid():
            new_comment = form.save(commit=False)
            new_comment.sender = request.user
            new_comment.recipient = art_piece.user
            new_comment.art_piece = art_piece
            if parent_comment:
                new_comment.parent_comment = parent_comment
            new_comment.save()
            return redirect('my_received_art')

    # Handle reply submission
    if request.method == 'POST' and 'reply_comment' in request.POST:
        comment_id = request.POST.get('comment_id')
        parent_comment = get_object_or_404(Comment, id=comment_id)
        while parent_comment.parent_comment:
            parent_comment = parent_comment.parent_comment
        form = CommentForm(request.POST)
        if form.is_valid():
            reply = form.save(commit=False)
            reply.sender = request.user
            reply.recipient = parent_comment.sender if parent_comment.sender != request.user else parent_comment.recipient
            reply.art_piece = parent_comment.art_piece
            reply.parent_comment = parent_comment
            reply.save()
            return redirect('my_received_art')

    context = {
        'pieces': pieces,
        'conversations': conversations,
    }

    return render(request, 'main/my_received_art.html', context)


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
