import pytest
from django.urls import reverse
from django.utils import timezone
from main.models import Comment, Notification, SentArtPiece
import re


@pytest.mark.django_db
class TestComments:
    def test_recipient_can_start_thread(self, client, user_a, user_b, art_by_a):
        """Recipients can start a new conversation with the owner."""
        SentArtPiece.objects.create(user=user_b, art_piece=art_by_a)

        # Login with EMAIL, since USERNAME_FIELD = 'email'
        assert client.login(username="b@example.com", password="pass")

        url = reverse("comments_create")
        resp = client.post(url, {"art_piece_id": art_by_a.id, "text": "Hello"})
        assert resp.status_code == 200

        c = Comment.objects.get()
        assert c.sender == user_b
        assert c.recipient == user_a
        assert c.parent_comment is None  # top-level

    def test_owner_cannot_start_thread(self, client, user_a, user_b, art_by_a):
        """Owner cannot start a top-level conversation with a recipient."""
        SentArtPiece.objects.create(user=user_b, art_piece=art_by_a)

        assert client.login(username="a@example.com", password="pass")
        url = reverse("comments_create")
        resp = client.post(url, {"art_piece_id": art_by_a.id, "text": "Hey"})
        assert resp.status_code == 403
        assert Comment.objects.count() == 0

    def test_owner_can_reply(self, client, user_a, user_b, art_by_a):
        """Owner can reply in an existing thread."""
        SentArtPiece.objects.create(user=user_b, art_piece=art_by_a)
        top = Comment.objects.create(
            art_piece=art_by_a, sender=user_b, recipient=user_a, text="Hi"
        )

        assert client.login(username="a@example.com", password="pass")
        url = reverse("comments_create")
        resp = client.post(
            url,
            {
                "art_piece_id": art_by_a.id,
                "text": "Replying",
                "top_level_comment_id": top.id,
            },
        )
        assert resp.status_code == 200
        assert Comment.objects.count() == 2
        reply = Comment.objects.exclude(id=top.id).get()
        assert reply.parent_comment == top
        assert reply.recipient == user_b

    def test_non_participant_cannot_comment(self, client, user_a, user_b, art_by_a, user_c):
        """A random user cannot comment on a piece they didn't receive or own."""
        assert client.login(username="c@example.com", password="pass")
        url = reverse("comments_create")
        resp = client.post(url, {"art_piece_id": art_by_a.id, "text": "Nope"})
        assert resp.status_code == 403
        assert Comment.objects.count() == 0

    def test_thread_coalescing(self, client, user_a, user_b, art_by_a):
        """Multiple starts by recipient fold into the same top-level thread."""
        SentArtPiece.objects.create(user=user_b, art_piece=art_by_a)

        assert client.login(username="b@example.com", password="pass")
        url = reverse("comments_create")

        r1 = client.post(url, {"art_piece_id": art_by_a.id, "text": "First"})
        assert r1.status_code == 200

        r2 = client.post(url, {"art_piece_id": art_by_a.id, "text": "Second"})
        assert r2.status_code == 200

        assert Comment.objects.count() == 2
        top = Comment.objects.get(text="First")
        second = Comment.objects.get(text="Second")
        assert second.parent_comment == top

    def test_unique_top_level_enforced(self, client, user_a, user_b, art_by_a):
        """DB constraint prevents duplicate top-level threads for same pair."""
        SentArtPiece.objects.create(user=user_b, art_piece=art_by_a)

        # manually create a top-level
        Comment.objects.create(
            art_piece=art_by_a, sender=user_b, recipient=user_a, text="Hi"
        )

        assert client.login(username="b@example.com", password="pass")
        url = reverse("comments_create")
        resp = client.post(url, {"art_piece_id": art_by_a.id, "text": "Again"})
        assert resp.status_code == 200
        assert Comment.objects.count() == 2  # no duplicate thread

    def test_missing_fields_error(self, client, user_a, user_b, art_by_a):
        SentArtPiece.objects.create(user=user_b, art_piece=art_by_a)
        assert client.login(username="b@example.com", password="pass")
        url = reverse("comments_create")
        resp = client.post(url, {"art_piece_id": art_by_a.id})  # no text
        assert resp.status_code == 400

    def test_notification_created_on_comment(self, client, user_a, user_b, art_by_a):
        """Posting a comment creates a notification for recipient."""
        SentArtPiece.objects.create(user=user_b, art_piece=art_by_a)
        assert client.login(username="b@example.com", password="pass")
        url = reverse("comments_create")
        client.post(url, {"art_piece_id": art_by_a.id, "text": "Hi"})
        n = Notification.objects.get(
            notification_type="comment",
            recipient=user_a,
            sender=user_b,
            art_piece=art_by_a,
        )
        assert n.recipient == user_a
        assert "message" in n.message.lower()

    def test_no_self_notification(self, client, user_a, art_by_a):
        """No notification if sender == recipient (guard in signal)."""
        SentArtPiece.objects.create(
            user=user_a, art_piece=art_by_a)  # odd case
        assert client.login(username="a@example.com", password="pass")
        url = reverse("comments_create")
        client.post(url, {"art_piece_id": art_by_a.id, "text": "Hello"})
        assert Notification.objects.count() == 0

    def test_owner_conversations_sorted_by_latest(self, client, user_a, user_b, art_by_a, user_c):
        """Owner sees conversations sorted by latest activity DESC."""
        SentArtPiece.objects.create(user=user_b, art_piece=art_by_a)
        SentArtPiece.objects.create(user=user_c, art_piece=art_by_a)

        # Two top-level starters (B and C)
        c_b = Comment.objects.create(
            art_piece=art_by_a, sender=user_b, recipient=user_a, text="From B"
        )
        c_c = Comment.objects.create(
            art_piece=art_by_a, sender=user_c, recipient=user_a, text="From C"
        )

        # Make C's thread newest by bumping its created_at
        c_c.created_at = timezone.now() + timezone.timedelta(minutes=5)
        c_c.save(update_fields=["created_at"])

        assert client.login(username="a@example.com", password="pass")
        url = reverse("art_detail", args=[art_by_a.public_id])
        resp = client.get(url)
        assert resp.status_code == 200

        html = resp.content.decode()
        # Grab the displayed names in conversation headers, in order of appearance
        names = re.findall(
            r'Conversation with\s*<strong>\s*([^<]+?)\s*</strong>',
            html
        )

        # We expect C’s thread (newest) before B’s thread (older)
        assert names[0] == "C User"
        assert names[1] == "B User"
