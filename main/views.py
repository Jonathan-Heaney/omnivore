from django.shortcuts import render, redirect
from .forms import RegisterForm, ArtPieceForm
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
import os
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.conf import settings
from .models import ArtPiece


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
def my_shared_art(request):
    user = request.user
    my_pieces = ArtPiece.objects.filter(user=user).order_by('-created_at')

    if request.method == 'POST':
        piece_id = request.POST.get("piece-id")

        if piece_id:
            piece = ArtPiece.objects.filter(id=piece_id).first()
            if piece:
                piece.delete()

    return render(request, 'main/my_shared_art.html', {"pieces": my_pieces})


def LogOut(request):
    logout(request)
    return redirect("/login/")


def load_email_template():
    template_path = os.path.join(
        settings.BASE_DIR, 'main/templates/emails/email_template.html')
    with open(template_path, 'r') as file:
        template = file.read()
    return template


def send_test_email(request):
    # Load the email template
    html_template = load_email_template()

    # Define the context to be used in the template
    context = {
        'username': 'Jonathan',
        'art_image_url': 'https://plus.unsplash.com/premium_photo-1669863280125-7789ef60adc0?q=80&w=2070&auto=format&fit=crop&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D',
        'art_description': 'This is a beautiful piece of art created by a renowned artist.',
    }

    # Render the HTML content with the context
    html_content = render_to_string('emails/email_template.html', context)

    subject = 'Test Email with MJML'
    from_email = 'Omnivore Arts <oliver@omnivorearts.com>'
    to = ['jonathan.heaney@gmail.com']

    msg = EmailMultiAlternatives(subject, '', from_email, to)
    msg.attach_alternative(html_content, "text/html")
    msg.send()

    return HttpResponse('Test email sent!')
