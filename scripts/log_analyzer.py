#!/usr/bin/env python3
"""
Advanced log analysis for MediPredict
"""

import os
import sys
import re
import json
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import argparse
from pathlib import Path
import logging
import matplotlib.pyplot as plt
import pandas as pd
from io import StringIO
import numpy as np

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/log_analyzer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class LogAnalyzer:
    def __init__(self, logs_dir='logs'):
        self.logs_dir = Path(logs_dir)
        self.analysis_results = {}
        
    def analyze_performance(self, hours=24):
        """Analyze application performance from logs"""
        logger.info(f"Analyzing performance for last {hours} hours...")
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        performance_data = {
            'request_times': [],
            'endpoint_performance': defaultdict(list),
            'status_codes': Counter(),
            'error_rates': [],
            'slow_requests': []
        }
        
        # Analyze Django logs
        django_log = self.logs_dir / 'django.log'
        if django_log.exists():
            self._analyze_django_performance(django_log, cutoff_time, performance_data)
        
        # Analyze error logs
        error_log = self.logs_dir / 'errors.log'
        if error_log.exists():
            self._analyze_error_logs(error_log, cutoff_time, performance_data)
        
        # Generate insights
        insights = self._generate_performance_insights(performance_data)
        
        self.analysis_results['performance'] = {
            'data': performance_data,
            'insights': insights,
            'summary': self._create_performance_summary(performance_data)
        }
        
        # Generate visualization
        self._create_performance_visualization(performance_data)
        
        return self.analysis_results['performance']
    
    def _analyze_django_performance(self, log_file, cutoff_time, performance_data):
        """Analyze Django request performance"""
        logger.info(f"Analyzing Django logs: {log_file.name}")
        
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                # Extract timestamp
                timestamp_match = re.search(r'\[(.*?)\]', line)
                if not timestamp_match:
                    continue
                
                try:
                    log_time = datetime.strptime(timestamp_match.group(1), '%Y-%m-%d %H:%M:%S')
                except:
                    continue
                
                if log_time < cutoff_time:
                    continue
                
                # Extract request information
                if any(method in line for method in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']):
                    # Extract endpoint
                    endpoint_match = re.search(r'"(GET|POST|PUT|DELETE|PATCH) (.*?) HTTP', line)
                    if endpoint_match:
                        method = endpoint_match.group(1)
                        endpoint = endpoint_match.group(2)
                        
                        # Extract status code
                        status_match = re.search(r'HTTP.*? (\d{3})', line)
                        if status_match:
                            status_code = status_match.group(1)
                            performance_data['status_codes'][status_code] += 1
                        
                        # Extract response time
                        time_match = re.search(r'(\d+\.\d+) seconds', line)
                        if time_match:
                            response_time = float(time_match.group(1))
                            performance_data['request_times'].append(response_time)
                            performance_data['endpoint_performance'][endpoint].append(response_time)
                            
                            # Track slow requests
                            if response_time > 2.0:  # 2 seconds threshold
                                performance_data['slow_requests'].append({
                                    'time': log_time,
                                    'endpoint': endpoint,
                                    'method': method,
                                    'duration': response_time,
                                    'line': line.strip()[:200]
                                })
        
        logger.info(f"  Analyzed {len(performance_data['request_times'])} requests")
    
    def _analyze_error_logs(self, log_file, cutoff_time, performance_data):
        """Analyze error patterns"""
        logger.info(f"Analyzing error logs: {log_file.name}")
        
        error_counts = defaultdict(int)
        
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if 'ERROR' in line or 'CRITICAL' in line:
                    timestamp_match = re.search(r'\[(.*?)\]', line)
                    if timestamp_match:
                        try:
                            log_time = datetime.strptime(timestamp_match.group(1), '%Y-%m-%d %H:%M:%S')
                            if log_time < cutoff_time:
                                continue
                        except:
                            continue
                    
                    # Categorize errors
                    error_type = 'Other'
                    for category in ['DatabaseError', 'ValidationError', 'PermissionDenied',
                                   'TimeoutError', 'ConnectionError', 'FileNotFound',
                                   'ValueError', 'TypeError', 'AttributeError']:
                        if category in line:
                            error_type = category
                            break
                    
                    error_counts[error_type] += 1
        
        performance_data['error_counts'] = dict(error_counts)
        logger.info(f"  Found {sum(error_counts.values())} errors")
    
    def _generate_performance_insights(self, performance_data):
        """Generate performance insights"""
        insights = []
        
        if not performance_data['request_times']:
            return insights
        
        # Calculate metrics
        avg_response_time = np.mean(performance_data['request_times'])
        max_response_time = np.max(performance_data['request_times'])
        p95_response_time = np.percentile(performance_data['request_times'], 95)
        
        # Error rate
        total_requests = len(performance_data['request_times'])
        error_requests = (performance_data['status_codes'].get('500', 0) +
                         performance_data['status_codes'].get('502', 0) +
                         performance_data['status_codes'].get('503', 0) +
                         performance_data['status_codes'].get('504', 0))
        
        error_rate = (error_requests / total_requests * 100) if total_requests > 0 else 0
        
        # Generate insights
        if avg_response_time > 1.0:
            insights.append(f"High average response time: {avg_response_time:.2f}s")
        
        if p95_response_time > 3.0:
            insights.append(f"95th percentile response time is high: {p95_response_time:.2f}s")
        
        if error_rate > 5.0:
            insights.append(f"High error rate: {error_rate:.1f}%")
        
        if performance_data.get('error_counts'):
            top_error = max(performance_data['error_counts'].items(), key=lambda x: x[1])
            if top_error[1] > 10:
                insights.append(f"Frequent error type: {top_error[0]} ({top_error[1]} occurrences)")
        
        # Slow endpoints
        slow_endpoints = []
        for endpoint, times in performance_data['endpoint_performance'].items():
            avg_time = np.mean(times)
            if avg_time > 1.0 and len(times) > 10:
                slow_endpoints.append((endpoint, avg_time, len(times)))
        
        slow_endpoints.sort(key=lambda x: x[1], reverse=True)
        for endpoint, avg_time, count in slow_endpoints[:3]:
            insights.append(f"Slow endpoint: {endpoint} (avg: {avg_time:.2f}s, requests: {count})")
        
        return insights
    
    def _create_performance_summary(self, performance_data):
        """Create performance summary"""
        if not performance_data['request_times']:
            return {"message": "No performance data available"}
        
        summary = {
            'total_requests': len(performance_data['request_times']),
            'avg_response_time': np.mean(performance_data['request_times']),
            'max_response_time': np.max(performance_data['request_times']),
            'p95_response_time': np.percentile(performance_data['request_times'], 95),
            'status_codes': dict(performance_data['status_codes']),
            'slow_requests_count': len(performance_data['slow_requests']),
            'unique_endpoints': len(performance_data['endpoint_performance'])
        }
        
        if performance_data.get('error_counts'):
            summary['error_counts'] = performance_data['error_counts']
            summary['total_errors'] = sum(performance_data['error_counts'].values())
        
        return summary
    
    def _create_performance_visualization(self, performance_data):
        """Create performance visualizations"""
        if not performance_data['request_times']:
            return
        
        try:
            # Create output directory for visualizations
            viz_dir = self.logs_dir / 'visualizations'
            viz_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # 1. Response time distribution
            plt.figure(figsize=(10, 6))
            plt.hist(performance_data['request_times'], bins=50, alpha=0.7, color='blue', edgecolor='black')
            plt.xlabel('Response Time (seconds)')
            plt.ylabel('Frequency')
            plt.title('Response Time Distribution')
            plt.grid(True, alpha=0.3)
            
            # Add statistics
            stats_text = f"""
            Mean: {np.mean(performance_data['request_times']):.3f}s
            Max: {np.max(performance_data['request_times']):.3f}s
            P95: {np.percentile(performance_data['request_times'], 95):.3f}s
            Total: {len(performance_data['request_times'])} requests
            """
            plt.text(0.95, 0.95, stats_text, transform=plt.gca().transAxes,
                    fontsize=10, verticalalignment='top', horizontalalignment='right',
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
            
            plt.tight_layout()
            plt.savefig(viz_dir / f'response_time_distribution_{timestamp}.png', dpi=150)
            plt.close()
            
            # 2. Status code distribution
            if performance_data['status_codes']:
                plt.figure(figsize=(8, 6))
                codes, counts = zip(*performance_data['status_codes'].most_common())
                
                colors = []
                for code in codes:
                    if code.startswith('2'):
                        colors.append('green')
                    elif code.startswith('3'):
                        colors.append('blue')
                    elif code.startswith('4'):
                        colors.append('orange')
                    else:
                        colors.append('red')
                
                bars = plt.bar(range(len(codes)), counts, color=colors, alpha=0.7)
                plt.xlabel('Status Code')
                plt.ylabel('Count')
                plt.title('HTTP Status Code Distribution')
                plt.xticks(range(len(codes)), codes)
                
                # Add count labels on bars
                for bar, count in zip(bars, counts):
                    plt.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                            str(count), ha='center', va='bottom')
                
                plt.tight_layout()
                plt.savefig(viz_dir / f'status_codes_{timestamp}.png', dpi=150)
                plt.close()
            
            # 3. Error type distribution
            if performance_data.get('error_counts'):
                plt.figure(figsize=(10, 6))
                error_types, error_counts = zip(*sorted(
                    performance_data['error_counts'].items(),
                    key=lambda x: x[1], reverse=True
                ))
                
                bars = plt.barh(range(len(error_types)), error_counts, alpha=0.7, color='red')
                plt.xlabel('Error Count')
                plt.ylabel('Error Type')
                plt.title('Error Type Distribution')
                plt.yticks(range(len(error_types)), error_types)
                
                # Add count labels
                for i, (bar, count) in enumerate(zip(bars, error_counts)):
                    plt.text(count + max(error_counts)*0.01, i, str(count),
                            va='center')
                
                plt.tight_layout()
                plt.savefig(viz_dir / f'error_distribution_{timestamp}.png', dpi=150)
                plt.close()
            
            # 4. Top slow endpoints
            if performance_data['endpoint_performance']:
                # Calculate average times for each endpoint
                endpoint_avg_times = []
                for endpoint, times in performance_data['endpoint_performance'].items():
                    if len(times) >= 5:  # Only consider endpoints with sufficient data
                        endpoint_avg_times.append((endpoint, np.mean(times), len(times)))
                
                # Sort by average time and take top 10
                endpoint_avg_times.sort(key=lambda x: x[1], reverse=True)
                top_endpoints = endpoint_avg_times[:10]
                
                if top_endpoints:
                    plt.figure(figsize=(12, 8))
                    endpoints, avg_times, request_counts = zip(*top_endpoints)
                    
                    # Truncate endpoint names for display
                    display_endpoints = []
                    for endpoint in endpoints:
                        if len(endpoint) > 50:
                            display_endpoints.append(endpoint[:47] + '...')
                        else:
                            display_endpoints.append(endpoint)
                    
                    y_pos = np.arange(len(display_endpoints))
                    
                    # Create bars
                    bars = plt.barh(y_pos, avg_times, alpha=0.7, color='orange')
                    
                    # Add request count as text
                    for i, (bar, count) in enumerate(zip(bars, request_counts)):
                        plt.text(bar.get_width() + max(avg_times)*0.01, i,
                                f'({count} requests)', va='center')
                    
                    plt.xlabel('Average Response Time (seconds)')
                    plt.ylabel('Endpoint')
                    plt.title('Top 10 Slowest Endpoints')
                    plt.yticks(y_pos, display_endpoints)
                    
                    plt.tight_layout()
                    plt.savefig(viz_dir / f'slow_endpoints_{timestamp}.png', dpi=150)
                    plt.close()
            
            logger.info(f"Visualizations saved to: {viz_dir}")
            
        except Exception as e:
            logger.error(f"Error creating visualizations: {e}")
    
    def analyze_security(self, days=7):
        """Analyze security-related logs"""
        logger.info(f"Analyzing security logs for last {days} days...")
        
        cutoff_time = datetime.now() - timedelta(days=days)
        
        security_data = {
            'failed_logins': [],
            'suspicious_ips': Counter(),
            'access_violations': [],
            'brute_force_attempts': [],
            'security_events': []
        }
        
        # Analyze all logs for security events
        for log_file in self.logs_dir.glob('*.log'):
            if log_file.stat().st_size == 0:
                continue
            
            self._analyze_security_events(log_file, cutoff_time, security_data)
        
        # Generate security report
        report = self._generate_security_report(security_data)
        
        self.analysis_results['security'] = {
            'data': security_data,
            'report': report
        }
        
        return self.analysis_results['security']
    
    def _analyze_security_events(self, log_file, cutoff_time, security_data):
        """Analyze security events in log file"""
        security_patterns = {
            'failed_login': [
                'Invalid login', 'Failed login', 'Authentication failed',
                'Invalid credentials', 'Login attempt failed'
            ],
            'brute_force': [
                'Too many login attempts', 'Rate limit exceeded',
                'Multiple failed logins', 'Brute force'
            ],
            'access_violation': [
                'Permission denied', 'Access denied', 'Forbidden',
                'Unauthorized access', 'Security violation'
            ],
            'suspicious_activity': [
                'SQL injection', 'XSS', 'CSRF', 'Malicious',
                'Suspicious request', 'Attack attempt'
            ]
        }
        
        ip_pattern = r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'
        
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                # Check timestamp
                timestamp_match = re.search(r'\[(.*?)\]', line)
                if timestamp_match:
                    try:
                        log_time = datetime.strptime(timestamp_match.group(1), '%Y-%m-%d %H:%M:%S')
                        if log_time < cutoff_time:
                            continue
                    except:
                        continue
                
                # Extract IP address
                ip_match = re.search(ip_pattern, line)
                ip_address = ip_match.group(0) if ip_match else 'Unknown'
                
                # Check for security patterns
                for event_type, patterns in security_patterns.items():
                    for pattern in patterns:
                        if pattern.lower() in line.lower():
                            event = {
                                'timestamp': timestamp_match.group(1) if timestamp_match else 'Unknown',
                                'file': log_file.name,
                                'line': line_num,
                                'event_type': event_type,
                                'ip_address': ip_address,
                                'message': line.strip()[:200]
                            }
                            
                            security_data['security_events'].append(event)
                            
                            if ip_address != 'Unknown':
                                security_data['suspicious_ips'][ip_address] += 1
                            
                            if event_type == 'failed_login':
                                security_data['failed_logins'].append(event)
                            elif event_type == 'brute_force':
                                security_data['brute_force_attempts'].append(event)
                            elif event_type == 'access_violation':
                                security_data['access_violations'].append(event)
                            
                            break
    
    def _generate_security_report(self, security_data):
        """Generate security report"""
        report = {
            'summary': {
                'total_security_events': len(security_data['security_events']),
                'failed_logins': len(security_data['failed_logins']),
                'brute_force_attempts': len(security_data['brute_force_attempts']),
                'access_violations': len(security_data['access_violations']),
                'unique_suspicious_ips': len(security_data['suspicious_ips'])
            },
            'top_suspicious_ips': dict(security_data['suspicious_ips'].most_common(10)),
            'recommendations': [],
            'risk_level': 'Low'
        }
        
        # Calculate risk level
        total_events = report['summary']['total_security_events']
        brute_force_attempts = report['summary']['brute_force_attempts']
        
        if brute_force_attempts > 10 or total_events > 50:
            report['risk_level'] = 'High'
        elif brute_force_attempts > 5 or total_events > 20:
            report['risk_level'] = 'Medium'
        
        # Generate recommendations
        if report['summary']['failed_logins'] > 20:
            report['recommendations'].append(
                "High number of failed logins detected. Consider implementing account lockout policy."
            )
        
        if report['summary']['brute_force_attempts'] > 0:
            report['recommendations'].append(
                "Brute force attempts detected. Enable rate limiting for login endpoints."
            )
        
        if report['summary']['unique_suspicious_ips'] > 5:
            report['recommendations'].append(
                "Multiple suspicious IP addresses detected. Consider implementing IP blocking rules."
            )
        
        if report['summary']['access_violations'] > 10:
            report['recommendations'].append(
                "Multiple access violations detected. Review user permissions and access controls."
            )
        
        return report
    
    def analyze_user_activity(self, days=30):
        """Analyze user activity patterns"""
        logger.info(f"Analyzing user activity for last {days} days...")
        
        cutoff_time = datetime.now() - timedelta(days=days)
        
        activity_data = {
            'user_sessions': defaultdict(list),
            'peak_hours': Counter(),
            'popular_endpoints': Counter(),
            'user_agents': Counter(),
            'geographic_data': defaultdict(int)  # Would need IP geolocation
        }
        
        # This is a simplified analysis - in production you'd want more detailed tracking
        for log_file in [self.logs_dir / 'django.log', self.logs_dir / 'requests.log']:
            if not log_file.exists():
                continue
            
            self._analyze_user_activity(log_file, cutoff_time, activity_data)
        
        # Generate activity insights
        insights = self._generate_activity_insights(activity_data)
        
        self.analysis_results['user_activity'] = {
            'data': activity_data,
            'insights': insights,
            'summary': self._create_activity_summary(activity_data)
        }
        
        return self.analysis_results['user_activity']
    
    def _analyze_user_activity(self, log_file, cutoff_time, activity_data):
        """Analyze user activity in log file"""
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                # Extract timestamp
                timestamp_match = re.search(r'\[(.*?)\]', line)
                if not timestamp_match:
                    continue
                
                try:
                    log_time = datetime.strptime(timestamp_match.group(1), '%Y-%m-%d %H:%M:%S')
                except:
                    continue
                
                if log_time < cutoff_time:
                    continue
                
                # Track peak hours
                hour_key = log_time.strftime('%H:00')
                activity_data['peak_hours'][hour_key] += 1
                
                # Extract user information (simplified)
                user_match = re.search(r'user[=:]\s*(\w+)', line, re.IGNORECASE)
                if user_match:
                    username = user_match.group(1)
                    activity_data['user_sessions'][username].append(log_time)
                
                # Extract endpoint
                endpoint_match = re.search(r'"(GET|POST|PUT|DELETE|PATCH) (.*?) HTTP', line)
                if endpoint_match:
                    endpoint = endpoint_match.group(2)
                    activity_data['popular_endpoints'][endpoint] += 1
                
                # Extract user agent
                ua_match = re.search(r'User-Agent:\s*(.*)', line)
                if ua_match:
                    user_agent = ua_match.group(1)
                    # Simplify user agent
                    if 'Mozilla' in user_agent:
                        simplified = 'Browser'
                    elif 'curl' in user_agent.lower():
                        simplified = 'cURL'
                    elif 'python' in user_agent.lower():
                        simplified = 'Python'
                    elif 'postman' in user_agent.lower():
                        simplified = 'Postman'
                    else:
                        simplified = 'Other'
                    
                    activity_data['user_agents'][simplified] += 1
    
    def _generate_activity_insights(self, activity_data):
        """Generate activity insights"""
        insights = []
        
        # Peak hours
        if activity_data['peak_hours']:
            peak_hour, peak_count = activity_data['peak_hours'].most_common(1)[0]
            insights.append(f"Peak activity hour: {peak_hour} ({peak_count} requests)")
        
        # Active users
        if activity_data['user_sessions']:
            active_users = len(activity_data['user_sessions'])
            insights.append(f"Active users: {active_users}")
            
            # Most active user
            user_activity = {user: len(sessions) for user, sessions in activity_data['user_sessions'].items()}
            if user_activity:
                most_active_user, user_count = max(user_activity.items(), key=lambda x: x[1])
                insights.append(f"Most active user: {most_active_user} ({user_count} sessions)")
        
        # Popular endpoints
        if activity_data['popular_endpoints']:
            popular_endpoint, endpoint_count = activity_data['popular_endpoints'].most_common(1)[0]
            insights.append(f"Most popular endpoint: {popular_endpoint[:50]} ({endpoint_count} requests)")
        
        # User agents
        if activity_data['user_agents']:
            insights.append("Client distribution:")
            for client, count in activity_data['user_agents'].most_common():
                insights.append(f"  - {client}: {count}")
        
        return insights
    
    def _create_activity_summary(self, activity_data):
        """Create activity summary"""
        summary = {
            'total_requests': sum(activity_data['peak_hours'].values()),
            'unique_users': len(activity_data['user_sessions']),
            'unique_endpoints': len(activity_data['popular_endpoints']),
            'peak_hour': activity_data['peak_hours'].most_common(1)[0] if activity_data['peak_hours'] else None,
            'top_endpoints': dict(activity_data['popular_endpoints'].most_common(10)),
            'client_distribution': dict(activity_data['user_agents'])
        }
        
        # Calculate user session statistics
        if activity_data['user_sessions']:
            session_counts = [len(sessions) for sessions in activity_data['user_sessions'].values()]
            summary['user_sessions'] = {
                'total_sessions': sum(session_counts),
                'avg_sessions_per_user': np.mean(session_counts) if session_counts else 0,
                'max_sessions_per_user': max(session_counts) if session_counts else 0
            }
        
        return summary
    
    def generate_comprehensive_report(self, output_file=None):
        """Generate comprehensive analysis report"""
        logger.info("Generating comprehensive analysis report...")
        
        # Run all analyses
        performance = self.analyze_performance(hours=24)
        security = self.analyze_security(days=7)
        activity = self.analyze_user_activity(days=30)
        
        # Create comprehensive report
        report = {
            'generated_at': datetime.now().isoformat(),
            'overview': {
                'performance_risk': self._assess_risk_level(performance),
                'security_risk': security['report']['risk_level'],
                'system_health': self._assess_system_health(performance, security, activity)
            },
            'performance_analysis': performance,
            'security_analysis': security,
            'user_activity_analysis': activity,
            'recommendations': self._generate_overall_recommendations(performance, security, activity),
            'executive_summary': self._create_executive_summary(performance, security, activity)
        }
        
        # Save report
        if output_file is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = self.logs_dir / 'reports' / f'comprehensive_analysis_{timestamp}.json'
        
        output_file.parent.mkdir(exist_ok=True, parents=True)
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        # Create human-readable version
        text_report = self._create_text_report(report)
        text_report_file = output_file.with_suffix('.txt')
        text_report_file.write_text(text_report)
        
        logger.info(f"✅ Comprehensive report generated: {output_file}")
        logger.info(f"📄 Text version: {text_report_file}")
        
        # Print executive summary
        print("\n" + "="*80)
        print("EXECUTIVE SUMMARY")
        print("="*80)
        print(text_report.split('EXECUTIVE SUMMARY')[1].split('='*80)[0])
        print("="*80)
        
        return report
    
    def _assess_risk_level(self, performance_data):
        """Assess performance risk level"""
        if not performance_data['summary']:
            return 'Unknown'
        
        avg_response_time = performance_data['summary']['avg_response_time']
        p95_response_time = performance_data['summary']['p95_response_time']
        error_count = performance_data['summary'].get('total_errors', 0)
        
        if avg_response_time > 2.0 or p95_response_time > 5.0 or error_count > 20:
            return 'High'
        elif avg_response_time > 1.0 or p95_response_time > 3.0 or error_count > 10:
            return 'Medium'
        else:
            return 'Low'
    
    def _assess_system_health(self, performance, security, activity):
        """Assess overall system health"""
        performance_risk = self._assess_risk_level(performance)
        security_risk = security['report']['risk_level']
        
        if performance_risk == 'High' or security_risk == 'High':
            return 'Poor'
        elif performance_risk == 'Medium' or security_risk == 'Medium':
            return 'Fair'
        else:
            return 'Good'
    
    def _generate_overall_recommendations(self, performance, security, activity):
        """Generate overall recommendations"""
        recommendations = []
        
        # Performance recommendations
        if performance['insights']:
            recommendations.extend(performance['insights'])
        
        # Security recommendations
        recommendations.extend(security['report']['recommendations'])
        
        # Activity-based recommendations
        if activity['summary']['total_requests'] > 10000:
            recommendations.append("High traffic volume detected. Consider scaling infrastructure.")
        
        if activity['summary'].get('user_sessions', {}).get('max_sessions_per_user', 0) > 100:
            recommendations.append("Some users have unusually high session counts. Investigate for bot activity.")
        
        return recommendations
    
    def _create_executive_summary(self, performance, security, activity):
        """Create executive summary"""
        summary = []
        
        # Performance
        if performance['summary']:
            avg_response = performance['summary']['avg_response_time']
            total_requests = performance['summary']['total_requests']
            summary.append(f"• Performance: {avg_response:.2f}s average response time across {total_requests:,} requests")
        
        # Security
        security_events = security['report']['summary']['total_security_events']
        risk_level = security['report']['risk_level']
        summary.append(f"• Security: {security_events} security events detected (Risk: {risk_level})")
        
        # Activity
        if activity['summary']:
            unique_users = activity['summary']['unique_users']
            total_reqs = activity['summary']['total_requests']
            summary.append(f"• Activity: {unique_users} unique users generated {total_reqs:,} requests")
        
        # System health
        system_health = self._assess_system_health(performance, security, activity)
        summary.append(f"• System Health: {system_health}")
        
        return "\n".join(summary)
    
    def _create_text_report(self, report):
        """Create human-readable text report"""
        lines = []
        lines.append("="*80)
        lines.append("MEDIPREDICT COMPREHENSIVE LOG ANALYSIS REPORT")
        lines.append("="*80)
        lines.append(f"Generated: {report['generated_at']}")
        lines.append("")
        
        # Overview
        lines.append("OVERVIEW")
        lines.append("-"*40)
        lines.append(f"Performance Risk: {report['overview']['performance_risk']}")
        lines.append(f"Security Risk: {report['overview']['security_risk']}")
        lines.append(f"System Health: {report['overview']['system_health']}")
        lines.append("")
        
        # Executive Summary
        lines.append("EXECUTIVE SUMMARY")
        lines.append("-"*40)
        lines.append(report['executive_summary'])
        lines.append("")
        
        # Performance Analysis
        lines.append("PERFORMANCE ANALYSIS")
        lines.append("-"*40)
        if report['performance_analysis']['summary']:
            perf = report['performance_analysis']['summary']
            lines.append(f"Total Requests: {perf['total_requests']:,}")
            lines.append(f"Average Response Time: {perf['avg_response_time']:.3f}s")
            lines.append(f"95th Percentile: {perf['p95_response_time']:.3f}s")
            lines.append(f"Max Response Time: {perf['max_response_time']:.3f}s")
            lines.append(f"Slow Requests (>2s): {perf['slow_requests_count']}")
        lines.append("")
        
        # Security Analysis
        lines.append("SECURITY ANALYSIS")
        lines.append("-"*40)
        if report['security_analysis']['report']:
            sec = report['security_analysis']['report']['summary']
            lines.append(f"Total Security Events: {sec['total_security_events']}")
            lines.append(f"Failed Logins: {sec['failed_logins']}")
            lines.append(f"Brute Force Attempts: {sec['brute_force_attempts']}")
            lines.append(f"Access Violations: {sec['access_violations']}")
            lines.append(f"Suspicious IPs: {sec['unique_suspicious_ips']}")
        lines.append("")
        
        # User Activity
        lines.append("USER ACTIVITY ANALYSIS")
        lines.append("-"*40)
        if report['user_activity_analysis']['summary']:
            act = report['user_activity_analysis']['summary']
            lines.append(f"Total Requests: {act['total_requests']:,}")
            lines.append(f"Unique Users: {act['unique_users']}")
            lines.append(f"Unique Endpoints: {act['unique_endpoints']}")
        lines.append("")
        
        # Recommendations
        lines.append("RECOMMENDATIONS")
        lines.append("-"*40)
        for i, rec in enumerate(report['recommendations'], 1):
            lines.append(f"{i}. {rec}")
        lines.append("")
        
        lines.append("="*80)
        lines.append("End of Report")
        lines.append("="*80)
        
        return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description='MediPredict Log Analyzer')
    parser.add_argument('--performance', action='store_true',
                       help='Analyze performance')
    parser.add_argument('--security', action='store_true',
                       help='Analyze security')
    parser.add_argument('--activity', action='store_true',
                       help='Analyze user activity')
    parser.add_argument('--comprehensive', action='store_true',
                       help='Generate comprehensive report')
    parser.add_argument('--hours', type=int, default=24,
                       help='Hours to analyze for performance (default: 24)')
    parser.add_argument('--days', type=int, default=7,
                       help='Days to analyze for security/activity (default: 7)')
    parser.add_argument('--output', help='Output file for report')
    parser.add_argument('--visualize', action='store_true',
                       help='Generate visualizations')
    
    args = parser.parse_args()
    
    analyzer = LogAnalyzer()
    
    if args.comprehensive:
        analyzer.generate_comprehensive_report(args.output)
    else:
        if args.performance:
            analyzer.analyze_performance(hours=args.hours)
        
        if args.security:
            analyzer.analyze_security(days=args.days)
        
        if args.activity:
            analyzer.analyze_user_activity(days=args.days)
        
        if not any([args.performance, args.security, args.activity, args.comprehensive]):
            parser.print_help()

if __name__ == '__main__':
    main()