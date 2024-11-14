# C:\Reservon\Reservon\reservon\urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('main.urls')),
    path('salons/', include('salons.urls')), 
    path('i18n/', include('django.conf.urls.i18n')), 
    path('auth/', include(('authentication.urls', 'authentication'), namespace='authentication')),


] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
