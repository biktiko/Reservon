from django.db import models

class salons(models.Model):
    salon_name = models.CharField('Salon name', max_length=50)
    logo = models.ImageField('Logo', upload_to='salon_logos/', blank=True, null=True)
    images = models.ImageField('Images', upload_to='salon_images/', blank=True, null=True)
    address = models.CharField('Address', max_length=100)
    coordinates = models.CharField('Coordinates', max_length=50, blank=True, null=True)
    description = models.TextField('Description', blank=True)

    def __str__(self):
        return self.salon_name

    class Meta:
        verbose_name = 'Salon'
        verbose_name_plural = 'Salons'
