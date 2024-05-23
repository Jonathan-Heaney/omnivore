from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField(unique=True)
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.first_name} {self.last_name}'


class ArtPiece(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    artist_name = models.CharField(max_length=200)
    piece_name = models.CharField(max_length=300)
    piece_description = models.TextField()
    link = models.URLField(blank=True, null=True)
    approved_status = models.BooleanField(default=True)

    def __str__(self):
        return self.piece_name


class SentArtPiece(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    art_piece = models.ForeignKey(ArtPiece, on_delete=models.CASCADE)
    sent_date = models.DateField()

    class Meta:
        unique_together = ('user', 'art_piece')

    def __str__(self):
        return f'{self.user} - {self.art_piece}'
