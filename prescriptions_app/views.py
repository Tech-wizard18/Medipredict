from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST, require_GET
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum, F
from django.utils import timezone
from django.conf import settings
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.db import transaction
import json
from datetime import datetime, timedelta
import pdfkit
import csv

from .models import (
    Prescription, PrescriptionItem, Medicine, RefillRequest,
    MedicationHistory, DrugInteraction, Pharmacy, PrescriptionAlert
)
from .forms import (
    PrescriptionForm, PrescriptionItemFormSet,
    RefillRequestForm, MedicineForm, DrugInteractionForm,
    PharmacyForm, PrescriptionSearchForm
)


@login_required
def prescription_list_view(request):
    """List all prescriptions for the user"""
    user = request.user
    is_doctor = hasattr(user, 'doctor_profile')
    
    if is_doctor:
        prescriptions = Prescription.objects.filter(doctor=user)
    else:
        prescriptions = Prescription.objects.filter(patient=user)
    
    # Filter by status
    status_filter = request.GET.get('status', 'all')
    if status_filter != 'all':
        prescriptions = prescriptions.filter(status=status_filter)
    
    # Search
    search_form = PrescriptionSearchForm(request.GET)
    if search_form.is_valid():
        search_query = search_form.cleaned_data.get('search_query')
        if search_query:
            prescriptions = prescriptions.filter(
                Q(prescription_id__icontains=search_query) |
                Q(diagnosis__icontains=search_query) |
                Q(notes__icontains=search_query) |
                Q(items__medicine__name__icontains=search_query)
            ).distinct()
    
    # Sort
    sort_by = request.GET.get('sort', '-issue_date')
    prescriptions = prescriptions.order_by(sort_by)
    
    # Pagination
    paginator = Paginator(prescriptions, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'is_doctor': is_doctor,
        'status_filter': status_filter,
        'search_form': search_form,
        'sort_by': sort_by,
        'status_counts': {
            'all': prescriptions.count(),
            'active': prescriptions.filter(status='active').count(),
            'completed': prescriptions.filter(status='completed').count(),
            'expired': prescriptions.filter(status='expired').count(),
        }
    }
    
    return render(request, 'prescriptions_app/prescription_list.html', context)


@login_required
def prescription_detail_view(request, prescription_id):
    """View prescription details"""
    prescription = get_object_or_404(Prescription, pk=prescription_id)
    
    # Check permissions
    user = request.user
    if user not in [prescription.patient, prescription.doctor] and not user.is_staff:
        messages.error(request, 'You do not have permission to view this prescription.')
        return redirect('prescription_list')
    
    # Get related data
    items = prescription.items.select_related('medicine').all()
    refill_requests = prescription.refill_requests.order_by('-request_date')
    history = MedicationHistory.objects.filter(prescription=prescription).order_by('-recorded_at')[:10]
    
    # Check for alerts
    alerts = PrescriptionAlert.objects.filter(
        patient=prescription.patient,
        prescription=prescription,
        is_resolved=False
    ).order_by('-priority')
    
    # Check drug interactions
    medicines = [item.medicine for item in items]
    interactions = []
    for i in range(len(medicines)):
        for j in range(i + 1, len(medicines)):
            interaction = DrugInteraction.objects.filter(
                Q(medicine1=medicines[i], medicine2=medicines[j]) |
                Q(medicine1=medicines[j], medicine2=medicines[i])
            ).first()
            if interaction:
                interactions.append(interaction)
    
    context = {
        'prescription': prescription,
        'items': items,
        'refill_requests': refill_requests,
        'history': history,
        'alerts': alerts,
        'interactions': interactions,
        'is_doctor': user == prescription.doctor,
        'can_refill': prescription.can_refill() and user == prescription.patient,
    }
    
    return render(request, 'prescriptions_app/prescription_detail.html', context)


@login_required
def create_prescription_view(request):
    """Create a new prescription"""
    if not hasattr(request.user, 'doctor_profile'):
        messages.error(request, 'Only doctors can create prescriptions.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        prescription_form = PrescriptionForm(request.POST)
        item_formset = PrescriptionItemFormSet(request.POST)
        
        if prescription_form.is_valid() and item_formset.is_valid():
            with transaction.atomic():
                # Create prescription
                prescription = prescription_form.save(commit=False)
                prescription.doctor = request.user
                prescription.status = 'active'
                prescription.save()
                
                # Save prescription items
                item_formset.instance = prescription
                item_formset.save()
                
                # Create medication history entry
                MedicationHistory.objects.create(
                    patient=prescription.patient,
                    prescription=prescription,
                    action='prescribed',
                    details=f"New prescription created by Dr. {request.user.get_full_name()}"
                )
                
                # Check for drug interactions
                check_prescription_interactions(prescription)
                
                # Send notification to patient
                send_prescription_notification(prescription)
                
            messages.success(request, 'Prescription created successfully.')
            return redirect('prescription_detail', prescription_id=prescription.id)
    else:
        patient_id = request.GET.get('patient')
        initial = {}
        if patient_id:
            try:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                patient = User.objects.get(pk=patient_id)
                initial['patient'] = patient
            except User.DoesNotExist:
                pass
        
        prescription_form = PrescriptionForm(initial=initial)
        item_formset = PrescriptionItemFormSet()
    
    # Get medicines for autocomplete
    medicines = Medicine.objects.filter(is_available=True).values('id', 'name', 'strength', 'form')
    
    context = {
        'prescription_form': prescription_form,
        'item_formset': item_formset,
        'medicines_json': json.dumps(list(medicines)),
    }
    
    return render(request, 'prescriptions_app/create_prescription.html', context)


@login_required
def edit_prescription_view(request, prescription_id):
    """Edit an existing prescription"""
    prescription = get_object_or_404(Prescription, pk=prescription_id)
    
    # Check permissions
    if request.user != prescription.doctor and not request.user.is_staff:
        messages.error(request, 'You do not have permission to edit this prescription.')
        return redirect('prescription_detail', prescription_id=prescription.id)
    
    if prescription.status not in ['draft', 'active']:
        messages.error(request, 'Only draft or active prescriptions can be edited.')
        return redirect('prescription_detail', prescription_id=prescription.id)
    
    if request.method == 'POST':
        prescription_form = PrescriptionForm(request.POST, instance=prescription)
        item_formset = PrescriptionItemFormSet(request.POST, instance=prescription)
        
        if prescription_form.is_valid() and item_formset.is_valid():
            with transaction.atomic():
                prescription_form.save()
                item_formset.save()
                
                # Update medication history
                MedicationHistory.objects.create(
                    patient=prescription.patient,
                    prescription=prescription,
                    action='changed',
                    details=f"Prescription modified by Dr. {request.user.get_full_name()}"
                )
                
                # Re-check interactions
                check_prescription_interactions(prescription)
                
            messages.success(request, 'Prescription updated successfully.')
            return redirect('prescription_detail', prescription_id=prescription.id)
    else:
        prescription_form = PrescriptionForm(instance=prescription)
        item_formset = PrescriptionItemFormSet(instance=prescription)
    
    medicines = Medicine.objects.filter(is_available=True).values('id', 'name', 'strength', 'form')
    
    context = {
        'prescription': prescription,
        'prescription_form': prescription_form,
        'item_formset': item_formset,
        'medicines_json': json.dumps(list(medicines)),
    }
    
    return render(request, 'prescriptions_app/edit_prescription.html', context)


@login_required
def request_refill_view(request, prescription_id):
    """Request a prescription refill"""
    prescription = get_object_or_404(Prescription, pk=prescription_id)
    
    # Check permissions
    if request.user != prescription.patient:
        messages.error(request, 'Only the patient can request refills.')
        return redirect('prescription_detail', prescription_id=prescription.id)
    
    if not prescription.can_refill():
        messages.error(request, 'This prescription cannot be refilled.')
        return redirect('prescription_detail', prescription_id=prescription.id)
    
    if request.method == 'POST':
        form = RefillRequestForm(request.POST)
        if form.is_valid():
            refill_request = form.save(commit=False)
            refill_request.prescription = prescription
            refill_request.patient = request.user
            refill_request.save()
            
            # Notify doctor
            send_refill_notification(refill_request)
            
            messages.success(request, 'Refill request submitted successfully.')
            return redirect('prescription_detail', prescription_id=prescription.id)
    else:
        form = RefillRequestForm(initial={
            'requested_refill_count': min(prescription.refills_remaining, 1)
        })
    
    context = {
        'prescription': prescription,
        'form': form,
    }
    
    return render(request, 'prescriptions_app/request_refill.html', context)


@login_required
def manage_refill_requests_view(request):
    """Manage refill requests (doctor view)"""
    if not hasattr(request.user, 'doctor_profile'):
        messages.error(request, 'Only doctors can manage refill requests.')
        return redirect('dashboard')
    
    status_filter = request.GET.get('status', 'pending')
    if status_filter == 'all':
        refill_requests = RefillRequest.objects.filter(
            prescription__doctor=request.user
        )
    else:
        refill_requests = RefillRequest.objects.filter(
            prescription__doctor=request.user,
            status=status_filter
        )
    
    refill_requests = refill_requests.select_related('prescription', 'patient').order_by('-request_date')
    
    # Pagination
    paginator = Paginator(refill_requests, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'status_counts': {
            'all': RefillRequest.objects.filter(prescription__doctor=request.user).count(),
            'pending': RefillRequest.objects.filter(prescription__doctor=request.user, status='pending').count(),
            'approved': RefillRequest.objects.filter(prescription__doctor=request.user, status='approved').count(),
            'denied': RefillRequest.objects.filter(prescription__doctor=request.user, status='denied').count(),
        }
    }
    
    return render(request, 'prescriptions_app/manage_refill_requests.html', context)


@login_required
@require_POST
def process_refill_request_view(request, request_id):
    """Process a refill request (approve/deny)"""
    if not hasattr(request.user, 'doctor_profile'):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    refill_request = get_object_or_404(RefillRequest, pk=request_id, prescription__doctor=request.user)
    
    action = request.POST.get('action')
    notes = request.POST.get('notes', '')
    
    if action == 'approve':
        success = refill_request.process_approval(request.user, notes)
        if success:
            # Notify patient
            send_refill_approval_notification(refill_request)
            messages.success(request, 'Refill request approved.')
        else:
            messages.error(request, 'Could not approve refill request.')
    elif action == 'deny':
        reason = request.POST.get('reason', '')
        success = refill_request.process_denial(request.user, reason)
        if success:
            # Notify patient
            send_refill_denial_notification(refill_request, reason)
            messages.success(request, 'Refill request denied.')
        else:
            messages.error(request, 'Could not deny refill request.')
    else:
        messages.error(request, 'Invalid action.')
    
    return redirect('manage_refill_requests')


@login_required
def medicine_list_view(request):
    """List all medicines"""
    medicines = Medicine.objects.all()
    
    # Filters
    category = request.GET.get('category')
    form = request.GET.get('form')
    available = request.GET.get('available')
    search = request.GET.get('search')
    
    if category:
        medicines = medicines.filter(category=category)
    if form:
        medicines = medicines.filter(form=form)
    if available == 'true':
        medicines = medicines.filter(is_available=True)
    elif available == 'false':
        medicines = medicines.filter(is_available=False)
    if search:
        medicines = medicines.filter(
            Q(name__icontains=search) |
            Q(generic_name__icontains=search) |
            Q(brand_name__icontains=search)
        )
    
    # Sort
    sort_by = request.GET.get('sort', 'name')
    medicines = medicines.order_by(sort_by)
    
    # Get categories and forms for filter dropdowns
    categories = Medicine.CATEGORY_CHOICES
    forms = Medicine.FORM_CHOICES
    
    # Pagination
    paginator = Paginator(medicines, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistics
    total_medicines = medicines.count()
    low_stock = medicines.filter(stock_quantity__lte=F('reorder_level')).count()
    out_of_stock = medicines.filter(stock_quantity=0).count()
    
    context = {
        'page_obj': page_obj,
        'categories': categories,
        'forms': forms,
        'category_filter': category,
        'form_filter': form,
        'available_filter': available,
        'search_query': search,
        'sort_by': sort_by,
        'statistics': {
            'total': total_medicines,
            'low_stock': low_stock,
            'out_of_stock': out_of_stock,
        }
    }
    
    return render(request, 'prescriptions_app/medicine_list.html', context)


@login_required
def medicine_detail_view(request, medicine_id):
    """View medicine details"""
    medicine = get_object_or_404(Medicine, pk=medicine_id)
    
    # Get interactions
    interactions = DrugInteraction.objects.filter(
        Q(medicine1=medicine) | Q(medicine2=medicine)
    ).select_related('medicine1', 'medicine2')
    
    # Get prescriptions using this medicine
    recent_prescriptions = PrescriptionItem.objects.filter(
        medicine=medicine
    ).select_related('prescription', 'prescription__patient').order_by('-created_at')[:10]
    
    context = {
        'medicine': medicine,
        'interactions': interactions,
        'recent_prescriptions': recent_prescriptions,
    }
    
    return render(request, 'prescriptions_app/medicine_detail.html', context)


@login_required
def add_medicine_view(request):
    """Add a new medicine to the database"""
    if not request.user.is_staff:
        messages.error(request, 'Only staff can add medicines.')
        return redirect('medicine_list')
    
    if request.method == 'POST':
        form = MedicineForm(request.POST, request.FILES)
        if form.is_valid():
            medicine = form.save()
            messages.success(request, f'Medicine "{medicine.name}" added successfully.')
            return redirect('medicine_detail', medicine_id=medicine.id)
    else:
        form = MedicineForm()
    
    context = {
        'form': form,
        'categories': Medicine.CATEGORY_CHOICES,
        'forms': Medicine.FORM_CHOICES,
    }
    
    return render(request, 'prescriptions_app/add_medicine.html', context)


@login_required
def edit_medicine_view(request, medicine_id):
    """Edit medicine details"""
    if not request.user.is_staff:
        messages.error(request, 'Only staff can edit medicines.')
        return redirect('medicine_list')
    
    medicine = get_object_or_404(Medicine, pk=medicine_id)
    
    if request.method == 'POST':
        form = MedicineForm(request.POST, request.FILES, instance=medicine)
        if form.is_valid():
            medicine = form.save()
            messages.success(request, f'Medicine "{medicine.name}" updated successfully.')
            return redirect('medicine_detail', medicine_id=medicine.id)
    else:
        form = MedicineForm(instance=medicine)
    
    context = {
        'medicine': medicine,
        'form': form,
        'categories': Medicine.CATEGORY_CHOICES,
        'forms': Medicine.FORM_CHOICES,
    }
    
    return render(request, 'prescriptions_app/edit_medicine.html', context)


@login_required
def medication_history_view(request):
    """View patient's medication history"""
    user = request.user
    is_doctor = hasattr(user, 'doctor_profile')
    
    if is_doctor:
        patient_id = request.GET.get('patient')
        if patient_id:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                patient = User.objects.get(pk=patient_id)
                history = MedicationHistory.objects.filter(patient=patient)
            except User.DoesNotExist:
                messages.error(request, 'Patient not found.')
                return redirect('dashboard')
        else:
            messages.error(request, 'Please select a patient.')
            return redirect('doctor_dashboard')
    else:
        patient = user
        history = MedicationHistory.objects.filter(patient=patient)
    
    # Filter by date range
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if date_from:
        try:
            history = history.filter(recorded_at__date__gte=datetime.strptime(date_from, '%Y-%m-%d').date())
        except ValueError:
            pass
    
    if date_to:
        try:
            history = history.filter(recorded_at__date__lte=datetime.strptime(date_to, '%Y-%m-%d').date())
        except ValueError:
            pass
    
    # Filter by action
    action_filter = request.GET.get('action')
    if action_filter:
        history = history.filter(action=action_filter)
    
    # Sort
    sort_by = request.GET.get('sort', '-recorded_at')
    history = history.order_by(sort_by)
    
    # Pagination
    paginator = Paginator(history, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'patient': patient,
        'is_doctor': is_doctor,
        'action_choices': MedicationHistory._meta.get_field('action').choices,
        'date_from': date_from,
        'date_to': date_to,
        'action_filter': action_filter,
        'sort_by': sort_by,
    }
    
    return render(request, 'prescriptions_app/medication_history.html', context)


@login_required
def drug_interactions_view(request):
    """Check drug interactions"""
    if request.method == 'POST':
        medicine_ids = request.POST.getlist('medicines')
        medicines = Medicine.objects.filter(id__in=medicine_ids)
        
        interactions = []
        for i in range(len(medicines)):
            for j in range(i + 1, len(medicines)):
                interaction = DrugInteraction.objects.filter(
                    Q(medicine1=medicines[i], medicine2=medicines[j]) |
                    Q(medicine1=medicines[j], medicine2=medicines[i])
                ).first()
                if interaction:
                    interactions.append(interaction)
        
        context = {
            'medicines': medicines,
            'interactions': interactions,
            'searched': True,
        }
        
        return render(request, 'prescriptions_app/drug_interactions.html', context)
    
    # GET request - show search form
    medicines = Medicine.objects.all().order_by('name')
    
    context = {
        'medicines': medicines,
        'searched': False,
    }
    
    return render(request, 'prescriptions_app/drug_interactions.html', context)


@login_required
def pharmacy_finder_view(request):
    """Find nearby pharmacies"""
    latitude = request.GET.get('lat')
    longitude = request.GET.get('lng')
    
    pharmacies = Pharmacy.objects.filter(is_verified=True)
    
    # Filter by services
    delivers = request.GET.get('delivers')
    if delivers == 'true':
        pharmacies = pharmacies.filter(delivers=True)
    
    accepts_insurance = request.GET.get('accepts_insurance')
    if accepts_insurance == 'true':
        pharmacies = pharmacies.filter(accepts_insurance=True)
    
    # Filter by opening status
    now = timezone.now().time()
    current_day = timezone.now().weekday()
    
    open_now = request.GET.get('open_now')
    if open_now == 'true':
        # Simplified: Check if current time is within opening hours
        pharmacies = pharmacies.filter(
            Q(is_24_hours=True) |
            Q(opening_time__lte=now, closing_time__gte=now)
        )
    
    # Search by name or address
    search = request.GET.get('search')
    if search:
        pharmacies = pharmacies.filter(
            Q(name__icontains=search) |
            Q(address__icontains=search)
        )
    
    context = {
        'pharmacies': pharmacies,
        'latitude': latitude,
        'longitude': longitude,
        'filters': {
            'delivers': delivers,
            'accepts_insurance': accepts_insurance,
            'open_now': open_now,
            'search': search,
        }
    }
    
    return render(request, 'prescriptions_app/pharmacy_finder.html', context)


@login_required
def pharmacy_detail_view(request, pharmacy_id):
    """View pharmacy details"""
    pharmacy = get_object_or_404(Pharmacy, pk=pharmacy_id)
    
    context = {
        'pharmacy': pharmacy,
    }
    
    return render(request, 'prescriptions_app/pharmacy_detail.html', context)


@login_required
def prescription_print_view(request, prescription_id):
    """Print prescription as PDF"""
    prescription = get_object_or_404(Prescription, pk=prescription_id)
    
    # Check permissions
    user = request.user
    if user not in [prescription.patient, prescription.doctor] and not user.is_staff:
        messages.error(request, 'You do not have permission to print this prescription.')
        return redirect('prescription_detail', prescription_id=prescription.id)
    
    items = prescription.items.select_related('medicine').all()
    
    context = {
        'prescription': prescription,
        'items': items,
        'today': timezone.now().date(),
    }
    
    # Generate PDF
    html_string = render_to_string('prescriptions_app/prescription_print.html', context)
    
    pdf = pdfkit.from_string(html_string, False, options={
        'page-size': 'A4',
        'encoding': 'UTF-8',
        'quiet': '',
    })
    
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="prescription_{prescription.prescription_id}.pdf"'
    
    return response


@login_required
def alerts_view(request):
    """View prescription alerts"""
    user = request.user
    
    if hasattr(user, 'doctor_profile'):
        # Doctor sees alerts for their patients
        alerts = PrescriptionAlert.objects.filter(
            patient__in=user.doctor_profile.patients.all()
        )
    else:
        # Patient sees their own alerts
        alerts = PrescriptionAlert.objects.filter(patient=user)
    
    # Filter by type
    alert_type = request.GET.get('type')
    if alert_type:
        alerts = alerts.filter(alert_type=alert_type)
    
    # Filter by priority
    priority = request.GET.get('priority')
    if priority:
        alerts = alerts.filter(priority=priority)
    
    # Filter by status
    show_resolved = request.GET.get('show_resolved', 'false') == 'true'
    if not show_resolved:
        alerts = alerts.filter(is_resolved=False)
    
    # Sort
    sort_by = request.GET.get('sort', '-created_at')
    alerts = alerts.order_by(sort_by)
    
    # Pagination
    paginator = Paginator(alerts, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'is_doctor': hasattr(user, 'doctor_profile'),
        'alert_type_filter': alert_type,
        'priority_filter': priority,
        'show_resolved': show_resolved,
        'sort_by': sort_by,
        'alert_type_choices': PrescriptionAlert.ALERT_TYPE_CHOICES,
        'priority_choices': PrescriptionAlert.PRIORITY_CHOICES,
    }
    
    return render(request, 'prescriptions_app/alerts.html', context)


@login_required
@require_POST
def mark_alert_resolved_view(request, alert_id):
    """Mark an alert as resolved"""
    alert = get_object_or_404(PrescriptionAlert, pk=alert_id)
    
    # Check permissions
    user = request.user
    if user != alert.patient and not hasattr(user, 'doctor_profile') and not user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    alert.is_resolved = True
    alert.resolved_at = timezone.now()
    alert.resolved_by = user
    alert.save()
    
    messages.success(request, 'Alert marked as resolved.')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    
    return redirect('alerts')


@login_required
def dashboard_view(request):
    """Prescription dashboard"""
    user = request.user
    is_doctor = hasattr(user, 'doctor_profile')
    
    if is_doctor:
        # Doctor dashboard
        prescriptions = Prescription.objects.filter(doctor=user)
        
        # Statistics
        active_prescriptions = prescriptions.filter(status='active').count()
        pending_refills = RefillRequest.objects.filter(
            prescription__doctor=user,
            status='pending'
        ).count()
        
        # Recent prescriptions
        recent_prescriptions = prescriptions.order_by('-issue_date')[:5]
        
        # Recent refill requests
        recent_refills = RefillRequest.objects.filter(
            prescription__doctor=user
        ).order_by('-request_date')[:5]
        
        context = {
            'is_doctor': True,
            'active_prescriptions': active_prescriptions,
            'pending_refills': pending_refills,
            'recent_prescriptions': recent_prescriptions,
            'recent_refills': recent_refills,
        }
    else:
        # Patient dashboard
        prescriptions = Prescription.objects.filter(patient=user)
        
        # Statistics
        active_prescriptions = prescriptions.filter(status='active').count()
        pending_refills = RefillRequest.objects.filter(
            patient=user,
            status='pending'
        ).count()
        unread_alerts = PrescriptionAlert.objects.filter(
            patient=user,
            is_read=False,
            is_resolved=False
        ).count()
        
        # Recent prescriptions
        recent_prescriptions = prescriptions.order_by('-issue_date')[:5]
        
        # Upcoming refills
        upcoming_refills = prescriptions.filter(
            status='active',
            refills_remaining__gt=0
        ).order_by('valid_until')[:5]
        
        # Recent alerts
        recent_alerts = PrescriptionAlert.objects.filter(
            patient=user,
            is_resolved=False
        ).order_by('-priority', '-created_at')[:5]
        
        context = {
            'is_doctor': False,
            'active_prescriptions': active_prescriptions,
            'pending_refills': pending_refills,
            'unread_alerts': unread_alerts,
            'recent_prescriptions': recent_prescriptions,
            'upcoming_refills': upcoming_refills,
            'recent_alerts': recent_alerts,
        }
    
    return render(request, 'prescriptions_app/dashboard.html', context)


@login_required
@require_GET
def api_search_medicines(request):
    """API endpoint for medicine search (autocomplete)"""
    query = request.GET.get('q', '')
    
    if not query:
        return JsonResponse({'results': []})
    
    medicines = Medicine.objects.filter(
        Q(name__icontains=query) |
        Q(generic_name__icontains=query) |
        Q(brand_name__icontains=query)
    ).filter(is_available=True)[:10]
    
    results = []
    for medicine in medicines:
        results.append({
            'id': medicine.id,
            'name': medicine.name,
            'generic_name': medicine.generic_name,
            'brand_name': medicine.brand_name,
            'strength': medicine.strength,
            'form': medicine.get_form_display(),
            'category': medicine.get_category_display(),
            'requires_prescription': medicine.requires_prescription,
        })
    
    return JsonResponse({'results': results})


@login_required
@require_GET
def api_medicine_detail(request, medicine_id):
    """API endpoint for medicine details"""
    medicine = get_object_or_404(Medicine, pk=medicine_id)
    
    data = {
        'id': medicine.id,
        'name': medicine.name,
        'generic_name': medicine.generic_name,
        'brand_name': medicine.brand_name,
        'strength': medicine.strength,
        'form': medicine.form,
        'form_display': medicine.get_form_display(),
        'category': medicine.category,
        'category_display': medicine.get_category_display(),
        'manufacturer': medicine.manufacturer,
        'side_effects': medicine.side_effects,
        'contraindications': medicine.contraindications,
        'storage_instructions': medicine.storage_instructions,
        'requires_prescription': medicine.requires_prescription,
        'is_controlled_substance': medicine.is_controlled_substance,
        'stock_quantity': medicine.stock_quantity,
        'is_available': medicine.is_available,
        'dosage_options': medicine.get_dosage_options(),
    }
    
    return JsonResponse(data)


@login_required
@require_GET
def export_prescriptions_csv(request):
    """Export prescriptions as CSV"""
    user = request.user
    is_doctor = hasattr(user, 'doctor_profile')
    
    if is_doctor:
        prescriptions = Prescription.objects.filter(doctor=user)
    else:
        prescriptions = Prescription.objects.filter(patient=user)
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="prescriptions_{timezone.now().date()}.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Prescription ID', 'Patient', 'Doctor', 'Diagnosis',
        'Issue Date', 'Valid Until', 'Status', 'Type',
        'Refills Allowed', 'Refills Remaining', 'Total Items', 'Total Cost'
    ])
    
    for prescription in prescriptions:
        writer.writerow([
            prescription.prescription_id,
            prescription.patient.get_full_name(),
            prescription.doctor.get_full_name(),
            prescription.diagnosis[:50] + '...' if len(prescription.diagnosis) > 50 else prescription.diagnosis,
            prescription.issue_date,
            prescription.valid_until,
            prescription.get_status_display(),
            prescription.get_prescription_type_display(),
            prescription.refills_allowed,
            prescription.refills_remaining,
            prescription.get_total_items(),
            prescription.get_total_cost(),
        ])
    
    return response


# Helper Functions

def check_prescription_interactions(prescription):
    """Check for drug interactions in a prescription"""
    items = prescription.items.select_related('medicine').all()
    medicines = [item.medicine for item in items]
    
    for i in range(len(medicines)):
        for j in range(i + 1, len(medicines)):
            interaction = DrugInteraction.objects.filter(
                Q(medicine1=medicines[i], medicine2=medicines[j]) |
                Q(medicine1=medicines[j], medicine2=medicines[i])
            ).first()
            
            if interaction and interaction.severity in ['major', 'contraindicated']:
                # Create alert for major interactions
                PrescriptionAlert.objects.create(
                    patient=prescription.patient,
                    prescription=prescription,
                    alert_type='interaction',
                    priority='high',
                    message=f"Potential {interaction.get_severity_display().lower()} interaction between {medicines[i].name} and {medicines[j].name}: {interaction.description}",
                    related_medicine=medicines[i],
                    related_interaction=interaction,
                )


def send_prescription_notification(prescription):
    """Send notification to patient about new prescription"""
    subject = f"New Prescription: {prescription.prescription_id}"
    message = render_to_string('prescriptions_app/emails/new_prescription.html', {
        'prescription': prescription,
    })
    
    send_mail(
        subject=subject,
        message='',  # Empty plain text message
        html_message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[prescription.patient.email],
        fail_silently=True,
    )


def send_refill_notification(refill_request):
    """Send notification to doctor about refill request"""
    subject = f"Refill Request: {refill_request.prescription.prescription_id}"
    message = render_to_string('prescriptions_app/emails/refill_request.html', {
        'refill_request': refill_request,
    })
    
    send_mail(
        subject=subject,
        message='',
        html_message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[refill_request.prescription.doctor.email],
        fail_silently=True,
    )


def send_refill_approval_notification(refill_request):
    """Send notification to patient about approved refill"""
    subject = f"Refill Approved: {refill_request.prescription.prescription_id}"
    message = render_to_string('prescriptions_app/emails/refill_approved.html', {
        'refill_request': refill_request,
    })
    
    send_mail(
        subject=subject,
        message='',
        html_message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[refill_request.patient.email],
        fail_silently=True,
    )


def send_refill_denial_notification(refill_request, reason):
    """Send notification to patient about denied refill"""
    subject = f"Refill Denied: {refill_request.prescription.prescription_id}"
    message = render_to_string('prescriptions_app/emails/refill_denied.html', {
        'refill_request': refill_request,
        'reason': reason,
    })
    
    send_mail(
        subject=subject,
        message='',
        html_message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[refill_request.patient.email],
        fail_silently=True,
    )