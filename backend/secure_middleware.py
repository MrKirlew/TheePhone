"""
Secure Authentication and Validation Middleware for KirlewAI Backend
"""

import os
import jwt
import hmac
import hashlib
import base64
import time
import json
from typing import Dict, Optional, Tuple
from functools import wraps
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from google.oauth2 import id_token
from google.auth.transport import requests
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SecurityConfig:
    """Security configuration constants"""
    JWT_SECRET_KEY = os.getenv('JWT_SECRET', 'your-secret-key-change-this')
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
    MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10MB
    TOKEN_EXPIRY_SECONDS = 3600  # 1 hour
    RATE_LIMIT_PER_MINUTE = 60
    ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', '').split(',')

class SecureMiddleware:
    """Security middleware for request validation and authentication"""
    
    def __init__(self):
        self.rate_limit_store = {}  # In production, use Redis
        self.encryption_key = self._generate_encryption_key()
    
    def _generate_encryption_key(self) -> bytes:
        """Generate encryption key from environment secret"""
        password = SecurityConfig.JWT_SECRET_KEY.encode()
        salt = b'kirlewai_salt'  # In production, use random salt per user
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(password))
    
    def validate_request_signature(self, request_data: Dict, signature: str, timestamp: str) -> bool:
        """Validate HMAC signature of request"""
        try:
            # Check timestamp (prevent replay attacks)
            request_time = int(timestamp)
            current_time = int(time.time() * 1000)
            if abs(current_time - request_time) > 300000:  # 5 minutes
                logger.warning(f"Request timestamp too old: {request_time}")
                return False
            
            # Recreate signature
            message = f"{request_data.get('method', 'POST')}|{request_data.get('url', '')}|{json.dumps(request_data, sort_keys=True)}|{timestamp}"
            expected_signature = base64.b64encode(
                hmac.new(
                    SecurityConfig.JWT_SECRET_KEY.encode(),
                    message.encode(),
                    hashlib.sha256
                ).digest()
            ).decode()
            
            return hmac.compare_digest(signature, expected_signature)
        except Exception as e:
            logger.error(f"Signature validation error: {e}")
            return False
    
    def validate_google_token(self, id_token_str: str) -> Optional[Dict]:
        """Validate Google ID token"""
        try:
            if not SecurityConfig.GOOGLE_CLIENT_ID:
                logger.error("Google Client ID not configured")
                return None
            
            idinfo = id_token.verify_oauth2_token(
                id_token_str,
                requests.Request(),
                SecurityConfig.GOOGLE_CLIENT_ID
            )
            
            # Verify token issuer
            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                logger.warning(f"Invalid token issuer: {idinfo['iss']}")
                return None
            
            return idinfo
        except ValueError as e:
            logger.error(f"Google token validation failed: {e}")
            return None
    
    def decrypt_request_data(self, encrypted_data: str, key: str, iv: str) -> Optional[str]:
        """Decrypt encrypted request data"""
        try:
            # Decode base64 encoded data
            encrypted_bytes = base64.b64decode(encrypted_data)
            key_bytes = base64.b64decode(key)
            iv_bytes = base64.b64decode(iv)
            
            # Create cipher and decrypt
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            cipher = Cipher(algorithms.AES(key_bytes), modes.CBC(iv_bytes))
            decryptor = cipher.decryptor()
            
            decrypted_padded = decryptor.update(encrypted_bytes) + decryptor.finalize()
            
            # Remove PKCS5 padding
            padding_length = decrypted_padded[-1]
            decrypted = decrypted_padded[:-padding_length]
            
            return decrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return None
    
    def validate_file_upload(self, file_data: bytes, filename: str) -> bool:
        """Validate uploaded file for security"""
        try:
            # Check file size
            if len(file_data) > SecurityConfig.MAX_REQUEST_SIZE:
                logger.warning(f"File too large: {len(file_data)} bytes")
                return False
            
            # Check file extension
            allowed_extensions = ['.jpg', '.jpeg', '.png', '.webp']
            file_extension = os.path.splitext(filename.lower())[1]
            if file_extension not in allowed_extensions:
                logger.warning(f"Invalid file extension: {file_extension}")
                return False
            
            # Basic file header validation
            if file_extension in ['.jpg', '.jpeg'] and not file_data.startswith(b'\xff\xd8'):
                logger.warning("Invalid JPEG file header")
                return False
            elif file_extension == '.png' and not file_data.startswith(b'\x89PNG'):
                logger.warning("Invalid PNG file header")
                return False
            
            return True
        except Exception as e:
            logger.error(f"File validation error: {e}")
            return False
    
    def check_rate_limit(self, client_id: str) -> bool:
        """Check if client has exceeded rate limit"""
        try:
            current_time = time.time()
            minute_window = int(current_time / 60)
            
            if client_id not in self.rate_limit_store:
                self.rate_limit_store[client_id] = {}
            
            client_requests = self.rate_limit_store[client_id]
            
            # Clean old windows
            for window in list(client_requests.keys()):
                if window < minute_window - 1:
                    del client_requests[window]
            
            # Count requests in current window
            current_requests = client_requests.get(minute_window, 0)
            if current_requests >= SecurityConfig.RATE_LIMIT_PER_MINUTE:
                logger.warning(f"Rate limit exceeded for client: {client_id}")
                return False
            
            # Increment counter
            client_requests[minute_window] = current_requests + 1
            return True
        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            return False
    
    def sanitize_input(self, input_text: str) -> str:
        """Sanitize user input to prevent injection attacks"""
        try:
            # Remove potential SQL injection patterns
            dangerous_patterns = [
                '--', ';--', '/*', '*/', 'xp_', 'sp_', 'exec', 'execute',
                'script', 'javascript:', 'vbscript:', 'onload', 'onerror'
            ]
            
            sanitized = input_text
            for pattern in dangerous_patterns:
                sanitized = sanitized.replace(pattern, '')
            
            # Limit length
            if len(sanitized) > 1000:
                sanitized = sanitized[:1000]
            
            return sanitized.strip()
        except Exception as e:
            logger.error(f"Input sanitization error: {e}")
            return ""
    
    def generate_response_signature(self, response_data: bytes) -> str:
        """Generate signature for response integrity"""
        try:
            signature = hmac.new(
                SecurityConfig.JWT_SECRET_KEY.encode(),
                response_data,
                hashlib.sha256
            ).digest()
            return base64.b64encode(signature).decode()
        except Exception as e:
            logger.error(f"Response signature generation error: {e}")
            return ""

def require_authentication(f):
    """Decorator to require authentication for endpoints"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import request, jsonify
        
        middleware = SecureMiddleware()
        
        # Check rate limiting
        client_id = request.headers.get('X-Request-ID', request.remote_addr)
        if not middleware.check_rate_limit(client_id):
            return jsonify({'error': 'Rate limit exceeded'}), 429
        
        # Validate request signature
        signature = request.headers.get('X-Signature')
        timestamp = request.headers.get('X-Timestamp')
        if signature and timestamp:
            request_data = {
                'method': request.method,
                'url': request.url,
                'data': request.get_json() or {}
            }
            if not middleware.validate_request_signature(request_data, signature, timestamp):
                logger.warning("Invalid request signature")
                return jsonify({'error': 'Invalid signature'}), 401
        
        # Validate Google ID token
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing authentication token'}), 401
        
        id_token_str = auth_header.split(' ')[1]
        user_info = middleware.validate_google_token(id_token_str)
        if not user_info:
            return jsonify({'error': 'Invalid authentication token'}), 401
        
        # Add user info to request context
        request.user_info = user_info
        request.security_middleware = middleware
        
        return f(*args, **kwargs)
    return decorated_function

def validate_multimodal_request(f):
    """Decorator to validate multimodal requests"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import request, jsonify
        
        middleware = getattr(request, 'security_middleware', SecureMiddleware())
        
        # Validate encrypted data if present
        encrypted_voice = request.form.get('encrypted_voice_command')
        if encrypted_voice:
            encryption_key = request.form.get('encryption_key')
            encryption_iv = request.form.get('encryption_iv')
            
            if not encryption_key or not encryption_iv:
                return jsonify({'error': 'Missing encryption parameters'}), 400
            
            decrypted_voice = middleware.decrypt_request_data(
                encrypted_voice, encryption_key, encryption_iv
            )
            if not decrypted_voice:
                return jsonify({'error': 'Decryption failed'}), 400
            
            # Sanitize decrypted input
            sanitized_voice = middleware.sanitize_input(decrypted_voice)
            request.sanitized_voice_command = sanitized_voice
        
        # Validate file upload if present
        if 'image_file' in request.files:
            file = request.files['image_file']
            if file.filename:
                file_data = file.read()
                if not middleware.validate_file_upload(file_data, file.filename):
                    return jsonify({'error': 'Invalid file upload'}), 400
                
                # Reset file pointer for later use
                file.seek(0)
        
        return f(*args, **kwargs)
    return decorated_function

# Security headers middleware
def add_security_headers(response):
    """Add security headers to response"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'"
    
    # Add response signature
    if hasattr(response, 'data'):
        middleware = SecureMiddleware()
        signature = middleware.generate_response_signature(response.data)
        response.headers['X-Response-Signature'] = signature
    
    return response