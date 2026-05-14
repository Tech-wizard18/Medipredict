from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json
import uuid
from datetime import timedelta

from .models import User, UserActivity, EmailVerification, PasswordResetToken
from .forms import (
    UserRegistrationForm, 
    UserLoginForm, 
    UserProfileForm,
    UserMedicalProfileForm,
    PasswordResetRequestForm,
    PasswordResetForm
)

def register_view(request):
    """User registration view"""
    if request.user.is_authenticated:
        return redirect('prediction_app:dashboard')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Create activity log
            UserActivity.objects.create(
                user=user,
                activity_type='login',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            # Log the user in
            login(request, user)
            
            # Send welcome email
            send_welcome_email(user)
            
            # Send email verification
            send_verification_email(user, request)
            
            messages.success(request, 'Registration successful! Welcome to MEDIPREDICT.')
            return redirect('users_app:profile_setup')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'users_app/register.html', {'form': form})


def login_view(request):
    """User login view"""
    if request.user.is_authenticated:
        return redirect('prediction_app:dashboard')
    
    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                login(request, user)
                
                # Create activity log
                UserActivity.objects.create(
                    user=user,
                    activity_type='login',
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
                
                # Update last login
                user.last_login = timezone.now()
                user.save(update_fields=['last_login'])
                
                messages.success(request, f'Welcome back, {user.first_name or user.username}!')
                
                # Redirect to next page if specified
                next_page = request.GET.get('next')
                if next_page:
                    return redirect(next_page)
                return redirect('prediction_app:dashboard')
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = UserLoginForm()
    
    return render(request, 'users_app/login.html', {'form': form})


@login_required
def logout_view(request):
    """User logout view"""
    # Create activity log
    UserActivity.objects.create(
        user=request.user,
        activity_type='logout',
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
    
    logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('users_app:login')


@login_required
def profile_view(request):
    """User profile view"""
    user = request.user
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            
            # Create activity log
            UserActivity.objects.create(
                user=user,
                activity_type='profile_update',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                details={'fields_updated': list(form.changed_data)}
            )
            
            messages.success(request, 'Profile updated successfully!')
            return redirect('users_app:profile')
    else:
        form = UserProfileForm(instance=user)
    
    # Get user activities
    activities = UserActivity.objects.filter(user=user).order_by('-timestamp')[:10]
    
    context = {
        'form': form,
        'user': user,
        'activities': activities,
        'bmi': user.bmi,
        'bmi_category': user.bmi_category,
        'age': user.age,
        'medical_conditions': user.get_medical_conditions()
    }
    
    return render(request, 'users_app/profile.html', context)


@login_required
def profile_setup_view(request):
    """Initial profile setup after registration"""
    user = request.user
    
    if request.method == 'POST':
        medical_form = UserMedicalProfileForm(request.POST, instance=user)
        if medical_form.is_valid():
            medical_form.save()
            messages.success(request, 'Profile setup completed successfully!')
            return redirect('prediction_app:dashboard')
    else:
        medical_form = UserMedicalProfileForm(instance=user)
    
    return render(request, 'users_app/profile_setup.html', {'form': medical_form})


@login_required
def change_password_view(request):
    """Change password view"""
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            
            # Create activity log
            UserActivity.objects.create(
                user=user,
                activity_type='password_change',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            # Update session to prevent logout
            update_session_auth_hash(request, user)
            
            messages.success(request, 'Your password was successfully updated!')
            return redirect('users_app:profile')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'users_app/change_password.html', {'form': form})


def password_reset_request_view(request):
    """Password reset request view"""
    if request.user.is_authenticated:
        return redirect('prediction_app:dashboard')
    
    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(email=email)
                # Create password reset token
                token = str(uuid.uuid4())
                expires_at = timezone.now() + timedelta(hours=24)
                
                PasswordResetToken.objects.create(
                    user=user,
                    token=token,
                    expires_at=expires_at
                )
                
                # Send password reset email
                reset_url = request.build_absolute_uri(
                    f'/users/password-reset/{token}/'
                )
                
                send_password_reset_email(user, reset_url)
                
                messages.success(request, 
                    'Password reset instructions have been sent to your email. '
                    'Please check your inbox.'
                )
                return redirect('users_app:login')
            except User.DoesNotExist:
                # Don't reveal that user doesn't exist
                messages.success(request, 
                    'If your email is registered, you will receive reset instructions.'
                )
                return redirect('users_app:login')
    else:
        form = PasswordResetRequestForm()
    
    return render(request, 'users_app/password_reset.html', {'form': form})


def password_reset_view(request, token):
    """Password reset view with token"""
    if request.user.is_authenticated:
        return redirect('prediction_app:dashboard')
    
    try:
        reset_token = PasswordResetToken.objects.get(
            token=token,
            used=False,
            expires_at__gt=timezone.now()
        )
    except PasswordResetToken.DoesNotExist:
        messages.error(request, 'Invalid or expired password reset link.')
        return redirect('users_app:password_reset_request')
    
    if request.method == 'POST':
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            # Update user password
            user = reset_token.user
            user.set_password(form.cleaned_data['new_password'])
            user.save()
            
            # Mark token as used
            reset_token.used = True
            reset_token.save()
            
            # Create activity log
            UserActivity.objects.create(
                user=user,
                activity_type='password_change',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                details={'via': 'password_reset'}
            )
            
            messages.success(request, 
                'Your password has been reset successfully. You can now login with your new password.'
            )
            return redirect('users_app:login')
    else:
        form = PasswordResetForm()
    
    return render(request, 'users_app/password_reset.html', {
        'form': form,
        'token': token
    })


def verify_email_view(request, token):
    """Email verification view"""
    try:
        verification = EmailVerification.objects.get(
            token=token,
            expires_at__gt=timezone.now(),
            verified=False
        )
        user = verification.user
        user.email_verified = True
        user.save()
        
        verification.verified = True
        verification.save()
        
        messages.success(request, 'Your email has been verified successfully!')
        
    except EmailVerification.DoesNotExist:
        messages.error(request, 'Invalid or expired verification link.')
    
    return redirect('users_app:profile' if request.user.is_authenticated else 'users_app:login')


@login_required
def resend_verification_email_view(request):
    """Resend verification email"""
    user = request.user
    if not user.email_verified:
        send_verification_email(user, request)
        messages.success(request, 'Verification email has been sent. Please check your inbox.')
    else:
        messages.info(request, 'Your email is already verified.')
    
    return redirect('users_app:profile')


@login_required
@require_http_methods(['POST'])
def update_notification_settings(request):
    """Update user notification settings (AJAX)"""
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            data = json.loads(request.body)
            user = request.user
            
            if 'email_notifications' in data:
                user.email_notifications = data['email_notifications']
            if 'sms_notifications' in data:
                user.sms_notifications = data['sms_notifications']
            if 'dark_mode' in data:
                user.dark_mode = data['dark_mode']
            
            user.save()
            
            # Create activity log
            UserActivity.objects.create(
                user=user,
                activity_type='account_settings_changed',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                details={'settings_updated': list(data.keys())}
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Settings updated successfully'
            })
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'message': 'Invalid data format'
            }, status=400)
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request'
    }, status=400)


@login_required
def delete_account_view(request):
    """Delete user account"""
    if request.method == 'POST':
        user = request.user
        logout(request)
        user.delete()
        messages.success(request, 'Your account has been deleted successfully.')
        return redirect('home')
    
    return render(request, 'users_app/delete_account_confirm.html')


# Helper functions
def send_welcome_email(user):
    """Send welcome email to new user"""
    subject = 'Welcome to MEDIPREDICT!'
    html_message = render_to_string('users_app/emails/welcome_email.html', {
        'user': user,
        'site_name': 'MEDIPREDICT'
    })
    plain_message = strip_tags(html_message)
    
    send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_message,
        fail_silently=True
    )


def send_verification_email(user, request):
    """Send email verification link"""
    # Delete any existing unverified tokens
    EmailVerification.objects.filter(user=user, verified=False).delete()
    
    # Create new verification token
    token = str(uuid.uuid4())
    expires_at = timezone.now() + timedelta(days=7)
    
    EmailVerification.objects.create(
        user=user,
        token=token,
        expires_at=expires_at
    )
    
    # Build verification URL
    verification_url = request.build_absolute_uri(
        f'/users/verify-email/{token}/'
    )
    
    subject = 'Verify Your Email - MEDIPREDICT'
    html_message = render_to_string('users_app/emails/verification_email.html', {
        'user': user,
        'verification_url': verification_url,
        'expires_in_days': 7
    })
    plain_message = strip_tags(html_message)
    
    send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_message,
        fail_silently=True
    )


def send_password_reset_email(user, reset_url):
    """Send password reset email"""
    subject = 'Password Reset Request - MEDIPREDICT'
    html_message = render_to_string('users_app/emails/password_reset_email.html', {
        'user': user,
        'reset_url': reset_url,
        'expires_in_hours': 24
    })
    plain_message = strip_tags(html_message)
    
    send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_message,
        fail_silently=True
    )