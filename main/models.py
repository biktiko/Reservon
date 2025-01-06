# main/models.py

from django.db import models
from simple_history.models import HistoricalRecords
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.auth.models import User

class Note(models.Model):
    """
    Модель для хранения записок, привязанных к различным объектам (Profile, Salon, Barber).
    """
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='notes')

    text = models.TextField('Текст записки')
    created_at = models.DateTimeField('Время создания', auto_now_add=True)

    def __str__(self):
        return f"Записка для {self.content_object} от {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        verbose_name = 'Записка'
        verbose_name_plural = 'Записки'
        ordering = ['-created_at']

class NotePhoto(models.Model):
    """
    Модель для хранения фотографий, прикрепленных к запискам.
    """
    note = models.ForeignKey(Note, on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField('Фото', upload_to='notes/photos/')

    def __str__(self):
        return f"Фото для {self.note}"

    class Meta:
        verbose_name = 'Фото записки'
        verbose_name_plural = 'Фотографии записок'

class VerificationCode(models.Model):
    phone_number = models.CharField(max_length=20)
    code = models.CharField(max_length=4)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        from django.utils import timezone
        expiration_time = self.created_at + timezone.timedelta(minutes=10)  # Код действует 10 минут
        return timezone.now() > expiration_time

    def __str__(self):
        return f"{self.phone_number} - {self.code}"
