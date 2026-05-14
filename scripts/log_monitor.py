#!/usr/bin/env python3
"""
Real-time log monitoring for MediPredict with web dashboard
"""

import os
import sys
import argparse
from pathlib import Path
import time
import re
import threading
from datetime import datetime
from collections import deque
import json
import logging
from http.server import HTTPServer, SimpleHTTPRequestHandler
import socketserver

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

# Setup logging for this script
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/log_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class LogMonitor:
    def __init__(self, logs_dir='logs', buffer_size=1000):
        self.logs_dir = Path(logs_dir)
        self.buffer_size = buffer_size
        self.log_buffer = deque(maxlen=buffer_size)
        self.running = False
        self.monitor_thread = None
        
        # Color codes for terminal
        self.COLORS = {
            'RESET': '\033[0m',
            'ERROR': '\033[91m',
            'WARNING': '\033[93m',
            'INFO': '\033[92m',
            'DEBUG': '\033[94m',
            'TIMESTAMP': '\033[36m',
            'HIGHLIGHT': '\033[1m'
        }
    
    def colorize_line(self, line):
        """Add colors to log line based on content"""
        colored_line = line
        
        # Color by log level
        for level, color in self.COLORS.items():
            if level in ['ERROR', 'WARNING', 'INFO', 'DEBUG']:
                if level in line:
                    colored_line = colored_line.replace(
                        level, f"{color}{level}{self.COLORS['RESET']}"
                    )
        
        # Color timestamps
        timestamp_pattern = r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]'
        colored_line = re.sub(
            timestamp_pattern,
            f"{self.COLORS['TIMESTAMP']}[\\1]{self.COLORS['RESET']}",
            colored_line
        )
        
        # Highlight IP addresses
        ip_pattern = r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'
        colored_line = re.sub(
            ip_pattern,
            f"{self.COLORS['HIGHLIGHT']}\\g<0>{self.COLORS['RESET']}",
            colored_line
        )
        
        return colored_line
    
    def tail_file(self, log_file, follow=True, filter_pattern=None, 
                  highlight_patterns=None, lines=50):
        """Tail a log file with filtering and highlighting"""
        file_path = self.logs_dir / log_file
        
        if not file_path.exists():
            logger.error(f"Log file not found: {log_file}")
            return
        
        logger.info(f"Monitoring: {log_file}")
        logger.info("Press Ctrl+C to stop")
        print("-" * 80)
        
        # Read last N lines initially
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                all_lines = f.readlines()
                last_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
                
                for line in last_lines:
                    self._process_and_print(line, filter_pattern, highlight_patterns)
                
                if follow:
                    self._follow_file(file_path, filter_pattern, highlight_patterns)
                    
        except KeyboardInterrupt:
            logger.info("\nMonitoring stopped by user")
        except Exception as e:
            logger.error(f"Error monitoring {log_file}: {e}")
    
    def _follow_file(self, file_path, filter_pattern, highlight_patterns):
        """Follow a file like tail -f"""
        last_position = file_path.stat().st_size
        
        while True:
            try:
                current_size = file_path.stat().st_size
                
                if current_size > last_position:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        f.seek(last_position)
                        new_content = f.read(current_size - last_position)
                        
                        for line in new_content.split('\n'):
                            if line.strip():
                                self._process_and_print(line, filter_pattern, highlight_patterns)
                                # Add to buffer
                                self.log_buffer.append({
                                    'timestamp': datetime.now().isoformat(),
                                    'file': file_path.name,
                                    'line': line
                                })
                        
                        last_position = current_size
                
                time.sleep(0.1)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error reading file: {e}")
                time.sleep(1)
    
    def _process_and_print(self, line, filter_pattern, highlight_patterns):
        """Process and print a single log line"""
        # Apply filter
        if filter_pattern and not re.search(filter_pattern, line, re.IGNORECASE):
            return
        
        # Apply highlighting
        highlighted_line = self.colorize_line(line)
        
        if highlight_patterns:
            for pattern in highlight_patterns:
                if pattern in line:
                    highlighted_line = highlighted_line.replace(
                        pattern, f"\033[7m{pattern}\033[0m"
                    )
        
        # Print the line
        print(highlighted_line)
    
    def monitor_multiple(self, log_files, filter_pattern=None):
        """Monitor multiple log files simultaneously"""
        logger.info(f"Monitoring multiple files: {', '.join(log_files)}")
        
        threads = []
        self.running = True
        
        def monitor_file(file_name):
            file_path = self.logs_dir / file_name
            last_position = file_path.stat().st_size
            
            while self.running:
                try:
                    if not file_path.exists():
                        time.sleep(1)
                        continue
                    
                    current_size = file_path.stat().st_size
                    
                    if current_size > last_position:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            f.seek(last_position)
                            new_content = f.read(current_size - last_position)
                            
                            for line in new_content.split('\n'):
                                if line.strip() and (not filter_pattern or 
                                                   re.search(filter_pattern, line, re.IGNORECASE)):
                                    timestamp = datetime.now().strftime('%H:%M:%S')
                                    colored_line = self.colorize_line(line)
                                    print(f"[{file_name}] {timestamp}: {colored_line}")
                                    
                                    # Add to buffer
                                    self.log_buffer.append({
                                        'timestamp': datetime.now().isoformat(),
                                        'file': file_name,
                                        'line': line
                                    })
                        
                        last_position = current_size
                    
                    time.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Error monitoring {file_name}: {e}")
                    time.sleep(1)
        
        # Start monitoring threads
        for log_file in log_files:
            thread = threading.Thread(target=monitor_file, args=(log_file,))
            thread.daemon = True
            thread.start()
            threads.append(thread)
        
        logger.info("Monitoring started. Press Ctrl+C to stop.")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("\nStopping monitoring...")
            self.running = False
            
            for thread in threads:
                thread.join(timeout=2)
            
            logger.info("Monitoring stopped")
    
    def get_buffer_contents(self, limit=100):
        """Get contents of log buffer"""
        return list(self.log_buffer)[-limit:]
    
    def search_logs(self, pattern, log_files=None, hours=24):
        """Search logs for pattern"""
        logger.info(f"Searching for pattern: {pattern}")
        
        if log_files is None:
            log_files = [f.name for f in self.logs_dir.glob('*.log')]
        
        results = []
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        for log_file in log_files:
            file_path = self.logs_dir / log_file
            
            if not file_path.exists():
                continue
            
            logger.info(f"Searching in: {log_file}")
            
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line_num, line in enumerate(f, 1):
                        # Check timestamp if available
                        timestamp_match = re.search(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]', line)
                        if timestamp_match:
                            try:
                                log_time = datetime.strptime(timestamp_match.group(1), '%Y-%m-%d %H:%M:%S')
                                if log_time < cutoff_time:
                                    continue
                            except:
                                pass
                        
                        if re.search(pattern, line, re.IGNORECASE):
                            results.append({
                                'file': log_file,
                                'line_num': line_num,
                                'line': line.strip(),
                                'timestamp': timestamp_match.group(1) if timestamp_match else None
                            })
                            
            except Exception as e:
                logger.error(f"Error searching {log_file}: {e}")
        
        # Print results
        if results:
            logger.info(f"Found {len(results)} matches:")
            for result in results[:20]:  # Show first 20 matches
                colored_line = self.colorize_line(result['line'])
                print(f"\n[{result['file']}:{result['line_num']}] {colored_line}")
            
            if len(results) > 20:
                logger.info(f"... and {len(results) - 20} more matches")
        else:
            logger.info("No matches found")
        
        return results
    
    def analyze_trends(self, hours=24):
        """Analyze log trends over time"""
        logger.info(f"Analyzing log trends for last {hours} hours...")
        
        trends = {
            'error_rate': [],
            'warning_rate': [],
            'activity_by_hour': defaultdict(int),
            'top_errors': Counter(),
            'top_warnings': Counter()
        }
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        for log_file in self.logs_dir.glob('*.log'):
            if not log_file.exists() or log_file.stat().st_size == 0:
                continue
            
            try:
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        # Extract timestamp
                        timestamp_match = re.search(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]', line)
                        if not timestamp_match:
                            continue
                        
                        try:
                            log_time = datetime.strptime(timestamp_match.group(1), '%Y-%m-%d %H:%M:%S')
                            if log_time < cutoff_time:
                                continue
                            
                            hour_key = log_time.strftime('%Y-%m-%d %H:00')
                            trends['activity_by_hour'][hour_key] += 1
                            
                            # Count errors and warnings
                            if 'ERROR' in line:
                                error_match = re.search(r'ERROR.*?:\s*(.*)', line)
                                if error_match:
                                    error_msg = error_match.group(1)[:100]
                                    trends['top_errors'][error_msg] += 1
                            
                            elif 'WARNING' in line:
                                warning_match = re.search(r'WARNING.*?:\s*(.*)', line)
                                if warning_match:
                                    warning_msg = warning_match.group(1)[:100]
                                    trends['top_warnings'][warning_msg] += 1
                                    
                        except:
                            continue
                            
            except Exception as e:
                logger.error(f"Error analyzing {log_file}: {e}")
        
        # Print trends
        print("\n" + "="*60)
        print("LOG TRENDS ANALYSIS")
        print("="*60)
        
        total_activity = sum(trends['activity_by_hour'].values())
        print(f"\nTotal log entries (last {hours}h): {total_activity:,}")
        
        if trends['activity_by_hour']:
            print("\nActivity by hour:")
            for hour, count in sorted(trends['activity_by_hour'].items(), reverse=True)[:12]:
                print(f"  {hour}: {count:,}")
        
        if trends['top_errors']:
            print("\nTop 5 Errors:")
            for error, count in trends['top_errors'].most_common(5):
                print(f"  {count}x: {error[:80]}...")
        
        if trends['top_warnings']:
            print("\nTop 5 Warnings:")
            for warning, count in trends['top_warnings'].most_common(5):
                print(f"  {count}x: {warning[:80]}...")
        
        print("="*60)
        
        return trends

class LogDashboard:
    """Web-based log dashboard"""
    
    def __init__(self, port=8080, logs_dir='logs'):
        self.port = port
        self.logs_dir = Path(logs_dir)
        self.monitor = LogMonitor(logs_dir)
    
    def create_dashboard_html(self):
        """Create dashboard HTML file"""
        html_content = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>MediPredict Log Dashboard</title>
            <style>
                body {
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                }
                
                .container {
                    max-width: 1400px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 10px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                    overflow: hidden;
                }
                
                .header {
                    background: linear-gradient(135deg, #4361ee 0%, #3a0ca3 100%);
                    color: white;
                    padding: 20px 30px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }
                
                .header h1 {
                    margin: 0;
                    font-size: 24px;
                }
                
                .status {
                    display: flex;
                    gap: 20px;
                    align-items: center;
                }
                
                .status-badge {
                    background: rgba(255,255,255,0.2);
                    padding: 5px 15px;
                    border-radius: 20px;
                    font-size: 14px;
                }
                
                .content {
                    display: grid;
                    grid-template-columns: 300px 1fr;
                    min-height: 800px;
                }
                
                .sidebar {
                    background: #f8f9fa;
                    border-right: 1px solid #dee2e6;
                    padding: 20px;
                }
                
                .main-content {
                    padding: 20px;
                }
                
                .log-file-list {
                    list-style: none;
                    padding: 0;
                    margin: 0;
                }
                
                .log-file-item {
                    padding: 10px 15px;
                    margin: 5px 0;
                    background: white;
                    border: 1px solid #dee2e6;
                    border-radius: 5px;
                    cursor: pointer;
                    transition: all 0.2s;
                }
                
                .log-file-item:hover {
                    background: #e9ecef;
                    transform: translateX(5px);
                }
                
                .log-file-item.active {
                    background: #4361ee;
                    color: white;
                    border-color: #4361ee;
                }
                
                .controls {
                    margin: 20px 0;
                    padding: 20px;
                    background: white;
                    border-radius: 5px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                }
                
                .control-group {
                    margin-bottom: 15px;
                }
                
                .control-group label {
                    display: block;
                    margin-bottom: 5px;
                    font-weight: bold;
                    color: #495057;
                }
                
                .control-group input, .control-group select {
                    width: 100%;
                    padding: 8px 12px;
                    border: 1px solid #ced4da;
                    border-radius: 4px;
                    font-size: 14px;
                }
                
                .control-group input:focus, .control-group select:focus {
                    outline: none;
                    border-color: #4361ee;
                    box-shadow: 0 0 0 3px rgba(67, 97, 238, 0.1);
                }
                
                .btn {
                    background: #4361ee;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 4px;
                    cursor: pointer;
                    font-size: 14px;
                    transition: background 0.2s;
                }
                
                .btn:hover {
                    background: #3a56d4;
                }
                
                .btn-secondary {
                    background: #6c757d;
                }
                
                .btn-secondary:hover {
                    background: #5a6268;
                }
                
                .log-viewer {
                    background: #1a1a1a;
                    color: #f8f9fa;
                    font-family: 'Courier New', monospace;
                    padding: 15px;
                    border-radius: 5px;
                    height: 600px;
                    overflow-y: auto;
                    font-size: 13px;
                    line-height: 1.4;
                }
                
                .log-line {
                    margin: 2px 0;
                    padding: 2px 5px;
                    border-radius: 2px;
                    word-wrap: break-word;
                }
                
                .log-line.error { color: #ff6b6b; }
                .log-line.warning { color: #ffd166; }
                .log-line.info { color: #06d6a0; }
                .log-line.debug { color: #118ab2; }
                
                .stats {
                    display: grid;
                    grid-template-columns: repeat(4, 1fr);
                    gap: 15px;
                    margin: 20px 0;
                }
                
                .stat-card {
                    background: white;
                    padding: 15px;
                    border-radius: 5px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                    text-align: center;
                }
                
                .stat-value {
                    font-size: 24px;
                    font-weight: bold;
                    color: #4361ee;
                }
                
                .stat-label {
                    font-size: 12px;
                    color: #6c757d;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                }
                
                .footer {
                    text-align: center;
                    padding: 20px;
                    color: #6c757d;
                    font-size: 12px;
                    border-top: 1px solid #dee2e6;
                }
                
                @media (max-width: 1024px) {
                    .content {
                        grid-template-columns: 1fr;
                    }
                    .sidebar {
                        display: none;
                    }
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📊 MediPredict Log Dashboard</h1>
                    <div class="status">
                        <span class="status-badge" id="status">🟢 Connected</span>
                        <span class="status-badge" id="lastUpdate">Last update: Just now</span>
                    </div>
                </div>
                
                <div class="content">
                    <div class="sidebar">
                        <h3>Log Files</h3>
                        <ul class="log-file-list" id="logFileList">
                            <!-- Dynamically populated -->
                        </ul>
                        
                        <div class="controls">
                            <h3>Controls</h3>
                            
                            <div class="control-group">
                                <label for="refreshInterval">Refresh Interval (seconds)</label>
                                <select id="refreshInterval">
                                    <option value="1">1 second</option>
                                    <option value="5" selected>5 seconds</option>
                                    <option value="10">10 seconds</option>
                                    <option value="30">30 seconds</option>
                                    <option value="60">60 seconds</option>
                                </select>
                            </div>
                            
                            <div class="control-group">
                                <label for="filterLevel">Filter by Level</label>
                                <select id="filterLevel">
                                    <option value="all">All Levels</option>
                                    <option value="error">Errors Only</option>
                                    <option value="warning">Warnings Only</option>
                                    <option value="info">Info Only</option>
                                </select>
                            </div>
                            
                            <div class="control-group">
                                <label for="searchPattern">Search Pattern</label>
                                <input type="text" id="searchPattern" placeholder="Enter regex pattern...">
                            </div>
                            
                            <button class="btn" onclick="applyFilters()">Apply Filters</button>
                            <button class="btn btn-secondary" onclick="clearLogs()">Clear Viewer</button>
                            <button class="btn" onclick="exportLogs()">Export Logs</button>
                        </div>
                    </div>
                    
                    <div class="main-content">
                        <div class="stats">
                            <div class="stat-card">
                                <div class="stat-value" id="totalErrors">0</div>
                                <div class="stat-label">Errors (24h)</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-value" id="totalWarnings">0</div>
                                <div class="stat-label">Warnings (24h)</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-value" id="logSize">0 MB</div>
                                <div class="stat-label">Total Size</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-value" id="activeFiles">0</div>
                                <div class="stat-label">Active Files</div>
                            </div>
                        </div>
                        
                        <h3>Live Log Viewer</h3>
                        <div class="log-viewer" id="logViewer">
                            <!-- Logs will appear here -->
                        </div>
                        
                        <div style="margin-top: 20px;">
                            <button class="btn" onclick="startAutoRefresh()">▶ Start Auto-refresh</button>
                            <button class="btn btn-secondary" onclick="stopAutoRefresh()">⏸ Stop Auto-refresh</button>
                            <span style="margin-left: 20px; color: #6c757d; font-size: 12px;">
                                Showing last <span id="lineCount">0</span> lines
                            </span>
                        </div>
                    </div>
                </div>
                
                <div class="footer">
                    <p>MediPredict Log Dashboard • Real-time monitoring • Version 1.0.0</p>
                    <p>Last refresh: <span id="refreshTime">-</span></p>
                </div>
            </div>
            
            <script>
                let currentLogFile = 'django.log';
                let autoRefreshInterval = null;
                let refreshInterval = 5000; // 5 seconds
                let filters = {
                    level: 'all',
                    pattern: ''
                };
                
                // DOM Elements
                const logViewer = document.getElementById('logViewer');
                const statusElement = document.getElementById('status');
                const lastUpdateElement = document.getElementById('lastUpdate');
                const refreshTimeElement = document.getElementById('refreshTime');
                const lineCountElement = document.getElementById('lineCount');
                
                // Statistics elements
                const totalErrorsElement = document.getElementById('totalErrors');
                const totalWarningsElement = document.getElementById('totalWarnings');
                const logSizeElement = document.getElementById('logSize');
                const activeFilesElement = document.getElementById('activeFiles');
                
                // Initialize
                document.addEventListener('DOMContentLoaded', function() {
                    loadLogFiles();
                    loadLogs();
                    updateStats();
                    startAutoRefresh();
                    
                    // Set up event listeners
                    document.getElementById('refreshInterval').addEventListener('change', function() {
                        refreshInterval = parseInt(this.value) * 1000;
                        if (autoRefreshInterval) {
                            stopAutoRefresh();
                            startAutoRefresh();
                        }
                    });
                });
                
                function loadLogFiles() {
                    fetch('/api/logs/files')
                        .then(response => response.json())
                        .then(files => {
                            const fileList = document.getElementById('logFileList');
                            fileList.innerHTML = '';
                            
                            files.forEach(file => {
                                const li = document.createElement('li');
                                li.className = 'log-file-item';
                                if (file.name === currentLogFile) {
                                    li.classList.add('active');
                                }
                                li.innerHTML = `
                                    <strong>${file.name}</strong>
                                    <div style="font-size: 11px; color: #6c757d;">
                                        ${file.size_mb.toFixed(2)} MB • Modified: ${file.modified}
                                    </div>
                                `;
                                li.onclick = () => selectLogFile(file.name);
                                fileList.appendChild(li);
                            });
                        });
                }
                
                function selectLogFile(fileName) {
                    currentLogFile = fileName;
                    loadLogFiles();
                    loadLogs();
                }
                
                function loadLogs() {
                    fetch(`/api/logs/view?file=${currentLogFile}&limit=100`)
                        .then(response => response.json())
                        .then(data => {
                            updateLogViewer(data.lines);
                            updateLastUpdate();
                        })
                        .catch(error => {
                            console.error('Error loading logs:', error);
                            statusElement.textContent = '🔴 Connection Error';
                            statusElement.style.color = '#ff6b6b';
                        });
                }
                
                function updateLogViewer(logLines) {
                    logViewer.innerHTML = '';
                    let lineCount = 0;
                    
                    logLines.forEach(line => {
                        if (applyLineFilter(line)) {
                            const lineElement = document.createElement('div');
                            lineElement.className = 'log-line';
                            
                            // Determine log level for styling
                            if (line.includes('ERROR')) {
                                lineElement.classList.add('error');
                            } else if (line.includes('WARNING')) {
                                lineElement.classList.add('warning');
                            } else if (line.includes('INFO')) {
                                lineElement.classList.add('info');
                            } else if (line.includes('DEBUG')) {
                                lineElement.classList.add('debug');
                            }
                            
                            // Highlight search pattern if any
                            let displayLine = line;
                            if (filters.pattern) {
                                try {
                                    const regex = new RegExp(`(${filters.pattern})`, 'gi');
                                    displayLine = line.replace(regex, '<mark>$1</mark>');
                                } catch (e) {
                                    console.error('Invalid regex pattern:', e);
                                }
                            }
                            
                            lineElement.innerHTML = displayLine;
                            logViewer.appendChild(lineElement);
                            lineCount++;
                        }
                    });
                    
                    lineCountElement.textContent = lineCount;
                    
                    // Scroll to bottom
                    logViewer.scrollTop = logViewer.scrollHeight;
                }
                
                function applyLineFilter(line) {
                    // Apply level filter
                    if (filters.level !== 'all') {
                        if (filters.level === 'error' && !line.includes('ERROR')) return false;
                        if (filters.level === 'warning' && !line.includes('WARNING')) return false;
                        if (filters.level === 'info' && !line.includes('INFO')) return false;
                    }
                    
                    // Apply pattern filter
                    if (filters.pattern) {
                        try {
                            const regex = new RegExp(filters.pattern, 'i');
                            if (!regex.test(line)) return false;
                        } catch (e) {
                            return true; // If pattern is invalid, show all lines
                        }
                    }
                    
                    return true;
                }
                
                function applyFilters() {
                    filters.level = document.getElementById('filterLevel').value;
                    filters.pattern = document.getElementById('searchPattern').value;
                    loadLogs();
                }
                
                function clearLogs() {
                    logViewer.innerHTML = '<div class="log-line">Log viewer cleared</div>';
                    lineCountElement.textContent = '0';
                }
                
                function exportLogs() {
                    fetch(`/api/logs/export?file=${currentLogFile}`)
                        .then(response => response.blob())
                        .then(blob => {
                            const url = window.URL.createObjectURL(blob);
                            const a = document.createElement('a');
                            a.href = url;
                            a.download = `${currentLogFile}_${new Date().toISOString().slice(0,10)}.log`;
                            document.body.appendChild(a);
                            a.click();
                            document.body.removeChild(a);
                            window.URL.revokeObjectURL(url);
                        });
                }
                
                function updateStats() {
                    fetch('/api/logs/stats')
                        .then(response => response.json())
                        .then(stats => {
                            totalErrorsElement.textContent = stats.errors_24h;
                            totalWarningsElement.textContent = stats.warnings_24h;
                            logSizeElement.textContent = stats.total_size_mb.toFixed(2) + ' MB';
                            activeFilesElement.textContent = stats.active_files;
                        });
                }
                
                function updateLastUpdate() {
                    const now = new Date();
                    lastUpdateElement.textContent = `Last update: ${now.toLocaleTimeString()}`;
                    refreshTimeElement.textContent = now.toLocaleTimeString();
                    statusElement.textContent = '🟢 Connected';
                    statusElement.style.color = '#06d6a0';
                }
                
                function startAutoRefresh() {
                    if (autoRefreshInterval) {
                        clearInterval(autoRefreshInterval);
                    }
                    autoRefreshInterval = setInterval(() => {
                        loadLogs();
                        updateStats();
                    }, refreshInterval);
                    
                    statusElement.textContent = '🟢 Auto-refresh ON';
                }
                
                function stopAutoRefresh() {
                    if (autoRefreshInterval) {
                        clearInterval(autoRefreshInterval);
                        autoRefreshInterval = null;
                        statusElement.textContent = '🟡 Auto-refresh OFF';
                    }
                }
            </script>
        </body>
        </html>
        """
        
        # Write HTML file
        dashboard_file = self.logs_dir / 'dashboard.html'
        dashboard_file.write_text(html_content)
        
        logger.info(f"Dashboard HTML created: {dashboard_file}")
    
    def start_webserver(self):
        """Start the web server with API endpoints"""
        self.create_dashboard_html()
        
        class LogRequestHandler(SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                self.dashboard = self.server.dashboard
                super().__init__(*args, **kwargs)
            
            def do_GET(self):
                # API endpoints
                if self.path.startswith('/api/logs/'):
                    self.handle_api_request()
                else:
                    # Serve static files
                    if self.path == '/':
                        self.path = '/logs/dashboard.html'
                    return SimpleHTTPRequestHandler.do_GET(self)
            
            def handle_api_request(self):
                """Handle API requests"""
                try:
                    if self.path == '/api/logs/files':
                        self.send_log_files()
                    elif self.path.startswith('/api/logs/view'):
                        self.send_log_contents()
                    elif self.path == '/api/logs/stats':
                        self.send_log_stats()
                    elif self.path.startswith('/api/logs/export'):
                        self.export_log_file()
                    else:
                        self.send_error(404, "API endpoint not found")
                except Exception as e:
                    logger.error(f"API error: {e}")
                    self.send_error(500, str(e))
            
            def send_log_files(self):
                """Send list of log files"""
                log_files = []
                for log_file in self.dashboard.logs_dir.glob('*.log'):
                    if log_file.is_file():
                        log_files.append({
                            'name': log_file.name,
                            'size_mb': log_file.stat().st_size / (1024 * 1024),
                            'modified': datetime.fromtimestamp(
                                log_file.stat().st_mtime
                            ).strftime('%Y-%m-%d %H:%M')
                        })
                
                self.send_json_response(log_files)
            
            def send_log_contents(self):
                """Send log file contents"""
                import urllib.parse
                
                # Parse query parameters
                query = urllib.parse.urlparse(self.path).query
                params = urllib.parse.parse_qs(query)
                
                file_name = params.get('file', ['django.log'])[0]
                limit = int(params.get('limit', [100])[0])
                
                file_path = self.dashboard.logs_dir / file_name
                
                if not file_path.exists():
                    self.send_error(404, f"Log file not found: {file_name}")
                    return
                
                # Read last N lines
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                        last_lines = lines[-limit:] if len(lines) > limit else lines
                    
                    self.send_json_response({'lines': [line.rstrip() for line in last_lines]})
                    
                except Exception as e:
                    self.send_error(500, f"Error reading log file: {e}")
            
            def send_log_stats(self):
                """Send log statistics"""
                import psutil
                
                stats = {
                    'errors_24h': 0,
                    'warnings_24h': 0,
                    'total_size_mb': 0,
                    'active_files': 0
                }
                
                cutoff_time = datetime.now() - timedelta(hours=24)
                
                for log_file in self.dashboard.logs_dir.glob('*.log'):
                    if log_file.is_file():
                        stats['total_size_mb'] += log_file.stat().st_size / (1024 * 1024)
                        stats['active_files'] += 1
                        
                        # Count errors and warnings in last 24 hours
                        try:
                            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                                for line in f:
                                    timestamp_match = re.search(
                                        r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]', line
                                    )
                                    if timestamp_match:
                                        try:
                                            log_time = datetime.strptime(
                                                timestamp_match.group(1), '%Y-%m-%d %H:%M:%S'
                                            )
                                            if log_time > cutoff_time:
                                                if 'ERROR' in line:
                                                    stats['errors_24h'] += 1
                                                elif 'WARNING' in line:
                                                    stats['warnings_24h'] += 1
                                        except:
                                            continue
                        except:
                            pass
                
                self.send_json_response(stats)
            
            def export_log_file(self):
                """Export log file for download"""
                import urllib.parse
                
                query = urllib.parse.urlparse(self.path).query
                params = urllib.parse.parse_qs(query)
                
                file_name = params.get('file', ['django.log'])[0]
                file_path = self.dashboard.logs_dir / file_name
                
                if not file_path.exists():
                    self.send_error(404, f"Log file not found: {file_name}")
                    return
                
                try:
                    with open(file_path, 'rb') as f:
                        content = f.read()
                    
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/plain')
                    self.send_header('Content-Disposition', 
                                   f'attachment; filename="{file_name}"')
                    self.send_header('Content-Length', str(len(content)))
                    self.end_headers()
                    self.wfile.write(content)
                    
                except Exception as e:
                    self.send_error(500, f"Error exporting log file: {e}")
            
            def send_json_response(self, data):
                """Send JSON response"""
                import json
                
                response = json.dumps(data, default=str).encode('utf-8')
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(response)))
                self.end_headers()
                self.wfile.write(response)
            
            def log_message(self, format, *args):
                """Override to reduce log noise"""
                pass
        
        class LogHTTPServer(HTTPServer):
            def __init__(self, *args, **kwargs):
                self.dashboard = kwargs.pop('dashboard')
                super().__init__(*args, **kwargs)
        
        # Change to project root directory
        os.chdir(Path(__file__).parent.parent)
        
        # Start server
        with LogHTTPServer(("", self.port), LogRequestHandler, dashboard=self) as httpd:
            logger.info(f"Log dashboard available at http://localhost:{self.port}")
            logger.info("Press Ctrl+C to stop the server")
            
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                logger.info("\nServer stopped by user")
            except Exception as e:
                logger.error(f"Server error: {e}")

def main():
    parser = argparse.ArgumentParser(description='MediPredict Log Monitor')
    parser.add_argument('--tail', metavar='LOG_FILE',
                       help='Tail a specific log file')
    parser.add_argument('--multi', nargs='+',
                       help='Monitor multiple log files')
    parser.add_argument('--search', metavar='PATTERN',
                       help='Search logs for pattern')
    parser.add_argument('--dashboard', action='store_true',
                       help='Start web dashboard')
    parser.add_argument('--port', type=int, default=8080,
                       help='Port for web dashboard (default: 8080)')
    parser.add_argument('--filter', metavar='PATTERN',
                       help='Filter pattern for monitoring')
    parser.add_argument('--highlight', nargs='+',
                       help='Patterns to highlight')
    parser.add_argument('--lines', type=int, default=50,
                       help='Number of lines to show initially (default: 50)')
    parser.add_argument('--trends', action='store_true',
                       help='Analyze log trends')
    parser.add_argument('--hours', type=int, default=24,
                       help='Hours to analyze for trends (default: 24)')
    
    args = parser.parse_args()
    
    monitor = LogMonitor()
    
    if args.dashboard:
        dashboard = LogDashboard(port=args.port)
        dashboard.start_webserver()
    elif args.tail:
        monitor.tail_file(
            args.tail,
            filter_pattern=args.filter,
            highlight_patterns=args.highlight,
            lines=args.lines
        )
    elif args.multi:
        monitor.monitor_multiple(args.multi, args.filter)
    elif args.search:
        monitor.search_logs(args.search, hours=args.hours)
    elif args.trends:
        monitor.analyze_trends(hours=args.hours)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()