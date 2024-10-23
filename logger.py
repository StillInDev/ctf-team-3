import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logging(app):
    """Configure application logging."""
    
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')

    # Configure application logger
    app.logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - IP: %(ip)s - %(message)s')

    # File handler for all requests
    file_handler = RotatingFileHandler('logs/app.log', maxBytes=1024 * 1024, backupCount=10)
    file_handler.setFormatter(formatter)
    app.logger.addHandler(file_handler)

    # Separate security events logger
    security_logger = logging.getLogger('security')
    security_logger.setLevel(logging.WARNING)
    security_handler = RotatingFileHandler('logs/security.log', maxBytes=1024 * 1024, backupCount=10)
    security_handler.setFormatter(formatter)
    security_logger.addHandler(security_handler)

def log_request_and_response(request, response, app):
    """Log both request and response."""
    ip = request.remote_addr
    extra = {'ip': ip}

    # Log request
    app.logger.info(f"REQUEST - Endpoint: {request.path} - Method: {request.method} - Args: {dict(request.args)}", extra=extra)

    # Log response
    app.logger.info(f"RESPONSE - Status: {response.status_code} - Data: {response.get_data(as_text=True)}", extra=extra)

    return response

def log_security_event(app, ip, message, level='warning'):
    """Log security-related events."""
    extra = {'ip': ip}
    security_logger = logging.getLogger('security')

    if level == 'warning':
        security_logger.warning(message, extra=extra)
    elif level == 'critical':
        security_logger.critical(message, extra=extra)
