# Generated by Django 5.1.2 on 2024-12-24 17:10

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0010_alter_pushsubscription_endpoint'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='pushsubscription',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='push_subscriptions', to=settings.AUTH_USER_MODEL, unique=True),
        ),
    ]