# Generated by Django 5.1.2 on 2025-01-06 14:14

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0011_poll_historicalpoll_historicaluser_note_notephoto_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='historicalchoice',
            name='history_user',
        ),
        migrations.RemoveField(
            model_name='historicalchoice',
            name='poll',
        ),
        migrations.RemoveField(
            model_name='historicalpoll',
            name='history_user',
        ),
        migrations.DeleteModel(
            name='Choice',
        ),
        migrations.DeleteModel(
            name='HistoricalChoice',
        ),
        migrations.DeleteModel(
            name='Poll',
        ),
        migrations.DeleteModel(
            name='HistoricalPoll',
        ),
    ]
