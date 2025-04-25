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
        # Initialize cash balances with proper error handling
        cash_balance = {}
        for unit in ["Unit A", "Unit B"]:
            try:
                balance = fetch_cash_balance(unit)
                cash_balance[unit] = balance
            except Exception as e:
                logging.warning(f"Failed to fetch balance for {unit}: {str(e)}")
                cash_balance[unit] = 10000.0  # Default balance
        
        # Initialize other data
        defaults = {
            'cash_balance': cash_balance,
            'current_price': fetch_latest_market_price()[0],
            'price_history': fetch_price_history(),
            'inventory': fetch_inventory(),
            'expenses': fetch_expenses(),
            'investments': fetch_investments(),
            'partners': fetch_partners(),
            'transactions': fetch_transactions(),
            'last_updated': datetime.now()
        }
        
        # Set session state
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value
                
    except Exception as e:
        logging.error(f"Error initializing default data: {str(e)}")
        st.error(f"Failed to initialize application data: {str(e)}")
        raise

def fetch_cash_balance(business_unit):
    """
    Safely fetch cash balance without creating duplicates.
    """
    try:
        # Try to fetch existing balance
        response = supabase.table('cash_balances')\
                   .select("balance")\
                   .eq("business_unit", business_unit)\
                   .execute()
        
        if response.data:
            return float(response.data[0]["balance"])
        
        # If doesn't exist, insert with upsert to prevent race conditions
        response = supabase.table('cash_balances').upsert({
            "business_unit": business_unit,
            "balance": 10000.0,  # Default balance
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }, on_conflict="business_unit").execute()
        
        return 10000.0
    except Exception as e:
        st.error(f"Failed to fetch balance: {str(e)}")
        return 10000.0  # Return default balance on failure

def update_cash_balance(amount, business_unit, operation='add'):
    """
    Atomic cash balance update with proper conflict handling
    """
    try:
        amount = float(amount)
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        # Get current balance safely
        current_balance = fetch_cash_balance(business_unit)
        
        # Calculate new balance
        new_balance = current_balance + (amount if operation == 'add' else -amount)
        
        # Check for sufficient funds if subtracting
        if operation == 'subtract' and new_balance < 0:
            raise ValueError(f"Insufficient funds in {business_unit}")
        
        # Use upsert with on_conflict to properly handle existing records
        response = supabase.table('cash_balances').upsert({
            "business_unit": business_unit,
            "balance": new_balance,
            "updated_at": datetime.now().isoformat()
        }, on_conflict="business_unit").execute()
        
        if not response.data:
            raise ValueError("Balance update failed")
        
        # Update session state
        if 'cash_balance' not in st.session_state:
            st.session_state.cash_balance = {}
        st.session_state.cash_balance[business_unit] = new_balance
        return True
        
    except Exception as e:
        st.error(f"Balance update failed: {str(e)}")
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

def fetch_latest_market_price():
    """Fetch the latest market price from price history."""
    try:
        price_history = fetch_price_history()
        if not price_history.empty:
            latest_price = price_history.iloc[-1]['Price']
            latest_date = price_history.iloc[-1]['Date']
            return float(latest_price), latest_date
        return 50.0, date.today()  # Default price if no history exists
    except Exception as e:
        logging.error(f"Error fetching latest market price: {str(e)}")
        return 50.0, date.today()

def fetch_inventory(business_unit=None):
    """
    Fetch inventory data from Supabase with type conversion.
    """
    try:
        query = supabase.table("inventory").select("*")
        if business_unit:
            query = query.eq("business_unit", business_unit)
        response = query.execute()
        if not response.data:
            return pd.DataFrame(columns=[
                'id', 'date', 'transaction_type', 'quantity_kg',
                'unit_price', 'total_amount', 'remarks', 'business_unit',
                'created_at', 'updated_at'
            ])
        df = pd.DataFrame(response.data)
        # Convert numeric columns
        numeric_cols = ['quantity_kg', 'unit_price', 'total_amount']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        # Convert date columns
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date']).dt.date
        if 'created_at' in df.columns:
            df['created_at'] = pd.to_datetime(df['created_at'])
        if 'updated_at' in df.columns:
            df['updated_at'] = pd.to_datetime(df['updated_at'])
        return df
    except Exception as e:
        st.error(f"Failed to load inventory: {str(e)}")
        return pd.DataFrame(columns=[
            'id', 'date', 'transaction_type', 'quantity_kg',
            'unit_price', 'total_amount', 'remarks', 'business_unit',
            'created_at', 'updated_at'
        ])

def fetch_expenses(unit=None):
    """Fetch expenses data from Supabase for a specific unit or all units."""
    try:
        query = supabase.table('expenses').select('*')
        if unit:
            query = query.eq('Business Unit', unit)
        response = query.execute()
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

def fetch_investments(unit=None):
    """Fetch investments data from Supabase for a specific unit or all units."""
    try:
        query = supabase.table('investments').select('*')
        if unit:
            query = query.eq('Business Unit', unit)
        response = query.execute()
        data = response.data
        return pd.DataFrame(data) if data else pd.DataFrame(columns=[
            'Date', 'Business Unit', 'Amount', 'Investor', 'Description'
        ])
    except Exception as e:
        logging.error(f"Error fetching investments: {str(e)}")
        return pd.DataFrame(columns=[
            'Date', 'Business Unit', 'Amount', 'Investor', 'Description'
        ])

def fetch_partners(unit=None):
    """Fetch partners data from Supabase for a specific unit or all units."""
    try:
        query = supabase.table('partners').select('*')
        if unit:
            query = query.eq('unit', unit)
        response = query.execute()
        data = response.data
        if not data:
            # Return default partner structure if no data exists
            default_partners = {
                'Unit A': pd.DataFrame([
                    {'Partner': 'Ahmed', 'Share': 60.0, 'Withdrawn': 0.0, 'Invested': 0.0, 'unit': 'Unit A'},
                    {'Partner': 'Fatima', 'Share': 40.0, 'Withdrawn': 0.0, 'Invested': 0.0, 'unit': 'Unit A'}
                ]),
                'Unit B': pd.DataFrame([
                    {'Partner': 'Ali', 'Share': 50.0, 'Withdrawn': 0.0, 'Invested': 0.0, 'unit': 'Unit B'},
                    {'Partner': 'Mariam', 'Share': 50.0, 'Withdrawn': 0.0, 'Invested': 0.0, 'unit': 'Unit B'}
                ])
            }
            return default_partners.get(unit, pd.DataFrame()) if unit else default_partners
        
        if unit:
            return pd.DataFrame(data)
        else:
            # Group by unit if no specific unit requested
            grouped = {}
            for item in data:
                unit_name = item['unit']
                if unit_name not in grouped:
                    grouped[unit_name] = []
                grouped[unit_name].append(item)
            return {unit: pd.DataFrame(grouped[unit]) for unit in grouped}
    except Exception as e:
        logging.error(f"Error fetching partners: {str(e)}")
        default_partners = {
            'Unit A': pd.DataFrame([
                {'Partner': 'Ahmed', 'Share': 60.0, 'Withdrawn': 0.0, 'Invested': 0.0, 'unit': 'Unit A'},
                {'Partner': 'Fatima', 'Share': 40.0, 'Withdrawn': 0.0, 'Invested': 0.0, 'unit': 'Unit A'}
            ]),
            'Unit B': pd.DataFrame([
                {'Partner': 'Ali', 'Share': 50.0, 'Withdrawn': 0.0, 'Invested': 0.0, 'unit': 'Unit B'},
                {'Partner': 'Mariam', 'Share': 50.0, 'Withdrawn': 0.0, 'Invested': 0.0, 'unit': 'Unit B'}
            ])
        }
        return default_partners.get(unit, pd.DataFrame()) if unit else default_partners

def fetch_transactions(unit=None):
    """Fetch transactions data from Supabase for a specific unit or all units."""
    try:
        query = supabase.table('transactions').select('*')
        if unit:
            query = query.or_(f"From.eq.{unit},To.eq.{unit}")
        response = query.execute()
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

def calculate_current_stock(unit=None):
    """
    Calculate current stock for a specific business unit or all units.
    Args:
        unit: The business unit (e.g., 'Unit A', 'Unit B'). None for all units.
    Returns:
        Current stock (sum of purchases - sum of sales).
    """
    try:
        inventory_data = fetch_inventory(unit)
        if inventory_data.empty:
            return 0.0

        purchases = inventory_data[inventory_data['transaction_type'] == 'Purchase']
        sales = inventory_data[inventory_data['transaction_type'] == 'Sale']

        total_purchased = purchases['quantity_kg'].sum() if not purchases.empty else 0.0
        total_sold = sales['quantity_kg'].sum() if not sales.empty else 0.0

        return round(total_purchased - total_sold, 2)
    except Exception as e:
        logging.error(f"Error calculating current stock: {str(e)}")
        return 0.0

def calculate_inventory_value(unit=None):
    """
    Calculate inventory value for a specific unit or all units.
    Args:
        unit: The business unit (e.g., 'Unit A', 'Unit B'). None for all units.
    Returns:
        tuple: (current_stock, current_value)
    """
    try:
        inventory_data = fetch_inventory(unit)
        if inventory_data.empty:
            return 0.0, 0.0

        current_stock = calculate_current_stock(unit)
        
        purchases = inventory_data[inventory_data['transaction_type'] == 'Purchase']
        if not purchases.empty:
            total_purchase_amount = purchases['total_amount'].sum()
            total_purchase_quantity = purchases['quantity_kg'].sum()
            avg_purchase_price = total_purchase_amount / total_purchase_quantity
        else:
            avg_purchase_price = fetch_latest_market_price()[0]

        current_value = current_stock * avg_purchase_price
        return round(current_stock, 2), round(current_value, 2)
    except Exception as e:
        logging.error(f"Error calculating inventory value: {str(e)}")
        return 0.0, 0.0

def calculate_operating_expenses(unit=None):
    """
    Calculate total operating expenses (excluding partner transactions).
    Args:
        unit: The business unit (e.g., 'Unit A', 'Unit B'). None for all units.
    Returns:
        float: Total operating expenses
    """
    try:
        expenses_data = fetch_expenses(unit)
        if expenses_data.empty:
            return 0.0

        operating_expenses = expenses_data[
            (~expenses_data['Category'].isin([
                'Partner Withdrawal',
                'Partner Contribution'
            ]))
        ]
        return round(float(operating_expenses['Amount'].sum()), 2)
    except Exception as e:
        logging.error(f"Error calculating operating expenses: {str(e)}")
        return 0.0

def calculate_profit_loss(unit=None):
    """
    Calculate profit/loss for a business unit or all units.
    Args:
        unit: The business unit (e.g., 'Unit A', 'Unit B'). None for all units.
    Returns:
        tuple: (gross_profit, net_profit)
    """
    try:
        inventory_data = fetch_inventory(unit)
        if inventory_data.empty:
            return 0.0, 0.0

        sales = inventory_data[inventory_data['transaction_type'] == 'Sale']
        purchases = inventory_data[inventory_data['transaction_type'] == 'Purchase']

        gross_profit = (sales['total_amount'].sum() if not sales.empty else 0.0) - \
                      (purchases['total_amount'].sum() if not purchases.empty else 0.0)

        operating_expenses = calculate_operating_expenses(unit)
        net_profit = gross_profit - operating_expenses

        return round(gross_profit, 2), round(net_profit, 2)
    except Exception as e:
        logging.error(f"Error calculating profit/loss: {str(e)}")
        return 0.0, 0.0

def calculate_provisional_profit(unit=None):
    """
    Calculate potential profit from current inventory.
    Provisional Profit = Inventory Value - Operating Expenses
    Args:
        unit: The business unit (e.g., 'Unit A', 'Unit B'). None for all units.
    Returns:
        float: Provisional profit
    """
    try:
        _, inventory_value = calculate_inventory_value(unit)
        operating_expenses = calculate_operating_expenses(unit)
        provisional_profit = inventory_value - operating_expenses
        return round(max(0.0, provisional_profit), 2)
    except Exception as e:
        logging.error(f"Error calculating provisional profit: {str(e)}")
        return 0.0

def calculate_partner_profits(unit):
    """
    Calculate profit distribution for partners with validation.
    Args:
        unit: The business unit (e.g., 'Unit A', 'Unit B').
    Returns:
        DataFrame: Partner profit distribution details
    """
    try:
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
    except Exception as e:
        logging.error(f"Error calculating partner profits: {str(e)}")
        return pd.DataFrame()

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

def refresh_all_data():
    """Force refresh all data from Supabase"""
    try:
        st.session_state.cash_balance = {
            "Unit A": fetch_cash_balance("Unit A"),
            "Unit B": fetch_cash_balance("Unit B")
        }
        st.session_state.price_history = fetch_price_history()
        st.session_state.current_price = fetch_latest_market_price()[0]
        st.session_state.inventory = fetch_inventory()
        st.session_state.expenses = fetch_expenses()
        st.session_state.investments = fetch_investments()
        st.session_state.partners = fetch_partners()
        st.session_state.transactions = fetch_transactions()
        st.session_state.last_updated = datetime.now()
        st.success("Data refreshed successfully!")
    except Exception as e:
        st.error(f"Failed to refresh data: {str(e)}")
