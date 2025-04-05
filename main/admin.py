# salon/admin.py

from django.contrib import admin
from authentication.models import PushSubscription
from django.contrib.contenttypes.admin import GenericTabularInline
from .models import Note, NotePhoto
@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'endpoint', 'created_at')
    search_fields = ('user__username', 'endpoint')

class NotePhotoInline(admin.TabularInline):
    model = NotePhoto
    extra = 1
    readonly_fields = ('image',)
class NoteAdmin(admin.ModelAdmin):
    list_display = ('content_object', 'created_at', 'short_text')
    list_filter = ('content_type', 'created_at')
    search_fields = ('text',)
    inlines = [NotePhotoInline]

    # Скрываем автора, чтобы в админке пользователь его не выбирал
    exclude = ('author',)

    # Подставляем request.user, если поле автор не заполнено
    def save_model(self, request, obj, form, change):
        if not obj.author_id:  # Если нет автора
            obj.author = request.user
        super().save_model(request, obj, form, change)

    def short_text(self, obj):
        return obj.text[:50] + ('...' if len(obj.text) > 50 else '')
    short_text.short_description = 'Текст'

class NoteInline(GenericTabularInline):
    model = Note
    # Выводим нужные поля в колонках:
    fields = ('text', 'created_at', 'author_display')
    # Указываем, что они только для чтения (чтобы не редактировать дату и автора):
    readonly_fields = ('created_at', 'author_display')
    show_change_link = True

    # Исключаем 'author', чтобы пользователь не заполнял вручную
    exclude = ('author',)

    def author_display(self, obj):
        """
        Отображение никнейма пользователя, если есть.
        Если у пользователя нет профиля или никнейм пуст, показывать username.
        """
        if obj.author:
            profile = getattr(obj.author, 'main_profile', None)
            if profile and profile.nickname:
            # fallback — если нет nickname, показываем username
                return profile.nickname
            if obj.author.first_name:
                return obj.author.get_full_name()
            return obj.author.username
        return '—'

    def save_formset(self, request, form, formset, change):
        """Проставляем автора при сохранении, если не установлен."""
        instances = formset.save(commit=False)
        for instance in instances:
            if not instance.author_id:
                instance.author = request.user
            instance.save()
        formset.save_m2m()

