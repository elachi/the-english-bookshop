import streamlit as st
from datetime import datetime
from supabase import create_client
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

st.set_page_config(page_title="My Customer Card", page_icon="📚", layout="centered")

# Supabase Connection Setup
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except Exception:
    SUPABASE_URL = ""
    SUPABASE_KEY = ""

@st.cache_resource
def init_supabase():
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    return create_client(SUPABASE_URL.strip().rstrip('/'), SUPABASE_KEY)

supabase = init_supabase()
ph = PasswordHasher()

# Session State Initialization
if "cust_logged_in" not in st.session_state:
    st.session_state.cust_logged_in = False
if "cust_mobile" not in st.session_state:
    st.session_state.cust_mobile = ""
if "cust_data" not in st.session_state:
    st.session_state.cust_data = None
if "cust_first_login_setup" not in st.session_state:
    st.session_state.cust_first_login_setup = False
if "cust_success_msg" not in st.session_state:
    st.session_state.cust_success_msg = ""

st.image("Logo_EnglishBookshop_logo.png", width=120)
st.title("📚 My Bookstore Loyalty Card")

# --- DISPLAY PERSISTENT SUCCESS MESSAGE IF ANY ---
if st.session_state.cust_success_msg:
    st.success(st.session_state.cust_success_msg)
    # Clear message after rendering so it doesn't repeat indefinitely on unrelated interactions
    st.session_state.cust_success_msg = ""

# --- 1. LOGGED-IN CUSTOMER DASHBOARD ---
if st.session_state.cust_logged_in:
    data = st.session_state.cust_data
    customer_name = data.get("name", "Valued Customer")
    customer_mobile = data["mobile_number"]
    current_stamps = data.get("stamps", 0)
    discounts = data.get("free_cups", 0)
    discount_expiries = data.get("free_cup_expiries", []) or []

    st.success(f"Welcome back, **{customer_name}**!")
    
    # --- EARNED DISCOUNTS BANK ---
    st.markdown("### 🏷️ Your Earned Discounts (Up to 2)")
    gift_cols = st.columns(2)
    for g in range(2):
        with gift_cols[g]:
            if g < discounts:
                exp_str = discount_expiries[g][:10] if g < len(discount_expiries) else "N/A"
                st.image("discount.png", width=40)
                st.caption(f"Discount #{g+1} (Ready! Exp: {exp_str})")
            else:
                st.image("discountE.png", width=40)
                st.caption(f"Discount #{g+1} (Locked)")

    st.divider()

    # --- BOOK STAMP PROGRESS (9 Books) ---
    st.markdown(f"### 📖 Book Purchase Progress ({current_stamps} / 9)")
    book_emojis = ["📕", "📒", "📘", "📔", "📗", "📓", "📙", "📖", "📚"]
    cols = st.columns(3) + st.columns(3) + st.columns(3)
    for i in range(9):
        with cols[i]:
            if i < current_stamps:
                st.markdown(f"### {book_emojis[i]}")
                st.caption(f"Book {i+1} (Collected)")
            else:
                st.markdown("### ⚪")
                st.caption(f"Book {i+1} (Empty)")

    st.divider()

    # --- EDIT PROFILE SECTION (Name, Password with Old Password Check, Ads Checkbox) ---
    with st.expander("⚙️ Edit My Profile (Name, Password & Ad Preferences)"):
        with st.form("edit_profile_form"):
            new_name_input = st.text_input("Name", value=data.get("name", ""))
            
            st.markdown("---")
            st.markdown("🔒 **Change Password** (Requires current password)")
            old_pwd_input = st.text_input("Current Password", type="password", placeholder="Enter current password")
            new_pwd_input = st.text_input("New Password", type="password", placeholder="Enter new password")
            
            st.markdown("---")
            receive_ads_input = st.checkbox("Receive promotional emails & special offer ads", value=bool(data.get("receive_ads", True)))
            
            save_profile_btn = st.form_submit_button("Save Profile Changes", use_container_width=True)
            
            if save_profile_btn:
                try:
                    update_payload = {
                        "name": new_name_input.strip() if new_name_input else "Valued Customer",
                        "receive_ads": receive_ads_input,
                        "updated_at": datetime.utcnow().isoformat()
                    }
                    
                    # If they typed a new password, require and verify the old password first
                    if new_pwd_input.strip():
                        if not old_pwd_input.strip():
                            st.error("❌ Please enter your current password to set a new one.")
                        else:
                            stored_hash = data.get("password_hash")
                            try:
                                ph.verify(stored_hash, old_pwd_input.strip())
                                update_payload["password_hash"] = ph.hash(new_pwd_input.strip())
                                
                                supabase.table("loyalty_cards").update(update_payload).eq("mobile_number", customer_mobile).execute()
                                
                                res_refresh = supabase.table("loyalty_cards").select("*").eq("mobile_number", customer_mobile).execute()
                                st.session_state.cust_data = res_refresh.data[0]
                                st.session_state.cust_success_msg = "✅ Profile and password updated successfully!"
                                st.rerun()
                            except VerifyMismatchError:
                                st.error("❌ Incorrect current password.")
                    else:
                        # Updating name or ad preferences without changing password
                        supabase.table("loyalty_cards").update(update_payload).eq("mobile_number", customer_mobile).execute()
                        
                        res_refresh = supabase.table("loyalty_cards").select("*").eq("mobile_number", customer_mobile).execute()
                        st.session_state.cust_data = res_refresh.data[0]
                        st.session_state.cust_success_msg = "✅ Profile updated successfully!"
                        st.rerun()
                        
                except Exception as update_err:
                    st.error(f"Error updating profile: {update_err}")

    st.divider()
    if st.button("🚪 Log Out", use_container_width=True):
        st.session_state.cust_logged_in = False
        st.session_state.cust_mobile = ""
        st.session_state.cust_data = None
        st.rerun()

    st.stop()

# --- 2. FIRST-TIME PASSWORD SETUP (Pre-registered by bookstore) ---
if st.session_state.cust_first_login_setup:
    st.warning("🔒 First-time login detected. Please set up your secure password.")
    with st.form("setup_pwd_form"):
        new_pwd = st.text_input("Create New Password", type="password")
        confirm_pwd = st.text_input("Confirm New Password", type="password")
        setup_btn = st.form_submit_button("Save Password & View Card", use_container_width=True)
        
        if setup_btn:
            if not new_pwd.strip():
                st.error("Password cannot be empty.")
            elif new_pwd != confirm_pwd:
                st.error("Passwords do not match.")
            else:
                try:
                    hashed = ph.hash(new_pwd)
                    supabase.table("loyalty_cards").update({
                        "password_hash": hashed,
                        "updated_at": datetime.utcnow().isoformat()
                    }).eq("mobile_number", st.session_state.cust_mobile).execute()
                    
                    res = supabase.table("loyalty_cards").select("*").eq("mobile_number", st.session_state.cust_mobile).execute()
                    st.session_state.cust_data = res.data[0]
                    st.session_state.cust_logged_in = True
                    st.session_state.cust_first_login_setup = False
                    st.session_state.cust_success_msg = "✅ Password saved successfully!"
                    st.rerun()
                except Exception as e:
                    st.error(f"Error setting password: {e}")
    st.stop()

# --- 3. LOGIN & SELF-REGISTRATION TABS ---
tab_login, tab_register = st.tabs(["🔑 Customer Login", "📝 Register New Card"])

with tab_login:
    st.subheader("View Your Stamp Card")
    with st.form("cust_login_form"):
        login_mobile = st.text_input("Mobile Number", placeholder="e.g., 555-0200")
        login_password = st.text_input("Password", type="password", placeholder="Enter your password")
        login_btn = st.form_submit_button("Log In", use_container_width=True)
        
        if login_btn:
            if not login_mobile.strip() or not login_password.strip():
                st.error("Please enter both mobile number and password.")
            else:
                try:
                    res = supabase.table("loyalty_cards").select("*").eq("mobile_number", login_mobile.strip()).execute()
                    if not res.data:
                        st.error("No account found with this mobile number.")
                    else:
                        cust = res.data[0]
                        stored_hash = cust.get("password_hash")
                        
                        if not stored_hash:
                            st.session_state.cust_mobile = login_mobile.strip()
                            st.session_state.cust_first_login_setup = True
                            st.rerun()
                        else:
                            try:
                                ph.verify(stored_hash, login_password)
                                st.session_state.cust_logged_in = True
                                st.session_state.cust_data = cust
                                st.session_state.cust_mobile = cust["mobile_number"]
                                st.session_state.cust_success_msg = "✅ Login successful!"
                                st.rerun()
                            except VerifyMismatchError:
                                st.error("❌ Incorrect password.")
                except Exception as e:
                    st.error(f"Login error: {e}")

with tab_register:
    st.subheader("Register a New Loyalty Card")
    with st.form("cust_reg_form"):
        reg_mobile = st.text_input("Mobile Number * (Required)", placeholder="e.g., 555-0200")
        reg_name = st.text_input("Your Name * (Required)", placeholder="e.g., Jane Doe")
        reg_password = st.text_input("Create Password * (Required)", type="password", placeholder="Choose a secure password")
        reg_email = st.text_input("Email (Optional)", placeholder="e.g., jane@hotmail.com")
        reg_receive_ads = st.checkbox("Receive promotional emails & special offer ads", value=True)
        
        reg_btn = st.form_submit_button("Register Account", use_container_width=True)
        
        if reg_btn:
            if not reg_mobile.strip() or not reg_password.strip() or not reg_name.strip():
                st.error("Mobile number, name, and password are required.")
            else:
                try:
                    check_res = supabase.table("loyalty_cards").select("mobile_number").eq("mobile_number", reg_mobile.strip()).execute()
                    if check_res.data:
                        st.error("An account with this mobile number already exists. Please log in instead.")
                    else:
                        now_str = datetime.utcnow().isoformat()
                        encrypted_pwd = ph.hash(reg_password)
                        
                        new_cust_payload = {
                            "mobile_number": reg_mobile.strip(),
                            "name": reg_name.strip(),
                            "password_hash": encrypted_pwd,
                            "email": reg_email.strip().lower() if reg_email else None,
                            "receive_ads": reg_receive_ads,
                            "stamps": 0,
                            "free_cups": 0,
                            "free_cup_expiries": [],
                            "created_at": now_str,
                            "last_visit": now_str,
                            "updated_at": now_str
                        }
                        
                        supabase.table("loyalty_cards").insert(new_cust_payload).execute()
                        st.session_state.cust_success_msg = "🎉 Account created successfully! Please switch to the 'Customer Login' tab to log in."
                        st.rerun()
                except Exception as e:
                    st.error(f"Registration error: {e}")
