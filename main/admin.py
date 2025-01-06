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

    def short_text(self, obj):
        return obj.text[:50] + ('...' if len(obj.text) > 50 else '')
    short_text.short_description = 'Текст'

admin.site.register(Note, NoteAdmin)

class NoteInline(GenericTabularInline):
    """
    Встроенная форма для добавления записок к любому объекту.
    """
    model = Note
    extra = 1
    readonly_fields = ('created_at',)
    show_change_link = True