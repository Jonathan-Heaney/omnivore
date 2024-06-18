from django.contrib.auth.models import User
from django.contrib.auth.models import AbstractUser
from django.db import models


# class CustomUser(AbstractUser):
#     email = models.EmailField(unique=True)

#     USERNAME_FIELD = 'email'
#     REQUIRED_FIELDS = ['first_name', 'last_name']

#     def save(self, *args, **kwargs):
#         self.first_name = self.first_name.capitalize()
#         self.last_name = self.last_name.capitalize()
#         if not self.username:
#             base_username = f"{self.first_name}{self.last_name}".lower()
#             username = base_username
#             counter = 1
#             while CustomUser.objects.filter(username=username).exists():
#                 username = f"{base_username}{counter}"
#                 counter += 1
#             self.username = username
#         super().save(*args, **kwargs)


class ArtPiece(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
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
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    art_piece = models.ForeignKey(ArtPiece, on_delete=models.CASCADE)
    sent_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'art_piece')

    def __str__(self):
        return f'{self.user} - {self.art_piece}'
