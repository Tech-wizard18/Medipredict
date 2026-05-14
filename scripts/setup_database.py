#!/usr/bin/env python3
"""
MEDIPREDICT Database Setup Script - UPDATED VERSION
Fixed health_check and all other import issues
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# ==================== CONFIGURE DJANGO WITHOUT health_check ISSUES ====================

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# CRITICAL: Set Django settings module FIRST
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'disease_app.settings.development')

# Configure minimal Django settings BEFORE importing anything
from django.conf import settings

if not settings.configured:
    # Use minimal configuration that EXCLUDES health_check completely
    settings.configure(
        DEBUG=True,
        INSTALLED_APPS=[
            'django.contrib.admin',
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django.contrib.messages',
            'django.contrib.staticfiles',
            'users_app',
            'prediction_app',
            'consultations_app',
            'prescriptions_app',
            'notifications_app',
            'api_app',
        ],
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': project_root / 'db.sqlite3',
            }
        },
        SECRET_KEY='temp-key-for-database-setup-' + os.urandom(24).hex(),
        ROOT_URLCONF='disease_app.urls',
        MIDDLEWARE=[
            'django.middleware.security.SecurityMiddleware',
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.middleware.common.CommonMiddleware',
            'django.middleware.csrf.CsrfViewMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
            'django.contrib.messages.middleware.MessageMiddleware',
        ],
        TEMPLATES=[
            {
                'BACKEND': 'django.template.backends.django.DjangoTemplates',
                'DIRS': [project_root / 'templates'],
                'APP_DIRS': True,
                'OPTIONS': {
                    'context_processors': [
                        'django.template.context_processors.debug',
                        'django.template.context_processors.request',
                        'django.contrib.auth.context_processors.auth',
                        'django.contrib.messages.context_processors.messages',
                    ],
                },
            },
        ],
        AUTH_USER_MODEL='users_app.User',
        TIME_ZONE='UTC',
        USE_TZ=True,
        LANGUAGE_CODE='en-us',
        USE_I18N=True,
        DEFAULT_AUTO_FIELD='django.db.models.BigAutoField',
    )

# NOW safely import and setup Django
import django
django.setup()

# ==================== IMPORT DJANGO MODULES AFTER SETUP ====================

from django.core.management import call_command
from django.db import connection, transaction
from django.contrib.auth import get_user_model
from django.db.utils import OperationalError, ProgrammingError

User = get_user_model()

# ==================== LOGGING AND UTILITIES ====================

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S',
        handlers=[logging.StreamHandler()]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

def print_banner(text):
    """Print a formatted banner"""
    print("\n" + "═" * 60)
    print(f"  {text}")
    print("═" * 60)

def print_step(step_num, description, success=True, details=""):
    """Print a step with status"""
    icon = "✅" if success else "❌"
    status = "PASS" if success else "FAIL"
    print(f"{icon} [{status}] Step {step_num}: {description}")
    if details:
        print(f"    └─ {details}")

class DatabaseSetup:
    def __init__(self):
        self.db_path = project_root / 'db.sqlite3'
        self.setup_start_time = None
        
    def start_timer(self):
        """Start setup timer"""
        import time
        self.setup_start_time = time.time()
    
    def stop_timer(self):
        """Stop setup timer and return duration"""
        import time
        if self.setup_start_time:
            return time.time() - self.setup_start_time
        return 0
    
    def check_database(self):
        """Step 1: Check database connection and status"""
        print_banner("STEP 1: DATABASE CHECK")
        
        checks = []
        
        # Check 1: Database file exists
        if self.db_path.exists():
            size_mb = self.db_path.stat().st_size / (1024 * 1024)
            checks.append(("Database file exists", True, f"Size: {size_mb:.2f} MB"))
        else:
            checks.append(("Database file exists", False, "File not found"))
        
        # Check 2: Database connection
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                if result and result[0] == 1:
                    checks.append(("Database connection", True, "Connection successful"))
                else:
                    checks.append(("Database connection", False, "Connection failed"))
        except Exception as e:
            checks.append(("Database connection", False, f"Error: {str(e)[:50]}"))
        
        # Check 3: Check if migrations table exists
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='django_migrations'")
                has_migrations = cursor.fetchone() is not None
                checks.append(("Migrations table", has_migrations, 
                             "Exists" if has_migrations else "Not found"))
        except:
            checks.append(("Migrations table", False, "Cannot check"))
        
        # Print results
        for i, (check_name, success, detail) in enumerate(checks, 1):
            print_step(i, check_name, success, detail)
        
        all_passed = all(success for _, success, _ in checks)
        return all_passed
    
    def run_migrations(self, force=False):
        """Step 2: Run Django migrations"""
        print_banner("STEP 2: RUNNING MIGRATIONS")
        
        try:
            # Check if migrations are needed
            if not force:
                try:
                    call_command('makemigrations', '--check', '--dry-run')
                    print_step(1, "No migrations needed", True, "Database is up to date")
                    return True
                except SystemExit:
                    pass  # Migrations are needed
            
            # Create migrations
            print("Creating migrations...")
            call_command('makemigrations')
            print_step(1, "Created migrations", True)
            
            # Apply migrations
            print("Applying migrations...")
            call_command('migrate')
            print_step(2, "Applied migrations", True)
            
            return True
            
        except Exception as e:
            print_step(1, "Migration failed", False, f"Error: {str(e)[:100]}")
            return False
    
    def create_admin_user(self, username='admin', email='admin@medipredict.com', password='Admin@123'):
        """Step 3: Create admin user"""
        print_banner("STEP 3: CREATING ADMIN USER")
        
        try:
            # Check if admin already exists
            if User.objects.filter(username=username).exists():
                admin = User.objects.get(username=username)
                print_step(1, "Admin user exists", True, f"Username: {admin.username}")
                return True
            
            # Create new admin user
            with transaction.atomic():
                admin = User.objects.create_superuser(
                    username=username,
                    email=email,
                    password=password
                )
                admin.first_name = 'System'
                admin.last_name = 'Administrator'
                admin.is_verified = True
                admin.save()
            
            print_step(1, "Admin user created", True, 
                      f"Username: {username}, Password: {password}")
            return True
            
        except Exception as e:
            print_step(1, "Failed to create admin", False, f"Error: {str(e)[:100]}")
            return False
    
    def create_test_users(self):
        """Step 4: Create test users for different roles"""
        print_banner("STEP 4: CREATING TEST USERS")
        
        test_users = [
            # Doctor users (check if your User model has is_doctor field or similar)
            {
                'username': 'dr_smith',
                'email': 'dr.smith@medipredict.com',
                'password': 'Doctor@123',
                'first_name': 'John',
                'last_name': 'Smith',
                'is_verified': True,
            },
            {
                'username': 'dr_jones',
                'email': 'dr.jones@medipredict.com',
                'password': 'Doctor@123',
                'first_name': 'Sarah',
                'last_name': 'Jones',
                'is_verified': True,
            },
            
            # Patient users
            {
                'username': 'john_doe',
                'email': 'john.doe@example.com',
                'password': 'Patient@123',
                'first_name': 'John',
                'last_name': 'Doe',
            },
            {
                'username': 'jane_smith',
                'email': 'jane.smith@example.com',
                'password': 'Patient@123',
                'first_name': 'Jane',
                'last_name': 'Smith',
            },
            
            # Staff users
            {
                'username': 'pharmacist1',
                'email': 'pharmacist@medipredict.com',
                'password': 'Pharmacy@123',
                'first_name': 'Robert',
                'last_name': 'Johnson',
                'is_verified': True
            },
            {
                'username': 'lab_tech1',
                'email': 'lab@medipredict.com',
                'password': 'LabTech@123',
                'first_name': 'Emily',
                'last_name': 'Williams',
                'is_verified': True
            },
            {
                'username': 'receptionist1',
                'email': 'reception@medipredict.com',
                'password': 'Reception@123',
                'first_name': 'Michael',
                'last_name': 'Brown',
                'is_verified': True
            }
        ]
        
        created_count = 0
        for user_data in test_users:
            username = user_data['username']
            
            # Skip if user already exists
            if User.objects.filter(username=username).exists():
                print(f"   ⚡ {username}: Already exists")
                created_count += 1
                continue
            
            try:
                with transaction.atomic():
                    # Create user
                    user = User.objects.create_user(
                        username=user_data['username'],
                        email=user_data['email'],
                        password=user_data['password']
                    )
                    
                    # Set additional fields (skip user_type)
                    for field in ['first_name', 'last_name', 'is_verified']:
                        if field in user_data:
                            setattr(user, field, user_data[field])
                    
                    user.save()
                    created_count += 1
                    
                    # Determine user type based on username
                    if 'dr_' in username:
                        user_type = 'doctor'
                    elif 'pharmacist' in username:
                        user_type = 'pharmacist'
                    elif 'lab_tech' in username:
                        user_type = 'lab technician'
                    elif 'receptionist' in username:
                        user_type = 'receptionist'
                    else:
                        user_type = 'patient'
                    
                    print(f"   ✅ {username}: Created ({user_type})")
                    
            except Exception as e:
                print(f"   ❌ {username}: Failed - {str(e)[:50]}")
        
        print_step(1, f"Created {created_count} test users", created_count > 0,
                f"Total users in system: {User.objects.count()}")
        return created_count > 0

    def setup_sample_data(self):
        """Step 5: Setup sample data for the system"""
        print_banner("STEP 5: SETTING UP SAMPLE DATA")
        
        try:
            # Import models
            from prediction_app.models import DiseaseModel, Symptom
            
            # 1. Disease Models - Try different field names
            diseases = [
                {'name': 'diabetes', 'is_active': True, 'accuracy': 0.95},
                {'name': 'heart', 'is_active': True, 'accuracy': 0.92},
                {'name': 'kidney', 'is_active': True, 'accuracy': 0.89},
                {'name': 'parkinson', 'is_active': True, 'accuracy': 0.88},
                {'name': 'breast_cancer', 'is_active': True, 'accuracy': 0.91},
                {'name': 'liver', 'is_active': True, 'accuracy': 0.87},
            ]
            
            created_count = 0
            for disease_data in diseases:
                # Try to get or create with minimal fields
                obj, created = DiseaseModel.objects.get_or_create(
                    name=disease_data['name'],
                    defaults={'is_active': disease_data['is_active']}
                )
                if created:
                    created_count += 1
                    # Try to set accuracy if field exists
                    if hasattr(obj, 'accuracy'):
                        obj.accuracy = disease_data['accuracy']
                        obj.save()
            
            print(f"   ✅ Created/verified {created_count} disease models")
            
            # 2. Symptoms
            symptoms = [
                ('Fever', 'general'),
                ('Headache', 'general'),
                ('Fatigue', 'general'),
                ('Chest Pain', 'cardiac'),
                ('Shortness of Breath', 'respiratory'),
                ('Nausea', 'digestive'),
                ('Dizziness', 'neurological'),
            ]
            
            for name, category in symptoms:
                Symptom.objects.get_or_create(name=name, defaults={'category': category})
            print("   ✅ Symptoms created")
            
            print_step(1, "Sample data created", True)
            return True
            
        except Exception as e:
            print_step(1, "Failed to create sample data", False, f"Error: {str(e)[:100]}")
            return False
            
    def verify_setup(self):
        """Step 6: Verify the complete setup"""
        print_banner("STEP 6: VERIFICATION")
        
        verification_results = []
        
        # 1. Check total users
        total_users = User.objects.count()
        verification_results.append((
            f"Total users: {total_users}",
            total_users >= 4,
            f"Expected ≥4, got {total_users}"
        ))
        
        # 2. Check admin exists
        admin_exists = User.objects.filter(username='admin', is_superuser=True).exists()
        verification_results.append((
            "Admin user exists",
            admin_exists,
            "Superuser 'admin' found" if admin_exists else "Admin not found"
        ))
        
        # 3. Check doctors exist (by username pattern)
        doctors_count = User.objects.filter(username__startswith='dr_').count()
        verification_results.append((
            f"Doctors: {doctors_count}",
            doctors_count >= 1,
            f"Expected ≥1 doctor, got {doctors_count}"
        ))
        
        # 4. Check patients exist
        patients = ['john_doe', 'jane_smith']
        patients_count = User.objects.filter(username__in=patients).count()
        verification_results.append((
            f"Patients: {patients_count}",
            patients_count >= 1,
            f"Expected ≥1 patient, got {patients_count}"
        ))
        
        # 5. Check disease models
        try:
            from prediction_app.models import DiseaseModel
            disease_count = DiseaseModel.objects.count()
            verification_results.append((
                f"Disease models: {disease_count}",
                disease_count >= 1,
                f"Found {disease_count} disease models"
            ))
        except:
            verification_results.append((
                "Disease models",
                False,
                "Could not verify disease models"
            ))
        
        # Print verification results
        for i, (check_name, success, detail) in enumerate(verification_results, 1):
            print_step(i, check_name, success, detail)
        
        # Calculate success rate
        passed = sum(1 for _, success, _ in verification_results if success)
        total = len(verification_results)
        success_rate = (passed / total) * 100
        
        print(f"\n📊 Verification Score: {passed}/{total} ({success_rate:.1f}%)")
        
        if success_rate >= 80:
            print("✅ SETUP VERIFICATION PASSED")
            return True
        else:
            print("⚠️ SETUP VERIFICATION HAS ISSUES")
            return False
    
    def print_summary(self):
        """Print setup summary and credentials"""
        print_banner("SETUP COMPLETE! 🎉")
        
        # Setup duration
        duration = self.stop_timer()
        print(f"⏱️  Setup completed in {duration:.1f} seconds")
        
        # Database info
        db_size = self.db_path.stat().st_size / (1024 * 1024) if self.db_path.exists() else 0
        print(f"💾 Database size: {db_size:.2f} MB")
        
        # User counts
        total_users = User.objects.count()
        doctors = User.objects.filter(user_type='doctor').count()
        patients = User.objects.filter(user_type='patient').count()
        staff = User.objects.filter(user_type__in=['pharmacist', 'lab_technician', 'receptionist']).count()
        
        print(f"👥 Users: {total_users} total")
        print(f"   ├─ 👨‍⚕️  Doctors: {doctors}")
        print(f"   ├─ 👤 Patients: {patients}")
        print(f"   └─ 👥 Staff: {staff}")
        
        # Login credentials
        print_banner("LOGIN CREDENTIALS")
        
        print("🔐 ADMIN ACCOUNT:")
        print("   Username: admin")
        print("   Password: Admin@123")
        print("   Email: admin@medipredict.com")
        print("   URL: http://localhost:8000/admin")
        
        print("\n👨‍⚕️ TEST DOCTORS:")
        doctors = User.objects.filter(user_type='doctor')[:3]
        for doctor in doctors:
            print(f"   {doctor.get_full_name()}:")
            print(f"     Username: {doctor.username}")
            print(f"     Password: Doctor@123")
        
        print("\n👤 TEST PATIENTS:")
        patients = User.objects.filter(user_type='patient')[:3]
        for patient in patients:
            print(f"   {patient.get_full_name()}:")
            print(f"     Username: {patient.username}")
            print(f"     Password: Patient@123")
        
        print("\n🚀 NEXT STEPS:")
        print("   1. Start server: python manage.py runserver")
        print("   2. Open browser: http://localhost:8000")
        print("   3. Login with credentials above")
        print("   4. Explore the admin panel at /admin")
        
        print("\n" + "═" * 60)
    
    def run_complete_setup(self, skip_migrations=False, quick_mode=False):
        """Run the complete database setup process"""
        self.start_timer()
        
        print_banner("MEDIPREDICT DATABASE SETUP")
        print("Starting complete database initialization...")
        
        steps = [
            ("Database Check", lambda: self.check_database()),
        ]
        
        if not skip_migrations:
            steps.append(("Run Migrations", lambda: self.run_migrations()))
        
        steps.extend([
            ("Create Admin User", lambda: self.create_admin_user()),
            ("Create Test Users", lambda: self.create_test_users()),
        ])
        
        if not quick_mode:
            steps.append(("Setup Sample Data", lambda: self.setup_sample_data()))
        
        steps.append(("Verify Setup", lambda: self.verify_setup()))
        
        # Execute all steps
        results = []
        for step_name, step_func in steps:
            print(f"\n▶️  Executing: {step_name}")
            try:
                result = step_func()
                results.append((step_name, result))
            except Exception as e:
                logger.error(f"Error in {step_name}: {e}")
                results.append((step_name, False))
        
        # Summary
        print_banner("SETUP SUMMARY")
        
        passed = sum(1 for _, success in results if success)
        total = len(results)
        
        for step_name, success in results:
            icon = "✅" if success else "❌"
            status = "PASS" if success else "FAIL"
            print(f"{icon} {status}: {step_name}")
        
        print(f"\n📈 Result: {passed}/{total} steps passed ({passed/total*100:.1f}%)")
        
        if passed == total:
            print("🎉 EXCELLENT! All steps completed successfully!")
        elif passed >= total * 0.7:
            print("👍 GOOD! Most steps completed successfully.")
        else:
            print("⚠️  SETUP HAS ISSUES. Some steps failed.")
        
        # Print final summary
        self.print_summary()
        
        return passed == total

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='MEDIPREDICT Database Setup - Fixed version without health_check issues',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Full setup
  %(prog)s --skip-migrations  # Skip migrations (if already run)
  %(prog)s --quick            # Quick setup (skip sample data)
  %(prog)s --admin-pass MyPass123  # Custom admin password
        """
    )
    
    parser.add_argument('--skip-migrations', action='store_true',
                       help='Skip running migrations (use if already migrated)')
    parser.add_argument('--quick', action='store_true',
                       help='Quick setup (skip sample data creation)')
    parser.add_argument('--admin-user', default='admin',
                       help='Admin username (default: admin)')
    parser.add_argument('--admin-email', default='admin@medipredict.com',
                       help='Admin email (default: admin@medipredict.com)')
    parser.add_argument('--admin-pass', default='Admin@123',
                       help='Admin password (default: Admin@123)')
    parser.add_argument('--force', action='store_true',
                       help='Force migrations even if not needed')
    parser.add_argument('--silent', action='store_true',
                       help='Run silently without prompts')
    
    args = parser.parse_args()
    
    # Display banner
    print("\n" + "⭐" * 60)
    print(" " * 20 + "MEDIPREDICT DATABASE SETUP")
    print(" " * 15 + "Fixed Version - No health_check issues")
    print("⭐" * 60)
    
    if not args.silent:
        print("\nThis script will:")
        print("  • Check database connection")
        print("  • Run Django migrations (unless skipped)")
        print("  • Create admin user")
        print("  • Create test users (doctors, patients, staff)")
        print("  • Setup sample data (diseases, symptoms, etc.)")
        print("  • Verify the complete setup")
        
        response = input("\nDo you want to continue? (yes/NO): ")
        if response.lower() not in ['yes', 'y']:
            print("\nSetup cancelled.")
            return
    
    try:
        # Run setup
        setup = DatabaseSetup()
        success = setup.run_complete_setup(
            skip_migrations=args.skip_migrations,
            quick_mode=args.quick
        )
        
        if success:
            print("\n" + "🎊" * 30)
            print("   MEDIPREDICT IS READY TO USE!")
            print("🎊" * 30)
        else:
            print("\n⚠️  Setup completed with some issues.")
            print("   Check the logs above for details.")
        
        # Exit with appropriate code
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\n❌ Setup interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        print("\nTroubleshooting:")
        print("1. Check if database exists: ls db.sqlite3")
        print("2. Run migrations manually: python manage.py migrate")
        print("3. Create admin manually: python manage.py createsuperuser")
        sys.exit(1)

if __name__ == '__main__':
    main()