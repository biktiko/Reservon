# Generated by Django 5.1.2 on 2024-10-16 18:39

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='salons',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('salon_name', models.CharField(max_length=15, verbose_name='Salon name')),
                ('logo', models.CharField(max_length=50, verbose_name='Logo')),
                ('address', models.CharField(max_length=20, verbose_name='Address')),
                ('description', models.TextField(verbose_name='Description')),
            ],
            options={
                'verbose_name': 'Salon',
                'verbose_name_plural': 'Salons',
            },
        ),
    ]
