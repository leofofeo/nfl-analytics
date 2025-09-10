"""
NFL Analytics - Multi-page Streamlit Application
"""
import streamlit as st

# Page configuration
st.set_page_config(
    page_title="NFL Analytics",
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import pages
from pages.qb_statistics import show_qb_statistics_page
from pages.skill_position_stats import show_skill_position_statistics_page

# Main navigation
def main():
    st.sidebar.title("🏈 NFL Analytics")
    st.sidebar.markdown("---")
    
    # Page selection
    page = st.sidebar.selectbox(
        "Choose a page:",
        [
            "🏈 Home",
            "📊 QB Statistics",
            "🏃‍♂️ Skill Position Stats",
            "📈 Team Analysis (Coming Soon)",
            "🎯 Player Comparison (Coming Soon)"
        ]
    )
    
    # Route to appropriate page
    if page == "🏈 Home":
        show_home_page()
    elif page == "📊 QB Statistics":
        show_qb_statistics_page()
    elif page == "🏃‍♂️ Skill Position Stats":
        show_skill_position_statistics_page()
    elif page == "📈 Team Analysis (Coming Soon)":
        show_coming_soon("Team Analysis")
    elif page == "🎯 Player Comparison (Coming Soon)":
        show_coming_soon("Player Comparison")


def show_home_page():
    """Home page with overview and getting started info"""
    st.title("🏈 NFL Analytics Dashboard")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        #### 📊 QB Statistics
        - Analyze quarterback performance by year
        - Compare QBs across seasons
        - Track individual QB trends
        - EPA and success rate metrics
        """)
    
    with col2:
        st.markdown("""
        #### 🏃‍♂️ Skill Position Stats
        - WR (including TE) and RB performance analysis
        - Rushing and receiving metrics
        - Multi-season comparisons
        - EPA and success rate tracking
        """)
    
    with col3:
        st.markdown("""
        #### 🎯 Player Comparison
        - Multi-player comparisons
        - Position-specific metrics
        - Advanced analytics
        - *Coming Soon*
        """)
    
    st.markdown("---")
    
    # Quick stats or recent data info
    st.markdown("### 📈 Quick Stats")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Data Coverage",
            value="1999-2024",
            help="Years of NFL data available"
        )
    
    with col2:
        st.metric(
            label="Play Types",
            value="Pass & Run",
            help="Types of plays analyzed"
        )
    
    with col3:
        st.metric(
            label="Metrics",
            value="EPA, Success Rate",
            help="Advanced analytics available"
        )
    
    with col4:
        st.metric(
            label="Data Source",
            value="nfl_data_py",
            help="Official NFL data source"
        )
    
    st.markdown("---")
    
    # Getting started
    st.markdown("### 🚀 Getting Started")
    st.markdown("""
    1. **Choose a page** from the sidebar navigation
    2. **Select your filters** (seasons, teams, etc.)
    3. **Explore the data** with interactive tables and charts
    4. **Analyze trends** and compare performance metrics
    """)
    
    # Data information
    with st.expander("ℹ️ About the Data"):
        st.markdown("""
        **Data Source**: This application uses data from `nfl_data_py`, which provides:
        - Play-by-play data from 1999-present
        - Player statistics and team information
        - Advanced metrics like EPA (Expected Points Added) and Success Rate
        
        **Key Metrics Explained**:
        - **EPA (Expected Points Added)**: Measures the value of each play in terms of points
        - **Success Rate**: Percentage of plays that achieve positive EPA
        - **Passer Rating**: Traditional QB efficiency metric
        - **Y/A (Yards per Attempt)**: Average yards gained per pass attempt
        """)


def show_coming_soon(feature_name):
    """Show coming soon page for features under development"""
    st.title(f"🚧 {feature_name}")
    st.markdown("### This feature is coming soon!")
    
    st.info(f"""
    The {feature_name} feature is currently under development. 
    
    In the meantime, check out the **QB Statistics** page for comprehensive quarterback analysis!
    """)
    
    st.markdown("---")
    st.markdown("### 💡 Suggestions?")
    st.markdown("""
    Have ideas for what you'd like to see in this feature? 
    Consider contributing to the project or opening an issue!
    """)


if __name__ == "__main__":
    main()