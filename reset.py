import streamlit as st
from supabase import create_client
from datetime import date
import time

# Initialize Supabase client
SUPABASE_URL = "https://umtgkoogrtvyqcrzygoe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVtdGdrb29ncnR2eXFjcnp5Z29lIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDUxMzYyNDYsImV4cCI6MjA2MDcxMjI0Nn0.QMrKSOa91fzE7sNWBfhePhRFG05YMwNbvHYK8Fzkjpk"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def reset_supabase_database():
    """Reset database while preserving users and setting cash balances to 10,000"""
    st.warning("🚨 This will DELETE MOST DATA in your Supabase database!")
    st.warning("Users will be preserved and cash balances set to 10,000")
    
    confirmation = st.text_input("Type 'RESET ALL' to confirm")
    if confirmation != "RESET ALL":
        return False
    
    with st.spinner("Resetting database..."):
        try:
            # List of tables to reset (excluding users)
            tables_to_reset = [
                "partnerships",
                "investments",
                "expenses",
                "inventory",
                "market_prices",
                "sessions"
            ]
            
            # Delete all data from tables (except users)
            for table in tables_to_reset:
                try:
                    supabase.table(table).delete().neq('id', 0).execute()
                    time.sleep(0.5)  # Add small delay between operations
                except Exception as e:
                    st.error(f"Error resetting {table}: {str(e)}")
                    return False
            
            # Set cash balances to 10,000 for both units
            supabase.table("cash_balances").upsert([
                {"business_unit": "Unit A", "balance": 10000.0},
                {"business_unit": "Unit B", "balance": 10000.0}
            ]).execute()
            
            # Initialize default market price
            supabase.table("market_prices").insert({
                "price": 50.0,
                "date": date.today().isoformat()
            }).execute()
            
            st.success("✅ Database reset successfully!")
            time.sleep(2)
            return True
            
        except Exception as e:
            st.error(f"Failed to reset database: {str(e)}")
            return False

# Streamlit UI for the reset tool
st.title("Supabase Database Reset Tool")
st.markdown("""
This tool will reset your Supabase database while:
- Preserving all user accounts
- Setting both business units' cash balances to 10,000
- Resetting all other tables to empty
""")

if st.button("Initialize Reset"):
    if reset_supabase_database():
        st.balloons()
    else:
        st.error("Reset failed or was cancelled")

# Show current status
st.markdown("### Current Database Status")
try:
    user_count = len(supabase.table("users").select("*").execute().data)
    cash_balance = supabase.table("cash_balances").select("*").execute().data
    st.write(f"Users: {user_count} accounts")
    for unit in cash_balance:
        st.write(f"{unit['business_unit']} cash balance: {unit['balance']}")
except Exception as e:
    st.error(f"Could not fetch database status: {str(e)}")