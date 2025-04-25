import streamlit as st
import pandas as pd
import plotly.express as px
from utils import (
    fetch_inventory, fetch_cash_balances, fetch_expenses,
    calculate_current_stock, calculate_inventory_value,
    calculate_profit_loss, calculate_partner_profits,
    calculate_combined_partner_profits
)

from supabase import create_client

# Initialize Supabase client
SUPABASE_URL = "https://umtgkoogrtvyqcrzygoe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVtdGdrb29ncnR2eXFjcnp5Z29lIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDUxMzYyNDYsImV4cCI6MjA2MDcxMjI0Nn0.QMrKSOa91fzE7sNWBfhePhRFG05YMwNbvHYK8Fzkjpk"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Fetch inventory data
def fetch_inventory(business_unit=None):
    """Fetch inventory data from Supabase"""
    query = supabase.table("inventory").select("*")
    if business_unit:
        query = query.eq("business_unit", business_unit)
    response = query.execute()
    return pd.DataFrame(response.data) if response.data else pd.DataFrame()

# Fetch cash balances
def fetch_cash_balances():
    """Fetch cash balances from Supabase"""
    response = supabase.table("cash_balances").select("*").execute()
    return {row['business_unit']: row['balance'] for row in response.data}

# Fetch expenses data
def fetch_expenses(business_unit=None):
    """Fetch expenses data from Supabase"""
    query = supabase.table("expenses").select("*")
    if business_unit:
        query = query.eq("business_unit", business_unit)
    response = query.execute()
    return pd.DataFrame(response.data) if response.data else pd.DataFrame()

# Calculate current stock for a specific unit
def calculate_current_stock(unit):
    """
    Calculate current stock for a specific business unit.
    Args:
        unit: The business unit (e.g., 'Unit A', 'Unit B').
    Returns:
        Current stock (sum of purchases - sum of sales).
    """
    try:
        # Fetch inventory data for the specified unit
        inventory_data = fetch_inventory(unit)
        if inventory_data.empty:
            return 0.0  # Return zero if no data exists

        # Separate purchases and sales
        purchases = inventory_data[inventory_data['transaction_type'] == 'Purchase']
        sales = inventory_data[inventory_data['transaction_type'] == 'Sale']

        # Calculate total purchased and sold quantities
        total_purchased = purchases['quantity_kg'].sum() if not purchases.empty else 0.0
        total_sold = sales['quantity_kg'].sum() if not sales.empty else 0.0

        # Calculate current stock
        current_stock = total_purchased - total_sold
        return round(current_stock, 2)
    except Exception as e:
        st.error(f"Error calculating current stock: {str(e)}")
        return 0.0
# Calculate inventory value (CORRECTED VERSION)
def calculate_inventory_value(unit):
    """Calculate inventory value for a specific unit"""
    inventory_data = fetch_inventory(unit)
    if inventory_data.empty:
        return 0.0, 0.0
    
    # Separate purchases and sales
    purchases = inventory_data[inventory_data['transaction_type'] == 'Purchase']
    sales = inventory_data[inventory_data['transaction_type'] == 'Sale']
    
    # Calculate net stock (purchases - sales)
    total_stock = (purchases['quantity_kg'].sum() if not purchases.empty else 0.0) - \
                  (sales['quantity_kg'].sum() if not sales.empty else 0.0)
    
    # Calculate weighted average purchase price for valuation
    if not purchases.empty:
        total_purchase_amount = purchases['total_amount'].sum()
        total_purchase_quantity = purchases['quantity_kg'].sum()
        avg_purchase_price = total_purchase_amount / total_purchase_quantity
    else:
        avg_purchase_price = 0
    
    # Calculate total inventory value
    current_value = total_stock * avg_purchase_price
    
    return round(total_stock, 2), round(current_value, 2)

# Calculate profit/loss
def calculate_profit_loss(unit):
    """Calculate profit/loss for a business unit"""
    inventory_data = fetch_inventory(unit)
    if inventory_data.empty:
        return 0.0, 0.0
    
    purchases = inventory_data[inventory_data['transaction_type'] == 'Purchase']
    sales = inventory_data[inventory_data['transaction_type'] == 'Sale']
    
    # Calculate gross profit (sales revenue - cost of goods sold)
    if not sales.empty:
        total_sales_amount = sales['total_amount'].sum()
        total_sales_quantity = sales['quantity_kg'].sum()
        
        if not purchases.empty:
            total_purchase_amount = purchases['total_amount'].sum()
            total_purchase_quantity = purchases['quantity_kg'].sum()
            avg_purchase_price = total_purchase_amount / total_purchase_quantity
            cost_of_goods_sold = total_sales_quantity * avg_purchase_price
            gross_profit = total_sales_amount - cost_of_goods_sold
        else:
            gross_profit = total_sales_amount
    else:
        gross_profit = 0.0
    
    # Calculate net profit (gross profit - expenses)
    expenses_data = fetch_expenses(unit)
    total_expenses = expenses_data['amount'].sum() if not expenses_data.empty else 0.0
    net_profit = gross_profit - total_expenses
    
    return round(gross_profit, 2), round(net_profit, 2)

# Show reports
def show_reports():
    """Business reporting dashboard"""
    user = st.session_state.get('user')
    if not user or not has_permission(user, 'reports'):
        st.error("Permission denied")
        return
    
    st.header("📈 Business Reports")
    
    # Available units
    units = []
    if user['business_unit'] in ['All', 'Unit A']:
        units.append('Unit A')
    if user['business_unit'] in ['All', 'Unit B']:
        units.append('Unit B')
    if user['business_unit'] == 'All':
        units.append('Combined')
    
    # Report selection
    report_type = st.selectbox(
        "Select Report Type",
        ["Financial Summary", "Inventory Analysis", "Partner Distributions"],
        key='report_type_selector'
    )
    
    if report_type == "Financial Summary":
        show_financial_report(units)
    elif report_type == "Inventory Analysis":
        show_inventory_report(units)
    else:
        show_partner_report(units)

# Financial performance report
def show_financial_report(units):
    """Financial performance report"""
    st.subheader("💰 Financial Summary")
    data = []
    for unit in units:
        if unit == 'Combined':
            try:
                cash = sum(fetch_cash_balances().values())
                stock_a, val_a = calculate_inventory_value('Unit A')
                stock_b, val_b = calculate_inventory_value('Unit B')
                gross_a, net_a = calculate_profit_loss('Unit A')
                gross_b, net_b = calculate_profit_loss('Unit B')
                data.append({
                    'Unit': 'Combined',
                    'Cash': cash,
                    'Inventory Value': val_a + val_b,
                    'Gross Profit': gross_a + gross_b,
                    'Net Profit': net_a + net_b
                })
            except Exception as e:
                st.error(f"Error calculating combined financials: {str(e)}")
                continue
        else:
            try:
                cash = fetch_cash_balances().get(unit, 0)
                stock, val = calculate_inventory_value(unit)
                gross, net = calculate_profit_loss(unit)
                data.append({
                    'Unit': unit,
                    'Cash': cash,
                    'Inventory Value': val,
                    'Gross Profit': gross,
                    'Net Profit': net
                })
            except Exception as e:
                st.error(f"Error calculating {unit} financials: {str(e)}")
                continue
    
    if not data:
        st.warning("No financial data available")
        return
    
    df = pd.DataFrame(data)
    
    # Display metrics
    cols = st.columns(len(df))
    for idx, row in df.iterrows():
        with cols[idx]:
            st.metric(f"{row['Unit']} Net Profit", f"AED {row['Net Profit']:,.2f}")
    
    # Display dataframe
    st.dataframe(
        df.style.format({
            'Cash': 'AED {:,.2f}',
            'Inventory Value': 'AED {:,.2f}',
            'Gross Profit': 'AED {:,.2f}',
            'Net Profit': 'AED {:,.2f}'
        }),
        height=200,
        use_container_width=True
    )
    
    # Visualizations
    try:
        fig = px.bar(
            df.melt(id_vars=['Unit'], value_vars=['Gross Profit', 'Net Profit']),
            x='Unit', y='value', color='variable',
            title="Profit Comparison",
            labels={'value': 'Amount (AED)'},
            barmode='group'
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Could not generate profit chart: {str(e)}")

# Inventory analysis report (CORRECTED VERSION)
def show_inventory_report(units):
    """Inventory analysis report"""
    st.subheader("📦 Inventory Analysis")
    for unit in units:
        try:
            if unit == 'Combined':
                inventory = fetch_inventory()
                st.write("### Combined Inventory")
                # Calculate combined values
                stock_a, val_a = calculate_inventory_value('Unit A')
                stock_b, val_b = calculate_inventory_value('Unit B')
                current_stock = stock_a + stock_b
                current_value = val_a + val_b
            else:
                inventory = fetch_inventory(unit)
                st.write(f"### {unit} Inventory")
                current_stock, current_value = calculate_inventory_value(unit)
            
            if not inventory.empty:
                # Current status
                cols = st.columns(2)
                cols[0].metric("Current Stock", f"{current_stock:,.2f} kg")
                cols[1].metric("Current Value", f"AED {current_value:,.2f}")
                
                # Transactions - Show only specified columns
                filtered_inventory = inventory[['date', 'transaction_type', 'quantity_kg', 'unit_price', 'total_amount', 'remarks', 'business_unit']]
                st.dataframe(
                    filtered_inventory.sort_values('date', ascending=False).style.format({
                        'quantity_kg': '{:,.2f} kg',
                        'unit_price': 'AED {:,.2f}',
                        'total_amount': 'AED {:,.2f}'
                    }),
                    height=300,
                    use_container_width=True
                )
                
                # Correct inventory movement chart
                try:
                    # Create a proper cumulative sum that accounts for purchases (+) and sales (-)
                    inventory['signed_quantity'] = inventory.apply(
                        lambda row: row['quantity_kg'] if row['transaction_type'] == 'Purchase' else -row['quantity_kg'],
                        axis=1
                    )
                    inventory['cumulative_stock'] = inventory['signed_quantity'].cumsum()
                    
                    fig = px.line(
                        inventory.sort_values('date'),
                        x='date', y='cumulative_stock',
                        title=f"Inventory Movement - {unit}",
                        labels={'cumulative_stock': 'Quantity (kg)'}
                    )
                    st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.error(f"Could not generate inventory chart: {str(e)}")
            else:
                st.info(f"No inventory data available for {unit}")
        except Exception as e:
            st.error(f"Error processing {unit} inventory: {str(e)}")

# Partner distributions report
def show_partner_report(units):
    """Partner distributions report"""
    st.subheader("👥 Partner Distributions")
    for unit in units:
        try:
            if unit == 'Combined':
                st.write("### Combined Partners")
                data = calculate_combined_partner_profits()
                if not data.empty:
                    data = data[['business_unit', 'partner_name', 'share', 'withdrawn', 'Total_Entitlement', 'Available_Now']]
            else:
                st.write(f"### {unit} Partners")
                data = calculate_partner_profits(unit)
                if not data.empty:
                    data = data[['business_unit', 'partner_name', 'share', 'withdrawn', 'Total_Entitlement', 'Available_Now']]
            
            if not data.empty:
                # Metrics
                total = data['Available_Now'].sum()
                withdrawn_col = 'withdrawn' if 'withdrawn' in data.columns else 'amount'
                withdrawn = data[withdrawn_col].sum()
                cols = st.columns(3)
                cols[0].metric("Total Available", f"AED {total:,.2f}")
                cols[1].metric("Total Withdrawn", f"AED {withdrawn:,.2f}")
                cols[2].metric("Net Payable", f"AED {total - withdrawn:,.2f}")
                
                # Detailed view
                st.dataframe(
                    data.style.format({
                        'share': '{:.1f}%',
                        'Total_Entitlement': 'AED {:,.2f}',
                        'withdrawn': 'AED {:,.2f}',
                        'Available_Now': 'AED {:,.2f}'
                    }),
                    use_container_width=True
                )
                
                # Visualization
                try:
                    fig = px.pie(
                        data, 
                        values='Available_Now', 
                        names='partner_name',
                        title=f"Available Profit Distribution - {unit}",
                        hover_data=['Available_Now', 'withdrawn']
                    )
                    st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.error(f"Could not generate partner chart: {str(e)}")
            else:
                st.info(f"No partner data available for {unit}")
        except Exception as e:
            st.error(f"Error processing {unit} partner data: {str(e)}")

if __name__ == "__main__":
    show_reports()
