from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.db.models import Count, Avg, Q
from django.utils import timezone
from django.core.cache import cache
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
import json
import csv
from datetime import datetime, timedelta
import logging
from django.contrib.auth.decorators import login_required


from .models import DiseaseModel, Prediction, HealthReport, Symptom, PatientSymptom
from .forms import (
    DiabetesPredictionForm, HeartDiseasePredictionForm, KidneyDiseasePredictionForm,
    ParkinsonPredictionForm, BreastCancerPredictionForm, LiverDiseasePredictionForm,
    PatientSymptomForm
)
from .ml_utils import PredictionEngine
from .tasks import predict_disease_async, generate_report_async

logger = logging.getLogger(__name__)


class HomeView(TemplateView):
    """Home page view."""
    template_name = 'prediction_app/home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['disease_models'] = DiseaseModel.objects.filter(is_active=True)
        context['total_predictions'] = Prediction.objects.count()
        context['total_users'] = self.request.user.is_authenticated
        return context


def home(request):
    """Home page."""
    return render(request, 'prediction_app/home.html', {
        'disease_models': DiseaseModel.objects.filter(is_active=True),
        'total_predictions': Prediction.objects.count(),
        'user_predictions': Prediction.objects.filter(user=request.user).count() if request.user.is_authenticated else 0,
    })


class DashboardView(LoginRequiredMixin, TemplateView):
    """User dashboard view."""
    template_name = 'prediction_app/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # User statistics
        predictions = Prediction.objects.filter(user=user)
        context['total_predictions'] = predictions.count()
        context['recent_predictions'] = predictions.order_by('-created_at')[:5]
        context['prediction_accuracy'] = predictions.aggregate(
            avg_confidence=Avg('confidence')
        )['avg_confidence'] or 0
        
        # Disease-specific stats
        disease_stats = predictions.values(
            'disease_model__name'
        ).annotate(
            count=Count('id'),
            avg_confidence=Avg('confidence')
        ).order_by('-count')
        context['disease_stats'] = disease_stats
        
        # Recent health reports
        context['recent_reports'] = HealthReport.objects.filter(
            user=user
        ).order_by('-report_date')[:3]
        
        # Symptoms tracking
        context['recent_symptoms'] = PatientSymptom.objects.filter(
            user=user
        ).order_by('-recorded_at')[:5]
        
        # Risk assessment (simplified)
        context['overall_risk'] = self.calculate_risk_assessment(user)
        
        # Quick stats for dashboard cards
        context['today_predictions'] = predictions.filter(
            created_at__date=timezone.now().date()
        ).count()
        
        context['week_predictions'] = predictions.filter(
            created_at__gte=timezone.now() - timedelta(days=7)
        ).count()
        
        context['month_predictions'] = predictions.filter(
            created_at__gte=timezone.now() - timedelta(days=30)
        ).count()
        
        # Active disease models
        context['active_models'] = DiseaseModel.objects.filter(is_active=True)
        
        # Unique diseases checked
        context['unique_diseases'] = predictions.values('disease_model').distinct().count()

        return context
    
    def calculate_risk_assessment(self, user):
        """Calculate user's overall health risk."""
        predictions = Prediction.objects.filter(user=user)
        
        if not predictions.exists():
            return {'level': 'low', 'score': 0.1, 'message': 'No prediction data available'}
        
        # Calculate average risk from predictions
        high_risk_predictions = predictions.filter(
            Q(prediction_label__icontains='positive') |
            Q(prediction_label__icontains='high') |
            Q(confidence__gt=0.7)
        )
        
        risk_score = high_risk_predictions.count() / predictions.count()
        
        if risk_score < 0.3:
            level = 'low'
            message = 'Low health risk detected'
        elif risk_score < 0.6:
            level = 'moderate'
            message = 'Moderate health risk detected'
        elif risk_score < 0.8:
            level = 'high'
            message = 'High health risk detected. Please consult a doctor.'
        else:
            level = 'critical'
            message = 'Critical health risk detected. Immediate medical attention recommended.'
        
        return {
            'level': level,
            'score': risk_score,
            'message': message,
            'total_predictions': predictions.count(),
            'high_risk_count': high_risk_predictions.count()
        }


# Disease-specific prediction views
class BasePredictionView(LoginRequiredMixin, TemplateView):
    """Base view for all disease predictions."""
    template_name = None
    form_class = None
    disease_type = None
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = self.form_class()
        context['disease_type'] = self.disease_type
        context['disease_model'] = get_object_or_404(
            DiseaseModel, name=self.disease_type, is_active=True
        )
        return context
    
    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        
        if form.is_valid():
            try:
                # Get prediction from ML model
                prediction_engine = PredictionEngine()
                input_data = form.cleaned_data
                
                # Make prediction
                result = prediction_engine.predict(
                    disease_type=self.disease_type,
                    input_data=input_data
                )
                
                # Get disease model record
                disease_model = get_object_or_404(
                    DiseaseModel, name=self.disease_type, is_active=True
                )

                # Save prediction to database
                prediction = Prediction.objects.create(
                    user=request.user,
                    disease_model=disease_model,
                    prediction_result=result['probability'],
                    prediction_label=result['label'],
                    confidence=result['confidence'],
                    input_data=input_data
                )
                
                messages.success(
                    request,
                    f"Prediction completed! Result: {result['label']}"
                )
                
                return redirect('prediction_app:prediction_result', prediction_id=prediction.id)
                
            except Exception as e:
                logger.error(f"Prediction error: {e}")
                messages.error(request, f"Prediction failed: {str(e)}")
        
        # Form is invalid or error
        context = self.get_context_data()
        context['form'] = form
        return render(request, self.template_name, context)


class DiabetesPredictionView(BasePredictionView):
    template_name = 'prediction_app/diabetes.html'
    form_class = DiabetesPredictionForm
    disease_type = 'diabetes'


class HeartDiseasePredictionView(BasePredictionView):
    template_name = 'prediction_app/heart.html'
    form_class = HeartDiseasePredictionForm
    disease_type = 'heart'


class KidneyDiseasePredictionView(BasePredictionView):
    template_name = 'prediction_app/kidney.html'
    form_class = KidneyDiseasePredictionForm
    disease_type = 'kidney'


class ParkinsonPredictionView(BasePredictionView):
    template_name = 'prediction_app/parkinson.html'
    form_class = ParkinsonPredictionForm
    disease_type = 'parkinson'


class BreastCancerPredictionView(BasePredictionView):
    template_name = 'prediction_app/breast_cancer.html'
    form_class = BreastCancerPredictionForm
    disease_type = 'breast_cancer'


class LiverDiseasePredictionView(BasePredictionView):
    template_name = 'prediction_app/liver.html'
    form_class = LiverDiseasePredictionForm
    disease_type = 'liver'


# Prediction History Views
class PredictionHistoryView(LoginRequiredMixin, ListView):
    """View prediction history."""
    model = Prediction
    template_name = 'prediction_app/history.html'
    context_object_name = 'predictions'
    paginate_by = 10
    
    def get_queryset(self):
        return Prediction.objects.filter(
            user=self.request.user
        ).select_related('disease_model').order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add filter options
        context['disease_types'] = DiseaseModel.objects.filter(is_active=True)
        context['selected_disease'] = self.request.GET.get('disease', '')
        context['date_from'] = self.request.GET.get('date_from', '')
        context['date_to'] = self.request.GET.get('date_to', '')
        
        # Apply filters
        queryset = self.get_queryset()
        
        disease_filter = self.request.GET.get('disease')
        if disease_filter:
            queryset = queryset.filter(disease_model__name=disease_filter)
        
        date_from = self.request.GET.get('date_from')
        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)
        
        date_to = self.request.GET.get('date_to')
        if date_to:
            queryset = queryset.filter(created_at__lte=date_to)
        
        context['filtered_count'] = queryset.count()
        context['predictions'] = queryset
        
        # Statistics
        context['total_count'] = self.get_queryset().count()
        context['positive_count'] = self.get_queryset().filter(
            prediction_label__icontains='positive'
        ).count()
        context['average_confidence'] = self.get_queryset().aggregate(
            avg=Avg('confidence')
        )['avg'] or 0
        
        return context


class PredictionDetailView(LoginRequiredMixin, DetailView):
    """View prediction details."""
    model = Prediction
    template_name = 'prediction_app/prediction_detail.html'
    context_object_name = 'prediction'
    
    def get_queryset(self):
        return Prediction.objects.filter(user=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add recommendations based on prediction
        prediction = self.object
        context['recommendations'] = self.get_recommendations(prediction)
        
        # Add similar predictions
        context['similar_predictions'] = Prediction.objects.filter(
            user=self.request.user,
            disease_model=prediction.disease_model
        ).exclude(id=prediction.id).order_by('-created_at')[:5]
        
        return context
    
    def get_recommendations(self, prediction):
        """Get health recommendations based on prediction."""
        recommendations = []
        
        if prediction.prediction_label.lower() in ['positive', 'high', '1']:
            recommendations.extend([
                "Consult with a healthcare professional",
                "Schedule follow-up tests",
                "Monitor symptoms regularly",
                "Maintain a healthy lifestyle",
                "Follow prescribed medication if any"
            ])
        else:
            recommendations.extend([
                "Continue regular health checkups",
                "Maintain a balanced diet",
                "Exercise regularly",
                "Monitor your health indicators",
                "Stay hydrated and get adequate sleep"
            ])
        
        # Disease-specific recommendations
        disease_type = prediction.disease_model.name
        
        if disease_type == 'diabetes':
            recommendations.extend([
                "Monitor blood sugar levels regularly",
                "Follow a diabetic-friendly diet",
                "Maintain healthy weight"
            ])
        elif disease_type == 'heart':
            recommendations.extend([
                "Monitor blood pressure regularly",
                "Reduce sodium intake",
                "Engage in cardiovascular exercises"
            ])
        elif disease_type == 'kidney':
            recommendations.extend([
                "Stay hydrated",
                "Monitor kidney function tests",
                "Limit protein intake if advised"
            ])
        
        return recommendations


class PredictionDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a prediction."""
    model = Prediction
    template_name = 'prediction_app/prediction_confirm_delete.html'
    success_url = reverse_lazy('prediction_app:history')
    
    def get_queryset(self):
        return Prediction.objects.filter(user=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, "Prediction deleted successfully.")
        return super().delete(request, *args, **kwargs)


# Health Reports Views
class HealthReportsView(LoginRequiredMixin, ListView):
    """View health reports."""
    model = HealthReport
    template_name = 'prediction_app/reports.html'
    context_object_name = 'reports'
    paginate_by = 5
    
    def get_queryset(self):
        return HealthReport.objects.filter(
            user=self.request.user
        ).order_by('-report_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add report statistics
        reports = self.get_queryset()
        context['total_reports'] = reports.count()
        context['latest_report'] = reports.first()
        
        # Risk level distribution
        risk_distribution = reports.values('risk_level').annotate(
            count=Count('id')
        ).order_by('risk_level')
        context['risk_distribution'] = risk_distribution
        
        # Generate new report button
        context['can_generate_report'] = Prediction.objects.filter(
            user=self.request.user
        ).exists()
        
        return context


class HealthReportDetailView(LoginRequiredMixin, DetailView):
    """View health report details."""
    model = HealthReport
    template_name = 'prediction_app/report_detail.html'
    context_object_name = 'report'
    
    def get_queryset(self):
        return HealthReport.objects.filter(user=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add related predictions
        report_date = self.object.report_date
        context['related_predictions'] = Prediction.objects.filter(
            user=self.request.user,
            created_at__date=report_date
        ).select_related('disease_model')
        
        # Add symptoms from that period
        context['symptoms'] = PatientSymptom.objects.filter(
            user=self.request.user,
            onset_date__lte=report_date,
            onset_date__gte=report_date - timedelta(days=30)
        )
        
        return context


# Symptoms Tracking Views
class SymptomsListView(LoginRequiredMixin, ListView):
    """View tracked symptoms."""
    model = PatientSymptom
    template_name = 'prediction_app/symptoms.html'
    context_object_name = 'symptoms'
    paginate_by = 10
    
    def get_queryset(self):
        return PatientSymptom.objects.filter(
            user=self.request.user
        ).select_related('symptom').order_by('-recorded_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add symptom statistics
        symptoms = self.get_queryset()
        context['total_symptoms'] = symptoms.count()
        context['active_symptoms'] = symptoms.filter(
            onset_date__gte=timezone.now() - timedelta(days=7)
        ).count()
        
        # Add symptom categories
        categories = Symptom.objects.values('category').distinct()
        context['categories'] = categories
        
        return context


class SymptomCreateView(LoginRequiredMixin, CreateView):
    """Add a new symptom."""
    model = PatientSymptom
    form_class = PatientSymptomForm
    template_name = 'prediction_app/symptom_form.html'
    success_url = reverse_lazy('prediction_app:symptoms')
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, "Symptom added successfully.")
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['symptoms'] = Symptom.objects.all()
        return context


class SymptomUpdateView(LoginRequiredMixin, UpdateView):
    """Update a symptom."""
    model = PatientSymptom
    form_class = PatientSymptomForm
    template_name = 'prediction_app/symptom_form.html'
    success_url = reverse_lazy('prediction_app:symptoms')
    
    def get_queryset(self):
        return PatientSymptom.objects.filter(user=self.request.user)
    
    def form_valid(self, form):
        messages.success(self.request, "Symptom updated successfully.")
        return super().form_valid(form)


class SymptomDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a symptom."""
    model = PatientSymptom
    template_name = 'prediction_app/symptom_confirm_delete.html'
    success_url = reverse_lazy('prediction_app:symptoms')
    
    def get_queryset(self):
        return PatientSymptom.objects.filter(user=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, "Symptom deleted successfully.")
        return super().delete(request, *args, **kwargs)


# API-like Views
@login_required
def ajax_predict(request, disease):
    """AJAX endpoint for predictions."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        form_classes = {
            'diabetes': DiabetesPredictionForm,
            'heart': HeartDiseasePredictionForm,
            'kidney': KidneyDiseasePredictionForm,
            'parkinson': ParkinsonPredictionForm,
            'breast_cancer': BreastCancerPredictionForm,
            'liver': LiverDiseasePredictionForm,
        }
        
        if disease not in form_classes:
            return JsonResponse({'error': 'Invalid disease type'}, status=400)
        
        # Support both JSON and form-encoded bodies
        content_type = request.content_type or ''
        if 'application/json' in content_type:
            try:
                post_data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({'error': 'Invalid JSON'}, status=400)
        else:
            post_data = request.POST

        form_class = form_classes[disease]
        form = form_class(post_data)
        
        if not form.is_valid():
            return JsonResponse({
                'error': 'Invalid form data',
                'errors': form.errors
            }, status=400)
        
        prediction_engine = PredictionEngine()
        input_data = form.cleaned_data
        
        result = prediction_engine.predict(
            disease_type=disease,
            input_data=input_data
        )
        
        disease_model = DiseaseModel.objects.get(name=disease, is_active=True)
        
        prediction = Prediction.objects.create(
            user=request.user,
            disease_model=disease_model,
            prediction_result=result['probability'],
            prediction_label=result['label'],
            confidence=result['confidence'],
            input_data=input_data
        )
        
        return JsonResponse({
            'success': True,
            'prediction_id': prediction.id,
            'result': result,
        })
        
    except Exception as e:
        logger.error(f"AJAX prediction error: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def prediction_result(request, prediction_id):
    """View prediction result."""
    prediction = get_object_or_404(
        Prediction, id=prediction_id, user=request.user
    )
    
    # Get recommendations
    recommendations = get_recommendations(
        prediction.disease_model.name,
        {
            'label': prediction.prediction_label,
            'probability': prediction.prediction_result,
            'confidence': prediction.confidence
        }
    )
    
    return render(request, 'prediction_app/prediction_result.html', {
        'prediction': prediction,
        'recommendations': recommendations,
        'input_data': prediction.input_data
    })


@login_required
def save_prediction_result(request, prediction_id):
    """Save prediction result (mark as important)."""
    prediction = get_object_or_404(
        Prediction, id=prediction_id, user=request.user
    )
    
    # In a real implementation, you might add a 'saved' field
    # For now, we'll just return success
    return JsonResponse({'success': True, 'message': 'Prediction saved'})


@login_required
def generate_health_report(request):
    """Generate a new health report."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        # Check if user has predictions
        if not Prediction.objects.filter(user=request.user).exists():
            return JsonResponse({
                'error': 'No prediction data available'
            }, status=400)
        
        # Generate report asynchronously
        task = generate_report_async.delay(request.user.id)
        
        return JsonResponse({
            'success': True,
            'task_id': task.id,
            'message': 'Report generation started'
        })
        
    except Exception as e:
        logger.error(f"Report generation error: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def download_health_report(request, pk):
    """Download health report as PDF."""
    report = get_object_or_404(HealthReport, pk=pk, user=request.user)
    
    # Generate PDF (simplified - in production use reportlab or similar)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="health_report_{report.report_date}.pdf"'
    
    # Simple PDF content (replace with actual PDF generation)
    pdf_content = f"""
    MEDIPREDICT Health Report
    ========================
    
    Patient: {request.user.get_full_name()}
    Report Date: {report.report_date}
    Risk Level: {report.get_risk_level_display()}
    Risk Score: {report.overall_risk_score:.2%}
    
    Recommendations:
    {report.recommendations}
    
    Findings:
    {json.dumps(report.findings, indent=2)}
    
    Generated by: {report.get_generated_by_display()}
    """
    
    response.write(pdf_content)
    return response


# Export Views
@login_required
def export_predictions(request):
    """Export predictions in various formats."""
    format = request.GET.get('format', 'csv')
    predictions = Prediction.objects.filter(user=request.user)
    
    if format == 'csv':
        return export_predictions_csv(request)
    elif format == 'json':
        return export_predictions_json(request)
    elif format == 'pdf':
        return export_predictions_pdf(request)
    else:
        messages.error(request, "Invalid export format")
        return redirect('prediction_app:history')


def export_predictions_csv(request):
    """Export predictions as CSV."""
    predictions = Prediction.objects.filter(
        user=request.user
    ).select_related('disease_model')
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="predictions.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Date', 'Disease', 'Result', 'Label', 
        'Confidence', 'Input Data'
    ])
    
    for prediction in predictions:
        writer.writerow([
            prediction.created_at.strftime('%Y-%m-%d %H:%M'),
            prediction.disease_model.get_name_display(),
            prediction.prediction_result,
            prediction.prediction_label,
            f"{prediction.confidence:.2%}",
            json.dumps(prediction.input_data)
        ])
    
    return response


def export_predictions_json(request):
    """Export predictions as JSON."""
    predictions = Prediction.objects.filter(
        user=request.user
    ).select_related('disease_model').values(
        'created_at', 'disease_model__name', 'prediction_result',
        'prediction_label', 'confidence', 'input_data'
    )
    
    data = list(predictions)
    
    response = JsonResponse(data, safe=False)
    response['Content-Disposition'] = 'attachment; filename="predictions.json"'
    return response


def export_predictions_pdf(request):
    """Export predictions as PDF (simplified)."""
    predictions = Prediction.objects.filter(user=request.user)
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="predictions_report.pdf"'
    
    # Simple PDF content
    pdf_content = "MEDIPREDICT Predictions Report\n"
    pdf_content += "=" * 40 + "\n\n"
    pdf_content += f"Patient: {request.user.get_full_name()}\n"
    pdf_content += f"Report Date: {timezone.now().strftime('%Y-%m-%d')}\n"
    pdf_content += f"Total Predictions: {predictions.count()}\n\n"
    
    for pred in predictions:
        pdf_content += f"- {pred.disease_model.get_name_display()}: {pred.prediction_label} "
        pdf_content += f"(Confidence: {pred.confidence:.2%})\n"
    
    response.write(pdf_content)
    return response


# Analytics Views
class AnalyticsView(LoginRequiredMixin, TemplateView):
    """Analytics dashboard."""
    template_name = 'prediction_app/analytics.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Basic stats
        predictions = Prediction.objects.filter(user=user)
        context['total_predictions'] = predictions.count()
        context['unique_diseases'] = predictions.values('disease_model').distinct().count()
        
        # Time-based analytics
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        context['today_count'] = predictions.filter(
            created_at__date=today
        ).count()
        
        context['week_count'] = predictions.filter(
            created_at__date__gte=week_ago
        ).count()
        
        context['month_count'] = predictions.filter(
            created_at__date__gte=month_ago
        ).count()
        
        # Disease distribution
        disease_distribution = predictions.values(
            'disease_model__name'
        ).annotate(
            count=Count('id')
        ).order_by('-count')
        
        context['disease_distribution'] = disease_distribution
        
        # Risk trend
        risk_trend = HealthReport.objects.filter(
            user=user
        ).order_by('report_date').values(
            'report_date', 'risk_level', 'overall_risk_score'
        )[:10]
        
        context['risk_trend'] = risk_trend
        
        return context


@login_required
def analytics_data(request):
    """Provide analytics data for charts."""
    user = request.user
    data_type = request.GET.get('type', 'disease_distribution')
    
    if data_type == 'disease_distribution':
        data = Prediction.objects.filter(
            user=user
        ).values(
            'disease_model__name'
        ).annotate(
            count=Count('id')
        ).order_by('disease_model__name')
        
        return JsonResponse({
            'labels': [item['disease_model__name'] for item in data],
            'data': [item['count'] for item in data]
        })
    
    elif data_type == 'risk_trend':
        data = HealthReport.objects.filter(
            user=user
        ).order_by('report_date').values(
            'report_date', 'overall_risk_score'
        )[:20]
        
        return JsonResponse({
            'dates': [item['report_date'].strftime('%Y-%m-%d') for item in data],
            'scores': [float(item['overall_risk_score']) for item in data]
        })
    
    elif data_type == 'monthly_trend':
        # Get predictions grouped by month
        from django.db.models.functions import TruncMonth
        
        data = Prediction.objects.filter(
            user=user
        ).annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            count=Count('id')
        ).order_by('month')[:12]
        
        return JsonResponse({
            'months': [item['month'].strftime('%Y-%m') for item in data],
            'counts': [item['count'] for item in data]
        })
    
    return JsonResponse({'error': 'Invalid data type'}, status=400)


# Model Management Views
class ModelManagementView(LoginRequiredMixin, TemplateView):
    """Model management view (admin only)."""
    template_name = 'prediction_app/model_management.html'
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            messages.error(request, "Access denied. Admin privileges required.")
            return redirect('prediction_app:dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context['models'] = DiseaseModel.objects.all().order_by('name')
        context['model_status'] = self.get_model_status()
        
        return context
    
    def get_model_status(self):
        """Get status of all ML models."""
        from .ml_utils import ModelManager
        
        status = {}
        for model_name in ['diabetes', 'heart', 'kidney', 'parkinson', 'breast_cancer', 'liver']:
            try:
                model = ModelManager.get_model(model_name)
                scaler = ModelManager.get_scaler(model_name)
                status[model_name] = {
                    'loaded': model is not None,
                    'scaler_loaded': scaler is not None,
                    'type': type(model).__name__ if model else 'Not loaded'
                }
            except Exception as e:
                status[model_name] = {
                    'loaded': False,
                    'error': str(e)
                }
        
        return status


@login_required
def reload_model(request, disease):
    """Reload a specific ML model."""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        from .ml_utils import ModelManager
        ModelManager.load_model(disease)
        
        messages.success(request, f"{disease.capitalize()} model reloaded successfully.")
        return JsonResponse({'success': True})
        
    except Exception as e:
        logger.error(f"Model reload error: {e}")
        return JsonResponse({'error': str(e)}, status=500)


# Settings Views
class PredictionSettingsView(LoginRequiredMixin, TemplateView):
    """User prediction settings."""
    template_name = 'prediction_app/settings.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get user preferences
        user = self.request.user
        
        # Default settings
        context['settings'] = {
            'email_notifications': True,
            'prediction_alerts': True,
            'weekly_reports': True,
            'data_sharing': False,
            'auto_save_predictions': True,
        }
        
        # Get user's disease preferences
        context['disease_preferences'] = DiseaseModel.objects.filter(is_active=True)
        
        return context
    
    def post(self, request, *args, **kwargs):
        # Update user settings
        settings_data = {
            'email_notifications': request.POST.get('email_notifications') == 'on',
            'prediction_alerts': request.POST.get('prediction_alerts') == 'on',
            'weekly_reports': request.POST.get('weekly_reports') == 'on',
            'data_sharing': request.POST.get('data_sharing') == 'on',
            'auto_save_predictions': request.POST.get('auto_save_predictions') == 'on',
        }
        
        # Save settings to user profile or cache
        cache_key = f"user_settings_{request.user.id}"
        cache.set(cache_key, settings_data, timeout=3600*24*30)  # 30 days
        
        messages.success(request, "Settings updated successfully.")
        return redirect('prediction_app:settings')


# Help and Documentation Views
class HelpView(TemplateView):
    """Help and support page."""
    template_name = 'prediction_app/help.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context['faqs'] = [
            {
                'question': 'How accurate are the predictions?',
                'answer': 'Our models are trained on medical datasets and have accuracy rates between 85-95%. However, predictions should not replace professional medical advice.'
            },
            {
                'question': 'How do I interpret the results?',
                'answer': 'Results show the probability of having a condition. High probability (>70%) suggests further medical consultation. Low probability (<30%) suggests low risk.'
            },
            {
                'question': 'Is my data secure?',
                'answer': 'Yes, we use encryption and follow strict privacy policies. Your data is never shared without consent.'
            },
            {
                'question': 'Can I export my prediction history?',
                'answer': 'Yes, you can export your predictions in CSV, JSON, or PDF format from the History page.'
            },
        ]
        
        return context


class DocumentationView(TemplateView):
    """Documentation page."""
    template_name = 'prediction_app/documentation.html'


# WebSocket View
class PredictionWebSocketView(LoginRequiredMixin, TemplateView):
    """WebSocket test view."""
    template_name = 'prediction_app/ws_test.html'


# Webhook View
@csrf_exempt
@require_http_methods(["POST"])
def prediction_webhook(request):
    """Webhook for external prediction requests."""
    try:
        # Verify webhook signature
        signature = request.headers.get('X-Webhook-Signature')
        if not verify_webhook_signature(request.body, signature):
            return JsonResponse({'error': 'Invalid signature'}, status=401)
        
        # Parse request data
        data = json.loads(request.body)
        
        # Validate required fields
        required_fields = ['disease_type', 'input_data', 'api_key']
        for field in required_fields:
            if field not in data:
                return JsonResponse({'error': f'Missing field: {field}'}, status=400)
        
        # Verify API key
        if not verify_api_key(data['api_key']):
            return JsonResponse({'error': 'Invalid API key'}, status=401)
        
        # Make prediction
        prediction_engine = PredictionEngine()
        result = prediction_engine.predict(
            disease_type=data['disease_type'],
            input_data=data['input_data']
        )
        
        return JsonResponse({
            'success': True,
            'result': result,
            'timestamp': timezone.now().isoformat()
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return JsonResponse({'error': str(e)}, status=500)


def verify_webhook_signature(payload, signature):
    """Verify webhook signature."""
    # Implement signature verification
    # For example, using HMAC-SHA256
    import hmac
    import hashlib
    
    secret = b'your-webhook-secret'  # Should be in settings
    expected_signature = hmac.new(
        secret, payload, hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected_signature)


def verify_api_key(api_key):
    """Verify API key."""
    # Implement API key verification
    # For example, check against database
    from django.conf import settings
    return api_key == settings.API_KEY  # Simplified


# Error Handling Views
def error_view(request, error_type):
    """Handle different error types."""
    error_messages = {
        'prediction_failed': 'Prediction processing failed. Please try again.',
        'model_not_loaded': 'ML model is not loaded. Please contact support.',
        'invalid_input': 'Invalid input data provided.',
        'rate_limit': 'Too many requests. Please try again later.',
        'server_error': 'Internal server error. Our team has been notified.',
    }
    
    error_message = error_messages.get(
        error_type, 'An unexpected error occurred.'
    )
    
    return render(request, 'prediction_app/error.html', {
        'error_type': error_type,
        'error_message': error_message
    })


def search_view(request):
    """Search diseases and predictions."""
    query = request.GET.get('q', '').strip()
    results = []

    if query:
        disease_models = DiseaseModel.objects.filter(
            Q(name__icontains=query) | Q(description__icontains=query),
            is_active=True
        )
        results = disease_models

    return render(request, 'prediction_app/search_results.html', {
        'query': query,
        'results': results,
    })


# Health Check View
def health_check(request):
    """Health check endpoint."""
    from django.db import connection
    
    # Check database connection
    try:
        connection.ensure_connection()
        db_status = 'healthy'
    except Exception as e:
        db_status = f'unhealthy: {str(e)}'
    
    # Check ML models
    from .ml_utils import ModelManager
    model_status = {}
    for model_name in ['diabetes', 'heart', 'kidney']:
        try:
            model = ModelManager.get_model(model_name)
            model_status[model_name] = 'loaded' if model else 'not loaded'
        except Exception as e:
            model_status[model_name] = f'error: {str(e)}'
    
    return JsonResponse({
        'status': 'healthy',
        'timestamp': timezone.now().isoformat(),
        'services': {
            'database': db_status,
            'models': model_status,
            'cache': 'healthy' if cache.get('health_check') is None else 'unhealthy'
        }
    })


# Rate Limit Info
def rate_limit_info(request):
    """Show rate limit information."""
    return JsonResponse({
        'limits': {
            'predictions_per_hour': 100,
            'api_requests_per_day': 1000,
            'report_generation_per_day': 5,
        },
        'current_usage': {
            'predictions_today': Prediction.objects.filter(
                user=request.user,
                created_at__date=timezone.now().date()
            ).count() if request.user.is_authenticated else 0,
        }
    })


# Redirect Views
def redirect_to_diabetes(request):
    """Redirect to diabetes prediction page."""
    return redirect('prediction_app:diabetes')


def redirect_to_heart(request):
    """Redirect to heart disease prediction page."""
    return redirect('prediction_app:heart')


# Static Pages
class AboutPredictionsView(TemplateView):
    """About predictions page."""
    template_name = 'prediction_app/about_predictions.html'


class PrivacyPolicyView(TemplateView):
    """Privacy policy page."""
    template_name = 'prediction_app/privacy_policy.html'


class TermsOfServiceView(TemplateView):
    """Terms of service page."""
    template_name = 'prediction_app/terms_of_service.html'


# Helper Functions
def get_recommendations(disease_type, result):
    """Get recommendations based on disease type and result."""
    recommendations = []
    
    label = result['label'].lower()
    probability = result['probability']
    
    # General recommendations
    if 'positive' in label or 'high' in label or probability > 0.7:
        recommendations.append("Consult with a healthcare professional immediately.")
        recommendations.append("Schedule follow-up tests as soon as possible.")
    else:
        recommendations.append("Continue with regular health checkups.")
        recommendations.append("Maintain a healthy lifestyle.")
    
    # Disease-specific recommendations
    disease_recommendations = {
        'diabetes': [
            "Monitor blood sugar levels regularly.",
            "Follow a balanced diet with controlled carbohydrates.",
            "Engage in regular physical activity."
        ],
        'heart': [
            "Monitor blood pressure regularly.",
            "Reduce sodium and saturated fat intake.",
            "Engage in cardiovascular exercises."
        ],
        'kidney': [
            "Stay hydrated.",
            "Monitor kidney function through regular tests.",
            "Limit protein intake if advised by a doctor."
        ],
        'parkinson': [
            "Consult a neurologist for proper diagnosis.",
            "Consider physical therapy for movement.",
            "Join support groups for Parkinson's patients."
        ],
        'breast_cancer': [
            "Schedule a mammogram for confirmation.",
            "Consult an oncologist for further evaluation.",
            "Perform regular self-examinations."
        ],
        'liver': [
            "Avoid alcohol consumption.",
            "Maintain a healthy weight.",
            "Get liver function tests regularly."
        ]
    }
    
    if disease_type in disease_recommendations:
        recommendations.extend(disease_recommendations[disease_type])
    
    return recommendations


@login_required
def ajax_stats(request):
    """Get user statistics via AJAX."""
    user = request.user
    
    predictions = Prediction.objects.filter(user=user)
    total = predictions.count()
    
    # Calculate recent activity
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    
    today_count = predictions.filter(created_at__date=today).count()
    week_count = predictions.filter(created_at__date__gte=week_ago).count()
    
    # Disease distribution
    disease_dist = predictions.values(
        'disease_model__name'
    ).annotate(
        count=Count('id')
    ).order_by('-count')[:5]
    
    return JsonResponse({
        'total_predictions': total,
        'today_predictions': today_count,
        'week_predictions': week_count,
        'disease_distribution': list(disease_dist)
    })


@login_required
def ajax_recent_predictions(request):
    """Get recent predictions via AJAX."""
    predictions = Prediction.objects.filter(
        user=request.user
    ).select_related('disease_model').order_by('-created_at')[:5]
    
    data = []
    for pred in predictions:
        data.append({
            'id': pred.id,
            'disease': pred.disease_model.get_name_display(),
            'result': pred.prediction_label,
            'confidence': f"{pred.confidence:.1%}",
            'date': pred.created_at.strftime('%Y-%m-%d %H:%M'),
            'is_positive': 'positive' in pred.prediction_label.lower()
        })
    
    return JsonResponse({'predictions': data})


@login_required
def ajax_risk_assessment(request):
    """Get risk assessment via AJAX."""
    user = request.user
    
    # Get predictions
    predictions = Prediction.objects.filter(user=user)
    
    if not predictions.exists():
        return JsonResponse({
            'risk_level': 'unknown',
            'score': 0,
            'message': 'No prediction data available'
        })
    
    # Calculate risk based on positive predictions
    positive_predictions = predictions.filter(
        Q(prediction_label__icontains='positive') |
        Q(prediction_label__icontains='high') |
        Q(confidence__gt=0.7)
    )
    
    risk_score = positive_predictions.count() / predictions.count()
    
    if risk_score < 0.3:
        level = 'low'
        color = 'success'
        message = 'Low health risk'
    elif risk_score < 0.6:
        level = 'moderate'
        color = 'warning'
        message = 'Moderate health risk'
    elif risk_score < 0.8:
        level = 'high'
        color = 'danger'
        message = 'High health risk - Consult a doctor'
    else:
        level = 'critical'
        color = 'dark'
        message = 'Critical health risk - Immediate attention needed'
    
    return JsonResponse({
        'risk_level': level,
        'risk_color': color,
        'risk_score': risk_score,
        'message': message,
        'total_predictions': predictions.count(),
        'high_risk_predictions': positive_predictions.count()
    })


# Export functions for direct URL access
def export_predictions_csv(request):
    return export_predictions(request)


def export_predictions_json(request):
    return export_predictions(request)


def export_reports_pdf(request):
    return export_predictions(request)


def export_reports(request):
    """Export reports in various formats."""
    format = request.GET.get('format', 'pdf')
    reports = HealthReport.objects.filter(user=request.user)
    
    if format == 'pdf':
        return export_reports_pdf(request)
    else:
        messages.error(request, "Invalid export format")
        return redirect('prediction_app:reports')


# WebSocket Test View
class WebSocketTestView(LoginRequiredMixin, TemplateView):
    """WebSocket test page."""
    template_name = 'prediction_app/ws_test.html'