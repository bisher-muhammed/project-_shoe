# Generated by Django 4.2.5 on 2024-01-27 15:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('adminapp', '0003_remove_banner_days_difference_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='size',
            name='quantity',
            field=models.IntegerField(default=0),
        ),
    ]