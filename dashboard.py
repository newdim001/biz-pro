import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from supabase import create_client
from utils import (
    init_supabase, fetch_inventory, fetch_expenses,
    fetch_cash_balances, fetch_latest_market_price,
    fetch_price_history, update_market_price,
    calculate_current_stock, calculate_inventory_value,
    calculate_profit_loss
)
from components.auth import has_permission

# Initialize Supabase client
@st.cache_resource
def init_supabase():
    SUPABASE_URL = "https://umtgkoogrtvyqcrzygoe.supabase.co"
    SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVtdGdrb29ncnR2eXFjcnp5Z29lIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDUxMzYyNDYsImV4cCI6MjA2MDcxMjI0Nn0.QMrKSOa91fzE7sNWBfhePhRFG05YMwNbvHYK8Fzkjpk"
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

# Data Fetching Functions
def fetch_inventory(business_unit=None):
    """Fetch inventory data from Supabase"""
    try:
        query = supabase.table("inventory").select("*")
        if business_unit:
            query = query.eq("business_unit", business_unit)
        response = query.execute()
        return pd.DataFrame(response.data) if response.data else pd.DataFrame()
    except Exception as e:
        st.error(f"Failed to load inventory: {str(e)}")
        return pd.DataFrame()

def fetch_expenses(business_unit=None):
    """Fetch expenses data from Supabase"""
    try:
        query = supabase.table("expenses").select("*")
        if business_unit:
            query = query.eq("business_unit", business_unit)
        response = query.execute()
        return pd.DataFrame(response.data) if response.data else pd.DataFrame()
    except Exception as e:
        st.error(f"Failed to load expenses: {str(e)}")
        return pd.DataFrame()

def fetch_cash_balances():
    """Fetch cash balances from Supabase"""
    try:
        response = supabase.table("cash_balances").select("*").execute()
        return {row['business_unit']: row['balance'] for row in response.data} if response.data else {}
    except Exception as e:
        st.error(f"Failed to load cash balances: {str(e)}")
        return {}

def fetch_latest_market_price():
    """Get the most recent market price"""
    try:
        response = supabase.table("market_prices").select("price, date").order("date", desc=True).limit(1).execute()
        if response.data:
            return float(response.data[0]['price']), datetime.fromisoformat(response.data[0]['date'])
    except Exception as e:
        st.error(f"Failed to load market price: {str(e)}")
    return 50.0, datetime.now()  # Fallback values

def fetch_price_history():
    """Get price history"""
    try:
        response = supabase.table("market_prices").select("price, date").order("date", desc=True).limit(30).execute()
        return pd.DataFrame(response.data) if response.data else pd.DataFrame()
    except Exception as e:
        st.error(f"Failed to load price history: {str(e)}")
        return pd.DataFrame()

# Data Update Functions
def update_market_price(new_price):
    """Update the current market price in Supabase"""
    try:
        response = supabase.table("market_prices").insert({
            "price": new_price,
            "date": datetime.now().isoformat()
        }).execute()
        return True if response else False
    except Exception as e:
        st.error(f"Price update failed: {str(e)}")
        return False

def update_cash_balance(amount, business_unit, action):
    """Update cash balance for a business unit"""
    try:
        current_balance = fetch_cash_balances().get(business_unit, 0.0)
        
        if action == 'subtract' and current_balance < amount:
            st.error(f"Insufficient balance in {business_unit}")
            return False
            
        new_balance = current_balance + (amount if action == 'add' else -amount)
        
        response = supabase.table("cash_balances").upsert({
            "business_unit": business_unit,
            "balance": new_balance
        }, on_conflict="business_unit").execute()
        
        return True if response else False
    except Exception as e:
        st.error(f"Balance update failed: {str(e)}")
        return False

# Dashboard Metrics
def get_system_summary():
    """Calculate system-wide metrics"""
    cash_balances = fetch_cash_balances()
    inventory = fetch_inventory()
    expenses = fetch_expenses()
    
    # Separate purchases and sales
    purchases = inventory[inventory['transaction_type'] == 'Purchase'] if not inventory.empty else pd.DataFrame(columns=inventory.columns)
    sales = inventory[inventory['transaction_type'] == 'Sale'] if not inventory.empty else pd.DataFrame(columns=inventory.columns)
    
    current_stock = calculate_current_stock(None)  # None returns system-wide stock
    current_market_price, _ = fetch_latest_market_price()
    current_inventory_value = current_stock * current_market_price
    
    inventory_value_purchase_price = ((purchases['quantity_kg'] * purchases['unit_price']).sum() if not purchases.empty else 0.0) - \
                                    ((sales['quantity_kg'] * sales['unit_price']).sum() if not sales.empty else 0.0)
    
    return {
        "Total Cash": sum(cash_balances.values()) if cash_balances else 0.0,
        "Current Inventory Value": current_inventory_value,
        "Inventory Value (Purchase Price)": inventory_value_purchase_price,
        "Current Stock": current_stock,
        "Total Expenses": expenses['amount'].sum() if not expenses.empty else 0.0
    }

def get_business_unit_summary(unit):
    """Calculate metrics for a specific unit"""
    cash_balance = fetch_cash_balances().get(unit, 0.0)
    inventory = fetch_inventory(unit)
    expenses = fetch_expenses(unit)
    
    # Separate purchases and sales
    purchases = inventory[inventory['transaction_type'] == 'Purchase'] if not inventory.empty else pd.DataFrame(columns=inventory.columns)
    sales = inventory[inventory['transaction_type'] == 'Sale'] if not inventory.empty else pd.DataFrame(columns=inventory.columns)
    
    current_stock = calculate_current_stock(unit)
    current_market_price, _ = fetch_latest_market_price()
    current_inventory_value = current_stock * current_market_price
    
    inventory_value_purchase_price = ((purchases['quantity_kg'] * purchases['unit_price']).sum() if not purchases.empty else 0.0) - \
                                    ((sales['quantity_kg'] * sales['unit_price']).sum() if not sales.empty else 0.0)
    
    return {
        "Cash Balance": cash_balance,
        "Current Inventory Value": current_inventory_value,
        "Inventory Value (Purchase Price)": inventory_value_purchase_price,
        "Current Stock": current_stock,
        "Operating Expenses": expenses['amount'].sum() if not expenses.empty else 0.0
    }

# UI Components
def show_price_management():
    """Show price update section"""
    current_price, last_updated = fetch_latest_market_price()
    
    with st.expander("💰 Market Price Management", expanded=True):
        col1, col2 = st.columns([3, 1])
        with col1:
            new_price = st.number_input(
                "Current Price (AED/kg)",
                min_value=0.01,
                value=current_price,
                step=0.01,
                format="%.2f"
            )
        with col2:
            st.write("")  # Spacer
            if st.button("Update Price"):
                if update_market_price(new_price):
                    st.success("Price updated!")
                    st.rerun()
        
        st.caption(f"Last updated: {last_updated.strftime('%Y-%m-%d %H:%M')}")
        
        # Price history chart
        price_history = fetch_price_history()
        if not price_history.empty:
            price_history['date'] = pd.to_datetime(price_history['date'])
            fig = px.line(
                price_history,
                x='date',
                y='price',
                title="Price History (Last 30 Days)",
                labels={'price': 'AED/kg', 'date': 'Date'}
            )
            st.plotly_chart(fig, use_container_width=True)

def show_business_overview():
    """Show high-level business metrics"""
    summary = get_system_summary()
    cols = st.columns(4)
    with cols[0]:
        st.metric("Total Cash", f"AED {summary['Total Cash']:,.2f}")
    with cols[1]:
        st.metric("Current Inventory Value", f"AED {summary['Current Inventory Value']:,.2f}",
                 f"Purchase Value: AED {summary['Inventory Value (Purchase Price)']:,.2f}")
    with cols[2]:
        st.metric("Current Stock", f"{summary['Current Stock']:,.2f} kg")
    with cols[3]:
        st.metric("Provisional Profit", f"AED {summary['Current Inventory Value'] - summary['Total Expenses']:,.2f}")

def show_unit_dashboard(unit):
    """Show dashboard for a specific business unit"""
    st.subheader(f"{unit} Dashboard")
    summary = get_business_unit_summary(unit)
    
    cols = st.columns(4)
    with cols[0]:
        st.metric("Cash Balance", f"AED {summary['Cash Balance']:,.2f}")
    with cols[1]:
        st.metric("Current Inventory Value", f"AED {summary['Current Inventory Value']:,.2f}",
                 f"Purchase Value: AED {summary['Inventory Value (Purchase Price)']:,.2f}")
    with cols[2]:
        st.metric("Current Stock", f"{summary['Current Stock']:,.2f} kg")
    with cols[3]:
        st.metric("Operating Expenses", f"AED {summary['Operating Expenses']:,.2f}")

# Main Dashboard View
def show_dashboard():
    """Main dashboard view"""
    try:
        # Check authentication
        if 'user' not in st.session_state:
            st.error("Please login first")
            return
            
        user = st.session_state.user
        
        st.title("📊 BizMaster Pro Dashboard")
        
        # Price management (admin only)
        if user.get('role') == 'admin':
            show_price_management()
        
        # Business overview
        show_business_overview()
        
        # Unit-specific dashboards
        units = []
        if user.get('business_unit') == 'All':
            units = ["Unit A", "Unit B"]
        else:
            units = [user.get('business_unit')]
        
        tabs = st.tabs(units)
        for i, unit in enumerate(units):
            with tabs[i]:
                show_unit_dashboard(unit)
                
    except Exception as e:
        st.error(f"Dashboard error: {str(e)}")

if __name__ == "__main__":
    show_dashboard()
