#!/usr/bin/env python3
"""
Authentication and Authorization Module
Implements JWT-based authentication with tenant context
"""

import os
import jwt
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from fastapi import HTTPException, Security, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from logger_config import get_logger

load_dotenv()

logger = get_logger(__name__)

# Security configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-this-in-production-min-32-chars")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("SESSION_TIMEOUT_MINUTES", "60"))

# Validate JWT secret in production
if len(JWT_SECRET_KEY) < 32:
    logger.warning("JWT_SECRET_KEY is too short. Use at least 32 characters in production.")

security = HTTPBearer()


class AuthenticationError(Exception):
    """Raised when authentication fails"""
    pass


class AuthorizationError(Exception):
    """Raised when authorization fails"""
    pass


def hash_password(password: str) -> str:
    """
    Hash password using SHA-256

    Args:
        password: Plain text password

    Returns:
        Hashed password

    Note: In production, use bcrypt or argon2 instead
    """
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify password against hash

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password

    Returns:
        True if password matches
    """
    return hash_password(plain_password) == hashed_password


def create_access_token(
    user_id: str,
    tenant_code: str,
    username: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create JWT access token

    Args:
        user_id: User ID
        tenant_code: Tenant code
        username: Username
        expires_delta: Optional custom expiration time

    Returns:
        JWT token string
    """
    to_encode = {
        "user_id": user_id,
        "tenant_code": tenant_code,
        "username": username,
        "type": "access"
    }

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "iat": datetime.utcnow()})

    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

    logger.info("Access token created", user_id=user_id, tenant_code=tenant_code)

    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate JWT token

    Args:
        token: JWT token string

    Returns:
        Decoded token payload

    Raises:
        AuthenticationError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])

        # Validate token type
        if payload.get("type") != "access":
            raise AuthenticationError("Invalid token type")

        # Validate required fields
        required_fields = ["user_id", "tenant_code", "username"]
        for field in required_fields:
            if field not in payload:
                raise AuthenticationError(f"Missing required field: {field}")

        return payload

    except jwt.ExpiredSignatureError:
        logger.warning("Token expired")
        raise AuthenticationError("Token has expired")
    except jwt.InvalidTokenError as e:
        logger.warning("Invalid token", error=str(e))
        raise AuthenticationError("Invalid token")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> Dict[str, Any]:
    """
    Dependency to get current authenticated user from JWT token

    Args:
        credentials: HTTP Bearer credentials

    Returns:
        User information dict

    Raises:
        HTTPException: If authentication fails
    """
    try:
        token = credentials.credentials
        payload = decode_access_token(token)

        user_info = {
            "user_id": payload["user_id"],
            "tenant_code": payload["tenant_code"],
            "username": payload["username"]
        }

        logger.debug("User authenticated", user_id=user_info["user_id"])

        return user_info

    except AuthenticationError as e:
        logger.error("Authentication failed", error=str(e))
        raise HTTPException(
            status_code=401,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_tenant(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> str:
    """
    Dependency to get current tenant code from authenticated user

    Args:
        current_user: Current user from get_current_user dependency

    Returns:
        Tenant code
    """
    return current_user["tenant_code"]


def authenticate_user(username: str, password: str, tenant_code: str) -> Tuple[bool, Optional[str], Optional[Dict]]:
    """
    Authenticate user credentials

    Args:
        username: Username
        password: Password
        tenant_code: Tenant code

    Returns:
        Tuple of (success, error_message, user_data)

    Note: This is a placeholder. In production, verify against database.
    """
    # TODO: Replace with actual database lookup
    # For now, accept any username/password for demo purposes
    # In production, this should query the Users table

    logger.info("Authentication attempt", username=username, tenant_code=tenant_code)

    # Validate tenant code format
    from tenant_security import TenantValidator
    is_valid, error = TenantValidator.validate_tenant_code(tenant_code)
    if not is_valid:
        logger.warning("Invalid tenant code", tenant_code=tenant_code, error=error)
        return False, f"Invalid tenant code: {error}", None

    # Mock user data - replace with database lookup
    user_data = {
        "user_id": f"user_{username}_{tenant_code}",
        "username": username,
        "tenant_code": tenant_code,
        "roles": ["user"]  # Add role-based access control
    }

    logger.info("Authentication successful", username=username, tenant_code=tenant_code)

    return True, None, user_data


async def optional_auth(
    authorization: Optional[str] = Header(None)
) -> Optional[Dict[str, Any]]:
    """
    Optional authentication - allows both authenticated and anonymous access

    Args:
        authorization: Optional Authorization header

    Returns:
        User information dict or None
    """
    if authorization is None:
        return None

    try:
        # Extract token from "Bearer <token>"
        if not authorization.startswith("Bearer "):
            return None

        token = authorization.replace("Bearer ", "")
        payload = decode_access_token(token)

        return {
            "user_id": payload["user_id"],
            "tenant_code": payload["tenant_code"],
            "username": payload["username"]
        }
    except AuthenticationError:
        return None
