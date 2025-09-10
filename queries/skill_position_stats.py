"""
Skill Position Player Statistics queries for NFL analytics
Covers Wide Receivers, Tight Ends, and Running Backs
"""
import pandas as pd
import duckdb
import streamlit as st
from typing import List, Optional


@st.cache_data(show_spinner=True)
def load_roster_data(years: List[int]) -> pd.DataFrame:
    """
    Load roster data to get player positions
    
    Args:
        years: List of years to load
        
    Returns:
        Pandas DataFrame with player roster information
    """
    import nfl_data_py as nfl
    
    # Load roster data
    roster_dfs = []
    for year in years:
        try:
            roster_pdf = nfl.import_seasonal_rosters([year])
            roster_dfs.append(roster_pdf)
        except Exception:
            # If roster data is not available for a year, skip it
            continue
    
    if not roster_dfs:
        # Return empty DataFrame with expected columns if no data
        return pd.DataFrame({
            "player_name": pd.Series([], dtype=str),
            "player_id": pd.Series([], dtype=str),
            "position": pd.Series([], dtype=str),
            "season": pd.Series([], dtype=int)
        })
    
    # Combine all roster data
    roster_df = pd.concat(roster_dfs, ignore_index=True)
    
    # Clean and standardize position data - no need to rename, columns already correct
    # Handle null values and ensure proper string type for position
    roster_df["position"] = roster_df["position"].fillna("UNK").astype(str)
    roster_df["season"] = pd.to_numeric(roster_df["season"], errors="coerce").astype(int)
    roster_df["player_name"] = roster_df["player_name"].fillna("").astype(str)
    roster_df["player_id"] = roster_df["player_id"].fillna("").astype(str)
    
    return roster_df[["player_name", "player_id", "position", "season"]]


def get_skill_position_stats_by_year(
    pbp_df: pd.DataFrame,
    seasons: List[int],
    positions: List[str],
    min_touches: int = 50,
    season_type: str = "REG",
    teams: Optional[List[str]] = None
) -> pd.DataFrame:
    """
    Get skill position player statistics aggregated by year
    
    Args:
        pbp_df: Play-by-play DataFrame
        seasons: List of seasons to include
        positions: List of positions ("WR", "TE", "RB")
        min_touches: Minimum touches (rushes + targets) to include player
        season_type: "REG", "POST", or "both"
        teams: Optional list of teams to filter by
    
    Returns:
        DataFrame with skill position stats by year
    """
    # Load roster data to get player positions
    roster_df = load_roster_data(seasons)
    
    # Data types are already handled in load_roster_data function
    
    con = duckdb.connect()
    con.register("pbp", pbp_df)
    con.register("roster", roster_df)
    
    # Build WHERE clause
    where_conditions = [
        f"p.season IN ({','.join(map(str, seasons))})"
    ]
    
    if season_type != "both":
        where_conditions.append(f"p.season_type = '{season_type}'")
    
    if teams:
        team_list = "'" + "','".join(teams) + "'"
        where_conditions.append(f"p.posteam IN ({team_list})")
    
    where_sql = " AND ".join(where_conditions)
    
    # Create position filter based on selection
    if not positions:
        return pd.DataFrame()
    
    # Automatically include TE when WR is selected since TEs are classified with WRs
    expanded_positions = positions.copy()
    if 'WR' in positions and 'TE' not in positions:
        expanded_positions.append('TE')
    
    # Convert positions to SQL IN clause
    position_list = "'" + "','".join(expanded_positions) + "'"
    
    skill_stats_sql = f"""
    WITH player_stats AS (
        -- Receiving stats with position from roster
        SELECT
            p.season,
            p.receiver_player_name AS player_name,
            p.receiver_player_id AS player_id,
            p.posteam AS team,
            COALESCE(r.position, 'WR') AS position_group,
            COUNT(*) AS targets,
            SUM(CASE WHEN p.complete_pass = 1 THEN 1 ELSE 0 END) AS receptions,
            SUM(p.receiving_yards) AS receiving_yards,
            SUM(p.pass_touchdown) AS receiving_tds,
            0 AS rushes,
            0 AS rushing_yards,
            0 AS rushing_tds,
            AVG(p.epa) AS avg_epa,
            SUM(CASE WHEN p.success = 1 THEN 1 ELSE 0 END)::DOUBLE / COUNT(*) AS success_rate
        FROM pbp p
        LEFT JOIN roster r ON (
            p.receiver_player_name = r.player_name 
            AND p.season = r.season
        )
        WHERE {where_sql}
            AND p.play_type = 'pass'
            AND p.receiver_player_name IS NOT NULL
            AND (r.position IN ({position_list}) OR (r.position IS NULL AND ('WR' IN ({position_list}) OR 'TE' IN ({position_list}))))
        GROUP BY p.season, p.receiver_player_name, p.receiver_player_id, p.posteam, r.position
        
        UNION ALL
        
        -- Rushing stats with position from roster
        SELECT
            p.season,
            p.rusher_player_name AS player_name,
            p.rusher_player_id AS player_id,
            p.posteam AS team,
            COALESCE(r.position, 'RB') AS position_group,
            0 AS targets,
            0 AS receptions,
            0 AS receiving_yards,
            0 AS receiving_tds,
            COUNT(*) AS rushes,
            SUM(p.rushing_yards) AS rushing_yards,
            SUM(p.rush_touchdown) AS rushing_tds,
            AVG(p.epa) AS avg_epa,
            SUM(CASE WHEN p.success = 1 THEN 1 ELSE 0 END)::DOUBLE / COUNT(*) AS success_rate
        FROM pbp p
        LEFT JOIN roster r ON (
            p.rusher_player_name = r.player_name 
            AND p.season = r.season
        )
        WHERE {where_sql}
            AND p.play_type = 'run'
            AND p.rusher_player_name IS NOT NULL
            AND (r.position IN ({position_list}) OR (r.position IS NULL AND 'RB' IN ({position_list})))
        GROUP BY p.season, p.rusher_player_name, p.rusher_player_id, p.posteam, r.position
    ),
    
    combined_stats AS (
        SELECT
            season,
            player_name,
            player_id,
            team,
            position_group,
            SUM(targets) AS targets,
            SUM(receptions) AS receptions,
            SUM(receiving_yards) AS receiving_yards,
            SUM(receiving_tds) AS receiving_tds,
            SUM(rushes) AS rushes,
            SUM(rushing_yards) AS rushing_yards,
            SUM(rushing_tds) AS rushing_tds,
            -- Weighted average EPA by total plays
            SUM(avg_epa * (targets + rushes)) / NULLIF(SUM(targets + rushes), 0) AS avg_epa,
            -- Weighted average success rate
            SUM(success_rate * (targets + rushes)) / NULLIF(SUM(targets + rushes), 0) AS success_rate
        FROM player_stats
        GROUP BY season, player_name, player_id, team, position_group
    )
    
    SELECT
        season,
        player_name,
        team,
        position_group,
        targets,
        receptions,
        CASE WHEN targets > 0 THEN ROUND(receptions::DOUBLE / targets * 100, 1) ELSE 0 END AS catch_rate,
        receiving_yards,
        CASE WHEN receptions > 0 THEN ROUND(receiving_yards::DOUBLE / receptions, 1) ELSE 0 END AS yards_per_reception,
        CASE WHEN targets > 0 THEN ROUND(receiving_yards::DOUBLE / targets, 1) ELSE 0 END AS yards_per_target,
        receiving_tds,
        rushes,
        rushing_yards,
        CASE WHEN rushes > 0 THEN ROUND(rushing_yards::DOUBLE / rushes, 1) ELSE 0 END AS yards_per_carry,
        rushing_tds,
        (targets + rushes) AS total_touches,
        (receiving_yards + rushing_yards) AS total_yards,
        (receiving_tds + rushing_tds) AS total_tds,
        ROUND(avg_epa, 3) AS avg_epa,
        ROUND(success_rate * 100, 1) AS success_rate
    FROM combined_stats
    WHERE (targets + rushes) >= {min_touches}
        AND position_group IN ({position_list})
    ORDER BY season DESC, avg_epa DESC
    """
    
    return con.execute(skill_stats_sql).df()


def get_skill_position_comparisons(
    pbp_df: pd.DataFrame,
    season: int,
    positions: List[str],
    min_touches: int = 75,
    season_type: str = "REG"
) -> pd.DataFrame:
    """
    Get skill position player comparisons for a specific season
    
    Args:
        pbp_df: Play-by-play DataFrame
        season: Season to analyze
        positions: List of positions ("WR", "TE", "RB")
        min_touches: Minimum touches to include
        season_type: "REG", "POST", or "both"
    
    Returns:
        DataFrame with skill position comparisons
    """
    # Load roster data
    roster_df = load_roster_data([season])
    
    con = duckdb.connect()
    con.register("pbp", pbp_df)
    con.register("roster", roster_df)
    
    where_conditions = [f"p.season = {season}"]
    
    if season_type != "both":
        where_conditions.append(f"p.season_type = '{season_type}'")
    
    where_sql = " AND ".join(where_conditions)
    
    if not positions:
        return pd.DataFrame()
    
    # Automatically include TE when WR is selected since TEs are classified with WRs
    expanded_positions = positions.copy()
    if 'WR' in positions and 'TE' not in positions:
        expanded_positions.append('TE')
    
    position_list = "'" + "','".join(expanded_positions) + "'"
    
    comparison_sql = f"""
    WITH player_stats AS (
        -- Receiving stats with position
        SELECT
            p.receiver_player_name AS player_name,
            p.receiver_player_id AS player_id,
            p.posteam AS team,
            COALESCE(r.position, 'WR') AS position_group,
            COUNT(*) AS targets,
            SUM(CASE WHEN p.complete_pass = 1 THEN 1 ELSE 0 END) AS receptions,
            SUM(p.receiving_yards) AS receiving_yards,
            SUM(p.pass_touchdown) AS receiving_tds,
            0 AS rushes,
            0 AS rushing_yards,
            0 AS rushing_tds,
            AVG(p.epa) AS avg_epa,
            SUM(CASE WHEN p.success = 1 THEN 1 ELSE 0 END)::DOUBLE / COUNT(*) AS success_rate
        FROM pbp p
        LEFT JOIN roster r ON (
            p.receiver_player_name = r.player_name 
            AND p.season = r.season
        )
        WHERE {where_sql}
            AND p.play_type = 'pass'
            AND p.receiver_player_name IS NOT NULL
            AND (r.position IN ({position_list}) OR (r.position IS NULL AND ('WR' IN ({position_list}) OR 'TE' IN ({position_list}))))
        GROUP BY p.receiver_player_name, p.receiver_player_id, p.posteam, r.position
        
        UNION ALL
        
        -- Rushing stats with position
        SELECT
            p.rusher_player_name AS player_name,
            p.rusher_player_id AS player_id,
            p.posteam AS team,
            COALESCE(r.position, 'RB') AS position_group,
            0 AS targets,
            0 AS receptions,
            0 AS receiving_yards,
            0 AS receiving_tds,
            COUNT(*) AS rushes,
            SUM(p.rushing_yards) AS rushing_yards,
            SUM(p.rush_touchdown) AS rushing_tds,
            AVG(p.epa) AS avg_epa,
            SUM(CASE WHEN p.success = 1 THEN 1 ELSE 0 END)::DOUBLE / COUNT(*) AS success_rate
        FROM pbp p
        LEFT JOIN roster r ON (
            p.rusher_player_name = r.player_name 
            AND p.season = r.season
        )
        WHERE {where_sql}
            AND p.play_type = 'run'
            AND p.rusher_player_name IS NOT NULL
            AND (r.position IN ({position_list}) OR (r.position IS NULL AND 'RB' IN ({position_list})))
        GROUP BY p.rusher_player_name, p.rusher_player_id, p.posteam, r.position
    ),
    
    combined_stats AS (
        SELECT
            player_name,
            player_id,
            team,
            position_group,
            SUM(targets) AS targets,
            SUM(receptions) AS receptions,
            SUM(receiving_yards) AS receiving_yards,
            SUM(receiving_tds) AS receiving_tds,
            SUM(rushes) AS rushes,
            SUM(rushing_yards) AS rushing_yards,
            SUM(rushing_tds) AS rushing_tds,
            SUM(avg_epa * (targets + rushes)) / NULLIF(SUM(targets + rushes), 0) AS avg_epa,
            SUM(success_rate * (targets + rushes)) / NULLIF(SUM(targets + rushes), 0) AS success_rate
        FROM player_stats
        GROUP BY player_name, player_id, team, position_group
    )
    
    SELECT
        player_name,
        team,
        position_group,
        (targets + rushes) AS total_touches,
        targets,
        receptions,
        receiving_yards,
        receiving_tds,
        rushes,
        rushing_yards,
        rushing_tds,
        (receiving_yards + rushing_yards) AS total_yards,
        (receiving_tds + rushing_tds) AS total_tds,
        ROUND(avg_epa, 3) AS avg_epa,
        ROUND(success_rate * 100, 1) AS success_rate,
        RANK() OVER (ORDER BY avg_epa DESC) AS epa_rank,
        RANK() OVER (ORDER BY success_rate DESC) AS success_rank,
        RANK() OVER (ORDER BY (receiving_yards + rushing_yards) DESC) AS yards_rank
    FROM combined_stats
    WHERE (targets + rushes) >= {min_touches}
        AND position_group IN ({position_list})
    ORDER BY avg_epa DESC
    """
    
    return con.execute(comparison_sql).df()


def get_skill_position_trends(
    pbp_df: pd.DataFrame,
    player_name: str,
    seasons: List[int],
    season_type: str = "REG"
) -> pd.DataFrame:
    """
    Get seasonal trends for a specific skill position player
    
    Args:
        pbp_df: Play-by-play DataFrame
        player_name: Player name to analyze
        seasons: List of seasons
        season_type: "REG", "POST", or "both"
    
    Returns:
        DataFrame with player trends over seasons
    """
    con = duckdb.connect()
    con.register("pbp", pbp_df)
    
    where_conditions = [
        f"season IN ({','.join(map(str, seasons))})"
    ]
    
    if season_type != "both":
        where_conditions.append(f"season_type = '{season_type}'")
    
    where_sql = " AND ".join(where_conditions)
    
    trends_sql = f"""
    WITH player_stats AS (
        -- Receiving stats
        SELECT
            season,
            posteam AS team,
            'receiving' AS play_type,
            COUNT(*) AS plays,
            SUM(receiving_yards) AS yards,
            SUM(pass_touchdown) AS touchdowns,
            AVG(epa) AS avg_epa,
            SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END)::DOUBLE / COUNT(*) AS success_rate
        FROM pbp
        WHERE {where_sql}
            AND play_type = 'pass'
            AND receiver_player_name = '{player_name}'
        GROUP BY season, posteam
        
        UNION ALL
        
        -- Rushing stats
        SELECT
            season,
            posteam AS team,
            'rushing' AS play_type,
            COUNT(*) AS plays,
            SUM(rushing_yards) AS yards,
            SUM(rush_touchdown) AS touchdowns,
            AVG(epa) AS avg_epa,
            SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END)::DOUBLE / COUNT(*) AS success_rate
        FROM pbp
        WHERE {where_sql}
            AND play_type = 'run'
            AND rusher_player_name = '{player_name}'
        GROUP BY season, posteam
    )
    
    SELECT
        season,
        team,
        SUM(CASE WHEN play_type = 'receiving' THEN plays ELSE 0 END) AS targets,
        SUM(CASE WHEN play_type = 'receiving' THEN yards ELSE 0 END) AS receiving_yards,
        SUM(CASE WHEN play_type = 'receiving' THEN touchdowns ELSE 0 END) AS receiving_tds,
        SUM(CASE WHEN play_type = 'rushing' THEN plays ELSE 0 END) AS rushes,
        SUM(CASE WHEN play_type = 'rushing' THEN yards ELSE 0 END) AS rushing_yards,
        SUM(CASE WHEN play_type = 'rushing' THEN touchdowns ELSE 0 END) AS rushing_tds,
        SUM(plays) AS total_touches,
        SUM(yards) AS total_yards,
        SUM(touchdowns) AS total_tds,
        SUM(avg_epa * plays) / NULLIF(SUM(plays), 0) AS avg_epa,
        SUM(success_rate * plays) / NULLIF(SUM(plays), 0) AS success_rate
    FROM player_stats
    GROUP BY season, team
    ORDER BY season
    """
    
    return con.execute(trends_sql).df()


def get_available_skill_players(
    pbp_df: pd.DataFrame, 
    min_touches: int = 25
) -> pd.DataFrame:
    """
    Get list of available skill position players from the data
    
    Args:
        pbp_df: Play-by-play DataFrame
        min_touches: Minimum touches to include player
        
    Returns:
        DataFrame with player names and their primary position
    """
    con = duckdb.connect()
    con.register("pbp", pbp_df)
    
    players_sql = f"""
    WITH receiving_stats AS (
        SELECT
            receiver_player_name AS player_name,
            COUNT(*) AS receiving_touches,
            0 AS rushing_touches
        FROM pbp
        WHERE play_type = 'pass'
            AND receiver_player_name IS NOT NULL
        GROUP BY receiver_player_name
    ),
    
    rushing_stats AS (
        SELECT
            rusher_player_name AS player_name,
            0 AS receiving_touches,
            COUNT(*) AS rushing_touches
        FROM pbp
        WHERE play_type = 'run'
            AND rusher_player_name IS NOT NULL
        GROUP BY rusher_player_name
    ),
    
    all_players AS (
        SELECT * FROM receiving_stats
        UNION ALL
        SELECT * FROM rushing_stats
    )
    
    SELECT
        player_name,
        SUM(receiving_touches) AS total_receiving,
        SUM(rushing_touches) AS total_rushing,
        SUM(receiving_touches + rushing_touches) AS total_touches,
        CASE 
            WHEN SUM(receiving_touches) > SUM(rushing_touches) THEN 'WR'
            ELSE 'RB'
        END AS primary_position
    FROM all_players
    GROUP BY player_name
    HAVING SUM(receiving_touches + rushing_touches) >= {min_touches}
    ORDER BY total_touches DESC
    """
    
    return con.execute(players_sql).df()
