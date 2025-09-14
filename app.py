# Import the necessary libraries
import streamlit as st
import pandas as pd
import os
import re # We'll use this for advanced text matching
import altair as alt # Import the Altair library
from PIL import Image # Used for the logo favicon

# --- Page Configuration & Favicon ---
try:
    logo = Image.open("lic_logo.png")
    st.set_page_config(
        page_title="P&GS Dossier",
        page_icon=logo,
        layout="centered",
        initial_sidebar_state="expanded"
    )
except FileNotFoundError:
    st.set_page_config(page_title="P&GS Dossier", page_icon="🏢", layout="centered")

# --- Custom CSS for Buttons and Table Header ---
st.markdown("""
<style>
    /* HIDE THE STREAMLIT TOOLBAR (Fork, GitHub buttons) */
    [data-testid="stToolbar"] {
        visibility: hidden;
        height: 0%;
        position: fixed;
    }
    [data-testid="stDecoration"] {
        visibility: hidden;
        height: 0%;
        position: fixed;
    }
    
    /* Define LIC Colors for easy reference */
    :root {
        --lic-blue: #0033A0;
        --lic-yellow: #FFD700;
        --lic-white: #FFFFFF;
    }

    /* Button Styling - Blue with Yellow Hover */
    .stButton > button {
        background-color: var(--lic-blue);
        color: var(--lic-white);
        border: 2px solid var(--lic-blue);
        border-radius: 8px;
        transition: all 0.2s ease-in-out;
        font-weight: bold;
    }
    .stButton > button:hover {
        background-color: var(--lic-yellow);
        color: var(--lic-blue);
        border-color: var(--lic-yellow);
    }
    .stButton > button:focus {
        box-shadow: 0 0 0 0.2rem rgba(255, 215, 0, 0.5) !important;
    }

    /* Table Header Styling */
    .stDataFrame th {
        background-color: var(--lic-blue);
        color: var(--lic-white);
    }
</style>
""", unsafe_allow_html=True)


# --- User Authentication & Data ---
USER_CREDENTIALS = {
    "k.anand": {"password": "pgsmsect@zochennai", "role": "admin", "name": "Anand K."},
    "user.chennaizo": {"password": "userpwd@southzone", "role": "user", "name": "South Zone User"}
}
DATA_FILE = 'data.xlsx'

# --- Login Function (FIXED: Simplified to remove scrollbar) ---
def check_password():
    if "authentication_status" not in st.session_state:
        st.session_state.authentication_status = None
    if not st.session_state.authentication_status:
        st.title("🔐 Welcome to the South Zone P&GS Dossier")
        st.write("Please log in to continue.")
        
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Log In")
            if submitted:
                if username in USER_CREDENTIALS and USER_CREDENTIALS[username]["password"] == password:
                    st.session_state.authentication_status = True
                    st.session_state.role = USER_CREDENTIALS[username]["role"]
                    st.session_state.name = USER_CREDENTIALS[username]["name"]
                    st.rerun()
                else:
                    st.error("😕 Incorrect username or password.")
        return False
    return True

# --- Data Loading Function (FIXED: Added robust data cleaning) ---
@st.cache_data(show_spinner=False)
def load_data():
    if not os.path.exists(DATA_FILE): return pd.DataFrame()
    df = pd.read_excel(DATA_FILE)
    new_cols = {}
    fund_col_keys = []
    for col in df.columns:
        clean_col = col.strip().lower()
        if clean_col == 'state': new_cols[col] = 'state'
        elif clean_col == 'unit': new_cols[col] = 'unit'
        elif clean_col == 'customer name': new_cols[col] = 'customer_name'
        elif clean_col == 'segment': new_cols[col] = 'segment'
        elif clean_col == 'gratuity': new_cols[col] = 'gratuity'
        elif clean_col == 'superannuation': new_cols[col] = 'superannuation'
        elif clean_col == 'leave encashment': new_cols[col] = 'leave_encashment'
        elif re.match(r'closing balance as on', clean_col, re.IGNORECASE):
            try:
                date_str = col.strip().split(' ')[-1]
                clean_date = pd.to_datetime(date_str, format='%d.%m.%Y').strftime('%Y-%m-%d')
                new_name = f'fund_{clean_date}'
                new_cols[col] = new_name
                fund_col_keys.append(new_name)
            except ValueError:
                print(f"--- WARNING: Could not parse date from column '{col}'. Skipping. ---")
                pass
    df.rename(columns=new_cols, inplace=True)

    for col_key in fund_col_keys:
        if col_key in df.columns:
            df[col_key] = pd.to_numeric(df[col_key], errors='coerce')

    return df

# --- Helper function to display Y/N fields beautifully ---
def display_policy_status(customer_data):
    st.subheader("Policy Details")
    cols = st.columns(3)
    policies = {'gratuity': 'Gratuity', 'superannuation': 'Superannuation', 'leave_encashment': 'Leave Encashment'}
    for i, (key, name) in enumerate(policies.items()):
        if key in customer_data.columns:
            status = customer_data[key].iloc[0]
            if pd.notna(status) and str(status).strip().upper() == 'Y':
                cols[i].success(f"{name}", icon="✅")
            else:
                cols[i].error(f"{name}", icon="❌")

# --- FINAL FIX: Helper function to display fund size and trend chart ---
def display_fund_details(customer_data):
    fund_cols = sorted([col for col in customer_data.columns if col.startswith('fund_')], reverse=True)
    
    most_recent_fund_size = None
    most_recent_date_str = None

    # FIX 1: Find the most recent VALID fund size, not just the newest column
    for col in fund_cols:
        fund_value = customer_data[col].iloc[0]
        if pd.notna(fund_value):
            most_recent_fund_size = fund_value
            most_recent_date_str = col.split('_')[-1]
            break # Stop as soon as we find the first valid one

    if most_recent_fund_size is None:
        st.warning("No fund size data available for this customer.")
        return

    most_recent_date = pd.to_datetime(most_recent_date_str).strftime('%d.%m.%Y')
    st.metric(label=f"💰 Most Recent Fund Size (as on {most_recent_date})", value=f"₹ {most_recent_fund_size:,.2f} Crores")

    fund_series = customer_data[fund_cols].iloc[0]
    fund_series.index = pd.to_datetime([col.split('_')[-1] for col in fund_cols])
    fund_series.sort_index(inplace=True)
    valid_funds = fund_series.dropna()
    
    if len(valid_funds) > 1:
        st.subheader("Fund Size Trend (in Crores)")
        chart_data = valid_funds.reset_index()
        chart_data.columns = ['Date', 'Fund Size']
        
        chart = (
            alt.Chart(chart_data)
            .mark_line(point=True, strokeWidth=3)
            .encode(
                # FIX 2: Format the x-axis to be clear (e.g., 'Mar 2023')
                x=alt.X('Date:T', title='Date', axis=alt.Axis(format='%b %Y')),
                y=alt.Y('Fund Size:Q', title='Fund Size (in Crores)'),
                tooltip=['Date', 'Fund Size']
            )
            .properties(background='transparent')
        )
        st.altair_chart(chart, use_container_width=True, theme="streamlit")


# --- VIEW 1: BROWSE BY LOCATION ---
def render_location_view():
    st.header("Browse by Location")
    if 'loc_state' not in st.session_state: st.session_state.loc_state = None
    if 'loc_unit' not in st.session_state: st.session_state.loc_unit = None
    def select_state(state): st.session_state.loc_state = state
    def select_unit(unit): st.session_state.loc_unit = unit
    def back_to_states(): st.session_state.loc_state = None; st.session_state.loc_unit = None
    def back_to_units(): st.session_state.loc_unit = None
    df = st.session_state.df
    if st.session_state.loc_state is None:
        st.subheader("Select a State")
        states = sorted(df['state'].unique())
        cols = st.columns(4)
        for i, state in enumerate(states):
            cols[i % 4].button(state, on_click=select_state, args=(state,), use_container_width=True)
    elif st.session_state.loc_unit is None:
        st.subheader(f"Select a Unit in {st.session_state.loc_state}")
        state_df = df[df['state'] == st.session_state.loc_state]
        units = sorted(state_df['unit'].unique())
        cols = st.columns(4)
        for i, unit in enumerate(units):
            cols[i % 4].button(unit, on_click=select_unit, args=(unit,), use_container_width=True)
        st.button("← Back to State Selection", on_click=back_to_states)
    else:
        st.button("← Back to Unit Selection", on_click=back_to_units)
        st.info(f"Current Selection: **{st.session_state.loc_state} → {st.session_state.loc_unit}**")
        unit_df = df[(df['state'] == st.session_state.loc_state) & (df['unit'] == st.session_state.loc_unit)]
        segments = sorted(unit_df['segment'].unique())
        selected_segment = st.selectbox("Select a Segment:", options=["--Select--"] + segments)
        if selected_segment != "--Select--":
            segment_df = unit_df[unit_df['segment'] == selected_segment]
            customers = sorted(segment_df['customer_name'].unique())
            selected_customer = st.selectbox("Select a Customer:", options=["--Select--"] + customers)
            if selected_customer != "--Select--":
                customer_df = segment_df[segment_df['customer_name'] == selected_customer]
                st.divider()
                st.subheader(f"Portfolio Details for: {selected_customer}")
                display_fund_details(customer_df)
                display_policy_status(customer_df)

# --- VIEW 2: BROWSE BY SEGMENT ---
def render_segment_view():
    st.header("Browse by Segment")
    if 'seg_segment' not in st.session_state: st.session_state.seg_segment = None
    def select_segment(segment): st.session_state.seg_segment = segment
    def back_to_segments(): st.session_state.seg_segment = None
    df = st.session_state.df
    if st.session_state.seg_segment is None:
        st.subheader("Select a Segment")
        segments = sorted(df['segment'].unique())
        cols = st.columns(4)
        for i, segment in enumerate(segments):
            cols[i % 4].button(segment, on_click=select_segment, args=(segment,), use_container_width=True)
    else:
        st.button("← Back to Segment Selection", on_click=back_to_segments)
        st.info(f"Showing all customers in segment: **{st.session_state.seg_segment}**")
        segment_df = df[df['segment'] == st.session_state.seg_segment]
        display_df = segment_df[['customer_name', 'state', 'unit']].copy()
        display_df.rename(columns={'customer_name': 'Customer Name', 'state': 'State', 'unit': 'Unit'}, inplace=True)
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        st.divider()
        customers = sorted(segment_df['customer_name'].unique())
        selected_customer = st.selectbox("Select a customer from the table above to view details:", options=["--Select--"] + customers)
        if selected_customer != "--Select--":
            customer_df = segment_df[segment_df['customer_name'] == selected_customer]
            display_fund_details(customer_df)
            display_policy_status(customer_df)

# --- Main Application Logic ---
if "authentication_status" not in st.session_state:
    st.session_state.authentication_status = None

if st.session_state.authentication_status:
    # --- MAIN APP SCREEN ---
    st.session_state.df = load_data()
    with st.sidebar:
        if os.path.exists("lic_logo.png"):
            st.image("lic_logo.png", use_container_width=True)
        st.success(f"Welcome {st.session_state['name']}!")
        if st.session_state["role"] == "admin":
            st.header("👑 Admin Panel")
            st.info("To update data, upload a new `data.xlsx` file to the project's GitHub repository.")
        st.divider()
        if 'view_mode' in st.session_state and st.session_state.view_mode is not None:
            if st.button("⬅️ Return to Main Menu", use_container_width=True):
                st.session_state.view_mode = None
                for key in ['loc_state', 'loc_unit', 'seg_segment']:
                    if key in st.session_state: del st.session_state[key]
                st.rerun()
        if st.button("Log Out", use_container_width=True):
            for key in st.session_state.keys():
                del st.session_state[key]
            st.rerun()
    
    st.title("Client Portfolio Explorer")
    if 'view_mode' not in st.session_state:
        st.session_state.view_mode = None
    if st.session_state.df.empty:
        st.warning("No data file found or the file is empty. Please contact the administrator.")
    elif st.session_state.view_mode is None:
        st.write("Choose how you would like to explore the client data.")
        col1, col2 = st.columns(2)
        if col1.button("🌍 Browse by Location", use_container_width=True):
            st.session_state.view_mode = 'location'
            st.rerun()
        if col2.button("📊 Browse by Segment", use_container_width=True):
            st.session_state.view_mode = 'segment'
            st.rerun()
    elif st.session_state.view_mode == 'location':
        render_location_view()
    elif st.session_state.view_mode == 'segment':
        render_segment_view()
else:
    # --- LOGIN SCREEN ---
    check_password()
