"""
Request context handling for authentication.

This module provides utilities for accessing the current request object
and extracting user information from it.
"""

import logging
from typing import Optional, Dict, Any
from starlette.requests import Request
from contextvars import ContextVar
from fastapi import Depends
from app.services.auth_service import get_current_user as get_user_from_token
from app.services.auth_service import oauth2_scheme
import contextvars

# Create a context variable to store the request
_request_var = contextvars.ContextVar("request", default=None)
logger = logging.getLogger(__name__)

def set_request(request: Request) -> None:
    """Set the current request in the context."""
    _request_var.set(request)

def get_request() -> Optional[Request]:
    """Get the current request from the context."""
    return _request_var.get()

def set_request_var(request: Request) -> None:
    """Set the request context variable (used for testing)"""
    _request_var.set(request)

def set_request_context(request: Request) -> None:
    """Legacy alias for set_request_var (for compatibility)"""
    set_request_var(request)

async def get_current_user_from_context() -> Optional[Dict[str, Any]]:
    """
    Get the current user from the request context.
    
    Returns:
        Dict[str, Any]: User information if authenticated, None otherwise.
    """
    request = get_request()
    
    if not request:
        logger.warning("get_current_user_from_context: No request in context")
        return None
    
    # Check if user is already available in request state
    if hasattr(request.state, "user"):
        return request.state.user
    
    # Try to get from authorization header
    if "Authorization" in request.headers:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth.replace("Bearer ", "")
            try:
                user = await get_user_from_token(token)
                # Cache in request state
                request.state.user = user
                return user
            except Exception as e:
                logger.error(f"Error getting user from token: {str(e)}")
    
    logger.warning("get_current_user_from_context: No user in context")
    return None

# Middleware to set request in context
async def request_context_middleware(request: Request, call_next):
    """Middleware to set the request in the context."""
    set_request(request)
    response = await call_next(request)
    return response 