# C:\Reservon\Reservon\reservon\urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from .views import ServiceWorkerView

urlpatterns = [
    path('grappelli/', include('grappelli.urls')),
    path('admin/', admin.site.urls),
    path('', include(('main.urls', 'main'), namespace='main')),
    path('auth/', include(('authentication.urls', 'authentication'), namespace='authentication')),
    path('salons/', include(('salons.urls', 'salons'), namespace='salons')),
    path('user-account/', include('user_account.urls')),
    path('i18n/', include('django.conf.urls.i18n')), 
    path('accounts/', include('allauth.urls')),
    path('__debug__/', include('debug_toolbar.urls')),
    path('service-worker.js', ServiceWorkerView.as_view(), name='service_worker'),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
