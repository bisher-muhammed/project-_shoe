# Generated by Django 4.2.5 on 2024-01-30 04:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('adminapp', '0007_offer_is_expired'),
    ]

    operations = [
        migrations.AddField(
            model_name='productoffer',
            name='is_expired',
            field=models.BooleanField(default=False),
        ),
    ]