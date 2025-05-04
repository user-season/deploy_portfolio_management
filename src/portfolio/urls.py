from django.urls import path

from . import views



urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),

    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),

    path('assets/', views.asset_list, name='asset_list'),
    path('portfolios/', views.portfolio_list, name='portfolio_list'),
    path('portfolios/create/', views.portfolio_create, name='portfolio_create'),

    path('transactions/', views.transaction_list, name='transaction_list'),
    path('wallet/', views.wallet, name='wallet'),
    path('wallet/deposit/', views.deposit_money, name='deposit_money'),
    path('wallet/withdraw/', views.withdraw_money, name='withdraw_money'),

    path('market/', views.market, name='market'),

]