# Generated by Django 5.1.1 on 2024-10-18 18:43

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0004_alter_salons_salon_name'),
    ]

    operations = [
        migrations.DeleteModel(
            name='salons',
        ),
    ]
