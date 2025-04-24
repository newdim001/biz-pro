import pandas as pd
import streamlit as st
from datetime import date, datetime
import numpy as np
import math
import logging
import os
from supabase import create_client

# Initialize Supabase client
SUPABASE_URL = "https://umtgkoogrtvyqcrzygoe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVtdGdrb29ncnR2eXFjcnp5Z29lIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDUxMzYyNDYsImV4cCI6MjA2MDcxMjI0Nn0.QMrKSOa91fzE7sNWBfhePhRFG05YMwNbvHYK8Fzkjpk"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Configure logging
logging.basicConfig(level=logging.INFO)

def initialize_default_data():
    """Initialize all required session state variables with default values from Supabase."""
    try:
        # Fetch default data from Supabase tables
        cash_balance = fetch_cash_balance("Unit A"), fetch_cash_balance("Unit B")
        price_history = fetch_price_history()
        inventory = fetch_inventory()
        expenses = fetch_expenses()
        investments = fetch_investments()
        partners = fetch_partners()
        # Initialize session state variables
        defaults = {
            'cash_balance': {'Unit A': cash_balance[0], 'Unit B': cash_balance[1]},
            'current_price': 50.0 if not price_history else price_history.iloc[-1]['Price'],
            'price_history': price_history,
            'inventory': inventory,
            'expenses': expenses,
            'investments': investments,
            'partners': partners,
            'transactions': fetch_transactions(),
        }
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value
    except Exception as e:
        logging.error(f"Error initializing default data: {str(e)}")
        raise ValueError(f"Error initializing default data: {str(e)}")

def fetch_cash_balance(business_unit):
    """
    Fetch the current cash balance for a specific business unit from Supabase.
    Args:
        business_unit (str): The business unit (e.g., "Unit A", "Unit B").
    Returns:
        float: The current cash balance.
    """
    try:
        response = supabase.table('cash_balances').select("balance").eq("unit", business_unit).execute()
        if response.data:
            return float(response.data[0]["balance"])
        logging.warning(f"No balance found for {business_unit}, returning default: 10000.0")
        return 10000.0  # Default balance if no record exists
    except Exception as e:
        logging.error(f"Failed to fetch cash balance for {business_unit}: {str(e)}")
        return 10000.0  # Default balance on error

def update_cash_balance(amount, business_unit, operation='add'):
    """
    Update the cash balance for a specific business unit in Supabase.
    Args:
        amount (float): The amount to add or subtract.
        business_unit (str): The business unit (e.g., "Unit A", "Unit B").
        operation (str): The type of operation ("add" or "subtract").
    Returns:
        bool: True if the update was successful, False otherwise.
    """
    try:
        amount = float(amount)
        if amount < 0.0:
            raise ValueError("Amount cannot be negative")
        if amount > 0.0 and amount < 0.01:
            raise ValueError("Amount must be at least 0.01")
        current_balance = fetch_cash_balance(business_unit)
        if operation == 'add':
            new_balance = current_balance + amount
        elif operation == 'subtract':
            if current_balance < amount:
                raise ValueError(f"Insufficient funds in {business_unit}")
            new_balance = current_balance - amount
        else:
            raise ValueError("Invalid operation. Use 'add' or 'subtract'.")
        # Use upsert to handle unique constraint
        response = supabase.table('cash_balances').upsert({
            'unit': business_unit,
            'balance': new_balance
        }, on_conflict="unit").execute()
        if not response.data:
            logging.error(f"Failed to update cash balance for {business_unit}")
            return False
        logging.info(f"Updated {business_unit} cash balance: {operation} {amount}. New balance: {new_balance}")
        return True
    except Exception as e:
        logging.error(f"Error updating cash balance for {business_unit}: {str(e)}")
        return False

def fetch_price_history():
    """Fetch price history from Supabase."""
    try:
        response = supabase.table('price_history').select('*').order('Date', desc=False).execute()
        data = response.data
        return pd.DataFrame(data) if data else pd.DataFrame([{
            'Date': date.today(),
            'Time': datetime.now().time(),
            'Price': 50.0
        }])
    except Exception as e:
        logging.error(f"Error fetching price history: {str(e)}")
        return pd.DataFrame([{
            'Date': date.today(),
            'Time': datetime.now().time(),
            'Price': 50.0
        }])

def fetch_inventory():
    """Fetch inventory data from Supabase."""
    try:
        response = supabase.table('inventory').select('*').execute()
        data = response.data
        return pd.DataFrame(data) if data else pd.DataFrame(columns=[
            'date', 'transaction_type', 'quantity_kg', 'unit_price',
            'total_amount', 'remarks', 'business_unit', 'created_at'
        ])
    except Exception as e:
        logging.error(f"Error fetching inventory: {str(e)}")
        return pd.DataFrame(columns=[
            'date', 'transaction_type', 'quantity_kg', 'unit_price',
            'total_amount', 'remarks', 'business_unit', 'created_at'
        ])

def fetch_expenses():
    """Fetch expenses data from Supabase."""
    try:
        response = supabase.table('expenses').select('*').execute()
        data = response.data
        return pd.DataFrame(data) if data else pd.DataFrame(columns=[
            'Date', 'Category', 'Amount', 'Description',
            'Business Unit', 'Partner', 'Payment Method'
        ])
    except Exception as e:
        logging.error(f"Error fetching expenses: {str(e)}")
        return pd.DataFrame(columns=[
            'Date', 'Category', 'Amount', 'Description',
            'Business Unit', 'Partner', 'Payment Method'
        ])

def fetch_investments():
    """Fetch investments data from Supabase."""
    try:
        response = supabase.table('investments').select('*').execute()
        data = response.data
        return pd.DataFrame(data) if data else pd.DataFrame(columns=[
            'Date', 'Business Unit', 'Amount', 'Investor', 'Description'
        ])
    except Exception as e:
        logging.error(f"Error fetching investments: {str(e)}")
        return pd.DataFrame(columns=[
            'Date', 'Business Unit', 'Amount', 'Investor', 'Description'
        ])

def fetch_partners():
    """Fetch partners data from Supabase."""
    try:
        response = supabase.table('partners').select('*').execute()
        data = response.data
        if not data:
            return {
                'Unit A': pd.DataFrame([
                    {'Partner': 'Ahmed', 'Share': 60.0, 'Withdrawn': 0.0, 'Invested': 0.0},
                    {'Partner': 'Fatima', 'Share': 40.0, 'Withdrawn': 0.0, 'Invested': 0.0}
                ]),
                'Unit B': pd.DataFrame([
                    {'Partner': 'Ali', 'Share': 50.0, 'Withdrawn': 0.0, 'Invested': 0.0},
                    {'Partner': 'Mariam', 'Share': 50.0, 'Withdrawn': 0.0, 'Invested': 0.0}
                ])
            }
        grouped = {}
        for item in data:
            unit = item['unit']
            if unit not in grouped:
                grouped[unit] = []
            grouped[unit].append(item)
        return {unit: pd.DataFrame(grouped[unit]) for unit in grouped}
    except Exception as e:
        logging.error(f"Error fetching partners: {str(e)}")
        return {
            'Unit A': pd.DataFrame([
                {'Partner': 'Ahmed', 'Share': 60.0, 'Withdrawn': 0.0, 'Invested': 0.0},
                {'Partner': 'Fatima', 'Share': 40.0, 'Withdrawn': 0.0, 'Invested': 0.0}
            ]),
            'Unit B': pd.DataFrame([
                {'Partner': 'Ali', 'Share': 50.0, 'Withdrawn': 0.0, 'Invested': 0.0},
                {'Partner': 'Mariam', 'Share': 50.0, 'Withdrawn': 0.0, 'Invested': 0.0}
            ])
        }

def fetch_transactions():
    """Fetch transactions data from Supabase."""
    try:
        response = supabase.table('transactions').select('*').execute()
        data = response.data
        return pd.DataFrame(data) if data else pd.DataFrame(columns=[
            'Date', 'Type', 'Amount', 'From', 'To', 'Description'
        ])
    except Exception as e:
        logging.error(f"Error fetching transactions: {str(e)}")
        return pd.DataFrame(columns=[
            'Date', 'Type', 'Amount', 'From', 'To', 'Description'
        ])

def update_market_price(new_price):
    """Update current market price with validation."""
    try:
        new_price = float(new_price)
        if new_price <= 0:
            raise ValueError("Price must be a positive number")
        st.session_state.current_price = new_price
        # Insert new price record into Supabase
        supabase.table('price_history').insert({
            'Date': str(date.today()),
            'Time': str(datetime.now().time()),
            'Price': new_price
        }).execute()
        logging.info(f"Market price updated to {new_price}")
    except Exception as e:
        logging.error(f"Error updating market price: {str(e)}")
        raise ValueError(f"Error updating market price: {str(e)}")

def calculate_inventory_value(unit):
    """Calculate current stock quantity and value."""
    inventory = st.session_state.inventory[
        st.session_state.inventory['business_unit'] == unit
    ]
    
    # Separate purchases and sales
    purchases = inventory[inventory['transaction_type'] == 'Purchase'] if not inventory.empty else pd.DataFrame(columns=inventory.columns)
    sales = inventory[inventory['transaction_type'] == 'Sale'] if not inventory.empty else pd.DataFrame(columns=inventory.columns)
    
    # Calculate net stock (purchases - sales)
    total_stock = (purchases['quantity_kg'].sum() if not purchases.empty else 0.0) - \
                  (sales['quantity_kg'].sum() if not sales.empty else 0.0)
    
    # Calculate current value based on market price
    current_value = total_stock * st.session_state.current_price
    
    return round(float(total_stock), 2), round(float(current_value), 2)

def calculate_operating_expenses(unit):
    """Calculate total operating expenses (excluding partner transactions)."""
    expenses = st.session_state.expenses[
        (st.session_state.expenses['Business Unit'] == unit) &
        (~st.session_state.expenses['Category'].isin([
            'Partner Withdrawal',
            'Partner Contribution'
        ]))
    ]
    return round(float(expenses['Amount'].sum()), 2)

def calculate_profit_loss(unit):
    """Calculate actual profit from sales."""
    sales = st.session_state.inventory[
        (st.session_state.inventory['business_unit'] == unit) &
        (st.session_state.inventory['transaction_type'] == 'Sale')
    ]
    purchases = st.session_state.inventory[
        (st.session_state.inventory['business_unit'] == unit) &
        (st.session_state.inventory['transaction_type'] == 'Purchase')
    ]
    gross_profit = (sales['total_amount'].sum() if not sales.empty else 0.0) - (purchases['total_amount'].sum() if not purchases.empty else 0.0)
    net_profit = gross_profit - calculate_operating_expenses(unit)
    return round(gross_profit, 2), round(net_profit, 2)

def calculate_provisional_profit(unit):
    """
    Calculate potential profit from current inventory.
    Provisional Profit = Inventory Value - Operating Expenses
    """
    current_stock, inventory_value = calculate_inventory_value(unit)
    operating_expenses = calculate_operating_expenses(unit)
    provisional_profit = inventory_value - operating_expenses
    return round(max(0.0, provisional_profit), 2)

def calculate_partner_profits(unit):
    """Calculate profit distribution for partners with validation."""
    partners_df = st.session_state.partners[unit].copy()
    provisional = calculate_provisional_profit(unit)
    _, actual = calculate_profit_loss(unit)
    distributable = max(float(provisional), float(actual))
    partners_df['Total_Entitlement'] = partners_df['Share'] / 100 * distributable
    partners_df['Available_Now'] = partners_df['Total_Entitlement'] - partners_df['Withdrawn']
    partners_df['Available_Now'] = partners_df['Available_Now'].apply(
        lambda x: max(0.0, float(x)) if float(x) >= 0.01 else 0.0
    )
    return partners_df[['Partner', 'Share', 'Total_Entitlement', 'Withdrawn', 'Available_Now']]

def record_partner_withdrawal(unit, partner, amount, description):
    """Record a partner withdrawal with validation."""
    try:
        amount = round(float(amount), 2)
        if amount < 0.01:
            raise ValueError("Amount must be at least 0.01")
        if amount > st.session_state.cash_balance.get(unit, 0.0):
            raise ValueError(f"Insufficient cash in {unit} for this withdrawal")
        profits_df = calculate_partner_profits(unit)
        partner_data = profits_df[profits_df['Partner'] == partner]
        if partner_data.empty:
            raise ValueError(f"Partner {partner} not found in {unit}")
        available = float(partner_data['Available_Now'].iloc[0])
        if amount > available:
            raise ValueError(f"Insufficient available balance. Max available: {available:.2f}")
        # Update partner's withdrawn amount in Supabase
        supabase.table('partners').update({
            'Withdrawn': available + amount
        }).eq('Partner', partner).eq('unit', unit).execute()
        # Record the expense
        supabase.table('expenses').insert({
            'Date': str(date.today()),
            'Category': 'Partner Withdrawal',
            'Amount': amount,
            'Description': description,
            'Business Unit': unit,
            'Partner': partner,
            'Payment Method': 'Bank Transfer'
        }).execute()
        # Update cash balance
        update_cash_balance(amount, unit, 'subtract')
        # Record transaction
        supabase.table('transactions').insert({
            'Date': str(date.today()),
            'Type': 'Partner Withdrawal',
            'Amount': amount,
            'From': unit,
            'To': partner,
            'Description': description
        }).execute()
        return True
    except Exception as e:
        logging.error(f"Withdrawal failed: {str(e)}")
        raise ValueError(f"Withdrawal failed: {str(e)}")

def distribute_investment(unit, amount, investor, description=None):
    """Distribute investment to partners according to their shares."""
    try:
        amount = float(amount)
        if amount == 0.0:
            logging.info(f"Skipping investment distribution for {investor} as amount is 0.0")
            return False
        if amount < 0.01:
            raise ValueError("Amount must be at least 0.01")
        # Record the investment in Supabase
        supabase.table('investments').insert({
            'Date': str(date.today()),
            'Business Unit': unit,
            'Amount': amount,
            'Investor': investor,
            'Description': description or f"Investment from {investor}"
        }).execute()
        # Update cash balance
        update_cash_balance(amount, unit, 'add')
        # Distribute to partners according to shares
        partners_df = st.session_state.partners[unit]
        total_share = float(partners_df['Share'].sum())
        for _, row in partners_df.iterrows():
            share_amount = (float(row['Share']) / total_share) * amount
            # Record as investment distribution
            supabase.table('expenses').insert({
                'Date': str(date.today()),
                'Category': 'Partner Contribution',
                'Amount': share_amount,
                'Description': f"Investment distribution from {investor}",
                'Business Unit': unit,
                'Partner': row['Partner'],
                'Payment Method': 'Bank Transfer'
            }).execute()
            # Update partner's invested amount in Supabase
            supabase.table('partners').update({
                'Invested': row['Invested'] + share_amount
            }).eq('Partner', row['Partner']).eq('unit', unit).execute()
        return True
    except Exception as e:
        logging.error(f"Error distributing investment: {str(e)}")
        raise ValueError(f"Error distributing investment: {str(e)}")
