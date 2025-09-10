# NFL Analytics Dashboard

A comprehensive NFL analytics dashboard built with Streamlit, Polars, and DuckDB.

## Features

- **QB Statistics**: Analyze quarterback performance across seasons
- **Skill Position Stats**: Compare WR, TE, and RB performance with both rushing and receiving metrics
- **Advanced Analytics**: EPA, success rate, and traditional NFL metrics
- **Interactive Visualizations**: Plotly charts with filtering and comparison tools

## Setup

### 1. Install Dependencies
```bash
uv install
```

### 2. Run the Application
```bash
uv run app
```

## Data Sources

- **nfl_data_py**: Official NFL play-by-play and roster data
- **Coverage**: 1999-2025 seasons
- **Metrics**: EPA, success rate, traditional stats

## Technology Stack

- **Streamlit**: Web application framework
- **Polars**: Fast DataFrame library for data processing
- **DuckDB**: In-memory analytical database
- **Plotly**: Interactive visualizations
- **nfl_data_py**: NFL data access
