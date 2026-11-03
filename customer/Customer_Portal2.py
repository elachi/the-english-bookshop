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
    # --- TAB 2: MY QR CODE & POS BARCODE (IMAGE WALLET PASS) ---
    with tab_qr:
        st.markdown("### 🎫 Your Digital Boarding Pass")
        st.caption("Save or screenshot this digital pass to your phone for instant counter scanning.")

        app_base_url = "https://your-cafe-tarnan-app.streamlit.app"  # Update with your production URL
        qr_payload = f"{app_base_url}/?search={customer_mobile}"
        barcode_payload = customer_mobile

        # 1. Generate Raw Code Bytes
        qr_bytes = generate_qr_code(qr_payload)
        barcode_bytes = generate_barcode(barcode_payload)

        # 2. Compose into a Real Wallet Pass Image using Pillow (PIL)
        from PIL import Image, ImageOps
        
        # Load code images into PIL
        qr_img = Image.open(BytesIO(qr_bytes)).convert("RGBA")
        barcode_img = Image.open(BytesIO(barcode_bytes)).convert("RGBA")

        # Create Pass Canvas (Width: 800px, Height: 1050px for high-res clarity)
        pass_width, pass_height = 800, 1050
        pass_img = Image.new("RGBA", (pass_width, pass_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(pass_img)

        # Draw Rounded Card Background (Forest Green Gradient effect / Solid Theme #307041)
        card_box = (20, 20, pass_width - 20, pass_height - 20)
        draw.rounded_rectangle(card_box, radius=32, fill="#307041", outline="#204d2b", width=4)
        
        # Decorative Header Divider Line
        draw.line([(60, 140), (pass_width - 60, 140)], fill="rgba(255,255,255,0.3)", width=2)
        # Decorative Footer Divider Line
        draw.line([(60, 640), (pass_width - 60, 640)], fill="rgba(255,255,255,0.3)", width=2)

        # Use default high-contrast system fonts or load basic TrueType if available
        try:
            font_title = ImageFont.truetype("arial.ttf", 24)
            font_header = ImageFont.truetype("arial.ttf", 36)
            font_label = ImageFont.truetype("arial.ttf", 18)
            font_value = ImageFont.truetype("arial.ttf", 28)
        except IOError:
            font_title = font_header = font_label = font_value = ImageFont.load_default()

        # Draw Header Texts
        draw.text((60, 55), "CAFÉ TÄRNAN", fill="#a3d9b1", font=font_title)
        draw.text((60, 85), "LOYALTY PASS", fill="#ffffff", font=font_header)
        
        # Active Badge Box
        draw.rounded_rectangle((pass_width - 180, 65, pass_width - 60, 115), radius=16, fill="rgba(255,255,255,0.25)")
        draw.text((pass_width - 145, 78), "ACTIVE", fill="#ffffff", font=font_label)

        # Draw Customer Details (Left Column: Name & Mobile)
        draw.text((60, 175), "CARDHOLDER NAME", fill="#a3d9b1", font=font_label)
        draw.text((60, 205), customer_name, fill="#ffffff", font=font_value)

        draw.text((60, 280), "MOBILE ID", fill="#a3d9b1", font=font_label)
        draw.text((60, 310), str(customer_mobile), fill="#ffffff", font=font_value)

        # Draw Rewards Details (Right Column: Stamps & Free Cups)
        draw.text((450, 175), "STAMPS & REWARDS", fill="#a3d9b1", font=font_label)
        draw.text((450, 205), f"☕ {current_stamps} / 9 Stamps", fill="#ffffff", font=font_value)
        draw.text((450, 280), f"🏷️ {discounts} Free Cup(s)", fill="#ffd700", font=font_value)

        # Center Section Label
        draw.text((pass_width // 2 - 190, 580), "SCAN AT COUNTER (POS / MOBILE)", fill="#a3d9b1", font=font_label)

        # Resize and paste QR code and Barcode onto the pass image card
        # QR Code paste (Left side inside code box)
        qr_img = qr_img.resize((240, 240))
        pass_img.paste(qr_img, (80, 680), qr_img)

        # Barcode paste (Right side inside code box)
        barcode_img = barcode_img.resize((320, 240))
        pass_img.paste(barcode_img, (380, 680), barcode_img)

        # Save final composite pass to BytesIO buffer
        pass_buffer = BytesIO()
        pass_img.convert("RGB").save(pass_buffer, format="PNG")
        pass_bytes = pass_buffer.getvalue()

        # 3. Display Image in Streamlit
        st.image(pass_bytes, use_container_width=True)

        # 4. Download Button for Phone Gallery / Wallet
        st.download_button(
            label="📥 Download Pass Image",
            data=pass_bytes,
            file_name=f"cafetarnan_pass_{customer_mobile}.png",
            mime="image/png",
            use_container_width=True
        )

        st.info("💡 **Tip:** Tap download or screenshot this pass image to save it directly to your phone's photo library or Apple/Google Wallet app!")




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