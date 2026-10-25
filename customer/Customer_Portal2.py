import streamlit as st
import qrcode
from io import BytesIO
from datetime import datetime
from supabase import create_client
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
import re
import os

# 1. MUST BE THE FIRST STREAMLIT COMMAND IN YOUR FILE
st.set_page_config(
    page_title="The English Bookstore - Loyalty Card", 
    page_icon="📚", 
    layout="centered"
)

# 2. INJECT CUSTOM CSS TO HIDE THE MENUS & FOOTER & STYLE THE THEME
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

# Helper functions for Mobile Sanitization & Validation
def sanitize_mobile(mobile: str) -> str:
    # Removes all non-digit characters (spaces, hyphens, dashes, parentheses)
    return re.sub(r'\D', '', mobile)

def validate_swedish_mobile(mobile: str) -> bool:
    cleaned = sanitize_mobile(mobile)
    # Must start with 07 and be exactly 10 digits total
    return bool(re.match(r'^07\d{8}$', cleaned))

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
    member_no = data.get("member_no", "N/A")
    current_stamps = data.get("stamps", 0)
    discounts = data.get("free_cups", 0)
    discount_expiries = data.get("free_cup_expiries", []) or []

    st.markdown(f"### Welcome back, **{customer_name}**! (Member #{member_no})")
    
    # Three Tabs: Digital Card, QR Code, Profile Editor
    tab_stamps, tab_qr, tab_profile = st.tabs(["📖 Digital Card", "📱 My QR Code", "⚙️ Profile Editor"])

    # --- TAB 1: DIGITAL CARD & REWARDS ---
    with tab_stamps:
        stamps_left = max(0, 9 - (current_stamps % 9))
        if stamps_left == 0 and current_stamps > 0:
            stamps_left = 9

        # Discount HTML (Ready/Unlocked)
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
        if has_discount:
            st.markdown(disc_card_html, unsafe_allow_html=True)

        # Digital Loyalty Card View
        st.markdown(f"""
        <div class="loyalty-card">
            <div style="font-size: 14px; opacity: 0.9;">Member No: #{member_no}</div>
            <div style="font-size: 18px; font-weight: bold; margin-top: 4px;">{customer_name}</div>
            <div style="font-size: 12px; opacity: 0.8; margin-bottom: 12px;">Mobile: {customer_mobile}</div>
            <div style="font-size: 22px; font-weight: bold; text-align: center; background: rgba(255,255,255,0.15); padding: 10px; border-radius: 8px;">
                Stamps Collected: {current_stamps} / 9
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.info(f"Collect {stamps_left} more stamp(s) to unlock your next discount reward!")

    # --- TAB 2: QR CODE ---
    with tab_qr:
        st.markdown("### Show this at the counter")
        qr_bytes = generate_qr_code(customer_mobile)
        st.image(qr_bytes, caption=f"QR for Mobile: {customer_mobile}", width=250)

    # --- TAB 3: PROFILE EDITOR ---
    with tab_profile:
        st.markdown("### Update Your Profile")
        with st.form("cust_profile_form"):
            edit_name = st.text_input("Name", value=customer_name)
            edit_email = st.text_input("Email", value=data.get("email", ""))
            update_submitted = st.form_submit_button("Save Updates", use_container_width=True)

            if update_submitted:
                try:
                    supabase.table("loyalty_cards").update({
                        "name": edit_name.strip(),
                        "email": edit_email.strip().lower() if edit_email else None,
                        "updated_at": datetime.utcnow().isoformat()
                    }).eq("mobile_number", customer_mobile).execute()
                    
                    st.success("✅ Profile updated successfully!")
                    st.toast("Changes saved!", icon="🎉")
                except Exception as e:
                    st.error(f"Error updating profile: {e}")

        if st.button("🚪 Log Out", use_container_width=True):
            st.session_state.cust_logged_in = False
            st.session_state.cust_mobile = ""
            st.session_state.cust_data = None
            st.rerun()

else:
    # --- 2. LOGIN / REGISTRATION GATE ---
    tab_login, tab_register = st.tabs(["🔑 Member Login", "📝 New Registration"])

    with tab_login:
        with st.form("cust_login_form"):
            login_mobile = st.text_input("Mobile Number (e.g., 0712345678 or 071-234-5678)")
            login_password = st.text_input("Password", type="password")
            login_btn = st.form_submit_button("Log In", use_container_width=True)

            if login_btn:
                cleaned_login_mobile = sanitize_mobile(login_mobile)
                if not validate_swedish_mobile(cleaned_login_mobile):
                    st.error("❌ Please enter a valid Swedish mobile number (e.g., 0712345678).")
                else:
                    if not supabase:
                        st.error("Database connection missing.")
                    else:
                        res = supabase.table("loyalty_cards").select("*").eq("mobile_number", cleaned_login_mobile).execute()
                        if res.data:
                            cust_record = res.data[0]
                            stored_hash = cust_record.get("password_hash")
                            try:
                                if stored_hash and ph.verify(stored_hash, login_password):
                                    st.session_state.cust_logged_in = True
                                    st.session_state.cust_mobile = cleaned_login_mobile
                                    st.session_state.cust_data = cust_record
                                    st.success("Login successful!")
                                    st.rerun()
                                else:
                                    st.error("Invalid password.")
                            except VerifyMismatchError:
                                st.error("Invalid password.")
                        else:
                            st.error("No member found with this mobile number.")

    with tab_register:
        with st.form("cust_reg_form"):
            reg_mobile = st.text_input("Mobile Number * (e.g., 071-234 56 78)", placeholder="0712345678")
            reg_name = st.text_input("Your Name *", placeholder="Jane Doe")
            reg_password = st.text_input("Create Password *", type="password")
            reg_email = st.text_input("Email (Optional)", placeholder="jane@hotmail.com")
            
            reg_btn = st.form_submit_button("Register Card", use_container_width=True)

            if reg_btn:
                cleaned_reg_mobile = sanitize_mobile(reg_mobile)
                if not validate_swedish_mobile(cleaned_reg_mobile):
                    st.error("❌ Invalid Swedish mobile number! Must start with 07 and contain 10 digits (hyphens/spaces are allowed and will be cleaned).")
                elif not reg_name.strip():
                    st.error("❌ Name is required.")
                elif not reg_password.strip():
                    st.error("❌ Password is required.")
                else:
                    if not supabase:
                        st.error("Database connection missing.")
                    else:
                        # Check if mobile already exists
                        existing = supabase.table("loyalty_cards").select("*").eq("mobile_number", cleaned_reg_mobile).execute()
                        if existing.data:
                            st.error("❌ A loyalty card with this mobile number already exists! Please log in instead.")
                        else:
                            try:
                                # Determine next sequential member number (No. 1, 2, 3...)
                                max_res = supabase.table("loyalty_cards").select("member_no").order("member_no", desc=True).limit(1).execute()
                                next_member_no = 1
                                if max_res.data and max_res.data[0].get("member_no") is not None:
                                    next_member_no = int(max_res.data[0]["member_no"]) + 1

                                now_str = datetime.utcnow().isoformat()
                                encrypted_pwd = ph.hash(reg_password)

                                supabase.table("loyalty_cards").insert({
                                    "member_no": next_member_no,
                                    "mobile_number": cleaned_reg_mobile,
                                    "name": reg_name.strip(),
                                    "password_hash": encrypted_pwd,
                                    "email": reg_email.strip().lower() if reg_email else None,
                                    "stamps": 0,
                                    "free_cups": 0,
                                    "free_cup_expiries": [],
                                    "created_at": now_str,
                                    "updated_at": now_str
                                }).execute()

                                st.success(f"🎉 Successfully registered! Your Member Number is **#{next_member_no}**. Please log in now.")
                                st.toast("Registration complete!", icon="✅")
                            except Exception as e:
                                st.error(f"Registration error: {e}")