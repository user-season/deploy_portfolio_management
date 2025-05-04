from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User, Portfolio, Transaction, Asset, BankAccount, WalletTransaction



class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField()
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']


class PortfolioForm(forms.ModelForm):
    class Meta:
        model = Portfolio
        fields = ['name', 'description', 'investment_goal', 'target_value', 'risk_tolerance']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nhập tên danh mục đầu tư'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Mô tả về danh mục đầu tư của bạn'
            }),
            'investment_goal': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ví dụ: Tăng trưởng dài hạn, Thu nhập cổ tức...'
            }),
            'target_value': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '1000000'
            }),
            'risk_tolerance': forms.Select(attrs={
                'class': 'form-control'
            })
        }
        
    def clean_target_value(self):
        target_value = self.cleaned_data.get('target_value')
        if target_value < 0:
            raise forms.ValidationError("Giá trị mục tiêu không thể là số âm")
        return target_value

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if len(name) < 3:
            raise forms.ValidationError("Tên danh mục phải có ít nhất 3 ký tự")
        return name
    

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['portfolio', 'asset', 'transaction_type', 'quantity', 'price', 'transaction_date', 'notes']
        widgets = {
            'transaction_date': forms.DateTimeInput(
                attrs={'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M'
            ),
            'notes': forms.Textarea(attrs={'rows': 3}),
            'portfolio': forms.HiddenInput(),
            'asset': forms.Select(attrs={
                'class': 'form-select',
                'required': True,
                'id': 'id_asset',
                'placeholder': 'Chọn mã cổ phiếu'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'initial' in kwargs and 'portfolio' in kwargs['initial']:
            portfolio = kwargs['initial']['portfolio']
            if kwargs['initial'].get('transaction_type') == 'sell':
                # Chỉ hiển thị các tài sản có trong danh mục khi bán
                self.fields['asset'].queryset = Asset.objects.filter(
                    portfolioasset__portfolio=portfolio,
                    portfolioasset__quantity__gt=0
                ).distinct()
            else:
                self.fields['asset'].queryset = Asset.objects.all()

    def clean(self):
        cleaned_data = super().clean()
        quantity = cleaned_data.get('quantity')
        price = cleaned_data.get('price')
        
        if quantity and quantity <= 0:
            raise forms.ValidationError('Số lượng phải lớn hơn 0')
        
        if price and price <= 0:
            raise forms.ValidationError('Giá phải lớn hơn 0')
        
        return cleaned_data
    

class AssetForm(forms.ModelForm):
    class Meta:
        model = Asset
        fields = ['symbol', 'name', 'type', 'sector', 'description', 'current_price']

class DepositForm(forms.Form):
    amount = forms.DecimalField(
        label="Số tiền muốn nạp",
        min_value=50000,
        max_digits=15,
        decimal_places=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Nhập số tiền muốn nạp',
            'min': '50000',
            'step': '50000'
        })
    )
    
    payment_method = forms.ChoiceField(
        label="Phương thức thanh toán",
        choices=WalletTransaction.PAYMENT_METHOD_CHOICES,
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input'
        })
    )
    
    bank_account = forms.ModelChoiceField(
        label="Tài khoản ngân hàng",
        queryset=BankAccount.objects.none(),
        required=False,
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input'
        })
    )
    
    agree_terms = forms.BooleanField(
        label="Tôi đồng ý với điều khoản nạp tiền",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'agreeTerms'
        })
    )
    
    # Các trường cho tài khoản ngân hàng mới
    new_bank_name = forms.ChoiceField(
        label="Ngân hàng",
        choices=BankAccount.BANK_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'bankName'
        })
    )
    
    new_other_bank_name = forms.CharField(
        label="Tên ngân hàng khác",
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'id': 'otherBankName',
            'placeholder': 'Nhập tên ngân hàng'
        })
    )
    
    new_account_name = forms.CharField(
        label="Chủ tài khoản",
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'id': 'accountName',
            'placeholder': 'Nhập tên chủ tài khoản'
        })
    )
    
    new_account_number = forms.CharField(
        label="Số tài khoản",
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'id': 'accountNumber',
            'placeholder': 'Nhập số tài khoản'
        })
    )
    
    new_branch = forms.CharField(
        label="Chi nhánh",
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'id': 'branch',
            'placeholder': 'Nhập chi nhánh (không bắt buộc)'
        })
    )
    
    new_is_default = forms.BooleanField(
        label="Đặt làm tài khoản mặc định",
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'defaultAccount'
        })
    )
    
    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['bank_account'].queryset = BankAccount.objects.filter(user=user).order_by('-is_default')
        self.user = user
        
    def clean(self):
        cleaned_data = super().clean()
        payment_method = cleaned_data.get('payment_method')
        bank_account = cleaned_data.get('bank_account')
        
        # Nếu phương thức thanh toán là chuyển khoản ngân hàng,
        # cần có tài khoản ngân hàng hoặc thông tin tài khoản mới
        if payment_method == 'bank_transfer' and not bank_account:
            # Kiểm tra xem đã nhập đủ thông tin tài khoản mới chưa
            new_bank_name = cleaned_data.get('new_bank_name')
            new_account_name = cleaned_data.get('new_account_name')
            new_account_number = cleaned_data.get('new_account_number')
            
            if not (new_bank_name and new_account_name and new_account_number):
                if BankAccount.objects.filter(user=self.user).exists():
                    self.add_error('bank_account', 'Vui lòng chọn tài khoản ngân hàng')
                else:
                    self.add_error(None, 'Vui lòng thêm thông tin tài khoản ngân hàng')
        
        return cleaned_data