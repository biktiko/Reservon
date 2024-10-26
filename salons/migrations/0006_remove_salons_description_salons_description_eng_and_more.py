# Generated by Django 5.1.2 on 2024-10-26 17:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('salons', '0005_salons_images_alter_salons_description'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='salons',
            name='description',
        ),
        migrations.AddField(
            model_name='salons',
            name='description_eng',
            field=models.TextField(blank=True, verbose_name='description'),
        ),
        migrations.AddField(
            model_name='salons',
            name='description_hy',
            field=models.TextField(blank=True, verbose_name='description'),
        ),
        migrations.AddField(
            model_name='salons',
            name='description_ru',
            field=models.TextField(blank=True, verbose_name='description'),
        ),
        migrations.AddField(
            model_name='salons',
            name='shortDescription_eng',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='Short description'),
        ),
        migrations.AddField(
            model_name='salons',
            name='shortDescription_hy',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='Short description'),
        ),
        migrations.AddField(
            model_name='salons',
            name='shortDescription_ru',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='Short description'),
        ),
        migrations.AlterField(
            model_name='salons',
            name='images',
            field=models.ImageField(blank=True, null=True, upload_to='salon_images/', verbose_name='Images'),
        ),
    ]
