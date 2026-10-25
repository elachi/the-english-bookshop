import streamlit as st
import qrcode
from io import BytesIO
from datetime import datetime
from supabase import create_client
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
import os
import re

# 1. MUST BE THE FIRST STREAMLIT COMMAND IN YOUR FILE
st.set_page_config(
    page_title="The English Bookstore - Loyalty Card", 
    page_icon="📚", 
    layout="centered"
)

# 2. INJECT CUSTOM CSS TO HIDE MENUS & STYLE THE APP
st.markdown("""
    <style>
        /* Hides the top-right hamburger menu and Deploy button */
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        
        /* Hides the default "Made with Streamlit" footer */
        footer {visibility: hidden;}
        
        /* Shifts the main content up slightly */
        .block-container {
            padding-top: 2rem;
        }

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

# Helper function to generate a dynamic QR code image
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

# Helper function to clean and validate Swedish mobile numbers (ignores spaces, hyphens, etc.)
def clean_swedish_mobile(mobile_input: str) -> str:
    return re.sub(r'\D', '', mobile_input)

def validate_swedish_mobile(digits: str) -> bool:
    return bool(re.match(r"^07\d{8}$", digits))

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

st.image("Logo_EnglishBookshop_logo.png", width=120)
st.subheader("Your Loyalty Stamp Card")

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
        stamps_left = max(0, 9 - (current_stamps % 9))
        if stamps_left == 0 and current_stamps > 0:
            stamps_left = 9

        has_discount = discounts > 0
        if has_discount:
            st.markdown(f"""
            <div style="background: #f2f8f3; border: 1px solid #307041; border-radius: 12px; padding: 12px; text-align: center; margin-bottom: 12px;">
                <div style="font-size: 24px; line-height: 1.1;">🎟️</div>
                <div style="font-size: 12px; color: #307041; margin-top: 2px; font-weight: 700;">
                    1x Bookstore Discount Unlocked! 🎉
                </div>
                <div style="font-size: 10px; color: #307041; opacity: 0.8; margin-top: 2px;">
                    {f"Expires on: {discount_expiries[0][:10]}" if discount_expiries else "Ready to use at counter"}
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="loyalty-card">
            <h3 style="margin: 0; color: white !important;">Stamp Balance: {current_stamps} / 9</h3>
            <p style="margin: 5px 0 0 0; font-size: 0.9rem;">Stamps until next reward: <b>{stamps_left}</b></p>
        </div>
        """, unsafe_allow_html=True)

    # --- TAB 2: QR CODE ---
    with tab_qr:
        st.markdown("Show this QR code at the counter:")
        qr_bytes = generate_qr_code(customer_mobile)
        st.image(qr_bytes, width=200)

    # --- TAB 3: PROFILE EDITOR ---
    with tab_profile:
        with st.form("customer_profile_edit"):
            ed_name = st.text_input("Name", value=customer_name)
            ed_email = st.text_input("Email", value=data.get("email", ""))
            ed_ads = st.checkbox("Receive promotional emails & special offer ads", value=data.get("receive_ads", True))
            
            save_prof = st.form_submit_button("Update Profile", use_container_width=True)
            if save_prof:
                try:
                    supabase.table("loyalty_cards").update({
                        "name": ed_name.strip(),
                        "email": ed_email.strip().lower() if ed_email else None,
                        "receive_ads": ed_ads,
                        "updated_at": datetime.utcnow().isoformat()
                    }).eq("mobile_number", customer_mobile).execute()
                    st.success("✅ Profile updated successfully!")
                    st.toast("Saved changes!", icon="🎉")
                except Exception as e:
                    st.error(f"Error updating profile: {e}")

    if st.button("🚪 Log Out"):
        st.session_state.cust_logged_in = False
        st.session_state.cust_mobile = ""
        st.session_state.cust_data = None
        st.rerun()

else:
    # --- 2. CUSTOMER LOGIN & REGISTRATION VIEW ---
    tab_login, tab_register = st.tabs(["🔐 Member Login", "📝 Register New Card"])

    with tab_login:
        with st.form("cust_login_form"):
            login_mobile_raw = st.text_input("Mobile Number (e.g. 071-2345678)", placeholder="0712345678")
            login_pass = st.text_input("Password", type="password")
            login_sub = st.form_submit_button("Log In", use_container_width=True)

            if login_sub:
                cleaned_login_mobile = clean_swedish_mobile(login_mobile_raw)
                if not validate_swedish_mobile(cleaned_login_mobile):
                    st.error("❌ Invalid Swedish mobile number format. Must be 10 digits starting with 07.")
                else:
                    if not supabase:
                        st.error("Database connection missing.")
                    else:
                        res = supabase.table("loyalty_cards").select("*").eq("mobile_number", cleaned_login_mobile).execute()
                        if res.data:
                            user_record = res.data[0]
                            stored_hash = user_record.get("password_hash")
                            if stored_hash:
                                try:
                                    ph.verify(stored_hash, login_pass)
                                    st.session_state.cust_logged_in = True
                                    st.session_state.cust_mobile = cleaned_login_mobile
                                    st.session_state.cust_data = user_record
                                    st.success("Login successful!")
                                    st.rerun()
                                except VerifyMismatchError:
                                    st.error("Invalid password.")
                            else:
                                st.error("Account password not set. Please contact staff.")
                        else:
                            st.warning("No member found with this mobile number.")

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