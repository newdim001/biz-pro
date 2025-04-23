# app.py - MUST be first Streamlit command
import streamlit as st
st.set_page_config(
    page_title="BizMaster Pro",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Now other imports
from supabase import create_client
import time
from datetime import date
from typing import Optional, Dict
import logging

# Local imports
from data.session_state import initialize_session_state
from components.styles import get_common_styles
from components.dashboard import show_dashboard
from components.inventory import show_inventory
from components.investments import show_investments
from components.expenses import show_expenses
from components.partnership import show_partnership
from components.reports import show_reports
from components.user_management import show_user_management

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Supabase client
def init_supabase():
    try:
        SUPABASE_URL = "https://umtgkoogrtvyqcrzygoe.supabase.co"
        SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVtdGdrb29ncnR2eXFjcnp5Z29lIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDUxMzYyNDYsImV4cCI6MjA2MDcxMjI0Nn0.QMrKSOa91fzE7sNWBfhePhRFG05YMwNbvHYK8Fzkjpk"
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {str(e)}")
        st.error("Failed to connect to database. Please try again later.")
        return None

supabase = init_supabase()

def refresh_session() -> bool:
    """Attempt to refresh the session if expired"""
    try:
        if not supabase:
            return False
            
        current_session = supabase.auth.get_session()
        if current_session:
            return True
            
        try:
            supabase.auth.refresh_session()
            return supabase.auth.get_session() is not None
        except Exception as refresh_error:
            logger.warning(f"Session refresh failed: {str(refresh_error)}")
            return False
            
    except Exception as e:
        logger.error(f"Session refresh error: {str(e)}")
        return False

def authenticate(username: str, password: str) -> Optional[Dict]:
    """Authenticate user using Supabase"""
    try:
        if not supabase:
            return None
            
        if not username or not password:
            st.warning("Please enter both username and password")
            return None
            
        response = supabase.auth.sign_in_with_password({
            "email": username,
            "password": password
        })
        
        if response and response.user:
            return {
                "id": response.user.id,
                "email": response.user.email,
                "full_name": response.user.user_metadata.get("full_name", "User"),
                "role": response.user.user_metadata.get("role", "user"),
                "business_unit": response.user.user_metadata.get("business_unit", "All"),
                "session": response.session
            }
        return None
        
    except Exception as e:
        logger.error(f"Authentication failed for {username}: {str(e)}")
        st.error("Invalid credentials or connection error")
        return None

def create_session(user_data: Dict) -> None:
    """Create a session for the authenticated user"""
    try:
        st.session_state['user'] = {
            "id": user_data["id"],
            "email": user_data["email"],
            "full_name": user_data["full_name"],
            "role": user_data["role"],
            "business_unit": user_data["business_unit"],
            "session": user_data.get("session")
        }
        logger.info(f"Session created for {user_data['email']}")
    except Exception as e:
        logger.error(f"Session creation failed: {str(e)}")
        raise

def validate_session() -> Optional[Dict]:
    """Validate the current session using Supabase"""
    try:
        if not refresh_session():
            return None
            
        session = supabase.auth.get_session()
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
    """Log out the user by ending the session"""
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
                user_data = authenticate(username, password)
                if user_data:
                    create_session(user_data)
                    st.success("Login successful! Loading application...")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Invalid credentials or account not found")

def has_permission(role: str, feature: str) -> bool:
    """Check if the user has permission to access a specific feature"""
    permissions = {
        "admin": ["dashboard", "inventory", "investments", "expenses", 
                 "partnership", "reports", "user_management", "reset_data"],
        "manager": ["dashboard", "inventory", "investments", "expenses", 
                    "partnership", "reports"],
        "user": ["dashboard", "inventory", "expenses"]
    }
    return feature in permissions.get(role, [])

def initialize_default_data() -> None:
    """Initialize default data in the database"""
    try:
        if not supabase:
            raise Exception("Database not initialized")
            
        response = supabase.table("market_prices") \
                         .select("*") \
                         .order("date", desc=True) \
                         .limit(1) \
                         .execute()
                         
        if not response.data:
            default_price = {
                "price": 50.0,
                "date": date.today().isoformat()
            }
            supabase.table("market_prices").insert(default_price).execute()
        
        cash_response = supabase.table("cash_balances").select("*").execute()
        if not cash_response.data:
            default_cash_balances = [
                {"business_unit": "Unit A", "balance": 40000000.0},
                {"business_unit": "Unit B", "balance": 10000.0}
            ]
            supabase.table("cash_balances").insert(default_cash_balances).execute()
            
    except Exception as e:
        logger.error(f"Error initializing default data: {str(e)}")
        raise

def reset_all_data() -> None:
    """Secure data reset function"""
    try:
        if 'user' not in st.session_state or st.session_state.user.get('role') != 'admin':
            st.error("Administrator privileges required")
            return

        st.warning("⚠️ This will delete ALL data and reset to defaults!")
        confirmation = st.text_input("Type 'RESET' to confirm:", key="reset_confirmation")
        
        if confirmation.strip().upper() != "RESET":
            if confirmation:
                st.error("Confirmation text must be exactly 'RESET'")
            return

        if not refresh_session():
            st.error("Session expired. Please login again")
            return

        status_area = st.empty()
        progress_bar = st.progress(0)
        status_area.info("🚀 Starting data reset process...")

        tables = [
            "partnerships",
            "investments", 
            "expenses",
            "inventory",
            "market_prices",
            "cash_balances"
        ]
        
        for i, table in enumerate(tables):
            try:
                status_area.info(f"🔄 Resetting {table}...")
                progress_bar.progress((i + 1) / (len(tables) + 2))
                response = supabase.table(table).delete().neq('id', 0).execute()
                
                if hasattr(response, 'error') and response.error:
                    raise Exception(response.error.message)

            except Exception as table_error:
                status_area.error(f"❌ Failed resetting {table}: {str(table_error)}")
                return

        status_area.info("📦 Loading default data...")
        progress_bar.progress(90)
        initialize_default_data()
        
        progress_bar.progress(100)
        status_area.success("✅ Data reset completed successfully!")
        time.sleep(2)
        st.rerun()

    except Exception as e:
        logger.error(f"Critical error during reset: {str(e)}")
        st.error(f"Reset failed: {str(e)}")

def show_main_interface(user: Dict) -> None:
    """Show the main application interface"""
    st.markdown(f'<p class="main-title">BizMaster Pro - Welcome {user["full_name"]} ({user["role"].capitalize()})</p>', 
                unsafe_allow_html=True)

    with st.sidebar:
        st.markdown(f'<p style="font-size:14px;"><strong>👤 {user["email"]}</strong></p>', 
                    unsafe_allow_html=True)
        st.markdown(f'<p style="font-size:12px;"><strong>Role:</strong> {user["role"].capitalize()}</p>', 
                    unsafe_allow_html=True)
        st.markdown(f'<p style="font-size:12px;"><strong>Business Unit:</strong> {user["business_unit"]}</p>', 
                    unsafe_allow_html=True)

        if st.button("🚪 Logout", key="logout_btn", use_container_width=True):
            logout()

        menu_options = []
        if has_permission(user['role'], 'dashboard'):
            menu_options.append("📊 Dashboard")
        if has_permission(user['role'], 'inventory'):
            menu_options.append("📦 Inventory")
        if has_permission(user['role'], 'investments'):
            menu_options.append("💼 Investments")
        if has_permission(user['role'], 'expenses'):
            menu_options.append("💰 Expenses")
        if has_permission(user['role'], 'partnership'):
            menu_options.append("🤝 Partnership")
        if has_permission(user['role'], 'reports'):
            menu_options.append("📈 Reports")
        if has_permission(user['role'], 'user_management'):
            menu_options.append("👥 User Management")
        if has_permission(user['role'], 'reset_data'):
            menu_options.append("♻️ Reset Data")

        menu = st.selectbox("Navigation", menu_options, key="main_menu")

    try:
        if menu == "📊 Dashboard":
            show_dashboard()
        elif menu == "📦 Inventory":
            show_inventory()
        elif menu == "💼 Investments":
            show_investments()
        elif menu == "💰 Expenses":
            show_expenses()
        elif menu == "🤝 Partnership":
            show_partnership()
        elif menu == "📈 Reports":
            show_reports()
        elif menu == "👥 User Management":
            show_user_management()
        elif menu == "♻️ Reset Data":
            reset_all_data()
    except Exception as e:
        logger.error(f"Error loading {menu}: {str(e)}")
        st.error(f"Failed to load {menu.split()[1] if menu else 'component'}. Please try again.")

def main() -> None:
    """Main function to run the application"""
    try:
        initialize_session_state()
        st.markdown(get_common_styles(), unsafe_allow_html=True)
        
        if 'user' not in st.session_state:
            user_data = validate_session()
            if user_data:
                st.session_state['user'] = user_data
        
        if 'user' not in st.session_state:
            show_login()
            return

        show_main_interface(st.session_state['user'])

    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        st.error("A critical error occurred. Please refresh the page or contact support.")

if __name__ == "__main__":
    main()