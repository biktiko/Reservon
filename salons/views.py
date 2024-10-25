# salons/views.py
from django.shortcuts import render
from .models import salons

def main(request):
    salons_list = salons.objects.all()  # Получаем все объекты из таблицы salons
    return render(request, 'salons/salons.html', {"salons": salons_list})