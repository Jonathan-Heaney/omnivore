from django.shortcuts import render, redirect, get_object_or_404
from .forms import RegisterForm, ArtPieceForm
from django.contrib.auth import login, logout, authenticate, views as auth_views
from django.contrib.auth.decorators import login_required
from django.utils.html import strip_tags
from django.core.mail import send_mail
import os
import random
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.conf import settings
from .models import ArtPiece, SentArtPiece
from django.contrib.auth.models import User


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
    if request.method == 'POST':
        form = ArtPieceForm(request.POST)
        if form.is_valid():
            art_piece = form.save(commit=False)
            art_piece.user = request.user
            art_piece.save()
            return redirect("/my-shared-art")
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

    return render(request, 'main/my_shared_art.html', {"pieces": my_pieces})


@login_required(login_url="/login")
def my_received_art(request):
    user = request.user
    received_pieces = SentArtPiece.objects.filter(
        user=user).select_related('art_piece__user').order_by('-sent_time')

    pieces = [received_piece.art_piece for received_piece in received_pieces]

    return render(request, 'main/my_received_art.html', {"pieces": pieces})


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
            'from_email': 'Omnivore Arts <jonathan@omnivorearts.com>',
            'email_template_name': self.email_template_name,
            'subject_template_name': 'registration/password_reset_subject.txt',
            'request': self.request,
            'html_email_template_name': self.email_template_name,
        }
        form.save(**opts)
        return super(auth_views.PasswordResetView, self).form_valid(form)
