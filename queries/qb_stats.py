"""
QB Statistics queries for NFL analytics
"""
import polars as pl
import duckdb
from typing import List, Optional


def get_qb_stats_by_year(
    pbp_df: pl.DataFrame,
    seasons: List[int],
    min_attempts: int = 100,
    season_type: str = "REG",
    teams: Optional[List[str]] = None
) -> pl.DataFrame:
    """
    Get QB statistics aggregated by year
    
    Args:
        pbp_df: Play-by-play DataFrame
        seasons: List of seasons to include
        min_attempts: Minimum pass attempts to include QB
        season_type: "REG", "POST", or "both"
        teams: Optional list of teams to filter by
    
    Returns:
        DataFrame with QB stats by year
    """
    con = duckdb.connect()
    con.register("pbp", pbp_df.to_arrow())
    
    # Build WHERE clause
    where_conditions = [
        "play_type = 'pass'",
        "passer IS NOT NULL",
        f"season IN ({','.join(map(str, seasons))})"
    ]
    
    if season_type != "both":
        where_conditions.append(f"season_type = '{season_type}'")
    
    if teams:
        team_list = "'" + "','".join(teams) + "'"
        where_conditions.append(f"posteam IN ({team_list})")
    
    where_sql = " AND ".join(where_conditions)
    
    qb_stats_sql = f"""
    SELECT
        season,
        passer AS qb_name,
        posteam AS team,
        COUNT(*) AS attempts,
        SUM(CASE WHEN complete_pass = 1 THEN 1 ELSE 0 END) AS completions,
        ROUND(SUM(CASE WHEN complete_pass = 1 THEN 1 ELSE 0 END)::DOUBLE / COUNT(*) * 100, 1) AS completion_pct,
        SUM(passing_yards) AS passing_yards,
        ROUND(SUM(passing_yards)::DOUBLE / COUNT(*), 1) AS yards_per_attempt,
        SUM(pass_touchdown) AS passing_tds,
        SUM(interception) AS interceptions,
        ROUND(AVG(epa), 3) AS avg_epa,
        ROUND(SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END)::DOUBLE / COUNT(*) * 100, 1) AS success_rate,
        -- Passer Rating calculation
        ROUND(
            CASE 
                WHEN COUNT(*) > 0 THEN
                    ((LEAST(GREATEST((SUM(CASE WHEN complete_pass = 1 THEN 1 ELSE 0 END)::DOUBLE / COUNT(*) - 0.3) * 5, 0), 2.375) +
                      LEAST(GREATEST((SUM(passing_yards)::DOUBLE / COUNT(*) - 3) * 0.25, 0), 2.375) +
                      LEAST(GREATEST((SUM(pass_touchdown)::DOUBLE / COUNT(*)) * 20, 0), 2.375) +
                      LEAST(GREATEST(2.375 - (SUM(interception)::DOUBLE / COUNT(*)) * 25, 0), 2.375)) / 6) * 100
                ELSE NULL
            END, 1
        ) AS passer_rating
    FROM pbp
    WHERE {where_sql}
    GROUP BY season, passer, posteam
    HAVING COUNT(*) >= {min_attempts}
    ORDER BY season DESC, avg_epa DESC
    """
    
    return con.execute(qb_stats_sql).pl()


def get_qb_seasonal_trends(
    pbp_df: pl.DataFrame,
    qb_name: str,
    seasons: List[int],
    season_type: str = "REG"
) -> pl.DataFrame:
    """
    Get seasonal trends for a specific QB
    
    Args:
        pbp_df: Play-by-play DataFrame
        qb_name: QB name to analyze
        seasons: List of seasons
        season_type: "REG", "POST", or "both"
    
    Returns:
        DataFrame with QB trends over seasons
    """
    con = duckdb.connect()
    con.register("pbp", pbp_df.to_arrow())
    
    where_conditions = [
        "play_type = 'pass'",
        f"passer = '{qb_name}'",
        f"season IN ({','.join(map(str, seasons))})"
    ]
    
    if season_type != "both":
        where_conditions.append(f"season_type = '{season_type}'")
    
    where_sql = " AND ".join(where_conditions)
    
    trends_sql = f"""
    SELECT
        season,
        posteam AS team,
        COUNT(*) AS attempts,
        ROUND(AVG(epa), 3) AS avg_epa,
        ROUND(SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END)::DOUBLE / COUNT(*) * 100, 1) AS success_rate,
        SUM(passing_yards) AS passing_yards,
        SUM(pass_touchdown) AS passing_tds,
        SUM(interception) AS interceptions
    FROM pbp
    WHERE {where_sql}
    GROUP BY season, posteam
    ORDER BY season
    """
    
    return con.execute(trends_sql).pl()


def get_qb_comparisons(
    pbp_df: pl.DataFrame,
    season: int,
    min_attempts: int = 200,
    season_type: str = "REG"
) -> pl.DataFrame:
    """
    Get QB comparisons for a specific season
    
    Args:
        pbp_df: Play-by-play DataFrame
        season: Season to analyze
        min_attempts: Minimum attempts to include
        season_type: "REG", "POST", or "both"
    
    Returns:
        DataFrame with QB comparisons
    """
    con = duckdb.connect()
    con.register("pbp", pbp_df.to_arrow())
    
    where_conditions = [
        "play_type = 'pass'",
        "passer IS NOT NULL",
        f"season = {season}"
    ]
    
    if season_type != "both":
        where_conditions.append(f"season_type = '{season_type}'")
    
    where_sql = " AND ".join(where_conditions)
    
    comparison_sql = f"""
    WITH qb_stats AS (
        SELECT
            passer AS qb_name,
            posteam AS team,
            COUNT(*) AS attempts,
            AVG(epa) AS avg_epa,
            SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END)::DOUBLE / COUNT(*) AS success_rate,
            SUM(passing_yards) AS passing_yards,
            SUM(pass_touchdown) AS passing_tds,
            SUM(interception) AS interceptions
        FROM pbp
        WHERE {where_sql}
        GROUP BY passer, posteam
        HAVING COUNT(*) >= {min_attempts}
    )
    SELECT
        qb_name,
        team,
        attempts,
        passing_yards,
        passing_tds,
        interceptions,
        ROUND(avg_epa, 3) AS avg_epa,
        ROUND(success_rate * 100, 1) AS success_rate,
        ROUND(passing_yards::DOUBLE / attempts, 1) AS yards_per_attempt,
        -- EPA rank
        RANK() OVER (ORDER BY avg_epa DESC) AS epa_rank,
        -- Success rate rank  
        RANK() OVER (ORDER BY success_rate DESC) AS success_rank
    FROM qb_stats
    ORDER BY avg_epa DESC
    """
    
    return con.execute(comparison_sql).pl()
