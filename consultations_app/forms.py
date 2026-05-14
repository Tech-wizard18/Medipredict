from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import (
    Doctor, Consultation, ConsultationMessage,
    Prescription, PrescriptionItem, Review,
    ConsultationSlot
)
from django.forms import inlineformset_factory


class DoctorRegistrationForm(forms.ModelForm):
    """Form for doctor registration"""
    agree_to_terms = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    class Meta:
        model = Doctor
        fields = [
            'specialization', 'license_number', 'years_of_experience',
            'qualifications', 'bio', 'hospital_name', 'hospital_address',
            'consultation_fee', 'verification_documents'
        ]
        widgets = {
            'specialization': forms.Select(attrs={'class': 'form-select'}),
            'license_number': forms.TextInput(attrs={'class': 'form-control'}),
            'years_of_experience': forms.NumberInput(attrs={'class': 'form-control'}),
            'qualifications': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'hospital_name': forms.TextInput(attrs={'class': 'form-control'}),
            'hospital_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'consultation_fee': forms.NumberInput(attrs={'class': 'form-control'}),
            'verification_documents': forms.FileInput(attrs={'class': 'form-control'}),
        }
    
    def clean_license_number(self):
        license_number = self.cleaned_data.get('license_number')
        if Doctor.objects.filter(license_number=license_number).exists():
            raise ValidationError("This license number is already registered.")
        return license_number
    
    def clean_consultation_fee(self):
        fee = self.cleaned_data.get('consultation_fee')
        if fee < 0:
            raise ValidationError("Consultation fee cannot be negative.")
        return fee


class ConsultationBookingForm(forms.ModelForm):
    """Form for booking a consultation"""
    
    class Meta:
        model = Consultation
        fields = [
            'slot', 'consultation_type', 'symptoms',
            'medical_history_notes', 'current_medications',
            'allergies'
        ]
        widgets = {
            'slot': forms.Select(attrs={'class': 'form-select'}),
            'consultation_type': forms.Select(attrs={'class': 'form-select'}),
            'symptoms': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Describe your symptoms...'}),
            'medical_history_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Any relevant medical history...'}),
            'current_medications': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Current medications if any...'}),
            'allergies': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Any allergies...'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.doctor = kwargs.pop('doctor', None)
        self.patient = kwargs.pop('patient', None)
        super().__init__(*args, **kwargs)
        
        if self.doctor:
            # Filter available slots for this doctor
            available_slots = ConsultationSlot.objects.filter(
                doctor=self.doctor,
                is_booked=False,
                start_time__gt=timezone.now()
            ).order_by('start_time')
            
            self.fields['slot'].queryset = available_slots
            self.fields['slot'].empty_label = "Select a time slot"
    
    def clean_slot(self):
        slot = self.cleaned_data.get('slot')
        if slot and slot.doctor != self.doctor:
            raise ValidationError("Invalid time slot selected.")
        if slot and slot.is_booked:
            raise ValidationError("This time slot is already booked.")
        if slot and slot.start_time <= timezone.now():
            raise ValidationError("Cannot book past time slots.")
        return slot


class ConsultationUpdateForm(forms.ModelForm):
    """Form for updating consultation status"""
    
    class Meta:
        model = Consultation
        fields = ['status', 'diagnosis', 'prescription', 'recommendations', 'follow_up_date']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'diagnosis': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'prescription': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'recommendations': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'follow_up_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
    
    def clean_follow_up_date(self):
        follow_up_date = self.cleaned_data.get('follow_up_date')
        if follow_up_date and follow_up_date < timezone.now().date():
            raise ValidationError("Follow-up date cannot be in the past.")
        return follow_up_date


class ConsultationMessageForm(forms.ModelForm):
    """Form for sending messages in consultation"""
    
    class Meta:
        model = ConsultationMessage
        fields = ['message', 'attachment']
        widgets = {
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Type your message here...'
            }),
            'attachment': forms.FileInput(attrs={'class': 'form-control'}),
        }
    
    def clean_attachment(self):
        attachment = self.cleaned_data.get('attachment')
        if attachment:
            # Validate file size (5MB limit)
            if attachment.size > 5 * 1024 * 1024:
                raise ValidationError("File size must be less than 5MB.")
            
            # Validate file type
            allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'application/pdf', 
                           'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
            if attachment.content_type not in allowed_types:
                raise ValidationError("Unsupported file type.")
        
        return attachment


class PrescriptionForm(forms.ModelForm):
    """Form for creating prescriptions"""
    
    class Meta:
        model = Prescription
        fields = ['diagnosis_summary', 'instructions', 'follow_up_instructions']
        widgets = {
            'diagnosis_summary': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'instructions': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'follow_up_instructions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class PrescriptionItemForm(forms.ModelForm):
    """Form for prescription items"""
    
    class Meta:
        model = PrescriptionItem
        fields = ['medicine_name', 'dosage', 'frequency', 'duration', 'instructions']
        widgets = {
            'medicine_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Medicine name'}),
            'dosage': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 500mg'}),
            'frequency': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Once daily'}),
            'duration': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 7 days'}),
            'instructions': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Additional instructions'}),
        }


# Formset for prescription items
PrescriptionItemFormSet = inlineformset_factory(
    Prescription,
    PrescriptionItem,
    form=PrescriptionItemForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True,
)


class ReviewForm(forms.ModelForm):
    """Form for submitting reviews"""
    
    class Meta:
        model = Review
        fields = ['rating', 'review_text']
        widgets = {
            'rating': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 5,
                'type': 'number'
            }),
            'review_text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Share your experience with the doctor...'
            }),
        }
    
    def clean_rating(self):
        rating = self.cleaned_data.get('rating')
        if rating < 1 or rating > 5:
            raise ValidationError("Rating must be between 1 and 5.")
        return rating


class SlotCreationForm(forms.Form):
    """Form for creating consultation slots"""
    date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'min': timezone.now().date().isoformat()
        })
    )
    start_time = forms.TimeField(
        widget=forms.TimeInput(attrs={
            'class': 'form-control',
            'type': 'time'
        })
    )
    duration = forms.IntegerField(
        initial=30,
        min_value=15,
        max_value=120,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': 15
        })
    )
    repeat_weekly = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    weeks_to_repeat = forms.IntegerField(
        required=False,
        initial=4,
        min_value=1,
        max_value=12,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )