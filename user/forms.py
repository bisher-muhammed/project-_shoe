from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User



class RegistrationForm(UserCreationForm):
    email =forms.EmailField(max_length=60,help_text='Required. Add a valid email address')
    
    
    class Meta:
        model = User # Use the built-in User model
        fields = ['username', 'email', 'password1', 'password2']

