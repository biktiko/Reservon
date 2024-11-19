from django.shortcuts import render, redirect
from django.db.models import Q
from salons.models import Salon

def main(request):
    return redirect('salons:salons_main')

def about(request):
    return render(request, 'main/about.html')

def contacts(request):
    return render(request, 'main/contacts.html')

def search_salons(request):
    return redirect('salons:salons_main')