import streamlit as st
from supabase import create_client
from datetime import date
import time

# Initialize Supabase client
SUPABASE_URL = "https://umtgkoogrtvyqcrzygoe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVtdGdrb29ncnR2eXFjcnp5Z29lIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDUxMzYyNDYsImV4cCI6MjA2MDcxMjI0Nn0.QMrKSOa91fzE7sNWBfhePhRFG05YMwNbvHYK8Fzkjpk"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def hard_reset_database():
    """Completely reset the database while preserving users"""
    try:
        # Tables to reset (based on your actual table names)
        tables = [
            "partnerships",
            "investments",
            "expenses",
            "inventory",
            "market_prices",
            "cash_balances"
        ]
        
        # Delete all data from tables
        for table in tables:
            try:
                # First count existing records
                data = supabase.table(table).select("*").execute()
                count = len(data.data)
                
                if count > 0:
                    # Delete all records
                    supabase.table(table).delete().neq('id', 0).execute()
                    st.success(f"✅ Deleted {count} records from {table}")
                else:
                    st.info(f"ℹ️ No data found in {table}")
                time.sleep(0.3)  # Small delay between operations
            except Exception as e:
                st.error(f"❌ Error resetting {table}: {str(e)}")
                return False
        
        # Reset cash balances to 10,000 for both units
        supabase.table("cash_balances").upsert([
            {"business_unit": "Unit A", "balance": 10000.0},
            {"business_unit": "Unit B", "balance": 10000.0}
        ]).execute()
        st.success("✅ Reset cash balances to 10,000")
        
        # Add default market price
        supabase.table("market_prices").insert({
            "price": 50.0,
            "date": date.today().isoformat()
        }).execute()
        st.success("✅ Added default market price")
        
        return True
        
    except Exception as e:
        st.error(f"❌ Critical error during reset: {str(e)}")
        return False

# Streamlit UI
st.title("Supabase Database Hard Reset")
st.warning("🚨 THIS WILL DELETE MOST DATA IN YOUR DATABASE!")
st.warning("Only user accounts will be preserved")

if st.button("Show Current Data"):
    st.subheader("Current Database Status")
    try:
        tables = ["users", "inventory", "investments", 
                 "expenses", "cash_balances", "market_prices"]
        for table in tables:
            data = supabase.table(table).select("*").execute()
            st.write(f"{table}: {len(data.data)} records")
            if table == "cash_balances":
                for item in data.data:
                    st.write(f"  - {item['business_unit']}: {item['balance']}")
    except Exception as e:
        st.error(f"Error fetching data: {str(e)}")

# Reset confirmation
st.subheader("Database Reset")
confirmation = st.text_input("To confirm, type 'RESET MY DATA'")

if st.button("Execute Reset"):
    if confirmation.strip().upper() == "RESET MY DATA":
        with st.spinner("Performing hard reset..."):
            if hard_reset_database():
                st.balloons()
                st.success("🎉 Database reset completed successfully!")
                time.sleep(2)
                st.rerun()
            else:
                st.error("Reset failed - check error messages above")
    else:
        st.error("Please type exactly 'RESET MY DATA' to confirm")