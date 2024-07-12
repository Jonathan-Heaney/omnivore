from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import ArtPiece, CustomUser, Comment
from django.core.exceptions import ValidationError


def validate_username(value):
    if '@' in value:
        raise ValidationError("Username cannot contain the '@' symbol.")


class RegisterForm(UserCreationForm):
    first_name = forms.CharField(
        required=True, widget=forms.TextInput(attrs={'autofocus': 'autofocus'}))
    last_name = forms.CharField(required=True)
    email = forms.EmailField(required=True)
    username = forms.CharField(
        required=True,
        validators=[validate_username],
        help_text="Please choose a unique username. Do not use your email address."
    )

    class Meta:
        model = CustomUser
        fields = ["first_name", "last_name", "username",
                  "email", "password1", "password2"]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class ArtPieceForm(forms.ModelForm):
    class Meta:
        model = ArtPiece
        fields = ["piece_name", "artist_name", "piece_description", "link"]
        labels = {
            "artist_name": "Who is the artist/creator(s)?",
            "piece_name": "What is the name of the artwork?",
            "link": "Include a link to view the piece online, if applicable.",
            "piece_description": "Tell us a bit about the piece and what it means to you. Why are you sharing it? What should people know about it? "
        }


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['text']
