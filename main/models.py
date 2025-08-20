from django.contrib.auth.models import User
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.urls import reverse


class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    email_on_art_shared = models.BooleanField(default=True)
    email_on_comment = models.BooleanField(default=True)
    email_on_like = models.BooleanField(default=False)

    # User can pause actually receiving new art (in-app + email)
    receive_art_paused = models.BooleanField(default=False)

    # So you don't have to query SentArtPiece each time
    last_art_sent_at = models.DateTimeField(null=True, blank=True)

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='customuser_set',
        blank=True,
        help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.',
        verbose_name='groups',
    )

    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='customuser_set',
        blank=True,
        help_text='Specific permission set for this user.',
        verbose_name='user permissions',
    )

    def save(self, *args, **kwargs):
        self.first_name = self.first_name.strip()
        self.last_name = self.last_name.strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.first_name} {self.last_name}'


class ArtPiece(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE)
    artist_name = models.CharField(max_length=200)
    piece_name = models.CharField(max_length=300)
    piece_description = models.TextField()
    link = models.URLField(blank=True, null=True)
    approved_status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.piece_name


class SentArtPiece(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE)
    art_piece = models.ForeignKey(ArtPiece, on_delete=models.CASCADE)
    sent_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'art_piece')

    def __str__(self):
        return f'{self.user} - {self.art_piece}'

    def art_piece_submitter(self):
        return self.art_piece.user

    art_piece_submitter.short_description = 'Submitted By'


class Comment(models.Model):
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_comments')
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_comments')
    art_piece = models.ForeignKey(ArtPiece, on_delete=models.CASCADE)
    text = models.TextField()
    parent_comment = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.sender} on {self.art_piece}: {self.text[:30]}'


class Like(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE)
    art_piece = models.ForeignKey(ArtPiece, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'art_piece')

    def __str__(self):
        return f"{self.user} loves {self.art_piece}"


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('like', 'Like'),
        ('comment', 'Comment'),
        ('shared_art', 'Shared Art'),
    ]

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_notifications'
    )
    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPES
    )
    art_piece = models.ForeignKey(
        ArtPiece,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    comment = models.ForeignKey(
        Comment,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    is_read = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    message = models.TextField()

    class Meta:
        ordering = ['-timestamp']

    def get_redirect_url(self):
        if self.notification_type == 'like':
            return reverse('my_shared_art') + f"#art-{self.art_piece.id}"
        elif self.notification_type == 'shared_art':
            return reverse('my_received_art') + f"#art-{self.art_piece.id}"
        elif self.notification_type == 'comment':
            # Choose logic based on sender/recipient relationship
            if self.recipient == self.art_piece.user:
                return reverse('my_shared_art') + f"#art-{self.art_piece.id}"
            else:
                return reverse('my_received_art') + f"#art-{self.art_piece.id}"
        else:
            return reverse('notifications')  # fallback if something's wrong

    def __str__(self):
        return f'{self.sender} -> {self.recipient} ({self.notification_type})'
