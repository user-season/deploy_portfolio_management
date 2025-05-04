from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User, Portfolio, Transaction, Asset



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