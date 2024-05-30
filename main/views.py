from django.shortcuts import render, redirect
from .forms import RegisterForm, ArtPieceForm
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.http import HttpResponse
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


def send_test_email(request):
    send_mail(
        'Test Email',
        'This is a test email sent from Django using Amazon SES.',
        'Omnivore Arts <oliver@omnivorearts.com>',
        ['jonathan.heaney@gmail.com'],
        fail_silently=False,
    )
    return HttpResponse('Test email sent!')
