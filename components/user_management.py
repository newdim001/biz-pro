import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client
from typing import List, Dict, Optional

# Initialize Supabase client
SUPABASE_URL = "https://umtgkoogrtvyqcrzygoe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVtdGdrb29ncnR2eXFjcnp5Z29lIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDUxMzYyNDYsImV4cCI6MjA2MDcxMjI0Nn0.QMrKSOa91fzE7sNWBfhePhRFG05YMwNbvHYK8Fzkjpk"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

from .auth import (
    get_users, create_user, delete_user, update_user,
    ROLES, require_permission
)

@require_permission("user_management")
def show_user_management():
    """Main user management interface"""
    st.header("📊 User Management")
    
    # Create new user form
    show_add_user_form()
    
    # User list with edit/delete options
    st.subheader("👥 Current Users")
    display_user_list()

def show_add_user_form():
    """Form to add new users"""
    with st.expander("➕ Add New User", expanded=False):
        with st.form("add_user_form", clear_on_submit=True):
            cols = st.columns(2)
            with cols[0]:
                username = st.text_input("Email/Username*", help="Must be a valid email address")
                full_name = st.text_input("Full Name*")
            with cols[1]:
                role = st.selectbox(
                    "Role*", 
                    list(ROLES.keys()), 
                    format_func=lambda x: x.capitalize(),
                    help="Determines user permissions"
                )
                business_unit = st.selectbox(
                    "Business Unit*", 
                    ["All", "Unit A", "Unit B"],
                    help="Which business unit this user belongs to"
                )
            
            password = st.text_input("Password*", type="password", help="At least 8 characters")
            confirm_password = st.text_input("Confirm Password*", type="password")
            
            if st.form_submit_button("Create User"):
                handle_user_creation(username, password, confirm_password, full_name, role, business_unit)

def handle_user_creation(username: str, password: str, confirm_password: str, 
                       full_name: str, role: str, business_unit: str):
    """Process user creation with validation"""
    try:
        if not all([username, password, full_name]):
            st.error("Please fill all required fields (marked with *)")
            return
            
        if '@' not in username or '.' not in username:
            st.error("Please enter a valid email address")
            return
            
        if password != confirm_password:
            st.error("Passwords do not match")
            return
            
        if len(password) < 8:
            st.error("Password must be at least 8 characters")
            return
            
        if create_user(username, password, full_name, role, business_unit):
            st.success(f"User {username} created successfully!")
            st.balloons()
        else:
            st.error("Username already exists or creation failed")
    except Exception as e:
        st.error(f"Error creating user: {str(e)}")

def display_user_list():
    """Display and manage list of users"""
    try:
        users = get_active_users()
        if not users:
            st.info("No active users found")
            return
            
        # Display user table
        df = prepare_user_table(users)
        st.dataframe(
            df,
            use_container_width=True,
            column_config={
                "created_at": st.column_config.DatetimeColumn("Created At"),
                "last_login": st.column_config.DatetimeColumn("Last Login")
            }
        )
        
        # User management options
        with st.expander("🛠 Manage Users", expanded=False):
            if users:
                selected_user = st.selectbox(
                    "Select User",
                    [f"{u['username']} ({u['role']})" for u in users],
                    key="user_select"
                )
                user_data = next(u for u in users if f"{u['username']} ({u['role']})" == selected_user)
                show_user_management_options(user_data)
    except Exception as e:
        st.error(f"Error loading users: {str(e)}")

def get_active_users() -> List[Dict]:
    """Get list of active users with proper error handling"""
    try:
        users = get_users()
        return [u for u in users if u.get('is_active', True)]
    except Exception as e:
        st.error(f"Failed to fetch users: {str(e)}")
        return []

def prepare_user_table(users: List[Dict]) -> pd.DataFrame:
    """Prepare user data for display in table"""
    df = pd.DataFrame(users)
    df = df[[
        'username', 
        'full_name', 
        'role', 
        'business_unit', 
        'created_at', 
        'last_login'
    ]]
    df['role'] = df['role'].str.capitalize()
    return df.sort_values('created_at', ascending=False)

def show_user_management_options(user_data: Dict):
    """Show edit/delete options for selected user"""
    tab1, tab2 = st.tabs(["✏️ Edit User", "🗑️ Delete User"])
    
    with tab1:
        show_edit_user_form(user_data)
    
    with tab2:
        show_delete_user_confirmation(user_data)

def show_edit_user_form(user_data: Dict):
    """Form to edit existing users"""
    with st.form(f"edit_user_{user_data['id']}"):
        cols = st.columns(2)
        with cols[0]:
            new_full_name = st.text_input(
                "Full Name", 
                value=user_data.get('full_name', ''),
                key=f"full_name_{user_data['id']}"
            )
            new_role = st.selectbox(
                "Role",
                list(ROLES.keys()),
                index=list(ROLES.keys()).index(user_data['role']),
                format_func=lambda x: x.capitalize(),
                key=f"role_{user_data['id']}"
            )
        with cols[1]:
            new_business_unit = st.selectbox(
                "Business Unit",
                ["All", "Unit A", "Unit B"],
                index=["All", "Unit A", "Unit B"].index(
                    user_data.get('business_unit', 'All')
                ),
                key=f"business_unit_{user_data['id']}"
            )
            new_password = st.text_input(
                "New Password (leave blank to keep current)", 
                type="password",
                key=f"password_{user_data['id']}"
            )
        
        if st.form_submit_button("Update User"):
            handle_user_update(user_data, new_full_name, new_role, new_business_unit, new_password)

def handle_user_update(user_data: Dict, full_name: str, role: str, 
                      business_unit: str, password: str):
    """Process user updates with validation"""
    try:
        updates = {
            'full_name': full_name,
            'role': role,
            'business_unit': business_unit
        }
        
        if password:
            updates['password'] = password
            
        if update_user(user_data['id'], **updates):
            st.success("✅ User updated successfully!")
        else:
            st.error("Failed to update user")
    except Exception as e:
        st.error(f"Error updating user: {str(e)}")

def show_delete_user_confirmation(user_data: Dict):
    """Confirmation dialog for user deletion"""
    st.warning(f"You are about to delete user: {user_data['username']}")
    
    if st.button("Confirm Delete", 
                key=f"confirm_delete_{user_data['id']}",
                type="primary",
                help="This action cannot be undone"):
        try:
            if delete_user(user_data['id']):
                st.success("User deactivated successfully")
                st.rerun()
            else:
                st.error("Failed to deactivate user")
        except Exception as e:
            st.error(f"Error deleting user: {str(e)}")
    
    if st.button("Cancel", key=f"cancel_delete_{user_data['id']}"):
        st.rerun()