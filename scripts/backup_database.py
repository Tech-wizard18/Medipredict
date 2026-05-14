#!/usr/bin/env python3
"""
Database backup script for MediPredict
Supports PostgreSQL, MySQL, and SQLite
"""

import os
import sys
import django
import argparse
from pathlib import Path
from datetime import datetime
import subprocess
import shutil
import logging
import zipfile
import hashlib

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'disease_app.settings')
django.setup()

from django.conf import settings

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/database_backup.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DatabaseBackup:
    def __init__(self, backup_dir='backups'):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
        
        # Get database config
        self.db_config = settings.DATABASES['default']
        self.engine = self.db_config.get('ENGINE', '')
        
        # Create backups subdirectories
        (self.backup_dir / 'database').mkdir(exist_ok=True)
        (self.backup_dir / 'media').mkdir(exist_ok=True)
        (self.backup_dir / 'logs').mkdir(exist_ok=True)
    
    def get_backup_filename(self, prefix='db_backup'):
        """Generate backup filename with timestamp"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"{prefix}_{timestamp}"
    
    def backup_postgresql(self):
        """Backup PostgreSQL database using pg_dump"""
        logger.info("Backing up PostgreSQL database...")
        
        db_name = self.db_config.get('NAME')
        db_user = self.db_config.get('USER')
        db_host = self.db_config.get('HOST', 'localhost')
        db_port = self.db_config.get('PORT', '5432')
        db_password = self.db_config.get('PASSWORD', '')
        
        # Set password in environment
        env = os.environ.copy()
        if db_password:
            env['PGPASSWORD'] = db_password
        
        # Generate backup filename
        backup_file = self.backup_dir / 'database' / f"{self.get_backup_filename()}.sql"
        
        # Build pg_dump command
        cmd = [
            'pg_dump',
            '-h', db_host,
            '-p', db_port,
            '-U', db_user,
            '-d', db_name,
            '-F', 'c',  # Custom format (compressed)
            '-f', str(backup_file)
        ]
        
        try:
            logger.info(f"Running: {' '.join(cmd[:5])}...")
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode == 0:
                size_mb = backup_file.stat().st_size / (1024 * 1024)
                logger.info(f"✅ PostgreSQL backup created: {backup_file.name} ({size_mb:.2f} MB)")
                return backup_file
            else:
                logger.error(f"❌ PostgreSQL backup failed: {result.stderr}")
                return None
                
        except FileNotFoundError:
            logger.error("❌ pg_dump not found. Install PostgreSQL client tools.")
            return None
        except Exception as e:
            logger.error(f"❌ PostgreSQL backup error: {e}")
            return None
    
    def backup_mysql(self):
        """Backup MySQL database using mysqldump"""
        logger.info("Backing up MySQL database...")
        
        db_name = self.db_config.get('NAME')
        db_user = self.db_config.get('USER')
        db_host = self.db_config.get('HOST', 'localhost')
        db_port = self.db_config.get('PORT', '3306')
        db_password = self.db_config.get('PASSWORD', '')
        
        # Generate backup filename
        backup_file = self.backup_dir / 'database' / f"{self.get_backup_filename()}.sql"
        
        # Build mysqldump command
        cmd = [
            'mysqldump',
            '-h', db_host,
            '-P', db_port,
            '-u', db_user,
            f'--password={db_password}' if db_password else '',
            '--single-transaction',
            '--routines',
            '--triggers',
            db_name
        ]
        
        # Remove empty strings
        cmd = [c for c in cmd if c]
        
        try:
            logger.info(f"Running mysqldump for database: {db_name}")
            with open(backup_file, 'w') as f:
                result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)
            
            if result.returncode == 0:
                size_mb = backup_file.stat().st_size / (1024 * 1024)
                logger.info(f"✅ MySQL backup created: {backup_file.name} ({size_mb:.2f} MB)")
                return backup_file
            else:
                logger.error(f"❌ MySQL backup failed: {result.stderr}")
                return None
                
        except FileNotFoundError:
            logger.error("❌ mysqldump not found. Install MySQL client tools.")
            return None
        except Exception as e:
            logger.error(f"❌ MySQL backup error: {e}")
            return None
    
    def backup_sqlite(self):
        """Backup SQLite database by copying the file"""
        logger.info("Backing up SQLite database...")
        
        db_path = Path(self.db_config.get('NAME'))
        
        if not db_path.exists():
            logger.error(f"❌ SQLite database not found: {db_path}")
            return None
        
        # Generate backup filename
        backup_file = self.backup_dir / 'database' / f"{self.get_backup_filename()}.db"
        
        try:
            # Copy the database file
            shutil.copy2(db_path, backup_file)
            
            size_mb = backup_file.stat().st_size / (1024 * 1024)
            logger.info(f"✅ SQLite backup created: {backup_file.name} ({size_mb:.2f} MB)")
            return backup_file
            
        except Exception as e:
            logger.error(f"❌ SQLite backup error: {e}")
            return None
    
    def backup_media_files(self):
        """Backup media files"""
        logger.info("Backing up media files...")
        
        media_dir = Path('media')
        if not media_dir.exists():
            logger.warning("⚠️ Media directory not found")
            return None
        
        # Create media backup directory
        media_backup_dir = self.backup_dir / 'media' / datetime.now().strftime('%Y%m%d')
        media_backup_dir.mkdir(exist_ok=True, parents=True)
        
        try:
            # Copy media files
            for item in media_dir.rglob('*'):
                if item.is_file():
                    # Create relative path
                    rel_path = item.relative_to(media_dir)
                    dest_path = media_backup_dir / rel_path
                    dest_path.parent.mkdir(exist_ok=True, parents=True)
                    shutil.copy2(item, dest_path)
            
            # Count files
            file_count = sum(1 for _ in media_backup_dir.rglob('*') if _.is_file())
            logger.info(f"✅ Media backup created: {file_count} files")
            return media_backup_dir
            
        except Exception as e:
            logger.error(f"❌ Media backup error: {e}")
            return None
    
    def backup_logs(self):
        """Backup log files"""
        logger.info("Backing up log files...")
        
        logs_dir = Path('logs')
        if not logs_dir.exists():
            logger.warning("⚠️ Logs directory not found")
            return None
        
        # Create logs backup directory
        logs_backup_dir = self.backup_dir / 'logs' / datetime.now().strftime('%Y%m%d')
        logs_backup_dir.mkdir(exist_ok=True, parents=True)
        
        try:
            # Copy log files (excluding current backup log)
            for log_file in logs_dir.glob('*.log'):
                if 'backup' not in log_file.name.lower():
                    shutil.copy2(log_file, logs_backup_dir / log_file.name)
            
            # Count files
            file_count = sum(1 for _ in logs_backup_dir.rglob('*.log'))
            logger.info(f"✅ Logs backup created: {file_count} files")
            return logs_backup_dir
            
        except Exception as e:
            logger.error(f"❌ Logs backup error: {e}")
            return None
    
    def create_compressed_archive(self, backup_files):
        """Create compressed archive of all backups"""
        logger.info("Creating compressed archive...")
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        archive_file = self.backup_dir / f"full_backup_{timestamp}.zip"
        
        try:
            with zipfile.ZipFile(archive_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add database backup
                for backup_file in backup_files:
                    if backup_file and backup_file.exists():
                        if backup_file.is_dir():
                            # Add directory contents
                            for file in backup_file.rglob('*'):
                                if file.is_file():
                                    arcname = file.relative_to(self.backup_dir)
                                    zipf.write(file, arcname)
                        else:
                            # Add single file
                            arcname = backup_file.relative_to(self.backup_dir)
                            zipf.write(backup_file, arcname)
                
                # Add README file
                readme_content = f"""MediPredict Backup Archive
Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Contains: Database, Media files, Logs
"""
                zipf.writestr('README.txt', readme_content)
            
            size_mb = archive_file.stat().st_size / (1024 * 1024)
            logger.info(f"✅ Compressed archive created: {archive_file.name} ({size_mb:.2f} MB)")
            return archive_file
            
        except Exception as e:
            logger.error(f"❌ Archive creation error: {e}")
            return None
    
    def calculate_checksum(self, file_path):
        """Calculate MD5 checksum of a file"""
        hash_md5 = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def cleanup_old_backups(self, days_to_keep=30):
        """Cleanup old backup files"""
        logger.info(f"Cleaning up backups older than {days_to_keep} days...")
        
        cutoff_date = datetime.now().timestamp() - (days_to_keep * 24 * 3600)
        deleted_count = 0
        
        try:
            for backup_file in self.backup_dir.rglob('*'):
                if backup_file.is_file():
                    if backup_file.stat().st_mtime < cutoff_date:
                        backup_file.unlink()
                        deleted_count += 1
            
            logger.info(f"✅ Cleaned up {deleted_count} old backup files")
            return deleted_count
            
        except Exception as e:
            logger.error(f"❌ Cleanup error: {e}")
            return 0
    
    def create_backup(self, full_backup=True, cleanup_old=True):
        """Create complete backup"""
        logger.info("=" * 60)
        logger.info("Starting Database Backup")
        logger.info(f"Database Engine: {self.engine}")
        logger.info(f"Backup Directory: {self.backup_dir}")
        logger.info("=" * 60)
        
        backup_files = []
        
        # Backup database based on engine
        if 'postgresql' in self.engine:
            db_backup = self.backup_postgresql()
        elif 'mysql' in self.engine:
            db_backup = self.backup_mysql()
        elif 'sqlite' in self.engine:
            db_backup = self.backup_sqlite()
        else:
            logger.error(f"❌ Unsupported database engine: {self.engine}")
            return None
        
        if db_backup:
            backup_files.append(db_backup)
        
        # Backup media files if full backup requested
        if full_backup:
            media_backup = self.backup_media_files()
            if media_backup:
                backup_files.append(media_backup)
            
            logs_backup = self.backup_logs()
            if logs_backup:
                backup_files.append(logs_backup)
        
        # Create compressed archive
        if backup_files:
            archive = self.create_compressed_archive(backup_files)
            if archive:
                # Calculate checksum
                checksum = self.calculate_checksum(archive)
                checksum_file = archive.with_suffix('.md5')
                checksum_file.write_text(f"{checksum}  {archive.name}\n")
                logger.info(f"✅ Checksum created: {checksum_file.name}")
                
                # Cleanup individual backup files
                for backup_file in backup_files:
                    if backup_file.exists():
                        if backup_file.is_file():
                            backup_file.unlink()
                        elif backup_file.is_dir():
                            shutil.rmtree(backup_file)
                
                # Cleanup old backups
                if cleanup_old:
                    self.cleanup_old_backups()
                
                logger.info("=" * 60)
                logger.info(f"🎉 Backup completed successfully!")
                logger.info(f"Archive: {archive.name}")
                logger.info(f"Size: {archive.stat().st_size / (1024*1024):.2f} MB")
                logger.info(f"Checksum: {checksum}")
                logger.info("=" * 60)
                
                return archive
        
        logger.error("❌ Backup failed")
        return None
    
    def list_backups(self):
        """List all available backups"""
        logger.info("Listing available backups...")
        
        backups = []
        for backup_file in self.backup_dir.glob('full_backup_*.zip'):
            if backup_file.is_file():
                size_mb = backup_file.stat().st_size / (1024 * 1024)
                mtime = datetime.fromtimestamp(backup_file.stat().st_mtime)
                backups.append({
                    'file': backup_file.name,
                    'size_mb': size_mb,
                    'modified': mtime,
                    'checksum': None
                })
        
        if backups:
            logger.info(f"Found {len(backups)} backup(s):")
            for backup in sorted(backups, key=lambda x: x['modified'], reverse=True):
                logger.info(f"  {backup['file']} - {backup['size_mb']:.2f} MB - {backup['modified'].strftime('%Y-%m-%d %H:%M')}")
        else:
            logger.info("No backups found")
        
        return backups

def main():
    parser = argparse.ArgumentParser(description='MediPredict Database Backup')
    parser.add_argument('--list', action='store_true',
                       help='List available backups')
    parser.add_argument('--partial', action='store_true',
                       help='Backup only database (no media or logs)')
    parser.add_argument('--no-cleanup', action='store_true',
                       help='Do not cleanup old backups')
    parser.add_argument('--days-to-keep', type=int, default=30,
                       help='Days to keep backups (default: 30)')
    parser.add_argument('--output-dir', default='backups',
                       help='Backup directory (default: backups)')
    
    args = parser.parse_args()
    
    backup = DatabaseBackup(backup_dir=args.output_dir)
    
    if args.list:
        backup.list_backups()
    else:
        backup.create_backup(
            full_backup=not args.partial,
            cleanup_old=not args.no_cleanup
        )

if __name__ == '__main__':
    main()