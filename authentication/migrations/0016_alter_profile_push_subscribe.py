# Generated by Django 5.1.2 on 2025-01-02 17:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0015_rename_push_profile_push_subscribe'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='push_subscribe',
            field=models.BooleanField(default=True),
        ),
    ]
