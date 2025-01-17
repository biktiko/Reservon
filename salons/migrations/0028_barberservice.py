# Generated by Django 5.1.2 on 2025-01-12 15:41

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('salons', '0027_alter_barber_services'),
    ]

    operations = [
        migrations.CreateModel(
            name='BarberService',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('barber', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='barber_services', to='salons.barber')),
                ('service', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='barber_services', to='salons.service')),
            ],
        ),
    ]
