from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from .models import BlogPost
from .tasks import send_blog_post_email


@receiver(pre_save, sender=BlogPost)
def blogpost_flag_transition(sender, instance: BlogPost, **kwargs):
    """
    Compute whether we are transitioning to published and stash on instance.
    This runs before hitting the DB.
    """
    instance._was_published = None
    if instance.pk:
        try:
            prev = sender.objects.only("published").get(pk=instance.pk)
            instance._was_published = prev.published
        except sender.DoesNotExist:
            instance._was_published = None


@receiver(post_save, sender=BlogPost)
def blogpost_send_on_publish(sender, instance: BlogPost, created, **kwargs):
    """
    Send exactly once when a post becomes published.
    - If created with published=True → send
    - If updated from False → True → send
    """
    just_published = False
    if created and instance.published:
        just_published = True
    elif instance._was_published is False and instance.published is True:
        just_published = True

    if just_published:
        # enqueue async
        send_blog_post_email.delay(instance.id)
