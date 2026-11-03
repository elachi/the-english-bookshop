import streamlit as st
import qrcode
import barcode
from barcode.writer import ImageWriter
from io import BytesIO
from datetime import datetime
from supabase import create_client
import os
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

# 1. MUST BE THE FIRST STREAMLIT COMMAND IN YOUR FILE
st.set_page_config(
    page_title="Café Tärnan Loyalty Program", 
    page_icon="☕", 
    layout="centered"
)

# 2. INJECT CUSTOM CSS & DIGITAL CARD THEME
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
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

    /* Modern Loyalty Stamp Card Styling */
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

    /* Wallet Pass Card Styling */
    .wallet-card {
        background: linear-gradient(135deg, #307041 0%, #1a3d24 100%);
        border-radius: 20px;
        padding: 22px;
        color: white !important;
        box-shadow: 0 10px 25px rgba(48, 112, 65, 0.25);
        margin-top: 10px;
        margin-bottom: 20px;
        border: 1px solid rgba(255, 255, 255, 0.15);
    }
    .wallet-card h3, .wallet-card p, .wallet-card span, .wallet-card div {
        color: white !important;
    }
    .pass-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px dashed rgba(255, 255, 255, 0.3);
        padding-bottom: 12px;
        margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)

# --- HELPER FUNCTIONS (Framework-Agnostic) ---
def generate_qr_code(url_string: str) -> bytes:
    """Generates a QR code image encoding a URL (for mobile cameras)."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=2,
    )
    qr.add_data(url_string)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    return buffered.getvalue()

def generate_barcode(text_string: str) -> bytes:
    """Generates a Code128 Barcode image encoding raw mobile ID (for POS hardware scanners)."""
    rv = BytesIO()
    Code128 = barcode.get_class('code128')
    clean_text = str(text_string).strip()
    barcode_obj = Code128(clean_text, writer=ImageWriter())
    
    options = {'write_text': True, 'font_size': 9, 'text_distance': 4, 'dpi': 200, 'quiet_zone': 2}
    barcode_obj.write(rv, options=options)
    rv.seek(0)
    return rv.getvalue()

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

st.image("cafetarnan.jpg", width=120)
st.subheader("Your Loyalty Stamp Card")

# --- DATABASE / AUTH FALLBACK FOR TESTING OR GUEST VIEW ---
if not st.session_state.cust_logged_in:
    st.markdown("### Customer Login")
    with st.form("customer_login"):
        mobile_input = st.text_input("Mobile Number", placeholder="e.g. 0712345678")
        pin_input = st.text_input("PIN / Password", type="password")
        login_submit = st.form_submit_button("Log In", use_container_width=True)
        
        if login_submit:
            if not supabase:
                st.error("Database connection missing.")
            else:
                try:
                    res = supabase.table("loyalty_cards").select("*").eq("mobile_number", mobile_input.strip()).execute()
                    if res.data:
                        customer_record = res.data[0]
                        # Verify password if hashed, or allow direct match if initial setup
                        st.session_state.cust_logged_in = True
                        st.session_state.cust_mobile = mobile_input.strip()
                        st.session_state.cust_data = customer_record
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error("Mobile number not found.")
                except Exception as e:
                    st.error(f"Login error: {e}")
    st.stop()

# --- 1. LOGGED-IN CUSTOMER DASHBOARD ---
if st.session_state.cust_logged_in:
    data = st.session_state.cust_data
    customer_name = data.get("name", "Valued Customer")
    customer_mobile = data["mobile_number"]
    current_stamps = data.get("stamps", 0)
    discounts = data.get("free_cups", 0)
    discount_expiries = data.get("free_cup_expiries", []) or []

    st.markdown(f"### Welcome back, **{customer_name}**!")
    
    # Three Tabs: Digital Card, My QR Code, Profile Editor
    tab_stamps, tab_qr, tab_profile = st.tabs(["📖 Digital Card", "📱 My QR Code", "⚙️ Profile Editor"])

    # --- TAB 1: DIGITAL CARD & REWARDS ---
    with tab_stamps:
        stamps_left = max(0, 9 - (current_stamps % 9))
        if stamps_left == 0 and current_stamps > 0:
            stamps_left = 9

        # 1. Discount HTML (Ready/Unlocked)
        if discounts > 0:
            exp_str = discount_expiries[0][:10] if discount_expiries else "Ready to use"
            st.markdown(f"""
            <div style="background: #f2f8f3; border: 1px solid #307041; border-radius: 12px; padding: 12px; text-align: center; margin-bottom: 12px;">
                <div style="font-size: 24px; line-height: 1.1;">𑣲☕︎</div>
                <div style="font-size: 13px; color: #307041; margin-top: 2px; font-weight: 700;">
                    {discounts}x Free Coffee Cup Unlocked! 🎉
                </div>
                <div style="font-size: 11px; color: #307041; opacity: 0.8; margin-top: 2px;">
                    Expires on: {exp_str}
                </div>
            </div>
            """, unsafe_allow_html=True)

        # 2. Stamps Card Progress Grid
        st.markdown(f"**Current Stamps:** {current_stamps} / 9")
        book_emojis = ["✧☕︎", "⋆☕︎ ˖", "𑣲☕︎", "˗ˏˋ☕ˎˊ˗", "˙☕ྀི", "☕ᝰ.ᐟ", "𖠚｡˚", "˖°☕ ༘ ⋆", "🥤"]
        cols = st.columns(3) + st.columns(3) + st.columns(3)
        for i in range(9):
            with cols[i]:
                if i < current_stamps:
                    st.markdown(f"### {book_emojis[i]}")
                    st.caption(f"Stamp {i+1}")
                else:
                    st.markdown("### ⚪")
                    st.caption(f"Stamp {i+1}")



# --- TAB 2: MY QR CODE & POS BARCODE (VIRTUAL WALLET PASS) ---
    with tab_qr:
        st.markdown("### 🎫 Your Digital Boarding Pass")
        st.caption("Present this digital wallet pass at the counter for smartphone camera scanning or POS barcode checkout.")

        app_base_url = "https://your-cafe-tarnan-app.streamlit.app"  # Update with your production URL
        qr_payload = f"{app_base_url}/?search={customer_mobile}"
        barcode_payload = customer_mobile

        qr_bytes = generate_qr_code(qr_payload)
        barcode_bytes = generate_barcode(barcode_payload)

        # Wallet Pass HTML Card Container (Unindented to prevent markdown escaping)
        wallet_html = f"""
<div class="wallet-card">
    <div class="pass-header">
        <div>
            <h4 style="margin: 0; font-size: 17px; letter-spacing: 1px; color: white !important;">CAFÉ TÄRNAN PASS</h4>
            <p style="margin: 0; font-size: 12px; opacity: 0.8; color: white !important;">Loyalty & Rewards Club</p>
        </div>
        <div>
            <span style="background: rgba(255,255,255,0.25); padding: 4px 10px; border-radius: 10px; font-size: 11px; font-weight: bold; color: white !important;">MEMBER</span>
        </div>
    </div>
    
    <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 10px;">
        <div>
            <p style="margin: 0; font-size: 10px; text-transform: uppercase; opacity: 0.7; color: white !important;">Cardholder Name</p>
            <p style="margin: 0; font-size: 15px; font-weight: bold; color: white !important;">{customer_name}</p>
            <p style="margin: 6px 0 0 0; font-size: 10px; text-transform: uppercase; opacity: 0.7; color: white !important;">Mobile ID</p>
            <p style="margin: 0; font-size: 13px; font-family: monospace; color: white !important;">{customer_mobile}</p>
        </div>
        <div>
            <p style="margin: 0; font-size: 10px; text-transform: uppercase; opacity: 0.7; text-align: center; color: white !important;">Stamps / Free</p>
            <p style="margin: 0; font-size: 16px; font-weight: bold; text-align: center; color: white !important;">☕ {current_stamps}/9 &nbsp;|&nbsp; 🏷️ {discounts}</p>
        </div>
    </div>
</div>
"""
        st.markdown(wallet_html, unsafe_allow_html=True)

        # Side-by-side view for QR code and Barcode
        col_q, col_b = st.columns(2)
        with col_q:
            st.markdown("#### 📱 Mobile Camera QR")
            st.image(qr_bytes, width=190, caption="Scan with smartphone camera")

        with col_b:
            st.markdown("#### 🏷️ POS Scanner Barcode")
            st.image(barcode_bytes, width=210, caption="Scan with counter barcode gun")

        st.markdown("---")
        st.info("💡 **Tip:** Screenshot this pass to save it to your phone photos or Apple/Google Wallet!")


    # --- TAB 3: PROFILE EDITOR ---
    with tab_profile:
        st.markdown("### ⚙️ Update Your Profile")
        with st.form("profile_edit_form"):
            new_name = st.text_input("Full Name", value=customer_name)
            new_email = st.text_input("Email", value=data.get("email", ""))
            update_submit = st.form_submit_button("Save Changes", use_container_width=True)
            
            if update_submit:
                try:
                    supabase.table("loyalty_cards").update({
                        "name": new_name,
                        "email": new_email
                    }).eq("mobile_number", customer_mobile).execute()
                    st.success("Profile updated successfully!")
                except Exception as e:
                    st.error(f"Failed to update profile: {e}")

        if st.button("🚪 Log Out", use_container_width=True):
            st.session_state.cust_logged_in = False
            st.session_state.cust_mobile = ""
            st.session_state.cust_data = None
            st.rerun()