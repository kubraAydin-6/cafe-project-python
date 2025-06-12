from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import Musteri

class GarsonLoginForm(AuthenticationForm):
    username = forms.EmailField(label='Email', widget=forms.EmailInput(attrs={'class': 'form-control'}))
    password = forms.CharField(label='Şifre', widget=forms.PasswordInput(attrs={'class': 'form-control'}))

class MusteriOturumForm(forms.ModelForm):
    class Meta:
        model = Musteri
        fields = ['isim', 'masa_no']
        widgets = {
            'isim': forms.TextInput(attrs={'class': 'form-control'}),
            'masa_no': forms.NumberInput(attrs={'class': 'form-control'})
        } 