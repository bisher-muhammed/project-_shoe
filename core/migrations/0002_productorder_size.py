# Generated by Django 4.2.5 on 2024-01-28 05:48

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('adminapp', '0004_size_quantity'),
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='productorder',
            name='size',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='adminapp.size'),
            preserve_default=False,
        ),
    ]
