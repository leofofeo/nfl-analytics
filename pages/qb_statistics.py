"""
QB Statistics page for NFL analytics
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from queries.qb_stats import get_qb_stats_by_year, get_qb_seasonal_trends, get_qb_comparisons
from queries.data_loader import load_pbp_data, get_available_teams, get_available_qbs


def show_qb_statistics_page():
    """Main QB statistics page"""
    st.title("🏈 QB Statistics by Year")
    st.markdown("Analyze quarterback performance across seasons using EPA, success rate, and traditional metrics.")
    
    # Sidebar filters
    with st.sidebar:
        st.header("📊 Filters")
        
        # Season selection
        default_last = 2025
        seasons = st.multiselect(
            "Seasons",
            options=list(range(1999, default_last + 1)),
            default=list(range(default_last - 3, default_last + 1)),
            help="Select seasons to analyze"
        )
        
        if not seasons:
            st.info("Please select at least one season.")
            st.stop()
        
        # Season type
        season_type = st.selectbox(
            "Season Type", 
            ["REG", "POST", "both"], 
            index=0,
            help="Regular season, playoffs, or both"
        )
        
        # Minimum attempts
        min_attempts = st.slider(
            "Minimum Pass Attempts", 
            50, 500, 200, 25,
            help="Minimum pass attempts to include QB in analysis"
        )
    
    # Load data
    with st.spinner("Loading NFL data..."):
        pbp_data = load_pbp_data(seasons)
    
    # Get available teams for filtering
    available_teams = get_available_teams(pbp_data)
    
    with st.sidebar:
        st.divider()
        team_filter = st.multiselect(
            "Filter by Teams",
            options=available_teams,
            default=[],
            help="Leave empty to include all teams"
        )
    
    # Main content tabs
    tab1, tab2, tab3 = st.tabs(["📈 Season Overview", "🎯 QB Comparison", "📊 Individual Trends"])
    
    with tab1:
        show_season_overview(pbp_data, seasons, min_attempts, season_type, team_filter)
    
    with tab2:
        show_qb_comparison(pbp_data, seasons, min_attempts, season_type, team_filter)
    
    with tab3:
        show_individual_trends(pbp_data, seasons, season_type)


def show_season_overview(pbp_data, seasons, min_attempts, season_type, team_filter):
    """Show QB statistics overview by season"""
    st.subheader("QB Performance by Season")
    
    # Get QB stats
    qb_stats = get_qb_stats_by_year(
        pbp_data, 
        seasons, 
        min_attempts, 
        season_type,
        team_filter if team_filter else None
    )
    
    if len(qb_stats) == 0:
        st.warning("No data found with current filters.")
        return
    
    # Display data table
    st.dataframe(
        qb_stats,
        use_container_width=True,
        column_config={
            "season": "Season",
            "qb_name": "QB Name",
            "team": "Team",
            "attempts": st.column_config.NumberColumn("Attempts", format="%d"),
            "completions": st.column_config.NumberColumn("Completions", format="%d"),
            "completion_pct": st.column_config.NumberColumn("Comp %", format="%.1f%%"),
            "passing_yards": st.column_config.NumberColumn("Pass Yards", format="%d"),
            "yards_per_attempt": st.column_config.NumberColumn("Y/A", format="%.1f"),
            "passing_tds": st.column_config.NumberColumn("Pass TDs", format="%d"),
            "interceptions": st.column_config.NumberColumn("INTs", format="%d"),
            "avg_epa": st.column_config.NumberColumn("EPA/Play", format="%.3f"),
            "success_rate": st.column_config.NumberColumn("Success %", format="%.1f%%"),
            "passer_rating": st.column_config.NumberColumn("Passer Rating", format="%.1f"),
        }
    )
    
    # Visualizations
    col1, col2 = st.columns(2)
    
    with col1:
        # EPA vs Success Rate scatter
        if len(seasons) == 1:
            season = seasons[0]
            season_data = qb_stats[qb_stats["season"] == season]
            
            fig = px.scatter(
                season_data,
                x="success_rate",
                y="avg_epa",
                hover_data=["qb_name", "team", "attempts"],
                title=f"EPA vs Success Rate - {season}",
                labels={"success_rate": "Success Rate (%)", "avg_epa": "EPA per Play"}
            )
            fig.update_traces(textposition="top center")
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Top QBs by EPA
        if len(qb_stats) > 0:
            top_qbs = qb_stats.head(15)
            
            fig = px.bar(
                top_qbs,
                x="avg_epa",
                y="qb_name",
                color="season",
                title="Top 15 QBs by EPA per Play",
                labels={"avg_epa": "EPA per Play", "qb_name": "Quarterback"},
                orientation="h"
            )
            fig.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig, use_container_width=True)


def show_qb_comparison(pbp_data, seasons, min_attempts, season_type, team_filter):
    """Show QB comparison for a specific season"""
    st.subheader("QB Comparison")
    
    # Season selector for comparison
    comparison_season = st.selectbox(
        "Select season for comparison",
        options=sorted(seasons, reverse=True),
        key="comparison_season"
    )
    
    # Get comparison data
    comparison_data = get_qb_comparisons(
        pbp_data,
        comparison_season,
        min_attempts,
        season_type
    )
    
    if len(comparison_data) == 0:
        st.warning(f"No data found for {comparison_season} with current filters.")
        return
    
    # Display comparison table
    st.dataframe(
        comparison_data,
        use_container_width=True,
        column_config={
            "qb_name": "QB Name",
            "team": "Team", 
            "attempts": st.column_config.NumberColumn("Attempts", format="%d"),
            "passing_yards": st.column_config.NumberColumn("Pass Yards", format="%d"),
            "passing_tds": st.column_config.NumberColumn("Pass TDs", format="%d"),
            "interceptions": st.column_config.NumberColumn("INTs", format="%d"),
            "avg_epa": st.column_config.NumberColumn("EPA/Play", format="%.3f"),
            "success_rate": st.column_config.NumberColumn("Success %", format="%.1f%%"),
            "yards_per_attempt": st.column_config.NumberColumn("Y/A", format="%.1f"),
            "epa_rank": st.column_config.NumberColumn("EPA Rank", format="%d"),
            "success_rank": st.column_config.NumberColumn("Success Rank", format="%d"),
        }
    )
    
    # Radar chart for top QBs
    st.subheader("Top QB Performance Radar")
    
    top_qbs_for_radar = comparison_data.head(6)
    
    if len(top_qbs_for_radar) > 0:
        # Create radar chart
        fig = go.Figure()
        
        for _, row in top_qbs_for_radar.iterrows():
            fig.add_trace(go.Scatterpolar(
                r=[
                    row['avg_epa'] * 10,  # Scale EPA for visibility
                    row['success_rate'],
                    row['yards_per_attempt'] * 5,  # Scale Y/A
                    min(row['passing_tds'] / 10, 10),  # Scale TDs, cap at 10
                    max(10 - row['interceptions'] / 5, 0)  # Inverse INTs (fewer is better)
                ],
                theta=['EPA×10', 'Success %', 'Y/A×5', 'TDs/10', 'Low INTs'],
                fill='toself',
                name=f"{row['qb_name']} ({row['team']})"
            ))
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 10]
                )
            ),
            showlegend=True,
            title=f"Top QBs Performance Comparison - {comparison_season}"
        )
        
        st.plotly_chart(fig, use_container_width=True)


def show_individual_trends(pbp_data, seasons, season_type):
    """Show individual QB trends over time"""
    st.subheader("Individual QB Trends")
    
    # Get available QBs
    available_qbs = get_available_qbs(pbp_data, min_attempts=100)
    
    selected_qb = st.selectbox(
        "Select QB to analyze",
        options=available_qbs,
        key="individual_qb"
    )
    
    if selected_qb:
        # Get trends data
        trends_data = get_qb_seasonal_trends(
            pbp_data,
            selected_qb,
            seasons,
            season_type
        )
        
        if len(trends_data) == 0:
            st.warning(f"No data found for {selected_qb} in selected seasons.")
            return
        
        # Display trends table
        st.dataframe(
            trends_data,
            use_container_width=True,
            column_config={
                "season": "Season",
                "team": "Team",
                "attempts": st.column_config.NumberColumn("Attempts", format="%d"),
                "avg_epa": st.column_config.NumberColumn("EPA/Play", format="%.3f"),
                "success_rate": st.column_config.NumberColumn("Success %", format="%.1f%%"),
                "passing_yards": st.column_config.NumberColumn("Pass Yards", format="%d"),
                "passing_tds": st.column_config.NumberColumn("Pass TDs", format="%d"),
                "interceptions": st.column_config.NumberColumn("INTs", format="%d"),
            }
        )
        
        # Trends visualization
        if len(trends_data) > 1:
            col1, col2 = st.columns(2)
            
            with col1:
                # EPA trend
                fig = px.line(
                    trends_data,
                    x="season",
                    y="avg_epa",
                    title=f"{selected_qb} - EPA per Play Trend",
                    markers=True
                )
                fig.update_layout(xaxis_title="Season", yaxis_title="EPA per Play")
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Success rate trend
                fig = px.line(
                    trends_data,
                    x="season",
                    y="success_rate",
                    title=f"{selected_qb} - Success Rate Trend",
                    markers=True
                )
                fig.update_layout(xaxis_title="Season", yaxis_title="Success Rate (%)")
                st.plotly_chart(fig, use_container_width=True)


if __name__ == "__main__":
    show_qb_statistics_page()
