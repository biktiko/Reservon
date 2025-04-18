# Generated by Django 5.1.2 on 2025-04-05 13:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('salons', '0013_alter_salon_address'),
    ]

    operations = [
        migrations.AddField(
            model_name='salon',
            name='additional_status',
            field=models.CharField(blank=True, choices=[('waiting_contact', 'Waiting for a contact'), ('they_think', 'They think'), ('mail', 'Mail'), ('ignored', 'Ignored'), ('inbound', 'Inbound'), ('former_partner', 'Former Partner'), ('expansion_needed', 'Expansion needed')], max_length=20, null=True, verbose_name='Additional Status'),
        ),
        migrations.AlterField(
            model_name='salon',
            name='status',
            field=models.CharField(choices=[('new', 'New'), ('active', 'Active'), ('in process', 'In process'), ('refused', 'Refused'), ('suspend', 'Suspend')], default='new', max_length=10, verbose_name='Status'),
        ),
        migrations.AlterField(
            model_name='salon',
            name='telegram_status',
            field=models.CharField(choices=[('new', 'New'), ('active', 'Active'), ('in process', 'In process'), ('refused', 'Refused'), ('suspend', 'Suspend')], default='active', max_length=10),
        ),
    ]
