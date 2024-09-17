    # signals.py
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Folder

@receiver(post_save, sender=User)
def create_trash_folder(sender, instance, created, **kwargs):
    if created:
        Folder.objects.create(name='Papelera', user=instance, is_fixed=True)
