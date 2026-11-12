
import streamlit as st
import qrcode
from io import BytesIO
from datetime import datetime
from supabase import create_client
import os
import json
import time
import hashlib
import zipfile
import re

import jwt
from PIL import Image

from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.serialization import pkcs7

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


    """Generates a signed Apple Wallet .pkpass byte stream safely."""
    if not APPLE_PASS_AVAILABLE:
        return None
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




def generate_apple_pkpass(
    customer_name,
    customer_mobile,
    current_stamps,
    free_cups=0
):
    """
    Generate a signed Apple Wallet loyalty card.
    Returns .pkpass file bytes.

    Requires Apple certificates in Streamlit secrets.
    """

    # 1. Read Apple Wallet configuration
    pass_type_id = st.secrets["APPLE_PASS_TYPE_ID"]
    team_id = st.secrets["APPLE_TEAM_ID"]

    cert_pem = st.secrets["APPLE_CERT_PEM"].replace("\\n", "\n")
    key_pem = st.secrets["APPLE_KEY_PEM"].replace("\\n", "\n")
    wwdr_pem = st.secrets["APPLE_WWDR_PEM"].replace("\\n", "\n")

    # 2. Load certificates and signing key
    certificate = x509.load_pem_x509_certificate(
        cert_pem.encode("utf-8")
    )

    private_key = serialization.load_pem_private_key(
        key_pem.encode("utf-8"),
        password=None
    )

    wwdr_certificate = x509.load_pem_x509_certificate(
        wwdr_pem.encode("utf-8")
    )

    # 3. Prepare customer data
    customer_name = str(customer_name)
    customer_mobile = str(customer_mobile)

    stamp_count = max(0, int(current_stamps))
    reward_count = max(0, int(free_cups))

    # 4. Create Apple Wallet pass data
    pass_data = {
        "formatVersion": 1,
        "passTypeIdentifier": pass_type_id,
        "serialNumber": customer_mobile,
        "teamIdentifier": team_id,
        "organizationName": "Café Tärnan",
        "description": "Café Tärnan Loyalty Card",

        "logoText": "Café Tärnan",
        "backgroundColor": "rgb(48,112,65)",
        "foregroundColor": "rgb(255,255,255)",
        "labelColor": "rgb(255,255,255)",

        "storeCard": {
            "primaryFields": [
                {
                    "key": "stamps",
                    "label": "COFFEE STAMPS",
                    "value": f"{stamp_count} / 9"
                }
            ],
            "secondaryFields": [
                {
                    "key": "customer",
                    "label": "CARDHOLDER",
                    "value": customer_name
                }
            ],
            "auxiliaryFields": [
                {
                    "key": "rewards",
                    "label": "FREE COFFEES",
                    "value": reward_count
                }
            ],
            "backFields": [
                {
                    "key": "instructions",
                    "label": "How it works",
                    "value": (
                        "Collect 9 stamps and earn a free coffee. "
                        "Present your QR code at Café Tärnan."
                    )
                }
            ]
        },

        "barcodes": [
            {
                "format": "PKBarcodeFormatQR",
                "message": customer_mobile,
                "messageEncoding": "iso-8859-1",
                "altText": customer_mobile
            }
        ]
    }

    # 5. Create pass files in memory
    pass_files = {
        "pass.json": json.dumps(
            pass_data,
            ensure_ascii=False
        ).encode("utf-8")
    }

    # Apple Wallet requires icon.png
    if os.path.exists("cafetarnan.jpg"):
        source_image = Image.open(
            "cafetarnan.jpg"
        ).convert("RGBA")
    else:
        source_image = Image.new(
            "RGBA", (87, 87), (48, 112, 65, 255)
        )

    for filename, size in [
        ("icon.png", 29),
        ("icon@2x.png", 58),
        ("icon@3x.png", 87)
    ]:
        resized = source_image.resize(
            (size, size),
            Image.Resampling.LANCZOS
        )

        image_buffer = BytesIO()
        resized.save(image_buffer, format="PNG")
        pass_files[filename] = image_buffer.getvalue()

    # 6. Generate manifest with SHA-1 file hashes
    manifest = {
        filename: hashlib.sha1(content).hexdigest()
        for filename, content in pass_files.items()
    }

    manifest_bytes = json.dumps(
        manifest,
        separators=(",", ":")
    ).encode("utf-8")

    pass_files["manifest.json"] = manifest_bytes

    # 7. Sign manifest with Apple's certificate
    signature = (
        pkcs7.PKCS7SignatureBuilder()
        .set_data(manifest_bytes)
        .add_signer(
            certificate,
            private_key,
            hashes.SHA256()
        )
        .add_certificate(wwdr_certificate)
        .sign(
            serialization.Encoding.DER,
            [
                pkcs7.PKCS7Options.DetachedSignature,
                pkcs7.PKCS7Options.Binary
            ]
        )
    )

    pass_files["signature"] = signature

    # 8. Package as a .pkpass ZIP archive
    output = BytesIO()

    with zipfile.ZipFile(
        output,
        "w",
        zipfile.ZIP_DEFLATED
    ) as archive:
        for filename, content in pass_files.items():
            archive.writestr(filename, content)

    output.seek(0)

    return output.getvalue()





def generate_google_wallet_link(
    customer_name,
    customer_mobile,
    current_stamps,
    free_cups=0
):
    """
    Create or update a Google Wallet loyalty card.

    Returns a signed Add to Google Wallet URL.
    """

    # 1. Read Google Wallet configuration
    issuer_id = str(st.secrets["GOOGLE_ISSUER_ID"])
    logo_url = st.secrets["GOOGLE_WALLET_LOGO_URL"]

    service_info = json.loads(
        st.secrets["GOOGLE_SERVICE_ACCOUNT_JSON"]
    )

    # 2. Authenticate
    credentials = (
        service_account.Credentials.from_service_account_info(
            service_info,
            scopes=[
                "https://www.googleapis.com/auth/wallet_object.issuer"
            ]
        )
    )

    session = AuthorizedSession(credentials)

    api_base = "https://walletobjects.googleapis.com/walletobjects/v1"

    # 3. Create stable identifiers
    class_id = f"{issuer_id}.cafetarnan_loyalty"

    # Google Wallet IDs can only use supported characters
    customer_id = re.sub(
        r"[^A-Za-z0-9_.-]",
        "_",
        str(customer_mobile)
    )

    object_id = f"{issuer_id}.customer_{customer_id}"

    customer_name = str(customer_name)
    customer_mobile = str(customer_mobile)

    stamp_count = max(0, int(current_stamps))
    reward_count = max(0, int(free_cups))

    # 4. Ensure the loyalty class exists
    class_response = session.get(
        f"{api_base}/loyaltyClass/{class_id}",
        timeout=20
    )

    if class_response.status_code == 404:

        loyalty_class = {
            "id": class_id,
            "issuerName": "Café Tärnan",
            "programName": "Coffee Loyalty",
            "reviewStatus": "UNDER_REVIEW",
            "programLogo": {
                "sourceUri": {
                    "uri": logo_url
                },
                "contentDescription": {
                    "defaultValue": {
                        "language": "en-US",
                        "value": "Café Tärnan logo"
                    }
                }
            },
            "hexBackgroundColor": "#307041"
        }

        create_response = session.post(
            f"{api_base}/loyaltyClass",
            json=loyalty_class,
            timeout=20
        )

        if create_response.status_code not in (200, 201, 409):
            raise RuntimeError(
                "Could not create Google Wallet loyalty class: "
                f"{create_response.status_code} "
                f"{create_response.text[:300]}"
            )

    elif not class_response.ok:
        raise RuntimeError(
            "Could not access Google Wallet loyalty class: "
            f"{class_response.status_code} "
            f"{class_response.text[:300]}"
        )

    # 5. Customer-specific loyalty object
    loyalty_object = {
        "id": object_id,
        "classId": class_id,
        "state": "ACTIVE",
        "accountId": customer_mobile,
        "accountName": customer_name,

        "loyaltyPoints": {
            "label": "Coffee Stamps",
            "balance": {
                "int": stamp_count
            }
        },

        "textModulesData": [
            {
                "id": "stamp_progress",
                "header": "STAMPS",
                "body": f"{stamp_count} / 9"
            },
            {
                "id": "free_coffees",
                "header": "FREE COFFEES",
                "body": str(reward_count)
            },
            {
                "id": "instructions",
                "header": "HOW IT WORKS",
                "body": "Collect 9 stamps and get a free coffee."
            }
        ],

        "barcode": {
            "type": "QR_CODE",
            "value": customer_mobile,
            "alternateText": customer_mobile
        }
    }

    # 6. Check whether customer object already exists
    object_response = session.get(
        f"{api_base}/loyaltyObject/{object_id}",
        timeout=20
    )

    if object_response.status_code == 200:

        # Update the existing card details
        update_data = {
            "accountName": customer_name,
            "loyaltyPoints": loyalty_object["loyaltyPoints"],
            "textModulesData": loyalty_object["textModulesData"],
            "barcode": loyalty_object["barcode"]
        }

        update_response = session.patch(
            f"{api_base}/loyaltyObject/{object_id}",
            json=update_data,
            timeout=20
        )

        update_response.raise_for_status()

        # Existing object only needs its ID in the JWT
        wallet_payload = {
            "loyaltyObjects": [
                {"id": object_id}
            ]
        }

    elif object_response.status_code == 404:

        # Create the object when the customer saves it
        wallet_payload = {
            "loyaltyObjects": [loyalty_object]
        }

    else:
        object_response.raise_for_status()

    # 7. Sign Add to Google Wallet JWT
    claims = {
        "iss": service_info["client_email"],
        "aud": "google",
        "typ": "savetowallet",
        "iat": int(time.time()),
        "payload": wallet_payload
    }

    token = jwt.encode(
        claims,
        service_info["private_key"],
        algorithm="RS256"
    )

    # 8. Return Add to Google Wallet URL
    return f"https://pay.google.com/gp/v/save/{token}"






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



    
    # --- TAB 2: SMARTPHONE WALLET PASSES ---
    with tab_wallet:

        st.markdown("### 📱 Your Café Tärnan Wallet Card")

        st.caption(
            "Save your loyalty card to your phone. "
            "Use it at Café Tärnan to collect stamps."
        )

        # Show current loyalty information
        st.markdown(f"**Customer:** {customer_name}")
        st.markdown(f"**Stamps:** {current_stamps} / 9")
        st.markdown(f"**Free coffees:** {discounts}")

        st.divider()

        col_apple, col_google = st.columns(2)

        # --- APPLE WALLET ---
        with col_apple:

            st.markdown("#### 🍏 Apple Wallet")

            try:
                apple_bytes = generate_apple_pkpass(
                    customer_name,
                    customer_mobile,
                    current_stamps,
                    discounts
                )

                st.download_button(
                    label="Add to Apple Wallet",
                    data=apple_bytes,
                    file_name="cafetarnan_loyalty.pkpass",
                    mime="application/vnd.apple.pkpass",
                    use_container_width=True
                )

            except Exception as e:
                st.info(
                    "Apple Wallet is not yet configured."
                )
                # For debugging during development:
                # st.error(str(e))

        # --- GOOGLE WALLET ---
        with col_google:

            st.markdown("#### 💳 Google Wallet")

            try:
                google_url = generate_google_wallet_link(
                    customer_name,
                    customer_mobile,
                    current_stamps,
                    discounts
                )

                st.link_button(
                    label="Add to Google Wallet",
                    url=google_url,
                    use_container_width=True
                )

            except Exception as e:
                st.info(
                    "Google Wallet is not yet configured."
                )
                # For debugging during development:
                # st.error(str(e))

        st.divider()

        # --- EXISTING QR CODE BACKUP ---
        st.markdown("### 📱 Customer QR Code")

        qr_bytes = generate_qr_code(customer_mobile)

        st.image(qr_bytes, width=200)

        st.caption(
            "Show this code at Café Tärnan "
            "to collect your stamps."
        )

    






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