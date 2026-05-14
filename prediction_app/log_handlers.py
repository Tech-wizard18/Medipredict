"""
Custom log handlers for MEDIPREDICT
"""

import logging
import logging.handlers
import json
from datetime import datetime
from typing import Dict, Any
import requests
from django.conf import settings


class SlackLogHandler(logging.Handler):
    """Send log messages to Slack."""
    
    def __init__(self, webhook_url, level=logging.ERROR, username='MEDIPREDICT Bot'):
        super().__init__(level)
        self.webhook_url = webhook_url
        self.username = username
        
    def emit(self, record):
        """Send log record to Slack."""
        try:
            # Format message
            message = self.format(record)
            
            # Create Slack payload
            payload = {
                'text': f"*{record.levelname}* in MEDIPREDICT",
                'username': self.username,
                'attachments': [{
                    'color': self.get_color(record.levelno),
                    'text': message,
                    'fields': [
                        {
                            'title': 'Module',
                            'value': record.module,
                            'short': True
                        },
                        {
                            'title': 'Function',
                            'value': record.funcName,
                            'short': True
                        },
                        {
                            'title': 'Timestamp',
                            'value': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'short': False
                        }
                    ]
                }]
            }
            
            # Send to Slack
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=5
            )
            
            if response.status_code != 200:
                self.handleError(record)
                
        except Exception:
            self.handleError(record)
    
    def get_color(self, levelno):
        """Get Slack attachment color based on log level."""
        if levelno >= logging.ERROR:
            return '#FF0000'  # Red
        elif levelno >= logging.WARNING:
            return '#FFA500'  # Orange
        elif levelno >= logging.INFO:
            return '#00FF00'  # Green
        else:
            return '#808080'  # Gray


class DatabaseLogHandler(logging.Handler):
    """Store log messages in database."""
    
    def __init__(self, level=logging.ERROR):
        super().__init__(level)
    
    def emit(self, record):
        """Store log record in database."""
        try:
            from prediction_app.models import SystemLog  # Assuming you have this model
            
            log_entry = SystemLog(
                level=record.levelname,
                message=self.format(record),
                module=record.module,
                func_name=record.funcName,
                line_no=record.lineno,
                exception=record.exc_text if record.exc_info else None,
                timestamp=datetime.fromtimestamp(record.created)
            )
            log_entry.save()
            
        except Exception:
            self.handleError(record)


class JSONFileHandler(logging.handlers.RotatingFileHandler):
    """Log handler that writes JSON formatted log entries."""
    
    def __init__(self, filename, **kwargs):
        super().__init__(filename, **kwargs)
    
    def format(self, record):
        """Format log record as JSON."""
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'message': record.getMessage(),
            'module': record.module,
            'funcName': record.funcName,
            'lineNo': record.lineno,
            'process': record.process,
            'thread': record.thread,
            'threadName': record.threadName,
        }
        
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)
        
        return json.dumps(log_entry)