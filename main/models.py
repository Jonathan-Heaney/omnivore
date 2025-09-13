from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.urls import reverse
from django.db.models import Q, UniqueConstraint
from urllib.parse import urlencode
import uuid
from django.utils import timezone
from datetime import timedelta
from django.db.models.functions import Lower
from main.utils.username import _clean_base, generate_unique_username


class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    # Make username optional at the model level; we’ll fill it in automatically.
    username = models.CharField(max_length=150, unique=True, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    email_on_art_shared = models.BooleanField(default=True)
    email_on_comment = models.BooleanField(default=True)
    email_on_like = models.BooleanField(default=False)

    # User can pause actually receiving new art (in-app + email)
    receive_art_paused = models.BooleanField(default=False)

    # So you don't have to query SentArtPiece each time
    last_art_sent_at = models.DateTimeField(null=True, blank=True)

    # Store IANA tz name, e.g. "America/New_York"
    timezone = models.CharField(
        max_length=64, null=True, blank=True)

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
        # Normalize
        if self.email:
            self.email = self.email.strip().lower()
        if self.first_name:
            self.first_name = self.first_name.strip()
        if self.last_name:
            self.last_name = self.last_name.strip()

        # Auto-assign a unique handle if missing
        if not self.username:
            self.username = generate_unique_username(
                self.first_name or '',
                self.last_name or '',
                self.email or '',
                Model=type(self),
            )

        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            # Enforce case-insensitive uniqueness at DB level (Postgres)
            models.UniqueConstraint(
                Lower('email'),
                name='uniq_user_email_lower'
            ),
            models.UniqueConstraint(
                Lower('username'), name='uniq_username_lower'),
        ]

    def __str__(self):
        full = f'{self.first_name} {self.last_name}'.strip()
        return full or self.email


class NotDeletedManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class ArtPiece(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE)
    artist_name = models.CharField(max_length=200)
    piece_name = models.CharField(max_length=300)
    piece_description = models.TextField()
    link = models.URLField(blank=True, null=True)
    approved_status = models.BooleanField(default=True)
    welcome_eligible = models.BooleanField(default=False)
    welcome_weight = models.PositiveSmallIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    public_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
    )

    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='deleted_artpieces'
    )
    delete_reason = models.CharField(max_length=200, blank=True)

    objects = models.Manager()        # all rows
    active = NotDeletedManager()      # only not-deleted

    def soft_delete(self, *, user=None, reason=''):
        if self.is_deleted:
            return
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.delete_reason = reason[:200]
        self.approved_status = False
        self.save(update_fields=['is_deleted',
                  'deleted_at', 'deleted_by', 'delete_reason'])

    # optional: undelete for admin
    def restore(self):
        if not self.is_deleted:
            return
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.delete_reason = ''
        self.save(update_fields=['is_deleted',
                  'deleted_at', 'deleted_by', 'delete_reason'])

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse("edit_art_piece", args=[self.public_id])

    def __str__(self):
        return self.piece_name


class SentArtPiece(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE)
    art_piece = models.ForeignKey(ArtPiece, on_delete=models.CASCADE)
    sent_time = models.DateTimeField(auto_now_add=True)
    seen_at = models.DateTimeField(null=True, blank=True, db_index=True)

    SOURCE_CHOICES = [
        ("weekly", "Weekly"),
        ("welcome", "Welcome"),
        ("reciprocal", "Reciprocal"),
        ("manual", "Manual"),
    ]

    source = models.CharField(
        max_length=20, choices=SOURCE_CHOICES, default="weekly")

    @property
    def is_new(self) -> bool:
        if self.seen_at is not None:
            return False
        window = getattr(settings, "NEW_BADGE_WINDOW_DAYS", 30)
        return self.sent_time >= timezone.now() - timedelta(days=window)

    class Meta:
        unique_together = ('user', 'art_piece')

    def __str__(self):
        return f'{self.user} - {self.art_piece}'

    def art_piece_submitter(self):
        return self.art_piece.user

    art_piece_submitter.short_description = 'Submitted By'


class ReciprocalGrant(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE)
    trigger_art_piece = models.OneToOneField(
        "ArtPiece", on_delete=models.CASCADE, related_name="reciprocal_grant"
    )
    sent_art_piece = models.ForeignKey(
        "ArtPiece",
        on_delete=models.SET_NULL,   # so we can null it if the piece disappears
        null=True,                   # <-- make nullable
        blank=True,                  # <-- allow blank in forms/admin
        related_name="reciprocal_granted_to",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["user", "created_at"])]


class WelcomeGrant(models.Model):
    """
    Records the single welcome gift given to a user.
    Ensures we only grant once per user (idempotent by schema).
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="welcome_grant")
    sent_art_piece = models.ForeignKey(
        "ArtPiece",
        on_delete=models.SET_NULL,   # piece might be removed later
        null=True,
        blank=True,
        related_name="welcome_granted_to",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["created_at"])]


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

    class Meta:
        constraints = [
            # one top-level thread per (art_piece, sender, recipient)
            models.UniqueConstraint(
                fields=['art_piece', 'sender', 'recipient'],
                condition=Q(parent_comment__isnull=True),
                name='uniq_comment_top_thread_piece_sender_recipient',
            ),
        ]
        indexes = [
            models.Index(
                fields=['art_piece', 'sender', 'recipient'],
                name='idx_comment_piece_sender_recip',
            ),
            models.Index(
                fields=['art_piece', 'created_at'],
                name='idx_comment_piece_created',
            ),
            models.Index(
                fields=['parent_comment'],
                name='idx_comment_parent',
            ),
        ]

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

    from django.urls import reverse

    def get_redirect_url(self):
        if not self.art_piece_id:
            return reverse("notifications")

        url = reverse("art_detail", args=[self.art_piece.public_id])

        params = {"n": self.id}

        # Where should the detail page land/focus?
        if self.notification_type == "comment":
            # owner will have many threads; sender is the "other" to open
            # recipient has only one thread — still fine to say "thread"
            params.update({"focus": "thread", "other": self.sender_id})
        elif self.notification_type in ("like", "shared_art"):
            params.update({"focus": "piece"})  # don't open/focus any thread

        return f"{url}?{urlencode(params)}"

    def __str__(self):
        return f'{self.sender} -> {self.recipient} ({self.notification_type})'


class Feedback(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    page = models.URLField(max_length=1024, blank=True)
    user_agent = models.TextField(blank=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["created_at"])]
