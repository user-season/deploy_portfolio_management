from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone

from .forms import UserRegistrationForm, PortfolioForm, TransactionForm
from .models import Portfolio, PortfolioAsset, Transaction, Asset


def home(request):
    return render(request, 'portfolio/home.html')

@login_required
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


@login_required
def user_profile(request):
    return render(request, 'portfolio/user_profile.html')

@login_required
def portfolio_list(request):
    portfolios = Portfolio.objects.filter(user=request.user)
    return render(request, 'portfolio/portfolio_list.html', {'portfolios': portfolios})

@login_required
def portfolio_create(request):
    if request.method == 'POST':
        form = PortfolioForm(request.POST)
        if form.is_valid():
            portfolio = form.save(commit=False)
            portfolio.user = request.user
            portfolio.save()
            
            messages.success(request, 'Danh mục đầu tư đã được tạo thành công!')
            
            # Chuyển hướng đến trang chi tiết danh mục vừa tạo
            return redirect('portfolio_detail', pk=portfolio.pk)
    else:
        form = PortfolioForm()
    
    return render(request, 'portfolio/portfolio_form.html', {
        'form': form,
        'title': 'Tạo danh mục mới'
    })

@login_required
def portfolio_detail(request, pk):
    portfolio = get_object_or_404(Portfolio, pk=pk, user=request.user)
    
    # Lấy danh sách tài sản trong danh mục
    portfolio_assets = PortfolioAsset.objects.filter(
        portfolio=portfolio,
        quantity__gt=0
    ).select_related('asset')
    
    # Lấy các giao dịch gần đây
    recent_transactions = Transaction.objects.filter(
        portfolio=portfolio
    ).select_related('asset').order_by('-transaction_date')[:5]
    
    # Tính toán thống kê
    total_invested = sum(pa.quantity * pa.average_price for pa in portfolio_assets)
    total_current_value = sum(pa.current_value for pa in portfolio_assets)
    total_profit_loss = total_current_value - total_invested
    profit_percentage = (total_profit_loss / total_invested * 100) if total_invested > 0 else 0
    
    # Phân bổ tài sản theo loại
    asset_allocation = {}
    for pa in portfolio_assets:
        asset_type = pa.asset.get_type_display()
        asset_allocation[asset_type] = asset_allocation.get(asset_type, 0) + pa.current_value
    
    context = {
        'portfolio': portfolio,
        'portfolio_assets': portfolio_assets,
        'recent_transactions': recent_transactions,
        'total_invested': total_invested,
        'total_current_value': total_current_value,
        'total_profit_loss': total_profit_loss,
        'profit_percentage': profit_percentage,
        'asset_allocation': asset_allocation,
    }
    
    return render(request, 'portfolio/portfolio_detail.html', context)

@login_required
def portfolio_update(request, pk):
    portfolio = get_object_or_404(Portfolio, pk=pk, user=request.user)
    if request.method == 'POST':
        form = PortfolioForm(request.POST, instance=portfolio)
        if form.is_valid():
            form.save()
            messages.success(request, 'Danh mục đầu tư đã được cập nhật!')
            return redirect('portfolio_detail', pk=pk)
    else:
        form = PortfolioForm(instance=portfolio)
    return render(request, 'portfolio/portfolio_form.html', {
        'form': form,
        'title': 'Chỉnh sửa danh mục'
    })

@login_required
def buy_stock(request, portfolio_id):
    portfolio = get_object_or_404(Portfolio, pk=portfolio_id, user=request.user)
    
    # Get all assets for the autocomplete feature
    all_assets = Asset.objects.all()
    
    if request.method == 'POST':
        # Get symbol and convert to asset
        symbol = request.POST.get('symbol')
        
        try:
            # Find asset by symbol
            asset = Asset.objects.get(symbol=symbol)
            
            # Build form data with the asset included
            form_data = request.POST.copy()
            form_data['asset'] = asset.id  # Set the asset ID in the form data
            
            form = TransactionForm(form_data, initial={'portfolio': portfolio, 'transaction_type': 'buy'})
            
            if form.is_valid():
                transaction = form.save(commit=False)
                transaction.portfolio = portfolio
                transaction.transaction_type = 'buy'
                transaction.transaction_date = timezone.now()
                transaction.save()
                
                messages.success(request, 'Giao dịch mua đã được thực hiện thành công!')
                return redirect('portfolio_detail', pk=portfolio_id)
            else:
                messages.error(request, f"Lỗi khi xử lý giao dịch: {form.errors}")
        except Asset.DoesNotExist:
            messages.error(request, f"Không tìm thấy cổ phiếu với mã {symbol}")
            form = TransactionForm(initial={
                'portfolio': portfolio,
                'transaction_type': 'buy',
                'transaction_date': timezone.now()
            })
    else:
        # Create form with initial values
        form = TransactionForm(initial={
            'portfolio': portfolio,
            'transaction_type': 'buy',
            'transaction_date': timezone.now()
        })
        
        # Direct assignment of assets queryset
        form.fields['asset'].queryset = all_assets
        
        # Log the asset count
        print(f"DEBUG: Asset count in buy_stock form: {form.fields['asset'].queryset.count()}")
    
    return render(request, 'portfolio/transaction_form.html', {
        'form': form,
        'title': 'Mua cổ phiếu',
        'portfolio': portfolio,
        'portfolio_assets': portfolio.portfolioasset_set.all(),
        'all_assets': all_assets
    })

@login_required
def sell_stock(request, portfolio_id):
    # Check that the portfolio exists and belongs to the current user
    portfolio = get_object_or_404(Portfolio, pk=portfolio_id, user=request.user)
    
    # Get owned assets for this portfolio with quantity > 0
    portfolio_assets = PortfolioAsset.objects.filter(
        portfolio=portfolio,
        quantity__gt=0
    ).select_related('asset')
    
    # Get assets that can be sold (having quantity > 0)
    owned_assets = Asset.objects.filter(
        id__in=portfolio_assets.values_list('asset_id', flat=True)
    )
    
    # Debug info
    print(f"DEBUG: Portfolio ID: {portfolio_id}, User: {request.user.username}")
    print(f"DEBUG: Owned assets count: {owned_assets.count()}")
    print(f"DEBUG: Portfolio assets count: {portfolio_assets.count()}")
    
    if request.method == 'POST':
        # Get symbol and convert to asset
        symbol = request.POST.get('symbol')
        
        try:
            # Find asset by symbol
            asset = Asset.objects.get(symbol=symbol)
            
            # Build form data with the asset included
            form_data = request.POST.copy()
            form_data['asset'] = asset.id  # Set the asset ID in the form data
            
            form = TransactionForm(form_data, initial={'portfolio': portfolio, 'transaction_type': 'sell'})
            
            if form.is_valid():
                quantity = form.cleaned_data['quantity']
                
                # Kiểm tra số lượng bán không vượt quá số lượng hiện có
                portfolio_asset = portfolio_assets.filter(asset=asset).first()
                
                if not portfolio_asset or portfolio_asset.quantity < quantity:
                    messages.error(request, 'Số lượng bán vượt quá số lượng hiện có!')
                    # Reset the asset queryset to only owned assets
                    form.fields['asset'].queryset = owned_assets
                    return render(request, 'portfolio/transaction_form.html', {
                        'form': form,
                        'title': 'Bán cổ phiếu',
                        'portfolio': portfolio,
                        'portfolio_assets': portfolio_assets,
                        'owned_assets': owned_assets
                    })
                
                transaction = form.save(commit=False)
                transaction.portfolio = portfolio
                transaction.transaction_type = 'sell'
                transaction.transaction_date = timezone.now()
                transaction.save()
                
                messages.success(request, 'Giao dịch bán đã được thực hiện thành công!')
                return redirect('portfolio_detail', pk=portfolio_id)
            else:
                # Debug form errors
                print(f"DEBUG: Form errors: {form.errors}")
                messages.error(request, f"Lỗi nhập dữ liệu: {form.errors}")
                # Reset the asset queryset to only owned assets
                form.fields['asset'].queryset = owned_assets
        except Asset.DoesNotExist:
            messages.error(request, f"Không tìm thấy cổ phiếu với mã {symbol}")
            form = TransactionForm(initial={
                'portfolio': portfolio,
                'transaction_type': 'sell',
                'transaction_date': timezone.now()
            })
            form.fields['asset'].queryset = owned_assets
    else:
        # Create form with initial values
        form = TransactionForm(initial={
            'portfolio': portfolio,
            'transaction_type': 'sell',
            'transaction_date': timezone.now()
        })
        
        # Direct assignment of assets queryset
        form.fields['asset'].queryset = owned_assets
        
        # Log the asset count
        print(f"DEBUG: Owned asset count in sell_stock form: {owned_assets.count()}")
        
        # Debug owned assets
        for asset in owned_assets:
            try:
                portfolio_asset = portfolio_assets.get(asset=asset)
                print(f"  - {asset.symbol}: {portfolio_asset.quantity} shares at {portfolio_asset.average_price}")
            except PortfolioAsset.DoesNotExist:
                print(f"  - Error: No PortfolioAsset found for {asset.symbol}")
        
        # Add warning message if no assets are available
        if not owned_assets.exists():
            messages.warning(request, 'Không có cổ phiếu nào trong danh mục để bán. Hãy mua cổ phiếu trước.')
    
    return render(request, 'portfolio/transaction_form.html', {
        'form': form,
        'title': 'Bán cổ phiếu',
        'portfolio': portfolio,
        'portfolio_assets': portfolio_assets,
        'owned_assets': owned_assets
    })

@login_required
def portfolio_transactions(request, portfolio_id):
    portfolio = get_object_or_404(Portfolio, pk=portfolio_id, user=request.user)
    transactions = Transaction.objects.filter(portfolio=portfolio).order_by('-transaction_date')
    return render(request, 'portfolio/portfolio_transactions.html', {
        'portfolio': portfolio,
        'transactions': transactions
    })


@login_required
def asset_list(request):
    return render(request, 'portfolio/asset_list.html')

@login_required
def transaction_list(request):
    return render(request, 'portfolio/transaction_list.html')

@login_required
def transaction_create(request):
    return render(request, 'portfolio/transaction_form.html')


@login_required
def wallet(request):
    return render(request, 'portfolio/wallet.html')

@login_required
def wallet_transactions(request):
    return render(request, 'portfolio/wallet_transactions.html')
    
@login_required
def bank_account_list(request):
    return render(request, 'portfolio/bank_account_list.html')

@login_required
def bank_account_create(request):
    return render(request, 'portfolio/bank_account_form.html')
    

@login_required
def deposit_money(request):
    return render(request, 'portfolio/deposit.html')

@login_required
def withdraw_money(request):
    return render(request, 'portfolio/withdraw.html')

@login_required
def market(request):
    return render(request, 'portfolio/market.html')