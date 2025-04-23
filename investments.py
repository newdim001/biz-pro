import streamlit as st
import pandas as pd
from datetime import date
from supabase import create_client
from components.auth import has_permission  # Import the has_permission function

# Initialize Supabase client
SUPABASE_URL = "https://umtgkoogrtvyqcrzygoe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVtdGdrb29ncnR2eXFjcnp5Z29lIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDUxMzYyNDYsImV4cCI6MjA2MDcxMjI0Nn0.QMrKSOa91fzE7sNWBfhePhRFG05YMwNbvHYK8Fzkjpk"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def initialize_cash_balances():
    """
    Initialize the cash_balances table with default balances for business units.
    This ensures that every business unit has a starting balance.
    """
    business_units = ["Unit A", "Unit B"]
    default_balance = 10000.0  # Default initial balance
    
    for unit in business_units:
        response = supabase.table("cash_balances").select("*").eq("business_unit", unit).execute()
        if not response.data:  # If no record exists for the business unit
            print(f"Initializing cash balance for {unit} with default: {default_balance}")
            supabase.table("cash_balances").insert({
                "business_unit": unit,
                "balance": default_balance
            }).execute()

def fetch_cash_balance(business_unit):
    """Fetch the current cash balance for a business unit from Supabase"""
    response = supabase.table("cash_balances").select("balance").eq("business_unit", business_unit).execute()
    if response.data:
        balance = float(response.data[0]["balance"])  # Ensure numeric type
        print(f"Fetched balance for {business_unit}: {balance}")  # Log the balance
        return balance
    print(f"No balance found for {business_unit}, returning default: 10000.0")
    return 10000.0  # Default initial balance if no record exists

def update_cash_balance(amount, business_unit, action):
    """
    Updates the cash balance for a business unit in Supabase.
    
    Parameters:
        amount (float): The amount to add/subtract.
        business_unit (str): The business unit ('Unit A', 'Unit B', etc.).
        action (str): 'add' or 'subtract'.
    
    Returns:
        bool: True if the update was successful, False otherwise.
    """
    current_balance = fetch_cash_balance(business_unit)
    print(f"Current balance for {business_unit}: {current_balance}")
    
    if action == 'subtract':
        if current_balance < amount:
            print(f"Insufficient balance: {current_balance} < {amount}")
            return False  # Insufficient balance
        new_balance = current_balance - amount
    elif action == 'add':
        new_balance = current_balance + amount
    
    # Update or insert the new balance in Supabase
    response = supabase.table("cash_balances").select("*").eq("business_unit", business_unit).execute()
    if response.data:
        # Update existing record
        supabase.table("cash_balances").update({"balance": new_balance}).eq("business_unit", business_unit).execute()
    else:
        # Insert new record
        supabase.table("cash_balances").insert({"business_unit": business_unit, "balance": new_balance}).execute()
    
    print(f"Updated balance for {business_unit}: {new_balance}")
    return True

def fetch_investments():
    """Fetch all investments from Supabase"""
    try:
        response = supabase.table("investments").select("*").execute()
        if not response.data:
            return pd.DataFrame(columns=["business_unit", "inv_date", "amount", "investor", "description"])
        return pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"Error fetching investments: {str(e)}")
        return pd.DataFrame(columns=["business_unit", "inv_date", "amount", "investor", "description"])

def add_investment(unit, inv_date, amount, investor, description):
    """Add a new investment to Supabase and update the cash balance"""
    try:
        # Update the cash balance for the business unit
        cash_updated = update_cash_balance(amount, unit, 'add')
        if not cash_updated:
            st.error(f"Failed to update cash balance for {unit}. Investment not recorded.")
            return False
        
        # Add the investment record to the database
        response = supabase.table("investments").insert({
            "business_unit": unit,
            "inv_date": inv_date.isoformat(),
            "amount": amount,
            "investor": investor,
            "description": description
        }).execute()
        return True if response else False
    except Exception as e:
        st.error(f"Error adding investment: {str(e)}")
        return False

def show_investments():
    """Complete investment management interface"""
    user = st.session_state.get('user')
    if not user or not has_permission(user, 'investments'):  # Check user permissions
        st.error("Permission denied")
        return
    
    # Initialize cash balances table
    initialize_cash_balances()
    
    # Fetch existing investments from Supabase
    investments_data = fetch_investments()
    
    # Ensure 'business_unit' column exists
    if 'business_unit' not in investments_data.columns:
        st.error("Critical error: 'business_unit' column is missing from the investments table.")
        return
    
    st.session_state.investments = investments_data
    
    st.header("💼 Investment Management")
    
    units = []
    if user['business_unit'] in ['All', 'Unit A']:
        units.append('Unit A')
    if user['business_unit'] in ['All', 'Unit B']:
        units.append('Unit B')
    
    tabs = st.tabs(units)
    
    for i, unit in enumerate(units):
        with tabs[i]:
            with st.form(f"invest_form_{unit}", clear_on_submit=True):
                st.subheader(f"New Investment - {unit}")
                
                cols = st.columns(2)
                with cols[0]:
                    inv_date = st.date_input("Date*", value=date.today())
                    amount = st.number_input(
                        "Amount (AED)*", 
                        min_value=1.0,
                        step=100.0,
                        value=1000.0,
                        format="%.2f"
                    )
                with cols[1]:
                    investor = st.text_input("Investor*", placeholder="Name/Company")
                    desc = st.text_input("Description", placeholder="Purpose")
                
                if st.form_submit_button("Record Investment"):
                    if not investor:
                        st.error("Investor name required")
                    elif amount <= 0:
                        st.error("Investment amount must be greater than zero")
                    else:
                        # Add new investment to Supabase
                        success = add_investment(
                            unit=unit,
                            inv_date=inv_date,
                            amount=amount,
                            investor=investor,
                            description=desc or f"Investment from {investor}"
                        )
                        if success:
                            st.success(f"✅ AED {amount:,.2f} invested in {unit}")
                            st.rerun()
                        else:
                            st.error("Failed to record investment")
            
            st.subheader(f"📋 {unit} Investment History")
            if 'investments' in st.session_state:
                unit_inv = st.session_state.investments[
                    st.session_state.investments['business_unit'] == unit
                ]
                
                # Filter to display only the required columns
                unit_inv = unit_inv[["business_unit", "inv_date", "amount", "investor", "description"]]
                
                if not unit_inv.empty:
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.dataframe(
                            unit_inv.sort_values('inv_date', ascending=False).style.format({
                                'amount': 'AED {:,.2f}',
                                'inv_date': lambda x: pd.to_datetime(x).strftime('%Y-%m-%d')
                            }),
                            height=300,
                            use_container_width=True
                        )
                    with col2:
                        total = unit_inv['amount'].sum()
                        last = unit_inv.iloc[-1]
                        st.metric("Total Invested", f"AED {total:,.2f}")
                        st.metric("Last Investment", 
                                 f"AED {last['amount']:,.2f}", 
                                 last['investor'])
                    
                    csv = unit_inv.to_csv(index=False)
                    st.download_button(
                        "📥 Export CSV",
                        data=csv,
                        file_name=f"{unit}_investments.csv",
                        mime="text/csv"
                    )
                else:
                    st.info("No investments recorded")
            else:
                st.info("No investments recorded")

if __name__ == "__main__":
    show_investments()