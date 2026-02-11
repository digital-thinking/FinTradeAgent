"""Security middleware for production deployment."""

import time
from typing import Dict, Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers and enforce security policies."""
    
    def __init__(self, app, headers: Optional[Dict[str, str]] = None):
        super().__init__(app)
        self.security_headers = headers or {}
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Add security headers to all responses."""
        
        # Check for security violations before processing
        if self._check_security_violations(request):
            return Response(
                content="Security violation detected",
                status_code=403,
                headers=self.security_headers
            )
        
        # Process request
        response = await call_next(request)
        
        # Add security headers
        for header, value in self.security_headers.items():
            response.headers[header] = value
        
        # Add additional security headers based on content type
        if response.headers.get("content-type", "").startswith("text/html"):
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
        
        # Remove potentially sensitive headers
        response.headers.pop("Server", None)
        response.headers.pop("X-Powered-By", None)
        
        return response
    
    def _check_security_violations(self, request: Request) -> bool:
        """Check for common security violations."""
        
        # Check for suspicious user agents
        user_agent = request.headers.get("user-agent", "").lower()
        suspicious_agents = [
            "sqlmap", "nikto", "nmap", "masscan", 
            "dirb", "dirbuster", "gobuster", "wpscan"
        ]
        
        if any(agent in user_agent for agent in suspicious_agents):
            return True
        
        # Check for path traversal attempts
        path = str(request.url.path)
        if "../" in path or "..%2F" in path or "..%5C" in path:
            return True
        
        # Check for SQL injection patterns in query parameters
        query_string = str(request.url.query).lower()
        sql_patterns = [
            "union select", "drop table", "insert into",
            "delete from", "update set", "exec xp_",
            "script>", "<iframe", "javascript:"
        ]
        
        if any(pattern in query_string for pattern in sql_patterns):
            return True
        
        return False