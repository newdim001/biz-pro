import streamlit as st
from supabase import create_client

# Initialize Supabase client
SUPABASE_URL = "https://umtgkoogrtvyqcrzygoe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVtdGdrb29ncnR2eXFjcnp5Z29lIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDUxMzYyNDYsImV4cCI6MjA2MDcxMjI0Nn0.QMrKSOa91fzE7sNWBfhePhRFG05YMwNbvHYK8Fzkjpk"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def initialize_cash_balances():
    """Initialize default cash balances if they don't exist"""
    business_units = ["Unit A", "Unit B"]
    default_balance = 10000.0
    
    try:
        for unit in business_units:
            response = supabase.table("cash_balances")\
                             .select("*")\
                             .eq("business_unit", unit)\
                             .execute()
            
            if not response.data:
                # Insert initial balance
                supabase.table("cash_balances").insert({
                    "business_unit": unit,
                    "balance": default_balance
                }).execute()
                    
    except Exception as e:
        st.error(f"Balance initialization error: {str(e)}")

def fetch_cash_balance(business_unit: str) -> float:
    """Get current cash balance for a business unit"""
    try:
        response = supabase.table("cash_balances")\
                         .select("balance")\
                         .eq("business_unit", business_unit)\
                         .execute()
        
        if response.data:
            return float(response.data[0]["balance"])
        return 10000.0  # Default balance if not found
    except Exception as e:
        st.error(f"Failed to fetch balance: {str(e)}")
        return 10000.0

def update_cash_balance(amount: float, business_unit: str, action: str) -> bool:
    """
    Update cash balance after validating sufficient funds
    Simplified version without last_updated column dependency
    """
    try:
        current_balance = fetch_cash_balance(business_unit)
        
        if action == 'subtract':
            if current_balance < amount:
                st.error(f"Insufficient funds in {business_unit}")
                return False
            new_balance = current_balance - amount
        else:  # 'add'
            new_balance = current_balance + amount
        
        # Simple upsert without last_updated
        supabase.table("cash_balances").upsert({
            "business_unit": business_unit,
            "balance": new_balance
        }).execute()
        
        return True
    except Exception as e:
        st.error(f"Failed to update balance: {str(e)}")
        return False
