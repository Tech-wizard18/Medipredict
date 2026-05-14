from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordResetForm as DjangoPasswordResetForm
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import User

class UserRegistrationForm(UserCreationForm):
    """Form for user registration"""
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address'
        })
    )
    
    first_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First Name'
        })
    )
    
    last_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last Name'
        })
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Choose a username'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Create a password'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Confirm password'})
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('A user with this email already exists.')
        return email
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise ValidationError('This username is already taken.')
        return username


class UserLoginForm(AuthenticationForm):
    """Form for user login"""
    
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username or Email'
        })
    )
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        })
    )
    
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        
        if username and password:
            # Try to authenticate with username
            user = authenticate(username=username, password=password)
            
            # If authentication fails, try with email
            if user is None:
                try:
                    user_obj = User.objects.get(email=username)
                    user = authenticate(username=user_obj.username, password=password)
                except User.DoesNotExist:
                    user = None
            
            if user is None:
                raise ValidationError('Invalid username/email or password.')
            
            if not user.is_active:
                raise ValidationError('This account is inactive.')
            
            self.cleaned_data['user'] = user
        
        return self.cleaned_data


class UserProfileForm(forms.ModelForm):
    """Form for updating user profile"""
    
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'email', 'phone_number',
            'date_of_birth', 'gender', 'profile_picture'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'date_of_birth': forms.DateInput(
                attrs={
                    'class': 'form-control',
                    'type': 'date',
                    'max': timezone.now().date().isoformat()
                }
            ),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'}),
        }
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError('This email is already registered with another account.')
        return email
    
    def clean_date_of_birth(self):
        dob = self.cleaned_data.get('date_of_birth')
        if dob and dob > timezone.now().date():
            raise ValidationError('Date of birth cannot be in the future.')
        return dob
    
    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        if phone and not phone.replace('+', '').replace(' ', '').replace('-', '').isdigit():
            raise ValidationError('Enter a valid phone number.')
        return phone


class UserMedicalProfileForm(forms.ModelForm):
    """Form for medical profile information"""
    
    class Meta:
        model = User
        fields = [
            'blood_group', 'height', 'weight',
            'has_diabetes', 'has_hypertension', 
            'has_heart_disease', 'has_kidney_disease', 
            'has_liver_disease', 'family_history',
            'smokes', 'drinks_alcohol', 'exercise_frequency'
        ]
        widgets = {
            'blood_group': forms.Select(attrs={'class': 'form-select'}),
            'height': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Height in cm',
                'step': '0.1',
                'min': '50',
                'max': '250'
            }),
            'weight': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Weight in kg',
                'step': '0.1',
                'min': '20',
                'max': '300'
            }),
            'has_diabetes': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_hypertension': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_heart_disease': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_kidney_disease': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_liver_disease': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'family_history': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Any family history of diseases...'
            }),
            'smokes': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'drinks_alcohol': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'exercise_frequency': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def clean_height(self):
        height = self.cleaned_data.get('height')
        if height and (height < 50 or height > 250):
            raise ValidationError('Height must be between 50 and 250 cm.')
        return height
    
    def clean_weight(self):
        weight = self.cleaned_data.get('weight')
        if weight and (weight < 20 or weight > 300):
            raise ValidationError('Weight must be between 20 and 300 kg.')
        return weight


class PasswordResetRequestForm(forms.Form):
    """Form for requesting password reset"""
    
    email = forms.EmailField(
        max_length=254,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address'
        })
    )


class PasswordResetForm(forms.Form):
    """Form for resetting password"""
    
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'New password'
        }),
        min_length=8,
        help_text="Password must be at least 8 characters long."
    )
    
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new password'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if password and confirm_password and password != confirm_password:
            raise ValidationError("Passwords don't match.")
        
        return cleaned_data