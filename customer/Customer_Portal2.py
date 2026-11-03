import streamlit as st
import qrcode
import barcode
from barcode.writer import ImageWriter
from io import BytesIO
from supabase import create_client
import os
import base64

# 1. Page Config
st.set_page_config(
    page_title="Drop Caffee - Member Card", 
    page_icon="☕", 
    layout="centered"
)

# 2. Custom CSS for Boarding Pass / Wallet Card & Branding
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
        .wallet-card {
            background: linear-gradient(135deg, #0f2648 0%, #1c3b6d 100%);
            border-radius: 20px;
            padding: 25px;
            color: white !important;
            box-shadow: 0 12px 30px rgba(15, 38, 72, 0.25);
            margin-top: 10px;
            margin-bottom: 20px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        .wallet-card h3, .wallet-card p, .wallet-card span, .wallet-card div {
            color: white !important;
        }
        .pass-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px dashed rgba(255, 255, 255, 0.3);
            padding-bottom: 15px;
            margin-bottom: 15px;
        }
    </style>
""", unsafe_allow_html=True)

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

# --- HELPER FUNCTIONS (Framework-Agnostic) ---
def generate_qr_code(url_string: str) -> bytes:
    """Generates a QR code image encoding a URL (for mobile cameras)."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=1,
    )
    qr.add_data(url_string)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0f2648", back_color="white")
    
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    return buffered.getvalue()

def generate_barcode(text_string: str) -> bytes:
    """Generates a Code128 Barcode image encoding a raw mobile ID (for POS scanners)."""
    rv = BytesIO()
    Code128 = barcode.get_class('code128')
    clean_text = str(text_string).strip()
    barcode_obj = Code128(clean_text, writer=ImageWriter())
    
    options = {'write_text': True, 'font_size': 9, 'text_distance': 4, 'dpi': 200, 'quiet_zone': 2}
    barcode_obj.write(rv, options=options)
    rv.seek(0)
    return rv.getvalue()

def img_to_base64(img_bytes: bytes) -> str:
    return base64.b64encode(img_bytes).decode('utf-8')

# --- CUSTOMER PORTAL VIEW ---
st.image("DropCaffee/images/dropcafe.png", width=140)
st.title("☕ Customer Member Portal")

# For demonstration or session-based customer lookup
# You can replace customer_mobile with your dynamic session state variable (e.g. st.session_state.get("customer_mobile"))
customer_mobile = st.session_state.get("customer_mobile", "0712345678")
customer_name = st.session_state.get("customer_name", "Valued Member")
app_base_url = "https://your-dropcaffee-app.streamlit.app"  # Update with your deployed URL

# Fetch live card data from Supabase if connected
current_stamps = 0
current_discounts = 0
if supabase:
    try:
        res = supabase.table("loyalty_cards").select("*").eq("mobile_number", customer_mobile).execute()
        if res.data:
            card_data = res.data[0]
            customer_name = card_data.get("name", customer_name)
            current_stamps = card_data.get("stamps", 0)
            current_discounts = card_data.get("free_cups", 0)
    except Exception:
        pass

# Payloads
qr_payload = f"{app_base_url}/?search={customer_mobile}"
barcode_payload = customer_mobile

qr_bytes = generate_qr_code(qr_payload)
barcode_bytes = generate_barcode(barcode_payload)

# --- VIRTUAL BOARDING PASS CARD UI ---
st.markdown("### 🎫 Your Digital Member Pass")
st.caption("Present this wallet pass at the counter for instant mobile scanning or POS barcode checkout.")

st.markdown(f"""
<div class="wallet-card">
    <div class="pass-header">
        <div>
            <h4 style="margin: 0; font-size: 18px; letter-spacing: 1px;">DROP CAFFEE PASS</h4>
            <p style="margin: 0; font-size: 13px; opacity: 0.8;">Loyalty & Rewards Club</p>
        </div>
        <div style="text-align: right;">
            <span style="background: rgba(255,255,255,0.2); padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: bold;">ACTIVE</span>
        </div>
    </div>
    
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
        <div>
            <p style="margin: 0; font-size: 11px; text-transform: uppercase; opacity: 0.7;">Cardholder Name</p>
            <p style="margin: 0; font-size: 16px; font-weight: bold;">{customer_name}</p>
            <p style="margin: 8px 0 0 0; font-size: 11px; text-transform: uppercase; opacity: 0.7;">Mobile ID</p>
            <p style="margin: 0; font-size: 14px; font-family: monospace;">{customer_mobile}</p>
        </div>
        <div>
            <p style="margin: 0; font-size: 11px; text-transform: uppercase; opacity: 0.7; text-align: center;">Stamps / Rewards</p>
            <p style="margin: 0; font-size: 18px; font-weight: bold; text-align: center;">☕ {current_stamps}/9 &nbsp;|&nbsp; 🏷️ {current_discounts} Free</p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Side-by-side display of the QR code and Barcode inside clean sections
col1, col2 = st.columns(2)

with col1:
    st.markdown("#### 📱 Mobile Camera QR")
    st.image(qr_bytes, width=200, caption="Scan with smartphone camera")

with col2:
    st.markdown("#### 🏷️ POS Scanner Barcode")
    st.image(barcode_bytes, width=220, caption="Scan with counter barcode gun")

st.markdown("---")
st.info("💡 **Tip:** Take a screenshot of this pass and save it to your phone's photo library or Apple/Google Wallet for fast access!")