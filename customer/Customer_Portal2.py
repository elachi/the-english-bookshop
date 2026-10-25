
import streamlit as st
import qrcode
from io import BytesIO
from datetime import datetime
from supabase import create_client
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError


# 1. MUST BE THE FIRST STREAMLIT COMMAND IN YOUR FILE
st.set_page_config(
    page_title="Cafe Loyalty Program", 
    page_icon="☕", 
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



st.set_page_config(page_title="My Bookstore Loyalty Card - V2", page_icon="📚", layout="centered")

# --- MOBILE STYLING & DIGITAL CARD THEME ---
st.markdown("""
<style>
    /* Apply forest green color across text elements */
    h1, h2, h3, h4, h5, h6, p, span, label, div, .stMarkdown {
        color: #307041 !important;
    }

    /* Enlarge tab text */
    button[data-baseweb="tab"] div p {
        font-size: 1.05rem !important;
        font-weight: 600 !important;
        color: #307041 !important;
    }

    /* Modern Loyalty Card Styling */
    .loyalty-card {
        background: linear-gradient(135deg, #307041 0%, #204d2b 100%);
        padding: 20px;
        border-radius: 16px;
        color: white !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        margin-bottom: 12px;
    }
    .loyalty-card * {
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# Helper function to generate a dynamic QR code image from a mobile number/ID
def generate_qr_code(data_string):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=2,
    )
    qr.add_data(data_string)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    return buffered.getvalue()

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

st.image("Logo_EnglishBookshop_logo.png", width=120)
st.subheader("Your loyalty stamp Card")

# --- 1. LOGGED-IN CUSTOMER DASHBOARD ---
if st.session_state.cust_logged_in:
    data = st.session_state.cust_data
    customer_name = data.get("name", "Valued Customer")
    customer_mobile = data["mobile_number"]
    current_stamps = data.get("stamps", 0)
    discounts = data.get("free_cups", 0)
    discount_expiries = data.get("free_cup_expiries", []) or []

    st.markdown(f"### Welcome back, **{customer_name}**!")
    
    # Three Tabs: Digital Card, QR Code, Profile Editor
    tab_stamps, tab_qr, tab_profile = st.tabs(["📖 Digital Card", "📱 My QR Code", "⚙️ Profile Editor"])

    # --- TAB 1: DIGITAL CARD & REWARDS ---
    with tab_stamps:
        # Calculate remaining stamps until next discount (assuming target is 9)
        stamps_left = max(0, 9 - (current_stamps % 9))
        if stamps_left == 0 and current_stamps > 0:
            stamps_left = 9

        # --- HTML COMPONENTS FOR REWARDS & STAMPS ---
        
        # 1. Discount HTML (Ready/Unlocked)
        has_discount = discounts > 0
        disc_card_html = f"""
        <div style="background: #f2f8f3; border: 1px solid #307041; border-radius: 12px; padding: 12px; text-align: center; margin-bottom: 12px;">
            <div style="font-size: 24px; line-height: 1.1;">🎟️</div>
            <div style="font-size: 12px; color: #307041; margin-top: 2px; font-weight: 700;">
                1x Bookstore Discount Unlocked! 🎉
            </div>
            <div style="font-size: 10px; color: #307041; opacity: 0.8; margin-top: 2px;">
                {f"Expires on: {discount_expiries[0][:10]}" if discount_expiries else "Ready to use at counter"}
            </div>
        </div>
        """

        # 2. Stamps Card HTML
        stamps_card_html = f"""
        <div class="loyalty-card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <span style="font-size: 13px; font-weight: 700; letter-spacing: 1px;">THE ENGLISH BOOKSHOP</span>
            </div>
            <div style="font-size: 12px; opacity: 0.9; text-transform: uppercase; letter-spacing: 0.5px;">Book Purchases</div>
            <div style="font-size: 34px; font-weight: 800; margin: 2px 0;">{current_stamps} / 9 <span style="font-size: 18px; font-weight: 400;">Books 📚</span></div>
            <div style="font-size: 11px; opacity: 0.8; margin-top: 4px;">📖 Keep reading to unlock your bookstore discount!</div>
        </div>
        """

        # 3. Discount HTML (Locked / Underneath)
        locked_disc_html = f"""
        <div style="background: #fafafa; border: 1px dashed #d5ddd7; border-radius: 12px; padding: 12px; text-align: center; margin-top: 4px;">
            <div style="font-size: 20px; line-height: 1.1;">🔒</div>
            <div style="font-size: 12px; color: #78947c; margin-top: 2px; font-weight: 700;">
                Discount Reward Locked
            </div>
            <div style="font-size: 11px; color: #78947c; margin-top: 2px;">
                Only <b>{stamps_left} more book{"" if stamps_left == 1 else "s"}</b> 📗 left to unlock your discount!
            </div>
        </div>
        """

        # --- CONDITIONAL LAYOUT ORDER ---
        if has_discount:
            # If discount is ready, place it ON TOP of the stamps card
            st.markdown(disc_card_html, unsafe_allow_html=True)
            st.markdown(stamps_card_html, unsafe_allow_html=True)
        else:
            # If not earned yet, place stamps card first, then the locked message underneath
            st.markdown(stamps_card_html, unsafe_allow_html=True)
            st.markdown(locked_disc_html, unsafe_allow_html=True)

    # --- TAB 2: MY QR CODE ---
    with tab_qr:
        st.markdown("### 📱 Member QR Code")
        st.markdown("Show this QR code at the bookstore counter to scan and update your stamps:")
        
        # Center the QR code nicely
        col_q1, col_q2, col_q3 = st.columns([1, 2, 1])
        with col_q2:
            qr_bytes = generate_qr_code(customer_mobile)
            st.image(qr_bytes, use_container_width=True)
            st.markdown(f"<div style='text-align: center; font-weight: 600; margin-top: 8px;'>ID: {customer_mobile}</div>", unsafe_allow_html=True)

    # --- TAB 3: PROFILE EDITOR ---
    with tab_profile:
        st.markdown("### 🛠️ Edit Your Profile")
        with st.form("edit_profile_form"):
            e_name = st.text_input("Name", value=data.get("name", ""))
            e_mobile = st.text_input("Mobile Number (Primary ID)", value=data.get("mobile_number", ""))
            e_email = st.text_input("Email", value=data.get("email", "") or "")
            
            st.markdown("---")
            st.markdown("🔒 **Change Password** (Fill out only if changing password)")
            old_pwd_input = st.text_input("Current Password", type="password", placeholder="Enter current password")
            new_pwd_input = st.text_input("New Password", type="password", placeholder="Enter new password")
            
            st.markdown("---")
            receive_ads_input = st.checkbox("Receive promotional emails & special offer ads", value=bool(data.get("receive_ads", True)))
            
            save_profile_btn = st.form_submit_button("Save Profile Changes", use_container_width=True)
            
            if save_profile_btn:
                try:
                    update_payload = {
                        "name": e_name.strip() if e_name else "Valued Customer",
                        "mobile_number": e_mobile.strip(),
                        "email": e_email.strip().lower() if e_email else None,
                        "receive_ads": receive_ads_input,
                        "updated_at": datetime.utcnow().isoformat()
                    }
                    
                    if new_pwd_input.strip():
                        if not old_pwd_input.strip():
                            st.error("❌ Please enter your current password to set a new one.")
                        else:
                            stored_hash = data.get("password_hash")
                            try:
                                ph.verify(stored_hash, old_pwd_input.strip())
                                update_payload["password_hash"] = ph.hash(new_pwd_input.strip())
                                
                                supabase.table("loyalty_cards").update(update_payload).eq("mobile_number", customer_mobile).execute()
                                
                                res_refresh = supabase.table("loyalty_cards").select("*").eq("mobile_number", e_mobile.strip()).execute()
                                st.session_state.cust_data = res_refresh.data[0]
                                st.session_state.cust_mobile = e_mobile.strip()
                                st.toast("✅ Profile and password updated successfully!", icon="🎉")
                                st.rerun()
                            except VerifyMismatchError:
                                st.error("❌ Incorrect current password.")
                    else:
                        supabase.table("loyalty_cards").update(update_payload).eq("mobile_number", customer_mobile).execute()
                        
                        res_refresh = supabase.table("loyalty_cards").select("*").eq("mobile_number", e_mobile.strip()).execute()
                        st.session_state.cust_data = res_refresh.data[0]
                        st.session_state.cust_mobile = e_mobile.strip()
                        st.toast("✅ Profile updated successfully!", icon="🎉")
                        st.rerun()
                        
                except Exception as update_err:
                    st.error(f"Error updating profile: {update_err}")

    # --- REFRESH & LOG OUT BUTTONS ---
    st.divider()
    with st.container(horizontal=True, wrap=False):
        if st.button("🔄 Refresh Stamps", use_container_width=True):
            try:
                res_refresh = supabase.table("loyalty_cards").select("*").eq("mobile_number", customer_mobile).execute()
                if res_refresh.data:
                    st.session_state.cust_data = res_refresh.data[0]
                    st.toast("🔄 Stamps refreshed successfully!", icon="✨")
                    st.rerun()
            except Exception as e:
                st.error(f"Error refreshing: {e}")
                
        if st.button("🚪 Log Out", use_container_width=True):
            st.session_state.cust_logged_in = False
            st.session_state.cust_mobile = ""
            st.session_state.cust_data = None
            st.rerun()

    st.stop()

# --- 2. FIRST-TIME PASSWORD SETUP ---
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
                    st.toast("✅ Password saved successfully!", icon="🎉")
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
                                st.toast("✅ Login successful!", icon="🎉")
                                st.rerun()
                            except VerifyMismatchError:
                                st.error("❌ Incorrect password.")
                except Exception as e:
                    st.error(f"Login error: {e}")


with tab_register:
        st.subheader("Create New Loyalty Account")
        with st.form("cust_reg_form", clear_on_submit=True):
            reg_mobile_raw = st.text_input("Mobile Number * (e.g. 071-234-56-78)", placeholder="0712345678")
            reg_name = st.text_input("Customer Name *", placeholder="Jane Doe")
            reg_pass = st.text_input("Password *", type="password", placeholder="Create account password")
            reg_email = st.text_input("Email (Optional)", placeholder="jane@hotmail.com")
            reg_ads = st.checkbox("Receive promotional emails & special offer ads", value=True)
            
            reg_sub = st.form_submit_button("Register & Create Card", use_container_width=True)

            if reg_sub:
                cleaned_reg_mobile = clean_swedish_mobile(reg_mobile_raw)
                if not validate_swedish_mobile(cleaned_reg_mobile):
                    st.error("❌ Invalid Swedish mobile number format! Must start with '07' and be 10 digits (e.g. 0712345678).")
                elif not reg_name.strip():
                    st.error("❌ Customer name is required.")
                elif not reg_pass.strip():
                    st.error("❌ Password is required.")
                else:
                    if not supabase:
                        st.error("Database connection missing.")
                    else:
                        try:
                            # FIX: Check existing by mobile_number instead of non-existent 'id'
                            check_existing = supabase.table("loyalty_cards").select("mobile_number").eq("mobile_number", cleaned_reg_mobile).execute()
                            if check_existing.data:
                                st.error("❌ An account with this mobile number already exists.")
                            else:
                                now_str = datetime.utcnow().isoformat()
                                encrypted_pwd = ph.hash(reg_pass)

                                supabase.table("loyalty_cards").insert({
                                    "mobile_number": cleaned_reg_mobile,
                                    "name": reg_name.strip(),
                                    "password_hash": encrypted_pwd,
                                    "email": reg_email.strip().lower() if reg_email else None,
                                    "receive_ads": reg_ads,
                                    "stamps": 0,
                                    "free_cups": 0,
                                    "free_cup_expiries": [],
                                    "created_at": now_str,
                                    "last_visit": now_str,
                                    "updated_at": now_str
                                }).execute()

                                st.success(f"✅ Successfully registered member! ({cleaned_reg_mobile})")
                                st.toast("Account created successfully!", icon="🎉")
                        except Exception as e:
                            st.error(f"Registration error: {e}")