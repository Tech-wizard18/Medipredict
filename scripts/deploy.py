#!/usr/bin/env python3
"""
Deployment Automation Script for MEDIPREDICT
Handles deployment to different environments with comprehensive checks.
"""

import os
import sys
import subprocess
import argparse
import logging
import time
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import requests
import docker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/deployment.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DeploymentManager:
    """Manages deployment process for different environments."""
    
    def __init__(self, environment='production'):
        self.project_root = Path(__file__).parent.parent
        self.environment = environment
        self.deployment_log = self.project_root / 'logs' / f'deployment_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        
        # Environment configurations
        self.env_configs = {
            'development': {
                'branch': 'develop',
                'requirements': 'requirements-dev.txt',
                'django_settings': 'disease_app.settings.development',
                'hosts': ['localhost', '127.0.0.1'],
                'port': 8000,
                'debug': True
            },
            'staging': {
                'branch': 'staging',
                'requirements': 'requirements.txt',
                'django_settings': 'disease_app.settings.production',
                'hosts': ['staging.medipredict.example.com'],
                'port': 8000,
                'debug': False
            },
            'production': {
                'branch': 'main',
                'requirements': 'requirements.txt',
                'django_settings': 'disease_app.settings.production',
                'hosts': ['medipredict.example.com', 'www.medipredict.example.com'],
                'port': 8000,
                'debug': False
            }
        }
        
        # Deployment steps
        self.steps = [
            'pre_deployment_checks',
            'backup_database',
            'pull_latest_code',
            'install_dependencies',
            'run_migrations',
            'collect_static_files',
            'update_permissions',
            'restart_services',
            'post_deployment_checks',
            'cleanup'
        ]
        
        self.results = {}
    
    def log_step(self, step: str, message: str, level='info'):
        """Log deployment step."""
        log_msg = f"[{step}] {message}"
        if level == 'info':
            logger.info(log_msg)
        elif level == 'warning':
            logger.warning(log_msg)
        elif level == 'error':
            logger.error(log_msg)
        
        # Write to deployment log
        with open(self.deployment_log, 'a') as f:
            f.write(f"{datetime.now().isoformat()} - {log_msg}\n")
    
    def pre_deployment_checks(self) -> bool:
        """Run pre-deployment checks."""
        self.log_step('pre_deployment_checks', 'Starting pre-deployment checks...')
        
        checks = []
        
        # Check Python version
        py_version = sys.version_info
        if py_version >= (3, 8):
            checks.append(('Python Version', True, f"{py_version.major}.{py_version.minor}.{py_version.micro}"))
        else:
            checks.append(('Python Version', False, f"Requires 3.8+, found {py_version.major}.{py_version.minor}"))
        
        # Check disk space
        try:
            import shutil
            total, used, free = shutil.disk_usage("/")
            free_gb = free // (2**30)
            checks.append(('Disk Space', free_gb > 5, f"{free_gb} GB free"))
        except:
            checks.append(('Disk Space', False, "Unable to check"))
        
        # Check memory
        try:
            import psutil
            mem = psutil.virtual_memory()
            mem_gb = mem.total // (2**30)
            checks.append(('Memory', mem_gb >= 2, f"{mem_gb} GB total"))
        except:
            checks.append(('Memory', False, "Unable to check"))
        
        # Check required services
        services = ['postgresql', 'redis', 'nginx']
        for service in services:
            try:
                result = subprocess.run(
                    ['systemctl', 'is-active', '--quiet', service],
                    capture_output=True
                )
                checks.append((f"Service: {service}", result.returncode == 0, 
                             'Running' if result.returncode == 0 else 'Not running'))
            except:
                checks.append((f"Service: {service}", False, 'Check failed'))
        
        # Check environment variables
        required_vars = ['SECRET_KEY', 'DATABASE_URL', 'REDIS_URL']
        for var in required_vars:
            value = os.getenv(var)
            checks.append((f"Env: {var}", value is not None, 
                         'Set' if value else 'Not set'))
        
        # Print check results
        print("\nPre-deployment Checks:")
        print("-" * 50)
        all_passed = True
        for check_name, passed, message in checks:
            status = "✓" if passed else "✗"
            color = "\033[92m" if passed else "\033[91m"
            reset = "\033[0m"
            print(f"{color}{status}{reset} {check_name}: {message}")
            if not passed:
                all_passed = False
        
        self.log_step('pre_deployment_checks', 
                     f"Pre-deployment checks {'passed' if all_passed else 'failed'}")
        
        return all_passed
    
    def backup_database(self) -> bool:
        """Backup database before deployment."""
        self.log_step('backup_database', 'Creating database backup...')
        
        try:
            backup_dir = self.project_root / 'backups'
            backup_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = backup_dir / f'db_backup_{timestamp}.sql'
            
            # Get database config from environment
            db_url = os.getenv('DATABASE_URL', '')
            
            if 'postgresql' in db_url:
                # PostgreSQL backup
                import urllib.parse
                parsed = urllib.parse.urlparse(db_url)
                
                cmd = [
                    'pg_dump',
                    '-h', parsed.hostname or 'localhost',
                    '-U', parsed.username or 'postgres',
                    '-d', parsed.path[1:] if parsed.path else 'medipredict',
                    '-f', str(backup_file)
                ]
                
                # Set password in environment
                env = os.environ.copy()
                env['PGPASSWORD'] = parsed.password or ''
                
                result = subprocess.run(cmd, env=env, capture_output=True)
                
                if result.returncode == 0:
                    self.log_step('backup_database', f"Database backup created: {backup_file}")
                    return True
                else:
                    self.log_step('backup_database', 
                                 f"Database backup failed: {result.stderr.decode()}", 
                                 'error')
                    return False
            else:
                self.log_step('backup_database', 
                             'Database backup skipped (non-PostgreSQL database)', 
                             'warning')
                return True
                
        except Exception as e:
            self.log_step('backup_database', f"Backup failed: {e}", 'error')
            return False
    
    def pull_latest_code(self) -> bool:
        """Pull latest code from Git repository."""
        self.log_step('pull_latest_code', 'Pulling latest code...')
        
        try:
            branch = self.env_configs[self.environment]['branch']
            
            # Check if git is available
            result = subprocess.run(['git', '--version'], capture_output=True)
            if result.returncode != 0:
                self.log_step('pull_latest_code', 'Git not available', 'error')
                return False
            
            # Fetch latest changes
            subprocess.run(['git', 'fetch', 'origin'], 
                          cwd=self.project_root, check=True)
            
            # Checkout to the target branch
            subprocess.run(['git', 'checkout', branch], 
                          cwd=self.project_root, check=True)
            
            # Pull latest changes
            subprocess.run(['git', 'pull', 'origin', branch], 
                          cwd=self.project_root, check=True)
            
            # Get latest commit hash
            result = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'],
                                   cwd=self.project_root, capture_output=True, text=True)
            commit_hash = result.stdout.strip()
            
            self.log_step('pull_latest_code', 
                         f"Code updated to commit: {commit_hash}")
            
            return True
            
        except subprocess.CalledProcessError as e:
            self.log_step('pull_latest_code', f"Git pull failed: {e}", 'error')
            return False
        except Exception as e:
            self.log_step('pull_latest_code', f"Error: {e}", 'error')
            return False
    
    def install_dependencies(self) -> bool:
        """Install Python dependencies."""
        self.log_step('install_dependencies', 'Installing dependencies...')
        
        try:
            requirements_file = self.env_configs[self.environment]['requirements']
            req_path = self.project_root / requirements_file
            
            if not req_path.exists():
                self.log_step('install_dependencies', 
                             f"Requirements file not found: {requirements_file}", 
                             'error')
                return False
            
            # Upgrade pip
            subprocess.run([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'],
                          capture_output=True)
            
            # Install dependencies
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'install', '-r', str(req_path)],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                self.log_step('install_dependencies', 'Dependencies installed successfully')
                return True
            else:
                self.log_step('install_dependencies', 
                             f"Dependency installation failed: {result.stderr}", 
                             'error')
                return False
                
        except Exception as e:
            self.log_step('install_dependencies', f"Installation error: {e}", 'error')
            return False
    
    def run_migrations(self) -> bool:
        """Run Django database migrations."""
        self.log_step('run_migrations', 'Running database migrations...')
        
        try:
            # Set Django settings module
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 
                                self.env_configs[self.environment]['django_settings'])
            
            # Run migrations
            result = subprocess.run(
                [sys.executable, 'manage.py', 'migrate'],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                self.log_step('run_migrations', 'Migrations completed successfully')
                return True
            else:
                self.log_step('run_migrations', 
                             f"Migrations failed: {result.stderr}", 
                             'error')
                return False
                
        except Exception as e:
            self.log_step('run_migrations', f"Migration error: {e}", 'error')
            return False
    
    def collect_static_files(self) -> bool:
        """Collect static files."""
        self.log_step('collect_static_files', 'Collecting static files...')
        
        try:
            result = subprocess.run(
                [sys.executable, 'manage.py', 'collectstatic', '--noinput'],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                self.log_step('collect_static_files', 'Static files collected')
                return True
            else:
                self.log_step('collect_static_files', 
                             f"Static collection failed: {result.stderr}", 
                             'error')
                return False
                
        except Exception as e:
            self.log_step('collect_static_files', f"Static collection error: {e}", 'error')
            return False
    
    def update_permissions(self) -> bool:
        """Update file permissions."""
        self.log_step('update_permissions', 'Updating file permissions...')
        
        try:
            directories = [
                'media',
                'logs',
                'static',
                'prediction_app/ml_models'
            ]
            
            for directory in directories:
                dir_path = self.project_root / directory
                if dir_path.exists():
                    # Set directory permissions to 755
                    os.chmod(dir_path, 0o755)
                    
                    # Set file permissions within directory
                    for root, dirs, files in os.walk(dir_path):
                        for d in dirs:
                            os.chmod(os.path.join(root, d), 0o755)
                        for f in files:
                            os.chmod(os.path.join(root, f), 0o644)
            
            self.log_step('update_permissions', 'Permissions updated')
            return True
            
        except Exception as e:
            self.log_step('update_permissions', f"Permission update error: {e}", 'error')
            return False
    
    def restart_services(self) -> bool:
        """Restart required services."""
        self.log_step('restart_services', 'Restarting services...')
        
        try:
            services = []
            
            # Determine which services to restart based on environment
            if self.environment == 'production':
                services = ['gunicorn', 'celery', 'celery-beat', 'nginx']
            elif self.environment == 'staging':
                services = ['gunicorn', 'celery', 'nginx']
            else:  # development
                services = []  # Development doesn't use service managers
            
            for service in services:
                try:
                    subprocess.run(['systemctl', 'restart', service], check=True)
                    self.log_step('restart_services', f"Service restarted: {service}")
                    time.sleep(2)  # Give service time to start
                    
                    # Verify service is running
                    result = subprocess.run(['systemctl', 'is-active', service], 
                                           capture_output=True, text=True)
                    if result.stdout.strip() == 'active':
                        self.log_step('restart_services', f"Service active: {service}")
                    else:
                        self.log_step('restart_services', 
                                     f"Service not active: {service}", 
                                     'warning')
                        
                except subprocess.CalledProcessError:
                    self.log_step('restart_services', 
                                 f"Failed to restart: {service}", 
                                 'error')
                    return False
            
            self.log_step('restart_services', 'Services restarted successfully')
            return True
            
        except Exception as e:
            self.log_step('restart_services', f"Service restart error: {e}", 'error')
            return False
    
    def post_deployment_checks(self) -> bool:
        """Run post-deployment checks."""
        self.log_step('post_deployment_checks', 'Running post-deployment checks...')
        
        checks = []
        
        # Check if application is responding
        try:
            port = self.env_configs[self.environment]['port']
            response = requests.get(f'http://localhost:{port}/health/', timeout=10)
            
            if response.status_code == 200:
                checks.append(('Application Health', True, 'Healthy'))
            else:
                checks.append(('Application Health', False, 
                             f"HTTP {response.status_code}"))
        except Exception as e:
            checks.append(('Application Health', False, f"Unreachable: {e}"))
        
        # Check database connection
        try:
            import django
            django.setup()
            from django.db import connection
            
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                checks.append(('Database Connection', True, 'Connected'))
                
        except Exception as e:
            checks.append(('Database Connection', False, f"Failed: {e}"))
        
        # Check Redis connection
        try:
            import redis
            r = redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))
            r.ping()
            checks.append(('Redis Connection', True, 'Connected'))
        except Exception as e:
            checks.append(('Redis Connection', False, f"Failed: {e}"))
        
        # Check static files
        static_dir = self.project_root / 'static'
        if static_dir.exists() and any(static_dir.iterdir()):
            checks.append(('Static Files', True, 'Available'))
        else:
            checks.append(('Static Files', False, 'Missing or empty'))
        
        # Print check results
        print("\nPost-deployment Checks:")
        print("-" * 50)
        all_passed = True
        for check_name, passed, message in checks:
            status = "✓" if passed else "✗"
            color = "\033[92m" if passed else "\033[91m"
            reset = "\033[0m"
            print(f"{color}{status}{reset} {check_name}: {message}")
            if not passed:
                all_passed = False
        
        self.log_step('post_deployment_checks', 
                     f"Post-deployment checks {'passed' if all_passed else 'failed'}")
        
        return all_passed
    
    def cleanup(self) -> bool:
        """Clean up temporary files and old backups."""
        self.log_step('cleanup', 'Cleaning up...')
        
        try:
            # Clean up Python cache files
            for pycache in self.project_root.rglob('__pycache__'):
                shutil.rmtree(pycache, ignore_errors=True)
            
            # Clean up .pyc files
            for pyc_file in self.project_root.rglob('*.pyc'):
                pyc_file.unlink(missing_ok=True)
            
            # Remove old backups (keep only last 5)
            backup_dir = self.project_root / 'backups'
            if backup_dir.exists():
                backup_files = sorted(backup_dir.glob('db_backup_*.sql'))
                if len(backup_files) > 5:
                    for old_backup in backup_files[:-5]:
                        old_backup.unlink()
            
            self.log_step('cleanup', 'Cleanup completed')
            return True
            
        except Exception as e:
            self.log_step('cleanup', f"Cleanup error: {e}", 'warning')
            return False
    
    def generate_deployment_report(self) -> Dict:
        """Generate deployment report."""
        report = {
            'timestamp': datetime.now().isoformat(),
            'environment': self.environment,
            'steps': {},
            'success': all(step.get('success', False) for step in self.results.values()),
            'duration': None
        }
        
        for step_name, result in self.results.items():
            report['steps'][step_name] = {
                'success': result.get('success', False),
                'message': result.get('message', ''),
                'timestamp': result.get('timestamp', '')
            }
        
        # Save report
        reports_dir = self.project_root / 'deployment_reports'
        reports_dir.mkdir(exist_ok=True)
        
        report_file = reports_dir / f'deployment_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.log_step('report', f"Deployment report saved: {report_file}")
        
        return report
    
    def deploy(self, skip_checks: bool = False) -> bool:
        """Execute the complete deployment pipeline."""
        start_time = time.time()
        
        print(f"\n{'='*60}")
        print(f"MEDIPREDICT Deployment - {self.environment.upper()} Environment")
        print(f"{'='*60}")
        
        if not skip_checks:
            # Run pre-deployment checks
            if not self.pre_deployment_checks():
                print("\n\033[91mPre-deployment checks failed! Aborting deployment.\033[0m")
                return False
        
        # Execute deployment steps
        for step in self.steps:
            print(f"\n\033[94m[{step.upper()}]\033[0m")
            
            step_start = time.time()
            step_func = getattr(self, step)
            
            try:
                success = step_func()
                step_duration = time.time() - step_start
                
                self.results[step] = {
                    'success': success,
                    'message': f"Completed in {step_duration:.2f}s",
                    'timestamp': datetime.now().isoformat()
                }
                
                if not success and step not in ['cleanup']:  # Skip cleanup failures
                    print(f"\033[91mStep '{step}' failed!\033[0m")
                    if step != 'pre_deployment_checks':
                        print("Continuing with next steps...")
                    
            except Exception as e:
                self.results[step] = {
                    'success': False,
                    'message': f"Error: {str(e)}",
                    'timestamp': datetime.now().isoformat()
                }
                print(f"\033[91mStep '{step}' errored: {e}\033[0m]")
        
        # Generate report
        total_duration = time.time() - start_time
        report = self.generate_deployment_report()
        report['duration'] = total_duration
        
        # Print summary
        print(f"\n{'='*60}")
        print("DEPLOYMENT SUMMARY")
        print(f"{'='*60}")
        
        successful_steps = sum(1 for r in self.results.values() if r.get('success', False))
        total_steps = len(self.results)
        
        print(f"Steps completed: {successful_steps}/{total_steps}")
        print(f"Total duration: {total_duration:.2f} seconds")
        
        if report['success']:
            print(f"\n\033[92m✓ Deployment to {self.environment} completed successfully!\033[0m")
        else:
            print(f"\n\033[91m✗ Deployment to {self.environment} completed with errors.\033[0m")
        
        print(f"\nDetailed report: {self.deployment_log}")
        print(f"{'='*60}")
        
        return report['success']

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='MEDIPREDICT Deployment Script')
    parser.add_argument('environment', choices=['development', 'staging', 'production'],
                       help='Deployment environment')
    parser.add_argument('--skip-checks', action='store_true',
                       help='Skip pre-deployment checks')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without actually deploying')
    parser.add_argument('--step', type=str,
                       help='Run specific step only')
    
    args = parser.parse_args()
    
    if args.dry_run:
        print("DRY RUN - No changes will be made")
        print(f"Would deploy to: {args.environment}")
        
        manager = DeploymentManager(args.environment)
        print("\nDeployment steps would be:")
        for step in manager.steps:
            print(f"  - {step}")
        
        return
    
    # Run deployment
    manager = DeploymentManager(args.environment)
    
    if args.step:
        # Run specific step only
        if hasattr(manager, args.step):
            step_func = getattr(manager, args.step)
            success = step_func()
            print(f"Step '{args.step}' {'completed successfully' if success else 'failed'}")
        else:
            print(f"Unknown step: {args.step}")
    else:
        # Run full deployment
        success = manager.deploy(skip_checks=args.skip_checks)
        sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()