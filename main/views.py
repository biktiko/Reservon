from django.shortcuts import render, redirect
from salons.models import salons

# def main(request):
#     salons_list = salons.objects.all()  # Получаем все объекты из таблицы salons
#     return render(request, 'main/home.html', {'salons': salons_list})

def main(request):
    return redirect('salons_main')

def about(request):
    return render(request, 'main/about.html')

def contacts(request):
    return render(request, 'main/contacts.html')