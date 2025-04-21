from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.conf import settings
from django.contrib.auth import get_user_model
import os

@receiver(post_migrate)
def criar_superuser_automatico(sender, **kwargs):
    Usuario = get_user_model()
    email = os.getenv('EMAIL_ADMIN')
    senha = os.getenv('SENHA_ADMIN')

    if email and senha:
        if not Usuario.objects.filter(email=email).exists():
            Usuario.objects.create_superuser(
                username='admin',
                email=email,
                password=senha
            )
