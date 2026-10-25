import streamlit as st
import pandas as pd
from supabase import create_client




# 1. MUST BE THE FIRST STREAMLIT COMMAND IN YOUR FILE
st.set_page_config(
    page_title="Cafe Loyalty Program", 
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






if not st.session_state.get("logged_in", False):
    st.warning("Please log in from the main home page first.")
    st.stop()

supabase = create_client(st.secrets["SUPABASE_URL"].strip().rstrip('/'), st.secrets["SUPABASE_KEY"])

st.image("Logo_EnglishBookshop_logo.png", width=150)

st.title("📊 Bookstore Reports & Analytics")

try:
    res = supabase.table("loyalty_cards").select("*").order("created_at", desc=True).execute()
    data = res.data

    if data:
        df = pd.DataFrame(data)
        
        # Summary Metrics
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Members", len(df))
        col2.metric("Total Stamps Logged", int(df["stamps"].sum()))
        col3.metric("Total Active Discounts", int(df["free_cups"].sum()))
        
        st.divider()
        
        # Filter Regulars (Members with 5 or more stamps or redeemed rewards)
        st.subheader("🌟 Regular Customers")
        regulars = df[(df["stamps"] >= 5) | (df["free_cups"] > 0)]
        if not regulars.empty:
            st.dataframe(regulars[["name", "mobile_number", "email", "stamps", "free_cups", "last_visit"]], use_container_width=True)
        else:
            st.info("No regular customer milestones hit yet.")
            
        st.divider()
        
        # Full Directory & Export
        st.subheader("📁 Full Member Directory & Export")
        st.dataframe(df, use_container_width=True)
        
        csv_data = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Export Member Directory to CSV",
            data=csv_data,
            file_name=f"bookstore_members_{pd.Timestamp.now().strftime('%Y-%m-%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    else:
        st.info("No member data found.")
except Exception as e:
    st.error(f"Error generating reports: {e}")


#Testing
