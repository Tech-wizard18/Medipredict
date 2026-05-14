from django import forms
from django.forms import inlineformset_factory
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import (
    Prescription, PrescriptionItem, Medicine,
    RefillRequest, DrugInteraction, Pharmacy
)


class PrescriptionForm(forms.ModelForm):
    """Form for creating/editing prescriptions"""
    
    class Meta:
        model = Prescription
        fields = [
            'patient', 'diagnosis', 'notes', 'prescription_type',
            'valid_until', 'refills_allowed', 'pharmacy_notes'
        ]
        widgets = {
            'patient': forms.Select(attrs={'class': 'form-control'}),
            'diagnosis': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter diagnosis...'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Additional instructions for patient...'
            }),
            'prescription_type': forms.Select(attrs={'class': 'form-control'}),
            'valid_until': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'min': timezone.now().date().isoformat()
            }),
            'refills_allowed': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'max': 12
            }),
            'pharmacy_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Notes for pharmacy...'
            }),
        }
    
    def clean_valid_until(self):
        """Ensure valid_until is in the future"""
        valid_until = self.cleaned_data.get('valid_until')
        if valid_until and valid_until < timezone.now().date():
            raise ValidationError('Prescription validity must be in the future.')
        return valid_until
    
    def clean_refills_allowed(self):
        """Limit maximum refills"""
        refills_allowed = self.cleaned_data.get('refills_allowed')
        if refills_allowed and refills_allowed > 12:
            raise ValidationError('Maximum 12 refills allowed.')
        return refills_allowed


class PrescriptionItemForm(forms.ModelForm):
    """Form for individual prescription items"""
    
    medicine_search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control medicine-search',
            'placeholder': 'Search medicine...',
            'autocomplete': 'off'
        })
    )
    
    class Meta:
        model = PrescriptionItem
        fields = [
            'medicine', 'dosage', 'frequency', 'duration',
            'duration_unit', 'instructions', 'take_with_food',
            'avoid_alcohol', 'specific_times', 'quantity',
            'unit_price', 'allow_generic'
        ]
        widgets = {
            'medicine': forms.Select(attrs={'class': 'form-control medicine-select'}),
            'dosage': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., 1 tablet, 10ml'
            }),
            'frequency': forms.Select(attrs={'class': 'form-control'}),
            'duration': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 365
            }),
            'duration_unit': forms.Select(attrs={'class': 'form-control'}),
            'instructions': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Specific instructions...'
            }),
            'specific_times': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., 8:00, 20:00'
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 1000
            }),
            'unit_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': 0
            }),
            'take_with_food': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'avoid_alcohol': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'allow_generic': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean_quantity(self):
        """Validate quantity"""
        quantity = self.cleaned_data.get('quantity')
        if quantity and quantity < 1:
            raise ValidationError('Quantity must be at least 1.')
        if quantity and quantity > 1000:
            raise ValidationError('Quantity cannot exceed 1000.')
        return quantity
    
    def clean_unit_price(self):
        """Validate unit price"""
        unit_price = self.cleaned_data.get('unit_price')
        if unit_price and unit_price < 0:
            raise ValidationError('Unit price cannot be negative.')
        return unit_price


# Create formset for prescription items
PrescriptionItemFormSet = inlineformset_factory(
    Prescription,
    PrescriptionItem,
    form=PrescriptionItemForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True,
    max_num=20,
    validate_max=True,
)


class RefillRequestForm(forms.ModelForm):
    """Form for requesting prescription refills"""
    
    class Meta:
        model = RefillRequest
        fields = ['requested_refill_count', 'reason']
        widgets = {
            'requested_refill_count': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 12
            }),
            'reason': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Reason for refill request...'
            }),
        }
    
    def clean_requested_refill_count(self):
        """Validate refill count"""
        count = self.cleaned_data.get('requested_refill_count')
        if count and count < 1:
            raise ValidationError('Must request at least 1 refill.')
        if count and count > 12:
            raise ValidationError('Cannot request more than 12 refills at once.')
        return count


class MedicineForm(forms.ModelForm):
    """Form for adding/editing medicines"""
    
    class Meta:
        model = Medicine
        fields = [
            'name', 'generic_name', 'brand_name', 'category', 'form',
            'strength', 'manufacturer', 'side_effects', 'contraindications',
            'pregnancy_category', 'storage_instructions',
            'requires_prescription', 'is_controlled_substance', 'schedule',
            'medicine_image', 'leaflet', 'stock_quantity', 'reorder_level'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'generic_name': forms.TextInput(attrs={'class': 'form-control'}),
            'brand_name': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'form': forms.Select(attrs={'class': 'form-control'}),
            'strength': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., 500mg, 10mg/ml'
            }),
            'manufacturer': forms.TextInput(attrs={'class': 'form-control'}),
            'side_effects': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'List common side effects...'
            }),
            'contraindications': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'List contraindications...'
            }),
            'pregnancy_category': forms.TextInput(attrs={'class': 'form-control'}),
            'storage_instructions': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Storage instructions...'
            }),
            'requires_prescription': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_controlled_substance': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'schedule': forms.TextInput(attrs={'class': 'form-control'}),
            'medicine_image': forms.FileInput(attrs={'class': 'form-control'}),
            'leaflet': forms.FileInput(attrs={'class': 'form-control'}),
            'stock_quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0
            }),
            'reorder_level': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0
            }),
        }
    
    def clean_stock_quantity(self):
        """Validate stock quantity"""
        stock_quantity = self.cleaned_data.get('stock_quantity')
        if stock_quantity is not None and stock_quantity < 0:
            raise ValidationError('Stock quantity cannot be negative.')
        return stock_quantity
    
    def clean_reorder_level(self):
        """Validate reorder level"""
        reorder_level = self.cleaned_data.get('reorder_level')
        if reorder_level is not None and reorder_level < 0:
            raise ValidationError('Reorder level cannot be negative.')
        return reorder_level


class DrugInteractionForm(forms.ModelForm):
    """Form for adding/editing drug interactions"""
    
    class Meta:
        model = DrugInteraction
        fields = ['medicine1', 'medicine2', 'severity', 'description', 'mechanism', 'recommendations', 'reference']
        widgets = {
            'medicine1': forms.Select(attrs={'class': 'form-control'}),
            'medicine2': forms.Select(attrs={'class': 'form-control'}),
            'severity': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe the interaction...'
            }),
            'mechanism': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Mechanism of interaction...'
            }),
            'recommendations': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Recommendations for management...'
            }),
            'reference': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'Reference URL...'
            }),
        }
    
    def clean(self):
        """Ensure medicine1 and medicine2 are different"""
        cleaned_data = super().clean()
        medicine1 = cleaned_data.get('medicine1')
        medicine2 = cleaned_data.get('medicine2')
        
        if medicine1 and medicine2 and medicine1 == medicine2:
            raise ValidationError('Please select two different medicines.')
        
        return cleaned_data


class PharmacyForm(forms.ModelForm):
    """Form for adding/editing pharmacies"""
    
    class Meta:
        model = Pharmacy
        fields = [
            'name', 'address', 'phone', 'email',
            'opening_time', 'closing_time', 'is_24_hours',
            'delivers', 'accepts_insurance', 'has_compounding',
            'latitude', 'longitude', 'license_number'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Full address...'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., +1-234-567-8900'
            }),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'opening_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'closing_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'is_24_hours': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'delivers': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'accepts_insurance': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_compounding': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'latitude': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': 'any',
                'placeholder': 'e.g., 40.7128'
            }),
            'longitude': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': 'any',
                'placeholder': 'e.g., -74.0060'
            }),
            'license_number': forms.TextInput(attrs={'class': 'form-control'}),
        }


class PrescriptionSearchForm(forms.Form):
    """Form for searching prescriptions"""
    search_query = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search prescriptions...',
            'style': 'max-width: 300px;'
        })
    )