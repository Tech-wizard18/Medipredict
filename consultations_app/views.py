from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg
from django.utils import timezone
from django.conf import settings
import json
from datetime import datetime, timedelta

from .models import (
    Doctor, Specialization, Consultation, ConsultationSlot,
    ConsultationMessage, Prescription, PrescriptionItem,
    Review, Billing, Notification
)
from .forms import (
    DoctorRegistrationForm, ConsultationBookingForm,
    ConsultationMessageForm, ReviewForm, PrescriptionForm,
    PrescriptionItemFormSet, ConsultationUpdateForm
)


@login_required
def doctor_list_view(request):
    """Display list of available doctors"""
    specialization_id = request.GET.get('specialization')
    search_query = request.GET.get('search', '')
    
    doctors = Doctor.objects.filter(is_verified=True, is_available=True)
    
    if specialization_id:
        doctors = doctors.filter(specialization_id=specialization_id)
    
    if search_query:
        doctors = doctors.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(specialization__name__icontains=search_query) |
            Q(hospital_name__icontains=search_query)
        )
    
    # Sort options
    sort_by = request.GET.get('sort', 'rating')
    if sort_by == 'rating':
        doctors = doctors.order_by('-average_rating')
    elif sort_by == 'experience':
        doctors = doctors.order_by('-years_of_experience')
    elif sort_by == 'fee_low':
        doctors = doctors.order_by('consultation_fee')
    elif sort_by == 'fee_high':
        doctors = doctors.order_by('-consultation_fee')
    
    # Pagination
    paginator = Paginator(doctors, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    specializations = Specialization.objects.all()
    
    context = {
        'page_obj': page_obj,
        'specializations': specializations,
        'selected_specialization': specialization_id,
        'search_query': search_query,
        'sort_by': sort_by,
    }
    
    return render(request, 'consultations_app/doctor_list.html', context)


@login_required
def doctor_detail_view(request, doctor_id):
    """Display doctor details and available slots"""
    doctor = get_object_or_404(Doctor, id=doctor_id, is_verified=True)
    
    # Get available slots for next 7 days
    start_date = timezone.now()
    end_date = start_date + timedelta(days=7)
    
    available_slots = doctor.available_slots.filter(
        start_time__range=[start_date, end_date]
    ).order_by('start_time')
    
    # Group slots by date
    slots_by_date = {}
    for slot in available_slots:
        date_str = slot.start_time.strftime('%Y-%m-%d')
        if date_str not in slots_by_date:
            slots_by_date[date_str] = []
        slots_by_date[date_str].append(slot)
    
    # Get doctor reviews
    reviews = Review.objects.filter(doctor=doctor).order_by('-created_at')[:5]
    
    # Check if user has upcoming consultation with this doctor
    has_upcoming = Consultation.objects.filter(
        patient=request.user,
        doctor=doctor,
        status__in=['confirmed', 'pending']
    ).exists()
    
    context = {
        'doctor': doctor,
        'slots_by_date': slots_by_date,
        'reviews': reviews,
        'has_upcoming': has_upcoming,
        'today': timezone.now().date().isoformat(),
    }
    
    return render(request, 'consultations_app/doctor_detail.html', context)


@login_required
def book_consultation_view(request, doctor_id):
    """Book a consultation with a doctor"""
    doctor = get_object_or_404(Doctor, id=doctor_id, is_verified=True, is_available=True)
    
    if request.method == 'POST':
        form = ConsultationBookingForm(request.POST, doctor=doctor, patient=request.user)
        if form.is_valid():
            consultation = form.save(commit=False)
            consultation.patient = request.user
            consultation.doctor = doctor
            consultation.consultation_fee = doctor.consultation_fee
            consultation.save()
            
            # Create billing record
            Billing.objects.create(
                consultation=consultation,
                amount=doctor.consultation_fee,
                tax_amount=0,
                total_amount=doctor.consultation_fee,
                payment_status='pending'
            )
            
            # Create notification for doctor
            Notification.objects.create(
                user=doctor.user,
                notification_type='consultation_booked',
                message=f"New consultation booked by {request.user.get_full_name()}",
                consultation=consultation
            )
            
            # Create notification for patient
            Notification.objects.create(
                user=request.user,
                notification_type='consultation_booked',
                message=f"Your consultation with Dr. {doctor.user.get_full_name()} has been booked",
                consultation=consultation
            )
            
            messages.success(request, 'Consultation booked successfully!')
            return redirect('consultation_detail', consultation_id=consultation.id)
    else:
        slot_id = request.GET.get('slot_id')
        initial = {'slot': slot_id} if slot_id else {}
        form = ConsultationBookingForm(doctor=doctor, patient=request.user, initial=initial)
    
    context = {
        'doctor': doctor,
        'form': form,
    }
    
    return render(request, 'consultations_app/book_consultation.html', context)


@login_required
def consultation_detail_view(request, consultation_id):
    """View consultation details"""
    consultation = get_object_or_404(
        Consultation.objects.select_related('patient', 'doctor__user', 'slot'),
        id=consultation_id,
        patient=request.user
    )
    
    # Get messages
    messages_list = ConsultationMessage.objects.filter(
        consultation=consultation
    ).select_related('sender').order_by('timestamp')
    
    # Get prescription if exists
    prescription = getattr(consultation, 'detailed_prescription', None)
    
    # Get billing info
    billing = getattr(consultation, 'billing', None)
    
    # Get review if exists
    review = getattr(consultation, 'review', None)
    
    context = {
        'consultation': consultation,
        'messages': messages_list,
        'prescription': prescription,
        'billing': billing,
        'review': review,
        'is_doctor': False,
    }
    
    return render(request, 'consultations_app/consultation_detail.html', context)


@login_required
def doctor_consultation_detail_view(request, consultation_id):
    """Doctor's view of consultation details"""
    if not hasattr(request.user, 'doctor_profile'):
        messages.error(request, 'Access denied. Doctor profile required.')
        return redirect('dashboard')
    
    consultation = get_object_or_404(
        Consultation.objects.select_related('patient', 'doctor__user', 'slot'),
        id=consultation_id,
        doctor=request.user.doctor_profile
    )
    
    # Get messages
    messages_list = ConsultationMessage.objects.filter(
        consultation=consultation
    ).select_related('sender').order_by('timestamp')
    
    # Get prescription if exists
    prescription = getattr(consultation, 'detailed_prescription', None)
    
    # Forms
    if request.method == 'POST':
        if 'update_status' in request.POST:
            status_form = ConsultationUpdateForm(request.POST, instance=consultation)
            if status_form.is_valid():
                consultation = status_form.save()
                messages.success(request, 'Consultation status updated.')
                return redirect('doctor_consultation_detail', consultation_id=consultation.id)
        elif 'send_message' in request.POST:
            message_form = ConsultationMessageForm(request.POST, request.FILES)
            if message_form.is_valid():
                message = message_form.save(commit=False)
                message.consultation = consultation
                message.sender = request.user
                message.save()
                
                # Create notification for patient
                Notification.objects.create(
                    user=consultation.patient,
                    notification_type='message_received',
                    message=f"New message from Dr. {request.user.get_full_name()}",
                    consultation=consultation
                )
                
                messages.success(request, 'Message sent.')
                return redirect('doctor_consultation_detail', consultation_id=consultation.id)
    else:
        status_form = ConsultationUpdateForm(instance=consultation)
        message_form = ConsultationMessageForm()
    
    context = {
        'consultation': consultation,
        'messages': messages_list,
        'prescription': prescription,
        'status_form': status_form,
        'message_form': message_form,
        'is_doctor': True,
    }
    
    return render(request, 'consultations_app/doctor_consultation_detail.html', context)


@login_required
def send_message_view(request, consultation_id):
    """Send a message in consultation chat"""
    if request.method == 'POST':
        consultation = get_object_or_404(Consultation, id=consultation_id)
        
        # Check if user is part of this consultation
        if request.user not in [consultation.patient, consultation.doctor.user]:
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        form = ConsultationMessageForm(request.POST, request.FILES)
        if form.is_valid():
            message = form.save(commit=False)
            message.consultation = consultation
            message.sender = request.user
            message.save()
            
            # Create notification for other party
            other_user = consultation.patient if request.user == consultation.doctor.user else consultation.doctor.user
            Notification.objects.create(
                user=other_user,
                notification_type='message_received',
                message=f"New message from {request.user.get_full_name()}",
                consultation=consultation
            )
            
            return JsonResponse({
                'success': True,
                'message_id': message.id,
                'sender_name': request.user.get_full_name(),
                'timestamp': message.timestamp.strftime('%Y-%m-%d %H:%M'),
                'message': message.message,
            })
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required
def my_consultations_view(request):
    """View user's consultations"""
    consultations = Consultation.objects.filter(
        patient=request.user
    ).select_related('doctor__user', 'slot').order_by('-booked_at')
    
    # Filter by status
    status_filter = request.GET.get('status', 'all')
    if status_filter != 'all':
        consultations = consultations.filter(status=status_filter)
    
    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        consultations = consultations.filter(
            Q(doctor__user__first_name__icontains=search_query) |
            Q(doctor__user__last_name__icontains=search_query) |
            Q(consultation_id__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(consultations, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'search_query': search_query,
        'status_counts': {
            'all': Consultation.objects.filter(patient=request.user).count(),
            'pending': Consultation.objects.filter(patient=request.user, status='pending').count(),
            'confirmed': Consultation.objects.filter(patient=request.user, status='confirmed').count(),
            'in_progress': Consultation.objects.filter(patient=request.user, status='in_progress').count(),
            'completed': Consultation.objects.filter(patient=request.user, status='completed').count(),
            'cancelled': Consultation.objects.filter(patient=request.user, status='cancelled').count(),
        }
    }
    
    return render(request, 'consultations_app/my_consultations.html', context)


@login_required
def doctor_consultations_view(request):
    """View doctor's consultations"""
    if not hasattr(request.user, 'doctor_profile'):
        messages.error(request, 'Access denied. Doctor profile required.')
        return redirect('dashboard')
    
    consultations = Consultation.objects.filter(
        doctor=request.user.doctor_profile
    ).select_related('patient', 'slot').order_by('-booked_at')
    
    # Filter by status
    status_filter = request.GET.get('status', 'all')
    if status_filter != 'all':
        consultations = consultations.filter(status=status_filter)
    
    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        consultations = consultations.filter(
            Q(patient__first_name__icontains=search_query) |
            Q(patient__last_name__icontains=search_query) |
            Q(consultation_id__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(consultations, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'search_query': search_query,
        'status_counts': {
            'all': Consultation.objects.filter(doctor=request.user.doctor_profile).count(),
            'pending': Consultation.objects.filter(doctor=request.user.doctor_profile, status='pending').count(),
            'confirmed': Consultation.objects.filter(doctor=request.user.doctor_profile, status='confirmed').count(),
            'in_progress': Consultation.objects.filter(doctor=request.user.doctor_profile, status='in_progress').count(),
            'completed': Consultation.objects.filter(doctor=request.user.doctor_profile, status='completed').count(),
            'cancelled': Consultation.objects.filter(doctor=request.user.doctor_profile, status='cancelled').count(),
        }
    }
    
    return render(request, 'consultations_app/doctor_consultations.html', context)


@login_required
def create_prescription_view(request, consultation_id):
    """Create prescription for consultation"""
    if not hasattr(request.user, 'doctor_profile'):
        messages.error(request, 'Access denied. Doctor profile required.')
        return redirect('dashboard')
    
    consultation = get_object_or_404(
        Consultation,
        id=consultation_id,
        doctor=request.user.doctor_profile,
        status__in=['in_progress', 'completed']
    )
    
    if hasattr(consultation, 'detailed_prescription'):
        messages.info(request, 'Prescription already exists.')
        return redirect('doctor_consultation_detail', consultation_id=consultation.id)
    
    if request.method == 'POST':
        form = PrescriptionForm(request.POST)
        formset = PrescriptionItemFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            prescription = form.save(commit=False)
            prescription.consultation = consultation
            prescription.doctor = request.user.doctor_profile
            prescription.patient = consultation.patient
            prescription.save()
            
            formset.instance = prescription
            formset.save()
            
            # Update consultation diagnosis
            consultation.diagnosis = prescription.diagnosis_summary
            consultation.prescription = prescription.instructions
            consultation.save()
            
            # Create notification for patient
            Notification.objects.create(
                user=consultation.patient,
                notification_type='prescription_ready',
                message=f"Prescription ready from Dr. {request.user.get_full_name()}",
                consultation=consultation
            )
            
            messages.success(request, 'Prescription created successfully.')
            return redirect('doctor_consultation_detail', consultation_id=consultation.id)
    else:
        form = PrescriptionForm()
        formset = PrescriptionItemFormSet()
    
    context = {
        'consultation': consultation,
        'form': form,
        'formset': formset,
    }
    
    return render(request, 'consultations_app/create_prescription.html', context)


@login_required
def submit_review_view(request, consultation_id):
    """Submit review for completed consultation"""
    consultation = get_object_or_404(
        Consultation,
        id=consultation_id,
        patient=request.user,
        status='completed'
    )
    
    if hasattr(consultation, 'review'):
        messages.info(request, 'You have already reviewed this consultation.')
        return redirect('consultation_detail', consultation_id=consultation.id)
    
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.consultation = consultation
            review.patient = request.user
            review.doctor = consultation.doctor
            review.save()
            
            messages.success(request, 'Thank you for your review!')
            return redirect('consultation_detail', consultation_id=consultation.id)
    else:
        form = ReviewForm()
    
    context = {
        'consultation': consultation,
        'form': form,
    }
    
    return render(request, 'consultations_app/submit_review.html', context)


@login_required
def doctor_dashboard_view(request):
    """Doctor's dashboard"""
    if not hasattr(request.user, 'doctor_profile'):
        messages.error(request, 'Access denied. Doctor profile required.')
        return redirect('dashboard')
    
    doctor = request.user.doctor_profile
    
    # Statistics
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    
    stats = {
        'total_consultations': Consultation.objects.filter(doctor=doctor).count(),
        'upcoming_consultations': Consultation.objects.filter(
            doctor=doctor,
            status='confirmed',
            slot__start_time__gt=timezone.now()
        ).count(),
        'today_consultations': Consultation.objects.filter(
            doctor=doctor,
            slot__start_time__date=today
        ).count(),
        'weekly_earnings': Billing.objects.filter(
            consultation__doctor=doctor,
            payment_status='paid',
            created_at__gte=week_ago
        ).aggregate(total=models.Sum('total_amount'))['total'] or 0,
    }
    
    # Recent consultations
    recent_consultations = Consultation.objects.filter(
        doctor=doctor
    ).select_related('patient').order_by('-booked_at')[:5]
    
    # Upcoming slots
    upcoming_slots = ConsultationSlot.objects.filter(
        doctor=doctor,
        start_time__gt=timezone.now(),
        is_booked=False
    ).order_by('start_time')[:10]
    
    # Recent reviews
    recent_reviews = Review.objects.filter(
        doctor=doctor
    ).select_related('patient').order_by('-created_at')[:5]
    
    context = {
        'doctor': doctor,
        'stats': stats,
        'recent_consultations': recent_consultations,
        'upcoming_slots': upcoming_slots,
        'recent_reviews': recent_reviews,
    }
    
    return render(request, 'consultations_app/doctor_dashboard.html', context)


@login_required
def manage_slots_view(request):
    """Doctor's slot management"""
    if not hasattr(request.user, 'doctor_profile'):
        messages.error(request, 'Access denied. Doctor profile required.')
        return redirect('dashboard')
    
    doctor = request.user.doctor_profile
    
    if request.method == 'POST':
        # Handle slot creation
        date_str = request.POST.get('date')
        start_time_str = request.POST.get('start_time')
        duration = int(request.POST.get('duration', 30))
        
        if date_str and start_time_str:
            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                start_time_obj = datetime.strptime(start_time_str, '%H:%M').time()
                
                start_datetime = timezone.make_aware(
                    datetime.combine(date_obj, start_time_obj)
                )
                end_datetime = start_datetime + timedelta(minutes=duration)
                
                # Check if slot overlaps with existing slots
                overlapping = ConsultationSlot.objects.filter(
                    doctor=doctor,
                    start_time__lt=end_datetime,
                    end_time__gt=start_datetime
                ).exists()
                
                if not overlapping:
                    ConsultationSlot.objects.create(
                        doctor=doctor,
                        start_time=start_datetime,
                        end_time=end_datetime,
                        duration_minutes=duration
                    )
                    messages.success(request, 'Slot added successfully.')
                else:
                    messages.error(request, 'Slot overlaps with existing slot.')
                
            except ValueError:
                messages.error(request, 'Invalid date or time format.')
    
    # Get slots for next 14 days
    start_date = timezone.now()
    end_date = start_date + timedelta(days=14)
    
    slots = ConsultationSlot.objects.filter(
        doctor=doctor,
        start_time__range=[start_date, end_date]
    ).order_by('start_time')
    
    # Group slots by date
    slots_by_date = {}
    for slot in slots:
        date_str = slot.start_time.strftime('%Y-%m-%d')
        if date_str not in slots_by_date:
            slots_by_date[date_str] = []
        slots_by_date[date_str].append(slot)
    
    context = {
        'doctor': doctor,
        'slots_by_date': slots_by_date,
        'today': timezone.now().date().isoformat(),
        'min_date': timezone.now().date().isoformat(),
        'max_date': (timezone.now().date() + timedelta(days=30)).isoformat(),
    }
    
    return render(request, 'consultations_app/manage_slots.html', context)


@login_required
@require_POST
def delete_slot_view(request, slot_id):
    """Delete a consultation slot"""
    if not hasattr(request.user, 'doctor_profile'):
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    slot = get_object_or_404(
        ConsultationSlot,
        id=slot_id,
        doctor=request.user.doctor_profile,
        is_booked=False
    )
    
    slot.delete()
    return JsonResponse({'success': True})


@login_required
def notifications_view(request):
    """View user notifications"""
    notifications = Notification.objects.filter(
        user=request.user
    ).select_related('consultation').order_by('-created_at')
    
    # Mark all as read
    notifications.filter(is_read=False).update(is_read=True)
    
    # Pagination
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
    }
    
    return render(request, 'consultations_app/notifications.html', context)


@login_required
@require_GET
def get_messages_view(request, consultation_id):
    """Get consultation messages (AJAX)"""
    consultation = get_object_or_404(Consultation, id=consultation_id)
    
    # Check if user is part of this consultation
    if request.user not in [consultation.patient, consultation.doctor.user]:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    messages_list = ConsultationMessage.objects.filter(
        consultation=consultation
    ).select_related('sender').order_by('timestamp')
    
    messages_data = []
    for msg in messages_list:
        messages_data.append({
            'id': msg.id,
            'sender': {
                'id': msg.sender.id,
                'name': msg.sender.get_full_name(),
                'is_current_user': msg.sender == request.user,
                'is_doctor': hasattr(msg.sender, 'doctor_profile'),
            },
            'message': msg.message,
            'attachment': msg.attachment.url if msg.attachment else None,
            'attachment_name': msg.attachment.name.split('/')[-1] if msg.attachment else None,
            'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M'),
            'is_read': msg.is_read,
        })
    
    return JsonResponse({'messages': messages_data})