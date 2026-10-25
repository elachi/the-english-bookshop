import streamlit as st
import qrcode
from io import BytesIO
from datetime import datetime
from supabase import create_client
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
import re

# 1. MUST BE THE FIRST STREAMLIT COMMAND IN YOUR FILE
st.set_page_config(
    page_title="The English Bookstore Loyalty Card - V2", 
    page_icon="📚", 
    layout="centered"
)

# 2. INJECT CUSTOM CSS TO HIDE THE MENUS & FOOTER & APPLY THEME
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

# Helper function to normalize Swedish mobile numbers (strips spaces and hyphens)
def clean_mobile_number(mobile_input: str) -> str:
    # Remove all spaces and hyphens
    return re.sub(r'[\s-]', '', mobile_input.strip())

# Helper validation for Swedish format (07 followed by 8 digits)
def validate_swedish_mobile(mobile: str) -> bool:
    cleaned = clean_mobile_number(mobile)
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

        st.info(f"You currently have **{current_stamps}** stamps. ({stamps_left} more to your next reward!)")
        
        if st.button("🚪 Log Out"):
            st.session_state.cust_logged_in = False
            st.session_state.cust_mobile = ""
            st.session_state.cust_data = None
            st.rerun()

    # --- TAB 2: MY QR CODE ---
    with tab_qr:
        st.markdown("Show this QR code at the counter to scan your stamps:")
        qr_bytes = generate_qr_code(customer_mobile)
        st.image(qr_bytes, caption=f"Mobile ID: {customer_mobile}", width=200)

    # --- TAB 3: PROFILE EDITOR ---
    with tab_profile:
        with st.form("customer_profile_edit"):
            updated_name = st.text_input("Name", value=customer_name)
            updated_email = st.text_input("Email", value=data.get("email", ""))
            
            save_profile_btn = st.form_submit_button("Save Changes")
            if save_profile_btn:
                try:
                    supabase.table("loyalty_cards").update({
                        "name": updated_name.strip(),
                        "email": updated_email.strip().lower() if updated_email else None,
                        "updated_at": datetime.utcnow().isoformat()
                    }).eq("mobile_number", customer_mobile).execute()
                    
                    st.success("✅ Profile updated successfully!")
                    st.toast("Saved changes!", icon="🎉")
                except Exception as e:
                    st.error(f"Error updating profile: {e}")

else:
    # --- 2. LOGIN / REGISTRATION GATE ---
    tab_login, tab_register = st.tabs(["🔐 Member Login", "📝 New Registration"])

    with tab_login:
        with st.form("customer_login_form"):
            login_mobile_input = st.text_input("Mobile Number", placeholder="0712345678")
            login_password = st.text_input("Password", type="password")
            login_submit = st.form_submit_button("Log In", use_container_width=True)

            if login_submit:
                cleaned_login_mobile = clean_mobile_number(login_mobile_input)
                if not cleaned_login_mobile:
                    st.error("Please enter your mobile number.")
                else:
                    try:
                        res = supabase.table("loyalty_cards").select("*").eq("mobile_number", cleaned_login_mobile).execute()
                        if res.data:
                            cust_record = res.data[0]
                            stored_hash = cust_record.get("password_hash")
                            if stored_hash:
                                try:
                                    ph.verify(stored_hash, login_password)
                                    st.session_state.cust_logged_in = True
                                    st.session_state.cust_mobile = cleaned_login_mobile
                                    st.session_state.cust_data = cust_record
                                    st.success("Login successful!")
                                    st.rerun()
                                except VerifyMismatchError:
                                    st.error("Invalid password.")
                            else:
                                st.error("Account password not set. Please contact staff.")
                        else:
                            st.error("Mobile number not found.")
                    except Exception as e:
                        st.error(f"Login error: {e}")

    with tab_register:
        with st.form("customer_registration_form"):
            reg_mobile = st.text_input("Mobile Number * (Swedish format e.g., 071-2345678)", placeholder="0712345678")
            reg_name = st.text_input("Full Name", placeholder="Jane Doe")
            reg_password = st.text_input("Create Password *", type="password")
            reg_email = st.text_input("Email (Optional)", placeholder="jane@hotmail.com")
            reg_ads = st.checkbox("Receive promotional emails & special offer ads", value=True)
            
            reg_submit = st.form_submit_button("Register Card", use_container_width=True)

            if reg_submit:
                cleaned_reg_mobile = clean_mobile_number(reg_mobile)
                if not cleaned_reg_mobile:
                    st.error("❌ Mobile number is required.")
                elif not validate_swedish_mobile(cleaned_reg_mobile):
                    st.error("❌ Invalid Swedish mobile number format! Must start with '07' and be 10 digits (e.g., 0712345678).")
                elif not reg_password.strip():
                    st.error("❌ Password is required.")
                else:
                    try:
                        # Check if mobile already exists
                        existing = supabase.table("loyalty_cards").select("mobile_number").eq("mobile_number", cleaned_reg_mobile).execute()
                        if existing.data:
                            st.error("❌ An account with this mobile number already exists.")
                        else:
                            # 1. Determine the next sequence order number (No. 1, 2, 3...)
                            count_res = supabase.table("loyalty_cards").select("member_number", count="exact").execute()
                            next_seq_no = (count_res.count or 0) + 1

                            now_str = datetime.utcnow().isoformat()
                            hashed_pwd = ph.hash(reg_password)

                            # 2. Insert with normalized mobile number and sequential member_number
                            supabase.table("loyalty_cards").insert({
                                "member_number": next_seq_no,
                                "mobile_number": cleaned_reg_mobile,
                                "name": reg_name.strip() if reg_name else "Valued Customer",
                                "email": reg_email.strip().lower() if reg_email else None,
                                "password_hash": hashed_pwd,
                                "receive_ads": reg_ads,
                                "stamps": 0,
                                "free_cups": 0,
                                "free_cup_expiries": [],
                                "created_at": now_str,
                                "last_visit": now_str,
                                "updated_at": now_str
                            }).execute()

                            st.success(f"✅ Registration successful! Your Member Sequence No. is #{next_seq_no}.")
                            st.toast("Card created successfully!", icon="🎉")
                    except Exception as e:
                        st.error(f"Error during registration: {e}")