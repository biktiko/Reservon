# Generated by Django 5.1.2 on 2024-11-07 17:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('salons', '0009_remove_appointment_salons_appo_salon_i_86cbcc_idx_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='appointment',
            name='start_datetime',
            field=models.DateTimeField(),
        ),
    ]