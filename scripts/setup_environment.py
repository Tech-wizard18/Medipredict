#!/usr/bin/env python3
"""
Environment Setup and Validation Script for MEDIPREDICT
Checks system requirements, environment variables, and sets up the project environment.
"""

import os
import sys
import platform
import subprocess
import json
import shutil
from pathlib import Path
import argparse
import logging
from typing import Dict, List, Tuple
import dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/setup.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class EnvironmentSetup:
    """Main class for environment setup and validation."""
    
    def __init__(self, env_file='.env'):
        self.project_root = Path(__file__).parent.parent
        self.env_file = self.project_root / env_file
        self.env_example = self.project_root / '.env.example'
        
    def check_python_version(self) -> Tuple[bool, str]:
        """Check if Python version meets requirements."""
        required_version = (3, 8, 0)
        current_version = sys.version_info
        
        if current_version >= required_version:
            return True, f"Python {current_version.major}.{current_version.minor}.{current_version.micro} meets requirements"
        else:
            return False, f"Python {current_version.major}.{current_version.minor}.{current_version.micro} is below required {required_version[0]}.{required_version[1]}"
    
    def check_system_resources(self) -> Dict[str, Tuple[bool, str]]:
        """Check system resources."""
        import psutil
        
        checks = {}
        
        # Check RAM
        ram_gb = psutil.virtual_memory().total / (1024 ** 3)
        checks['ram'] = (ram_gb >= 4, f"RAM: {ram_gb:.1f} GB")
        
        # Check disk space
        disk = psutil.disk_usage('/')
        disk_gb = disk.free / (1024 ** 3)
        checks['disk'] = (disk_gb >= 5, f"Free disk space: {disk_gb:.1f} GB")
        
        # Check CPU cores
        cpu_cores = psutil.cpu_count(logical=False)
        checks['cpu'] = (cpu_cores >= 2, f"CPU cores: {cpu_cores}")
        
        return checks
    
    def check_python_dependencies(self) -> List[Tuple[bool, str]]:
        """Check for required Python packages."""
        required_packages = [
            'django',
            'celery',
            'redis',
            'psycopg2-binary',
            'numpy',
            'pandas',
            'scikit-learn',
            'joblib',
            'pillow',
            'django-crispy-forms',
            'django-rest-framework',
            'python-dotenv',
            'psutil'
        ]
        
        results = []
        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
                results.append((True, f"{package} ✓"))
            except ImportError:
                results.append((False, f"{package} ✗"))
        
        return results
    
    def setup_environment_file(self) -> bool:
        """Create .env file from example if it doesn't exist."""
        if not self.env_file.exists():
            if self.env_example.exists():
                shutil.copy(self.env_example, self.env_file)
                logger.info(f"Created {self.env_file} from example")
                
                # Set default values
                self.update_env_file({
                    'SECRET_KEY': self.generate_secret_key(),
                    'DEBUG': 'True',
                    'ALLOWED_HOSTS': 'localhost,127.0.0.1'
                })
                return True
            else:
                logger.error("No .env.example file found!")
                return False
        return True
    
    def generate_secret_key(self) -> str:
        """Generate Django secret key."""
        import random
        import string
        
        chars = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'
        return ''.join(random.choice(chars) for _ in range(50))
    
    def update_env_file(self, updates: Dict[str, str]):
        """Update environment variables in .env file."""
        if not self.env_file.exists():
            self.env_file.touch()
        
        lines = []
        existing_vars = {}
        
        # Read existing variables
        if self.env_file.exists():
            with open(self.env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        existing_vars[key.strip()] = value.strip()
                    lines.append(line)
        
        # Update with new values
        existing_vars.update(updates)
        
        # Write back
        with open(self.env_file, 'w') as f:
            for key, value in existing_vars.items():
                f.write(f"{key}={value}\n")
        
        logger.info(f"Updated {self.env_file}")
    
    def create_directory_structure(self):
        """Create necessary directories."""
        directories = [
            'media/profiles',
            'media/prescriptions',
            'media/reports',
            'logs',
            'scripts',
            'tests',
            'static',
            'templates/error_pages',
            'prediction_app/ml_models/scalers'
        ]
        
        for directory in directories:
            dir_path = self.project_root / directory
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory: {directory}")
    
    def setup_database(self):
        """Set up initial database migrations."""
        try:
            # Run migrations
            subprocess.run([
                sys.executable, 'manage.py', 'makemigrations'
            ], cwd=self.project_root, check=True)
            
            subprocess.run([
                sys.executable, 'manage.py', 'migrate'
            ], cwd=self.project_root, check=True)
            
            # Create superuser if needed
            create_superuser = input("Create superuser? (y/n): ").lower()
            if create_superuser == 'y':
                subprocess.run([
                    sys.executable, 'manage.py', 'createsuperuser'
                ], cwd=self.project_root, check=True)
            
            logger.info("Database setup completed")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Database setup failed: {e}")
            return False
    
    def collect_static_files(self):
        """Collect static files."""
        try:
            subprocess.run([
                sys.executable, 'manage.py', 'collectstatic',
                '--noinput'
            ], cwd=self.project_root, check=True)
            logger.info("Static files collected")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Static collection failed: {e}")
            return False
    
    def validate_environment(self) -> Dict[str, List[Tuple[bool, str]]]:
        """Run all validation checks."""
        results = {}
        
        # Python version check
        py_check = self.check_python_version()
        results['python_version'] = [py_check]
        
        # System resources
        resource_checks = self.check_system_resources()
        results['system_resources'] = [(status, msg) for status, msg in resource_checks.values()]
        
        # Dependencies
        results['dependencies'] = self.check_python_dependencies()
        
        # Environment file
        env_status = self.setup_environment_file()
        results['environment'] = [(env_status, "Environment file setup")]
        
        # Directory structure
        try:
            self.create_directory_structure()
            results['directories'] = [(True, "Directory structure created")]
        except Exception as e:
            results['directories'] = [(False, f"Directory creation failed: {e}")]
        
        return results
    
    def print_summary(self, results: Dict[str, List[Tuple[bool, str]]]):
        """Print validation summary."""
        print("\n" + "="*60)
        print("ENVIRONMENT SETUP SUMMARY")
        print("="*60)
        
        all_passed = True
        
        for category, checks in results.items():
            print(f"\n{category.upper()}:")
            for status, message in checks:
                icon = "✓" if status else "✗"
                color = "\033[92m" if status else "\033[91m"
                reset = "\033[0m"
                print(f"  {color}{icon}{reset} {message}")
                
                if not status:
                    all_passed = False
        
        print("\n" + "="*60)
        if all_passed:
            print("\033[92m✓ All checks passed! Environment is ready.\033[0m")
        else:
            print("\033[91m✗ Some checks failed. Please review the issues above.\033[0m")
        print("="*60)
    
    def run(self, skip_db=False, skip_static=False):
        """Run the complete setup process."""
        print("Starting MEDIPREDICT Environment Setup...")
        
        # Validate environment
        results = self.validate_environment()
        
        # Print summary
        self.print_summary(results)
        
        # Additional setup steps
        if not skip_db:
            print("\nSetting up database...")
            self.setup_database()
        
        if not skip_static:
            print("\nCollecting static files...")
            self.collect_static_files()
        
        print("\n" + "="*60)
        print("SETUP COMPLETE!")
        print("="*60)
        print("\nNext steps:")
        print("1. Review .env file and update configuration")
        print("2. Run: python manage.py runserver")
        print("3. Access: http://localhost:8000")
        print("\nFor development:")
        print("- pip install -r requirements-dev.txt")
        print("- python train_models.py")
        print("="*60)

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='MEDIPREDICT Environment Setup')
    parser.add_argument('--skip-db', action='store_true', help='Skip database setup')
    parser.add_argument('--skip-static', action='store_true', help='Skip static file collection')
    parser.add_argument('--env', default='.env', help='Environment file name')
    
    args = parser.parse_args()
    
    setup = EnvironmentSetup(env_file=args.env)
    setup.run(skip_db=args.skip_db, skip_static=args.skip_static)

if __name__ == '__main__':
    main()