from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Specialization, Doctor, ConsultationSlot, Consultation,
    ConsultationMessage, Prescription, PrescriptionItem,
    Review, Billing, Notification
)

@admin.register(Specialization)
class SpecializationAdmin(admin.ModelAdmin):
    list_display = ('name', 'description_preview')
    search_fields = ('name',)
    
    def description_preview(self, obj):
        return obj.description[:100] + '...' if len(obj.description) > 100 else obj.description
    description_preview.short_description = 'Description'


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ('get_name', 'specialization', 'hospital_name', 'is_verified', 'is_available', 'average_rating')
    list_filter = ('is_verified', 'is_available', 'specialization')
    search_fields = ('user__first_name', 'user__last_name', 'user__email', 'license_number', 'hospital_name')
    readonly_fields = ('average_rating', 'total_reviews')
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Professional Information', {
            'fields': ('specialization', 'license_number', 'years_of_experience', 
                      'qualifications', 'bio')
        }),
        ('Contact Information', {
            'fields': ('hospital_name', 'hospital_address')
        }),
        ('Availability & Pricing', {
            'fields': ('is_available', 'consultation_fee')
        }),
        ('Ratings', {
            'fields': ('average_rating', 'total_reviews')
        }),
        ('Verification', {
            'fields': ('is_verified', 'verification_documents')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def get_name(self, obj):
        return f"Dr. {obj.user.get_full_name()}"
    get_name.short_description = 'Name'
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            return self.readonly_fields + ('user',)
        return self.readonly_fields


class ConsultationMessageInline(admin.TabularInline):
    model = ConsultationMessage
    extra = 0
    readonly_fields = ('sender', 'timestamp')
    can_delete = False


@admin.register(Consultation)
class ConsultationAdmin(admin.ModelAdmin):
    list_display = ('consultation_id', 'get_patient', 'get_doctor', 'consultation_type', 
                   'status', 'booked_at', 'is_paid')
    list_filter = ('status', 'consultation_type', 'booked_at', 'is_paid')
    search_fields = ('consultation_id', 'patient__first_name', 'patient__last_name', 
                    'patient__email', 'doctor__user__first_name', 'doctor__user__last_name')
    readonly_fields = ('consultation_id', 'booked_at', 'confirmed_at', 'started_at', 
                      'completed_at', 'cancelled_at')
    inlines = [ConsultationMessageInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('consultation_id', 'patient', 'doctor', 'slot', 'consultation_type')
        }),
        ('Medical Information', {
            'fields': ('symptoms', 'medical_history_notes', 'current_medications', 'allergies')
        }),
        ('Consultation Details', {
            'fields': ('status', 'diagnosis', 'prescription', 'recommendations', 'follow_up_date')
        }),
        ('Payment', {
            'fields': ('consultation_fee', 'is_paid', 'payment_id')
        }),
        ('Timestamps', {
            'fields': ('booked_at', 'confirmed_at', 'started_at', 'completed_at', 'cancelled_at')
        }),
    )
    
    def get_patient(self, obj):
        return obj.patient.get_full_name()
    get_patient.short_description = 'Patient'
    
    def get_doctor(self, obj):
        return f"Dr. {obj.doctor.user.get_full_name()}"
    get_doctor.short_description = 'Doctor'


@admin.register(ConsultationSlot)
class ConsultationSlotAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'start_time', 'end_time', 'duration_minutes', 'is_booked')
    list_filter = ('is_booked', 'start_time', 'doctor')
    search_fields = ('doctor__user__first_name', 'doctor__user__last_name')
    readonly_fields = ('start_time', 'end_time')


class PrescriptionItemInline(admin.TabularInline):
    model = PrescriptionItem
    extra = 1


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_patient', 'get_doctor', 'created_at')
    search_fields = ('patient__first_name', 'patient__last_name', 
                    'doctor__user__first_name', 'doctor__user__last_name')
    inlines = [PrescriptionItemInline]
    
    def get_patient(self, obj):
        return obj.patient.get_full_name()
    get_patient.short_description = 'Patient'
    
    def get_doctor(self, obj):
        return f"Dr. {obj.doctor.user.get_full_name()}"
    get_doctor.short_description = 'Doctor'


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('get_patient', 'get_doctor', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('patient__first_name', 'patient__last_name', 
                    'doctor__user__first_name', 'doctor__user__last_name')
    readonly_fields = ('created_at', 'updated_at')
    
    def get_patient(self, obj):
        return obj.patient.get_full_name()
    get_patient.short_description = 'Patient'
    
    def get_doctor(self, obj):
        return f"Dr. {obj.doctor.user.get_full_name()}"
    get_doctor.short_description = 'Doctor'


@admin.register(Billing)
class BillingAdmin(admin.ModelAdmin):
    list_display = ('consultation', 'total_amount', 'payment_status', 'created_at')
    list_filter = ('payment_status', 'created_at')
    search_fields = ('consultation__consultation_id', 'transaction_id')
    readonly_fields = ('created_at', 'paid_at')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('user__first_name', 'user__last_name', 'user__email', 'message')
    readonly_fields = ('created_at',)
    list_per_page = 50