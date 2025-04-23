import streamlit as st
import pandas as pd
from datetime import date
from supabase import create_client
from components.auth import has_permission  # Import the has_permission function

# Initialize Supabase client
SUPABASE_URL = "https://umtgkoogrtvyqcrzygoe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVtdGdrb29ncnR2eXFjcnp5Z29lIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDUxMzYyNDYsImV4cCI6MjA2MDcxMjI0Nn0.QMrKSOa91fzE7sNWBfhePhRFG05YMwNbvHYK8Fzkjpk"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch_expenses():
    """Fetch all expenses from Supabase"""
    response = supabase.table("expenses").select("*").execute()
    return pd.DataFrame(response.data)

def add_expense(exp_date, category, amount, description, business_unit, payment_method):
    """
    Add a new expense record to Supabase.
    Parameters:
        exp_date (date): Expense date.
        category (str): Expense category.
        amount (float): Expense amount.
        description (str): Purpose of the expense.
        business_unit (str): Business unit ('Unit A', 'Unit B', etc.).
        payment_method (str): Payment method.
    """
    response = supabase.table("expenses").insert({
        "date": exp_date.isoformat(),
        "category": category,
        "amount": amount,
        "description": description,
        "business_unit": business_unit,
        "payment_method": payment_method
    }).execute()
    return True if response else False

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
    if current_balance is None:
        st.error("Failed to fetch cash balance.")
        return False
    if action == 'subtract':
        if current_balance < amount:
            return False  # Insufficient balance
        new_balance = current_balance - amount
    elif action == 'add':
        new_balance = current_balance + amount
    # Update cash balance in Supabase
    response = supabase.table("cash_balances").upsert({
        "business_unit": business_unit,
        "balance": new_balance
    }, on_conflict="business_unit").execute()  # Ensure proper handling of conflicts
    return True if response else False

def fetch_cash_balance(business_unit):
    """Fetch the current cash balance for a business unit from Supabase"""
    response = supabase.table("cash_balances").select("balance").eq("business_unit", business_unit).execute()
    if response.data:
        return response.data[0]["balance"]
    return 1.0  # Default initial balance if no record exists

def fetch_partner_profits(unit):
    """Fetch partner profits for a given business unit"""
    response = supabase.table("partnerships").select("*").eq("business_unit", unit).execute()
    partnerships_data = response.data
    profit_df = pd.DataFrame(partnerships_data)
    if not profit_df.empty:
        # Fetch provisional profit for the business unit
        provisional_profit = get_business_unit_summary(unit)["Provisional Profit"]
        # Calculate Total Entitlement as (partner_share %) × provisional_profit
        profit_df['Total_Entitlement'] = profit_df['share'] * 0.01 * provisional_profit
        profit_df['Available_Now'] = profit_df['Total_Entitlement'] - profit_df['withdrawn']
    return profit_df

def get_business_unit_summary(unit):
    """Calculate summary metrics for a specific business unit (copied from dashboard file)"""
    cash_balance = fetch_cash_balance(unit)
    inventory_data = fetch_inventory(unit)
    stock_quantity = inventory_data['quantity_kg'].sum() if not inventory_data.empty else 0.0
    inventory_value = (inventory_data['quantity_kg'] * inventory_data['unit_price']).sum() if not inventory_data.empty else 0.0
    investments_data = fetch_investments(unit)
    investment_total = investments_data['amount'].sum() if not investments_data.empty else 0.0
    expenses_data = fetch_expenses()
    operating_expenses = expenses_data['amount'].sum() if not expenses_data.empty else 0.0
    provisional_profit = inventory_value - operating_expenses  # Calculate provisional profit
    return {
        "Cash Balance": cash_balance,
        "Inventory Quantity (kg)": stock_quantity,
        "Inventory Value": inventory_value,
        "Investment Total": investment_total,
        "Operating Expenses": operating_expenses,
        "Provisional Profit": provisional_profit
    }

def fetch_inventory(business_unit=None):
    """Fetch inventory data from Supabase"""
    query = supabase.table("inventory").select("*")
    if business_unit:
        query = query.eq("business_unit", business_unit)
    response = query.execute()
    return pd.DataFrame(response.data)

def fetch_investments(business_unit=None):
    """Fetch investments data from Supabase"""
    query = supabase.table("investments").select("*")
    if business_unit:
        query = query.eq("business_unit", business_unit)
    response = query.execute()
    return pd.DataFrame(response.data)

def record_partner_withdrawal(unit, partner, amount, description):
    """
    Record a partner withdrawal in Supabase.
    Parameters:
        unit (str): Business unit.
        partner (str): Partner name.
        amount (float): Withdrawal amount.
        description (str): Purpose of the withdrawal.
    Returns:
        bool: True if the withdrawal was recorded successfully, False otherwise.
    """
    # Fetch current withdrawn amount
    response = supabase.table("partnerships").select("withdrawn").eq("partner_name", partner).eq("business_unit", unit).execute()
    if not response.data:
        return False
    current_withdrawn = response.data[0]["withdrawn"]
    new_withdrawn = current_withdrawn + amount
    # Update partnership record
    response = supabase.table("partnerships").update({
        "withdrawn": new_withdrawn
    }).eq("partner_name", partner).eq("business_unit", unit).execute()
    if not response:
        return False
    # Update cash balance
    update_cash_balance(amount, unit, 'subtract')
    return True

def show_expenses():
    """Display and manage business expenses and partner withdrawals"""
    try:
        user = st.session_state.get('user')
        if not user or not has_permission(user, 'expenses'):  # Check user permissions
            st.error("Permission denied")
            return
        st.header("💰 Expense Management")
        # Determine which units to show based on user's role
        units_to_show = []
        if user['business_unit'] in ['All', 'Unit A']:
            units_to_show.append('Unit A')
        if user['business_unit'] in ['All', 'Unit B']:
            units_to_show.append('Unit B')
        tabs = st.tabs(units_to_show)
        for i, unit in enumerate(units_to_show):
            with tabs[i]:
                tab1, tab2 = st.tabs(["Business Expenses", "Partner Withdrawals"])
                with tab1:
                    show_business_expenses(unit)
                with tab2:
                    show_partner_withdrawals(unit)
    except Exception as e:
        st.error(f"Error loading expenses: {str(e)}")

def show_business_expenses(unit):
    """Show business expenses section"""
    with st.form(f"expense_form_{unit}", clear_on_submit=True):
        st.subheader(f"New Expense - {unit}")
        cols = st.columns(2)
        with cols[0]:
            exp_date = st.date_input("Date*", value=date.today())
            amount = st.number_input(
                "Amount (AED)*",
                min_value=0.01,
                step=0.01,
                value=100.00,
                format="%.2f"
            )
        with cols[1]:
            category = st.selectbox("Category*", [
                "Operational", "Personnel", "Logistics", "Marketing",
                "Utilities", "Rent", "Other"
            ])
            payment_method = st.selectbox("Payment Method*", [
                "Cash", "Bank Transfer", "Credit Card", "Cheque"
            ])
        description = st.text_input("Description*", placeholder="Purpose of expense")
        submitted = st.form_submit_button("Record Expense")
        if submitted:
            try:
                if not description:
                    st.error("Description is required")
                    return
                amount = float(amount)
                if amount < 0.01:
                    st.error("Amount must be at least 0.01 AED")
                    return
                success = add_expense(
                    exp_date=exp_date,
                    category=category,
                    amount=amount,
                    description=description,
                    business_unit=unit,
                    payment_method=payment_method
                )
                if success:
                    update_cash_balance(amount, unit, 'subtract')
                    st.success("Expense recorded successfully!")
                    st.rerun()
                else:
                    st.error("Failed to record expense.")
            except Exception as e:
                st.error(f"Error recording expense: {str(e)}")
    # Display recent expenses
    expenses_data = fetch_expenses()
    if not expenses_data.empty:
        unit_expenses = expenses_data[
            (expenses_data['business_unit'] == unit) &
            (expenses_data['partner'].isna())
        ]
        if not unit_expenses.empty:
            st.subheader("Recent Expenses")
            # Filter and display only the required columns
            st.dataframe(
                unit_expenses[[
                    "date", "category", "amount", "description", "business_unit", "partner", "payment_method"
                ]].sort_values('date', ascending=False).head(10),
                hide_index=True,
                use_container_width=True,
                column_config={
                    "date": st.column_config.DateColumn(format="YYYY-MM-DD"),
                    "amount": st.column_config.NumberColumn(format="AED %.2f"),
                    "category": "Category",
                    "description": "Description",
                    "business_unit": "Business Unit",
                    "partner": "Partner",
                    "payment_method": "Payment Method"
                }
            )

def show_partner_withdrawals(unit):
    """Show partner withdrawals section"""
    st.subheader(f"Partner Withdrawals - {unit}")
    profit_df = fetch_partner_profits(unit)
    if not profit_df.empty:
        # Filter partners with available balance > 0.01
        eligible_partners = profit_df[profit_df['Available_Now'] >= 0.01]
        if not eligible_partners.empty:
            form = st.form(key=f"withdrawal_form_{unit}")
            with form:
                partner = st.selectbox(
                    "Partner*",
                    eligible_partners['partner_name'].unique()
                )
                available = float(eligible_partners.loc[
                    eligible_partners['partner_name'] == partner,
                    'Available_Now'
                ].values[0])
                cols = st.columns(2)
                with cols[0]:
                    default_amount = min(1000.00, available) if available >= 0.01 else 0.01
                    amount = st.number_input(
                        "Amount (AED)*",
                        min_value=0.01,
                        max_value=available,
                        value=default_amount,
                        step=100.00,
                        format="%.2f"
                    )
                with cols[1]:
                    payment_method = st.selectbox(
                        "Payment Method*",
                        ["Cash", "Bank Transfer", "Cheque"]
                    )
                description = st.text_input(
                    "Purpose*",
                    placeholder="Reason for withdrawal"
                )
                submitted = form.form_submit_button("Process Withdrawal")
                if submitted:
                    try:
                        if not description:
                            st.error("Purpose is required")
                            return
                        amount = float(amount)
                        if amount < 0.01:
                            st.error("Amount must be at least 0.01 AED")
                            return
                        if amount > available:
                            st.error(f"Amount cannot exceed available balance of {available:.2f} AED")
                            return
                        success = record_partner_withdrawal(
                            unit=unit,
                            partner=partner,
                            amount=amount,
                            description=f"{description} ({payment_method})"
                        )
                        if success:
                            st.success("Withdrawal processed successfully!")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error processing withdrawal: {str(e)}")
        else:
            st.info("No partners currently have available funds for withdrawal")
        # Display profit distribution
        st.subheader("Partner Profit Distribution")
        st.dataframe(
            profit_df[[
                "business_unit",
                "partner_name",
                "share",
                "withdrawn",
                "Total_Entitlement",
                "Available_Now"
            ]],
            column_config={
                "business_unit": "Business Unit",
                "partner_name": "Partner",
                "share": st.column_config.NumberColumn("Share %", format="%.1f"),
                "withdrawn": st.column_config.NumberColumn("Withdrawn", format="AED %.2f"),
                "Total_Entitlement": st.column_config.NumberColumn("Total Entitlement", format="AED %.2f"),
                "Available_Now": st.column_config.NumberColumn("Available Now", format="AED %.2f")
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("No partners available for this business unit")

if __name__ == "__main__":
    show_expenses()
