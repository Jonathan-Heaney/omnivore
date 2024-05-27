from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import ArtPiece


class RegisterForm(UserCreationForm):
    first_name = forms.CharField(required=True)
    last_name = forms.CharField(required=True)
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "username",
                  "email", "password1", "password2"]


class ArtPieceForm(forms.ModelForm):
    class Meta:
        model = ArtPiece
        fields = ["artist_name", "piece_name", "piece_description", "link"]
