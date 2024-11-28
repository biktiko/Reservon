# Generated by Django 5.1.2 on 2024-11-08 19:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0007_alter_profile_phone_number_alter_profile_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='status',
            field=models.CharField(choices=[('unverified', 'Unverified'), ('verified', 'Verified'), ('suspended', 'Suspended')], default='unverified', max_length=10),
        ),
        migrations.AlterField(
            model_name='verificationcode',
            name='code',
            field=models.CharField(max_length=4),
        ),
    ]