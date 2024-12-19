from django.views.generic import TemplateView

class ServiceWorkerView(TemplateView):
    template_name = "service-worker.js"
    content_type = "application/javascript"