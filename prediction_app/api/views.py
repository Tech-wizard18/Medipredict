from rest_framework import viewsets, status, generics, mixins
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.pagination import PageNumberPagination
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Count, Avg, Q
from datetime import timedelta
import json
import csv
import logging

from prediction_app.models import (
    Prediction, HealthReport, Symptom, PatientSymptom, DiseaseModel
)
from prediction_app.api.serializers import (
    DiabetesPredictionSerializer,
    HeartDiseasePredictionSerializer,        # Was HeartDiseasePredictionSerializer
    KidneyDiseasePredictionSerializer,     # Was KidneyDiseasePredictionSerializer
    ParkinsonPredictionSerializer,
    BreastCancerPredictionSerializer,
    LiverDiseasePredictionSerializer,       # Was LiverDiseasePredictionSerializer
    PredictionSerializer,
    HealthReportSerializer,
    SymptomSerializer,
    PatientSymptomSerializer,
    DiseaseModelSerializer,
    BatchPredictionSerializer,
    BatchSymptomSerializer,
)
from prediction_app.ml_utils import PredictionEngine
from prediction_app.tasks import predict_disease_async, generate_report_async

logger = logging.getLogger(__name__)


class StandardResultsSetPagination(PageNumberPagination):
    """Custom pagination for API results."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class PredictionViewSet(viewsets.ModelViewSet):
    """API endpoint for predictions."""
    serializer_class = PredictionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['disease_model', 'prediction_label', 'created_at']
    throttle_classes = [UserRateThrottle]
    
    def get_queryset(self):
        """Return predictions for the authenticated user."""
        return Prediction.objects.filter(
            user=self.request.user
        ).select_related('disease_model').order_by('-created_at')
    
    def perform_create(self, serializer):
        """Save prediction with current user."""
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get prediction statistics."""
        queryset = self.get_queryset()
        
        stats = {
            'total': queryset.count(),
            'by_disease': queryset.values('disease_model__name').annotate(
                count=Count('id'),
                avg_confidence=Avg('confidence')
            ),
            'by_label': queryset.values('prediction_label').annotate(
                count=Count('id')
            ),
            'recent_30_days': queryset.filter(
                created_at__gte=timezone.now() - timedelta(days=30)
            ).count(),
        }
        
        return Response(stats)
    
    @action(detail=True, methods=['post'])
    def export(self, request, pk=None):
        """Export prediction as PDF or CSV."""
        prediction = self.get_object()
        format = request.data.get('format', 'json')
        
        if format == 'pdf':
            # Generate PDF (simplified)
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="prediction_{prediction.id}.pdf"'
            response.write(f"Prediction Report\nID: {prediction.id}")
            return response
        
        elif format == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="prediction_{prediction.id}.csv"'
            writer = csv.writer(response)
            writer.writerow(['Field', 'Value'])
            writer.writerow(['ID', prediction.id])
            writer.writerow(['Disease', prediction.disease_model.name])
            writer.writerow(['Result', prediction.prediction_label])
            writer.writerow(['Confidence', prediction.confidence])
            return response
        
        else:
            # Default to JSON
            serializer = self.get_serializer(prediction)
            return Response(serializer.data)


class HealthReportViewSet(viewsets.ModelViewSet):
    """API endpoint for health reports."""
    serializer_class = HealthReportSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        """Return health reports for the authenticated user."""
        return HealthReport.objects.filter(
            user=self.request.user
        ).order_by('-report_date')
    
    def perform_create(self, serializer):
        """Save health report with current user."""
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download health report as PDF."""
        report = self.get_object()
        
        # Generate PDF content (simplified)
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="health_report_{report.id}.pdf"'
        
        pdf_content = f"""
        MEDIPREDICT Health Report
        ========================
        
        Report ID: {report.id}
        Date: {report.report_date}
        Risk Level: {report.get_risk_level_display()}
        Risk Score: {report.overall_risk_score:.2%}
        
        Recommendations:
        {report.recommendations}
        
        Generated by: {report.get_generated_by_display()}
        """
        
        response.write(pdf_content)
        return response


class SymptomViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for symptoms (read-only)."""
    queryset = Symptom.objects.all()
    serializer_class = SymptomSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['category']


class PatientSymptomViewSet(viewsets.ModelViewSet):
    """API endpoint for patient symptoms."""
    serializer_class = PatientSymptomSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['symptom', 'severity', 'onset_date']
    
    def get_queryset(self):
        """Return patient symptoms for the authenticated user."""
        return PatientSymptom.objects.filter(
            user=self.request.user
        ).select_related('symptom').order_by('-recorded_at')
    
    def perform_create(self, serializer):
        """Save patient symptom with current user."""
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def timeline(self, request):
        """Get symptom timeline."""
        symptoms = self.get_queryset().values(
            'onset_date', 'symptom__name', 'severity'
        ).order_by('onset_date')
        
        return Response(list(symptoms))


class DiseaseModelViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for disease models (read-only)."""
    queryset = DiseaseModel.objects.filter(is_active=True)
    serializer_class = DiseaseModelSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination


# Disease-specific prediction views
class BasePredictionView(generics.GenericAPIView):
    """Base view for disease prediction."""
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            try:
                # Get prediction engine
                prediction_engine = PredictionEngine()
                
                # Make prediction
                result = prediction_engine.predict(
                    disease_type=self.disease_type,
                    input_data=serializer.validated_data
                )
                
                # Get disease model
                disease_model = DiseaseModel.objects.get(
                    name=self.disease_type, is_active=True
                )
                
                # Save prediction
                prediction = Prediction.objects.create(
                    user=request.user,
                    disease_model=disease_model,
                    prediction_result=result['probability'],
                    prediction_label=result['label'],
                    confidence=result['confidence'],
                    input_data=serializer.validated_data
                )
                
                # Include prediction ID in response
                result['prediction_id'] = prediction.id
                
                return Response({
                    'success': True,
                    'result': result,
                    'recommendations': self.get_recommendations(result)
                })
                
            except Exception as e:
                logger.error(f"Prediction error: {e}")
                return Response({
                    'success': False,
                    'error': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    def get_recommendations(self, result):
        """Get recommendations based on prediction result."""
        recommendations = []
        
        if 'positive' in result['label'].lower() or result['probability'] > 0.7:
            recommendations.append("Consult with a healthcare professional.")
            recommendations.append("Schedule follow-up tests.")
        else:
            recommendations.append("Continue regular health checkups.")
            recommendations.append("Maintain healthy lifestyle.")
        
        return recommendations


class PredictDiabetesView(BasePredictionView):
    """Predict diabetes."""
    serializer_class = DiabetesPredictionSerializer
    disease_type = 'diabetes'


class PredictHeartDiseaseView(BasePredictionView):
    """Predict heart disease."""
    serializer_class = HeartDiseasePredictionSerializer
    disease_type = 'heart'


class PredictKidneyDiseaseView(BasePredictionView):
    """Predict kidney disease."""
    serializer_class = KidneyDiseasePredictionSerializer
    disease_type = 'kidney'


class PredictParkinsonView(BasePredictionView):
    """Predict Parkinson disease."""
    serializer_class = ParkinsonPredictionSerializer
    disease_type = 'parkinson'


class PredictBreastCancerView(BasePredictionView):
    """Predict breast cancer."""
    serializer_class = BreastCancerPredictionSerializer
    disease_type = 'breast_cancer'


class PredictLiverDiseaseView(BasePredictionView):
    """Predict liver disease."""
    serializer_class = LiverDiseasePredictionSerializer
    disease_type = 'liver'


class PredictDiseaseView(BasePredictionView):
    """Generic disease prediction view."""
    
    def get_serializer_class(self):
        """Get serializer based on disease type."""
        disease_type = self.kwargs.get('disease')
        
        serializer_map = {
            'diabetes': DiabetesPredictionSerializer,
            'heart': HeartDiseasePredictionSerializer,
            'kidney': KidneyDiseasePredictionSerializer,
            'parkinson': ParkinsonPredictionSerializer,
            'breast_cancer': BreastCancerPredictionSerializer,
            'liver': LiverDiseasePredictionSerializer,
        }
        
        if disease_type not in serializer_map:
            raise ValueError(f"Unknown disease type: {disease_type}")
        
        return serializer_map[disease_type]
    
    @property
    def disease_type(self):
        return self.kwargs.get('disease')


class AsyncPredictionView(APIView):
    """Make prediction asynchronously."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, disease_type):
        serializer_class = self.get_serializer_class(disease_type)
        serializer = serializer_class(data=request.data)
        
        if serializer.is_valid():
            # Start async task
            task = predict_disease_async.delay(
                user_id=request.user.id,
                disease_type=disease_type,
                input_data=serializer.validated_data
            )
            
            return Response({
                'success': True,
                'task_id': task.id,
                'message': 'Prediction started asynchronously'
            })
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    def get_serializer_class(self, disease_type):
        """Get serializer based on disease type."""
        serializer_map = {
            'diabetes': DiabetesPredictionSerializer,
            'heart': HeartDiseasePredictionSerializer,
            'kidney': KidneyDiseasePredictionSerializer,
            'parkinson': ParkinsonPredictionSerializer,
            'breast_cancer': BreastCancerPredictionSerializer,
            'liver': LiverDiseasePredictionSerializer,
        }
        
        if disease_type not in serializer_map:
            raise ValueError(f"Unknown disease type: {disease_type}")
        
        return serializer_map[disease_type]


# Analytics views
class AnalyticsStatsView(APIView):
    """Get analytics statistics."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Prediction statistics
        predictions = Prediction.objects.filter(user=user)
        total_predictions = predictions.count()
        
        # Time-based statistics
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        stats = {
            'predictions': {
                'total': total_predictions,
                'today': predictions.filter(created_at__date=today).count(),
                'this_week': predictions.filter(created_at__date__gte=week_ago).count(),
                'this_month': predictions.filter(created_at__date__gte=month_ago).count(),
                'by_disease': predictions.values('disease_model__name').annotate(
                    count=Count('id')
                ).order_by('-count'),
                'positive_rate': predictions.filter(
                    prediction_label__icontains='positive'
                ).count() / total_predictions if total_predictions > 0 else 0,
            },
            'reports': {
                'total': HealthReport.objects.filter(user=user).count(),
                'latest': HealthReport.objects.filter(user=user)
                    .order_by('-report_date')
                    .values('report_date', 'risk_level').first(),
            },
            'symptoms': {
                'total': PatientSymptom.objects.filter(user=user).count(),
                'active': PatientSymptom.objects.filter(
                    user=user,
                    onset_date__gte=today - timedelta(days=7)
                ).count(),
            }
        }
        
        return Response(stats)


class AnalyticsTrendsView(APIView):
    """Get analytics trends."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Get predictions grouped by month
        from django.db.models.functions import TruncMonth
        
        monthly_trends = Prediction.objects.filter(
            user=user
        ).annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            count=Count('id'),
            positive=Count('id', filter=Q(prediction_label__icontains='positive')),
            avg_confidence=Avg('confidence')
        ).order_by('month')[-12:]  # Last 12 months
        
        # Risk trend from health reports
        risk_trend = HealthReport.objects.filter(
            user=user
        ).order_by('report_date').values(
            'report_date', 'risk_level', 'overall_risk_score'
        )[-10:]
        
        # Symptom trends
        symptom_trend = PatientSymptom.objects.filter(
            user=user
        ).values(
            'symptom__name', 'severity'
        ).annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        return Response({
            'monthly_trends': list(monthly_trends),
            'risk_trend': list(risk_trend),
            'symptom_trend': list(symptom_trend)
        })


class DiseaseDistributionView(APIView):
    """Get disease distribution."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        distribution = Prediction.objects.filter(
            user=user
        ).values(
            'disease_model__name'
        ).annotate(
            total=Count('id'),
            positive=Count('id', filter=Q(prediction_label__icontains='positive')),
            avg_confidence=Avg('confidence')
        ).order_by('-total')
        
        return Response(list(distribution))


# Report generation
class GenerateReportView(APIView):
    """Generate health report."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # Start async report generation
        task = generate_report_async.delay(
            user_id=request.user.id,
            report_date=request.data.get('report_date')
        )
        
        return Response({
            'success': True,
            'task_id': task.id,
            'message': 'Report generation started'
        })


class DownloadReportView(APIView):
    """Download health report."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk):
        report = get_object_or_404(HealthReport, pk=pk, user=request.user)
        
        format = request.query_params.get('format', 'pdf')
        
        if format == 'json':
            serializer = HealthReportSerializer(report)
            return Response(serializer.data)
        
        else:  # PDF
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="report_{report.id}.pdf"'
            
            # Simple PDF content
            pdf_content = f"""
            Health Report #{report.id}
            ======================
            
            Date: {report.report_date}
            Risk Level: {report.get_risk_level_display()}
            Risk Score: {report.overall_risk_score:.2%}
            
            Recommendations:
            {report.recommendations}
            """
            
            response.write(pdf_content)
            return response


# Model management
class ModelStatusView(APIView):
    """Get ML model status."""
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        from prediction_app.ml_utils import ModelManager
        
        try:
            model_info = ModelManager.get_all_model_info()
            return Response(model_info)
        except Exception as e:
            return Response({'error': str(e)}, 
                          status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ReloadModelView(APIView):
    """Reload ML model."""
    permission_classes = [IsAdminUser]
    
    def post(self, request, disease):
        from prediction_app.ml_utils import ModelManager
        
        try:
            success = ModelManager.load_model(disease)
            
            if success:
                return Response({'success': True, 'message': f'Model {disease} reloaded'})
            else:
                return Response({'success': False, 'message': 'Failed to reload model'},
                              status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({'error': str(e)}, 
                          status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RetrainModelView(APIView):
    """Retrain ML model."""
    permission_classes = [IsAdminUser]
    
    def post(self, request, disease):
        from prediction_app.tasks import retrain_model
        
        try:
            task = retrain_model.delay(disease)
            return Response({
                'success': True,
                'task_id': task.id,
                'message': f'Model {disease} retraining started'
            })
        except Exception as e:
            return Response({'error': str(e)}, 
                          status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Export views
class ExportPredictionsCSVView(APIView):
    """Export predictions as CSV."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        predictions = Prediction.objects.filter(
            user=request.user
        ).select_related('disease_model')
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="predictions.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Date', 'Disease', 'Result', 'Label', 'Confidence'])
        
        for pred in predictions:
            writer.writerow([
                pred.created_at.strftime('%Y-%m-%d %H:%M'),
                pred.disease_model.get_name_display(),
                pred.prediction_result,
                pred.prediction_label,
                f"{pred.confidence:.2%}"
            ])
        
        return response


class ExportPredictionsJSONView(APIView):
    """Export predictions as JSON."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        predictions = Prediction.objects.filter(
            user=request.user
        ).select_related('disease_model').values(
            'created_at', 'disease_model__name', 'prediction_result',
            'prediction_label', 'confidence', 'input_data'
        )
        
        data = list(predictions)
        
        response = Response(data)
        response['Content-Disposition'] = 'attachment; filename="predictions.json"'
        return response


class ExportReportsPDFView(APIView):
    """Export reports as PDF."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        reports = HealthReport.objects.filter(user=request.user)
        
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="health_reports.pdf"'
        
        # Simple PDF content
        pdf_content = "MEDIPREDICT Health Reports\n"
        pdf_content += "=" * 30 + "\n\n"
        
        for report in reports:
            pdf_content += f"Report #{report.id}\n"
            pdf_content += f"Date: {report.report_date}\n"
            pdf_content += f"Risk Level: {report.get_risk_level_display()}\n"
            pdf_content += f"Risk Score: {report.overall_risk_score:.2%}\n"
            pdf_content += "-" * 20 + "\n\n"
        
        response.write(pdf_content)
        return response


# Batch operations
class BatchPredictView(APIView):
    """Batch prediction."""
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]
    
    def post(self, request):
        serializer = BatchPredictionSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                prediction_engine = PredictionEngine()
                results = []
                
                for input_data in serializer.validated_data['inputs']:
                    try:
                        result = prediction_engine.predict(
                            disease_type=serializer.validated_data['disease_type'],
                            input_data=input_data
                        )
                        
                        # Save prediction
                        disease_model = DiseaseModel.objects.get(
                            name=serializer.validated_data['disease_type'],
                            is_active=True
                        )
                        
                        prediction = Prediction.objects.create(
                            user=request.user,
                            disease_model=disease_model,
                            prediction_result=result['probability'],
                            prediction_label=result['label'],
                            confidence=result['confidence'],
                            input_data=input_data
                        )
                        
                        result['prediction_id'] = prediction.id
                        results.append(result)
                        
                    except Exception as e:
                        results.append({
                            'error': str(e),
                            'input_data': input_data
                        })
                
                return Response({
                    'success': True,
                    'results': results,
                    'total': len(results),
                    'successful': len([r for r in results if 'error' not in r])
                })
                
            except Exception as e:
                return Response({
                    'success': False,
                    'error': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class BatchSymptomsView(APIView):
    """Batch symptom creation."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = BatchSymptomSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                created = []
                errors = []
                
                for symptom_data in serializer.validated_data['symptoms']:
                    try:
                        symptom = PatientSymptom.objects.create(
                            user=request.user,
                            **symptom_data
                        )
                        created.append(symptom.id)
                    except Exception as e:
                        errors.append({
                            'error': str(e),
                            'data': symptom_data
                        })
                
                return Response({
                    'success': True,
                    'created': len(created),
                    'errors': len(errors),
                    'symptom_ids': created,
                    'error_details': errors
                })
                
            except Exception as e:
                return Response({
                    'success': False,
                    'error': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


# Webhook endpoints
class PredictionWebhookView(APIView):
    """Webhook for external prediction requests."""
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            disease_type = request.data.get('disease_type')
            input_data = request.data.get('input_data')
            
            if not disease_type or not input_data:
                return Response({
                    'error': 'Missing disease_type or input_data'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate API key permissions
            if not self.has_permission(request.user, disease_type):
                return Response({
                    'error': 'Insufficient permissions for this disease type'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Make prediction
            prediction_engine = PredictionEngine()
            result = prediction_engine.predict(disease_type, input_data)
            
            return Response({
                'success': True,
                'result': result,
                'timestamp': timezone.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Webhook error: {e}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def has_permission(self, user, disease_type):
        """Check if user has permission for disease type."""
        # Implement permission logic
        return True


class HealthAlertWebhookView(APIView):
    """Webhook for health alerts."""
    
    def post(self, request):
        try:
            # Verify webhook signature
            signature = request.headers.get('X-Webhook-Signature')
            if not self.verify_signature(request.body, signature):
                return Response({'error': 'Invalid signature'}, 
                              status=status.HTTP_401_UNAUTHORIZED)
            
            alert_data = request.data
            
            # Process alert
            # This could trigger notifications, emails, etc.
            
            logger.info(f"Health alert received: {alert_data}")
            
            return Response({'success': True})
            
        except Exception as e:
            logger.error(f"Health alert webhook error: {e}")
            return Response({'error': str(e)}, 
                          status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def verify_signature(self, payload, signature):
        """Verify webhook signature."""
        # Implement signature verification
        import hmac
        import hashlib
        
        secret = b'your-webhook-secret'  # Should be in settings
        expected = hmac.new(secret, payload, hashlib.sha256).hexdigest()
        
        return hmac.compare_digest(signature, expected)


# Health check
class APIHealthCheckView(APIView):
    """API health check."""
    
    def get(self, request):
        from django.db import connection
        import redis
        
        checks = {}
        
        # Database check
        try:
            connection.ensure_connection()
            checks['database'] = 'healthy'
        except Exception as e:
            checks['database'] = f'unhealthy: {e}'
        
        # Redis check
        try:
            redis_client = redis.from_url(settings.CELERY_BROKER_URL)
            redis_client.ping()
            checks['redis'] = 'healthy'
        except Exception as e:
            checks['redis'] = f'unhealthy: {e}'
        
        # ML models check
        from prediction_app.ml_utils import ModelManager
        try:
            model_info = ModelManager.get_all_model_info()
            loaded = sum(1 for info in model_info.values() if info.get('loaded'))
            checks['ml_models'] = f'healthy ({loaded}/{len(model_info)} loaded)'
        except Exception as e:
            checks['ml_models'] = f'unhealthy: {e}'
        
        # Determine overall status
        unhealthy = any('unhealthy' in str(v) for v in checks.values())
        
        return Response({
            'status': 'unhealthy' if unhealthy else 'healthy',
            'timestamp': timezone.now().isoformat(),
            'checks': checks
        })


class APIVersionView(APIView):
    """Get API version information."""
    
    def get(self, request):
        return Response({
            'api': 'MEDIPREDICT Disease Prediction API',
            'version': '1.0.0',
            'documentation': f'{request.build_absolute_uri("/api/docs/")}',
            'endpoints': {
                'predictions': f'{request.build_absolute_uri("/api/predictions/")}',
                'health_reports': f'{request.build_absolute_uri("/api/health-reports/")}',
                'symptoms': f'{request.build_absolute_uri("/api/symptoms/")}',
            }
        })


class RateLimitInfoView(APIView):
    """Get rate limit information."""
    
    def get(self, request):
        return Response({
            'limits': {
                'authenticated': {
                    'hourly': 1000,
                    'daily': 10000,
                },
                'anonymous': {
                    'hourly': 100,
                    'daily': 1000,
                }
            },
            'current': {
                'user': request.user.username if request.user.is_authenticated else 'anonymous',
                'remaining': self.get_remaining(request)
            }
        })
    
    def get_remaining(self, request):
        """Get remaining rate limit."""
        # This is a simplified implementation
        # In production, use django-ratelimit or similar
        return 'unlimited'