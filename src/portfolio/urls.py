from django.urls import path

from . import views



urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),

    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.user_profile, name='user_profile'),

    path('assets/', views.asset_list, name='asset_list'),
    path('assets/create/', views.asset_create, name='asset_create'),
    path('assets/<int:pk>/', views.asset_detail, name='asset_detail'),
    path('assets/<int:pk>/update/', views.asset_update, name='asset_update'),

    path('portfolios/', views.portfolio_list, name='portfolio_list'),
    path('portfolios/create/', views.portfolio_create, name='portfolio_create'),
    path('portfolios/<int:pk>/', views.portfolio_detail, name='portfolio_detail'),
    path('portfolios/<int:pk>/update/', views.portfolio_update, name='portfolio_update'),
    path('portfolios/<int:portfolio_id>/buy/', views.buy_stock, name='buy_stock'),
    path('portfolios/<int:portfolio_id>/sell/', views.sell_stock, name='sell_stock'),
    path('portfolios/<int:portfolio_id>/transactions/', views.portfolio_transactions, name='portfolio_transactions'),

    path('transactions/', views.transaction_list, name='transaction_list'),
    path('transactions/create/', views.transaction_create, name='transaction_create'),

    path('wallet/', views.wallet, name='wallet'),
    path('wallet/deposit/', views.deposit_money, name='deposit_money'),
    path('wallet/deposit/verify/', views.verify_deposit, name='verify_deposit'),
    path('wallet/withdraw/', views.withdraw_money, name='withdraw_money'),
    path('wallet/transactions/', views.wallet_transactions, name='wallet_transactions'),
    path('wallet/bank-accounts/', views.bank_account_list, name='bank_account_list'),
    path('wallet/bank-accounts/create/', views.bank_account_create, name='bank_account_create'),
    path('wallet/bank-accounts/<int:pk>/update/', views.update_bank_account, name='bank_account_update'),
    path('wallet/bank-accounts/<int:pk>/delete/', views.delete_bank_account, name='bank_account_delete'),
    path('wallet/bank-accounts/<int:pk>/set-default/', views.set_default_bank_account, name='bank_account_set_default'),

    path('market/', views.market, name='market'),

]