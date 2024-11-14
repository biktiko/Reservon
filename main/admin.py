# main/admin.py

# from django.contrib import admin
# from .models import Profile

# class ProfileAdmin(admin.ModelAdmin):
#     list_display = ('user_first_name', 'phone_number', 'status')
#     list_filter = ('status',)
#     search_fields = ('user__username', 'phone_number')

#     def user_first_name(self, obj):
#         return obj.user.first_name
#     user_first_name.short_description = 'Username'

# admin.site.register(Profile, ProfileAdmin)