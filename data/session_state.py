import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
import time

# Initialize Supabase client with error handling
try:
    SUPABASE_URL = "https://umtgkoogrtvyqcrzygoe.supabase.co"
    SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVtdGdrb29ncnR2eXFjcnp5Z29lIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDUxMzYyNDYsImV4cCI6MjA2MDcxMjI0Nn0.QMrKSOa91fzE7sNWBfhePhRFG05YMwNbvHYK8Fzkjpk"
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"Failed to initialize Supabase client: {str(e)}")
    st.stop()

# Default data structures
DEFAULT_INVENTORY_COLS = [
    'Date', 'Transaction Type', 'Quantity_kg', 
    'Unit Price', 'Total Amount', 'Remarks', 'Business Unit'
]
DEFAULT_INVESTMENTS_COLS = [
    'Date', 'Amount', 'Investor', 'Remarks', 'Business Unit'
]
DEFAULT_EXPENSES_COLS = [
    'Date', 'Category', 'Amount', 'Description', 'Business Unit', 'Partner'
]
DEFAULT_PARTNERSHIP_COLS = ['Partner', 'Share', 'Withdrawn']

def initialize_default_data(business_units=['Unit A', 'Unit B']):
    """Initialize default data in Supabase tables"""
    try:
        # Initialize cash balances if empty
        cash_response = supabase.table("cash_balances").select("*").execute()
        if not cash_response.data:
            for unit in business_units:
                supabase.table("cash_balances").upsert({
                    "business_unit": unit,
                    "balance": 0.0
                }).execute()
        
        # Initialize other tables with empty DataFrames if they don't exist
        tables = {
            "inventory": DEFAULT_INVENTORY_COLS,
            "investments": DEFAULT_INVESTMENTS_COLS,
            "expenses": DEFAULT_EXPENSES_COLS,
            "partnerships": DEFAULT_PARTNERSHIP_COLS + ['business_unit']
        }
        
        for table, cols in tables.items():
            response = supabase.table(table).select("*").limit(1).execute()
            if not response.data:
                # Table exists but is empty - no need to initialize structure
                pass
                
    except Exception as e:
        st.error(f"Error initializing default data: {str(e)}")

def initialize_session_state():
    """Initialize or refresh session state from Supabase"""
    try:
        if 'initialized' not in st.session_state:
            st.session_state.initialized = False
            
        # Initialize with loading indicator
        with st.spinner("Loading application data..."):
            # Fetch all data in parallel where possible
            inventory_response = supabase.table("inventory").select("*").execute()
            cash_balance_response = supabase.table("cash_balances").select("*").execute()
            investments_response = supabase.table("investments").select("*").execute()
            expenses_response = supabase.table("expenses").select("*").execute()
            partnerships_response = supabase.table("partnerships").select("*").execute()
            
            # Process inventory data
            st.session_state.inventory = pd.DataFrame(
                inventory_response.data if inventory_response.data else [],
                columns=DEFAULT_INVENTORY_COLS
            )
            
            # Process cash balances
            st.session_state.cash_balance = {
                row['business_unit']: row['balance'] 
                for row in cash_balance_response.data
            } if cash_balance_response.data else {unit: 0.0 for unit in ['Unit A', 'Unit B']}
            
            # Process investments
            st.session_state.investments = pd.DataFrame(
                investments_response.data if investments_response.data else [],
                columns=DEFAULT_INVESTMENTS_COLS
            )
            
            # Process expenses
            st.session_state.expenses = pd.DataFrame(
                expenses_response.data if expenses_response.data else [],
                columns=DEFAULT_EXPENSES_COLS
            )
            
            # Process partnerships
            if partnerships_response.data:
                st.session_state.partners = {
                    unit: pd.DataFrame([
                        p for p in partnerships_response.data 
                        if p['business_unit'] == unit
                    ]) for unit in ['Unit A', 'Unit B']
                }
            else:
                st.session_state.partners = {
                    unit: pd.DataFrame(columns=DEFAULT_PARTNERSHIP_COLS) 
                    for unit in ['Unit A', 'Unit B']
                }
            
            # Initialize current price
            st.session_state.current_price = 0.0
            
            # Mark initialization complete
            st.session_state.initialized = True
            st.session_state.last_updated = datetime.now()
            
    except Exception as e:
        st.error(f"Failed to initialize session: {str(e)}")
        st.session_state.initialized = False

def update_cash_balance(amount, business_unit, action, description=""):
    """
    Secure cash balance update with transaction logging
    
    Args:
        amount (float): Amount to modify
        business_unit (str): Target business unit
        action (str): 'add' or 'subtract'
        description (str): Optional transaction description
    
    Returns:
        tuple: (success: bool, new_balance: float)
    """
    try:
        # Validate inputs
        if not isinstance(amount, (int, float)) or amount <= 0:
            return False, 0.0
        if business_unit not in ['Unit A', 'Unit B']:
            return False, 0.0
        
        # Get current balance
        response = supabase.table("cash_balances")\
                         .select("balance")\
                         .eq("business_unit", business_unit)\
                         .execute()
        
        current_balance = response.data[0]['balance'] if response.data else 0.0
        
        # Calculate new balance
        if action == 'subtract':
            if current_balance < amount:
                return False, current_balance
            new_balance = current_balance - amount
        elif action == 'add':
            new_balance = current_balance + amount
        else:
            return False, current_balance
        
        # Update in database
        update_response = supabase.table("cash_balances")\
                                .upsert({
                                    "business_unit": business_unit,
                                    "balance": new_balance,
                                    "last_updated": datetime.now().isoformat()
                                }).execute()
        
        if update_response:
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
        
        return False, current_balance
        
    except Exception as e:
        st.error(f"Cash balance update failed: {str(e)}")
        return False, current_balance

def reset_session_state(hard_reset=False):
    """
    Reset session state with options
    
    Args:
        hard_reset (bool): If True, clears all data including cached Supabase data
    """
    try:
        if hard_reset:
            # Full reset including Supabase data
            st.warning("Performing full data reset...")
            
            # Get confirmation
            if not st.session_state.get('confirmed_reset', False):
                st.warning("This will delete ALL data. Type 'CONFIRM RESET' to proceed.")
                confirmation = st.text_input("Confirmation:")
                if confirmation.strip().upper() == "CONFIRM RESET":
                    st.session_state.confirmed_reset = True
                    st.rerun()
                return
            
            # Reset all tables
            tables = ["inventory", "investments", "expenses", "partnerships", "cash_balances"]
            for table in tables:
                supabase.table(table).delete().neq("id", 0).execute()
            
            # Reinitialize defaults
            initialize_default_data()
            st.success("All data has been reset to defaults!")
            time.sleep(2)
        
        # Clear and reinitialize session
        st.session_state.clear()
        initialize_session_state()
        st.experimental_rerun()
        
    except Exception as e:
        st.error(f"Reset failed: {str(e)}")

# Example usage
if __name__ == "__main__":
    initialize_session_state()
    
    # Example UI for testing
    st.write("Current Cash Balances:", st.session_state.cash_balance)
    
    if st.button("Refresh Data"):
        initialize_session_state()
        st.success("Data refreshed!")
    
    if st.button("Soft Reset"):
        reset_session_state(hard_reset=False)
    
    if st.button("Hard Reset (Dangerous)"):
        reset_session_state(hard_reset=True)