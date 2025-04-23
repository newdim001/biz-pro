import streamlit as st
import pandas as pd
from supabase import create_client
from components.auth import has_permission  # Import the has_permission function

# Initialize Supabase client
SUPABASE_URL = "https://umtgkoogrtvyqcrzygoe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVtdGdrb29ncnR2eXFjcnp5Z29lIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDUxMzYyNDYsImV4cCI6MjA2MDcxMjI0Nn0.QMrKSOa91fzE7sNWBfhePhRFG05YMwNbvHYK8Fzkjpk"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def initialize_partnership_data():
    """Fetch partnership data from Supabase"""
    try:
        response = supabase.table("partnerships").select("business_unit, partner_name, share").execute()
        if not response.data:
            st.warning("No data found in the partnerships table. Initializing empty data.")
            return {
                'Unit A': pd.DataFrame(columns=["business_unit", "partner_name", "share"]),
                'Unit B': pd.DataFrame(columns=["business_unit", "partner_name", "share"])
            }
        partnerships_data = response.data

        # Organize data by business unit
        unit_a_data = [p for p in partnerships_data if p.get('business_unit') == 'Unit A']
        unit_b_data = [p for p in partnerships_data if p.get('business_unit') == 'Unit B']

        # Ensure required columns exist
        unit_a_df = pd.DataFrame(unit_a_data)
        unit_b_df = pd.DataFrame(unit_b_data)

        # Add missing columns if necessary
        for df in [unit_a_df, unit_b_df]:
            if 'partner_name' not in df.columns:
                df['partner_name'] = None
            if 'share' not in df.columns:
                df['share'] = 0.0

        return {
            'Unit A': unit_a_df,
            'Unit B': unit_b_df
        }
    except Exception as e:
        st.error(f"Error fetching partnership data: {str(e)}")
        return {
            'Unit A': pd.DataFrame(columns=["business_unit", "partner_name", "share"]),
            'Unit B': pd.DataFrame(columns=["business_unit", "partner_name", "share"])
        }

def show_partnership():
    """Main function to display partnership management interface"""
    user = st.session_state.get('user')
    if not user or not has_permission(user, 'partnership'):  # Check user permissions
        st.error("You don't have permission to access this page")
        return

    # Initialize partnership data
    st.session_state.partners = initialize_partnership_data()
    st.header("👥 Partnership Management")

    # Determine which units to show based on user's business unit
    units_to_show = []
    if user['business_unit'] in ['All', 'Unit A']:
        units_to_show.append('Unit A')
    if user['business_unit'] in ['All', 'Unit B']:
        units_to_show.append('Unit B')

    unit_tabs = st.tabs(units_to_show)
    for i, unit in enumerate(units_to_show):
        with unit_tabs[i]:
            st.subheader(f"{unit} Ownership Structure")
            cols = st.columns(2)
            with cols[0]:
                show_existing_partners(unit)
            with cols[1]:
                show_add_partner_form(unit)

def show_existing_partners(unit):
    """Display existing partners for a given unit"""
    partners_df = st.session_state.partners[unit]

    # Ensure required columns exist
    if 'partner_name' not in partners_df.columns or 'share' not in partners_df.columns:
        st.error(f"Critical error: Missing required columns ('partner_name', 'share') in {unit} partnerships data.")
        return

    if not partners_df.empty:
        st.write("Current Partners:")
        total_allocated = partners_df['share'].sum()
        st.dataframe(partners_df)
        st.metric("Total Allocated", f"{total_allocated:.2f}%")
        remaining_pct = max(0, 100 - total_allocated)
        st.metric("Remaining", f"{remaining_pct:.2f}%")

        if st.checkbox(f"Remove Partner from {unit}", key=f"remove_checkbox_{unit}"):
            partner_to_remove = st.selectbox(
                "Select Partner to Remove",
                partners_df['partner_name'].unique(),
                key=f"remove_{unit}"
            )
            if st.button(f"Confirm Removal of {partner_to_remove}", key=f"confirm_remove_{unit}"):
                removed_share = partners_df.loc[partners_df['partner_name'] == partner_to_remove, 'share'].values[0]
                # Delete partner from Supabase
                supabase.table("partnerships").delete() \
                    .eq("partner_name", partner_to_remove) \
                    .eq("business_unit", unit) \
                    .execute()
                # Update session state
                st.session_state.partners[unit] = partners_df[partners_df['partner_name'] != partner_to_remove]
                st.session_state[f'removed_share_{unit}'] = removed_share
                st.session_state[f'partner_removed_{unit}'] = True
                st.success(f"{partner_to_remove} removed. Freed share: {removed_share:.1f}%")

        if st.session_state.get(f'partner_removed_{unit}', False):
            handle_freed_share(unit)
    else:
        st.info(f"No partners added for {unit} yet")

def handle_freed_share(unit):
    """Handle freed share after partner removal"""
    removed_share = st.session_state.get(f'removed_share_{unit}', 0)
    st.subheader(f"Handle Freed Share ({removed_share:.1f}%)")
    action = st.radio(
        "Action",
        ["Redistribute Among Existing Partners", "Assign to a New Partner"],
        key=f"action_{unit}"
    )

    if action == "Redistribute Among Existing Partners":
        if st.button(f"Redistribute {removed_share:.1f}%", key=f"redist_{unit}"):
            if not st.session_state.partners[unit].empty:
                # Redistribute shares among existing partners
                st.session_state.partners[unit]['share'] += removed_share / len(st.session_state.partners[unit])
                # Update Supabase records
                for _, row in st.session_state.partners[unit].iterrows():
                    supabase.table("partnerships").update({
                        "share": row['share']
                    }).eq("partner_name", row['partner_name']).eq("business_unit", unit).execute()
                st.success(f"Redistributed {removed_share:.1f}% among existing partners")
                del st.session_state[f'removed_share_{unit}']
                del st.session_state[f'partner_removed_{unit}']
            else:
                st.warning("No existing partners to redistribute to")
    elif action == "Assign to a New Partner":
        with st.form(f"new_partner_form_{unit}"):
            new_partner_name = st.text_input("New Partner Name", key=f"new_name_{unit}")
            new_partner_share = st.number_input(
                "Share Percentage",
                min_value=0.1,
                max_value=float(removed_share),
                value=float(min(20, removed_share)),
                step=0.1,
                format="%.1f",
                key=f"new_share_{unit}"
            )
            if st.form_submit_button(f"Add New Partner to {unit}"):
                if new_partner_name.strip() == "":
                    st.error("Please enter a valid partner name")
                elif new_partner_name in st.session_state.partners[unit]['partner_name'].values:
                    st.error("Partner with this name already exists")
                else:
                    # Add new partner to Supabase
                    supabase.table("partnerships").insert({
                        "business_unit": unit,
                        "partner_name": new_partner_name,
                        "share": new_partner_share,
                        "withdrawn": False
                    }).execute()
                    # Update session state
                    st.session_state.partners[unit] = pd.concat([
                        st.session_state.partners[unit],
                        pd.DataFrame([{
                            "business_unit": unit,
                            "partner_name": new_partner_name,
                            "share": new_partner_share
                        }])
                    ], ignore_index=True)
                    remaining_share = removed_share - new_partner_share
                    if remaining_share > 0 and not st.session_state.partners[unit].empty:
                        st.session_state.partners[unit]['share'] += remaining_share / len(st.session_state.partners[unit])
                        # Update Supabase records
                        for _, row in st.session_state.partners[unit].iterrows():
                            supabase.table("partnerships").update({
                                "share": row['share']
                            }).eq("partner_name", row['partner_name']).eq("business_unit", unit).execute()
                    st.success(f"Added {new_partner_name} with {new_partner_share:.1f}% share")
                    del st.session_state[f'removed_share_{unit}']
                    del st.session_state[f'partner_removed_{unit}']

def show_add_partner_form(unit):
    """Display form to add a new partner"""
    st.subheader(f"Add New Partner - {unit}")
    with st.form(f"add_partner_form_{unit}"):
        partner_name = st.text_input("Partner Name", key=f"name_{unit}")
        partners_df = st.session_state.partners[unit]

        if not partners_df.empty:
            total_allocated = partners_df['share'].sum()
            remaining_pct = max(0, 100 - total_allocated)
            if remaining_pct > 0:
                share = st.slider(
                    "Share Percentage",
                    min_value=0.1,
                    max_value=float(remaining_pct),
                    value=float(min(20, remaining_pct)),
                    step=0.1,
                    format="%.1f%%",
                    key=f"share_{unit}"
                )
            else:
                st.warning("No remaining share available")
                share = 0
        else:
            share = st.slider(
                "Share Percentage",
                min_value=0.1,
                max_value=100.0,
                value=40.0,
                step=0.1,
                format="%.1f%%",
                key=f"share_{unit}"
            )

        if st.form_submit_button(f"Add Partner to {unit}"):
            if partner_name.strip() == "":
                st.error("Please enter a partner name")
            elif share <= 0:
                st.error("Share percentage must be greater than 0")
            elif partner_name in partners_df['partner_name'].values:
                st.error("Partner with this name already exists")
            else:
                current_total = partners_df['share'].sum()
                if (current_total + share) > 100:
                    st.error(f"Adding {share:.1f}% would exceed 100% (current total: {current_total:.1f}%)")
                else:
                    # Add new partner to Supabase
                    supabase.table("partnerships").insert({
                        "business_unit": unit,
                        "partner_name": partner_name,
                        "share": share,
                        "withdrawn": False
                    }).execute()
                    # Update session state
                    st.session_state.partners[unit] = pd.concat([
                        partners_df,
                        pd.DataFrame([{
                            "business_unit": unit,
                            "partner_name": partner_name,
                            "share": share
                        }])
                    ], ignore_index=True)
                    st.success(f"Added {partner_name} with {share:.1f}% share to {unit}")

if __name__ == "__main__":
    show_partnership()