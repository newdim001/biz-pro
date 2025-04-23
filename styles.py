def get_common_styles():
    return """
    <style>
        /* ===== CORE RESETS ===== */
        html, body, .stApp {
            font-size: 14px !important;
            line-height: 1.3 !important;
        }

        /* ===== METRIC CARDS ===== */
        div[data-testid="stMetric"] {
            margin: 4px 0 !important;
            padding: 6px 10px !important;
            border-radius: 5px !important;
            background: #f8f9fa !important;  /* Light gray background */
            border: 1px solid #e1e4e8 !important;  /* Border color */
        }
        
        div[data-testid="stMetricValue"] > div {
            font-size: 14px !important;
            font-weight: 500 !important;
            color: #2e59d9 !important;  /* Blue values (unchanged) */
        }
        
        div[data-testid="stMetricLabel"] > div {
            font-size: 14px !important;
            color: #5a5c69 !important;  /* Gray labels (unchanged) */
            letter-spacing: 0.3px !important;
        }

        /* ===== TITLES & HEADERS ===== */
        .main-title {
            font-size: 16px !important;
            font-weight: 600 !important;
            color: #2e59d9 !important;  /* Blue title (unchanged) */
            margin-bottom: 10px !important;
        }
        
        .section-header {
            font-size: 16px !important;
            border-bottom: 1px solid #eee !important;  /* Light gray border */
            padding-bottom: 3px !important;
            margin: 12px 0 8px 0 !important;
            color: inherit !important;  /* Inherits default text color */
        }

        /* ===== PROVISIONAL PROFIT ===== */
        .provisional-profit {
            font-size: 14px !important;
            padding: 6px 10px !important;
            background-color: #f8f9fa !important;  /* Light gray */
            border-left: 3px solid #4e73df !important;  /* Darker blue */
        }
        .provisional-profit p {
            margin: 0 !important;
            color: #5a5c69 !important;  /* Gray text */
        }
        .provisional-profit h3 {
            color: #2e59d9 !important;  /* Blue value */
            margin: 2px 0 0 0 !important;
        }

        /* ===== TABLES ===== */
        .dataframe {
            font-size: 14px !important;
        }
        .dataframe thead th {
            background-color: #f7fafc !important;  /* Header background */
            color: #4a5568 !important;  /* Gray text */
        }

        /* ===== FORM CONTROLS ===== */
        .stTextInput input, 
        .stNumberInput input, 
        .stSelectbox select {
            font-size: 12px !important;
            border: 1px solid #e1e4e8 !important;  /* Light gray border */
        }

        /* ===== COLOR PALETTE PRESERVATION ===== */
        /* Blues */
        --primary-blue: #2e59d9;
        --dark-blue: #2c5282;
        --light-blue: #f0f5ff;
        
        /* Grays */
        --dark-gray: #4a5568;
        --medium-gray: #5a5c69;
        --light-gray: #e1e4e8;
    </style>
    """