from fastapi import APIRouter, HTTPException, Depends, Query, status
from typing import Dict, Any, Optional
from backend.app.models import LoginRequest, LoginResponse, UserResponse
from backend.app.auth import LOCAL_USERS, create_access_token, get_current_user
from backend.app.config import (
    AUTH_MODE,
    STORAGE_MODE,
    COGNITO_USER_POOL_ID,
    COGNITO_APP_CLIENT_ID,
    AWS_REGION
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/config")
def get_auth_config():
    """Returns the current server authentication & storage mode to the frontend."""
    return {
        "auth_mode": AUTH_MODE,
        "storage_mode": STORAGE_MODE,
        "is_local": AUTH_MODE in ["local", "development", "dev"],
        "default_admin": {
            "username": "admin@intellistock.in",
            "role": "Admin",
            "name": "Dr. S. Sharma (Administrator)"
        },
        "default_staff": {
            "username": "staff@intellistock.in",
            "role": "Staff",
            "name": "Seshadhri (Operations Staff)"
        }
    }


@router.get("/demo-token")
def get_demo_token(role: str = Query("Admin", pattern="^(Admin|Staff)$")):
    """
    Returns an immediate signed development token for zero-friction local testing.
    Only active in local mode.
    """
    if AUTH_MODE not in ["local", "development", "dev"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo token generator is disabled in AWS Production Mode."
        )
    
    user_email = "admin@inventory.io" if role == "Admin" else "staff@inventory.io"
    user_record = LOCAL_USERS[user_email]
    token = create_access_token(user_record)
    
    return {
        "success": True,
        "token": token,
        "dev_token_alias": "dev-admin-token" if role == "Admin" else "dev-staff-token",
        "user": user_record
    }


@router.post("/login", response_model=Dict[str, Any])
def login(payload: LoginRequest):
    """
    Authenticates user credentials against:
    - Local user registry when AUTH_MODE=local
    - Amazon Cognito User Pool when AUTH_MODE=aws
    """
    username = payload.username.lower().strip()

    # LOCAL DEVELOPMENT AUTHENTICATION
    if AUTH_MODE in ["local", "development", "dev"]:
        user_record = LOCAL_USERS.get(username)
        if not user_record or user_record["password"] != payload.password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password. For demo, use admin@inventory.io with Password123!"
            )
        
        token = create_access_token(user_record)
        return {
            "success": True,
            "token": token,
            "auth_mode": "local",
            "user": {
                "id": user_record["id"],
                "username": user_record["username"],
                "role": user_record["role"],
                "name": user_record["name"]
            }
        }

    # AWS PRODUCTION COGNITO AUTHENTICATION
    try:
        import boto3
        cognito = boto3.client("cognito-idp", region_name=AWS_REGION)
        resp = cognito.initiate_auth(
            ClientId=COGNITO_APP_CLIENT_ID,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={
                "USERNAME": username,
                "PASSWORD": payload.password
            }
        )
        auth_res = resp.get("AuthenticationResult", {})
        id_token = auth_res.get("IdToken")
        access_token = auth_res.get("AccessToken")

        return {
            "success": True,
            "token": id_token or access_token,
            "auth_mode": "aws_cognito",
            "user": {
                "id": username,
                "username": username,
                "role": "Admin",  # Extracted from Cognito claims
                "name": username
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"AWS Cognito authentication failed: {str(e)}"
        )


@router.get("/me", response_model=UserResponse)
def get_profile(current_user: dict = Depends(get_current_user)):
    """Returns currently authenticated user profile."""
    return {
        "id": current_user.get("sub", current_user.get("id", "USR-001")),
        "username": current_user.get("username", "admin@inventory.io"),
        "role": current_user.get("role", "Admin"),
        "name": current_user.get("name", "Administrator")
    }


@router.post("/logout")
def logout():
    """Client handles token disposal."""
    return {"success": True, "message": "Logged out successfully."}
