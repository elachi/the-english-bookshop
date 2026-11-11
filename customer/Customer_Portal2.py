import streamlit as st
import qrcode
from io import BytesIO
from datetime import datetime
from supabase import create_client
import os
import jwt
import time
from google.oauth2 import service_account
from py_pkpass import Pass, Barcode, BarcodeFormat
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

# 1. MUST BE THE FIRST STREAMLIT COMMAND IN YOUR FILE (Called only once)
st.set_page_config(
    page_title="Café Tärnan Loyalty Program", 
    page_icon="☕", 
    layout="centered"
)

# 2. INJECT CUSTOM CSS TO HIDE THE MENUS & FOOTER & STYLE THE CARD
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        .block-container {
            padding-top: 2rem;
        }
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

# --- HELPER FUNCTIONS ---
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

def generate_apple_pkpass(customer_name, customer_mobile, current_stamps):
    """Generates a signed Apple Wallet .pkpass byte stream."""
    try:
        passfile = Pass(
            passTypeIdentifier="pass.com.cafetarnan.loyalty",
            teamIdentifier="YOUR_APPLE_TEAM_ID",
            organizationName="Café Tärnan",
            description="Café Tärnan Loyalty Pass"
        )
        passfile.serial_number = str(customer_mobile)
        passfile.backgroundColor = "rgb(48, 112, 65)"
        passfile.foregroundColor = "rgb(255, 255, 255)"
        
        passfile.barcode = Barcode(
            message=str(customer_mobile),
            format=BarcodeFormat.CODE128,
            altText=str(customer_mobile)
        )
        
        passfile.addPrimaryField('customer_name', customer_name, 'CARDHOLDER')
        passfile.addSecondaryField('stamps', f"{current_stamps} / 9", 'STAMPS')
        
        # Uncomment once your .pem certificate files are added to your directory:
        # return passfile.create('certificate.pem', 'private.key', 'wwdr.pem')
        return None
    except Exception as e:
        return None

def generate_google_wallet_link(customer_name, customer_mobile, current_stamps):
    """Generates a secure 'Save to Google Wallet' URL via JWT."""
    try:
        issuer_id = "YOUR_GOOGLE_ISSUER_ID"
        key_file_path = "service_account.json"
        
        if not os.path.exists(key_file_path):
            return None
            
        credentials = service_account.Credentials.from_service_account_file(key_file_path)
        object_id = f"{issuer_id}.cust_{customer_mobile}"
        
        new_object = {
            "id": object_id,
            "classId": f"{issuer_id}.cafetarnan_loyalty_class",
            "state": "ACTIVE",
            "textModulesData": [
                {"header": "CARDHOLDER", "body": customer_name},
                {"header": "STAMPS", "body": f"{current_stamps} / 9"}
            ],
            "barcode": {
                "type": "CODE_128",
                "value": str(customer_mobile),
                "alternateText": str(customer_mobile)
            }
        }
        
        claims = {
            "iss": credentials.service_account_email,
            "aud": "google",
            "typ": "savetowallet",
            "iat": int(time.time()),
            "payload": {"loyaltyObjects": [new_object]}
        }
        
        token = jwt.encode(claims, credentials.signer_secret_string or key_file_path, algorithm="RS256")
        return f"https://pay.google.com/gp/v/save/{token}"
    except Exception as e:
        return None

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

if os.path.exists("cafetarnan.jpg"):
    st.image("cafetarnan.jpg", width=120)
st.subheader("Your loyalty stamp Card")

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
    
    # Three Tabs: Digital Card, Smartphone Wallet Passes, Profile Editor
    tab_stamps, tab_wallet, tab_profile = st.tabs(["📖 Digital Card", "📱 Smartphone Wallets", "⚙️ Profile Editor"])

    # --- TAB 1: DIGITAL CARD & REWARDS ---
    with tab_stamps:
        stamps_left = max(0, 9 - (current_stamps % 9))
        if stamps_left == 0 and current_stamps > 0:
            stamps_left = 9

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

    # --- TAB 2: SMARTPHONE WALLET PASSES (Apple & Google) ---
    with tab_wallet:
        st.markdown("### 🎫 Native Smartphone Wallet Passes")
        st.caption("Add your loyalty pass directly to Apple Wallet or Google Wallet.")

        col_apple, col_google = st.columns(2)

        with col_apple:
            st.markdown("#### 🍏 Apple Wallet")
            apple_bytes = generate_apple_pkpass(customer_name, customer_mobile, current_stamps)
            if apple_bytes:
                st.download_button(
                    label="Download .pkpass",
                    data=apple_bytes,
                    file_name=f"cafetarnan_{customer_mobile}.pkpass",
                    mime="application/vnd.apple.pkpass",
                    use_container_width=True
                )
            else:
                st.info("Apple Developer certificates required to generate live .pkpass files.")

        with col_google:
            st.markdown("#### 💳 Google Wallet")
            google_url = generate_google_wallet_link(customer_name, customer_mobile, current_stamps)
            if google_url:
                st.markdown(f"""
                    <a href="{google_url}" target="_blank">
                        <img src="https://developers.google.com/pay/wallet/images/wallet-button.png" height="45px" alt="Save to Google Wallet">
                    </a>
                """, unsafe_allow_html=True)
            else:
                st.info("Google Service Account JSON required to enable instant 'Save to Google Wallet' links.")

        st.markdown("---")
        st.markdown("### 📱 QR Code Backup")
        qr_bytes = generate_qr_code(customer_mobile)
        st.image(qr_bytes, width=200)

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