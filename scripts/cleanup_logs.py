#!/usr/bin/env python3
"""
Log cleanup and maintenance script for MediPredict
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta
import gzip
import shutil
import logging
import json

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

# Setup logging for this script
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/cleanup.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class LogCleanup:
    def __init__(self, logs_dir='logs', retention_days=30):
        self.logs_dir = Path(logs_dir)
        self.retention_days = retention_days
        self.cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        # Ensure logs directory exists
        self.logs_dir.mkdir(exist_ok=True)
    
    def cleanup_log_files(self):
        """Cleanup old log files"""
        logger.info(f"Cleaning up log files older than {self.retention_days} days...")
        
        deleted_files = []
        deleted_size = 0
        
        # Process all .log files
        for log_file in self.logs_dir.glob('*.log'):
            try:
                # Skip active log files that might be in use
                if self._is_file_active(log_file):
                    continue
                
                # Check file modification time
                mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                
                if mtime < self.cutoff_date:
                    # Compress before deletion
                    compressed_file = self._compress_log_file(log_file)
                    if compressed_file:
                        # Delete original file
                        file_size = log_file.stat().st_size
                        log_file.unlink()
                        
                        deleted_files.append(log_file.name)
                        deleted_size += file_size
                        
                        logger.info(f"Compressed and removed: {log_file.name}")
                    else:
                        logger.warning(f"Failed to compress: {log_file.name}")
                        
            except Exception as e:
                logger.error(f"Error processing {log_file}: {e}")
        
        # Cleanup old compressed files
        self._cleanup_compressed_logs()
        
        # Summary
        if deleted_files:
            size_mb = deleted_size / (1024 * 1024)
            logger.info(f"✅ Cleaned up {len(deleted_files)} log files ({size_mb:.2f} MB)")
        else:
            logger.info("✅ No old log files to clean up")
        
        return deleted_files
    
    def _is_file_active(self, file_path):
        """Check if a file is currently being written to"""
        try:
            # Try to open file in append mode
            with open(file_path, 'a') as f:
                f.write('')
            return False
        except IOError:
            # File is locked/being used
            return True
    
    def _compress_log_file(self, log_file):
        """Compress a log file using gzip"""
        compressed_file = log_file.with_suffix('.log.gz')
        
        try:
            with open(log_file, 'rb') as f_in:
                with gzip.open(compressed_file, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            return compressed_file
        except Exception as e:
            logger.error(f"Compression error for {log_file}: {e}")
            return None
    
    def _cleanup_compressed_logs(self):
        """Cleanup old compressed log files"""
        logger.info("Cleaning up old compressed logs...")
        
        deleted_count = 0
        cutoff_timestamp = self.cutoff_date.timestamp()
        
        for compressed_file in self.logs_dir.glob('*.log.gz'):
            try:
                if compressed_file.stat().st_mtime < cutoff_timestamp:
                    compressed_file.unlink()
                    deleted_count += 1
            except Exception as e:
                logger.error(f"Error deleting {compressed_file}: {e}")
        
        if deleted_count > 0:
            logger.info(f"✅ Removed {deleted_count} old compressed log files")
        
        return deleted_count
    
    def analyze_log_sizes(self):
        """Analyze log file sizes"""
        logger.info("Analyzing log file sizes...")
        
        log_sizes = {}
        total_size = 0
        
        # Get all log files
        for log_file in self.logs_dir.glob('*.log'):
            try:
                size_mb = log_file.stat().st_size / (1024 * 1024)
                log_sizes[log_file.name] = {
                    'size_mb': size_mb,
                    'modified': datetime.fromtimestamp(log_file.stat().st_mtime)
                }
                total_size += size_mb
            except Exception as e:
                logger.error(f"Error analyzing {log_file}: {e}")
        
        # Get compressed files
        compressed_sizes = {}
        for compressed_file in self.logs_dir.glob('*.log.gz'):
            try:
                size_mb = compressed_file.stat().st_size / (1024 * 1024)
                compressed_sizes[compressed_file.name] = {
                    'size_mb': size_mb,
                    'modified': datetime.fromtimestamp(compressed_file.stat().st_mtime)
                }
                total_size += size_mb
            except Exception as e:
                logger.error(f"Error analyzing {compressed_file}: {e}")
        
        # Print analysis
        logger.info(f"Total logs directory size: {total_size:.2f} MB")
        
        if log_sizes:
            logger.info("\nActive log files:")
            for name, info in sorted(log_sizes.items(), key=lambda x: x[1]['size_mb'], reverse=True):
                logger.info(f"  {name}: {info['size_mb']:.2f} MB (modified: {info['modified'].strftime('%Y-%m-%d')})")
        
        if compressed_sizes:
            logger.info("\nCompressed log files:")
            for name, info in sorted(compressed_sizes.items(), key=lambda x: x[1]['modified'], reverse=True)[:10]:
                logger.info(f"  {name}: {info['size_mb']:.2f} MB (modified: {info['modified'].strftime('%Y-%m-%d')})")
        
        return {
            'active_logs': log_sizes,
            'compressed_logs': compressed_sizes,
            'total_size_mb': total_size
        }
    
    def cleanup_empty_logs(self):
        """Remove empty log files"""
        logger.info("Cleaning up empty log files...")
        
        deleted_files = []
        
        for log_file in self.logs_dir.glob('*.log'):
            try:
                if log_file.stat().st_size == 0:
                    # Check if file has been empty for more than 1 day
                    mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                    if datetime.now() - mtime > timedelta(days=1):
                        log_file.unlink()
                        deleted_files.append(log_file.name)
            except Exception as e:
                logger.error(f"Error checking {log_file}: {e}")
        
        if deleted_files:
            logger.info(f"✅ Removed {len(deleted_files)} empty log files: {', '.join(deleted_files)}")
        
        return deleted_files
    
    def rotate_large_logs(self, max_size_mb=10):
        """Rotate log files that exceed maximum size"""
        logger.info(f"Rotating log files larger than {max_size_mb} MB...")
        
        max_size_bytes = max_size_mb * 1024 * 1024
        rotated_files = []
        
        for log_file in self.logs_dir.glob('*.log'):
            try:
                if log_file.stat().st_size > max_size_bytes:
                    # Create rotated filename with timestamp
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    rotated_name = f"{log_file.stem}_{timestamp}.log"
                    rotated_file = log_file.with_name(rotated_name)
                    
                    # Rename the current log file
                    shutil.move(log_file, rotated_file)
                    
                    # Create new empty log file
                    log_file.touch()
                    
                    # Compress the rotated file
                    compressed_file = self._compress_log_file(rotated_file)
                    if compressed_file:
                        rotated_file.unlink()  # Delete uncompressed rotated file
                        rotated_files.append(compressed_file.name)
                    else:
                        rotated_files.append(rotated_file.name)
                    
                    logger.info(f"Rotated: {log_file.name} -> {rotated_file.name}")
                    
            except Exception as e:
                logger.error(f"Error rotating {log_file}: {e}")
        
        if rotated_files:
            logger.info(f"✅ Rotated {len(rotated_files)} log files")
        
        return rotated_files
    
    def generate_report(self):
        """Generate cleanup report"""
        logger.info("Generating cleanup report...")
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'retention_days': self.retention_days,
            'cleanup_results': {},
            'analysis': {},
            'recommendations': []
        }
        
        # Run analysis
        analysis = self.analyze_log_sizes()
        report['analysis'] = analysis
        
        # Run cleanup
        cleaned_files = self.cleanup_log_files()
        report['cleanup_results']['cleaned_files'] = cleaned_files
        
        # Rotate large files
        rotated_files = self.rotate_large_logs()
        report['cleanup_results']['rotated_files'] = rotated_files
        
        # Cleanup empty logs
        empty_files = self.cleanup_empty_logs()
        report['cleanup_results']['empty_files'] = empty_files
        
        # Generate recommendations
        total_size = analysis['total_size_mb']
        
        if total_size > 100:  # If logs exceed 100 MB
            report['recommendations'].append(
                f"Log directory is large ({total_size:.1f} MB). Consider increasing log rotation frequency."
            )
        
        if len(analysis['active_logs']) > 20:
            report['recommendations'].append(
                f"Many active log files ({len(analysis['active_logs'])}). Consider consolidating logs."
            )
        
        # Save report
        report_file = self.logs_dir / f"cleanup_report_{datetime.now().strftime('%Y%m%d')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"✅ Report saved: {report_file.name}")
        
        # Print summary
        logger.info("\n" + "="*60)
        logger.info("CLEANUP SUMMARY")
        logger.info("="*60)
        logger.info(f"Total log size: {total_size:.2f} MB")
        logger.info(f"Files cleaned: {len(cleaned_files)}")
        logger.info(f"Files rotated: {len(rotated_files)}")
        logger.info(f"Empty files removed: {len(empty_files)}")
        
        if report['recommendations']:
            logger.info("\nRecommendations:")
            for rec in report['recommendations']:
                logger.info(f"  • {rec}")
        
        logger.info("="*60)
        
        return report
    
    def run_all(self):
        """Run all cleanup operations"""
        logger.info("="*60)
        logger.info("Starting Complete Log Cleanup")
        logger.info(f"Logs Directory: {self.logs_dir}")
        logger.info(f"Retention Period: {self.retention_days} days")
        logger.info("="*60)
        
        report = self.generate_report()
        
        logger.info("✅ Log cleanup completed successfully!")
        return report

def main():
    parser = argparse.ArgumentParser(description='MediPredict Log Cleanup')
    parser.add_argument('--dir', default='logs',
                       help='Logs directory (default: logs)')
    parser.add_argument('--retention', type=int, default=30,
                       help='Retention period in days (default: 30)')
    parser.add_argument('--analyze', action='store_true',
                       help='Only analyze log sizes, no cleanup')
    parser.add_argument('--rotate-size', type=int, default=10,
                       help='Maximum log file size in MB before rotation (default: 10)')
    parser.add_argument('--report', action='store_true',
                       help='Generate detailed report')
    
    args = parser.parse_args()
    
    cleanup = LogCleanup(
        logs_dir=args.dir,
        retention_days=args.retention
    )
    
    if args.analyze:
        cleanup.analyze_log_sizes()
    elif args.report:
        cleanup.generate_report()
    else:
        cleanup.run_all()

if __name__ == '__main__':
    main()