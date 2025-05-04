from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum
from django.db import transaction
from django.core.paginator import Paginator

from datetime import timedelta
from decimal import Decimal
import uuid

from .forms import UserRegistrationForm, PortfolioForm, TransactionForm, AssetForm, DepositForm, WithdrawForm, BankAccountForm
from .models import Portfolio, PortfolioAsset, Transaction, Asset, Wallet, WalletTransaction, BankAccount
from .utils import generate_qr_code, check_paid
from .templatetags.currency_filters import dinh_dang_tien



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
def asset_create(request):
    if request.method == 'POST':
        form = AssetForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tài sản đã được thêm thành công!')
            return redirect('asset_list')
    else:
        form = AssetForm()
    return render(request, 'portfolio/asset_form.html', {'form': form, 'title': 'Thêm tài sản mới'})

@login_required
def asset_detail(request, pk):
    asset = get_object_or_404(Asset, pk=pk)
    return render(request, 'portfolio/asset_detail.html', {'asset': asset})

@login_required
def asset_update(request, pk):
    asset = get_object_or_404(Asset, pk=pk)
    if request.method == 'POST':
        form = AssetForm(request.POST, instance=asset)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tài sản đã được cập nhật!')
            return redirect('asset_detail', pk=pk)
    else:
        form = AssetForm(instance=asset)
    return render(request, 'portfolio/asset_form.html', {
        'form': form,
        'title': 'Chỉnh sửa tài sản'
    })
    

@login_required
def transaction_list(request):
    return render(request, 'portfolio/transaction_list.html')

@login_required
def transaction_create(request):
    return render(request, 'portfolio/transaction_form.html')


@login_required
def wallet(request):
    # Lấy hoặc tạo ví cho người dùng
    wallet, created = Wallet.objects.get_or_create(user=request.user)
    
    # Hiển thị thông báo về các giao dịch rút tiền đã được xử lý mà người dùng chưa xem
    # Lấy các giao dịch rút tiền đã hoàn thành và chưa được đánh dấu là đã thông báo
    completed_withdrawals = WalletTransaction.objects.filter(
        user=request.user,
        type='withdraw',
        status='completed',
        completed_at__isnull=False,
    ).exclude(
        notes__icontains='đã thông báo'
    ).order_by('-completed_at')[:5]  # Lấy 5 giao dịch gần nhất
    
    # Hiển thị thông báo cho từng giao dịch
    for withdrawal in completed_withdrawals:
        messages.success(
            request,
            f'Yêu cầu rút tiền #{withdrawal.transaction_id} của bạn đã được phê duyệt! '
            f'<br>Số tiền rút: {dinh_dang_tien(withdrawal.amount)} VNĐ'
            f'<br>Phí giao dịch: {dinh_dang_tien(withdrawal.fee)} VNĐ'
            f'<br>Số tiền thực nhận: {dinh_dang_tien(withdrawal.net_amount)} VNĐ'
            f'<br>Thời gian xử lý: {timezone.localtime(withdrawal.completed_at).strftime("%H:%M %d-%m-%Y")}'
        )
        # Đánh dấu là đã thông báo
        withdrawal.notes = f"{withdrawal.notes or ''} | đã thông báo"
        withdrawal.save(update_fields=['notes'])
    
    # Hiển thị thông báo cho các giao dịch bị từ chối
    rejected_withdrawals = WalletTransaction.objects.filter(
        user=request.user,
        type='withdraw',
        status='failed',
        updated_at__isnull=False,
    ).exclude(
        notes__icontains='đã thông báo'
    ).order_by('-updated_at')[:5]
    
    for withdrawal in rejected_withdrawals:
        messages.error(
            request,
            f'Yêu cầu rút tiền #{withdrawal.transaction_id} của bạn đã bị từ chối. '
            f'<br>Số tiền rút: {dinh_dang_tien(withdrawal.amount)} VNĐ'
            f'<br>Thời gian xử lý: {timezone.localtime(withdrawal.updated_at).strftime("%H:%M %d-%m-%Y")}'
            f'<br>Lý do: {withdrawal.notes if "Từ chối" in withdrawal.notes else "Không đáp ứng điều kiện rút tiền"}'
        )
        # Đánh dấu là đã thông báo
        withdrawal.notes = f"{withdrawal.notes or ''} | đã thông báo"
        withdrawal.save(update_fields=['notes'])
    
    # Lấy các giao dịch gần đây
    transactions = WalletTransaction.objects.filter(user=request.user).order_by('-created_at')[:5]
    
    # Các thống kê
    transaction_type = request.GET.get('type', None)
    from_date = request.GET.get('from_date', None)
    to_date = request.GET.get('to_date', None)
    
    # Bộ lọc
    filter_params = {'user': request.user}
    if transaction_type in ['deposit', 'withdraw']:
        filter_params['type'] = transaction_type
    
    if from_date:
        filter_params['created_at__gte'] = from_date
    
    if to_date:
        filter_params['created_at__lte'] = to_date
    
    # Tính tổng nạp và rút
    total_deposit = WalletTransaction.objects.filter(
        user=request.user,
        type='deposit',
        status='completed'
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    total_withdraw = WalletTransaction.objects.filter(
        user=request.user,
        type='withdraw',
        status='completed'
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Tính tổng nạp và rút trong 30 ngày gần đây
    thirty_days_ago = timezone.now() - timedelta(days=30)
    monthly_deposit = WalletTransaction.objects.filter(
        user=request.user,
        type='deposit',
        created_at__gte=thirty_days_ago,
        status='completed'
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    monthly_withdraw = WalletTransaction.objects.filter(
        user=request.user,
        type='withdraw',
        created_at__gte=thirty_days_ago,
        status='completed'
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    context = {
        'wallet': wallet,
        'transactions': transactions,
        'total_deposit': total_deposit,
        'total_withdraw': total_withdraw,
        'monthly_deposit': monthly_deposit,
        'monthly_withdraw': monthly_withdraw
    }
    
    return render(request, 'portfolio/wallet.html', context)

@login_required
def wallet_transactions(request):
    # Lấy tất cả giao dịch của người dùng
    transactions = WalletTransaction.objects.filter(user=request.user).order_by('-created_at')
    
    # Lọc theo loại giao dịch nếu có
    transaction_type = request.GET.get('type')
    if transaction_type in ['deposit', 'withdraw']:
        transactions = transactions.filter(type=transaction_type)
    
    # Lọc theo trạng thái nếu có
    status = request.GET.get('status')
    if status in ['pending', 'completed', 'failed', 'cancelled']:
        transactions = transactions.filter(status=status)
    
    # Lọc theo ngày
    from_date = request.GET.get('from_date')
    if from_date:
        transactions = transactions.filter(created_at__gte=from_date)
    
    to_date = request.GET.get('to_date')
    if to_date:
        transactions = transactions.filter(created_at__lte=to_date)
    
    # Phân trang
    paginator = Paginator(transactions, 10)  # 10 giao dịch mỗi trang
    page_number = request.GET.get('page')
    paged_transactions = paginator.get_page(page_number)
    
    context = {
        'transactions': paged_transactions,
        'transaction_types': WalletTransaction.TYPE_CHOICES,
        'status_choices': WalletTransaction.STATUS_CHOICES
    }
    
    return render(request, 'portfolio/wallet_transactions.html', context)
    
@login_required
def bank_account_list(request):
    bank_accounts = BankAccount.objects.filter(user=request.user).order_by('-is_default', '-created_at')
    
    context = {
        'bank_accounts': bank_accounts
    }
    
    return render(request, 'portfolio/bank_account_list.html', context)

@login_required
def bank_account_create(request):
    if request.method == 'POST':
        form = BankAccountForm(request.POST)
        if form.is_valid():
            bank_account = form.save(commit=False)
            bank_account.user = request.user
            bank_account.save()
            
            bank_name = form.cleaned_data['bank_name']
            if bank_name == 'other':
                display_name = form.cleaned_data['other_bank_name']
            else:
                display_name = dict(BankAccount.BANK_CHOICES)[bank_name]
                
            account_number = form.cleaned_data['account_number']
            
            messages.success(request, f'Đã thêm tài khoản {display_name} - {account_number}')
            return redirect('bank_account_list')
    else:
        form = BankAccountForm()
    
    context = {
        'form': form,
        'title': 'Thêm tài khoản ngân hàng'
    }
    
    return render(request, 'portfolio/bank_account_form.html', context)
    
@login_required
def update_bank_account(request, pk):
    bank_account = get_object_or_404(BankAccount, id=pk, user=request.user)
    
    if request.method == 'POST':
        form = BankAccountForm(request.POST, instance=bank_account)
        if form.is_valid():
            form.save()
            
            bank_name = form.cleaned_data['bank_name']
            if bank_name == 'other':
                display_name = form.cleaned_data['other_bank_name']
            else:
                display_name = dict(BankAccount.BANK_CHOICES)[bank_name]
                
            account_number = form.cleaned_data['account_number']
            
            messages.success(request, f'Đã cập nhật tài khoản {display_name} - {account_number}')
            return redirect('bank_account_list')
    else:
        form = BankAccountForm(instance=bank_account)
    
    context = {
        'form': form,
        'bank_account': bank_account,
        'title': 'Cập nhật tài khoản ngân hàng'
    }
    
    return render(request, 'portfolio/bank_account_form.html', context)

@login_required
def delete_bank_account(request, pk):
    bank_account = get_object_or_404(BankAccount, id=pk, user=request.user)
    
    if request.method == 'POST':
        # Kiểm tra xem có giao dịch đang sử dụng tài khoản này không
        transactions_using_account = WalletTransaction.objects.filter(
            bank_account=bank_account,
            status='pending'
        ).exists()
        
        if transactions_using_account:
            messages.error(request, 'Không thể xóa tài khoản này vì có giao dịch đang xử lý.')
            return redirect('bank_account_list')
        
        # Lưu thông tin để hiển thị thông báo
        bank_name = bank_account.bank_name
        if bank_name == 'other':
            display_name = bank_account.other_bank_name
        else:
            display_name = dict(BankAccount.BANK_CHOICES)[bank_name]
            
        account_number = bank_account.account_number
        
        # Xóa tài khoản
        bank_account.delete()
        
        messages.success(request, f'Đã xóa tài khoản {display_name} - {account_number}')
        return redirect('bank_account_list')
    
    context = {
        'bank_account': bank_account
    }
    
    return render(request, 'portfolio/bank_account_confirm_delete.html', context)
    
@login_required
def set_default_bank_account(request, pk):
    bank_account = get_object_or_404(BankAccount, id=pk, user=request.user)
    
    # Đặt tất cả tài khoản khác thành không mặc định
    BankAccount.objects.filter(user=request.user).update(is_default=False)
    
    # Đặt tài khoản hiện tại thành mặc định
    bank_account.is_default = True
    bank_account.save()
    
    bank_name = bank_account.bank_name
    if bank_name == 'other':
        display_name = bank_account.other_bank_name
    else:
        display_name = dict(BankAccount.BANK_CHOICES)[bank_name]
        
    account_number = bank_account.account_number
    
    messages.success(request, f'Đã đặt {display_name} - {account_number} làm tài khoản mặc định')
    
    return redirect('bank_account_list')


@login_required
def deposit_money(request):
    # Lấy hoặc tạo ví cho người dùng
    wallet, created = Wallet.objects.get_or_create(user=request.user)
    
    # Lấy danh sách tài khoản ngân hàng
    bank_accounts = BankAccount.objects.filter(user=request.user).order_by('-is_default', '-created_at')
    
    # Comprueba si hay un transaction_id en el formulario
    if request.method == 'POST' and 'transaction_id' in request.POST and request.POST.get('transaction_id'):
        transaction_id = request.POST.get('transaction_id')
    else:
        # Tạo transaction_id duy nhất
        transaction_id = f"DEP{uuid.uuid4().hex[:8].upper()}"
    
    # Mặc định amount
    default_amount = Decimal('100000')
    
    # Tạo URL mã QR VietQR
    qr_code_url = generate_qr_code(
        amount=default_amount,
        transaction_id=transaction_id,
        username=request.user.username
    )
    
    # Kiểm tra nếu có xác nhận nạp tiền
    verification_result = None
    if 'verify_deposit' in request.POST:
        # Lấy thông tin giao dịch cần xác nhận
        verify_transaction_id = request.POST.get('verify_transaction_id', transaction_id)
        verify_amount = request.POST.get('verify_amount')
        
        # Log para depuración
        print(f"Verificando depósito: ID={verify_transaction_id}, Monto={verify_amount}")
        
        if verify_transaction_id and verify_amount:
            # Kiểm tra thông tin giao dịch
            verification_result = check_paid(
                transaction_id=verify_transaction_id,
                amount=Decimal(verify_amount)
            )
            
            # Nếu xác nhận thành công
            if verification_result['success']:
                # Tạo transaction_obj trong DB
                with transaction.atomic():
                    # Tạo giao dịch nạp tiền
                    transaction_obj = WalletTransaction.objects.create(
                        user=request.user,
                        wallet=wallet,
                        type='deposit',
                        amount=Decimal(verify_amount),
                        fee=0,  # Miễn phí nạp tiền
                        net_amount=Decimal(verify_amount),
                        status='completed',  # Trạng thái hoàn thành
                        payment_method='bank_transfer',
                        transaction_id=verify_transaction_id,
                        notes=f"Nạp tiền xác nhận thủ công: {verification_result['message']}"
                    )
                
                messages.success(request, verification_result['message'])
                return redirect('wallet')
            else:
                messages.error(request, verification_result['message'])
    
    # Xử lý form deposit bình thường
    if request.method == 'POST' and 'confirm_transfer' in request.POST:
        print("POST request received for deposit_money")
        print("POST data:", request.POST)
        
        form = DepositForm(request.user, request.POST)
        if form.is_valid():
            print("Form is valid, processing deposit...")
            # Xử lý form nạp tiền
            amount = form.cleaned_data['amount']
            payment_method = form.cleaned_data['payment_method']
            bank_account = form.cleaned_data.get('bank_account')
            agree_terms = form.cleaned_data['agree_terms']
            
            # Kiểm tra xem giao dịch có trùng lặp không (trong vòng 5 phút gần đây)
            five_minutes_ago = timezone.now() - timedelta(minutes=5)
            recent_deposits = WalletTransaction.objects.filter(
                user=request.user,
                type='deposit',
                amount=amount,
                payment_method=payment_method,
                created_at__gte=five_minutes_ago
            )
            
            if recent_deposits.exists():
                messages.warning(request, 'Một giao dịch nạp tiền tương tự đã được thực hiện trong vòng 5 phút qua. Vui lòng đợi một lát và kiểm tra số dư của bạn trước khi thử lại.')
                return redirect('wallet')
            
            # Nếu là phương thức thanh toán chuyển khoản ngân hàng nhưng không chọn tài khoản nào
            if payment_method == 'bank_transfer' and not bank_account:
                # Xử lý tài khoản ngân hàng mới
                bank_name = form.cleaned_data.get('new_bank_name')
                other_bank_name = form.cleaned_data.get('new_other_bank_name')
                account_name = form.cleaned_data.get('new_account_name')
                account_number = form.cleaned_data.get('new_account_number')
                branch = form.cleaned_data.get('new_branch')
                is_default = form.cleaned_data.get('new_is_default', False)
                
                if bank_name and account_name and account_number:
                    if bank_name == 'other' and other_bank_name:
                        display_name = other_bank_name
                    else:
                        display_name = dict(BankAccount.BANK_CHOICES)[bank_name]
                    
                    # Tạo tài khoản ngân hàng mới
                    bank_account = BankAccount.objects.create(
                        user=request.user,
                        bank_name=bank_name,
                        other_bank_name=other_bank_name,
                        account_name=account_name,
                        account_number=account_number,
                        branch=branch,
                        is_default=is_default
                    )
                    
                    messages.success(request, f'Đã thêm tài khoản {display_name} - {account_number}')
                else:
                    messages.error(request, 'Vui lòng chọn hoặc thêm tài khoản ngân hàng để tiếp tục nạp tiền.')
                    return redirect('deposit_money')
            
            # Chuyển sang trang xác nhận nạp tiền
            context = {
                'wallet': wallet,
                'amount': amount,
                'transaction_id': transaction_id,
                'payment_method': payment_method,
                'qr_code_url': generate_qr_code(
                    amount=amount,
                    transaction_id=transaction_id,
                    username=request.user.username
                ),
                'bank_account': bank_account,
                'verify_mode': True
            }
            
            return render(request, 'portfolio/deposit.html', context)
        else:
            print("Form is invalid")
            print("Form errors:", form.errors)
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{error}")
            
            # Nếu có amount trong form không hợp lệ, tạo lại mã QR với amount từ form
            amount = request.POST.get('amount', default_amount)
            qr_code_url = generate_qr_code(
                amount=amount,
                transaction_id=transaction_id,
                username=request.user.username
            )
    else:
        form = DepositForm(request.user)
    
    context = {
        'wallet': wallet,
        'bank_accounts': bank_accounts,
        'form': form,
        'qr_code_url': qr_code_url,
        'transaction_id': transaction_id,
        'verification_result': verification_result,
        'verify_mode': False
    }
    
    return render(request, 'portfolio/deposit.html', context)

@login_required
def verify_deposit(request, transaction_id=None):
    """View để kiểm tra giao dịch nạp tiền cuối cùng"""
    if request.method != 'POST':
        return redirect('deposit_money')
        
    # Lấy thông tin từ form
    # Prioriza obtener el transaction_id del parámetro, luego del formulario
    if not transaction_id:
        # Usamos el campo oculto transaction_id si está presente
        transaction_id = request.POST.get('transaction_id')
        # Como fallback, usamos verify_transaction_id
        if not transaction_id:
            transaction_id = request.POST.get('verify_transaction_id')
    
    verify_transaction_id = transaction_id  # Aseguramos que se use el mismo ID
    verify_amount = request.POST.get('verify_amount')
    
    if not verify_transaction_id or not verify_amount:
        messages.error(request, "Vui lòng cung cấp đầy đủ mã giao dịch và số tiền để xác nhận nạp tiền")
        return redirect('deposit_money')
    
    # Kiểm tra thông tin giao dịch
    verification_result = check_paid(
        transaction_id=verify_transaction_id,
        amount=Decimal(verify_amount)
    )
    
    # Log para depuración
    print(f"Verificando transacción: ID={verify_transaction_id}, Monto={verify_amount}")
    
    # Lấy hoặc tạo ví cho người dùng
    wallet, created = Wallet.objects.get_or_create(user=request.user)
    
    # Nếu xác nhận thành công
    if verification_result['success']:
        # Kiểm tra xem giao dịch này đã được xử lý chưa
        if WalletTransaction.objects.filter(
            user=request.user, 
            transaction_id=verify_transaction_id, 
            status='completed'
        ).exists():
            messages.warning(request, f"Giao dịch với mã {verify_transaction_id} đã được xử lý trước đó.")
            return redirect('wallet')
            
        # Tạo transaction_obj trong DB
        with transaction.atomic():
            # Tạo giao dịch nạp tiền
            transaction_obj = WalletTransaction.objects.create(
                user=request.user,
                wallet=wallet,
                type='deposit',
                amount=Decimal(verify_amount),
                fee=0,  # Miễn phí nạp tiền
                net_amount=Decimal(verify_amount),
                status='completed',  # Trạng thái hoàn thành
                payment_method='bank_transfer',
                transaction_id=verify_transaction_id,
                notes=f"Nạp tiền xác nhận thủ công: {verification_result['message']}"
            )
        
        messages.success(request, verification_result['message'])
        return redirect('wallet')
    else:
        messages.error(request, verification_result['message'])
        
    # Quay lại trang nạp tiền với kết quả xác nhận
    return redirect('deposit_money')

@login_required
def withdraw_money(request):
    # Lấy hoặc tạo ví cho người dùng
    wallet, created = Wallet.objects.get_or_create(user=request.user)
    
    # Lấy danh sách tài khoản ngân hàng
    bank_accounts = BankAccount.objects.filter(user=request.user).order_by('-is_default', '-created_at')
    
    # Số dư tối thiểu để rút tiền (50,000 VND)
    MINIMUM_BALANCE = Decimal('50000')
    
    # Phí cố định cho mỗi giao dịch rút tiền (10,000 VND)
    WITHDRAWAL_FEE = Decimal('10000')
    
    if request.method == 'POST':
        form = WithdrawForm(request.user, request.POST)
        if form.is_valid():
            # Xử lý form rút tiền
            amount = form.cleaned_data['amount']
            bank_account = form.cleaned_data.get('bank_account')
            withdraw_note = form.cleaned_data.get('notes', '')
            
            # Tính phí rút tiền và số tiền thực nhận
            fee = WITHDRAWAL_FEE
            net_amount = amount - fee
            
            # Kiểm tra số tiền rút hợp lệ (sau khi trừ phí phải > 0)
            if net_amount <= 0:
                messages.error(request, f'Số tiền rút phải lớn hơn phí giao dịch ({dinh_dang_tien(WITHDRAWAL_FEE)} VNĐ).')
                return redirect('withdraw_money')
            
            # Kiểm tra số dư - phải đảm bảo đủ rút và đảm bảo số dư còn lại trên mức tối thiểu
            if amount > wallet.balance:
                messages.error(request, 'Số dư của bạn không đủ để thực hiện giao dịch này.')
                return redirect('withdraw_money')
            
            # Kiểm tra số dư còn lại sau khi rút phải lớn hơn hoặc bằng số dư tối thiểu
            if (wallet.balance - amount) < MINIMUM_BALANCE:
                messages.error(request, f'Số dư còn lại sau khi rút phải lớn hơn hoặc bằng {dinh_dang_tien(MINIMUM_BALANCE)} VNĐ.')
                return redirect('withdraw_money')
            
            # Nếu không chọn tài khoản nào
            if not bank_account:
                # Xử lý tài khoản ngân hàng mới
                bank_name = form.cleaned_data.get('new_bank_name')
                other_bank_name = form.cleaned_data.get('new_other_bank_name')
                account_name = form.cleaned_data.get('new_account_name')
                account_number = form.cleaned_data.get('new_account_number')
                branch = form.cleaned_data.get('new_branch')
                is_default = form.cleaned_data.get('new_is_default', False)
                
                if bank_name and account_name and account_number:
                    if bank_name == 'other' and other_bank_name:
                        display_name = other_bank_name
                    else:
                        display_name = dict(BankAccount.BANK_CHOICES)[bank_name]
                    
                    # Tạo tài khoản ngân hàng mới
                    bank_account = BankAccount.objects.create(
                        user=request.user,
                        bank_name=bank_name,
                        other_bank_name=other_bank_name,
                        account_name=account_name,
                        account_number=account_number,
                        branch=branch,
                        is_default=is_default
                    )
                    
                    messages.success(request, f'Đã thêm tài khoản {display_name} - {account_number}')
                else:
                    messages.error(request, 'Vui lòng chọn hoặc thêm tài khoản ngân hàng để tiếp tục rút tiền.')
                    return redirect('withdraw_money')
            
            # Tạo transaction_id duy nhất để tránh giao dịch trùng lặp
            transaction_id = f"WIT{uuid.uuid4().hex[:8].upper()}"
            
            # Kiểm tra xem giao dịch có trùng lặp không (trong vòng 5 phút gần đây)
            five_minutes_ago = timezone.now() - timedelta(minutes=5)
            recent_withdrawals = WalletTransaction.objects.filter(
                user=request.user,
                type='withdraw',
                amount=amount,
                created_at__gte=five_minutes_ago
            )
            
            if recent_withdrawals.exists():
                messages.warning(request, 'Một giao dịch rút tiền tương tự đã được thực hiện trong vòng 5 phút qua. Vui lòng đợi một lát và kiểm tra số dư của bạn trước khi thử lại.')
                return redirect('wallet')
            
            # Sử dụng transaction.atomic để đảm bảo tính toàn vẹn dữ liệu
            with transaction.atomic():
                # Tạo giao dịch rút tiền với trạng thái 'pending' - chờ admin phê duyệt
                transaction_obj = WalletTransaction.objects.create(
                    user=request.user,
                    wallet=wallet,
                    type='withdraw',
                    amount=amount,
                    fee=fee,
                    net_amount=net_amount,
                    status='pending', # Thay đổi trạng thái thành 'pending' thay vì 'completed'
                    bank_account=bank_account,
                    payment_method='bank_transfer',
                    transaction_id=transaction_id,
                    notes=withdraw_note
                )
            
            messages.success(
                request, 
                f'Yêu cầu rút tiền đã được gửi đi và đang chờ xét duyệt! '
                f'<br>Số tiền rút: {dinh_dang_tien(amount)} VNĐ'
                f'<br>Phí giao dịch: {dinh_dang_tien(fee)} VNĐ'
                f'<br>Số tiền thực nhận: {dinh_dang_tien(net_amount)} VNĐ'
                f'<br>Số dư hiện tại: {dinh_dang_tien(wallet.balance)} VNĐ'
                f'<br>Trạng thái: Đang chờ xử lý'
            )
            return redirect('wallet')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{error}")
    else:
        form = WithdrawForm(request.user)
    
    context = {
        'wallet': wallet,
        'bank_accounts': bank_accounts,
        'form': form,
        'minimum_balance': MINIMUM_BALANCE,
        'withdrawal_fee': WITHDRAWAL_FEE
    }
    
    return render(request, 'portfolio/withdraw.html', context)

@login_required
def market(request):
    return render(request, 'portfolio/market.html')