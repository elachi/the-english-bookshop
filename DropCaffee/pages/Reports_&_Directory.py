import streamlit as st
import pandas as pd
from supabase import create_client
import os
from datetime import datetime

# 1. MUST BE THE FIRST STREAMLIT COMMAND IN YOUR FILE
st.set_page_config(
    page_title="Drop Caffee Loyalty Program - Reports", 
    page_icon="📚", 
    layout="centered"
)

# 2. INJECT CUSTOM CSS TO HIDE MENUS & FOOTER
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
    </style>
""", unsafe_allow_html=True)

if not st.session_state.get("logged_in", False):
    st.warning("Please log in from the main home page first.")
    st.stop()

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

st.image("dropcafe.jpg", width=150)
st.title("Drop Caffee Reports & Analytics")

if not supabase:
    st.error("Database connection missing.")
    st.stop()

# Session state initialization for directory pagination
if "dir_limit" not in st.session_state:
    st.session_state.dir_limit = 20

try:
    res = supabase.table("loyalty_cards").select("*").execute()
    data = res.data

    if data:
        df = pd.DataFrame(data)
        
        # Parse and make timezone-naive to prevent comparison errors
        if "created_at" in df.columns:
            df["created_at_dt"] = pd.to_datetime(df["created_at"], errors='coerce').dt.tz_localize(None)
        if "last_visit" in df.columns:
            df["last_visit_dt"] = pd.to_datetime(df["last_visit"], errors='coerce').dt.tz_localize(None)
        else:
            df["last_visit_dt"] = df["created_at_dt"]

        # Summary Metrics
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Members", len(df))
        col2.metric("Total Stamps Logged", int(df["stamps"].sum()) if "stamps" in df.columns else 0)
        col3.metric("Total Active Discounts", int(df["free_cups"].sum()) if "free_cups" in df.columns else 0)
        
        st.divider()

        # Regular Customers Filter (Members with >= 5 stamps or free cups)
        regulars = df[(df["stamps"] >= 5) | (df["free_cups"] > 0)].copy() if "stamps" in df.columns and "free_cups" in df.columns else df.copy()

        st.subheader("🌟 Regular Customer Leaderboards")
        
        top_limit = st.selectbox("Show Top Leaderboard Size:", [5, 10, 20], index=0, key="leaderboard_limit")

        if not regulars.empty:
            now = pd.Timestamp.now()
            
            # 1. THIS MONTH REGULARS
            st.markdown("### 📅 Top Regulars This Month")
            current_month_start = pd.Timestamp(now.year, now.month, 1)
            df_month = regulars[regulars["last_visit_dt"] >= current_month_start].sort_values(by="stamps", ascending=False)
            
            if not df_month.empty:
                st.dataframe(df_month[["name", "mobile_number", "email", "stamps", "free_cups", "last_visit"]].head(top_limit), use_container_width=True)
            else:
                st.info("No regular customer activity recorded this month yet.")

            # 2. LAST 3 MONTHS REGULARS
            st.markdown("### 🗓️ Top Regulars (Last 3 Months)")
            three_months_ago = current_month_start - pd.DateOffset(months=3)
            df_3months = regulars[regulars["last_visit_dt"] >= three_months_ago].sort_values(by="stamps", ascending=False)
            
            if not df_3months.empty:
                st.dataframe(df_3months[["name", "mobile_number", "email", "stamps", "free_cups", "last_visit"]].head(top_limit), use_container_width=True)
            else:
                st.info("No regular customer activity recorded in the last 3 months.")

            # 3. ALL-TIME REGULARS
            st.markdown("### 🏆 Top Regulars (All-Time)")
            df_alltime = regulars.sort_values(by="stamps", ascending=False)
            st.dataframe(df_alltime[["name", "mobile_number", "email", "stamps", "free_cups", "last_visit"]].head(top_limit), use_container_width=True)
            
        else:
            st.info("No regular customer milestones hit yet.")
            
        st.divider()
        
        # --- FULL MEMBER DIRECTORY ---
        st.subheader("📁 Full Member Directory & Export")
        
        if "created_at_dt" in df.columns:
            df_sorted = df.sort_values(by="created_at_dt", ascending=False)
        else:
            df_sorted = df

        # Restrict visible columns strictly to: Name, Mobile, Email, Registration Date (No sequence number!)
        directory_columns = ["name", "mobile_number", "email", "created_at"]
        available_dir_cols = [col for col in directory_columns if col in df_sorted.columns]
        
        # Slice dataframe based on pagination limit (default 20)
        current_limit = st.session_state.dir_limit
        df_subset = df_sorted.head(current_limit)
        
        st.dataframe(df_subset[available_dir_cols], use_container_width=True)
        
        # Load More Button
        if current_limit < len(df_sorted):
            if st.button("🔽 Load More Members (+20)", use_container_width=True):
                st.session_state.dir_limit += 20
                st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)

        # CSV Export (Exports full data set)
        csv_data = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Export Full Member Directory to CSV",
            data=csv_data,
            file_name=f"bookstore_members_{pd.Timestamp.now().strftime('%Y-%m-%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    else:
        st.info("No member data found.")
except Exception as e:
    st.error(f"Error generating reports: {e}")