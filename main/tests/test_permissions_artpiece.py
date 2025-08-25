import pytest
from django.urls import reverse
from main.forms import ArtPieceForm


@pytest.mark.django_db
def test_owner_can_get_edit_form(client, user_a, art_by_a):
    client.force_login(user_a)
    url = reverse("edit_art_piece", args=[art_by_a.public_id])
    resp = client.get(url)
    assert resp.status_code == 200
    assert b"edit" in resp.content.lower()  # weak smoke check


@pytest.mark.django_db
def test_non_owner_gets_404_on_edit(client, user_a, art_by_b):
    client.force_login(user_a)
    url = reverse("edit_art_piece", args=[art_by_b.public_id])
    resp = client.get(url)
    assert resp.status_code == 404


@pytest.mark.django_db
def test_owner_can_post_edit_and_changes_persist(client, user_a, art_by_a):
    client.force_login(user_a)
    url = reverse("edit_art_piece", args=[art_by_a.public_id])

    # Build a valid payload straight from the form’s expected fields
    form = ArtPieceForm(instance=art_by_a)
    data = form.initial.copy()

    # If your form has a URLField that might be blank in fixtures but required=True,
    # ensure it’s present and valid:
    if "link" in data and not data.get("link"):
        data["link"] = "https://example.com"

    # Now override what we actually want to change
    data.update({
        "piece_name": "New Title",
        "artist_name": "New Artist",
        "piece_description": "Updated desc",
        "approved_status": True,
    })

    resp = client.post(url, data)
    assert resp.status_code in (302, 303)  # should redirect to my_shared_art

    art_by_a.refresh_from_db()
    assert art_by_a.piece_name == "New Title"
    assert art_by_a.piece_description == "Updated desc"


@pytest.mark.django_db
def test_non_owner_post_edit_is_404(client, user_a, art_by_b):
    client.force_login(user_a)
    url = reverse("edit_art_piece", args=[art_by_b.public_id])
    data = {"piece_name": "Hacker change",
            "piece_description": "Oops", "approved_status": True}
    resp = client.post(url, data)
    assert resp.status_code == 404


@pytest.mark.django_db
def test_owner_can_delete_via_post(client, user_a, art_by_a):
    client.force_login(user_a)
    url = reverse("delete_art_piece", args=[art_by_a.public_id])
    resp = client.post(url)
    assert resp.status_code in (302, 303)
    # object should be gone
    from main.models import ArtPiece
    assert not ArtPiece.objects.filter(pk=art_by_a.public_id).exists()


@pytest.mark.django_db
def test_non_owner_delete_is_404(client, user_a, art_by_b):
    client.force_login(user_a)
    url = reverse("delete_art_piece", args=[art_by_b.public_id])
    resp = client.post(url)
    assert resp.status_code == 404


@pytest.mark.django_db
def test_delete_requires_post(client, user_a, art_by_a):
    client.force_login(user_a)
    url = reverse("delete_art_piece", args=[art_by_a.public_id])
    resp = client.get(url)
    # @require_POST should emit 405 Method Not Allowed
    assert resp.status_code == 405


@pytest.mark.django_db
def test_edit_and_delete_use_uuid_urls(client, user_a, art_by_a):
    client.force_login(user_a)
    url = reverse("edit_art_piece", args=[art_by_a.public_id])
    resp = client.get(url)
    assert resp.status_code == 200

    del_url = reverse("delete_art_piece", args=[art_by_a.public_id])
    resp = client.post(del_url)
    assert resp.status_code in (302, 303)
