import streamlit as st
from datetime import datetime
from supabase import create_client
from argon2 import PasswordHasher
import re

# 1. MUST BE THE FIRST STREAMLIT COMMAND IN YOUR FILE
st.set_page_config(
    page_title="The English Bookstore - Member Management", 
    page_icon="📚", 
    layout="centered"
)

# 2. INJECT CUSTOM CSS TO HIDE THE MENUS & FOOTER
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
    </style>
""", unsafe_allow_html=True)

# --- SECURITY CHECK ---
if not st.session_state.get("logged_in", False):
    st.warning("Please log in from the main home page first.")
    st.stop()

# Supabase Connection Setup (Using Streamlit Secrets)
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except Exception as e:
    st.error(f"Missing Streamlit secrets configuration: {e}")
    st.stop()

@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL.strip().rstrip('/'), SUPABASE_KEY)

supabase = init_supabase()

st.title("📝 New Members & Profile Editor")

# --- ARGON2ID PASSWORD HASHER ---
ph = PasswordHasher()

def hash_password(password: str) -> str:
    return ph.hash(password)

# Helper function for Swedish mobile validation
def validate_swedish_mobile(mobile: str) -> bool:
    pattern = r"^07\d{8}$"
    return bool(re.match(pattern, mobile.strip()))

# --- SESSION STATES ---
if "edit_search" not in st.session_state:
    st.session_state.edit_search = ""
if "do_clear_edit" not in st.session_state:
    st.session_state.do_clear_edit = False
if "confirm_delete" not in st.session_state:
    st.session_state.confirm_delete = False

if st.session_state.do_clear_edit:
    st.session_state.edit_search = ""
    st.session_state.do_clear_edit = False
    st.session_state.confirm_delete = False

def reset_edit_search():
    st.session_state.do_clear_edit = True

tab_reg, tab_edit = st.tabs(["➕ Register New Member", "🔍 Search & Edit Member"])

# ------------------------------------------
# TAB 1: REGISTER NEW MEMBER
# ------------------------------------------
with tab_reg:
    st.subheader("Onboard Walk-In Customer")
    
    with st.form("reg_form", clear_on_submit=True):
        new_mobile = st.text_input("Mobile Number * (Swedish format e.g., 0712345678)", placeholder="0712345678")
        new_name = st.text_input("Customer Name", placeholder="e.g., Jane Doe")
        
        # --- PASSWORD FIELD ---
        new_password = st.text_input("Member Password * (Required)", type="password", placeholder="Enter member password")
        
        new_email = st.text_input("Email (Optional)", placeholder="e.g., jane@hotmail.com")
        initial_stamps = st.number_input("Initial Book Stamps", min_value=0, max_value=9, value=0)
        receive_ads = st.checkbox("Receive promotional emails & special offer ads", value=True)
        
        submitted = st.form_submit_button("Create Member Card", use_container_width=True)
            
        if submitted:
            cleaned_mobile = new_mobile.strip()
            if not cleaned_mobile:
                st.error("❌ Mobile number is required.")
            elif not validate_swedish_mobile(cleaned_mobile):
                st.error("❌ Invalid Swedish mobile number format! Must start with '07' and be exactly 10 digits (e.g., 0712345678).")
            elif not new_password.strip():
                st.error("❌ Password is required for member account creation.")
            else:
                try:
                    now_str = datetime.utcnow().isoformat()
                    encrypted_pwd = hash_password(new_password) # Never saved in plain text
                    
                    supabase.table("loyalty_cards").insert({
                        "mobile_number": cleaned_mobile,
                        "email": new_email.strip().lower() if new_email else None,
                        "name": new_name.strip() if new_name else "Valued Customer",
                        "password_hash": encrypted_pwd,
                        "receive_ads": receive_ads,
                        "stamps": initial_stamps,
                        "free_cups": 0,
                        "free_cup_expiries": [],
                        "created_at": now_str,
                        "last_stamp_at": now_str if initial_stamps > 0 else None,
                        "last_visit": now_str,
                        "updated_at": now_str
                    }).execute()
                    
                    st.success(f"✅ Successfully registered member! (Mobile: {cleaned_mobile})")
                    st.toast("Member created successfully!", icon="🎉")
                except Exception as e:
                    st.error(f"Error creating account: {e}")

# ------------------------------------------
# TAB 2: SEARCH & EDIT MEMBER
# ------------------------------------------
with tab_edit:
    st.subheader("Edit Existing Member Details")
    
    col_input, col_btn = st.columns([4, 1])
    with col_input:
        search_query = st.text_input("Lookup Mobile or Email to Edit", placeholder="Enter mobile or email...", key="edit_search")
    with col_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        st.button("🧹 Clear", on_click=reset_edit_search, use_container_width=True)

    if search_query:
        try:
            query_val = search_query.strip()
            res = supabase.table("loyalty_cards").select("*").eq("mobile_number", query_val).execute()
            if not res.data:
                res = supabase.table("loyalty_cards").select("*").eq("email", query_val.lower()).execute()
            
            if res.data:
                member = res.data[0]
                member_id = member["id"]
                
                st.success(f"Found member: **{member.get('name', 'Valued Customer')}**")
                
                with st.form("edit_member_form"):
                    edit_name = st.text_input("Customer Name", value=member.get("name", ""))
                    edit_mobile = st.text_input("Mobile Number (07xxxxxxxx)", value=member.get("mobile_number", ""))
                    edit_email = st.text_input("Email Address", value=member.get("email", ""))
                    edit_stamps = st.number_input("Current Stamps", min_value=0, max_value=9, value=member.get("stamps", 0))
                    edit_discounts = st.number_input("Available Discounts (Bank)", min_value=0, max_value=2, value=member.get("free_cups", 0))
                    
                    save_btn = st.form_submit_button("Save Changes", use_container_width=True)
                    
                    if save_btn:
                        cleaned_edit_mobile = edit_mobile.strip()
                        if not validate_swedish_mobile(cleaned_edit_mobile):
                            st.error("❌ Invalid Swedish mobile number format! Must start with '07' and be 10 digits (e.g., 0712345678).")
                        else:
                            try:
                                supabase.table("loyalty_cards").update({
                                    "name": edit_name.strip(),
                                    "mobile_number": cleaned_edit_mobile,
                                    "email": edit_email.strip().lower() if edit_email else None,
                                    "stamps": edit_stamps,
                                    "free_cups": edit_discounts,
                                    "updated_at": datetime.utcnow().isoformat()
                                }).eq("id", member_id).execute()
                                
                                st.success("✅ Member profile updated successfully!")
                                st.toast("Changes saved!", icon="💾")
                            except Exception as err:
                                st.error(f"Failed to update member: {err}")
            else:
                st.warning("No member found matching that mobile number or email.")
        except Exception as e:
            st.error(f"Database lookup error: {e}")