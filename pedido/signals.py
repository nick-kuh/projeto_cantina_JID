from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.conf import settings
import os
from .models import Usuario

@receiver(post_migrate)
def criar_superuser_automaticamente(sender, **kwargs):
    email = os.getenv('EMAIL_ADMIN')
    senha = os.getenv('SENHA_ADMIN')

    if email and senha and not Usuario.objects.filter(email=email).exists():
        Usuario.objects.create_superuser(
            username='nick_jid',
            email=email,
            password=senha,
            is_staff=True,
            is_active=True,
        )
        print("Superusuário criado automaticamente.")
