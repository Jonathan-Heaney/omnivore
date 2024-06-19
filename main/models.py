from django.contrib.auth.models import User
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings


class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

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
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )

    def save(self, *args, **kwargs):
        self.first_name = self.first_name.capitalize().strip()
        self.last_name = self.last_name.capitalize().strip()
        super().save(*args, **kwargs)


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
