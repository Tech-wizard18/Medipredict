""" 

default_app_config = 'prescriptions_app.apps.PrescriptionsAppConfig'

__version__ = '1.0.0'
__author__ = 'Medical System Team'
__email__ = 'support@medsystem.example.com'
__license__ = 'MIT'
__copyright__ = 'Copyright 2024 Medical System'

# API version
API_VERSION = 'v1'

# Export commonly used classes and functions
from .models import (
    Medicine,
    Prescription,
    PrescriptionItem,
    RefillRequest,
    MedicationHistory,
    DrugInteraction,
    Pharmacy,
    PrescriptionAlert
)

from .forms import (
    PrescriptionForm,
    PrescriptionItemForm,
    PrescriptionItemFormSet,
    RefillRequestForm,
    MedicineForm,
    DrugInteractionForm,
    PharmacyForm,
    PrescriptionSearchForm
)

from .views import (
    prescription_list_view,
    prescription_detail_view,
    create_prescription_view,
    edit_prescription_view,
    request_refill_view,
    manage_refill_requests_view,
    process_refill_request_view,
    medicine_list_view,
    medicine_detail_view,
    add_medicine_view,
    edit_medicine_view,
    medication_history_view,
    drug_interactions_view,
    pharmacy_finder_view,
    pharmacy_detail_view,
    prescription_print_view,
    alerts_view,
    mark_alert_resolved_view,
    dashboard_view,
    export_prescriptions_csv,
    api_search_medicines,
    api_medicine_detail
)

# Helper functions
from .views import (
    check_prescription_interactions,
    send_prescription_notification,
    send_refill_notification,
    send_refill_approval_notification,
    send_refill_denial_notification
)

# Constants
MEDICINE_CATEGORIES = Medicine.CATEGORY_CHOICES
MEDICINE_FORMS = Medicine.FORM_CHOICES
PRESCRIPTION_STATUS_CHOICES = Prescription.STATUS_CHOICES
PRESCRIPTION_TYPE_CHOICES = Prescription.TYPE_CHOICES
FREQUENCY_CHOICES = PrescriptionItem.FREQUENCY_CHOICES
DURATION_UNIT_CHOICES = PrescriptionItem.DURATION_UNIT_CHOICES
REFILL_STATUS_CHOICES = RefillRequest.STATUS_CHOICES
INTERACTION_SEVERITY_CHOICES = DrugInteraction.SEVERITY_CHOICES
ALERT_TYPE_CHOICES = PrescriptionAlert.ALERT_TYPE_CHOICES
ALERT_PRIORITY_CHOICES = PrescriptionAlert.PRIORITY_CHOICES

# Export constants as a dictionary
CONSTANTS = {
    'MEDICINE_CATEGORIES': MEDICINE_CATEGORIES,
    'MEDICINE_FORMS': MEDICINE_FORMS,
    'PRESCRIPTION_STATUS_CHOICES': PRESCRIPTION_STATUS_CHOICES,
    'PRESCRIPTION_TYPE_CHOICES': PRESCRIPTION_TYPE_CHOICES,
    'FREQUENCY_CHOICES': FREQUENCY_CHOICES,
    'DURATION_UNIT_CHOICES': DURATION_UNIT_CHOICES,
    'REFILL_STATUS_CHOICES': REFILL_STATUS_CHOICES,
    'INTERACTION_SEVERITY_CHOICES': INTERACTION_SEVERITY_CHOICES,
    'ALERT_TYPE_CHOICES': ALERT_TYPE_CHOICES,
    'ALERT_PRIORITY_CHOICES': ALERT_PRIORITY_CHOICES,
}

# Export exceptions
class PrescriptionError(Exception):
    "
    pass

class MedicineNotFoundError(PrescriptionError):
    
    pass

class PrescriptionExpiredError(PrescriptionError):
    
    pass

class InsufficientRefillsError(PrescriptionError):
    
    pass

class DrugInteractionError(PrescriptionError):
    
    pass

class InsufficientStockError(PrescriptionError):
    
    pass

# Utility functions
def get_prescription_by_id(prescription_id):
    
    from .models import Prescription
    try:
        return Prescription.objects.get(pk=prescription_id)
    except Prescription.DoesNotExist:
        return None

def get_medicine_by_name(name):
    
    from .models import Medicine
    try:
        return Medicine.objects.get(name=name)
    except Medicine.DoesNotExist:
        return None

def calculate_prescription_cost(prescription_id):
    
    from .models import Prescription
    try:
        prescription = Prescription.objects.get(pk=prescription_id)
        return prescription.get_total_cost()
    except Prescription.DoesNotExist:
        return 0.0

def check_medicine_availability(medicine_id, quantity_needed):
    
    from .models import Medicine
    try:
        medicine = Medicine.objects.get(pk=medicine_id)
        return medicine.stock_quantity >= quantity_needed
    except Medicine.DoesNotExist:
        return False

# Module information
__all__ = [
    # Models
    'Medicine',
    'Prescription',
    'PrescriptionItem',
    'RefillRequest',
    'MedicationHistory',
    'DrugInteraction',
    'Pharmacy',
    'PrescriptionAlert',
    
    # Forms
    'PrescriptionForm',
    'PrescriptionItemForm',
    'PrescriptionItemFormSet',
    'RefillRequestForm',
    'MedicineForm',
    'DrugInteractionForm',
    'PharmacyForm',
    'PrescriptionSearchForm',
    
    # Views
    'prescription_list_view',
    'prescription_detail_view',
    'create_prescription_view',
    'edit_prescription_view',
    'request_refill_view',
    'manage_refill_requests_view',
    'process_refill_request_view',
    'medicine_list_view',
    'medicine_detail_view',
    'add_medicine_view',
    'edit_medicine_view',
    'medication_history_view',
    'drug_interactions_view',
    'pharmacy_finder_view',
    'pharmacy_detail_view',
    'prescription_print_view',
    'alerts_view',
    'mark_alert_resolved_view',
    'dashboard_view',
    'export_prescriptions_csv',
    'api_search_medicines',
    'api_medicine_detail',
    
    # Helper functions
    'check_prescription_interactions',
    'send_prescription_notification',
    'send_refill_notification',
    'send_refill_approval_notification',
    'send_refill_denial_notification',
    
    # Constants
    'CONSTANTS',
    'MEDICINE_CATEGORIES',
    'MEDICINE_FORMS',
    'PRESCRIPTION_STATUS_CHOICES',
    'PRESCRIPTION_TYPE_CHOICES',
    'FREQUENCY_CHOICES',
    'DURATION_UNIT_CHOICES',
    'REFILL_STATUS_CHOICES',
    'INTERACTION_SEVERITY_CHOICES',
    'ALERT_TYPE_CHOICES',
    'ALERT_PRIORITY_CHOICES',
    
    # Exceptions
    'PrescriptionError',
    'MedicineNotFoundError',
    'PrescriptionExpiredError',
    'InsufficientRefillsError',
    'DrugInteractionError',
    'InsufficientStockError',
    
    # Utility functions
    'get_prescription_by_id',
    'get_medicine_by_name',
    'calculate_prescription_cost',
    'check_medicine_availability',
    
    # Metadata
    '__version__',
    '__author__',
    '__email__',
    '__license__',
    '__copyright__',
    'API_VERSION',
]

# Package initialization
print(f"Loading Prescriptions Management System v{__version__}")

# Check Django settings on import
try:
    from django.conf import settings
    
    # Verify required settings
    REQUIRED_SETTINGS = [
        'MEDIA_ROOT',
        'MEDIA_URL',
        'EMAIL_BACKEND',
    ]
    
    missing_settings = []
    for setting in REQUIRED_SETTINGS:
        if not hasattr(settings, setting):
            missing_settings.append(setting)
    
    if missing_settings:
        print(f"Warning: Missing Django settings: {', '.join(missing_settings)}")
        
except ImportError:
    print("Warning: Django not available - running in standalone mode")

# Version compatibility check
try:
    import django
    DJANGO_VERSION = django.get_version()
    print(f"Compatible with Django {DJANGO_VERSION}")
except ImportError:
    pass """