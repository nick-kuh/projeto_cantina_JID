# Generated by Django 5.1.6 on 2025-07-06 17:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pedido', '0025_produto_categoria'),
    ]

    operations = [
        migrations.AlterField(
            model_name='produto',
            name='categoria',
            field=models.CharField(choices=[('Salgados', 'Salgados'), ('Doces', 'Doces'), ('Bebidas', 'Bebidas'), ('Caldos', 'Caldos'), ('Combos', 'Combos')], default='Outros', max_length=20),
        ),
    ]
