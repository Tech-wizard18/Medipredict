from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Medicine, Prescription, PrescriptionItem,
    RefillRequest, MedicationHistory, DrugInteraction,
    Pharmacy, PrescriptionAlert
)


@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    list_display = ['name', 'generic_name', 'category', 'form', 'strength', 'is_available', 'stock_quantity', 'needs_reorder']
    list_filter = ['category', 'form', 'is_available', 'requires_prescription', 'is_controlled_substance']
    search_fields = ['name', 'generic_name', 'brand_name']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'generic_name', 'brand_name', 'category', 'form', 'strength', 'manufacturer')
        }),
        ('Safety Information', {
            'fields': ('side_effects', 'contraindications', 'pregnancy_category', 'storage_instructions')
        }),
        ('Regulatory Information', {
            'fields': ('requires_prescription', 'is_controlled_substance', 'schedule')
        }),
        ('Images & Documentation', {
            'fields': ('medicine_image', 'leaflet'),
            'classes': ('collapse',)
        }),
        ('Stock Information', {
            'fields': ('is_available', 'stock_quantity', 'reorder_level')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def needs_reorder(self, obj):
        return obj.needs_reorder()
    needs_reorder.boolean = True
    needs_reorder.short_description = 'Needs Reorder'


class PrescriptionItemInline(admin.TabularInline):
    model = PrescriptionItem
    extra = 0
    readonly_fields = ['created_at', 'updated_at']
    fields = ['medicine', 'dosage', 'frequency', 'duration', 'instructions', 'is_dispensed']


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ['prescription_id', 'patient', 'doctor', 'issue_date', 'valid_until', 'status', 'prescription_type', 'total_items']
    list_filter = ['status', 'prescription_type', 'issue_date', 'is_pharmacy_verified']
    search_fields = ['prescription_id', 'patient__username', 'doctor__username', 'diagnosis']
    readonly_fields = ['prescription_id', 'created_at', 'updated_at', 'verified_at']
    inlines = [PrescriptionItemInline]
    fieldsets = (
        ('Prescription Information', {
            'fields': ('prescription_id', 'patient', 'doctor', 'consultation')
        }),
        ('Prescription Details', {
            'fields': ('diagnosis', 'notes', 'prescription_type', 'status')
        }),
        ('Validity', {
            'fields': ('issue_date', 'valid_until', 'refills_allowed', 'refills_remaining')
        }),
        ('Digital Signature', {
            'fields': ('doctor_signature', 'digital_signature_hash'),
            'classes': ('collapse',)
        }),
        ('Pharmacy Information', {
            'fields': ('pharmacy_notes', 'is_pharmacy_verified', 'verified_by', 'verified_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def total_items(self, obj):
        return obj.items.count()
    total_items.short_description = 'Items'


@admin.register(PrescriptionItem)
class PrescriptionItemAdmin(admin.ModelAdmin):
    list_display = ['prescription', 'medicine', 'dosage', 'frequency', 'duration', 'is_dispensed']
    list_filter = ['frequency', 'is_dispensed', 'allow_generic']
    search_fields = ['prescription__prescription_id', 'medicine__name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(RefillRequest)
class RefillRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'prescription', 'patient', 'request_date', 'status', 'requested_refill_count']
    list_filter = ['status', 'request_date']
    search_fields = ['prescription__prescription_id', 'patient__username', 'reason']
    readonly_fields = ['created_at', 'updated_at', 'responded_at']


@admin.register(MedicationHistory)
class MedicationHistoryAdmin(admin.ModelAdmin):
    list_display = ['patient', 'prescription', 'action', 'recorded_at', 'severity']
    list_filter = ['action', 'severity', 'recorded_at']
    search_fields = ['patient__username', 'prescription__prescription_id', 'details']
    readonly_fields = ['recorded_at']
    date_hierarchy = 'recorded_at'


@admin.register(DrugInteraction)
class DrugInteractionAdmin(admin.ModelAdmin):
    list_display = ['medicine1', 'medicine2', 'severity']
    list_filter = ['severity']
    search_fields = ['medicine1__name', 'medicine2__name']
    readonly_fields = ['last_updated']


@admin.register(Pharmacy)
class PharmacyAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'is_verified', 'delivers', 'accepts_insurance', 'is_24_hours']
    list_filter = ['is_verified', 'delivers', 'accepts_insurance', 'is_24_hours']
    search_fields = ['name', 'address', 'phone']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(PrescriptionAlert)
class PrescriptionAlertAdmin(admin.ModelAdmin):
    list_display = ['patient', 'alert_type', 'priority', 'is_read', 'is_resolved', 'created_at']
    list_filter = ['alert_type', 'priority', 'is_read', 'is_resolved', 'created_at']
    search_fields = ['patient__username', 'message']
    readonly_fields = ['created_at', 'resolved_at']
    actions = ['mark_as_read', 'mark_as_resolved']
    
    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)
        self.message_user(request, f"{queryset.count()} alerts marked as read.")
    mark_as_read.short_description = "Mark selected alerts as read"
    
    def mark_as_resolved(self, request, queryset):
        queryset.update(is_resolved=True, resolved_at=timezone.now(), resolved_by=request.user)
        self.message_user(request, f"{queryset.count()} alerts marked as resolved.")
    mark_as_resolved.short_description = "Mark selected alerts as resolved"