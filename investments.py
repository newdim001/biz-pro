import streamlit as st
import pandas as pd
from datetime import date, datetime
from supabase import create_client
import traceback

# Initialize Supabase client
SUPABASE_URL = "https://umtgkoogrtvyqcrzygoe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def initialize_cash_balances():
    """Initialize default cash balances if they don't exist."""
    business_units = ["Unit A", "Unit B"]
    default_balance = 10000.0
    try:
        for unit in business_units:
            # Check if balance exists
            response = supabase.table("cash_balances").select("*").eq("business_unit", unit).execute()
            if not response.data:
                # Insert initial balance
                supabase.table("cash_balances").insert({
                    "business_unit": unit,
                    "balance": default_balance,
                    "last_updated": date.today().isoformat()
                }).execute()
    except Exception as e:
        st.error(f"Balance initialization error: {str(e)}")

def fetch_cash_balance(business_unit: str) -> float:
    """Get current cash balance for a business unit."""
    try:
        response = supabase.table("cash_balances").select("balance").eq("business_unit", business_unit).execute()
        return float(response.data[0]["balance"]) if response.data else 10000.0
    except Exception as e:
        st.error(f"Failed to fetch balance: {str(e)}")
        return 10000.0

def update_cash_balance(amount: float, business_unit: str, action: str) -> bool:
    """Update cash balance after validating sufficient funds."""
    try:
        current_balance = fetch_cash_balance(business_unit)
        new_balance = current_balance + amount if action == 'add' else current_balance - amount
        if action == 'subtract' and current_balance < amount:
            st.error(f"Insufficient funds in {business_unit}")
            return False
        # Update balance using upsert with conflict resolution
        response = supabase.table("cash_balances").upsert({
            "business_unit": business_unit,
            "balance": new_balance,
            "last_updated": date.today().isoformat()
        }, on_conflict="business_unit").execute()
        return True if response.data else False
    except Exception as e:
        st.error(f"Failed to update balance: {str(e)}")
        return False

def fetch_investments() -> pd.DataFrame:
    """Fetch all investments from Supabase with error handling."""
    try:
        response = supabase.table("investments").select("*").execute()
        if not response.data:
            st.info("No investments found in the database.")
            return pd.DataFrame(columns=[
                "id", "business_unit", "inv_date", "amount", "investor", "description", "created_at"
            ])
        df = pd.DataFrame(response.data)
        # Ensure required columns exist
        required_cols = ["business_unit", "inv_date", "amount", "investor"]
        for col in required_cols:
            if col not in df.columns:
                df[col] = None if col != "amount" else 0.0
        return df
    except Exception as e:
        st.error(f"Failed to load investments: {str(e)}")
        print(traceback.format_exc())  # Log the full traceback for debugging
        return pd.DataFrame(columns=[
            "id", "business_unit", "inv_date", "amount", "investor", "description", "created_at"
        ])

def add_investment(unit: str, inv_date: date, amount: float, investor: str, description: str) -> bool:
    """Add a new investment to Supabase and update the cash balance."""
    try:
        # First update the cash balance
        if not update_cash_balance(amount, unit, 'add'):
            return False
        # Then add the investment record
        investment_data = {
            "business_unit": unit,
            "inv_date": inv_date.isoformat(),
            "amount": float(amount),
            "investor": investor,
            "description": description or f"Investment from {investor}"
        }
        response = supabase.table("investments").insert(investment_data).execute()
        return bool(response.data)
    except Exception as e:
        st.error(f"Failed to add investment: {str(e)}")
        print(traceback.format_exc())  # Log the full traceback for debugging
        # Attempt to rollback cash balance update
        update_cash_balance(amount, unit, 'subtract')
        return False

def show_investments():
    """Complete investment management interface."""
    # Authentication check
    if 'user' not in st.session_state:
        st.error("Please log in")
        return
    user = st.session_state['user']
    if not has_permission(user, 'investments'):
        st.error("Permission denied")
        return

    # Initialize data
    initialize_cash_balances()
    investments_df = fetch_investments()

    if investments_df.empty:
        st.session_state.investments = pd.DataFrame(columns=[
            "business_unit", "inv_date", "amount", "investor", "description"
        ])
    else:
        st.session_state.investments = investments_df

    st.title("💼 Investment Management")

    # Determine which units to show based on user permissions
    units = []
    if user['business_unit'] in ['All', 'Unit A']:
        units.append('Unit A')
    if user['business_unit'] in ['All', 'Unit B']:
        units.append('Unit B')

    # Create tabs for each business unit
    tabs = st.tabs(units)
    for i, unit in enumerate(units):
        with tabs[i]:
            # New investment form
            with st.form(f"new_investment_{unit}", clear_on_submit=True):
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
                submitted = st.form_submit_button("Record Investment")
                if submitted:
                    if not investor:
                        st.error("Investor name is required")
                    elif amount <= 0:
                        st.error("Amount must be positive")
                    else:
                        if add_investment(unit, inv_date, amount, investor, desc):
                            st.success("Investment recorded successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to record investment")

            # Investment history
            st.subheader(f"Investment History - {unit}")
            if 'investments' in st.session_state:
                unit_investments = st.session_state.investments[
                    st.session_state.investments['business_unit'] == unit
                ].copy()
                if not unit_investments.empty:
                    # Convert date strings to datetime objects for sorting
                    unit_investments['inv_date'] = pd.to_datetime(unit_investments['inv_date'])
                    # Display metrics
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        total_invested = unit_investments['amount'].sum()
                        st.metric("Total Invested", f"AED {total_invested:,.2f}")
                    with col2:
                        last_investment = unit_investments.iloc[-1]
                        st.metric(
                            "Last Investment",
                            f"AED {last_investment['amount']:,.2f}",
                            last_investment['investor']
                        )
                    # Display dataframe
                    st.dataframe(
                        unit_investments.sort_values('inv_date', ascending=False)[
                            ['inv_date', 'amount', 'investor', 'description']
                        ].rename(columns={
                            'inv_date': 'Date',
                            'amount': 'Amount (AED)',
                            'investor': 'Investor',
                            'description': 'Description'
                        }),
                        column_config={
                            "Date": st.column_config.DateColumn("Date", format="YYYY-MM-DD"),
                            "Amount (AED)": st.column_config.NumberColumn(
                                "Amount (AED)",
                                format="AED %.2f"
                            )
                        },
                        use_container_width=True,
                        hide_index=True
                    )
                    # Export button
                    csv = unit_investments.to_csv(index=False)
                    st.download_button(
                        "📥 Export as CSV",
                        data=csv,
                        file_name=f"{unit}_investments.csv",
                        mime="text/csv"
                    )
                else:
                    st.info(f"No investments found for {unit}")
            else:
                st.info("No investment data available")

if __name__ == "__main__":
    show_investments()
