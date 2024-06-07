from django.shortcuts import render, redirect, get_object_or_404
from .forms import RegisterForm, ArtPieceForm
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.utils.safestring import mark_safe
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


def send_art_piece_email(request, user_id):
    user = User.objects.get(id=user_id)
    art_piece = choose_art_piece(user)

    if not art_piece:
        return HttpResponse('No eligible art piece to send.')

    # Mark the art piece as sent
    mark_art_piece_as_sent(user, art_piece)

    # Prepare the link or plain text based on the existence of art_link
    if art_piece.link:
        art_link_or_name = mark_safe(
            f'<a href="{art_piece.link}" target="_blank">{art_piece.piece_name}</a>')
    else:
        art_link_or_name = art_piece.piece_name

    # Load the email template
    template_path = os.path.join(
        settings.BASE_DIR, 'main/templates/emails/email_template.html')
    with open(template_path, 'r') as file:
        html_template = file.read()

    sender = f'{art_piece.user.first_name} {art_piece.user.last_name}'

    # Define the context to be used in the template
    context = {
        'username': user.first_name,
        'art_link_or_name': art_link_or_name,
        'artist_name': art_piece.artist_name,
        'piece_description': art_piece.piece_description,
        'sender': sender
    }

    # Render the HTML content with the context
    html_content = render_to_string('emails/email_template.html', context)

    subject = f"You have new art from {sender}!"
    from_email = 'Omnivore Arts <oliver@omnivorearts.com>'
    to = [user.email]

    msg = EmailMultiAlternatives(subject, '', from_email, to)
    msg.attach_alternative(html_content, "text/html")
    msg.send()

    return HttpResponse('Art piece email sent!')


def custom_404(request, exception):
    return render(request, 'main/404.html', status=404)
