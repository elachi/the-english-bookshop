import streamlit as st
from datetime import datetime, timedelta
from supabase import create_client
import os
import re

# 1. MUST BE THE FIRST STREAMLIT COMMAND IN YOUR FILE
st.set_page_config(
    page_title="The English Bookstore stamp programme", 
    page_icon="📚", 
    layout="centered"
)

# 2. INJECT CUSTOM CSS TO HIDE THE MENUS & FOOTER
st.markdown("""
    <style>
        /* Hides the top-right hamburger menu and Deploy button */
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        
        /* Hides the default "Made with Streamlit" footer */
        footer {visibility: hidden;}
        
        /* Optional: Shifts the main content up slightly so there isn't a blank gap at the top */
        .block-container {
            padding-top: 2rem;
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

# Helper function for Swedish mobile validation
def validate_swedish_mobile(mobile: str) -> bool:
    # Must start with 07 and be exactly 10 digits total
    pattern = r"^07\d{8}$"
    return bool(re.match(pattern, mobile.strip()))

# --- AUTHENTICATION GATE ---
if not st.session_state.logged_in:
    st.image("Logo_EnglishBookshop_logo.png", width=150)

    st.title("📚 The stamp loyalty programme")
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

# --- MAIN SCANNER VIEW ---
st.image("Logo_EnglishBookshop_logo.png", width=150)

search_input = st.text_input(
    "Enter Customer Mobile Number or Email:", 
    placeholder="e.g., 0712345678 or jane@hotmail.com",
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
        customer_id = data["id"]
        current_stamps = data["stamps"]
        discounts = data.get("free_cups", 0)  
        discount_expiries = data.get("free_cup_expiries", []) or []

        st.subheader(f"Member: {customer_name} (Mobile: {customer_mobile})")

        # --- EDIT CUSTOMER INFO SECTION WITH CONFIRMATION ---
        with st.expander("✏️ Edit Customer Information"):
            with st.form("edit_customer_form"):
                new_name = st.text_input("Customer Name", value=customer_name)
                new_mobile = st.text_input("Mobile Number (Swedish format e.g. 0712345678)", value=customer_mobile)
                new_email = st.text_input("Email Address", value=data.get("email", ""))
                
                update_btn = st.form_submit_button("Save Changes", use_container_width=True)
                
                if update_btn:
                    cleaned_mobile = new_mobile.strip()
                    if not validate_swedish_mobile(cleaned_mobile):
                        st.error("Invalid Swedish mobile number format! Must start with 07 and be 10 digits long (e.g., 0712345678).")
                    else:
                        try:
                            supabase.table("loyalty_cards").update({
                                "name": new_name.strip(),
                                "mobile_number": cleaned_mobile,
                                "email": new_email.strip().lower()
                            }).eq("id", customer_id).execute()
                            
                            st.success("✅ Customer information updated successfully!")
                            st.toast("Changes saved!", icon="🎉")
                        except Exception as err:
                            st.error(f"Failed to update customer: {err}")

        # --- EARNED BOOKSTORE DISCOUNTS BANK ---
        st.markdown("### 🏷️ Earned Bookstore Discounts (Bank: Up to 2)")
        gift_cols = st.columns(2)
        for g in range(2):
            with gift_cols[g]:
                if g < discounts:
                    st.success(f"Discount #{g+1} Available!")
                else:
                    st.info(f"Discount #{g+1} Locked")
    else:
        st.warning("No customer found matching that mobile number or email.")