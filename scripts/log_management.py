#!/usr/bin/env python3
"""
Log Management Utility for MEDIPREDICT
Handles log rotation, cleanup, analysis, and monitoring.
"""

import os
import sys
import re
import gzip
import json
import shutil
import argparse
import logging
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from collections import defaultdict, Counter
import pandas as pd
import numpy as np

# Configure logging for this script
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/log_management.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class LogManager:
    """Manage application logs including rotation, cleanup, and analysis."""
    
    def __init__(self, logs_dir='logs', retention_days=30, max_log_size_mb=100):
        self.project_root = Path(__file__).parent.parent
        self.logs_dir = self.project_root / logs_dir
        self.retention_days = retention_days
        self.max_log_size_bytes = max_log_size_mb * 1024 * 1024
        
        # Log patterns for different log types
        self.log_patterns = {
            'django': r'django(?:\.log(?:\.\d+)?)?',
            'celery': r'celery(?:\.log(?:\.\d+)?)?',
            'error': r'errors(?:\.log(?:\.\d+)?)?',
            'prediction': r'prediction(?:\.log(?:\.\d+)?)?',
            'api': r'api(?:\.log(?:\.\d+)?)?',
            'request': r'requests(?:\.log(?:\.\d+)?)?',
            'access': r'access(?:\.log(?:\.\d+)?)?',
            'health': r'health_check(?:\.log(?:\.\d+)?)?',
            'training': r'training(?:\.log(?:\.\d+)?)?',
        }
        
        # Critical error patterns
        self.error_patterns = {
            'critical': [
                r'CRITICAL',
                r'500 Internal Server Error',
                r'DatabaseError',
                r'OperationalError',
                r'MemoryError',
                r'Segmentation fault',
                r'OutOfMemoryError'
            ],
            'error': [
                r'ERROR',
                r'Exception:',
                r'Traceback',
                r'failed',
                r'timeout',
                r'connection refused'
            ],
            'warning': [
                r'WARNING',
                r'Warning:',
                r'deprecated',
                r'will be removed'
            ]
        }
        
        # Ensure logs directory exists
        self.logs_dir.mkdir(exist_ok=True)
    
    def rotate_logs(self, force=False):
        """Rotate log files based on size."""
        rotated_files = []
        
        for log_file in self.logs_dir.iterdir():
            if log_file.is_file() and log_file.suffix == '.log':
                try:
                    file_size = log_file.stat().st_size
                    
                    if force or file_size >= self.max_log_size_bytes:
                        # Create backup with timestamp
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        backup_file = log_file.parent / f"{log_file.stem}_{timestamp}.log"
                        
                        # Move current log to backup
                        shutil.move(log_file, backup_file)
                        
                        # Create new empty log file
                        log_file.touch()
                        
                        # Compress old backup files
                        self.compress_old_logs()
                        
                        rotated_files.append(str(log_file))
                        logger.info(f"Rotated log file: {log_file.name} -> {backup_file.name}")
                        
                except Exception as e:
                    logger.error(f"Error rotating {log_file}: {e}")
        
        return rotated_files
    
    def compress_old_logs(self, days_threshold=7):
        """Compress log files older than specified days."""
        compressed_files = []
        threshold_date = datetime.now() - timedelta(days=days_threshold)
        
        for log_file in self.logs_dir.iterdir():
            if log_file.is_file() and log_file.suffix == '.log':
                try:
                    # Check if file is old enough
                    file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                    
                    if file_mtime < threshold_date:
                        # Check if not already compressed
                        if not log_file.with_suffix('.log.gz').exists():
                            # Compress the file
                            with open(log_file, 'rb') as f_in:
                                with gzip.open(f"{log_file}.gz", 'wb') as f_out:
                                    shutil.copyfileobj(f_in, f_out)
                            
                            # Remove original file
                            log_file.unlink()
                            compressed_files.append(str(log_file))
                            logger.info(f"Compressed log file: {log_file.name}")
                            
                except Exception as e:
                    logger.error(f"Error compressing {log_file}: {e}")
        
        return compressed_files
    
    def cleanup_old_logs(self):
        """Remove old log files based on retention policy."""
        removed_files = []
        threshold_date = datetime.now() - timedelta(days=self.retention_days)
        
        for log_file in self.logs_dir.iterdir():
            if log_file.is_file():
                try:
                    # Get file modification time
                    file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                    
                    if file_mtime < threshold_date:
                        # Remove the file
                        log_file.unlink()
                        removed_files.append(str(log_file))
                        logger.info(f"Removed old log file: {log_file.name}")
                        
                except Exception as e:
                    logger.error(f"Error removing {log_file}: {e}")
        
        return removed_files
    
    def analyze_logs(self, log_type=None, days=1):
        """Analyze logs for patterns and statistics."""
        analysis_results = {
            'timestamp': datetime.now().isoformat(),
            'period_days': days,
            'log_type': log_type or 'all',
            'summary': {},
            'errors': {},
            'patterns': {},
            'performance': {}
        }
        
        try:
            # Get log files to analyze
            log_files = self.get_log_files(log_type, days)
            
            # Analyze each log file
            for log_file in log_files:
                file_stats = self.analyze_single_log(log_file)
                
                # Merge statistics
                for key, value in file_stats.items():
                    if key not in analysis_results['summary']:
                        analysis_results['summary'][key] = value
                    else:
                        if isinstance(value, (int, float)):
                            analysis_results['summary'][key] += value
                        elif isinstance(value, dict):
                            for sub_key, sub_value in value.items():
                                if sub_key not in analysis_results['summary'][key]:
                                    analysis_results['summary'][key][sub_key] = sub_value
                                else:
                                    analysis_results['summary'][key][sub_key] += sub_value
            
            # Generate insights
            analysis_results['insights'] = self.generate_insights(analysis_results)
            
            # Save analysis report
            self.save_analysis_report(analysis_results)
            
            return analysis_results
            
        except Exception as e:
            logger.error(f"Error analyzing logs: {e}")
            return analysis_results
    
    def get_log_files(self, log_type=None, days=1):
        """Get log files for analysis."""
        log_files = []
        threshold_date = datetime.now() - timedelta(days=days)
        
        for log_file in self.logs_dir.iterdir():
            if log_file.is_file():
                # Check if file matches log type
                if log_type:
                    pattern = self.log_patterns.get(log_type)
                    if pattern and re.match(pattern, log_file.stem):
                        pass
                    elif log_type not in self.log_patterns:
                        # If log_type is a filename pattern
                        if log_type in log_file.name:
                            pass
                        else:
                            continue
                
                # Check if file is within date range
                file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                if file_mtime >= threshold_date:
                    log_files.append(log_file)
        
        return log_files
    
    def analyze_single_log(self, log_file: Path) -> Dict[str, Any]:
        """Analyze a single log file."""
        stats = {
            'file': log_file.name,
            'size_mb': log_file.stat().st_size / (1024 * 1024),
            'line_count': 0,
            'error_count': 0,
            'warning_count': 0,
            'critical_count': 0,
            'level_distribution': defaultdict(int),
            'hourly_distribution': defaultdict(int),
            'common_messages': Counter(),
            'recent_errors': []
        }
        
        try:
            # Determine file type and open appropriately
            if log_file.suffix == '.gz':
                open_func = gzip.open
                mode = 'rt'
            else:
                open_func = open
                mode = 'r'
            
            with open_func(log_file, mode, encoding='utf-8', errors='ignore') as f:
                for line in f:
                    stats['line_count'] += 1
                    
                    # Extract timestamp if available
                    timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
                    if timestamp_match:
                        hour = timestamp_match.group(1)[11:13]
                        stats['hourly_distribution'][hour] += 1
                    
                    # Check for error levels
                    line_lower = line.lower()
                    
                    if any(pattern.lower() in line_lower for pattern in self.error_patterns['critical']):
                        stats['critical_count'] += 1
                        stats['level_distribution']['CRITICAL'] += 1
                        stats['recent_errors'].append(line.strip())
                    
                    elif any(pattern.lower() in line_lower for pattern in self.error_patterns['error']):
                        stats['error_count'] += 1
                        stats['level_distribution']['ERROR'] += 1
                        stats['recent_errors'].append(line.strip())
                    
                    elif any(pattern.lower() in line_lower for pattern in self.error_patterns['warning']):
                        stats['warning_count'] += 1
                        stats['level_distribution']['WARNING'] += 1
                    
                    elif 'INFO' in line:
                        stats['level_distribution']['INFO'] += 1
                    
                    elif 'DEBUG' in line:
                        stats['level_distribution']['DEBUG'] += 1
                    
                    # Extract message content for common patterns
                    message_match = re.search(r'(ERROR|WARNING|INFO|DEBUG|CRITICAL).*?-\s*(.+)', line)
                    if message_match:
                        message = message_match.group(2)[:100]  # First 100 chars
                        stats['common_messages'][message] += 1
            
            # Keep only recent errors (last 50)
            stats['recent_errors'] = stats['recent_errors'][-50:]
            
        except Exception as e:
            logger.error(f"Error analyzing {log_file}: {e}")
            stats['error'] = str(e)
        
        return stats
    
    def generate_insights(self, analysis_results: Dict) -> Dict[str, Any]:
        """Generate insights from log analysis."""
        insights = {
            'health_status': 'HEALTHY',
            'issues_found': [],
            'recommendations': [],
            'metrics': {}
        }
        
        summary = analysis_results['summary']
        
        # Calculate error rate
        total_lines = summary.get('line_count', 1)
        total_errors = summary.get('error_count', 0) + summary.get('critical_count', 0)
        error_rate = (total_errors / total_lines) * 100
        
        insights['metrics']['error_rate'] = f"{error_rate:.2f}%"
        insights['metrics']['total_lines'] = total_lines
        insights['metrics']['total_errors'] = total_errors
        insights['metrics']['total_warnings'] = summary.get('warning_count', 0)
        
        # Determine health status
        if summary.get('critical_count', 0) > 0:
            insights['health_status'] = 'CRITICAL'
            insights['issues_found'].append(f"Critical errors detected: {summary['critical_count']}")
        
        elif error_rate > 5:  # More than 5% error rate
            insights['health_status'] = 'UNHEALTHY'
            insights['issues_found'].append(f"High error rate: {error_rate:.2f}%")
        
        elif summary.get('warning_count', 0) > 100:
            insights['health_status'] = 'WARNING'
            insights['issues_found'].append(f"Many warnings: {summary['warning_count']}")
        
        # Generate recommendations
        if error_rate > 10:
            insights['recommendations'].append(
                "Investigate high error rate in application logs"
            )
        
        if summary.get('critical_count', 0) > 0:
            insights['recommendations'].append(
                "Review critical errors immediately"
            )
        
        # Check for common error patterns
        if 'common_messages' in summary:
            common_errors = summary['common_messages'].most_common(5)
            if common_errors:
                insights['common_errors'] = common_errors
        
        # Check hourly distribution for peak error times
        if 'hourly_distribution' in summary:
            hourly_data = dict(summary['hourly_distribution'])
            if hourly_data:
                peak_hour = max(hourly_data.items(), key=lambda x: x[1])
                insights['metrics']['peak_hour'] = f"{peak_hour[0]}:00 ({peak_hour[1]} events)"
        
        return insights
    
    def save_analysis_report(self, analysis_results: Dict):
        """Save analysis report to file."""
        try:
            reports_dir = self.project_root / 'log_reports'
            reports_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_file = reports_dir / f'log_analysis_{timestamp}.json'
            
            with open(report_file, 'w') as f:
                json.dump(analysis_results, f, indent=2, default=str)
            
            logger.info(f"Log analysis report saved: {report_file}")
            
            # Also save a simplified HTML report
            self.generate_html_report(analysis_results, report_file.with_suffix('.html'))
            
        except Exception as e:
            logger.error(f"Error saving analysis report: {e}")
    
    def generate_html_report(self, analysis_results: Dict, output_file: Path):
        """Generate HTML report from analysis results."""
        try:
            html_content = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>MEDIPREDICT Log Analysis Report</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
                    .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                    .header {{ text-align: center; padding-bottom: 20px; border-bottom: 2px solid #4CAF50; }}
                    .status {{ padding: 10px; border-radius: 5px; margin: 10px 0; font-weight: bold; }}
                    .healthy {{ background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }}
                    .warning {{ background-color: #fff3cd; color: #856404; border: 1px solid #ffeaa7; }}
                    .critical {{ background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }}
                    .section {{ margin: 20px 0; padding: 15px; background: #f8f9fa; border-radius: 5px; }}
                    .section h3 {{ color: #495057; border-bottom: 1px solid #dee2e6; padding-bottom: 10px; }}
                    .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }}
                    .metric-card {{ background: white; padding: 15px; border-radius: 5px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); text-align: center; }}
                    .metric-value {{ font-size: 24px; font-weight: bold; color: #4CAF50; }}
                    .metric-label {{ color: #6c757d; font-size: 14px; }}
                    table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
                    th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #dee2e6; }}
                    th {{ background-color: #e9ecef; }}
                    .error-line {{ font-family: monospace; background: #fff5f5; padding: 5px; border-radius: 3px; margin: 2px 0; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>📊 MEDIPREDICT Log Analysis Report</h1>
                        <p>Generated: {analysis_results['timestamp']}</p>
                        <p>Period: {analysis_results['period_days']} days | Log Type: {analysis_results['log_type']}</p>
                    </div>
                    
                    <div class="section">
                        <h2>📈 System Health Status</h2>
                        <div class="status {analysis_results['insights']['health_status'].lower()}">
                            Status: {analysis_results['insights']['health_status']}
                        </div>
                        
                        <div class="metrics">
            """
            
            # Add metrics cards
            for key, value in analysis_results['insights']['metrics'].items():
                html_content += f"""
                            <div class="metric-card">
                                <div class="metric-value">{value}</div>
                                <div class="metric-label">{key.replace('_', ' ').title()}</div>
                            </div>
                """
            
            html_content += """
                        </div>
                    </div>
            """
            
            # Add issues found
            if analysis_results['insights']['issues_found']:
                html_content += """
                    <div class="section">
                        <h3>⚠️ Issues Found</h3>
                        <ul>
                """
                for issue in analysis_results['insights']['issues_found']:
                    html_content += f"<li>{issue}</li>"
                html_content += """
                        </ul>
                    </div>
                """
            
            # Add recommendations
            if analysis_results['insights']['recommendations']:
                html_content += """
                    <div class="section">
                        <h3>💡 Recommendations</h3>
                        <ul>
                """
                for rec in analysis_results['insights']['recommendations']:
                    html_content += f"<li>{rec}</li>"
                html_content += """
                        </ul>
                    </div>
                """
            
            # Add summary statistics
            if 'summary' in analysis_results:
                html_content += """
                    <div class="section">
                        <h3>📊 Summary Statistics</h3>
                        <table>
                            <tr>
                                <th>Metric</th>
                                <th>Value</th>
                            </tr>
                """
                
                summary = analysis_results['summary']
                for key, value in summary.items():
                    if key not in ['common_messages', 'recent_errors', 'hourly_distribution']:
                        if isinstance(value, (int, float)):
                            html_content += f"""
                            <tr>
                                <td>{key.replace('_', ' ').title()}</td>
                                <td>{value}</td>
                            </tr>
                            """
                
                html_content += """
                        </table>
                    </div>
                """
            
            # Add recent errors
            if 'summary' in analysis_results and 'recent_errors' in analysis_results['summary']:
                recent_errors = analysis_results['summary']['recent_errors'][-10:]  # Last 10 errors
                if recent_errors:
                    html_content += """
                        <div class="section">
                            <h3>🚨 Recent Errors</h3>
                    """
                    for error in recent_errors:
                        html_content += f'<div class="error-line">{error}</div>'
                    html_content += """
                        </div>
                    """
            
            html_content += """
                </div>
                <footer style="text-align: center; margin-top: 30px; color: #6c757d; font-size: 12px;">
                    <p>MEDIPREDICT Log Management System | Generated automatically</p>
                </footer>
            </body>
            </html>
            """
            
            with open(output_file, 'w') as f:
                f.write(html_content)
            
            logger.info(f"HTML report generated: {output_file}")
            
        except Exception as e:
            logger.error(f"Error generating HTML report: {e}")
    
    def monitor_logs_realtime(self, log_file_name='errors.log', tail_lines=50):
        """Monitor logs in real-time."""
        try:
            log_file = self.logs_dir / log_file_name
            
            if not log_file.exists():
                logger.error(f"Log file not found: {log_file}")
                return
            
            logger.info(f"Monitoring {log_file_name} in real-time...")
            logger.info("Press Ctrl+C to stop monitoring\n")
            
            # Show last N lines
            self.tail_log_file(log_file, tail_lines)
            
            # Monitor for new lines
            import time
            with open(log_file, 'r') as f:
                # Move to the end of file
                f.seek(0, 2)
                
                while True:
                    line = f.readline()
                    if line:
                        # Color code based on log level
                        if 'CRITICAL' in line:
                            print(f"\033[91m{line.strip()}\033[0m")  # Red
                        elif 'ERROR' in line:
                            print(f"\033[91m{line.strip()}\033[0m")  # Red
                        elif 'WARNING' in line:
                            print(f"\033[93m{line.strip()}\033[0m")  # Yellow
                        elif 'INFO' in line:
                            print(f"\033[92m{line.strip()}\033[0m")  # Green
                        else:
                            print(line.strip())
                    
                    time.sleep(0.1)
                    
        except KeyboardInterrupt:
            logger.info("\nMonitoring stopped by user")
        except Exception as e:
            logger.error(f"Error monitoring logs: {e}")
    
    def tail_log_file(self, log_file: Path, lines=50):
        """Show last N lines of a log file."""
        try:
            # For large files, use efficient tail implementation
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                # Read the file in chunks from the end
                f.seek(0, 2)
                file_size = f.tell()
                
                block_size = 1024
                lines_found = []
                current_block = 1
                
                while len(lines_found) < lines and file_size > 0:
                    if file_size - block_size > 0:
                        f.seek(file_size - block_size * current_block)
                        lines_found = f.readlines()
                    else:
                        f.seek(0)
                        lines_found = f.readlines()
                    
                    current_block += 1
                    file_size -= block_size
                
                # Print the last N lines
                for line in lines_found[-lines:]:
                    print(line.rstrip())
                    
        except Exception as e:
            logger.error(f"Error tailing log file: {e}")
    
    def search_logs(self, pattern: str, log_type=None, days=7, case_sensitive=False):
        """Search logs for specific patterns."""
        results = []
        log_files = self.get_log_files(log_type, days)
        
        flags = 0 if case_sensitive else re.IGNORECASE
        
        try:
            for log_file in log_files:
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    for line_num, line in enumerate(f, 1):
                        if re.search(pattern, line, flags):
                            results.append({
                                'file': log_file.name,
                                'line': line_num,
                                'content': line.strip(),
                                'timestamp': datetime.now().isoformat()
                            })
            
            # Save search results
            if results:
                self.save_search_results(pattern, results)
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching logs: {e}")
            return []
    
    def save_search_results(self, pattern: str, results: List[Dict]):
        """Save search results to file."""
        try:
            searches_dir = self.project_root / 'log_searches'
            searches_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_pattern = re.sub(r'[^\w\-]', '_', pattern)[:50]
            results_file = searches_dir / f'search_{safe_pattern}_{timestamp}.json'
            
            with open(results_file, 'w') as f:
                json.dump({
                    'pattern': pattern,
                    'timestamp': datetime.now().isoformat(),
                    'result_count': len(results),
                    'results': results[:100]  # Limit to 100 results
                }, f, indent=2, default=str)
            
            logger.info(f"Search results saved: {results_file}")
            
        except Exception as e:
            logger.error(f"Error saving search results: {e}")
    
    def get_log_statistics(self) -> Dict[str, Any]:
        """Get overall statistics about log files."""
        stats = {
            'total_files': 0,
            'total_size_mb': 0,
            'files_by_type': defaultdict(int),
            'size_by_type': defaultdict(float),
            'oldest_file': None,
            'newest_file': None,
            'compressed_files': 0,
            'compressed_size_mb': 0
        }
        
        try:
            for log_file in self.logs_dir.iterdir():
                if log_file.is_file():
                    stats['total_files'] += 1
                    file_size_mb = log_file.stat().st_size / (1024 * 1024)
                    stats['total_size_mb'] += file_size_mb
                    
                    # Determine file type
                    file_type = 'other'
                    for log_type, pattern in self.log_patterns.items():
                        if re.match(pattern, log_file.stem):
                            file_type = log_type
                            break
                    
                    stats['files_by_type'][file_type] += 1
                    stats['size_by_type'][file_type] += file_size_mb
                    
                    # Check if compressed
                    if log_file.suffix == '.gz':
                        stats['compressed_files'] += 1
                        stats['compressed_size_mb'] += file_size_mb
                    
                    # Track oldest and newest
                    file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                    if not stats['oldest_file'] or file_mtime < stats['oldest_file']['mtime']:
                        stats['oldest_file'] = {
                            'name': log_file.name,
                            'mtime': file_mtime,
                            'size_mb': file_size_mb
                        }
                    
                    if not stats['newest_file'] or file_mtime > stats['newest_file']['mtime']:
                        stats['newest_file'] = {
                            'name': log_file.name,
                            'mtime': file_mtime,
                            'size_mb': file_size_mb
                        }
        
        except Exception as e:
            logger.error(f"Error getting log statistics: {e}")
        
        return stats
    
    def run_maintenance(self):
        """Run complete log maintenance."""
        logger.info("Starting log maintenance...")
        
        results = {
            'rotated': self.rotate_logs(),
            'compressed': self.compress_old_logs(),
            'cleaned': self.cleanup_old_logs(),
            'statistics': self.get_log_statistics(),
            'timestamp': datetime.now().isoformat()
        }
        
        # Save maintenance report
        try:
            reports_dir = self.project_root / 'log_maintenance'
            reports_dir.mkdir(exist_ok=True)
            
            report_file = reports_dir / f'maintenance_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            
            with open(report_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            logger.info(f"Log maintenance completed. Report: {report_file}")
            
        except Exception as e:
            logger.error(f"Error saving maintenance report: {e}")
        
        return results

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='MEDIPREDICT Log Management')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Rotate logs command
    rotate_parser = subparsers.add_parser('rotate', help='Rotate log files')
    rotate_parser.add_argument('--force', action='store_true', help='Force rotation')
    
    # Analyze logs command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze logs')
    analyze_parser.add_argument('--type', help='Log type to analyze')
    analyze_parser.add_argument('--days', type=int, default=1, help='Number of days to analyze')
    
    # Monitor logs command
    monitor_parser = subparsers.add_parser('monitor', help='Monitor logs in real-time')
    monitor_parser.add_argument('--file', default='errors.log', help='Log file to monitor')
    monitor_parser.add_argument('--lines', type=int, default=50, help='Initial lines to show')
    
    # Search logs command
    search_parser = subparsers.add_parser('search', help='Search logs for pattern')
    search_parser.add_argument('pattern', help='Search pattern (regex)')
    search_parser.add_argument('--type', help='Log type to search')
    search_parser.add_argument('--days', type=int, default=7, help='Days to search')
    search_parser.add_argument('--case-sensitive', action='store_true', help='Case sensitive search')
    
    # Maintenance command
    subparsers.add_parser('maintenance', help='Run complete log maintenance')
    
    # Statistics command
    subparsers.add_parser('stats', help='Show log statistics')
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', help='Cleanup old logs')
    cleanup_parser.add_argument('--days', type=int, default=30, help='Retention days')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    log_manager = LogManager()
    
    if args.command == 'rotate':
        rotated = log_manager.rotate_logs(force=args.force)
        print(f"Rotated {len(rotated)} log files")
        
    elif args.command == 'analyze':
        results = log_manager.analyze_logs(log_type=args.type, days=args.days)
        insights = results.get('insights', {})
        
        print(f"\n📊 Log Analysis Results")
        print(f"Health Status: {insights.get('health_status', 'UNKNOWN')}")
        print(f"Error Rate: {insights.get('metrics', {}).get('error_rate', 'N/A')}")
        print(f"Total Lines: {insights.get('metrics', {}).get('total_lines', 0)}")
        
        if insights.get('issues_found'):
            print(f"\n⚠️ Issues Found:")
            for issue in insights['issues_found']:
                print(f"  - {issue}")
        
    elif args.command == 'monitor':
        log_manager.monitor_logs_realtime(log_file_name=args.file, tail_lines=args.lines)
        
    elif args.command == 'search':
        results = log_manager.search_logs(
            args.pattern,
            log_type=args.type,
            days=args.days,
            case_sensitive=args.case_sensitive
        )
        print(f"Found {len(results)} matches")
        for i, result in enumerate(results[:10], 1):
            print(f"{i}. {result['file']}:{result['line']} - {result['content'][:100]}...")
        
    elif args.command == 'maintenance':
        results = log_manager.run_maintenance()
        print(f"Maintenance completed:")
        print(f"  Rotated: {len(results['rotated'])} files")
        print(f"  Compressed: {len(results['compressed'])} files")
        print(f"  Cleaned: {len(results['cleaned'])} files")
        print(f"  Total size: {results['statistics']['total_size_mb']:.2f} MB")
        
    elif args.command == 'stats':
        stats = log_manager.get_log_statistics()
        print(f"\n📈 Log Statistics")
        print(f"Total Files: {stats['total_files']}")
        print(f"Total Size: {stats['total_size_mb']:.2f} MB")
        print(f"Compressed Files: {stats['compressed_files']}")
        print(f"Compressed Size: {stats['compressed_size_mb']:.2f} MB")
        
        print(f"\nFiles by Type:")
        for file_type, count in stats['files_by_type'].items():
            size_mb = stats['size_by_type'][file_type]
            print(f"  {file_type}: {count} files ({size_mb:.2f} MB)")
        
        if stats['oldest_file']:
            print(f"\nOldest File: {stats['oldest_file']['name']}")
            print(f"  Modified: {stats['oldest_file']['mtime']}")
            print(f"  Size: {stats['oldest_file']['size_mb']:.2f} MB")
        
    elif args.command == 'cleanup':
        log_manager.retention_days = args.days
        cleaned = log_manager.cleanup_old_logs()
        print(f"Cleaned {len(cleaned)} old log files")

if __name__ == '__main__':
    main()