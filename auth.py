import os
import streamlit as st
from datetime import datetime, timedelta
from supabase import create_client, Client
import hashlib
import secrets
import bcrypt
from typing import Optional, Dict, List, TypedDict
from typing import Literal
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Supabase client with better error handling
def init_supabase():
    try:
        SUPABASE_URL = "https://umtgkoogrtvyqcrzygoe.supabase.co"
        SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVtdGdrb29ncnR2eXFjcnp5Z29lIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDUxMzYyNDYsImV4cCI6MjA2MDcxMjI0Nn0.QMrKSOa91fzE7sNWBfhePhRFG05YMwNbvHYK8Fzkjpk"
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        # Test connection
        client.table("users").select("*").limit(1).execute()
        return client
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {str(e)}")
        st.error("Database connection failed. Please try again later.")
        return None

supabase = init_supabase()

# Type definitions
UserRole = Literal["admin", "manager", "user"]
Feature = Literal["dashboard", "inventory", "investments", 
                "expenses", "partnership", "reports", 
                "user_management", "data_export", "data_reset"]

class UserPermissions(TypedDict):
    dashboard: bool
    inventory: bool
    investments: bool
    expenses: bool
    partnership: bool
    reports: bool
    user_management: bool
    data_export: bool
    data_reset: bool

class RoleDefinition(TypedDict):
    permissions: UserPermissions

# Default admin configuration
DEFAULT_ADMIN = {
    "username": "admin@admin.com",
    "password": "admin123",
    "full_name": "System Administrator",
    "role": "admin",
    "business_unit": "All"
}

# Role-based permissions
ROLES: Dict[UserRole, RoleDefinition] = {
    "admin": {
        "permissions": {
            "dashboard": True,
            "inventory": True,
            "investments": True,
            "expenses": True,
            "partnership": True,
            "reports": True,
            "user_management": True,
            "data_export": True,
            "data_reset": True,
        }
    },
    "manager": {
        "permissions": {
            "dashboard": True,
            "inventory": True,
            "investments": True,
            "expenses": True,
            "partnership": True,
            "reports": True,
            "user_management": False,
            "data_export": True,
            "data_reset": False,
        }
    },
    "user": {
        "permissions": {
            "dashboard": True,
            "inventory": True,
            "investments": False,
            "expenses": True,
            "partnership": False,
            "reports": False,
            "user_management": False,
            "data_export": False,
            "data_reset": False,
        }
    }
}

# Security functions
def hash_password(password: str) -> str:
    """Hash password using bcrypt with increased work factor"""
    try:
        salt = bcrypt.gensalt(rounds=14)
        return bcrypt.hashpw(password.encode(), salt).decode()
    except Exception as e:
        logger.error(f"Password hashing failed: {str(e)}")
        raise

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash"""
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception as e:
        logger.error(f"Password verification failed: {str(e)}")
        return False

# Session management functions
def get_current_session() -> Optional[Dict]:
    """Get and validate current session with automatic refresh"""
    try:
        if not supabase:
            return None
            
        session = supabase.auth.get_session()
        if not session:
            # Attempt to refresh session
            try:
                supabase.auth.refresh_session()
                session = supabase.auth.get_session()
            except Exception as e:
                logger.warning(f"Session refresh failed: {str(e)}")
                return None
                
        if not session:
            return None
            
        # Check session expiration
        if hasattr(session, 'expires_at') and session.expires_at < datetime.now().timestamp():
            logger.warning("Session expired")
            return None
            
        return session
    except Exception as e:
        logger.error(f"Session error: {str(e)}")
        return None

def authenticate(username: str, password: str) -> Optional[Dict]:
    """Authenticate user and return user data if successful"""
    try:
        if not supabase:
            st.error("Database not available")
            return None
            
        if not username or not password:
            st.warning("Username and password are required")
            return None
            
        # Use Supabase auth for authentication
        auth_response = supabase.auth.sign_in_with_password({
            "email": username,
            "password": password
        })
        
        if auth_response and auth_response.user:
            return {
                "user": auth_response.user,
                "session": auth_response.session
            }
            
        st.warning("Invalid credentials")
        return None
        
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        st.error("Login failed. Please try again.")
        return None

def create_session(auth_data: Dict) -> bool:
    """Create application session from auth data"""
    try:
        if not auth_data or 'user' not in auth_data:
            return False
            
        user = auth_data['user']
        st.session_state['user'] = {
            "id": user.id,
            "email": user.email,
            "full_name": user.user_metadata.get("full_name", "User"),
            "role": user.user_metadata.get("role", "user"),
            "business_unit": user.user_metadata.get("business_unit", "All"),
            "session": auth_data.get('session')
        }
        return True
    except Exception as e:
        logger.error(f"Session creation failed: {str(e)}")
        return False

def validate_session() -> Optional[Dict]:
    """Validate and return current session data"""
    try:
        session = get_current_session()
        if not session:
            return None
            
        user = session.user
        return {
            "id": user.id,
            "email": user.email,
            "full_name": user.user_metadata.get("full_name", "User"),
            "role": user.user_metadata.get("role", "user"),
            "business_unit": user.user_metadata.get("business_unit", "All"),
            "session": session
        }
    except Exception as e:
        logger.error(f"Session validation failed: {str(e)}")
        return None

def logout() -> None:
    """Terminate user session"""
    try:
        if supabase:
            supabase.auth.sign_out()
            
        if 'user' in st.session_state:
            del st.session_state['user']
            
        st.success("You have been logged out successfully!")
        time.sleep(1)
        st.rerun()
    except Exception as e:
        logger.error(f"Logout failed: {str(e)}")
        st.error("Failed to log out properly. Please try again.")

def show_login() -> None:
    """Display the login form"""
    st.markdown(get_common_styles(), unsafe_allow_html=True)
    st.markdown('<p class="main-title">BizMaster Pro - Login</p>', unsafe_allow_html=True)
    
    with st.form("login_form", clear_on_submit=True):
        username = st.text_input("Email Address", placeholder="your@email.com")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        
        if submit:
            with st.spinner("Authenticating..."):
                auth_data = authenticate(username, password)
                if auth_data and create_session(auth_data):
                    st.success("Login successful! Loading application...")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Invalid credentials or account not found")

# Permission functions
def has_permission(user: Dict, feature: Feature) -> bool:
    """Check if user has permission to access a feature"""
    if not user or not isinstance(user, dict):
        return False
    
    if user.get("role") == "admin":
        return True
        
    role_permissions = ROLES.get(user.get("role", "user"), {}).get("permissions", {})
    return role_permissions.get(feature, False)

def require_permission(feature: Feature):
    """Decorator for permission-based access control"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            if 'user' not in st.session_state:
                st.error("Please login first")
                st.stop()
                
            if not has_permission(st.session_state.user, feature):
                st.error("You don't have permission to access this feature")
                st.stop()
                
            return func(*args, **kwargs)
        return wrapper
    return decorator

# User management functions
def create_default_admin() -> bool:
    """Ensure default admin exists in database"""
    try:
        if not supabase:
            return False
            
        response = supabase.table("users") \
                         .select("*") \
                         .eq("username", DEFAULT_ADMIN["username"]) \
                         .execute()
        
        if not response.data:
            admin_data = {
                "username": DEFAULT_ADMIN["username"],
                "password_hash": hash_password(DEFAULT_ADMIN["password"]),
                "full_name": DEFAULT_ADMIN["full_name"],
                "role": DEFAULT_ADMIN["role"],
                "business_unit": DEFAULT_ADMIN["business_unit"],
                "created_at": datetime.now().isoformat(),
                "is_active": True
            }
            
            supabase.table("users").insert(admin_data).execute()
            st.success("Default admin created successfully")
            return True
        
        existing_admin = response.data[0]
        if existing_admin.get("role") != "admin":
            supabase.table("users") \
                  .update({"role": "admin"}) \
                  .eq("id", existing_admin["id"]) \
                  .execute()
        return True
        
    except Exception as e:
        st.error(f"Admin creation failed: {str(e)}")
        return False

def get_users() -> List[Dict]:
    """Get all users from database"""
    try:
        if not supabase:
            return []
            
        response = supabase.table("users") \
                         .select("*") \
                         .order("created_at", desc=True) \
                         .execute()
        return response.data or []
        
    except Exception as e:
        st.error(f"Error fetching users: {str(e)}")
        return []

def create_user(username: str, password: str, full_name: str, role: str, business_unit: str) -> bool:
    """Create new user account"""
    try:
        if not supabase:
            return False
            
        user_data = {
            "username": username,
            "password_hash": hash_password(password),
            "full_name": full_name,
            "role": role,
            "business_unit": business_unit,
            "created_at": datetime.now().isoformat(),
            "is_active": True
        }
        
        response = supabase.table("users").insert(user_data).execute()
        return bool(response.data)
        
    except Exception as e:
        st.error(f"Error creating user: {str(e)}")
        return False

def update_user(user_id: str, **kwargs) -> bool:
    """Update user information"""
    try:
        if not supabase:
            return False
            
        updates = {}
        if "password" in kwargs:
            updates["password_hash"] = hash_password(kwargs["password"])
        if "full_name" in kwargs:
            updates["full_name"] = kwargs["full_name"]
        if "role" in kwargs:
            updates["role"] = kwargs["role"]
        if "business_unit" in kwargs:
            updates["business_unit"] = kwargs["business_unit"]
        if "is_active" in kwargs:
            updates["is_active"] = kwargs["is_active"]
            
        if updates:
            supabase.table("users").update(updates).eq("id", user_id).execute()
            return True
        return False
        
    except Exception as e:
        st.error(f"Error updating user: {str(e)}")
        return False

def delete_user(user_id: str) -> bool:
    """Soft delete user account"""
    try:
        if not supabase:
            return False
            
        supabase.table("users") \
               .update({
                   "is_active": False,
                   "deleted_at": datetime.now().isoformat()
               }) \
               .eq("id", user_id) \
               .execute()
               
        return True
        
    except Exception as e:
        st.error(f"Error deleting user: {str(e)}")
        return False

def clean_expired_sessions() -> None:
    """Clean up expired sessions"""
    try:
        if supabase:
            now = datetime.now().isoformat()
            supabase.table("sessions") \
                   .delete() \
                   .lt("expires_at", now) \
                   .execute()
    except Exception as e:
        st.error(f"Session cleanup error: {str(e)}")

# Initialize when imported
if supabase:
    try:
        create_default_admin()
        clean_expired_sessions()
    except Exception as e:
        st.error(f"Initialization error: {str(e)}")