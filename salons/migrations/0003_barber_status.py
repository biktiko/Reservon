# Generated by Django 5.1.2 on 2025-01-25 13:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('salons', '0002_barber_default_duration_alter_barberservice_duration'),
    ]

    operations = [
        migrations.AddField(
            model_name='barber',
            name='status',
            field=models.CharField(choices=[('active', 'Active'), ('suspend', 'Suspend')], default='active', max_length=10, verbose_name='Status'),
        ),
    ]
