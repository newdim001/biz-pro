import streamlit as st
import pandas as pd
from datetime import date, datetime
from supabase import create_client
from components.auth import has_permission

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
            # Check if balance exists
            response = supabase.table("cash_balances")\
                             .select("*")\
                             .eq("business_unit", unit)\
                             .execute()
            
            if not response.data:
                # Insert initial balance
                supabase.table("cash_balances").insert({
                    "business_unit": unit,
                    "balance": default_balance,
                    "last_updated": datetime.now().isoformat()
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
    """Update cash balance after validating sufficient funds"""
    try:
        current_balance = fetch_cash_balance(business_unit)
        
        if action == 'subtract':
            if current_balance < amount:
                st.error(f"Insufficient funds in {business_unit}")
                return False
            new_balance = current_balance - amount
        else:  # 'add'
            new_balance = current_balance + amount
        
        # Update balance
        supabase.table("cash_balances").upsert({
            "business_unit": business_unit,
            "balance": new_balance,
            "last_updated": datetime.now().isoformat()
        }).execute()
        
        return True
    except Exception as e:
        st.error(f"Failed to update balance: {str(e)}")
        return False

def fetch_inventory(business_unit: str = None) -> pd.DataFrame:
    """Get inventory data for a specific unit or all units"""
    try:
        query = supabase.table("inventory").select("*")
        if business_unit:
            query = query.eq("business_unit", business_unit)
        response = query.execute()
        return pd.DataFrame(response.data) if response.data else pd.DataFrame()
    except Exception as e:
        st.error(f"Failed to load inventory: {str(e)}")
        return pd.DataFrame()

def add_inventory_record(
    transaction_type: str,
    business_unit: str,
    date_transaction: date,
    quantity_kg: float,
    unit_price: float,
    remarks: str
) -> bool:
    """Add a new inventory transaction"""
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

def show_transaction_form(transaction_type: str, business_unit: str):
    """Show form for purchase/sale transactions"""
    with st.form(f"{transaction_type}_form_{business_unit}", clear_on_submit=True):
        st.subheader(f"New {transaction_type} - {business_unit}")
        
        cols = st.columns(2)
        with cols[0]:
            date_transaction = st.date_input("Date", value=date.today())
            quantity_kg = st.number_input("Quantity (kg)", 
                                         min_value=0.001, 
                                         step=0.001, 
                                         format="%.3f")
        with cols[1]:
            unit_price = st.number_input("Price per kg (AED)", 
                                       min_value=0.01, 
                                       step=0.01)
            remarks = st.text_input("Supplier" if transaction_type == "Purchase" else "Customer",
                                  max_chars=100)
        
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
                    return
            
            # Handle cash balance for sales
            elif transaction_type == "Sale":
                update_cash_balance(total_amount, business_unit, 'add')
            
            # Record the transaction
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

def show_inventory():
    """Main inventory management interface"""
    try:
        # Authentication check
        if 'user' not in st.session_state:
            st.error("Please login to access inventory")
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