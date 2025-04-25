import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime, timedelta
import time
from typing import Dict, Union

# Initialize Supabase client with error handling
try:
    SUPABASE_URL = "https://umtgkoogrtvyqcrzygoe.supabase.co"
    SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVtdGdrb29ncnR2eXFjcnp5Z29lIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDUxMzYyNDYsImV4cCI6MjA2MDcxMjI0Nn0.QMrKSOa91fzE7sNWBfhePhRFG05YMwNbvHYK8Fzkjpk"
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"Failed to initialize Supabase client: {str(e)}")
    st.stop()

# Standardized column names (all lowercase with underscores)
DEFAULT_INVENTORY_COLS = [
    'date', 'transaction_type', 'quantity_kg', 
    'unit_price', 'total_amount', 'remarks', 'business_unit'
]
DEFAULT_INVESTMENTS_COLS = [
    'date', 'amount', 'investor', 'remarks', 'business_unit'
]
DEFAULT_EXPENSES_COLS = [
    'date', 'category', 'amount', 'description', 'business_unit', 'partner'
]
DEFAULT_PARTNERSHIP_COLS = ['partner', 'share', 'withdrawn', 'invested']

def safe_convert(df: pd.DataFrame, column: str, dtype: type = float) -> pd.Series:
    """Safely convert DataFrame column to specified type."""
    try:
        return pd.to_numeric(df[column], errors='coerce').fillna(0).astype(dtype)
    except Exception as e:
        st.error(f"Failed to convert {column}: {str(e)}")
        return pd.Series([0] * len(df), False

def initialize_default_data(business_units: list = ['Unit A', 'Unit B']) -> None:
    """Initialize default data in Supabase tables with type safety."""
    try:
        # Initialize cash balances if empty
        cash_response = supabase.table("cash_balances").select("*").execute()
        if not cash_response.data:
            for unit in business_units:
                supabase.table("cash_balances").upsert({
                    "business_unit": unit,
                    "balance": 0.0
                }).execute()
       
def initialize_cash_balances():
    """Initialize cash balances with proper error handling"""
    cash_balance = {}
    for unit in ["Unit A", "Unit B"]:
        try:
            # Use upsert to ensure record exists
            response = supabase.table('cash_balances').upsert({
                "business_unit": unit,
                "balance": 10000.0,
                "updated_at": datetime.now().isoformat()
            }, on_conflict="business_unit").execute()
            
            if response.data:
                cash_balance[unit] = float(response.data[0].get("balance", 10000.0))
            else:
                cash_balance[unit] = 10000.0
        except Exception as e:
            st.error(f"Failed to initialize balance for {unit}: {str(e)}")
            cash_balance[unit] = 10000.0
    return cash_balance 
        # Initialize default partners if none exist
        partners_response = supabase.table("partnerships").select("*").execute()
        if not partners_response.data:
            default_partners = [
                {"business_unit": "Unit A", "partner": "Ahmed", "share": 60.0, "withdrawn": 0.0, "invested": 0.0},
                {"business_unit": "Unit A", "partner": "Fatima", "share": 40.0, "withdrawn": 0.0, "invested": 0.0},
                {"business_unit": "Unit B", "partner": "Ali", "share": 50.0, "withdrawn": 0.0, "invested": 0.0},
                {"business_unit": "Unit B", "partner": "Mariam", "share": 50.0, "withdrawn": 0.0, "invested": 0.0}
            ]
            supabase.table("partnerships").insert(default_partners).execute()
                
    except Exception as e:
        st.error(f"Error initializing default data: {str(e)}")

def refresh_all_data() -> None:
    """Force refresh all session state data from Supabase."""
    try:
        with st.spinner("Refreshing all data..."):
            # Fetch all data in parallel
            inventory = supabase.table("inventory").select("*").execute()
            cash_balances = supabase.table("cash_balances").select("*").execute()
            investments = supabase.table("investments").select("*").execute()
            expenses = supabase.table("expenses").select("*").execute()
            partnerships = supabase.table("partnerships").select("*").execute()

            # Process inventory with type conversion
            inventory_df = pd.DataFrame(
                inventory.data if inventory.data else [],
                columns=DEFAULT_INVENTORY_COLS
            )
            inventory_df['quantity_kg'] = safe_convert(inventory_df, 'quantity_kg')
            inventory_df['unit_price'] = safe_convert(inventory_df, 'unit_price')
            inventory_df['total_amount'] = safe_convert(inventory_df, 'total_amount')
            st.session_state.inventory = inventory_df

            # Process cash balances
            st.session_state.cash_balance = {
                row['business_unit']: float(row['balance'])
                for row in cash_balances.data
            } if cash_balances.data else {unit: 0.0 for unit in ['Unit A', 'Unit B']}

            # Process other data with type safety
            st.session_state.investments = pd.DataFrame(
                investments.data if investments.data else [],
                columns=DEFAULT_INVESTMENTS_COLS
            )
            st.session_state.expenses = pd.DataFrame(
                expenses.data if expenses.data else [],
                columns=DEFAULT_EXPENSES_COLS
            )
            
            # Process partnerships with numeric conversion
            if partnerships.data:
                partners_df = pd.DataFrame(partnerships.data)
                for col in ['share', 'withdrawn', 'invested']:
                    partners_df[col] = safe_convert(partners_df, col)
                st.session_state.partners = {
                    unit: partners_df[partners_df['business_unit'] == unit]
                    for unit in ['Unit A', 'Unit B']
                }
            
            st.session_state.last_updated = datetime.now()
            st.success("Data refreshed successfully!")
            
    except Exception as e:
        st.error(f"Refresh failed: {str(e)}")

def initialize_session_state() -> None:
    """Initialize or refresh session state with data validation."""
    if 'initialized' not in st.session_state:
        st.session_state.initialized = False
    
    if not st.session_state.initialized:
        initialize_default_data()
        refresh_all_data()
        st.session_state.initialized = True

def update_cash_balance(
    amount: float,
    business_unit: str,
    action: str,
    description: str = ""
) -> tuple[bool, float]:
    """
    Secure cash balance update with transaction logging and type safety.
    
    Args:
        amount: Positive number to modify
        business_unit: 'Unit A' or 'Unit B'
        action: 'add' or 'subtract'
        description: Optional transaction note
    
    Returns:
        (success status, new balance)
    """
    try:
        # Validate inputs
        amount = float(amount)
        if amount <= 0:
            raise ValueError("Amount must be positive")
        if business_unit not in ['Unit A', 'Unit B']:
            raise ValueError("Invalid business unit")
        
        # Get current balance
        response = supabase.table("cash_balances")\
                         .select("balance")\
                         .eq("business_unit", business_unit)\
                         .execute()
        current_balance = float(response.data[0]['balance']) if response.data else 0.0
        
        # Calculate new balance
        if action == 'subtract':
            if current_balance < amount:
                raise ValueError("Insufficient funds")
            new_balance = current_balance - amount
        elif action == 'add':
            new_balance = current_balance + amount
        else:
            raise ValueError("Invalid action")
        
        # Update database
        update_response = supabase.table("cash_balances")\
                                .upsert({
                                    "business_unit": business_unit,
                                    "balance": new_balance,
                                    "last_updated": datetime.now().isoformat()
                                }).execute()
        
        if not update_response.data:
            raise RuntimeError("Supabase update failed")
        
        # Log transaction
        supabase.table("cash_transactions").insert({
            "business_unit": business_unit,
            "amount": amount,
            "action": action,
            "description": description,
            "timestamp": datetime.now().isoformat(),
            "new_balance": new_balance
        }).execute()
        
        # Update session state
        st.session_state.cash_balance[business_unit] = new_balance
        return True, new_balance
        
    except Exception as e:
        st.error(f"Cash update failed: {str(e)}")
        return False, current_balance

def reset_session_state(hard_reset: bool = False) -> None:
    """
    Reset session state with optional Supabase data wipe.
    
    Args:
        hard_reset: If True, clears all Supabase data (dangerous)
    """
    try:
        if hard_reset:
            if not st.session_state.get('confirmed_reset', False):
                st.warning("This will delete ALL data. Type 'CONFIRM RESET' to proceed.")
                confirmation = st.text_input("Confirmation:")
                if confirmation.strip().upper() == "CONFIRM RESET":
                    st.session_state.confirmed_reset = True
                    st.rerun()
                return
            
            # Delete all data (except schema)
            tables = ["inventory", "investments", "expenses", "partnerships", "cash_balances"]
            for table in tables:
                supabase.table(table).delete().neq("id", 0).execute()
            
            initialize_default_data()
            st.success("Database reset complete!")
            time.sleep(2)
        
        # Refresh session
        st.session_state.clear()
        initialize_session_state()
        st.experimental_rerun()
        
    except Exception as e:
        st.error(f"Reset failed: {str(e)}")

# Auto-refresh logic (run in main app)
def check_data_freshness() -> None:
    """Auto-refresh data if stale (>5 minutes old)."""
    if 'last_updated' not in st.session_state:
        return
    
    if datetime.now() - st.session_state.last_updated > timedelta(minutes=5):
        refresh_all_data()

# Example usage
if __name__ == "__main__":
    initialize_session_state()
    
    st.title("Session State Manager")
    st.write("Current Inventory:", st.session_state.inventory)
    st.write("Cash Balances:", st.session_state.cash_balance)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Refresh Data"):
            refresh_all_data()
    with col2:
        if st.button("Soft Reset"):
            reset_session_state(hard_reset=False)
    
    if st.checkbox("Show dangerous options"):
        if st.button("Hard Reset (Wipes ALL Data)", type="primary"):
            reset_session_state(hard_reset=True)
