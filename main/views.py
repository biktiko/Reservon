# salons/views.py

from django.shortcuts import render, redirect

def main(request):
    return redirect('salons_main')

def about(request):
    return render(request, 'main/about.html')

def contacts(request):
    return render(request, 'main/contacts.html')
