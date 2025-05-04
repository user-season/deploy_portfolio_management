from django.urls import path

from . import views



urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),

    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('profile/', views.user_profile, name='user_profile'),

    path('assets/', views.asset_list, name='asset_list'),

    path('portfolios/', views.portfolio_list, name='portfolio_list'),
    path('portfolios/create/', views.portfolio_create, name='portfolio_create'),

    path('transactions/', views.transaction_list, name='transaction_list'),
    path('transactions/create/', views.transaction_create, name='transaction_create'),

    path('wallet/', views.wallet, name='wallet'),
    path('wallet/transactions/', views.wallet_transactions, name='wallet_transactions'),
    path('wallet/deposit/', views.deposit_money, name='deposit_money'),
    path('wallet/withdraw/', views.withdraw_money, name='withdraw_money'),
    path('wallet/transactions/', views.wallet_transactions, name='wallet_transactions'),
    path('wallet/bank-accounts/', views.bank_account_list, name='bank_account_list'),
    path('wallet/bank-accounts/create/', views.bank_account_create, name='bank_account_create'),

    path('market/', views.market, name='market'),

]