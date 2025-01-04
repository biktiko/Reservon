# main/context_processors.py

def is_admin_processor(request):
    if request.user.is_authenticated:
        is_admin = request.user.administered_salons.exists()
    else:
        is_admin = False
    return {'is_admin': is_admin}
