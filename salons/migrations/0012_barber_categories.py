# Generated by Django 5.1.2 on 2024-11-16 13:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('salons', '0011_appointmentbarberservice_alter_appointment_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='barber',
            name='categories',
            field=models.ManyToManyField(related_name='barbers', to='salons.servicecategory'),
        ),
    ]