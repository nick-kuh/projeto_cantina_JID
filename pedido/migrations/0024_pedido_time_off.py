# Generated by Django 5.1.6 on 2025-05-10 03:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pedido', '0023_pedidocancelado'),
    ]

    operations = [
        migrations.AddField(
            model_name='pedido',
            name='time_off',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
