import streamlit as st
from datetime import datetime, timedelta
from supabase import create_client
import os

# 1. MUST BE THE FIRST STREAMLIT COMMAND IN YOUR FILE
st.set_page_config(
    page_title="Drop Caffee Loyalty Program", 
    page_icon="☕", 
    layout="centered"
)

# 2. INJECT CUSTOM CSS TO HIDE THE MENUS & FOOTER
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        .block-container {
            padding-top: 2rem;
        }
        h1, h2, h3, h4, h5, h6, p, span, label, div, .stMarkdown {
            color: #0f2648 !important;
        }
    </style>
""", unsafe_allow_html=True)

# Supabase Connection Setup
try:
    SUPABASE_URL = st.secrets.get("SUPABASE_URL") or os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = st.secrets.get("SUPABASE_KEY") or os.environ.get("SUPABASE_KEY")
except Exception:
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

@st.cache_resource
def init_supabase():
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    return create_client(SUPABASE_URL.strip().rstrip('/'), SUPABASE_KEY)

supabase = init_supabase()

# Session State Initialization
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "role" not in st.session_state:
    st.session_state.role = ""
if "scanner_search" not in st.session_state:
    st.session_state.scanner_search = ""
if "confirm_redeem" not in st.session_state:
    st.session_state.confirm_redeem = False

def clear_scanner():
    st.session_state.scanner_search = ""
    st.session_state.confirm_redeem = False


# --- AUTHENTICATION GATE ---
if not st.session_state.logged_in:
    st.image("DropCaffee/images/dropcafe.png", width=150)
    

    st.title("☕ Drop Caffee Loyalty programme")
    with st.form("login_form"):
        username_input = st.text_input("Username")
        password_input = st.text_input("Password", type="password")
        login_btn = st.form_submit_button("Log In", use_container_width=True)
        
        if login_btn:
            if not supabase:
                st.error("Database connection missing.")
            else:
                res = supabase.table("app_users").select("*").eq("username", username_input.strip()).eq("password", password_input).execute()
                if res.data:
                    st.session_state.logged_in = True
                    st.session_state.username = res.data[0]["username"]
                    st.session_state.role = res.data[0]["role"]
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid credentials.")
    st.stop()

# --- SIDEBAR USER INFO ---
st.sidebar.header("👤 Staff Account")
st.sidebar.success(f"User: **{st.session_state.username}**\n\nRole: **{st.session_state.role.upper()}**")
if st.sidebar.button("🚪 Log Out", use_container_width=True):
    st.session_state.logged_in = False
    st.rerun()

#
# --- MAIN SCANNER VIEW ---

st.image("DropCaffee/images/dropcafe.png", width=150)

search_input = st.text_input(
    "Enter Customer Mobile Number or Email:", 
    placeholder="e.g., 555-0200 or jane@hotmail.com",
    key="scanner_search"
)

# Dynamic button that always appears: Search when empty, Clear when active
if st.session_state.scanner_search:
    st.button("🔄 Clear / Scan New Customer", on_click=clear_scanner)
else:
    if st.button("🔍 Find Customer"):
        st.rerun()

if search_input:
    member_found = False
    data = None
    try:
        query_val = search_input.strip()
        res = supabase.table("loyalty_cards").select("*").eq("mobile_number", query_val).execute()
        if not res.data:
            res = supabase.table("loyalty_cards").select("*").eq("email", query_val.lower()).execute()
        
        if res.data:
            data = res.data[0]
            member_found = True
    except Exception as e:
        st.error(f"Database error: {e}")

    if member_found:
        customer_name = data.get("name", "Valued Customer")
        customer_mobile = data["mobile_number"]
        current_stamps = data["stamps"]
        current_counter = data.get("counter", 0) or 0  # <--- Fetches lifetime counter
        discounts = data.get("free_cups", 0)  # Database column holding banked discounts
        discount_expiries = data.get("free_cup_expiries", []) or []

        st.subheader(f"Member: {customer_name} (Mobile: {customer_mobile})")

        # --- EARNED BOOKSTORE DISCOUNTS BANK (Up to 2) ---
        st.markdown("### 🏷️ Free Coffee Cup (Bank: Up to 2)")
        gift_cols = st.columns(2)
        for g in range(2):
            with gift_cols[g]:
                if g < discounts:
                    exp_str = discount_expiries[g][:10] if g < len(discount_expiries) else "N/A"
                    st.image("coffee-cup.png", width=35)
                else:
                    st.info(f"Cup #{g+1} Locked")

        # --- ADD STAMP BUTTON & LIFETIME COUNTER LOGIC ---
        if st.button("➕ Add Stamp", use_container_width=True):
            new_stamps = current_stamps + 1
            new_counter = current_counter + 1  # <--- Counter increments infinitely and never resets
            
            update_data = {
                "stamps": new_stamps,
                "counter": new_counter,         # <--- Saved to Supabase counter column
                "last_stamp_at": datetime.utcnow().isoformat(),
                "last_visit": datetime.utcnow().isoformat()
            }

            # Check if user reached 9 stamps to earn a free coffee cup
            if new_stamps >= 9:
                if discounts < 2:
                    new_stamps = 0  # Reset current card stamps back to 0
                    update_data["stamps"] = 0
                    update_data["free_cups"] = discounts + 1
                    
                    expiry_date = (datetime.utcnow() + timedelta(days=90)).isoformat()
                    discount_expiries.append(expiry_date)
                    update_data["free_cup_expiries"] = discount_expiries
                    st.success("🎉 Stamp card completed! A free coffee cup has been added to their bank!")
                else:
                    st.warning("⚠️ Customer already has the maximum of 2 banked discounts! Stamps capped at 9.")
                    update_data["stamps"] = 9

            try:
                supabase.table("loyalty_cards").update(update_data).eq("mobile_number", customer_mobile).execute()
                st.toast("Stamp added successfully!", icon="☕")
                st.rerun()
            except Exception as err:
                st.error(f"Failed to add stamp: {err}")
    else:
        st.warning("No customer found matching that mobile number or email.")