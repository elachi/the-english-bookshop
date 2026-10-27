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







st.set_page_config(page_title="Drop Caffee", page_icon="☕")
#, layout="wide"

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
                    st.caption(f"Free Cup of Coffee #{g+1} (Ready! Exp: {exp_str})")
                else:
                    st.image("coffee-cup-1.png", width=35)
                    st.caption(f"Free Cup of Coffee #{g+1} (**Locked**)")

        st.divider()





        
        # Stamp Progress Grid (9 Books)
        st.markdown(f"### Book Purchase Progress ({current_stamps} / 9)")
        book_emojis = ["✧☕︎", "⋆☕︎ ˖", "𑣲☕︎", "˗ˏˋ☕ˎˊ˗", "˙☕ྀི", "☕ᝰ.ᐟ", "𖠚｡˚", "˖°☕ ༘ ⋆", "🥤"]
        cols = st.columns(3) + st.columns(3) + st.columns(3)
        for i in range(9):
            with cols[i]:
                if i < current_stamps:
                    st.markdown(f"### {book_emojis[i]}")
                    st.caption(f"Book {i+1} (Collected)")
                else:
                    st.markdown("### ⚪")
                    st.caption(f"Book {i+1} (Empty)")

        st.markdown("")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("➕ Add Book Stamp", use_container_width=True):
                new_stamps = current_stamps + 1
                new_discounts = discounts
                new_expiries = list(discount_expiries)
                now_str = datetime.utcnow().isoformat()
                
                if new_stamps >= 9:
                    if new_discounts < 2:  # Max 2 banked discounts limit
                        new_discounts += 1
                        new_stamps = 0
                        expiry_date = (datetime.utcnow() + timedelta(days=180)).isoformat()
                        new_expiries.append(expiry_date)
                        st.success("🎉 Milestone reached! 9 books completed! 1 Bookstore Discount added to bank!")
                    else:
                        new_stamps = 9
                        st.warning("⚠️ Discount bank is full (2 max). Please redeem a discount first!")

                supabase.table("loyalty_cards").update({
                    "stamps": new_stamps,
                    "free_cups": new_discounts,
                    "free_cup_expiries": new_expiries,
                    "last_stamp_at": now_str,
                    "last_visit": now_str,
                    "updated_at": now_str
                }).eq("mobile_number", customer_mobile).execute()
                st.rerun()

        with col2:
            if st.button("🎁 Redeem Discount", use_container_width=True):
                if discounts > 0:
                    st.session_state.confirm_redeem = True
                else:
                    st.warning("No discounts available to redeem yet! Complete 9 book purchases first.")

        # --- REDEMPTION CONFIRMATION POPUP ---
        if st.session_state.confirm_redeem:
            st.warning(f"⚠️ **Confirm Redemption**: Apply Bookstore Discount for **{customer_name}**?")
            c_yes, c_no = st.columns(2)
            with c_yes:
                if st.button("✅ Yes, Confirm Redeem", use_container_width=True):
                    new_discounts = discounts - 1
                    updated_expiries = discount_expiries[1:] if len(discount_expiries) > 0 else []
                    now_str = datetime.utcnow().isoformat()
                    
                    supabase.table("loyalty_cards").update({
                        "free_cups": new_discounts,
                        "free_cup_expiries": updated_expiries,
                        "last_redeem_at": now_str,
                        "last_visit": now_str,
                        "updated_at": now_str
                    }).eq("mobile_number", customer_mobile).execute()
                    
                    st.session_state.confirm_redeem = False
                    st.balloons()
                    st.success("🏷️ Bookstore discount applied successfully!")
                    st.rerun()
            with c_no:
                if st.button("❌ Cancel", use_container_width=True):
                    st.session_state.confirm_redeem = False
                    st.rerun()
    else:
        st.warning(f"⚠️ Member matching **'{search_input}'** was not found.")
        st.info("Please navigate to the **Registration & Edit** page to sign up this customer.")


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