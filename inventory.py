import streamlit as st
import pandas as pd
from datetime import date
from supabase import create_client
from utils import fetch_cash_balance, update_cash_balance  # Import centralized cash balance functions

# Initialize Supabase client
SUPABASE_URL = "https://umtgkoogrtvyqcrzygoe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVtdGdrb29ncnR2eXFjcnp5Z29lIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDUxMzYyNDYsImV4cCI6MjA2MDcxMjI0Nn0.QMrKSOa91fzE7sNWBfhePhRFG05YMwNbvHYK8Fzkjpk"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def initialize_cash_balances():
    """Initialize cash balances for all business units."""
    try:
        cash_balances = fetch_cash_balance()
        if 'cash_balance' not in st.session_state:
            st.session_state.cash_balance = cash_balances
    except Exception as e:
        st.error(f"Failed to initialize cash balances: {str(e)}")

def fetch_inventory(business_unit=None):
    """Fetch inventory data from Supabase."""
    try:
        query = supabase.table("inventory").select("*")
        if business_unit:
            query = query.eq("business_unit", business_unit)
        response = query.execute()
        return pd.DataFrame(response.data) if response.data else pd.DataFrame(columns=[
            'date', 'transaction_type', 'quantity_kg', 'unit_price',
            'total_amount', 'remarks', 'business_unit', 'created_at'
        ])
    except Exception as e:
        st.error(f"Failed to load inventory: {str(e)}")
        return pd.DataFrame(columns=[
            'date', 'transaction_type', 'quantity_kg', 'unit_price',
            'total_amount', 'remarks', 'business_unit', 'created_at'
        ])

def show_transaction_form(transaction_type: str, business_unit: str):
    """Show form for purchase/sale transactions."""
    with st.form(f"{transaction_type}_form_{business_unit}", clear_on_submit=True):
        st.subheader(f"New {transaction_type} - {business_unit}")
        
        cols = st.columns(2)
        with cols[0]:
            date_transaction = st.date_input("Date", value=date.today())
            quantity_kg = st.number_input(
                "Quantity (kg)", 
                min_value=0.001, 
                step=0.001, 
                format="%.3f"
            )
        with cols[1]:
            unit_price = st.number_input(
                "Price per kg (AED)", 
                min_value=0.01, 
                step=0.01
            )
            remarks = st.text_input(
                "Supplier" if transaction_type == "Purchase" else "Customer",
                max_chars=100
            )
        
        total_amount = quantity_kg * unit_price
        st.write(f"Total Amount: AED {total_amount:,.2f}")
        
        if st.form_submit_button(f"Record {transaction_type}"):
            # Validate inputs
            if quantity_kg <= 0 or unit_price <= 0:
                st.error("Quantity and price must be positive values")
                return
            
            # Handle cash balance for purchases
            if transaction_type == "Purchase":
                if not update_cash_balance(total_amount, business_unit, 'subtract'):
                    st.error(f"Insufficient funds in {business_unit}")
                    return
            
            # Handle cash balance for sales
            elif transaction_type == "Sale":
                update_cash_balance(total_amount, business_unit, 'add')
            
            # Record the transaction in the database
            if add_inventory_record(
                transaction_type=transaction_type,
                business_unit=business_unit,
                date_transaction=date_transaction,
                quantity_kg=quantity_kg,
                unit_price=unit_price,
                remarks=remarks
            ):
                st.success(f"{transaction_type} recorded successfully!")
                st.rerun()

def add_inventory_record(
    transaction_type: str,
    business_unit: str,
    date_transaction: date,
    quantity_kg: float,
    unit_price: float,
    remarks: str
) -> bool:
    """Add a new inventory transaction to Supabase."""
    try:
        total_amount = quantity_kg * unit_price
        response = supabase.table("inventory").insert({
            "date": date_transaction.isoformat(),
            "transaction_type": transaction_type,
            "quantity_kg": quantity_kg,
            "unit_price": unit_price,
            "total_amount": total_amount,
            "remarks": remarks,
            "business_unit": business_unit
        }).execute()
        return bool(response.data)
    except Exception as e:
        st.error(f"Failed to record transaction: {str(e)}")
        return False

def show_inventory():
    """Main inventory management interface."""
    try:
        # Authentication check
        if 'user' not in st.session_state:
            st.error("Please log in to access inventory")
            return
            
        user = st.session_state.user
        if not has_permission(user, 'inventory'):
            st.error("You don't have permission to access this page")
            return
        
        # Initialize cash balances
        initialize_cash_balances()
        
        st.title("📦 Inventory Management")
        
        # Determine which units to show
        if user['business_unit'] == 'All':
            units = ["Unit A", "Unit B"]
        else:
            units = [user['business_unit']]
        
        # Create tabs for each business unit
        unit_tabs = st.tabs(units)
        for i, unit in enumerate(units):
            with unit_tabs[i]:
                # Purchase/Sale subtabs
                tab1, tab2 = st.tabs(["Purchase", "Sale"])
                
                with tab1:
                    show_transaction_form("Purchase", unit)
                
                with tab2:
                    show_transaction_form("Sale", unit)
                
                # Show recent transactions
                st.subheader(f"Recent Transactions - {unit}")
                inventory_data = fetch_inventory(unit)
                if not inventory_data.empty:
                    st.dataframe(
                        inventory_data.sort_values('date', ascending=False).head(10),
                        column_config={
                            "date": "Date",
                            "transaction_type": "Type",
                            "quantity_kg": "Quantity (kg)",
                            "unit_price": "Unit Price (AED)",
                            "total_amount": "Total Amount (AED)",
                            "remarks": "Details"
                        },
                        hide_index=True
                    )
                else:
                    st.info("No transactions found for this unit")

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    show_inventory()
