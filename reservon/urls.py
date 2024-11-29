# C:\Reservon\Reservon\reservon\urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('grappelli/', include('grappelli.urls')),
    path('admin/', admin.site.urls),
    path('', include('main.urls')),
    path('auth/', include(('authentication.urls', 'authentication'), namespace='authentication')),
    path('salons/', include(('salons.urls', 'salons'), namespace='salons')),
    path('account/', include('account.urls')),
    path('i18n/', include('django.conf.urls.i18n')), 



] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
