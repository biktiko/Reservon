# Generated by Django 5.1.2 on 2025-02-15 15:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('salons', '0010_salon_facebook'),
    ]

    operations = [
        migrations.AddField(
            model_name='salon',
            name='city',
            field=models.CharField(default='Yerevan', max_length=20, verbose_name='City'),
        ),
    ]
