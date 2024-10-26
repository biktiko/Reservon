# salons/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from .models import salons, Appointment

def main(request):
    # salons_list = salons.objects.all()  # Получаем все объекты из таблицы salons    active_salons = Salons.objects.filter(status='active')
    active_salons = salons.objects.filter(status='active')
    return render(request, 'salons/salons.html', {"salons": active_salons})

def salon_detail(request, id):
    salon = get_object_or_404(salons, id=id)
    services = salon.services_hy.split(',') if salon.services_hy else []  # Разбиваем строку на список
    return render(request, 'salons/salon_detail.html', {'salon': salon, 'services': services})

def salon_services(request, salon_id):
    salon = get_object_or_404(salons, id=salon_id)
    return render(request, 'salons/salon_services.html', {'salon': salon})

def book_appointment(request, id):
    if request.method == "POST":
        date = request.POST.get("date")
        time = request.POST.get("time")
        salon = get_object_or_404(salons, id=id)

        # Создаем новую запись о бронировании
        Appointment.objects.create(salon=salon, date=date, time=time, user=request.user)
        
        return redirect(reverse('salon_detail', args=[id]))