from django.db import models

# Create your models here.
class salons(models.Model):
    salon_name = models.CharField('Salon name', max_length=15)
    logo = models.CharField('Logo', max_length=50)
    address = models.CharField('Address', max_length=20)
    description = models.TextField('Description')

    def __str__(self):
        return self.salon_name
    
    class Meta:
        verbose_name='Salon'
        verbose_name_plural='Salons'