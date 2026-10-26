import streamlit as st
from datetime import datetime
from supabase import create_client
from argon2 import PasswordHasher





# 1. MUST BE THE FIRST STREAMLIT COMMAND IN YOUR FILE
st.set_page_config(
    page_title="Café Tärnan Loyalty Program", 
    page_icon="☕", 
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

supabase = create_client(st.secrets["SUPABASE_URL"].strip().rstrip('/'), st.secrets["SUPABASE_KEY"])

st.image("cafetarnan.jpg", width=150)
st.title("Tärnan New Members & Profile Editor")

# --- ARGON2ID PASSWORD HASHER ---
ph = PasswordHasher()

def hash_password(password: str) -> str:
    return ph.hash(password)

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
        new_mobile = st.text_input("Mobile Number * (Required - Primary ID)", placeholder="e.g., 071 234 56 78")
        new_name = st.text_input("Customer Name", placeholder="e.g., Jane Doe")
        
        # --- PASSWORD FIELD ---
        new_password = st.text_input("Member Password * (Required)", type="password", placeholder="Enter member password")
        
        new_email = st.text_input("Email (Optional)", placeholder="e.g., jane@hotmail.com")
        initial_stamps = st.number_input("Initial Book Stamps", min_value=0, max_value=9, value=0)
        receive_ads = st.checkbox("Receive promotional emails & special offer ads", value=True)
        
        submitted = st.form_submit_button("Create Member Card", use_container_width=True)
            
        if submitted:
            if not new_mobile.strip():
                st.error("❌ Mobile number is required.")
            elif not new_password.strip():
                st.error("❌ Password is required for member account creation.")
            else:
                try:
                    now_str = datetime.utcnow().isoformat()
                    encrypted_pwd = hash_password(new_password) # Never saved in plain text
                    
                    supabase.table("loyalty_cards").insert({
                        "mobile_number": new_mobile.strip(),
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
                    
                    st.success(f"✅ Successfully registered member! (Mobile: {new_mobile.strip()})")
                except Exception as e:
                    st.error(f"Error creating account: {e}")

# ------------------------------------------
# TAB 2: SEARCH & EDIT MEMBER
# ------------------------------------------
with tab_edit:
    st.subheader("Edit Existing Member Details")
    
    col_input, col_btn = st.columns([4, 1])
    with col_input:
        search_query = st.text_input("Lookup Mobile or Email to Edit", placeholder="Enter mobile number...", key="edit_search")
    with col_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        st.button("🧹 Clear", on_click=reset_edit_search, use_container_width=True)

    if search_query:
        try:
            res = supabase.table("loyalty_cards").select("*").eq("mobile_number", search_query.strip()).execute()
            if not res.data:
                res = supabase.table("loyalty_cards").select("*").eq("email", search_query.strip().lower()).execute()
            
            if res.data:
                m = res.data[0]
                customer_name = m.get("name", "Valued Customer")
                st.success(f"Found Member: **{customer_name}**")
                
                with st.form("edit_form"):
                    e_name = st.text_input("Name", value=m.get("name", ""))
                    e_mobile = st.text_input("Mobile Number", value=m.get("mobile_number", ""))
                    e_email = st.text_input("Email", value=m.get("email", "") or "")
                    e_password = st.text_input("Reset Password (Leave blank to keep existing)", type="password")
                    e_stamps = st.number_input("Stamps", min_value=0, max_value=9, value=int(m.get("stamps", 0)))
                    e_discounts = st.number_input("Discounts Bank", min_value=0, max_value=2, value=int(m.get("free_cups", 0)))
                    e_receive_ads = st.checkbox("Receive promotional emails & special offer ads", value=bool(m.get("receive_ads", True)))
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        update_btn = st.form_submit_button("💾 Save Changes", use_container_width=True)
                    with c2:
                        delete_click_btn = st.form_submit_button("🗑️ Delete Member", use_container_width=True)
                    
                    if update_btn:
                        try:
                            update_payload = {
                                "name": e_name,
                                "mobile_number": e_mobile,
                                "email": e_email if e_email else None,
                                "stamps": e_stamps,
                                "free_cups": e_discounts,
                                "receive_ads": e_receive_ads,
                                "updated_at": datetime.utcnow().isoformat()
                            }
                            if e_password.strip():
                                update_payload["password_hash"] = hash_password(e_password.strip())
                            
                            supabase.table("loyalty_cards").update(update_payload).eq("mobile_number", m["mobile_number"]).execute()
                            st.success("Profile updated successfully!")
                            st.rerun()
                        except Exception as update_err:
                            st.error(f"Error updating profile: {update_err}")
                    
                    if delete_click_btn:
                        st.session_state.confirm_delete = True
                        st.rerun()

                if st.session_state.confirm_delete:
                    st.warning(f"⚠️ **Confirm Deletion**: Are you sure you want to delete **{customer_name}**?")
                    d_yes, d_no = st.columns(2)
                    with d_yes:
                        if st.button("✅ Yes, Delete Permanently", use_container_width=True):
                            try:
                                supabase.table("loyalty_cards").delete().eq("mobile_number", m["mobile_number"]).execute()
                                st.session_state.do_clear_edit = True
                                st.success("Member deleted.")
                                st.rerun()
                            except Exception as del_err:
                                st.error(f"Error deleting member: {del_err}")
                    with d_no:
                        if st.button("❌ Cancel Deletion", use_container_width=True):
                            st.session_state.confirm_delete = False
                            st.rerun()
            else:
                st.warning("No member found matching that mobile number or email.")
        except Exception as e:
            st.error(f"Database error: {e}")
