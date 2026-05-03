import mysql.connector
import os
import time
from config import DB_CONFIG

# Merge allow_local_infile into config
db_config = {**DB_CONFIG, "allow_local_infile": True}

# Number of tables to import (in FK dependency order)
files_to_import = [
    ("Continents", "raw data/tbl_continents_202604131031.csv", "(code, name)"),
    ("Country", "raw data/tbl_country_202604131031.csv", "(code, ID_Country, CountryName, full_name, number, continent_code, display_order)"),
    ("PositionType", "raw data/tbl_positiontype_202604131031.csv", "(ID_Position, PositionTitle, SortNumber)"),
    ("ResearchArea", "raw data/tbl_researcharea_202604131031.csv", "(ID_ResearchArea, ResearchArea, Description)"),
    ("University", "raw data/tbl_university_202604131031.csv", "(ID_Country, ID_University, UniversityName, ShortName, @vLink, @vLogo, UniversityAddr, @vLogoPath, ProcessingDate, NumberofRecentPositions, @vState, Status, IndexID)"),
    ("Positions", "raw data/tbl_positions.csv", "(@vSiteId, ID, @vSource, ID_Country, ID_University, ID_Position, @vLang, JobTitle, @vHTML, NonHTMLAdvertisement, OriginalLink, Deadline, DateofPost, @vPub, @vIdx, IsAlive, Keywords, Abstract, FavoriteCount, JobStatus, WorkingTime, ContractType, Salary, @vPList, @vPListText, @vRAList, @vRAListText, @vPList2, @vRPList, @vRPText, @vRRAList, @vRRAText)"),
    ("JobPositionType", "raw data/tbl_job_positiontype_202604131031.csv", "(ID, ID_PositionType, Weight, @dummy)"),
    ("PositionsResearchAreas", "raw data/tbl_positions_researchareas_202604131031.csv", "(ID_ResearchArea, ID, @dummy, DateOfPost, Weight)"),
    ("Applicants", "raw data/applicants.csv", "(ApplicantName, Email, Age, Nationality, Gender, Major, Wanted_Job)"),
    ("Applications", "raw data/applications.csv", "(JobID, ApplicantID, Status)")
]

def detect_line_ending(filepath):
    """Phát hiện ký tự xuống dòng của file: \\r\\n (Windows) hoặc \\n (Unix)."""
    with open(filepath, 'rb') as f:
        chunk = f.read(8192)
        if b'\r\n' in chunk:
            return '\\r\\n'
        return '\\n'

def run_import():
    try:
        print("Connecting to MySQL...")
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        print("Connected. Starting data import...")
        cursor.execute("SET GLOBAL local_infile = 1;")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")

        base_path = os.path.dirname(os.path.abspath(__file__))

        for table, rel_path, columns in files_to_import:
            abs_path = os.path.join(base_path, rel_path).replace("\\", "/")
            print(f"Loading table {table}...", end=" ", flush=True)
            
            # Auto-detect line ending for each file
            line_term = detect_line_ending(abs_path)
            
            start_time = time.time()
            cursor.execute(f"TRUNCATE TABLE {table};")
            sql = f"""
                LOAD DATA LOCAL INFILE '{abs_path}'
                INTO TABLE {table}
                FIELDS TERMINATED BY ',' ENCLOSED BY '\"'
                LINES TERMINATED BY '{line_term}'
                IGNORE 1 ROWS
                {columns}
            """
            cursor.execute(sql)
            conn.commit()
            
            duration = time.time() - start_time
            print(f"Done! ({duration:.2f}s)")

        cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
        cursor.execute("CALL sp_refresh_university_counts();")
        print("\nALL DATA IMPORTED SUCCESSFULLY!")
        
        # Print statistics
        print("\n--- STATISTICS ---")
        for table, _, _ in files_to_import:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"{table:25}: {count} rows")

    except Exception as e:
        print(f"\nERROR: {e}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    run_import()
