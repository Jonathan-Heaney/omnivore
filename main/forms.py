from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm, AuthenticationForm, SetPasswordForm
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

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError(
                "An account with this email already exists.")
        return email

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
    error_messages = AuthenticationForm.error_messages | {
        # Replace default "Note that both fields may be case-sensitive."
        "invalid_login": "Please enter a correct email and password.",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Username field: autofocus + proper autocomplete
        self.fields["username"].widget.attrs.update({
            "autofocus": "autofocus",
            "autocomplete": "username",
            "placeholder": "you@example.com",
        })

        # Password field: hook up your password-eye + autocomplete
        self.fields["password"].widget.attrs.update({
            "class": "js-password",
            "autocomplete": "current-password",
            "placeholder": "Password",
        })

    # Normalize the “username” (which is actually the email)
    def clean_username(self):
        u = self.cleaned_data.get("username") or ""
        return u.strip().lower()

    def clean(self):
        # call parent to run the actual authentication
        return super().clean()


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

        def clean_email(self):
            email = (self.cleaned_data.get("email") or "").strip().lower()
            qs = CustomUser.objects.filter(email=email)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(
                    "Another account is already using this email.")
            return email


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


class CustomSetPasswordForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ensure both fields get the toggle class + good autocomplete hints
        for name in ("new_password1", "new_password2"):
            w = self.fields[name].widget
            # merge classes instead of overwriting
            existing = w.attrs.get("class", "")
            w.attrs["class"] = (existing + " js-password").strip()
            # hint browsers correctly
            w.attrs.setdefault("autocomplete", "new-password")


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
