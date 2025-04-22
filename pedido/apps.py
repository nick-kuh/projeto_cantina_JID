from django.apps import AppConfig


class PedidoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'pedido'

    # def ready(self):
    #     # from .models import Usuario
    #     # import os

    #     # email = os.getenv('EMAIL_ADMIN')
    #     # senha = os.getenv('SENHA_ADMIN')

    #     # usuarios = Usuario.objects.filter(email=email)
    #     # if not usuarios:
    #     #     Usuario.objects.create_superuser(
    #     #         username='nick_jid',
    #     #         email=email,
    #     #         password=senha,
    #     #         is_staff=True,
    #     #         is_active=True,
    #     #     )
    #     import pedido.signals  # só isso aqui, sem lógica de criação
