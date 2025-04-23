from supabase import create_client

# Initialize Supabase client
SUPABASE_URL = "https://umtgkoogrtvyqcrzygoe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVtdGdrb29ncnR2eXFjcnp5Z29lIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDUxMzYyNDYsImV4cCI6MjA2MDcxMjI0Nn0.QMrKSOa91fzE7sNWBfhePhRFG05YMwNbvHYK8Fzkjpk"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def clear_sample_data():
    try:
        # List of tables to clear
        tables_to_clear = [
            "inventory",
            "cash_balances",
            "investments",
            "expenses",
            "partnerships",
            "market_prices"
        ]
        
        for table in tables_to_clear:
            response = supabase.table(table).delete().neq("id", "nonexistent").execute()
            if response:
                print(f"Cleared data from table: {table}")
            else:
                print(f"Failed to clear data from table: {table}")
    
    except Exception as e:
        print(f"Error clearing sample data: {str(e)}")

if __name__ == "__main__":
    clear_sample_data()