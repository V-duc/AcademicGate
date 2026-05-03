"""
config.py
=========
Central configuration for AcademicGateDB CSV import.

Edit DB_CONFIG (host / user / password) before running import_data.py.
"""

from pathlib import Path
import os

# ──────────────────────────────────────────────────────────────
# DATABASE CONNECTION
# ──────────────────────────────────────────────────────────────
DB_CONFIG: dict = {
    "host":               "127.0.0.1",
    "port":               3306,
    "user":               "root",
    "password":           os.environ.get("DB_PASSWORD", "Ducvan123@"),   # ← set DB_PASSWORD env var
    "database":           "AcademicGateDB",
    "charset":            "utf8mb4",
    "use_unicode":        True,
    "connection_timeout": 30,
}

# ──────────────────────────────────────────────────────────────
# PATHS
# ──────────────────────────────────────────────────────────────
# Directory that contains this config file (project root)
BASE_DIR: Path = Path(__file__).parent

# Directory containing the raw CSV files
RAW_DATA_DIR: Path = BASE_DIR / "raw data"

# ──────────────────────────────────────────────────────────────
# IMPORT SETTINGS
# ──────────────────────────────────────────────────────────────
# Number of rows per INSERT batch (tune for your server's RAM)
DEFAULT_CHUNK_SIZE: int = 1_000

# ──────────────────────────────────────────────────────────────
# TABLE CONFIGURATION
# ──────────────────────────────────────────────────────────────
# Each entry describes one table to import:
#   group     – dependency group (lower numbers load first)
#   table     – MySQL table name
#   csv_file  – filename inside RAW_DATA_DIR
#   pk        – primary-key column name (used in log messages)
#   auto_pk   – True when the PK is AUTO_INCREMENT (excluded from INSERT)
#   columns   – explicit list of columns to load; None = all CSV headers
#
TABLE_CONFIG: list[dict] = [
    # ── Group 1: no FK dependencies ──────────────────────────
    {
        "group":    1,
        "table":    "Applicants",
        "csv_file": "applicants.csv",
        "pk":       "ApplicantID",
        "auto_pk":  True,
        "columns":  [
            "ApplicantName", "Email", "Age", "Nationality",
            "Gender", "Major", "Wanted_Job",
        ],
    },
    {
        "group":    1,
        "table":    "Continents",
        "csv_file": "tbl_continents_202604131031.csv",
        "pk":       "code",
        "auto_pk":  False,
        "columns":  ["code", "name"],
    },
    {
        "group":    1,
        "table":    "PositionType",
        "csv_file": "tbl_positiontype_202604131031.csv",
        "pk":       "ID_Position",
        "auto_pk":  False,
        "columns":  ["ID_Position", "PositionTitle", "SortNumber"],
    },
    {
        "group":    1,
        "table":    "ResearchArea",
        "csv_file": "tbl_researcharea_202604131031.csv",
        "pk":       "ID_ResearchArea",
        "auto_pk":  False,
        "columns":  ["ID_ResearchArea", "ResearchArea", "Description"],
    },
    # ── Group 2: depends on Group 1 ──────────────────────────
    {
        "group":    2,
        "table":    "Country",
        "csv_file": "tbl_country_202604131031.csv",
        "pk":       "ID_Country",
        "auto_pk":  False,
        "columns":  [
            "code", "ID_Country", "CountryName", "full_name",
            "number", "continent_code", "display_order",
        ],
    },
    # ── Group 3: depends on Group 2 ──────────────────────────
    {
        "group":    3,
        "table":    "University",
        "csv_file": "tbl_university_202604131031.csv",
        "pk":       "ID_University",
        "auto_pk":  False,
        "columns":  [
            "ID_Country", "ID_University", "UniversityName", "ShortName", 
            "@vLink", "@vLogo", "UniversityAddr", "@vLogoPath", 
            "ProcessingDate", "NumberofRecentPositions", "@vState", "Status", "IndexID"
        ],
    },
    # ── Group 4: central fact table ──────────────────────────
    {
        "group":    4,
        "table":    "Positions",
        "csv_file": "tbl_positions.csv",
        "pk":       "ID",
        "auto_pk":  False,
        "columns":  [
            "@vSiteId", "ID", "@vSource", "ID_Country", "ID_University", 
            "ID_Position", "@vLang", "JobTitle", "@vHTML", "NonHTMLAdvertisement", 
            "OriginalLink", "Deadline", "DateofPost", "@vPub", "@vIdx", 
            "IsAlive", "Keywords", "Abstract", "FavoriteCount", "JobStatus", 
            "WorkingTime", "ContractType", "Salary"
        ],
    },
    # ── Group 5: bridge / junction tables – load last ─────────
    {
        "group":    5,
        "table":    "PositionsResearchAreas",
        "csv_file": "tbl_positions_researchareas_202604131031.csv",
        "pk":       "IndexID",
        "auto_pk":  True,   # AUTO_INCREMENT – omit from INSERT
        "columns":  ["ID_ResearchArea", "ID", "DateOfPost", "Weight"],
    },
    {
        "group":    5,
        "table":    "JobPositionType",
        "csv_file": "tbl_job_positiontype_202604131031.csv",
        "pk":       "ID_Index",
        "auto_pk":  True,   # AUTO_INCREMENT – omit from INSERT
        "columns":  ["ID", "ID_PositionType", "Weight"],
    },
    {
        "group":    6,
        "table":    "Applications",
        "csv_file": "applications.csv",
        "pk":       "ApplicationID",
        "auto_pk":  True,
        "columns":  ["JobID", "ApplicantID", "Status"],
    },
]
