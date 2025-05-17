from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum, F
from django.utils import timezone
from .models import (
    User, Portfolio, Assets, PortfolioSymbol, StockTransaction,
    Wallet, BankAccount, BankTransaction
)

# Đăng ký User vào admin
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'phone', 'date_joined', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_active', 'gender', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'phone')
    readonly_fields = ('date_joined', 'last_login')
    fieldsets = (
        ('Thông tin cá nhân', {'fields': ('username', 'email', 'first_name', 'last_name', 'password')}),
        ('Liên hệ', {'fields': ('phone', 'address')}),
        ('Thông tin khác', {'fields': ('gender', 'profile_picture', 'profile_picture_url')}),
        ('Auth0', {'fields': ('auth0_user_id',)}),
        ('Quyền hạn', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Thời gian', {'fields': ('date_joined', 'last_login')}),
    )

# Đăng ký Portfolio vào admin
class PortfolioSymbolInline(admin.TabularInline):
    model = PortfolioSymbol
    extra = 0
    readonly_fields = ('current_price', 'profit_loss')

@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'risk_tolerance', 'profit_loss_display', 'created_at')
    list_filter = ('risk_tolerance', 'created_at')
    search_fields = ('name', 'user__username', 'description')
    inlines = [PortfolioSymbolInline]
    
    def profit_loss_display(self, obj):
        value = obj.profit_loss
        color = "green" if value >= 0 else "red"
        return format_html('<span style="color: {};">{:,.0f} VND ({}%)</span>', 
                          color, value, round(obj.profit_loss_percentage, 2))
    profit_loss_display.short_description = "Lãi/Lỗ"

# Đăng ký Assets vào admin
@admin.register(Assets)
class AssetsAdmin(admin.ModelAdmin):
    list_display = ('symbol', 'user', 'current_price', 'average_price', 'profit_loss')
    list_filter = ('user',)
    search_fields = ('symbol', 'user__username')
    
    def profit_loss_display(self, obj):
        value = obj.profit_loss
        color = "green" if value >= 0 else "red"
        return format_html('<span style="color: {};">{:,.0f} VND</span>', color, value)
    profit_loss_display.short_description = "Lãi/Lỗ"

# Đăng ký PortfolioSymbol vào admin
@admin.register(PortfolioSymbol)
class PortfolioSymbolAdmin(admin.ModelAdmin):
    list_display = ('portfolio', 'symbol', 'quantity', 'average_price', 'current_price', 'profit_loss_display')
    list_filter = ('portfolio__user',)
    search_fields = ('symbol', 'portfolio__name')
    
    def profit_loss_display(self, obj):
        value = obj.profit_loss
        color = "green" if value >= 0 else "red"
        profit_percentage = 0
        if obj.quantity * obj.average_price > 0:
            profit_percentage = (value / (obj.quantity * obj.average_price)) * 100
        return format_html('<span style="color: {};">{:,.0f} VND ({}%)</span>', 
                          color, value, round(profit_percentage, 2))
    profit_loss_display.short_description = "Lãi/Lỗ"

# Đăng ký StockTransaction vào admin
@admin.register(StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_type', 'symbol', 'quantity', 'price', 'total_price', 'transaction_time')
    list_filter = ('transaction_type', 'transaction_time')
    search_fields = ('symbol', 'portfolio__name', 'portfolio__user__username')
    date_hierarchy = 'transaction_time'

# Đăng ký Wallet vào admin
@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance')
    search_fields = ('user__username', 'user__email')

# Đăng ký BankAccount vào admin
@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ('user', 'get_bank_name', 'account_name', 'account_number', 'is_default')
    list_filter = ('bank_name', 'is_default')
    search_fields = ('user__username', 'account_name', 'account_number')
    
    def get_bank_name(self, obj):
        if obj.bank_name == 'other' and obj.other_bank_name:
            return obj.other_bank_name
        return obj.get_bank_name_display()
    get_bank_name.short_description = "Ngân hàng"

# Đăng ký BankTransaction vào admin
@admin.register(BankTransaction)
class BankTransaction(admin.ModelAdmin):
    list_display = ('type', 'quantity', 'fee', 'status', 'transaction_time', 'completed_at')
    list_filter = ('type', 'status', 'transaction_time')
    search_fields = ('description', )
    readonly_fields = ('transaction_time', 'completed_at')
    date_hierarchy = 'transaction_time'
    
    actions = ['approve_transactions', 'reject_transactions']
    
    def approve_transactions(self, request, queryset):
        # Đếm giao dịch đã xử lý theo từng loại
        deposit_count = 0
        withdraw_count = 0
        
        # Chỉ xử lý các giao dịch đang chờ xử lý
        pending_transactions = queryset.filter(status='pending')
        
        for transaction in pending_transactions:
            transaction.status = 'completed'
            transaction.completed_at = timezone.now()
            transaction.save()
            
            # Lưu ý: Việc cập nhật số dư ví đã được xử lý trong phương thức save() của model
            deposit_count += 1 if transaction.type == 'deposit' else 0
            withdraw_count += 1 if transaction.type == 'withdraw' else 0
        
        message_parts = []
        if deposit_count > 0:
            message_parts.append(f"phê duyệt {deposit_count} giao dịch nạp tiền")
        if withdraw_count > 0:
            message_parts.append(f"phê duyệt {withdraw_count} giao dịch rút tiền")
        
        if message_parts:
            self.message_user(request, f"Đã {' và '.join(message_parts)} thành công.")
        else:
            self.message_user(request, "Không có giao dịch nào được xử lý.")
            
    approve_transactions.short_description = "Phê duyệt giao dịch đã chọn"
    
    def reject_transactions(self, request, queryset):
        # Chỉ xử lý các giao dịch đang chờ xử lý
        count = queryset.filter(status='pending').update(
            status='failed',
            description=F('description') + " | Từ chối bởi quản trị viên."
        )
        self.message_user(request, f"Đã từ chối {count} giao dịch.")
    reject_transactions.short_description = "Từ chối giao dịch đã chọn"