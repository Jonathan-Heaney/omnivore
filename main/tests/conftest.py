import pytest
from django.contrib.auth import get_user_model
from main.models import ArtPiece


User = get_user_model()


@pytest.fixture(autouse=True)
def _plain_staticfiles_storage(settings):
    """
    Use non-manifest storage in tests so templates can {% static %} without collectstatic.
    Works for both Django 3.x/4.x styles.
    """
    # Django 4.2+ STORAGES setting
    if hasattr(settings, "STORAGES"):
        settings.STORAGES["staticfiles"]["BACKEND"] = (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
        )
    else:
        # Older Django fallback
        settings.STATICFILES_STORAGE = (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
        )


@pytest.fixture
def user_a(db):
    return User.objects.create_user(
        email="a@example.com", username="a", password="pass",
        first_name="A", last_name="User"
    )


@pytest.fixture
def user_b(db):
    return User.objects.create_user(
        email="b@example.com", username="b", password="pass",
        first_name="B", last_name="User"
    )


@pytest.fixture
def art_by_a(db, user_a):
    return ArtPiece.objects.create(
        user=user_a,
        artist_name='Joe',
        piece_name="Sunset",
        piece_description="Nice.",
        approved_status=True,
    )


@pytest.fixture
def art_by_b(db, user_b):
    return ArtPiece.objects.create(
        user=user_b,
        artist_name='Sam',
        piece_name="Forest",
        piece_description="Green.",
        approved_status=True,
    )
