import streamlit as st
import qrcode
import barcode
from barcode.writer import ImageWriter
from io import BytesIO
from supabase import create_client
import os

# --- HELPER FUNCTIONS (Framework-Agnostic Python Code) ---
def generate_qr_code(url_string: str) -> bytes:
    """Generates a QR code image encoding a URL (for mobile cameras)."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(url_string)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0f2648", back_color="white")
    
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    return buffered.getvalue()

def generate_barcode(text_string: str) -> bytes:
    """Generates a Code128 Barcode image encoding a raw ID/mobile (for POS hardware scanners)."""
    rv = BytesIO()
    # Code128 supports numbers and characters cleanly
    Code128 = barcode.get_class('code128')
    # Clean string for barcode encoding
    clean_text = str(text_string).strip()
    barcode_obj = Code128(clean_text, writer=ImageWriter())
    
    # Render barcode image with text label underneath
    options = {'write_text': True, 'font_size': 10, 'text_distance': 5, 'dpi': 200}
    barcode_obj.write(rv, options=options)
    rv.seek(0)
    return rv.getvalue()

# --- STREAMLIT CUSTOMER PORTAL UI ---
st.image("DropCaffee/images/dropcafe.png", width=150)
st.title("☕ Your Drop Caffee Member Card")

# Assuming you retrieve the logged-in customer's profile data
# (e.g., from session state or a customer login session)
customer_mobile = st.session_state.get("customer_mobile", "0712345678")
customer_name = st.session_state.get("customer_name", "Valued Customer")
app_base_url = "https://your-dropcaffee-app.streamlit.app"  # Update with your production URL

# 1. Prepare Data Payload for Codes
# QR Code encodes the full URL parameter link for smartphone cameras
qr_payload = f"{app_base_url}/?search={customer_mobile}"

# Barcode encodes the raw mobile number/ID for the POS hardware scanner gun
barcode_payload = customer_mobile

# 2. Render Member Card UI Container
with st.container():
    st.subheader(f"Cardholder: {customer_name}")
    st.markdown(f"**Mobile Number / ID:** `{customer_mobile}`")
    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📱 Mobile Scan")
        st.caption("Scan with smartphone camera")
        qr_bytes = generate_qr_code(qr_payload)
        st.image(qr_bytes, width=200)

    with col2:
        st.markdown("### 🏷️ POS Scanner")
        st.caption("Scan with POS hardware scanner gun")
        barcode_bytes = generate_barcode(barcode_payload)
        st.image(barcode_bytes, width=220)

    st.markdown("---")
    st.info("💡 **Tip:** Take a screenshot of this card or save it to your phone wallet for quick access at the counter!")