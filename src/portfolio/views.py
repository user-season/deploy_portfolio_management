from django.shortcuts import render
from django.contrib.auth.decorators import login_required




def home(request):
    return render(request, 'portfolio/home.html')

def dashboard(request):
    return render(request, 'portfolio/dashboard.html')

def login_view(request):
    return render(request, 'portfolio/login.html')

def register(request):
    return render(request, 'portfolio/register.html')

