"""
Skill Position Statistics page for NFL analytics
Covers Wide Receivers, Tight Ends, and Running Backs
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from queries.skill_position_stats import (
    get_skill_position_stats_by_year, 
    get_skill_position_comparisons, 
    get_skill_position_trends,
    get_available_skill_players
)
from queries.data_loader import load_pbp_data, get_available_teams


def show_skill_position_statistics_page():
    """Main skill position statistics page"""
    st.title("🏃‍♂️ Skill Position Statistics")
    st.markdown("Analyze Wide Receivers (including Tight Ends) and Running Backs performance with both rushing and receiving metrics.")
    
    # Sidebar filters
    with st.sidebar:
        st.header("📊 Filters")
        
        # Position group selection
        position_groups = st.multiselect(
            "Position Groups",
            options=["WR", "RB"],
            default=["WR", "RB"],
            help="Select position groups to analyze (TEs are included with WRs)"
        )
        
        if not position_groups:
            st.info("Please select at least one position group.")
            st.stop()
        
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
        
        # Minimum touches
        min_touches = st.slider(
            "Minimum Total Touches", 
            25, 200, 75, 25,
            help="Minimum touches (rushes + targets) to include player"
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
    tab1, tab2, tab3 = st.tabs(["📈 Season Overview", "🎯 Player Comparison", "📊 Individual Trends"])
    
    with tab1:
        show_season_overview(pbp_data, seasons, position_groups, min_touches, season_type, team_filter)
    
    with tab2:
        show_player_comparison(pbp_data, seasons, position_groups, min_touches, season_type)
    
    with tab3:
        show_individual_trends(pbp_data, seasons, position_groups, season_type)


def show_season_overview(pbp_data, seasons, position_groups, min_touches, season_type, team_filter):
    """Show skill position statistics overview by season"""
    st.subheader("Skill Position Performance by Season")
    
    # Get skill position stats
    skill_stats = get_skill_position_stats_by_year(
        pbp_data, 
        seasons, 
        position_groups,
        min_touches, 
        season_type,
        team_filter if team_filter else None
    )
    
    if len(skill_stats) == 0:
        st.warning("No data found with current filters.")
        return
    
    # Display data table with enhanced formatting
    st.dataframe(
        skill_stats,
        use_container_width=True,
        column_config={
            "season": "Season",
            "player_name": "Player",
            "team": "Team",
            "position_group": st.column_config.SelectboxColumn(
                "Position",
                options=["WR", "TE", "RB"]
            ),
            "targets": st.column_config.NumberColumn("Targets", format="%d"),
            "receptions": st.column_config.NumberColumn("Receptions", format="%d"),
            "catch_rate": st.column_config.NumberColumn("Catch %", format="%.1f%%"),
            "receiving_yards": st.column_config.NumberColumn("Rec Yards", format="%d"),
            "yards_per_reception": st.column_config.NumberColumn("Y/R", format="%.1f"),
            "yards_per_target": st.column_config.NumberColumn("Y/T", format="%.1f"),
            "receiving_tds": st.column_config.NumberColumn("Rec TDs", format="%d"),
            "rushes": st.column_config.NumberColumn("Rushes", format="%d"),
            "rushing_yards": st.column_config.NumberColumn("Rush Yards", format="%d"),
            "yards_per_carry": st.column_config.NumberColumn("Y/C", format="%.1f"),
            "rushing_tds": st.column_config.NumberColumn("Rush TDs", format="%d"),
            "total_touches": st.column_config.NumberColumn("Total Touches", format="%d"),
            "total_yards": st.column_config.NumberColumn("Total Yards", format="%d"),
            "total_tds": st.column_config.NumberColumn("Total TDs", format="%d"),
            "avg_epa": st.column_config.NumberColumn("EPA/Play", format="%.3f"),
            "success_rate": st.column_config.NumberColumn("Success %", format="%.1f%%"),
        }
    )
    
    # Visualizations
    col1, col2 = st.columns(2)
    
    with col1:
        # EPA vs Success Rate scatter by position
        if len(seasons) == 1:
            season = seasons[0]
            season_data = skill_stats[skill_stats["season"] == season]
            
            # Ensure size column is numeric
            season_pandas = season_data.copy()
            season_pandas["total_touches"] = season_pandas["total_touches"].astype(float)
            
            fig = px.scatter(
                season_pandas,
                x="success_rate",
                y="avg_epa",
                color="position_group",
                size="total_touches",
                hover_data=["player_name", "team", "total_yards"],
                title=f"EPA vs Success Rate by Position - {season}",
                labels={"success_rate": "Success Rate (%)", "avg_epa": "EPA per Play"}
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Top players by EPA
        if len(skill_stats) > 0:
            top_players = skill_stats.head(15)
            
            fig = px.bar(
                top_players,
                x="avg_epa",
                y="player_name",
                color="position_group",
                title="Top 15 Players by EPA per Play",
                labels={"avg_epa": "EPA per Play", "player_name": "Player"},
                orientation="h"
            )
            fig.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig, use_container_width=True)
    
    # Position group breakdown
    st.subheader("Position Group Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Position group performance comparison
        if len(skill_stats) > 0:
            # Create comparison chart across position groups
            position_summary = (
                skill_stats
                .groupby(["position_group", "season"])
                .agg({
                    "avg_epa": "mean",
                    "success_rate": "mean",
                    "total_yards": "mean"
                })
                .rename(columns={"success_rate": "avg_success_rate", "total_yards": "avg_total_yards"})
                .reset_index()
                .sort_values(["season", "position_group"])
            )
            
            if len(position_summary) > 0:
                fig = px.line(
                    position_summary,
                    x="season",
                    y="avg_epa",
                    color="position_group",
                    title="Average EPA by Position Group Over Time",
                    labels={"avg_epa": "Average EPA", "season": "Season", "position_group": "Position"},
                    markers=True
                )
                st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Touch distribution
        if len(skill_stats) > 0:
            # Calculate touch distribution by position
            touch_summary = (
                skill_stats
                .groupby("position_group")
                .agg({
                    "targets": "mean",
                    "rushes": "mean"
                })
                .rename(columns={"targets": "avg_targets", "rushes": "avg_rushes"})
                .reset_index()
            )
            
            fig = go.Figure()
            
            for _, row in touch_summary.iterrows():
                fig.add_trace(go.Bar(
                    name=row["position_group"],
                    x=["Targets", "Rushes"],
                    y=[row["avg_targets"], row["avg_rushes"]]
                ))
            
            fig.update_layout(
                title="Average Touches by Position Group",
                xaxis_title="Touch Type",
                yaxis_title="Average Touches",
                barmode="group"
            )
            
            st.plotly_chart(fig, use_container_width=True)


def show_player_comparison(pbp_data, seasons, position_groups, min_touches, season_type):
    """Show player comparison for a specific season"""
    st.subheader("Player Comparison")
    
    # Season selector for comparison
    comparison_season = st.selectbox(
        "Select season for comparison",
        options=sorted(seasons, reverse=True),
        key="skill_comparison_season"
    )
    
    # Get comparison data
    comparison_data = get_skill_position_comparisons(
        pbp_data,
        comparison_season,
        position_groups,
        min_touches,
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
            "player_name": "Player",
            "team": "Team",
            "position_group": "Position",
            "total_touches": st.column_config.NumberColumn("Total Touches", format="%d"),
            "targets": st.column_config.NumberColumn("Targets", format="%d"),
            "receptions": st.column_config.NumberColumn("Receptions", format="%d"),
            "receiving_yards": st.column_config.NumberColumn("Rec Yards", format="%d"),
            "receiving_tds": st.column_config.NumberColumn("Rec TDs", format="%d"),
            "rushes": st.column_config.NumberColumn("Rushes", format="%d"),
            "rushing_yards": st.column_config.NumberColumn("Rush Yards", format="%d"),
            "rushing_tds": st.column_config.NumberColumn("Rush TDs", format="%d"),
            "total_yards": st.column_config.NumberColumn("Total Yards", format="%d"),
            "total_tds": st.column_config.NumberColumn("Total TDs", format="%d"),
            "avg_epa": st.column_config.NumberColumn("EPA/Play", format="%.3f"),
            "success_rate": st.column_config.NumberColumn("Success %", format="%.1f%%"),
            "epa_rank": st.column_config.NumberColumn("EPA Rank", format="%d"),
            "success_rank": st.column_config.NumberColumn("Success Rank", format="%d"),
            "yards_rank": st.column_config.NumberColumn("Yards Rank", format="%d"),
        }
    )
    
    # Multi-metric comparison visualization
    st.subheader("Top Player Performance Comparison")
    
    # Position filter for radar chart
    position_for_radar = st.selectbox(
        "Select position group for detailed comparison",
        options=position_groups,
        key="radar_position"
    )
    
    position_data = comparison_data[comparison_data["position_group"] == position_for_radar].head(8)
    
    if len(position_data) > 0:
        col1, col2 = st.columns(2)
        
        with col1:
            # Yards breakdown
            fig = go.Figure()
            
            for _, row in position_data.head(6).iterrows():
                fig.add_trace(go.Bar(
                    name=row["player_name"],
                    x=["Receiving", "Rushing"],
                    y=[row["receiving_yards"], row["rushing_yards"]]
                ))
            
            fig.update_layout(
                title=f"Yards Breakdown - Top {position_for_radar} Players",
                xaxis_title="Yard Type",
                yaxis_title="Yards",
                barmode="group"
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # EPA vs Total Yards scatter
            # Ensure size column is numeric
            position_pandas = position_data.copy()
            position_pandas["total_touches"] = position_pandas["total_touches"].astype(float)
            
            fig = px.scatter(
                position_pandas,
                x="total_yards",
                y="avg_epa",
                size="total_touches",
                hover_data=["player_name", "team"],
                title=f"EPA vs Total Yards - {position_for_radar}",
                labels={"total_yards": "Total Yards", "avg_epa": "EPA per Play"}
            )
            
            # Add player name annotations
            for _, row in position_data.iterrows():
                fig.add_annotation(
                    x=row["total_yards"],
                    y=row["avg_epa"],
                    text=row["player_name"].split()[-1],  # Last name only
                    showarrow=False,
                    yshift=10
                )
            
            st.plotly_chart(fig, use_container_width=True)


def show_individual_trends(pbp_data, seasons, position_groups, season_type):
    """Show individual player trends over time"""
    st.subheader("Individual Player Trends")
    
    # Get available players
    available_players_df = get_available_skill_players(pbp_data, min_touches=50)
    
    # Filter by selected position groups
    if position_groups:
        # Convert position groups to match available data
        filter_positions = []
        if "WR" in position_groups:
            filter_positions.append("WR")  # WR includes TEs since they're classified together
        if "RB" in position_groups:
            filter_positions.append("RB")
        
        if filter_positions:
            available_players_df = available_players_df[
                available_players_df["primary_position"].isin(filter_positions)
            ]
    
    available_players = available_players_df["player_name"].tolist()
    
    selected_player = st.selectbox(
        "Select player to analyze",
        options=available_players,
        key="individual_skill_player"
    )
    
    if selected_player:
        # Show player info
        player_info = available_players_df[available_players_df["player_name"] == selected_player].iloc[0]
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Primary Position", player_info["primary_position"])
        with col2:
            st.metric("Total Receiving", f"{player_info['total_receiving']:,}")
        with col3:
            st.metric("Total Rushing", f"{player_info['total_rushing']:,}")
        with col4:
            st.metric("Total Touches", f"{player_info['total_touches']:,}")
        
        # Get trends data
        trends_data = get_skill_position_trends(
            pbp_data,
            selected_player,
            seasons,
            season_type
        )
        
        if len(trends_data) == 0:
            st.warning(f"No data found for {selected_player} in selected seasons.")
            return
        
        # Display trends table
        st.dataframe(
            trends_data,
            use_container_width=True,
            column_config={
                "season": "Season",
                "team": "Team",
                "targets": st.column_config.NumberColumn("Targets", format="%d"),
                "receiving_yards": st.column_config.NumberColumn("Rec Yards", format="%d"),
                "receiving_tds": st.column_config.NumberColumn("Rec TDs", format="%d"),
                "rushes": st.column_config.NumberColumn("Rushes", format="%d"),
                "rushing_yards": st.column_config.NumberColumn("Rush Yards", format="%d"),
                "rushing_tds": st.column_config.NumberColumn("Rush TDs", format="%d"),
                "total_touches": st.column_config.NumberColumn("Total Touches", format="%d"),
                "total_yards": st.column_config.NumberColumn("Total Yards", format="%d"),
                "total_tds": st.column_config.NumberColumn("Total TDs", format="%d"),
                "avg_epa": st.column_config.NumberColumn("EPA/Play", format="%.3f"),
                "success_rate": st.column_config.NumberColumn("Success %", format="%.1f%%"),
            }
        )
        
        # Trends visualization
        if len(trends_data) > 1:
            col1, col2 = st.columns(2)
            
            with col1:
                # Yards trends
                fig = go.Figure()
                
                fig.add_trace(go.Scatter(
                    x=trends_data["season"].tolist(),
                    y=trends_data["receiving_yards"].tolist(),
                    mode='lines+markers',
                    name='Receiving Yards',
                    line=dict(color='blue')
                ))
                
                fig.add_trace(go.Scatter(
                    x=trends_data["season"].tolist(),
                    y=trends_data["rushing_yards"].tolist(),
                    mode='lines+markers',
                    name='Rushing Yards',
                    line=dict(color='red')
                ))
                
                fig.update_layout(
                    title=f"{selected_player} - Yards Trend",
                    xaxis_title="Season",
                    yaxis_title="Yards"
                )
                
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # EPA and Success Rate trends
                fig = make_subplots(
                    rows=1, cols=1,
                    specs=[[{"secondary_y": True}]]
                )
                
                fig.add_trace(
                    go.Scatter(
                        x=trends_data["season"].tolist(),
                        y=trends_data["avg_epa"].tolist(),
                        mode='lines+markers',
                        name='EPA per Play',
                        line=dict(color='green')
                    ),
                    secondary_y=False
                )
                
                fig.add_trace(
                    go.Scatter(
                        x=trends_data["season"].tolist(),
                        y=trends_data["success_rate"].tolist(),
                        mode='lines+markers',
                        name='Success Rate (%)',
                        line=dict(color='orange')
                    ),
                    secondary_y=True
                )
                
                fig.update_layout(title=f"{selected_player} - EPA & Success Rate Trend")
                fig.update_xaxes(title_text="Season")
                fig.update_yaxes(title_text="EPA per Play", secondary_y=False)
                fig.update_yaxes(title_text="Success Rate (%)", secondary_y=True)
                
                st.plotly_chart(fig, use_container_width=True)


if __name__ == "__main__":
    show_skill_position_statistics_page()
