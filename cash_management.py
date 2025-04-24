import logging
from datetime import date
from supabase import create_client

# Initialize Supabase client
SUPABASE_URL = "https://umtgkoogrtvyqcrzygoe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVtdGdrb29ncnR2eXFjcnp5Z29lIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDUxMzYyNDYsImV4cCI6MjA2MDcxMjI0Nn0.QMrKSOa91fzE7sNWBfhePhRFG05YMwNbvHYK8Fzkjpk"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Configure logging
logging.basicConfig(level=logging.INFO)

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
        
        # Update the cash balance in Supabase
        response = supabase.table('cash_balances').update({
            'balance': new_balance
        }).eq('unit', business_unit).execute()
        
        if not response.data:
            logging.error(f"Failed to update cash balance for {business_unit}")
            return False
        
        logging.info(f"Updated {business_unit} cash balance: {operation} {amount}. New balance: {new_balance}")
        return True
    except Exception as e:
        logging.error(f"Error updating cash balance for {business_unit}: {str(e)}")
        return False
