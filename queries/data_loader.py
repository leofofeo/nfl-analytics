"""
Data loading utilities for NFL analytics
"""
import streamlit as st
import pandas as pd
from typing import List


@st.cache_data(show_spinner=True)
def load_pbp_data(years: List[int]) -> pd.DataFrame:
    """
    Load play-by-play data for specified years
    
    Args:
        years: List of years to load
        
    Returns:
        Pandas DataFrame with play-by-play data
    """
    import nfl_data_py as nfl
    
    # Load data using nfl_data_py (returns pandas)
    pdf = nfl.import_pbp_data(years)
    
    # Clean up the pandas DataFrame
    df = pdf.copy()
    
    # Keep common play types and normalize data types
    df = df[df["play_type"].isin(["pass", "run"])].copy()
    
    # Convert data types and handle null values properly
    df["week"] = pd.to_numeric(df["week"], errors="coerce")
    df["season"] = pd.to_numeric(df["season"], errors="coerce")
    df["success"] = df["success"].fillna(False).astype(bool)
    df["season_type"] = df["season_type"].fillna("").astype(str)
    df["posteam"] = df["posteam"].fillna("").astype(str)
    df["defteam"] = df["defteam"].fillna("").astype(str)
    df["complete_pass"] = df["complete_pass"].fillna(False).astype(bool)
    df["pass_touchdown"] = df["pass_touchdown"].fillna(False).astype(bool)
    df["interception"] = df["interception"].fillna(False).astype(bool)
    
    # Ensure key string columns are properly typed for DuckDB
    string_cols = ["passer", "rusher_player_name", "receiver_player_name", "receiver_player_id", "rusher_player_id"]
    for col in string_cols:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str)
    
    return df


def get_available_teams(df: pd.DataFrame) -> List[str]:
    """
    Get list of available teams from the data
    
    Args:
        df: Play-by-play DataFrame
        
    Returns:
        Sorted list of team abbreviations
    """
    offense_teams = set(df["posteam"].dropna().tolist())
    defense_teams = set(df["defteam"].dropna().tolist())
    
    return sorted(offense_teams | defense_teams)


def get_available_qbs(df: pd.DataFrame, min_attempts: int = 50) -> List[str]:
    """
    Get list of available QBs from the data
    
    Args:
        df: Play-by-play DataFrame
        min_attempts: Minimum pass attempts to include QB
        
    Returns:
        Sorted list of QB names
    """
    qb_attempts = (
        df[
            (df["play_type"] == "pass") & 
            (df["passer"].notna())
        ]
        .groupby("passer")
        .size()
        .reset_index(name="attempts")
        .query(f"attempts >= {min_attempts}")
        ["passer"]
        .tolist()
    )
    
    return sorted(qb_attempts)
