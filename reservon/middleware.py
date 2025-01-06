# reservon/middleware.py
from django.contrib.sites.models import Site
from django.utils.deprecation import MiddlewareMixin
import logging
import uuid
class DynamicSiteMiddleware(MiddlewareMixin):
    def process_request(self, request):
        host = request.get_host().split(':')[0]
        try:
            site = Site.objects.get(domain=host)
            request.site = site
            request.site_id = site.id
        except Site.DoesNotExist:
            # Если сайт не найден, используем сайт по умолчанию с id=2
            site = Site.objects.get(id=1)
            request.site = site
            request.site_id = site.id

class RequestIDMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.id = uuid.uuid4()
        logging.LoggerAdapter(logging.getLogger('reservon'), {'request_id': request.id})

    def process_response(self, request, response):
        response['X-Request-ID'] = request.id
        return response
