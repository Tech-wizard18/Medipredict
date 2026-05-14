from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import DiseaseModel, Prediction, HealthReport, Symptom, PatientSymptom
from .forms import DiseaseModelForm


@admin.register(DiseaseModel)
class DiseaseModelAdmin(admin.ModelAdmin):
    """Admin interface for DiseaseModel."""
    
    form = DiseaseModelForm
    list_display = ('name_display', 'accuracy_percentage', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active', 'name', 'created_at')
    search_fields = ('name',)
    readonly_fields = ('created_at', 'updated_at', 'accuracy_percentage')
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'is_active', 'accuracy')
        }),
        ('Model Files', {
            'fields': ('model_file', 'scaler_file'),
            'description': 'Upload .pkl files for the model and scaler'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    actions = ['activate_models', 'deactivate_models']
    
    def name_display(self, obj):
        """Display human-readable disease name."""
        return obj.get_name_display()
    name_display.short_description = 'Disease'
    
    def accuracy_percentage(self, obj):
        """Display accuracy as percentage."""
        return f"{obj.accuracy:.2%}"
    accuracy_percentage.short_description = 'Accuracy'
    
    def view_predictions(self, obj):
        """Link to predictions for this model."""
        url = reverse('admin:prediction_app_prediction_changelist') + f'?disease_model__id={obj.id}'
        return format_html('<a href="{}">View Predictions</a>', url)
    view_predictions.short_description = 'Predictions'
    
    def activate_models(self, request, queryset):
        """Activate selected models."""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} model(s) activated.')
    activate_models.short_description = 'Activate selected models'
    
    def deactivate_models(self, request, queryset):
        """Deactivate selected models."""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} model(s) deactivated.')
    deactivate_models.short_description = 'Deactivate selected models'


@admin.register(Prediction)
class PredictionAdmin(admin.ModelAdmin):
    """Admin interface for Prediction."""
    
    list_display = ('user_email', 'disease_name', 'prediction_label', 
                   'confidence_percentage', 'created_at')
    list_filter = ('disease_model__name', 'prediction_label', 'created_at')
    search_fields = ('user__email', 'user__first_name', 'user__last_name')
    readonly_fields = ('created_at', 'confidence_percentage', 'view_user')
    fieldsets = (
        ('Prediction Details', {
            'fields': ('user', 'disease_model', 'prediction_result', 
                      'prediction_label', 'confidence')
        }),
        ('Input Data', {
            'fields': ('input_data_preview',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    date_hierarchy = 'created_at'
    
    def user_email(self, obj):
        """Display user email."""
        return obj.user.email
    user_email.short_description = 'User'
    user_email.admin_order_field = 'user__email'
    
    def disease_name(self, obj):
        """Display disease name."""
        return obj.disease_model.get_name_display()
    disease_name.short_description = 'Disease'
    
    def confidence_percentage(self, obj):
        """Display confidence as percentage."""
        return f"{obj.confidence:.2%}"
    confidence_percentage.short_description = 'Confidence'
    
    def input_data_preview(self, obj):
        """Preview input data in a readable format."""
        return format_html('<pre>{}</pre>', obj.input_data)
    input_data_preview.short_description = 'Input Data'
    
    def view_user(self, obj):
        """Link to user admin."""
        url = reverse('admin:users_app_customuser_change', args=[obj.user.id])
        return format_html('<a href="{}">View User</a>', url)
    view_user.short_description = 'User Profile'
    
    def has_add_permission(self, request):
        """Prevent adding predictions manually."""
        return False
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related('user', 'disease_model')


@admin.register(HealthReport)
class HealthReportAdmin(admin.ModelAdmin):
    """Admin interface for HealthReport."""
    
    list_display = ('user_email', 'report_date', 'risk_level_display', 
                   'overall_risk_score_percentage', 'generated_by')
    list_filter = ('risk_level', 'generated_by', 'report_date')
    search_fields = ('user__email', 'recommendations', 'doctor_notes')
    readonly_fields = ('report_date', 'overall_risk_score_percentage', 
                      'findings_preview', 'view_user')
    fieldsets = (
        ('Report Information', {
            'fields': ('user', 'report_date', 'overall_risk_score', 'risk_level')
        }),
        ('Content', {
            'fields': ('recommendations', 'findings_preview', 'doctor_notes')
        }),
        ('Metadata', {
            'fields': ('generated_by',),
            'classes': ('collapse',)
        }),
    )
    date_hierarchy = 'report_date'
    
    def user_email(self, obj):
        """Display user email."""
        return obj.user.email
    user_email.short_description = 'User'
    
    def risk_level_display(self, obj):
        """Color-coded risk level."""
        colors = {
            'low': 'green',
            'moderate': 'orange',
            'high': 'red',
            'critical': 'darkred'
        }
        color = colors.get(obj.risk_level, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_risk_level_display()
        )
    risk_level_display.short_description = 'Risk Level'
    
    def overall_risk_score_percentage(self, obj):
        """Display risk score as percentage."""
        return f"{obj.overall_risk_score:.2%}"
    overall_risk_score_percentage.short_description = 'Risk Score'
    
    def findings_preview(self, obj):
        """Preview findings in a readable format."""
        return format_html('<pre>{}</pre>', obj.findings)
    findings_preview.short_description = 'Findings'
    
    def view_user(self, obj):
        """Link to user admin."""
        url = reverse('admin:users_app_customuser_change', args=[obj.user.id])
        return format_html('<a href="{}">View User</a>', url)
    view_user.short_description = 'User Profile'


@admin.register(Symptom)
class SymptomAdmin(admin.ModelAdmin):
    """Admin interface for Symptom."""
    
    list_display = ('name', 'category_display', 'severity_levels_count')
    list_filter = ('category',)
    search_fields = ('name', 'description')
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'category')
        }),
        ('Severity Levels', {
            'fields': ('severity_levels_preview',),
            'classes': ('collapse',)
        }),
    )
    
    def category_display(self, obj):
        """Display category."""
        return obj.get_category_display()
    category_display.short_description = 'Category'
    
    def severity_levels_count(self, obj):
        """Count severity levels."""
        if isinstance(obj.severity_levels, dict):
            return len(obj.severity_levels)
        return 0
    severity_levels_count.short_description = 'Severity Levels'
    
    def severity_levels_preview(self, obj):
        """Preview severity levels."""
        return format_html('<pre>{}</pre>', obj.severity_levels)


@admin.register(PatientSymptom)
class PatientSymptomAdmin(admin.ModelAdmin):
    """Admin interface for PatientSymptom."""
    
    list_display = ('user_email', 'symptom_name', 'severity', 
                   'onset_date', 'duration_days', 'recorded_at')
    list_filter = ('symptom__category', 'severity', 'onset_date')
    search_fields = ('user__email', 'symptom__name', 'notes')
    readonly_fields = ('recorded_at', 'view_user', 'view_symptom')
    fieldsets = (
        ('Patient Information', {
            'fields': ('user', 'symptom')
        }),
        ('Symptom Details', {
            'fields': ('severity', 'onset_date', 'duration_days', 'notes')
        }),
        ('Metadata', {
            'fields': ('recorded_at',),
            'classes': ('collapse',)
        }),
    )
    
    def user_email(self, obj):
        """Display user email."""
        return obj.user.email
    user_email.short_description = 'User'
    
    def symptom_name(self, obj):
        """Display symptom name."""
        return obj.symptom.name
    symptom_name.short_description = 'Symptom'
    
    def view_user(self, obj):
        """Link to user admin."""
        url = reverse('admin:users_app_customuser_change', args=[obj.user.id])
        return format_html('<a href="{}">View User</a>', url)
    view_user.short_description = 'User Profile'
    
    def view_symptom(self, obj):
        """Link to symptom admin."""
        url = reverse('admin:prediction_app_symptom_change', args=[obj.symptom.id])
        return format_html('<a href="{}">View Symptom</a>', url)
    view_symptom.short_description = 'Symptom Details'


# Custom admin site title
admin.site.site_header = 'MEDIPREDICT - Disease Prediction Administration'
admin.site.site_title = 'MEDIPREDICT Admin'
admin.site.index_title = 'Welcome to MEDIPREDICT Prediction System'