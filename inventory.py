import streamlit as st
import pandas as pd
from datetime import date, datetime
from supabase import create_client
from utils import fetch_cash_balance, update_cash_balance, calculate_inventory_value

# Initialize Supabase client
SUPABASE_URL = "https://umtgkoogrtvyqcrzygoe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVtdGdrb29ncnR2eXFjcnp5Z29lIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDUxMzYyNDYsImV4cCI6MjA2MDcxMjI0Nn0.QMrKSOa91fzE7sNWBfhePhRFG05YMwNbvHYK8Fzkjpk"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def has_permission(user, feature):
    """Check if user has permission for a feature"""
    permissions = {
        "admin": ["dashboard", "inventory", "investments", "expenses", 
                 "partnership", "reports", "user_management"],
        "manager": ["dashboard", "inventory", "investments", "expenses", 
                   "partnership", "reports"],
        "user": ["dashboard", "inventory", "expenses"]
    }
    return feature in permissions.get(user.get("role", ""), [])

def initialize_cash_balances():
    """Initialize cash balances for all business units."""
    try:
        if 'cash_balance' not in st.session_state:
            st.session_state.cash_balance = {
                "Unit A": fetch_cash_balance("Unit A"),
                "Unit B": fetch_cash_balance("Unit B")
            }
    except Exception as e:
        st.error(f"Failed to initialize cash balances: {str(e)}")

def fetch_inventory(business_unit=None):
    """Fetch inventory data from Supabase with type conversion"""
    try:
        query = supabase.table("inventory").select("*")
        if business_unit:
            query = query.eq("business_unit", business_unit)
        response = query.execute()
        
        if not response.data:
            return pd.DataFrame(columns=[
                'date', 'transaction_type', 'quantity_kg', 'unit_price',
                'total_amount', 'remarks', 'business_unit'
            ])
        
        df = pd.DataFrame(response.data)
        
        # Convert numeric columns
        numeric_cols = ['quantity_kg', 'unit_price', 'total_amount']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        return df
        
    except Exception as e:
        st.error(f"Failed to load inventory: {str(e)}")
        return pd.DataFrame(columns=[
            'date', 'transaction_type', 'quantity_kg', 'unit_price',
            'total_amount', 'remarks', 'business_unit'
        ])

def refresh_inventory_data(business_unit=None):
    """Force refresh inventory data and update session state"""
    try:
        st.session_state.inventory = fetch_inventory(business_unit)
        st.session_state.last_updated = datetime.now()
    except Exception as e:
        st.error(f"Refresh failed: {str(e)}")

def show_transaction_form(transaction_type: str, business_unit: str):
    """Show form for purchase/sale transactions with proper balance handling."""
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
        
        total_amount = round(quantity_kg * unit_price, 2)
        st.write(f"Total Amount: AED {total_amount:,.2f}")
        
        if st.form_submit_button(f"Record {transaction_type}"):
            try:
                # Validate inputs
                if quantity_kg <= 0 or unit_price <= 0:
                    st.error("Quantity and price must be positive values")
                    return
                
                # Record inventory transaction first
                inventory_success = add_inventory_record(
                    transaction_type=transaction_type,
                    business_unit=business_unit,
                    date_transaction=date_transaction,
                    quantity_kg=quantity_kg,
                    unit_price=unit_price,
                    remarks=remarks
                )
                
                if not inventory_success:
                    raise ValueError("Failed to record inventory transaction")
                
                # Handle cash balance AFTER successful inventory record
                if transaction_type == "Purchase":
                    if not update_cash_balance(total_amount, business_unit, 'subtract'):
                        # Rollback inventory if balance update fails
                        supabase.table("inventory")\
                            .delete()\
                            .eq("date", date_transaction.isoformat())\
                            .eq("business_unit", business_unit)\
                            .eq("remarks", remarks)\
                            .execute()
                        st.error(f"Insufficient funds in {business_unit}")
                        return
                elif transaction_type == "Sale":
                    update_cash_balance(total_amount, business_unit, 'add')
                
                st.success(f"{transaction_type} recorded successfully!")
                refresh_inventory_data(business_unit)
                st.rerun()
                    
            except Exception as e:
                st.error(f"Transaction failed: {str(e)}")

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
        total_amount = round(quantity_kg * unit_price, 2)
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
        
        # Initialize data
        initialize_cash_balances()
        if 'inventory' not in st.session_state:
            refresh_inventory_data()
        
        st.title("📦 Inventory Management")
        
        # Determine which units to show
        units = ["Unit A", "Unit B"] if user['business_unit'] == 'All' else [user['business_unit']]
        
        # Create tabs for each business unit
        unit_tabs = st.tabs(units)
        
        for i, unit in enumerate(units):
            with unit_tabs[i]:
                # Current stock status
                st.subheader(f"{unit} Inventory Status")
                
                cols = st.columns(3)
                with cols[0]:
                    st.metric("Cash Balance", f"AED {st.session_state.cash_balance.get(unit, 0):,.2f}")
                
                # Calculate and display current stock
                try:
                    stock, value = calculate_inventory_value(unit)
                    with cols[1]:
                        st.metric("Current Stock", f"{stock:,.2f} kg")
                    with cols[2]:
                        st.metric("Inventory Value", f"AED {value:,.2f}")
                except Exception as e:
                    st.error(f"Calculation error: {str(e)}")
                
                # Refresh button
                if st.button("🔄 Refresh Data", key=f"refresh_{unit}"):
                    refresh_inventory_data(unit)
                    st.rerun()
                
                # Purchase/Sale subtabs
                tab1, tab2 = st.tabs(["📥 Purchase", "📤 Sale"])
                
                with tab1:
                    show_transaction_form("Purchase", unit)
                
                with tab2:
                    show_transaction_form("Sale", unit)
                
                # Recent transactions
                st.subheader(f"Transaction History - {unit}")
                inventory_data = st.session_state.inventory[
                    st.session_state.inventory['business_unit'] == unit
                ].copy()
                
                if not inventory_data.empty:
                    # Format display columns
                    display_cols = ['date', 'transaction_type', 'quantity_kg', 
                                  'unit_price', 'total_amount', 'remarks']
                    inventory_data = inventory_data[display_cols]
                    
                    # Convert to proper types
                    inventory_data['quantity_kg'] = inventory_data['quantity_kg'].astype(float)
                    inventory_data['unit_price'] = inventory_data['unit_price'].astype(float)
                    inventory_data['total_amount'] = inventory_data['total_amount'].astype(float)
                    
                    # Display table
                    st.dataframe(
                        inventory_data.sort_values('date', ascending=False),
                        column_config={
                            "date": "Date",
                            "transaction_type": "Type",
                            "quantity_kg": st.column_config.NumberColumn(
                                "Quantity (kg)", 
                                format="%.3f kg"
                            ),
                            "unit_price": st.column_config.NumberColumn(
                                "Unit Price", 
                                format="AED %.2f"
                            ),
                            "total_amount": st.column_config.NumberColumn(
                                "Total Amount", 
                                format="AED %.2f"
                            ),
                            "remarks": "Details"
                        },
                        hide_index=True,
                        use_container_width=True,
                        height=400
                    )
                    
                    # Debug section (can be removed in production)
                    with st.expander("🔍 Debug View"):
                        st.write("Purchase Total:", inventory_data[
                            inventory_data['transaction_type']=='Purchase'
                        ]['quantity_kg'].sum(), "kg")
                        st.write("Sale Total:", inventory_data[
                            inventory_data['transaction_type']=='Sale'
                        ]['quantity_kg'].sum(), "kg")
                else:
                    st.info("No transactions found for this unit")

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    show_inventory()
