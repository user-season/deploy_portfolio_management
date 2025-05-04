from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from .models import Portfolio, Asset, Transaction, PortfolioAsset, User, Wallet
from .forms import PortfolioForm, AssetForm, TransactionForm, UserRegistrationForm, UserProfileForm
from django.contrib.auth import login, logout, authenticate
from decimal import Decimal
from django.http import JsonResponse
from .vnstock_services import get_price_board, get_historical_data, sync_vnstock_to_assets, fetch_stock_prices_snapshot
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .utils import get_ai_response
from django.urls import reverse
from urllib.parse import quote_plus, urlencode
import os
# from authlib.integrations.django_client import OAuth  # Comment out this import
from django.conf import settings
from vnstock import Vnstock
import json
import pandas as pd
import random

# Comment out OAuth setup temporarily
"""
oauth = OAuth()
oauth.register(
    "auth0",
    client_id=settings.AUTH0_CLIENT_ID,
    client_secret=settings.AUTH0_CLIENT_SECRET,
    client_kwargs={"scope": "openid profile email"},
    server_metadata_url=f"https://{settings.AUTH0_DOMAIN}/.well-known/openid-configuration",
)
"""

def home(request):
    return render(request, 'portfolio/home.html')

@login_required
def dashboard(request):
    portfolios = Portfolio.objects.filter(user=request.user)
    total_value = sum(p.total_value for p in portfolios)
    total_cost = sum(p.total_cost for p in portfolios)
    total_profit = ((total_value - total_cost) / total_cost * 100) if total_cost > 0 else 0
    
    total_assets = PortfolioAsset.objects.filter(
        portfolio__user=request.user,
        quantity__gt=0
    ).count()
    
    monthly_transactions = Transaction.objects.filter(
        portfolio__user=request.user,
        transaction_date__gte=timezone.now() - timezone.timedelta(days=30)
    ).count()
    
    recent_transactions = Transaction.objects.filter(
        portfolio__user=request.user
    ).order_by('-transaction_date')[:5]
    
    # Get wallet for displaying balance on dashboard
    wallet, created = Wallet.objects.get_or_create(user=request.user)

    context = {
        'portfolios': portfolios,
        'total_value': total_value,
        'total_profit': total_profit,
        'total_assets': total_assets,
        'monthly_transactions': monthly_transactions,
        'recent_transactions': recent_transactions,
        'wallet': wallet,
    }
    return render(request, 'portfolio/dashboard.html', context)

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
def asset_list(request):
    # Get portfolio assets that user actually owns (quantity > 0)
    portfolio_assets = PortfolioAsset.objects.filter(
        portfolio__user=request.user,
        quantity__gt=0
    ).select_related('asset')
    
    # Get unique assets from portfolio assets
    owned_asset_ids = portfolio_assets.values_list('asset_id', flat=True).distinct()
    owned_assets = Asset.objects.filter(id__in=owned_asset_ids)
    
    # Calculate total values and add portfolio-related attributes to each asset
    assets_with_data = []
    
    for asset in owned_assets:
        # Get portfolio asset data for this asset across all portfolios
        asset_portfolio_items = portfolio_assets.filter(asset=asset)
        
        # Sum quantities and calculate weighted average price
        total_quantity = sum(pa.quantity for pa in asset_portfolio_items)
        total_cost = sum(pa.quantity * pa.average_price for pa in asset_portfolio_items)
        average_price = total_cost / total_quantity if total_quantity > 0 else 0
        
        # Calculate current value and profit/loss
        current_value = total_quantity * asset.current_price
        profit_loss = current_value - total_cost
        profit_loss_percent = (profit_loss / total_cost * 100) if total_cost > 0 else 0
        
        # Add data to asset
        asset.quantity = total_quantity
        asset.average_price = average_price
        asset.total_value = current_value
        asset.profit_loss = profit_loss
        asset.profit_loss_percent = profit_loss_percent
        
        assets_with_data.append(asset)
    
    # Calculate portfolio totals
    total_investment = sum(asset.quantity * asset.average_price for asset in assets_with_data)
    total_current_value = sum(asset.quantity * asset.current_price for asset in assets_with_data)
    print(f"DEBUG: Total investment: {total_investment}, Total current value: {total_current_value}")
    total_profit_loss = total_current_value - total_investment
    total_profit_loss_percent = (total_profit_loss / total_investment * 100) if total_investment > 0 else 0
    
    # Fetch stock data for debug table
    try:
        # Initialize VNStock instance
        vnstock_instance = Vnstock()
        stock = vnstock_instance.stock(symbol='VN30', source='VCI')
        
        # Get stock list and price board
        all_symbols_df = stock.listing.all_symbols()
        symbols_list = all_symbols_df['ticker'].tolist()[:5]  # Get first 5 stocks
        price_board = stock.trading.price_board(symbols_list=symbols_list)
        
        # Convert to list of dictionaries for template
        debug_stocks = []
        for symbol in symbols_list:
            try:
                symbol_info = all_symbols_df[all_symbols_df['ticker'] == symbol].iloc[0]
                price_info = price_board[price_board['listing_symbol'] == symbol].iloc[0]
                
                # Extract needed info
                stock_data = {
                    'ticker': symbol,
                    'organ_name': symbol_info['organ_name'],
                    'price': price_info['match_match_price'] if 'match_match_price' in price_info else None,
                    'change': price_info['match_change_percent'] if 'match_change_percent' in price_info else None,
                    'volume': price_info['match_match_qtty'] if 'match_match_qtty' in price_info else None
                }
                debug_stocks.append(stock_data)
            except (IndexError, KeyError):
                continue
    except Exception as e:
        # Provide mock data for debug stocks if API fails
        debug_stocks = [
            {
                'ticker': 'VNM',
                'organ_name': 'Công ty Cổ phần Sữa Việt Nam',
                'price': 75000,
                'change': 2.5,
                'volume': 1250000
            },
            {
                'ticker': 'FPT',
                'organ_name': 'Công ty Cổ phần FPT',
                'price': 92300,
                'change': 1.8,
                'volume': 980500
            },
            {
                'ticker': 'VIC',
                'organ_name': 'Tập đoàn Vingroup',
                'price': 48600,
                'change': -1.2,
                'volume': 1432000
            },
            {
                'ticker': 'VHM',
                'organ_name': 'Công ty Cổ phần Vinhomes',
                'price': 45800,
                'change': -0.7,
                'volume': 875000
            },
            {
                'ticker': 'MSN',
                'organ_name': 'Tập đoàn Masan',
                'price': 82500,
                'change': 3.2,
                'volume': 654300
            }
        ]
        print(f"Using mock data for debug stocks. Error was: {e}")
    
    # Get asset types for filter
    asset_types = Asset.ASSET_TYPES
    
    # Get unique sectors for filter
    sectors = Asset.objects.values_list('sector', flat=True).distinct()
    
    context = {
        'assets': assets_with_data,
        'debug_stocks': debug_stocks,
        'asset_types': asset_types,
        'sectors': sectors,
        'total_investment': total_investment,
        'total_current_value': total_current_value,
        'total_profit_loss': total_profit_loss,
        'total_profit_loss_percent': total_profit_loss_percent
    }
    
    return render(request, 'portfolio/asset_list.html', context)

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
    transactions = Transaction.objects.filter(portfolio__user=request.user)
    
    # Lọc theo danh mục
    portfolio_id = request.GET.get('portfolio')
    if portfolio_id:
        transactions = transactions.filter(portfolio_id=portfolio_id)
    
    # Lọc theo loại giao dịch
    transaction_type = request.GET.get('type')
    if transaction_type:
        transactions = transactions.filter(transaction_type=transaction_type)
    
    # Lọc theo ngày
    from_date = request.GET.get('from_date')
    if from_date:
        transactions = transactions.filter(transaction_date__gte=from_date)
    
    to_date = request.GET.get('to_date')
    if to_date:
        transactions = transactions.filter(transaction_date__lte=to_date)
    
    # Phân trang
    paginator = Paginator(transactions.order_by('-transaction_date'), 10)
    page = request.GET.get('page')
    transactions = paginator.get_page(page)
    
    context = {
        'transactions': transactions,
        'portfolios': Portfolio.objects.filter(user=request.user)
    }
    return render(request, 'portfolio/transaction_list.html', context)

@login_required
def transaction_create(request):
    if request.method == 'POST':
        form = TransactionForm(request.POST)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.total_amount = transaction.quantity * transaction.price
            transaction.save()
            messages.success(request, 'Giao dịch đã được tạo thành công!')
            return redirect('transaction_list')
    else:
        form = TransactionForm()
    return render(request, 'portfolio/transaction_form.html', {
        'form': form,
        'title': 'Tạo giao dịch mới'
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

# Auth0 related views - replaced with Django authentication
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

# Callback không còn cần thiết khi không sử dụng Auth0
def callback(request):
    """Function này sẽ không được sử dụng khi không dùng Auth0"""
    return redirect('home')

def logout_view(request):
    """Log the user out of Django"""
    # Log the user out of Django
    logout(request)
    # Redirect to home page
    return redirect('home')

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

# User profile view
@login_required
def user_profile(request):
    user = request.user
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            user_data = form.save(commit=False)
            
            # Check if a new profile picture was uploaded
            if 'profile_picture' in request.FILES and request.FILES['profile_picture']:
                # If Auth0 user uploads a local picture, prioritize it over the Auth0 URL
                user_data.profile_picture = request.FILES['profile_picture']
            
            user_data.save()
            messages.success(request, 'Thông tin cá nhân đã được cập nhật thành công!')
            return redirect('user_profile')
    else:
        form = UserProfileForm(instance=user)
    
    return render(request, 'portfolio/user_profile.html', {
        'form': form
    })

# ============ MARKET =======
@login_required
def market(request):
    # Get price board data or use fallback data if there's an error
    try:
        price_board = get_price_board()
        price_board_json = price_board.to_json(orient='split')
        print("Successfully fetched price board data")
    except Exception as e:
        print(f"Error in market view: {str(e)}")
        # Simple fallback data with explicit index structure
        fallback_data = {
            "index": [0, 1, 2, 3, 4],
            "columns": ["symbol", "ceiling", "floor", "ref_price", "match_price", "match_vol"],
            "data": [
                ["AAA", 25000, 20000, 22000, 22500, 10000],
                ["VNM", 60000, 50000, 55000, 56000, 5000],
                ["FPT", 90000, 80000, 85000, 86000, 3000],
                ["VIC", 45000, 35000, 40000, 41000, 2000],
                ["MSN", 70000, 60000, 65000, 66000, 4000]
            ]
        }
        price_board_json = json.dumps(fallback_data)
        messages.warning(request, "Không thể tải dữ liệu thị trường thực. Hiển thị dữ liệu mẫu.")
    
    # Log data for debugging
    print(f"Data structure sent to template: {price_board_json[:100]}...")
    
    context = {
        "price_board_json": price_board_json,
    }
    return render(request, 'portfolio/market.html', context)

def get_historical_data_api(request, stock_code):
    try:
        data = get_historical_data(stock_code)
        return JsonResponse({'data': data.to_dict('records')})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
def get_stock_historical_data(request, symbol):
    try:
        # Lấy dữ liệu lịch sử từ vnstock service
        historical_data = get_historical_data(symbol)
        
        # Chuyển đổi dữ liệu thành định dạng phù hợp cho biểu đồ
        chart_data = []
        for _, row in historical_data.iterrows():
            chart_data.append({
                'time': row['time'].strftime('%Y-%m-%d') if hasattr(row['time'], 'strftime') else str(row['time']),
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close'])
            })
        
        print(f"Returning data for {symbol}: {len(chart_data)} records") # Debug log
        print(f"Sample data: {chart_data[:1]}") # Debug log để xem mẫu dữ liệu
        return JsonResponse(chart_data, safe=False)
    except Exception as e:
        print(f"Error getting data for {symbol}: {str(e)}") # Debug log
        print(f"Data structure: {historical_data.head()}") if 'historical_data' in locals() else print("No data fetched") # Debug log để xem cấu trúc dữ liệu
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_POST
def ai_chat_api(request):
    """
    API endpoint để xử lý các yêu cầu chat với AI
    """
    try:
        data = json.loads(request.body)
        message = data.get('message', '')
        
        if not message:
            return JsonResponse({
                'success': False,
                'error': 'Tin nhắn không được để trống'
            }, status=400)
        
        # Gọi API AI để nhận phản hồi
        response = get_ai_response(message)
        
        # Đơn giản hóa định dạng phản hồi và loại bỏ ký tự formatting
        response = response.strip()
        # Loại bỏ các ký tự đánh dấu in đậm và in nghiêng
        response = response.replace('**', '').replace('*', '')
        
        return JsonResponse({
            'success': True,
            'response': response
        })
    
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Dữ liệu JSON không hợp lệ'
        }, status=400)
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

# Debug view to directly test asset retrieval 
@login_required
def debug_assets(request):
    """Debug view to directly test asset retrieval"""
    # Get all assets
    all_assets = Asset.objects.all()
    
    # Create a simple context
    context = {
        'assets': all_assets,
        'assets_count': all_assets.count(),
        'portfolios': Portfolio.objects.filter(user=request.user),
    }
    
    # Log to console
    print(f"DEBUG: Found {all_assets.count()} assets in database")
    for asset in all_assets:
        print(f"  - Asset: {asset.id} | {asset.symbol} | {asset.name}")
    
    return render(request, 'portfolio/debug_assets.html', context)

@login_required
def sync_assets(request):
    """View to synchronize assets from VNStock to the database"""
    if request.method == 'POST' or request.method == 'GET':  # Allow both GET and POST
        try:
            result = sync_vnstock_to_assets()
            
            if isinstance(result, dict):
                messages.success(
                    request, 
                    f"Đồng bộ thành công! Đã thêm {result['created']} cổ phiếu mới, cập nhật {result['updated']} cổ phiếu. Bây giờ bạn có thể mua/bán những cổ phiếu này."
                )
            else:
                messages.error(request, "Đồng bộ không thành công, không có cổ phiếu nào được thêm.")
        except Exception as e:
            messages.error(request, f"Lỗi khi đồng bộ dữ liệu: {str(e)}")
    
    # Check if the request came from the market page
    referer = request.META.get('HTTP_REFERER', '')
    if 'market' in referer:
        return redirect('market')
    else:
        return redirect('debug_assets')

@login_required
def update_stock_prices(request):
    """View to update current stock prices"""
    if request.method == 'POST':
        try:
            # Call the function to fetch and update prices
            snapshot_df = fetch_stock_prices_snapshot()
            
            if snapshot_df is not None:
                # Count non-null prices
                non_null_prices = sum(1 for col in snapshot_df.columns if col != 'time' and snapshot_df[col].iloc[0] is not None)
                messages.success(
                    request, 
                    f"Cập nhật giá thành công! Đã cập nhật giá cho {non_null_prices} cổ phiếu."
                )
            else:
                messages.error(request, "Không thể cập nhật giá cổ phiếu.")
        except Exception as e:
            messages.error(request, f"Lỗi khi cập nhật giá: {str(e)}")
    
    return redirect('debug_assets')

@login_required
def get_stock_symbols(request):
    """API view để lấy danh sách mã cổ phiếu phù hợp với từ khóa tìm kiếm"""
    term = request.GET.get('term', '')
    
    # Tìm kiếm cổ phiếu phù hợp với từ khóa
    assets = Asset.objects.filter(symbol__istartswith=term)[:10]  # Giới hạn 10 kết quả
    
    # Trả về danh sách các mã cổ phiếu
    symbols = [asset.symbol for asset in assets]
    
    return JsonResponse(symbols, safe=False)

@login_required
def get_stock_price(request, symbol):
    """
    API endpoint để lấy giá cổ phiếu hiện tại và giá gợi ý mua/bán.
    """
    try:
        import random

        # Tìm cổ phiếu trong cơ sở dữ liệu
        asset = Asset.objects.filter(symbol=symbol).first()
        if asset:
            # Lấy giá từ cơ sở dữ liệu
            match_price = float(asset.current_price)
            
            # Tạo giá trị giả lập cho biến động giá
            change_percent = random.uniform(-2, 2)
            
            # Tính giá mua/bán: giá mua thấp hơn 0.5%, giá bán cao hơn 0.5%
            buy_price = round(match_price * 0.995)
            sell_price = round(match_price * 1.005)
            
            # Chuẩn bị dữ liệu phản hồi
            response_data = {
                'success': True,
                'symbol': symbol,
                'price': match_price,
                'change_percent': change_percent,
                'buy_price': buy_price,
                'sell_price': sell_price,
                'source': 'database'
            }
            
            # Trả về phản hồi JSON
            return JsonResponse(response_data)
        else:
            # Không tìm thấy cổ phiếu trong cơ sở dữ liệu
            return JsonResponse({
                'success': False,
                'error': f'Không tìm thấy mã cổ phiếu {symbol}'
            }, status=404)
    except Exception as e:
        # Xử lý lỗi
        print(f"ERROR in get_stock_price: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)