from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate
from django.shortcuts import render, redirect
from django.contrib import messages

from .forms import UserRegistrationForm



def home(request):
    return render(request, 'portfolio/home.html')

def dashboard(request):
    return render(request, 'portfolio/dashboard.html')


def login_view(request):
    """Sử dụng login của Django thay vì Auth0"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'Tên đăng nhập hoặc mật khẩu không đúng')
    return render(request, 'portfolio/login.html')

def register(request):
    """Django registration instead of Auth0"""
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Đăng ký thành công!')
            return redirect('dashboard')
    else:
        form = UserRegistrationForm()
    return render(request, 'portfolio/register.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('home')


def user_profile(request):
    return render(request, 'portfolio/user_profile.html')


def portfolio_list(request):
    return render(request, 'portfolio/portfolio_list.html')
    
def portfolio_create(request):
    return render(request, 'portfolio/portfolio_form.html')

def asset_list(request):
    return render(request, 'portfolio/asset_list.html')


def transaction_list(request):
    return render(request, 'portfolio/transaction_list.html')

def transaction_create(request):
    return render(request, 'portfolio/transaction_form.html')

def wallet(request):
    return render(request, 'portfolio/wallet.html')

def wallet_transactions(request):
    return render(request, 'portfolio/wallet_transactions.html')
    
def bank_account_list(request):
    return render(request, 'portfolio/bank_account_list.html')

def bank_account_create(request):
    return render(request, 'portfolio/bank_account_form.html')
    

def deposit_money(request):
    return render(request, 'portfolio/deposit.html')

def withdraw_money(request):
    return render(request, 'portfolio/withdraw.html')

def market(request):
    return render(request, 'portfolio/market.html')