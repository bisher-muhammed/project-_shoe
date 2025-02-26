# Generated by Django 4.2.5 on 2024-01-29 08:51

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('adminapp', '0005_remove_size_quantity'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProductSize',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField(default=0)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='productsizes', to='adminapp.product')),
                ('size', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='adminapp.size')),
            ],
        ),
    ]
