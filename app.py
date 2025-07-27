import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import datetime as dt

# --- Streamlit Page Configuration ---
st.set_page_config(
    page_title="Social Media Engagement Dashboard",
    page_icon="📊",
    layout="wide", # Use 'wide' layout for better visual arrangement
    initial_sidebar_state="expanded"
)

# --- Helper Functions (for caching data loading and processing) ---
@st.cache_data
def load_data(uploaded_file):
    """Loads CSV data from uploaded file and performs initial processing."""
    try:
        df = pd.read_csv(uploaded_file)

        # Standardize column names: lowercase, replace spaces/dots with underscore
        df.columns = [col.strip().replace(' ', '_').replace('.', '').lower() for col in df.columns]

        # --- IMPORTANT CHANGE HERE: Checking for 'post_id' instead of 'postid' ---
        # Ensure 'post_id' exists and is string type
        if 'post_id' not in df.columns:
            st.error("Error: The column 'Post_ID' (or 'Post ID') was not found in your CSV. Please ensure your CSV has a column named 'Post_ID' or 'Post ID'.")
            return pd.DataFrame()
        df['post_id'] = df['post_id'].astype(str) # Using 'post_id'

        # Convert 'date' column to datetime objects (assuming 'post_date' from your file)
        if 'post_date' in df.columns: # Using 'post_date' as per your CSV
            df['post_date'] = pd.to_datetime(df['post_date'], errors='coerce')
            df = df.dropna(subset=['post_date']) # Remove rows where date conversion failed
            # Create Day of Week columns for analysis
            df['day_of_week'] = df['post_date'].dt.day_name()
            df['day_of_week_num'] = df['post_date'].dt.dayofweek # Monday=0, Sunday=6
            # Ensure day of week is sorted correctly for visuals
            day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            df['day_of_week'] = pd.Categorical(df['day_of_week'], categories=day_order, ordered=True)
        else:
            st.warning("Warning: 'Post_Date' column not found. Date-based analysis will be skipped.")
            df['post_date'] = pd.NaT # Set to Not a Time to prevent errors if used
            df['day_of_week'] = None
            df['day_of_week_num'] = None

        # Ensure engagement metrics are numeric and fill NaNs with 0
        # Your CSV has 'likes', 'shares', 'comments' (all lowercase already)
        engagement_cols = ['likes', 'shares', 'comments']
        for col in engagement_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
            else:
                st.warning(f"Warning: '{col.capitalize()}' column not found. Setting to 0 for calculations.")
                df[col] = 0

        # Calculate Total Engagement Per Post as a new column
        df['total_engagement_per_post'] = df['likes'] + df['shares'] + df['comments']

        # Ensure 'content_type' column exists (renamed from 'Type' in previous versions to match your CSV)
        if 'content_type' not in df.columns: # Using 'content_type' as per your CSV
            st.warning("Warning: 'Content_Type' column not found. Post type distribution will be skipped.")
            df['content_type'] = 'Unknown' # Default value if missing

        return df
    except Exception as e:
        st.error(f"Error loading or processing data. Please check your CSV format: {e}")
        return pd.DataFrame() # Return empty DataFrame on error

# --- Main Dashboard Logic ---
st.title("📊 Social Media Post Engagement Dashboard")

# --- Sidebar for File Upload and Filters ---
with st.sidebar:
    st.header("1. Upload Your Data")
    uploaded_file = st.file_uploader("Choose a CSV file", type="csv", key="file_uploader")
    st.markdown("---")

    # Load data only if a file is uploaded
    df = pd.DataFrame() # Initialize df as empty DataFrame
    if uploaded_file is not None:
        df = load_data(uploaded_file)

    # Filter section appears only if data is loaded successfully
    st.header("2. Filter Data")

    # Post Type Filter (using 'content_type' from your CSV)
    selected_post_types = ['All']
    if 'content_type' in df.columns and not df.empty:
        unique_types = df['content_type'].unique().tolist()
        selected_post_types = st.multiselect(
            "Filter by Content Type(s)",
            options=['All'] + unique_types,
            default=['All']
        )

    # Date Range Filter (only if 'post_date' column exists and is valid)
    date_filter_enabled = False
    min_date_data = None
    max_date_data = None
    if 'post_date' in df.columns and not df['post_date'].empty and df['post_date'].dtype == 'datetime64[ns]':
        date_filter_enabled = st.checkbox("Enable Date Filter")
        if date_filter_enabled:
            min_date_data = df['post_date'].min().date()
            max_date_data = df['post_date'].max().date()

            # Check if min_date_data and max_date_data are valid dates
            if pd.isna(min_date_data) or pd.isna(max_date_data):
                st.warning("Invalid dates found in 'Post_Date' column. Date filter disabled.")
                date_filter_enabled = False
            else:
                date_range_selection = st.slider(
                    "Select Date Range",
                    min_value=min_date_data,
                    max_value=max_date_data,
                    value=(min_date_data, max_date_data),
                    format="YYYY-MM-DD"
                )

    # Apply Filters to the DataFrame
    df_filtered = df.copy()

    if 'content_type' in df_filtered.columns and 'All' not in selected_post_types:
        df_filtered = df_filtered[df_filtered['content_type'].isin(selected_post_types)]

    if date_filter_enabled and min_date_data is not None: # Only apply if enabled and valid dates exist
        df_filtered = df_filtered[
            (df_filtered['post_date'].dt.date >= date_range_selection[0]) &
            (df_filtered['post_date'].dt.date <= date_range_selection[1])
        ]

    st.markdown("---")

# --- Dashboard Content ---
if df.empty:
    st.info("Upload your social media post data CSV from the sidebar to begin the analysis. Ensure it contains 'Post_ID', 'Post_Date', 'Likes', 'Shares', 'Comments', and 'Content_Type' columns.")
else:
    if df_filtered.empty:
        st.warning("No data available for the selected filters. Please adjust your filters.")
    else:
        st.write(f"Displaying analysis for **{len(df_filtered)}** posts.")

        # --- Row 1: KPIs ---
        st.header("Key Performance Indicators (KPIs)")
        col1, col2, col3, col4, col5 = st.columns(5)

        total_posts = len(df_filtered)
        total_likes = df_filtered['likes'].sum()
        total_shares = df_filtered['shares'].sum()
        total_comments = df_filtered['comments'].sum()

        # Calculate average post engagement (handle division by zero)
        avg_post_engagement = df_filtered['total_engagement_per_post'].mean() if total_posts > 0 else 0

        with col1:
            st.metric("Total Posts", total_posts)
        with col2:
            st.metric("Total Likes", f"{total_likes:,.0f}")
        with col3:
            st.metric("Total Shares", f"{total_shares:,.0f}")
        with col4:
            st.metric("Total Comments", f"{total_comments:,.0f}")
        with col5:
            st.metric("Avg. Post Engagement", f"{avg_post_engagement:,.2f}")
        st.markdown("---")

        # --- Row 2: Basic Charts (Bar & Pie) ---
        col_chart1, col_chart2 = st.columns(2)

        with col_chart1:
            st.subheader("Engagement (Likes, Shares, Comments) per Post")
            # --- IMPORTANT CHANGE HERE: Using 'post_id' ---
            if 'post_id' in df_filtered.columns and all(col in df_filtered.columns for col in ['likes', 'shares', 'comments']):
                # Limit to top N posts by total engagement for readability on charts
                df_top_posts_for_chart = df_filtered.nlargest(20, 'total_engagement_per_post') # Show top 20 posts
                df_melted = df_top_posts_for_chart.melt(
                    id_vars=['post_id'], # Using 'post_id'
                    value_vars=['likes', 'shares', 'comments'],
                    var_name='Engagement Type',
                    value_name='Count'
                )
                fig_bar, ax_bar = plt.subplots(figsize=(10, 6))
                sns.barplot(data=df_melted, x='post_id', y='Count', hue='Engagement Type', ax=ax_bar) # Using 'post_id'
                ax_bar.set_title('Top 20 Posts: Likes, Shares, and Comments')
                ax_bar.set_xlabel('Post ID')
                ax_bar.set_ylabel('Count')
                ax_bar.tick_params(axis='x', rotation=45)
                ax_bar.legend(title='Metric')
                st.pyplot(fig_bar)
            else:
                st.info("Required columns ('post_id', 'likes', 'shares', 'comments') missing or empty for this chart.") # Using 'post_id'

        with col_chart2:
            st.subheader("Post Type Distribution")
            # --- IMPORTANT CHANGE HERE: Using 'content_type' ---
            if 'content_type' in df_filtered.columns and not df_filtered['content_type'].empty:
                post_type_counts = df_filtered['content_type'].value_counts() # Using 'content_type'
                fig_pie, ax_pie = plt.subplots(figsize=(8, 8))
                ax_pie.pie(post_type_counts, labels=post_type_counts.index, autopct='%1.1f%%', startangle=90, colors=sns.color_palette('pastel'))
                ax_pie.set_title('Content Type Distribution') # Changed title to match 'Content_Type'
                ax_pie.axis('equal') # Equal aspect ratio ensures that pie is drawn as a circle.
                st.pyplot(fig_pie)
            else:
                st.info("Required column ('content_type') missing or empty for this chart.") # Using 'content_type'
        st.markdown("---")

        # --- Row 3: Advanced Charts (Trends & Day of Week) ---
        st.header("Engagement Trends & Patterns")
        col_trend1, col_trend2 = st.columns(2)

        with col_trend1:
            st.subheader("Engagement Over Time")
            # --- IMPORTANT CHANGE HERE: Using 'post_date' ---
            if 'post_date' in df_filtered.columns and 'total_engagement_per_post' in df_filtered.columns and not df_filtered['post_date'].empty:
                df_daily_engagement = df_filtered.groupby(df_filtered['post_date'].dt.date)['total_engagement_per_post'].sum().reset_index() # Using 'post_date'
                fig_line, ax_line = plt.subplots(figsize=(10, 6))
                sns.lineplot(data=df_daily_engagement, x='post_date', y='total_engagement_per_post', marker='o', ax=ax_line) # Using 'post_date'
                ax_line.set_title('Total Engagement Over Time')
                ax_line.set_xlabel('Date')
                ax_line.set_ylabel('Total Engagement')
                ax_line.tick_params(axis='x', rotation=45)
                st.pyplot(fig_line)
            else:
                st.info("Required columns ('post_date', 'total_engagement_per_post') missing or empty for this chart.") # Using 'post_date'

        with col_trend2:
            st.subheader("Engagement by Day of the Week")
            if 'day_of_week' in df_filtered.columns and 'total_engagement_per_post' in df_filtered.columns and not df_filtered['day_of_week'].empty:
                engagement_by_day = df_filtered.groupby('day_of_week')['total_engagement_per_post'].sum().reset_index()
                fig_dow, ax_dow = plt.subplots(figsize=(10, 6))
                sns.barplot(data=engagement_by_day, x='day_of_week', y='total_engagement_per_post', palette='coolwarm', ax=ax_dow)
                ax_dow.set_title('Total Engagement by Day of the Week')
                ax_dow.set_xlabel('Day of Week')
                ax_dow.set_ylabel('Total Engagement')
                ax_dow.tick_params(axis='x', rotation=45)
                st.pyplot(fig_dow)
            else:
                st.info("Required columns ('day_of_week', 'total_engagement_per_post') missing or empty for this chart.")
        st.markdown("---")

        # --- Row 4: More Visuals (Type Breakdown & Scatter) ---
        col_more1, col_more2 = st.columns(2)

        with col_more1:
            st.subheader("Engagement Breakdown by Content Type") # Changed title
            # --- IMPORTANT CHANGE HERE: Using 'content_type' ---
            if 'content_type' in df_filtered.columns and all(col in df_filtered.columns for col in ['likes', 'shares', 'comments']) and not df_filtered['content_type'].empty:
                df_type_engagement = df_filtered.groupby('content_type')[['likes', 'shares', 'comments']].sum().reset_index() # Using 'content_type'
                df_type_melted = df_type_engagement.melt(
                    id_vars=['content_type'], # Using 'content_type'
                    value_vars=['likes', 'shares', 'comments'],
                    var_name='Engagement Metric',
                    value_name='Total Count'
                )
                fig_type_bar, ax_type_bar = plt.subplots(figsize=(10, 6))
                sns.barplot(data=df_type_melted, x='content_type', y='Total Count', hue='Engagement Metric', palette='viridis', ax=ax_type_bar) # Using 'content_type'
                ax_type_bar.set_title('Engagement Breakdown by Content Type') # Changed title
                ax_type_bar.set_xlabel('Content Type') # Changed label
                ax_type_bar.set_ylabel('Total Count')
                ax_type_bar.tick_params(axis='x', rotation=45)
                ax_type_bar.legend(title='Metric')
                st.pyplot(fig_type_bar)
            else:
                st.info("Required columns ('content_type', 'likes', 'shares', 'comments') missing or empty for this chart.") # Using 'content_type'

        with col_more2:
            st.subheader("Likes vs. Comments")
            # --- IMPORTANT CHANGE HERE: Using 'content_type' for hue ---
            if 'likes' in df_filtered.columns and 'comments' in df_filtered.columns and not df_filtered['likes'].empty:
                fig_scatter, ax_scatter = plt.subplots(figsize=(10, 6))
                sns.scatterplot(data=df_filtered, x='likes', y='comments', hue='content_type', size='total_engagement_per_post', sizes=(20, 400), ax=ax_scatter) # Using 'content_type' for hue
                ax_scatter.set_title('Likes vs. Comments per Post')
                ax_scatter.set_xlabel('Likes')
                ax_scatter.set_ylabel('Comments')
                ax_scatter.legend(title='Content Type') # Changed title
                st.pyplot(fig_scatter)
            else:
                st.info("Required columns ('likes', 'comments') missing or empty for this chart.")
        st.markdown("---")

        # --- Top Post Details ---
        st.header("Top Performing Post Details")
        # --- IMPORTANT CHANGE HERE: Using 'post_id' ---
        if 'post_id' in df_filtered.columns and 'total_engagement_per_post' in df_filtered.columns and not df_filtered.empty:
            # Find the post with the highest total engagement
            top_post = df_filtered.loc[df_filtered['total_engagement_per_post'].idxmax()]

            st.markdown(f"""
            <div style="background-color:#e6f7ff; padding: 15px; border-radius: 10px; border-left: 5px solid #007bff;">
                <h3>🥇 Post ID: <span style="color:#007bff;">{top_post['post_id']}</span></h3>
                <p><strong>Content Type:</strong> {top_post.get('content_type', 'N/A')}</p>
                <p><strong>Likes:</strong> {top_post.get('likes', 0):,.0f}</p>
                <p><strong>Shares:</strong> {top_post.get('shares', 0):,.0f}</p>
                <p><strong>Comments:</strong> {top_post.get('comments', 0):,.0f}</p>
                <p><strong>Total Engagement:</strong> <span style="font-size: 1.2em; font-weight: bold; color:#28a745;">{top_post['total_engagement_per_post']:,.0f}</span></p>
                <p><strong>Date:</strong> {top_post['post_date'].strftime('%Y-%m-%d') if pd.notna(top_post.get('post_date')) else 'N/A'}</p>
            </div>
            """, unsafe_allow_html=True)
        elif not df_filtered.empty: # Data exists but required columns are missing
            st.info("Required columns ('post_id', 'total_engagement_per_post') missing or empty to identify the top post.") # Using 'post_id'
        else: # No data at all after filtering
            st.info("No data available to determine the top post.")

        st.markdown("---")

        # --- Raw Data Display ---
        st.header("Raw Data Preview")
        st.dataframe(df_filtered)

# Instructions for initial load
