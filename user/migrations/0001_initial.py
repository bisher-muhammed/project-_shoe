# Generated by Django 4.2.5 on 2024-01-24 09:16

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('adminapp', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AddressUS',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('first_name', models.CharField(blank=True, max_length=400, null=True)),
                ('last_name', models.CharField(blank=True, max_length=400, null=True)),
                ('address_1', models.CharField(max_length=255)),
                ('city', models.CharField(max_length=200)),
                ('state', models.CharField(max_length=255)),
                ('zipcode', models.IntegerField()),
                ('is_default', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(blank=True, default='user-icon-big.png', null=True, upload_to='media/user')),
                ('status', models.CharField(default='New', max_length=10)),
                ('last_wallet_update_timestamp', models.DateTimeField(blank=True, null=True)),
                ('address', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='user.addressus')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to=settings.AUTH_USER_MODEL)),
                ('wishlist', models.ManyToManyField(related_name='wishlist_items', to='adminapp.product')),
            ],
        ),
        migrations.CreateModel(
            name='Wishlist',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('products', models.ManyToManyField(related_name='wishlists', to='adminapp.product')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Wallet',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('balance', models.DecimalField(decimal_places=2, default=0.0, max_digits=10)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('user_profile', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='user.userprofile')),
            ],
        ),
        migrations.AddField(
            model_name='addressus',
            name='user_profile',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='addresses', to='user.userprofile'),
        ),
    ]
