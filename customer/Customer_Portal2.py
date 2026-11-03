import streamlit as st
import qrcode
import barcode
from barcode.writer import ImageWriter
from io import BytesIO
from datetime import datetime
from supabase import create_client
import os
import base64  # <--- Make sure this is added here!
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






# --- TAB 2: MY QR CODE & POS BARCODE (WALLET BOARDING PASS) ---
    # --- TAB 2: MY QR CODE & POS BARCODE (WALLET BOARDING PASS) ---
    with tab_qr:
        st.markdown("### 🎫 Your Digital Boarding Pass")
        st.caption("Present this digital wallet pass at the counter for smartphone camera scanning or POS barcode checkout.")

        app_base_url = "https://your-cafe-tarnan-app.streamlit.app"  # Update with your production URL
        qr_payload = f"{app_base_url}/?search={customer_mobile}"
        barcode_payload = customer_mobile

        qr_bytes = generate_qr_code(qr_payload)
        barcode_bytes = generate_barcode(barcode_payload)

        # Convert images to base64
        qr_b64 = base64.b64encode(qr_bytes).decode('utf-8')
        barcode_b64 = base64.b64encode(barcode_bytes).decode('utf-8')

        # Single-line HTML string to prevent markdown code-block escaping
        pass_html = f'<div style="background: linear-gradient(135deg, #307041 0%, #1a3d24 100%); border-radius: 20px; padding: 24px; color: white; box-shadow: 0 12px 30px rgba(48, 112, 65, 0.3); font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, sans-serif; margin-top: 15px; margin-bottom: 20px; border: 1px solid rgba(255,255,255,0.2);"><div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px dashed rgba(255, 255, 255, 0.4); padding-bottom: 15px; margin-bottom: 18px;"><div><div style="font-size: 11px; text-transform: uppercase; letter-spacing: 1.5px; opacity: 0.8; color: #a3d9b1;">CAFÉ TÄRNAN</div><div style="font-size: 18px; font-weight: 800; letter-spacing: 0.5px; color: #ffffff; margin-top: 2px;">LOYALTY PASS</div></div><div style="text-align: right;"><span style="background: rgba(255, 255, 255, 0.2); padding: 5px 12px; border-radius: 12px; font-size: 11px; font-weight: bold; letter-spacing: 1px; color: #ffffff;">ACTIVE</span></div></div><div style="display: flex; justify-content: space-between; margin-bottom: 20px;"><div><div style="font-size: 10px; text-transform: uppercase; opacity: 0.7; letter-spacing: 1px; color: #a3d9b1;">Cardholder Name</div><div style="font-size: 16px; font-weight: 700; color: #ffffff; margin-top: 2px;">{customer_name}</div><div style="font-size: 10px; text-transform: uppercase; opacity: 0.7; letter-spacing: 1px; color: #a3d9b1; margin-top: 12px;">Mobile ID</div><div style="font-size: 14px; font-family: monospace; color: #ffffff; margin-top: 2px;">{customer_mobile}</div></div><div style="text-align: right;"><div style="font-size: 10px; text-transform: uppercase; opacity: 0.7; letter-spacing: 1px; color: #a3d9b1;">Stamps & Rewards</div><div style="font-size: 16px; font-weight: 700; color: #ffffff; margin-top: 2px;">☕ {current_stamps} / 9</div><div style="font-size: 13px; font-weight: 600; color: #ffd700; margin-top: 4px;">🏷️ {discounts} Free Cup(s)</div></div></div><div style="border-top: 1px dashed rgba(255, 255, 255, 0.4); padding-top: 18px; margin-top: 10px; text-align: center;"><div style="font-size: 10px; text-transform: uppercase; letter-spacing: 1px; opacity: 0.8; color: #a3d9b1; margin-bottom: 10px;">Scan at Counter (POS / Mobile Camera)</div><div style="display: flex; justify-content: center; gap: 15px; align-items: center; background: white; padding: 12px; border-radius: 12px;"><div style="text-align: center;"><img src="data:image/png;base64,{qr_b64}" width="125" style="display: block; margin: 0 auto;"/><span style="font-size: 9px; color: #307041; font-weight: bold; margin-top: 4px; display: block;">QR Code</span></div><div style="width: 1px; background: #ddd; height: 105px;"></div><div style="text-align: center;"><img src="data:image/png;base64,{barcode_b64}" width="155" style="display: block; margin: 0 auto;"/><span style="font-size: 9px; color: #307041; font-weight: bold; margin-top: 4px; display: block;">POS Barcode</span></div></div></div></div>'
        
        st.markdown(pass_html, unsafe_allow_html=True)
        st.info("💡 **Tip:** Take a screenshot of this boarding pass and save it directly to your phone's photo library or wallet app for instant scanning!")




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