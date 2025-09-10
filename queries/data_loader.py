"""
Data loading utilities for NFL analytics
"""
import streamlit as st
import polars as pl
from typing import List


@st.cache_data(show_spinner=True)
def load_pbp_data(years: List[int]) -> pl.DataFrame:
    """
    Load play-by-play data for specified years
    
    Args:
        years: List of years to load
        
    Returns:
        Polars DataFrame with play-by-play data
    """
    import nfl_data_py as nfl
    
    # Load data using nfl_data_py (returns pandas)
    pdf = nfl.import_pbp_data(years)
    
    # Convert to Polars and clean up
    df = pl.from_pandas(pdf)
    
    # Keep common play types and normalize data types
    df = (
        df
        .filter(pl.col("play_type").is_in(["pass", "run"]))
        .with_columns([
            pl.col("week").cast(pl.Int32, strict=False),
            pl.col("season").cast(pl.Int32, strict=False),
            pl.col("success").cast(pl.Boolean, strict=False),
            pl.col("season_type").cast(pl.Utf8, strict=False),
            pl.col("posteam").cast(pl.Utf8, strict=False),
            pl.col("defteam").cast(pl.Utf8, strict=False),
            pl.col("complete_pass").cast(pl.Boolean, strict=False),
            pl.col("pass_touchdown").cast(pl.Boolean, strict=False),
            pl.col("interception").cast(pl.Boolean, strict=False),
        ])
    )
    
    return df


def get_available_teams(df: pl.DataFrame) -> List[str]:
    """
    Get list of available teams from the data
    
    Args:
        df: Play-by-play DataFrame
        
    Returns:
        Sorted list of team abbreviations
    """
    offense_teams = set(df.select(pl.col("posteam")).drop_nulls().to_series().to_list())
    defense_teams = set(df.select(pl.col("defteam")).drop_nulls().to_series().to_list())
    
    return sorted(offense_teams | defense_teams)


def get_available_qbs(df: pl.DataFrame, min_attempts: int = 50) -> List[str]:
    """
    Get list of available QBs from the data
    
    Args:
        df: Play-by-play DataFrame
        min_attempts: Minimum pass attempts to include QB
        
    Returns:
        Sorted list of QB names
    """
    qb_attempts = (
        df
        .filter(
            (pl.col("play_type") == "pass") & 
            (pl.col("passer").is_not_null())
        )
        .group_by("passer")
        .agg(pl.count().alias("attempts"))
        .filter(pl.col("attempts") >= min_attempts)
        .select("passer")
        .to_series()
        .to_list()
    )
    
    return sorted(qb_attempts)
