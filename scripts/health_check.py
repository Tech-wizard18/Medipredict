#!/usr/bin/env python3
"""
System Health Check Script for MEDIPREDICT
Monitors system health, service status, and application metrics.
"""

import os
import sys
import time
import json
import socket
import psutil
import requests
import logging
import smtplib
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import django
from django.conf import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/health_check.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class HealthChecker:
    """Main class for system health monitoring."""
    
    def __init__(self, config_file='health_config.json'):
        self.project_root = Path(__file__).parent.parent
        self.config_file = self.project_root / 'config' / config_file
        self.health_data = {}
        self.alerts = []
        
        # Load configuration
        self.config = self.load_config()
        
        # Initialize Django for database checks
        try:
            sys.path.append(str(self.project_root))
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'disease_app.settings')
            django.setup()
        except Exception as e:
            logger.warning(f"Django setup failed: {e}")
    
    def load_config(self) -> Dict:
        """Load health check configuration."""
        default_config = {
            'thresholds': {
                'cpu_percent': 80,
                'memory_percent': 85,
                'disk_percent': 90,
                'response_time': 5.0,  # seconds
                'error_rate': 0.05,  # 5%
                'queue_size': 100
            },
            'monitoring': {
                'check_interval': 300,  # 5 minutes
                'retention_days': 30,
                'alert_cooldown': 3600  # 1 hour
            },
            'alerts': {
                'enabled': True,
                'email': {
                    'enabled': True,
                    'recipients': ['admin@medipredict.example.com'],
                    'smtp_server': 'smtp.gmail.com',
                    'smtp_port': 587
                },
                'slack': {
                    'enabled': False,
                    'webhook_url': ''
                },
                'telegram': {
                    'enabled': False,
                    'bot_token': '',
                    'chat_id': ''
                }
            },
            'endpoints': [
                {
                    'name': 'Main Application',
                    'url': 'http://localhost:8000/health/',
                    'method': 'GET',
                    'expected_status': 200
                },
                {
                    'name': 'API Health',
                    'url': 'http://localhost:8000/api/health/',
                    'method': 'GET',
                    'expected_status': 200
                },
                {
                    'name': 'Admin Interface',
                    'url': 'http://localhost:8000/admin/',
                    'method': 'GET',
                    'expected_status': 200
                }
            ],
            'services': [
                'postgresql',
                'redis',
                'celery',
                'nginx',
                'gunicorn'
            ]
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    user_config = json.load(f)
                    # Merge with default config
                    default_config.update(user_config)
            except Exception as e:
                logger.error(f"Error loading config: {e}")
        
        return default_config
    
    def check_system_resources(self) -> Dict[str, Any]:
        """Check system resource usage."""
        resources = {
            'timestamp': datetime.now().isoformat(),
            'cpu': {},
            'memory': {},
            'disk': {},
            'network': {},
            'processes': {}
        }
        
        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            
            resources['cpu'] = {
                'percent': cpu_percent,
                'count': cpu_count,
                'frequency': cpu_freq.current if cpu_freq else None,
                'status': 'OK' if cpu_percent < self.config['thresholds']['cpu_percent'] else 'WARNING'
            }
            
            if cpu_percent >= self.config['thresholds']['cpu_percent']:
                self.add_alert('CPU', f"CPU usage high: {cpu_percent}%")
            
            # Memory
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            resources['memory'] = {
                'total_gb': memory.total / (1024 ** 3),
                'available_gb': memory.available / (1024 ** 3),
                'percent': memory.percent,
                'swap_percent': swap.percent,
                'status': 'OK' if memory.percent < self.config['thresholds']['memory_percent'] else 'WARNING'
            }
            
            if memory.percent >= self.config['thresholds']['memory_percent']:
                self.add_alert('Memory', f"Memory usage high: {memory.percent}%")
            
            # Disk
            disk = psutil.disk_usage('/')
            disk_io = psutil.disk_io_counters()
            
            resources['disk'] = {
                'total_gb': disk.total / (1024 ** 3),
                'free_gb': disk.free / (1024 ** 3),
                'percent': disk.percent,
                'read_bytes': disk_io.read_bytes if disk_io else 0,
                'write_bytes': disk_io.write_bytes if disk_io else 0,
                'status': 'OK' if disk.percent < self.config['thresholds']['disk_percent'] else 'WARNING'
            }
            
            if disk.percent >= self.config['thresholds']['disk_percent']:
                self.add_alert('Disk', f"Disk usage high: {disk.percent}%")
            
            # Network
            net_io = psutil.net_io_counters()
            
            resources['network'] = {
                'bytes_sent': net_io.bytes_sent,
                'bytes_recv': net_io.bytes_recv,
                'packets_sent': net_io.packets_sent,
                'packets_recv': net_io.packets_recv,
                'status': 'OK'
            }
            
            # Processes
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    proc_info = proc.info
                    processes.append({
                        'pid': proc_info['pid'],
                        'name': proc_info['name'],
                        'cpu': proc_info['cpu_percent'],
                        'memory': proc_info['memory_percent']
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            resources['processes'] = sorted(processes, key=lambda x: x['cpu'], reverse=True)[:10]
            
        except Exception as e:
            logger.error(f"System resource check failed: {e}")
            resources['error'] = str(e)
        
        return resources
    
    def check_services(self) -> Dict[str, Any]:
        """Check status of required services."""
        services_status = {
            'timestamp': datetime.now().isoformat(),
            'services': {}
        }
        
        for service_name in self.config['services']:
            status = self.check_service_status(service_name)
            services_status['services'][service_name] = status
            
            if not status['running']:
                self.add_alert('Service', f"Service {service_name} is not running")
        
        return services_status
    
    def check_service_status(self, service_name: str) -> Dict[str, Any]:
        """Check individual service status."""
        status = {
            'name': service_name,
            'running': False,
            'uptime': None,
            'memory_mb': None,
            'cpu_percent': None
        }
        
        try:
            # Check using systemctl for Linux
            import subprocess
            result = subprocess.run(
                ['systemctl', 'is-active', service_name],
                capture_output=True,
                text=True
            )
            
            status['running'] = result.stdout.strip() == 'active'
            
            if status['running']:
                # Get service details
                result = subprocess.run(
                    ['systemctl', 'show', service_name, '--property=ActiveEnterTimestamp'],
                    capture_output=True,
                    text=True
                )
                
                if result.stdout:
                    timestamp_str = result.stdout.strip().split('=')[1]
                    # Parse timestamp (simplified)
                    status['uptime'] = timestamp_str
                
                # Find process and get resource usage
                for proc in psutil.process_iter(['name', 'pid', 'cpu_percent', 'memory_info']):
                    try:
                        if service_name in proc.info['name'].lower():
                            proc_info = proc.info
                            status['pid'] = proc_info['pid']
                            status['cpu_percent'] = proc_info['cpu_percent']
                            if proc_info['memory_info']:
                                status['memory_mb'] = proc_info['memory_info'].rss / (1024 ** 2)
                            break
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
        
        except Exception as e:
            logger.error(f"Service check failed for {service_name}: {e}")
            status['error'] = str(e)
        
        return status
    
    def check_endpoints(self) -> Dict[str, Any]:
        """Check application endpoints."""
        endpoints_status = {
            'timestamp': datetime.now().isoformat(),
            'endpoints': {},
            'summary': {
                'total': 0,
                'healthy': 0,
                'unhealthy': 0,
                'avg_response_time': 0
            }
        }
        
        total_response_time = 0
        healthy_count = 0
        
        for endpoint in self.config['endpoints']:
            result = self.check_endpoint(endpoint)
            endpoints_status['endpoints'][endpoint['name']] = result
            
            endpoints_status['summary']['total'] += 1
            
            if result['status'] == 'healthy':
                healthy_count += 1
                total_response_time += result['response_time']
            
            if result['status'] == 'unhealthy':
                self.add_alert('Endpoint', 
                             f"Endpoint {endpoint['name']} ({endpoint['url']}) is unhealthy")
        
        if healthy_count > 0:
            endpoints_status['summary']['avg_response_time'] = total_response_time / healthy_count
        
        endpoints_status['summary']['healthy'] = healthy_count
        endpoints_status['summary']['unhealthy'] = endpoints_status['summary']['total'] - healthy_count
        
        return endpoints_status
    
    def check_endpoint(self, endpoint: Dict) -> Dict[str, Any]:
        """Check individual endpoint."""
        result = {
            'name': endpoint['name'],
            'url': endpoint['url'],
            'method': endpoint['method'],
            'expected_status': endpoint['expected_status'],
            'status': 'unknown',
            'response_time': None,
            'http_status': None,
            'error': None
        }
        
        try:
            start_time = time.time()
            response = requests.request(
                endpoint['method'],
                endpoint['url'],
                timeout=10,
                headers={'User-Agent': 'MEDIPREDICT-Health-Check'}
            )
            response_time = time.time() - start_time
            
            result['response_time'] = response_time
            result['http_status'] = response.status_code
            
            if response.status_code == endpoint['expected_status']:
                result['status'] = 'healthy'
            else:
                result['status'] = 'unhealthy'
                result['error'] = f"HTTP {response.status_code}"
            
            # Check response time threshold
            if response_time > self.config['thresholds']['response_time']:
                result['status'] = 'warning'
                result['warning'] = f"Slow response: {response_time:.2f}s"
        
        except requests.exceptions.Timeout:
            result['status'] = 'unhealthy'
            result['error'] = 'Timeout'
            self.add_alert('Endpoint', f"Endpoint {endpoint['name']} timeout")
        
        except requests.exceptions.ConnectionError:
            result['status'] = 'unhealthy'
            result['error'] = 'Connection refused'
            self.add_alert('Endpoint', f"Endpoint {endpoint['name']} connection refused")
        
        except Exception as e:
            result['status'] = 'unhealthy'
            result['error'] = str(e)
            self.add_alert('Endpoint', f"Endpoint {endpoint['name']} error: {e}")
        
        return result
    
    def check_database(self) -> Dict[str, Any]:
        """Check database connectivity and performance."""
        db_status = {
            'timestamp': datetime.now().isoformat(),
            'connected': False,
            'tables': [],
            'size_mb': None,
            'query_time': None
        }
        
        try:
            from django.db import connection
            
            # Test connection
            with connection.cursor() as cursor:
                start_time = time.time()
                cursor.execute("SELECT 1")
                db_status['query_time'] = time.time() - start_time
                db_status['connected'] = True
                
                # Get table information
                cursor.execute("""
                    SELECT tablename 
                    FROM pg_tables 
                    WHERE schemaname = 'public'
                    ORDER BY tablename
                """)
                db_status['tables'] = [row[0] for row in cursor.fetchall()]
                
                # Get database size
                cursor.execute("""
                    SELECT pg_database_size(current_database()) / (1024 * 1024)
                """)
                db_status['size_mb'] = cursor.fetchone()[0]
                
                # Check for long-running queries
                cursor.execute("""
                    SELECT pid, age(clock_timestamp(), query_start), query
                    FROM pg_stat_activity
                    WHERE state != 'idle' 
                    AND query NOT ILIKE '%pg_stat_activity%'
                    ORDER BY age DESC LIMIT 5
                """)
                long_queries = cursor.fetchall()
                if long_queries:
                    db_status['long_running_queries'] = [
                        {'pid': q[0], 'age_seconds': q[1], 'query': q[2][:100]}
                        for q in long_queries
                    ]
        
        except Exception as e:
            logger.error(f"Database check failed: {e}")
            db_status['error'] = str(e)
            self.add_alert('Database', f"Database check failed: {e}")
        
        return db_status
    
    def check_redis(self) -> Dict[str, Any]:
        """Check Redis connectivity and status."""
        redis_status = {
            'timestamp': datetime.now().isoformat(),
            'connected': False,
            'memory_used_mb': None,
            'connected_clients': None,
            'keys': None
        }
        
        try:
            import redis
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
            r = redis.from_url(redis_url, socket_timeout=5)
            
            # Test connection
            r.ping()
            redis_status['connected'] = True
            
            # Get Redis info
            info = r.info()
            
            redis_status['memory_used_mb'] = info['used_memory'] / (1024 ** 2)
            redis_status['connected_clients'] = info['connected_clients']
            redis_status['keys'] = info.get('db0', {}).get('keys', 0)
            redis_status['uptime_days'] = info['uptime_in_days']
            
            # Check memory usage
            memory_pct = (info['used_memory'] / info['total_system_memory']) * 100
            if memory_pct > 80:
                self.add_alert('Redis', f"Redis memory usage high: {memory_pct:.1f}%")
            
            # Check connected clients
            if info['connected_clients'] > 100:
                self.add_alert('Redis', f"Redis connected clients high: {info['connected_clients']}")
        
        except Exception as e:
            logger.error(f"Redis check failed: {e}")
            redis_status['error'] = str(e)
            self.add_alert('Redis', f"Redis check failed: {e}")
        
        return redis_status
    
    def check_celery(self) -> Dict[str, Any]:
        """Check Celery workers and task queue."""
        celery_status = {
            'timestamp': datetime.now().isoformat(),
            'workers': [],
            'tasks': {},
            'queues': {}
        }
        
        try:
            from celery import current_app
            
            # Inspect workers
            i = current_app.control.inspect()
            
            # Get active workers
            active = i.active()
            if active:
                for worker, tasks in active.items():
                    celery_status['workers'].append({
                        'name': worker,
                        'active_tasks': len(tasks),
                        'status': 'active'
                    })
            
            # Get scheduled tasks
            scheduled = i.scheduled()
            if scheduled:
                total_scheduled = sum(len(tasks) for tasks in scheduled.values())
                celery_status['tasks']['scheduled'] = total_scheduled
            
            # Get registered tasks
            registered = i.registered()
            if registered:
                celery_status['tasks']['registered'] = len(registered)
        
        except Exception as e:
            logger.error(f"Celery check failed: {e}")
            celery_status['error'] = str(e)
        
        return celery_status
    
    def check_logs(self) -> Dict[str, Any]:
        """Check application logs for errors."""
        logs_status = {
            'timestamp': datetime.now().isoformat(),
            'recent_errors': [],
            'error_count': 0
        }
        
        try:
            log_dir = self.project_root / 'logs'
            if log_dir.exists():
                # Check recent log files
                log_files = list(log_dir.glob('*.log'))
                for log_file in log_files[-5:]:  # Last 5 log files
                    try:
                        with open(log_file, 'r') as f:
                            lines = f.readlines()[-100:]  # Last 100 lines
                            for line in lines:
                                if 'ERROR' in line or 'CRITICAL' in line:
                                    logs_status['recent_errors'].append({
                                        'file': log_file.name,
                                        'line': line.strip(),
                                        'timestamp': line[:23] if line else 'unknown'
                                    })
                                    logs_status['error_count'] += 1
                    except Exception as e:
                        logger.error(f"Error reading log file {log_file}: {e}")
        
        except Exception as e:
            logger.error(f"Log check failed: {e}")
        
        return logs_status
    
    def add_alert(self, category: str, message: str, level: str = 'warning'):
        """Add an alert to be sent."""
        alert = {
            'timestamp': datetime.now().isoformat(),
            'category': category,
            'message': message,
            'level': level
        }
        
        # Check if similar alert was sent recently
        cooldown = self.config['monitoring']['alert_cooldown']
        for existing_alert in self.alerts[-10:]:  # Check last 10 alerts
            if (existing_alert['category'] == category and 
                existing_alert['message'] == message):
                time_diff = datetime.now() - datetime.fromisoformat(existing_alert['timestamp'])
                if time_diff.total_seconds() < cooldown:
                    return  # Skip if within cooldown period
        
        self.alerts.append(alert)
        logger.warning(f"ALERT: [{category}] {message}")
    
    def send_alerts(self):
        """Send collected alerts via configured channels."""
        if not self.alerts or not self.config['alerts']['enabled']:
            return
        
        # Email alerts
        if self.config['alerts']['email']['enabled']:
            self.send_email_alerts()
        
        # Slack alerts (if configured)
        if self.config['alerts']['slack']['enabled']:
            self.send_slack_alerts()
        
        # Telegram alerts (if configured)
        if self.config['alerts']['telegram']['enabled']:
            self.send_telegram_alerts()
    
    def send_email_alerts(self):
        """Send alerts via email."""
        try:
            email_config = self.config['alerts']['email']
            recipients = email_config['recipients']
            
            if not recipients:
                return
            
            # Create email
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f'MEDIPREDICT Health Alert - {datetime.now().strftime("%Y-%m-%d %H:%M")}'
            msg['From'] = os.getenv('EMAIL_HOST_USER', 'noreply@medipredict.example.com')
            msg['To'] = ', '.join(recipients)
            
            # Create HTML content
            html = f"""
            <html>
            <body>
                <h2>MEDIPREDICT System Health Alerts</h2>
                <p><strong>Time:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
                
                <h3>Alerts ({len(self.alerts)})</h3>
                <table border="1" cellpadding="8" style="border-collapse: collapse;">
                    <tr>
                        <th>Time</th>
                        <th>Category</th>
                        <th>Level</th>
                        <th>Message</th>
                    </tr>
            """
            
            for alert in self.alerts:
                level_color = {
                    'critical': 'red',
                    'warning': 'orange',
                    'info': 'blue'
                }.get(alert['level'], 'black')
                
                html += f"""
                    <tr>
                        <td>{alert['timestamp'][11:19]}</td>
                        <td>{alert['category']}</td>
                        <td style="color: {level_color}">{alert['level'].upper()}</td>
                        <td>{alert['message']}</td>
                    </tr>
                """
            
            html += """
                </table>
                
                <h3>System Status</h3>
                <pre>
            """
            
            # Add system status summary
            if self.health_data:
                html += json.dumps(self.health_data.get('summary', {}), indent=2)
            
            html += """
                </pre>
                
                <hr>
                <p><em>This is an automated alert from MEDIPREDICT Health Monitoring System.</em></p>
            </body>
            </html>
            """
            
            # Attach HTML
            msg.attach(MIMEText(html, 'html'))
            
            # Send email
            with smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port']) as server:
                server.starttls()
                server.login(
                    os.getenv('EMAIL_HOST_USER', ''),
                    os.getenv('EMAIL_HOST_PASSWORD', '')
                )
                server.send_message(msg)
            
            logger.info(f"Sent email alert to {len(recipients)} recipients")
            
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
    
    def send_slack_alerts(self):
        """Send alerts to Slack."""
        # Implementation for Slack webhook
        pass
    
    def send_telegram_alerts(self):
        """Send alerts to Telegram."""
        # Implementation for Telegram bot
        pass
    
    def save_health_data(self):
        """Save health data to file."""
        try:
            # Create summary
            summary = {
                'timestamp': datetime.now().isoformat(),
                'overall_status': 'healthy',
                'checks_passed': 0,
                'checks_total': 0,
                'alerts': len(self.alerts)
            }
            
            # Count checks
            for category, data in self.health_data.items():
                if isinstance(data, dict) and 'status' in data:
                    summary['checks_total'] += 1
                    if data.get('status') == 'OK' or data.get('connected', False):
                        summary['checks_passed'] += 1
            
            if summary['checks_passed'] < summary['checks_total']:
                summary['overall_status'] = 'degraded'
            
            if self.alerts:
                summary['overall_status'] = 'unhealthy'
            
            self.health_data['summary'] = summary
            
            # Save to file
            health_dir = self.project_root / 'health_data'
            health_dir.mkdir(exist_ok=True)
            
            filename = f"health_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            filepath = health_dir / filename
            
            with open(filepath, 'w') as f:
                json.dump(self.health_data, f, indent=2, default=str)
            
            logger.info(f"Health data saved to {filepath}")
            
            # Clean up old files
            self.cleanup_old_files(health_dir)
            
        except Exception as e:
            logger.error(f"Failed to save health data: {e}")
    
    def cleanup_old_files(self, directory: Path):
        """Remove old health data files."""
        retention_days = self.config['monitoring']['retention_days']
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        for file in directory.glob('health_*.json'):
            try:
                # Extract date from filename
                date_str = file.stem.split('_')[1]
                file_date = datetime.strptime(date_str, '%Y%m%d_%H%M%S')
                
                if file_date < cutoff_date:
                    file.unlink()
                    logger.debug(f"Removed old health file: {file.name}")
            except Exception as e:
                logger.error(f"Error cleaning up file {file}: {e}")
    
    def run_health_check(self) -> Dict[str, Any]:
        """Run complete health check."""
        logger.info("Starting comprehensive health check...")
        
        self.health_data = {}
        self.alerts = []
        
        # Run all checks
        checks = [
            ('system_resources', self.check_system_resources),
            ('services', self.check_services),
            ('endpoints', self.check_endpoints),
            ('database', self.check_database),
            ('redis', self.check_redis),
            ('celery', self.check_celery),
            ('logs', self.check_logs)
        ]
        
        for name, check_func in checks:
            try:
                logger.info(f"Running {name} check...")
                self.health_data[name] = check_func()
            except Exception as e:
                logger.error(f"Check {name} failed: {e}")
                self.health_data[name] = {'error': str(e)}
        
        # Send alerts if any
        self.send_alerts()
        
        # Save health data
        self.save_health_data()
        
        # Print summary
        self.print_summary()
        
        return self.health_data
    
    def print_summary(self):
        """Print health check summary."""
        print("\n" + "="*60)
        print("MEDIPREDICT HEALTH CHECK SUMMARY")
        print("="*60)
        
        if 'summary' in self.health_data:
            summary = self.health_data['summary']
            status_color = {
                'healthy': '\033[92m',
                'degraded': '\033[93m',
                'unhealthy': '\033[91m'
            }.get(summary['overall_status'], '\033[0m')
            
            print(f"\nOverall Status: {status_color}{summary['overall_status'].upper()}\033[0m")
            print(f"Checks Passed: {summary['checks_passed']}/{summary['checks_passed']}")
            print(f"Alerts: {summary['alerts']}")
        
        # Print individual check status
        print("\nDetailed Status:")
        print("-" * 40)
        
        for category, data in self.health_data.items():
            if category == 'summary':
                continue
            
            status = 'N/A'
            if isinstance(data, dict):
                if 'status' in data:
                    status = data['status']
                elif 'connected' in data:
                    status = 'OK' if data['connected'] else 'ERROR'
                elif 'summary' in data:
                    healthy = data['summary'].get('healthy', 0)
                    total = data['summary'].get('total', 0)
                    status = f"{healthy}/{total} OK"
            
            color = '\033[92m' if status in ['OK', 'healthy'] else '\033[91m'
            reset = '\033[0m'
            print(f"{category:<20}: {color}{status}{reset}")
        
        # Print recent alerts
        if self.alerts:
            print(f"\n\033[93mRecent Alerts:\033[0m")
            for alert in self.alerts[-5:]:  # Last 5 alerts
                print(f"  [{alert['category']}] {alert['message']}")
        
        print("\n" + "="*60)
    
    def continuous_monitoring(self, interval_minutes: int = 5):
        """Run health checks continuously."""
        logger.info(f"Starting continuous monitoring (interval: {interval_minutes} minutes)")
        
        try:
            while True:
                self.run_health_check()
                logger.info(f"Next check in {interval_minutes} minutes...")
                time.sleep(interval_minutes * 60)
                
        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user")
        except Exception as e:
            logger.error(f"Monitoring stopped unexpectedly: {e}")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='MEDIPREDICT Health Check System')
    parser.add_argument('--mode', choices=['single', 'continuous'], default='single',
                       help='Run mode: single check or continuous monitoring')
    parser.add_argument('--interval', type=int, default=5,
                       help='Interval in minutes for continuous monitoring')
    parser.add_argument('--config', type=str, default='health_config.json',
                       help='Configuration file name')
    parser.add_argument('--no-alerts', action='store_true',
                       help='Disable alert notifications')
    
    args = parser.parse_args()
    
    checker = HealthChecker(config_file=args.config)
    
    if args.no_alerts:
        checker.config['alerts']['enabled'] = False
    
    if args.mode == 'continuous':
        checker.continuous_monitoring(interval_minutes=args.interval)
    else:
        checker.run_health_check()

if __name__ == '__main__':
    main()