# Generated by Django 5.1.2 on 2024-11-22 16:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('salons', '0012_barber_categories'),
    ]

    operations = [
        migrations.AddField(
            model_name='appointment',
            name='barbers',
            field=models.ManyToManyField(related_name='appointments', through='salons.AppointmentBarberService', to='salons.barber'),
        ),
    ]