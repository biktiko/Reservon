# Generated by Django 5.1.2 on 2025-01-25 13:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0020_alter_profile_login_method'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='login_method',
            field=models.CharField(choices=[('password', 'Password'), ('google', 'Google'), ('sms', 'SMS')], default='sms', max_length=20),
        ),
    ]
