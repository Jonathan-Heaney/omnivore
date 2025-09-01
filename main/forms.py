from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm, AuthenticationForm
from .models import ArtPiece, CustomUser, Comment
from django.core.exceptions import ValidationError
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, HTML, Submit, Div


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
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={'class': 'js-password'})
    )
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={'class': 'js-password'})
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


class CustomAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password'].widget.attrs.update({'class': 'js-password'})


class AccountInfoForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'username']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'username': forms.TextInput(attrs={'class': 'form-control'}),
        }


class ArtDeliveryForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ["receive_art_paused"]
        labels = {
            "receive_art_paused": "Pause receiving new art",
        }
        help_texts = {
            "receive_art_paused": (
                "When paused, you won’t receive new art. "
                "You can still view previously received art. "
                "You’ll continue to receive comments/likes emails based on your preferences."
            ),
        }
        widgets = {
            "receive_art_paused": forms.CheckboxInput(attrs={"class": "form-check-input"})
        }


class EmailPreferencesForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['email_on_art_shared', 'email_on_comment', 'email_on_like']
        labels = {
            'email_on_art_shared': 'Email me when someone shares art with me',
            'email_on_comment': 'Email me when someone comments on my art',
            'email_on_like': 'Email me when someone likes my art',
        }


class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'old_password' in self.fields:
            self.fields['old_password'].widget.attrs.pop('autofocus', None)


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

        widgets = {
            "piece_description": forms.Textarea(attrs={"rows": 6}),

        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False  # we wrap the <form> in the template
        self.helper.label_class = "form-label"
        self.helper.field_class = ""
        self.helper.form_show_labels = True
        self.helper.layout = Layout(
            Field("piece_name"),
            Field("artist_name"),
            Field("piece_description"),
            Field("link"),
            HTML('<p class="form-hint mt-1">Share why it matters to you—context helps!</p>')
        )


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['text']
