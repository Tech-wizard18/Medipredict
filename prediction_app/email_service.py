from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags
import logging
from typing import List, Dict, Any, Optional
from celery import shared_task

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails related to predictions."""
    
    @staticmethod
    def send_prediction_result(user_email: str, prediction_data: Dict[str, Any]) -> bool:
        """Send prediction result email."""
        try:
            subject = f"MEDIPREDICT - Your {prediction_data['disease']} Prediction Result"
            
            # Render HTML template
            html_content = render_to_string('prediction_app/emails/prediction_result.html', {
                'user_email': user_email,
                'prediction': prediction_data,
                'site_url': settings.SITE_URL
            })
            
            # Create plain text version
            text_content = strip_tags(html_content)
            
            # Send email
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user_email]
            )
            email.attach_alternative(html_content, "text/html")
            email.send()
            
            logger.info(f"Prediction result email sent to {user_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send prediction email: {e}")
            return False
    
    @staticmethod
    def send_health_report(user_email: str, report_data: Dict[str, Any]) -> bool:
        """Send health report email."""
        try:
            subject = f"MEDIPREDICT - Your Health Report ({report_data['report_date']})"
            
            html_content = render_to_string('prediction_app/emails/health_report.html', {
                'user_email': user_email,
                'report': report_data,
                'site_url': settings.SITE_URL
            })
            
            text_content = strip_tags(html_content)
            
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user_email]
            )
            email.attach_alternative(html_content, "text/html")
            
            # Attach PDF if available
            if 'pdf_path' in report_data:
                try:
                    with open(report_data['pdf_path'], 'rb') as f:
                        email.attach('health_report.pdf', f.read(), 'application/pdf')
                except Exception as e:
                    logger.warning(f"Could not attach PDF: {e}")
            
            email.send()
            
            logger.info(f"Health report email sent to {user_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send health report email: {e}")
            return False
    
    @staticmethod
    def send_weekly_summary(user_email: str, summary_data: Dict[str, Any]) -> bool:
        """Send weekly summary email."""
        try:
            subject = "MEDIPREDICT - Your Weekly Health Summary"
            
            html_content = render_to_string('prediction_app/emails/weekly_summary.html', {
                'user_email': user_email,
                'summary': summary_data,
                'site_url': settings.SITE_URL
            })
            
            text_content = strip_tags(html_content)
            
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user_email]
            )
            email.attach_alternative(html_content, "text/html")
            email.send()
            
            logger.info(f"Weekly summary email sent to {user_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send weekly summary email: {e}")
            return False
    
    @staticmethod
    def send_alert(user_email: str, alert_type: str, alert_data: Dict[str, Any]) -> bool:
        """Send alert email."""
        try:
            alert_subjects = {
                'high_risk': "MEDIPREDICT - High Risk Alert",
                'abnormal_result': "MEDIPREDICT - Abnormal Test Result",
                'system_update': "MEDIPREDICT - System Update",
                'data_breach': "MEDIPREDICT - Security Alert",
            }
            
            subject = alert_subjects.get(alert_type, "MEDIPREDICT Alert")
            
            html_content = render_to_string('prediction_app/emails/alert.html', {
                'user_email': user_email,
                'alert_type': alert_type,
                'alert_data': alert_data,
                'site_url': settings.SITE_URL
            })
            
            text_content = strip_tags(html_content)
            
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user_email]
            )
            email.attach_alternative(html_content, "text/html")
            email.send()
            
            logger.info(f"Alert email ({alert_type}) sent to {user_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send alert email: {e}")
            return False
    
    @staticmethod
    def send_bulk_emails(emails: List[str], subject: str, template_name: str, 
                        context: Dict[str, Any]) -> Dict[str, int]:
        """Send bulk emails."""
        results = {'sent': 0, 'failed': 0}
        
        for email in emails:
            try:
                html_content = render_to_string(template_name, context)
                text_content = strip_tags(html_content)
                
                email_msg = EmailMultiAlternatives(
                    subject=subject,
                    body=text_content,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[email]
                )
                email_msg.attach_alternative(html_content, "text/html")
                email_msg.send()
                
                results['sent'] += 1
                logger.info(f"Bulk email sent to {email}")
                
            except Exception as e:
                results['failed'] += 1
                logger.error(f"Failed to send bulk email to {email}: {e}")
        
        return results
    
    @staticmethod
    def send_welcome_email(user_email: str, user_name: str) -> bool:
        """Send welcome email to new user."""
        try:
            subject = "Welcome to MEDIPREDICT - Your Health Prediction Platform"
            
            html_content = render_to_string('prediction_app/emails/welcome.html', {
                'user_name': user_name,
                'user_email': user_email,
                'site_url': settings.SITE_URL
            })
            
            text_content = strip_tags(html_content)
            
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user_email]
            )
            email.attach_alternative(html_content, "text/html")
            email.send()
            
            logger.info(f"Welcome email sent to {user_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send welcome email: {e}")
            return False
    
    @staticmethod
    def send_password_reset(user_email: str, reset_link: str) -> bool:
        """Send password reset email."""
        try:
            subject = "MEDIPREDICT - Password Reset Request"
            
            html_content = render_to_string('prediction_app/emails/password_reset.html', {
                'user_email': user_email,
                'reset_link': reset_link,
                'site_url': settings.SITE_URL
            })
            
            text_content = strip_tags(html_content)
            
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user_email]
            )
            email.attach_alternative(html_content, "text/html")
            email.send()
            
            logger.info(f"Password reset email sent to {user_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send password reset email: {e}")
            return False


@shared_task
def send_prediction_email_async(user_email: str, prediction_data: Dict[str, Any]) -> bool:
    """Send prediction email asynchronously."""
    return EmailService.send_prediction_result(user_email, prediction_data)


@shared_task
def send_health_report_email_async(user_email: str, report_data: Dict[str, Any]) -> bool:
    """Send health report email asynchronously."""
    return EmailService.send_health_report(user_email, report_data)


@shared_task
def send_weekly_summary_async(user_email: str, summary_data: Dict[str, Any]) -> bool:
    """Send weekly summary email asynchronously."""
    return EmailService.send_weekly_summary(user_email, summary_data)


@shared_task
def send_bulk_emails_async(emails: List[str], subject: str, 
                          template_name: str, context: Dict[str, Any]) -> Dict[str, int]:
    """Send bulk emails asynchronously."""
    return EmailService.send_bulk_emails(emails, subject, template_name, context)


class EmailTemplateManager:
    """Manage email templates."""
    
    @staticmethod
    def get_template_variables(template_name: str) -> List[str]:
        """Get required variables for a template."""
        templates = {
            'prediction_result.html': ['user_email', 'prediction', 'site_url'],
            'health_report.html': ['user_email', 'report', 'site_url'],
            'weekly_summary.html': ['user_email', 'summary', 'site_url'],
            'alert.html': ['user_email', 'alert_type', 'alert_data', 'site_url'],
            'welcome.html': ['user_name', 'user_email', 'site_url'],
            'password_reset.html': ['user_email', 'reset_link', 'site_url'],
        }
        
        return templates.get(template_name, [])
    
    @staticmethod
    def validate_template_data(template_name: str, data: Dict[str, Any]) -> bool:
        """Validate data for email template."""
        required_vars = EmailTemplateManager.get_template_variables(template_name)
        
        for var in required_vars:
            if var not in data:
                logger.error(f"Missing required variable {var} for template {template_name}")
                return False
        
        return True
    
    @staticmethod
    def preview_template(template_name: str, data: Dict[str, Any]) -> str:
        """Preview email template with data."""
        try:
            return render_to_string(f'prediction_app/emails/{template_name}', data)
        except Exception as e:
            logger.error(f"Failed to preview template {template_name}: {e}")
            return ""