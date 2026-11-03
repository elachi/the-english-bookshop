
import streamlit as st
import qrcode
import barcode
from barcode.writer import ImageWriter
from io import BytesIO
from datetime import datetime
from supabase import create_client
import os
import base64
from PIL import Image, ImageOps, ImageDraw, ImageFont
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

# --- CUSTOMER LOGIN SCREEN ---
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

# --- LOGGED-IN CUSTOMER DASHBOARD ---
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



    # --- TAB 2: MOBILE WALLET-STYLE LOYALTY CARD ---
    with tab_qr:
        st.markdown("### 📱 Your Café Tärnan Wallet Card")
        st.caption("Show this card at the counter to collect stamps or redeem rewards.")

        # Use the same member ID in both codes so POS scanners receive a
        # consistent value. Do not point the QR code to an unconfigured URL.
        member_id = str(customer_mobile).strip()
        qr_bytes = generate_qr_code(member_id)
        barcode_bytes = generate_barcode(member_id)

        @st.cache_data(show_spinner=False)
        def render_wallet_card(name, member_id, stamps, free_cups, qr_png, barcode_png):
            """Produce a scannable high-resolution wallet-style PNG."""
            W, H = 760, 1080
            img = Image.new("RGB", (W, H), "#f2f5f1")
            draw = ImageDraw.Draw(img)
            green, dark, pale = "#307041", "#204d2b", "#d5ead9"

            def font(size, bold=False):
                paths = ([
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                    "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
                    "arialbd.ttf",
                ] if bold else [
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                    "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
                    "arial.ttf",
                ])
                for path in paths:
                    try:
                        return ImageFont.truetype(path, size)
                    except OSError:
                        pass
                return ImageFont.load_default()

            # Card silhouette and green header (no alpha-to-black corners).
            draw.rounded_rectangle((22, 22, 738, 1058), radius=38, fill="white")
            draw.rounded_rectangle((22, 22, 738, 435), radius=38, fill=green)
            draw.rectangle((22, 395, 738, 435), fill=green)

            draw.text((70, 72), "CAFÉ TÄRNAN", font=font(33, True), fill="white")
            draw.text((70, 123), "LOYALTY CARD", font=font(18, True), fill=pale)
            draw.rounded_rectangle((568, 111, 686, 151), radius=20, fill=dark)
            draw.text((591, 121), "ACTIVE", font=font(17, True), fill="white")

            draw.text((70, 202), "CARDHOLDER", font=font(18, True), fill=pale)
            holder = str(name or "Valued Customer").strip()
            holder_font = font(38, True)
            while draw.textbbox((0, 0), holder, font=holder_font)[2] > 605 and len(holder) > 1:
                holder_font = font(max(18, holder_font.size - 2), True)
                if holder_font.size == 18:
                    while draw.textbbox((0, 0), holder + "…", font=holder_font)[2] > 605:
                        holder = holder[:-1]
                    holder += "…"
                    break
            draw.text((70, 235), holder, font=holder_font, fill="white")

            draw.text((70, 323), "STAMPS", font=font(18, True), fill=pale)
            draw.text((70, 352), f"{int(stamps) % 9} / 9", font=font(31, True), fill="white")
            draw.text((365, 323), "FREE COFFEES", font=font(18, True), fill=pale)
            draw.text((365, 352), str(int(free_cups)), font=font(31, True), fill="white")

            # White scanning area; quiet zones are preserved around both codes.
            draw.text((W // 2, 475), "SCAN AT THE COUNTER", anchor="mt",




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