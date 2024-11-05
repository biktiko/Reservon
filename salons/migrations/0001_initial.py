# Generated by Django 5.1.2 on 2024-11-01 17:55

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Salon',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, verbose_name='Salon name')),
                ('logo', models.ImageField(blank=True, null=True, upload_to='salon_logos/', verbose_name='Logo')),
                ('address', models.CharField(max_length=100, verbose_name='Address')),
                ('coordinates', models.CharField(blank=True, max_length=50, null=True, verbose_name='Coordinates')),
                ('opening_hours', models.JSONField(default=dict, help_text="JSON format: {'monday': {'open': '09:00', 'close': '18:00'}, ... }", verbose_name='Working Hours')),
                ('default_duration', models.IntegerField(default=20, verbose_name='Default duration (minutes)')),
                ('default_price', models.DecimalField(decimal_places=0, default=2000, max_digits=15, verbose_name='Default price')),
                ('services_hy', models.CharField(blank=True, max_length=100, null=True, verbose_name='Services_hy')),
                ('services_ru', models.CharField(blank=True, max_length=100, null=True, verbose_name='Services_ru')),
                ('services_eng', models.CharField(blank=True, max_length=100, null=True, verbose_name='Services_eng')),
                ('shortDescription_hy', models.CharField(blank=True, max_length=100, null=True, verbose_name='Short description_hy')),
                ('shortDescription_ru', models.CharField(blank=True, max_length=100, null=True, verbose_name='Short description_ru')),
                ('shortDescription_eng', models.CharField(blank=True, max_length=100, null=True, verbose_name='Short description_eng')),
                ('description_hy', models.TextField(blank=True, verbose_name='description_hy')),
                ('description_ru', models.TextField(blank=True, verbose_name='description_ru')),
                ('description_eng', models.TextField(blank=True, verbose_name='description_eng')),
                ('reservDays', models.IntegerField(default=9, verbose_name='Reserv days')),
                ('status', models.CharField(choices=[('new', 'New'), ('active', 'Active'), ('suspend', 'Suspend'), ('disable', 'Disable')], default='new', max_length=10, verbose_name='Status')),
            ],
            options={
                'verbose_name': 'Salon',
                'verbose_name_plural': 'Salons',
            },
        ),
        migrations.CreateModel(
            name='Barber',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('availability', models.JSONField(default=dict, verbose_name="Barber's Working Hours")),
                ('avatar', models.ImageField(blank=True, null=True, upload_to='barbers/avatars/')),
                ('description', models.TextField(blank=True, null=True)),
                ('salon', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='barbers', to='salons.salon')),
            ],
        ),
        migrations.CreateModel(
            name='Appointment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('time', models.TimeField()),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('salon', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='salons.salon')),
            ],
        ),
        migrations.CreateModel(
            name='SalonImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(upload_to='salon_images/')),
                ('upload_date', models.DateTimeField(auto_now_add=True)),
                ('salon', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='images', to='salons.salon')),
            ],
        ),
        migrations.CreateModel(
            name='ServiceCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('salon', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='service_categories', to='salons.salon')),
            ],
        ),
        migrations.CreateModel(
            name='Service',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('price', models.DecimalField(decimal_places=2, max_digits=8)),
                ('duration', models.DurationField()),
                ('salon', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='services', to='salons.salon')),
                ('category', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='services', to='salons.servicecategory')),
            ],
        ),
    ]
