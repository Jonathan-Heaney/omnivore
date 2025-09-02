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
    error_messages = {
        "password_mismatch": "Passwords don’t match. Please re-enter both fields."
    }

    first_name = forms.CharField(
        required=True,
        widget=forms.TextInput(
            attrs={"autofocus": "autofocus", "autocomplete": "given-name"})
    )
    last_name = forms.CharField(required=True, widget=forms.TextInput(
        attrs={"autocomplete": "family-name"}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(
        attrs={"autocomplete": "email"}))
    username = forms.CharField(
        required=True,
        validators=[validate_username],
        help_text="Choose a unique username (not your email).",
        widget=forms.TextInput(attrs={"autocomplete": "username"})
    )
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(
            attrs={"class": "js-password", "autocomplete": "new-password"})
    )
    password2 = forms.CharField(
        label="Confirm password",
        widget=forms.PasswordInput(
            attrs={"class": "js-password", "autocomplete": "new-password"})
    )

    class Meta:
        model = CustomUser
        fields = ["first_name", "last_name", "username",
                  "email", "password1", "password2"]

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")

        # If the form has a non-field mismatch, also attach it to password2:
        if p1 and p2 and p1 != p2:
            self.add_error(
                "password2", self.error_messages["password_mismatch"])

        return cleaned

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_show_errors = True
        self.helper.form_tag = False
        self.helper.label_class = "form-label"
        self.helper.form_show_labels = True
        self.helper.layout = Layout(
            Field("first_name"),
            Field("last_name"),
            Field("email"),
            Field("username"),
            Field("password1"),
            Field("password2"),
            HTML(
                '<p class="form-hint mt-1">Use at least 8 characters. Avoid reusing a password.</p>'),
        )

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
