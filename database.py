"""
web/database.py
Centralized Database Access Layer
"""

import uuid
from config import DB_CONFIG
from mysql.connector import MySQLConnection
import mysql.connector
from typing import Generator
from contextlib import contextmanager
import re
"""
app/db.py
=========
Database connection context manager for AcademicGateDB.

Usage
-----
    from app.db import get_connection

    with get_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT ...")
        rows = cursor.fetchall()
        cursor.close()
"""





@contextmanager
def get_connection() -> Generator[MySQLConnection, None, None]:
    """
    Yield an open MySQL connection and guarantee it is closed on exit.

    Automatically rolls back any uncommitted transaction if an exception
    is raised inside the ``with`` block before propagating the exception.

    Examples
    --------
    >>> with get_connection() as conn:
    ...     cur = conn.cursor(dictionary=True)
    ...     cur.execute("SELECT 1")
    ...     cur.fetchone()
    ...     cur.close()
    """
    conn: MySQLConnection = mysql.connector.connect(**DB_CONFIG)
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def execute_query(sql: str, params: tuple | list | None = None) -> list[dict]:
    """
    Run a SELECT query and return all rows as a list of dicts.

    Parameters
    ----------
    sql : str
        SQL query with %s placeholders.
    params : tuple or list, optional
        Bind parameters.

    Returns
    -------
    list[dict]
        Each dict maps column name → value.
    """
    with get_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(sql, params or ())
            return cursor.fetchall()
        finally:
            cursor.close()


def execute_one(sql: str, params: tuple | list | None = None) -> dict | None:
    """Run a SELECT query and return the first row as a dict, or None."""
    rows = execute_query(sql, params)
    return rows[0] if rows else None


def execute_write(
    sql: str,
    params: tuple | list | None = None,
    *,
    conn: MySQLConnection | None = None,
) -> int:
    """
    Run an INSERT / UPDATE / DELETE statement.

    If *conn* is provided the caller is responsible for committing.
    Otherwise the function opens its own connection and auto-commits.

    Returns
    -------
    int
        ``lastrowid`` for INSERT, ``rowcount`` for UPDATE/DELETE.
    """
    def _run(c: MySQLConnection) -> int:
        cursor = c.cursor()
        try:
            cursor.execute(sql, params or ())
            return cursor.lastrowid or cursor.rowcount
        finally:
            cursor.close()

    if conn is not None:
        return _run(conn)

    with get_connection() as c:
        result = _run(c)
        c.commit()
        return result


def callproc(proc_name: str, args: tuple | list = ()) -> list[dict]:
    """
    Call a stored procedure and return all result rows as dicts.

    Parameters
    ----------
    proc_name : str
        Name of the stored procedure.
    args : tuple or list
        Input arguments.

    Returns
    -------
    list[dict]
        Combined rows from all result sets.
    """
    rows: list[dict] = []
    with get_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.callproc(proc_name, args)
            for result in cursor.stored_results():
                rows.extend(result.fetchall())
            conn.commit()
        finally:
            cursor.close()
    return rows


"""
app/managers/employer_manager.py
=================================
CRUD operations for University (Employer) records.
"""



# ── READ ──────────────────────────────────────────────────────────────────────

def list_employers(
    search: str | None = None,
    country_id: str | None = None,
    status: int | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """Liệt kê các trường đại học sử dụng Stored Procedure."""
    rows = callproc("sp_list_employers", (search, country_id, status, page, page_size))
    # Tổng số bản ghi (tạm tính để hiển thị phân trang)
    total = execute_one("SELECT COUNT(*) AS total FROM University")["total"]
    return {"data": rows, "total": total, "page": page, "page_size": page_size,
            "total_pages": max(1, (total + page_size - 1) // page_size)}


def get_employer(univ_id: str) -> dict | None:
    return execute_one(
        """
        SELECT  u.*,
                c.CountryName, c.code AS CountryCode,
                cont.name AS ContinentName
        FROM    University u
        LEFT JOIN Country    c    ON u.ID_Country       = c.ID_Country
        LEFT JOIN Continents cont ON c.continent_code   = cont.code
        WHERE   u.ID_University = %s
        """,
        (univ_id,),
    )


def get_employer_jobs(univ_id: str, limit: int = 10) -> list[dict]:
    return execute_query(
        """
        SELECT  ID, JobTitle, Deadline, IsAlive, JobStatus,
                DateofPost, FavoriteCount
        FROM    Positions
        WHERE   ID_University = %s
        ORDER BY DateofPost DESC
        LIMIT %s
        """,
        (univ_id, limit),
    )


def get_countries() -> list[dict]:
    return execute_query(
        "SELECT ID_Country, CountryName FROM Country ORDER BY CountryName"
    )


# ── CREATE ────────────────────────────────────────────────────────────────────

def add_employer(data: dict) -> str:
    """Thêm trường học mới qua Procedure."""
    callproc("sp_upsert_university", (
        data["ID_University"], data["UniversityName"], data.get("ShortName"),
        data.get("UniversityAddr"), data["ID_Country"], data.get("Website"),
        data.get("ContactEmail"), data.get("Status", 1)
    ))
    return data["ID_University"]


def update_employer(univ_id: str, data: dict) -> int:
    """Cập nhật trường học qua Procedure."""
    callproc("sp_upsert_university", (
        univ_id, data.get("UniversityName"), data.get("ShortName"),
        data.get("UniversityAddr"), data.get("ID_Country"), data.get("Website"),
        data.get("ContactEmail"), data.get("Status")
    ))
    return 1


def set_employer_status(univ_id: str, status: int) -> int:
    return execute_write(
        "UPDATE University SET Status = %s WHERE ID_University = %s",
        (status, univ_id),
    )


"""
app/managers/job_manager.py
============================
CRUD operations for Positions (Job Postings).
Delegates creation/closing to the existing stored procedures.
"""




# ── READ ──────────────────────────────────────────────────────────────────────

def list_jobs(
    search: str | None = None,
    country_id: str | None = None,
    univ_id: str | None = None,
    position_type: str | None = None,
    is_alive: int | None = 1,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    conditions, params = [], []

    if search:
        conditions.append("(p.JobTitle LIKE %s OR p.Keywords LIKE %s OR p.Abstract LIKE %s)")
        params += [f"%{search}%", f"%{search}%", f"%{search}%"]
    if country_id:
        conditions.append("p.ID_Country = %s")
        params.append(country_id)
    if univ_id:
        conditions.append("p.ID_University = %s")
        params.append(univ_id)
    if position_type:
        conditions.append("p.ID_Position = %s")
        params.append(position_type)
    if is_alive is not None:
        conditions.append("p.IsAlive = %s")
        params.append(is_alive)

    where  = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    offset = (page - 1) * page_size

    total_row = execute_one(
        f"SELECT COUNT(*) AS total FROM Positions p {where}", params
    )
    total = total_row["total"] if total_row else 0

    rows = execute_query(
        f"""
        SELECT  p.ID, p.JobTitle, p.Deadline, p.DateofPost, p.IsAlive,
                p.JobStatus, p.WorkingTime, p.ContractType, p.Salary,
                p.FavoriteCount, p.Source,
                u.UniversityName, u.ShortName,
                c.CountryName,
                pt.PositionTitle
        FROM    Positions p
        LEFT JOIN University  u  ON p.ID_University = u.ID_University
        LEFT JOIN Country     c  ON p.ID_Country    = c.ID_Country
        LEFT JOIN PositionType pt ON p.ID_Position  = pt.ID_Position
        {where}
        ORDER BY p.DateofPost DESC
        LIMIT %s OFFSET %s
        """,
        params + [page_size, offset],
    )
    return {"data": rows, "total": total, "page": page, "page_size": page_size,
            "total_pages": max(1, (total + page_size - 1) // page_size)}


def get_job(job_id: str) -> dict | None:
    return execute_one(
        """
        SELECT  p.*,
                u.UniversityName, u.ShortName, u.Website AS UniversityWebsite,
                c.CountryName,
                pt.PositionTitle
        FROM    Positions p
        LEFT JOIN University   u  ON p.ID_University = u.ID_University
        LEFT JOIN Country      c  ON p.ID_Country    = c.ID_Country
        LEFT JOIN PositionType pt ON p.ID_Position   = pt.ID_Position
        WHERE   p.ID = %s
        """,
        (job_id,),
    )


def get_job_research_areas(job_id: str) -> list[dict]:
    return execute_query(
        """
        SELECT  ra.ResearchArea, pra.Weight
        FROM    PositionsResearchAreas pra
        JOIN    ResearchArea ra ON pra.ID_ResearchArea = ra.ID_ResearchArea
        WHERE   pra.ID = %s
        ORDER BY pra.Weight DESC
        """,
        (job_id,),
    )


def get_position_types() -> list[dict]:
    return execute_query(
        "SELECT ID_Position, PositionTitle FROM PositionType ORDER BY SortNumber"
    )


def search_jobs_proc(keyword: str, country_id: str | None = None,
                     position_type: str | None = None,
                     page_size: int = 20, offset: int = 0) -> list[dict]:
    """Call sp_search_jobs stored procedure."""
    return callproc("sp_search_jobs",
                    (keyword or "", country_id or "", position_type or "",
                     page_size, offset))


# ── CREATE ────────────────────────────────────────────────────────────────────

def post_job(data: dict) -> str:
    """
    Create a new job posting via sp_post_job stored procedure.

    Parameters (data keys)
    ----------------------
    ID_University, ID_Position, ID_Country, JobTitle,
    NonHTMLAdvertisement, OriginalLink, Deadline,
    WorkingTime, ContractType, Salary  (all optional except first 4)

    Returns
    -------
    str  — new UUID for the posting
    """
    job_id = str(uuid.uuid4())
    callproc("sp_post_job", (
        job_id,
        data["ID_University"],
        data["ID_Position"],
        data.get("ID_Country", ""),
        data["JobTitle"],
        data.get("NonHTMLAdvertisement", ""),
        data.get("OriginalLink", ""),
        data.get("Deadline"),
        data.get("WorkingTime", "Full time"),
        data.get("ContractType", "Open-ended"),
        data.get("Salary", ""),
        data.get("Keywords", ""),
        "",
    ))
    return job_id


# ── UPDATE / DELETE ───────────────────────────────────────────────────────────

def close_job(job_id: str) -> list[dict]:
    """Call sp_close_job stored procedure."""
    return callproc("sp_close_job", (job_id,))


def expire_overdue_jobs() -> list[dict]:
    """Call sp_expire_overdue_jobs to mark expired postings."""
    return callproc("sp_expire_overdue_jobs")


def update_job(job_id: str, data: dict) -> int:
    allowed = {"JobTitle", "NonHTMLAdvertisement", "OriginalLink",
                "Deadline", "WorkingTime", "ContractType", "Salary",
                "IsAlive", "JobStatus"}
    fields  = {k: v for k, v in data.items() if k in allowed}
    if not fields:
        return 0
    set_clause = ", ".join(f"`{k}` = %s" for k in fields)
    return execute_write(
        f"UPDATE Positions SET {set_clause} WHERE ID = %s",
        list(fields.values()) + [job_id],
    )


"""
app/managers/applicant_manager.py
===================================
CRUD operations for Applicant records.
"""



def list_applicants(
    search: str | None = None,
    is_active: int | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """Liệt kê ứng viên sử dụng Stored Procedure."""
    rows = callproc("sp_list_applicants", (search, page, page_size))
    total = execute_one("SELECT COUNT(*) AS total FROM Applicants")["total"]
    return {"data": rows, "total": total, "page": page, "page_size": page_size,
            "total_pages": max(1, (total + page_size - 1) // page_size)}


def get_smart_recommendations(applicant_id: int, limit: int = 10) -> list[dict]:
    """
    Tìm kiếm việc làm phù hợp dựa trên Chuyên ngành và Công việc mong muốn của Ứng viên.
    Sử dụng MySQL Full-text Search để tối ưu hiệu năng.
    """
    # 1. Lấy thông tin ứng viên
    app_info = get_applicant(applicant_id)
    if not app_info:
        return []

    # 2. Tạo chuỗi tìm kiếm từ Major và Wanted_Job
    # Tách từ và loại bỏ các ký tự đặc biệt để tạo Boolean Mode query

    raw_text = f"{app_info.get('Major', '')} {app_info.get('Wanted_Job', '')}"
    keywords = re.findall(r'\w+', raw_text)
    
    # Chỉ lấy các từ có độ dài > 2
    search_query = " ".join([f"{k}" for k in keywords if len(k) > 2])
    
    if not search_query:
        return []

    # 3. Truy vấn SQL sử dụng MATCH AGAINST để tính điểm Relevance Score
    sql = """
        SELECT  p.ID, p.JobTitle, p.NonHTMLAdvertisement, u.UniversityName,
                MATCH(p.JobTitle, p.Abstract, p.Keywords) AGAINST(%s) AS score
        FROM    Positions p
        LEFT JOIN University u ON p.ID_University = u.ID_University
        WHERE   p.IsAlive = 1
          AND   MATCH(p.JobTitle, p.Abstract, p.Keywords) AGAINST(%s)
        ORDER BY score DESC
        LIMIT %s
    """
    return execute_query(sql, (search_query, search_query, limit))


def get_applicant(applicant_id: int) -> dict | None:
    return execute_one(
        "SELECT * FROM Applicants WHERE ApplicantID = %s", (applicant_id,)
    )


def get_applicant_applications(applicant_id: int) -> list[dict]:
    return execute_query(
        """
        SELECT  a.ApplicationID, a.ApplyDate, a.Status,
                p.JobTitle, u.UniversityName
        FROM    Applications a
        JOIN    Positions  p ON a.JobID      = p.ID
        JOIN    University u ON p.ID_University = u.ID_University
        WHERE   a.ApplicantID = %s
        ORDER BY a.ApplyDate DESC
        """,
        (applicant_id,),
    )


def register_applicant(data: dict) -> int:
    """Đăng ký ứng viên mới qua Procedure."""
    return callproc("sp_upsert_applicant", (
        0, data["ApplicantName"], data["Email"],
        data.get("Age"), data.get("Nationality"), data.get("Gender"),
        data.get("Major"), data.get("Wanted_Job"), 1
    ))


def update_applicant(applicant_id: int, data: dict) -> int:
    """Cập nhật ứng viên qua Procedure."""
    return callproc("sp_upsert_applicant", (
        applicant_id, data.get("ApplicantName"), data.get("Email"),
        data.get("Age"), data.get("Nationality"), data.get("Gender"),
        data.get("Major"), data.get("Wanted_Job"), data.get("IsActive", 1)
    ))


def deactivate_applicant(applicant_id: int) -> int:
    return execute_write(
        "UPDATE Applicants SET IsActive = 0 WHERE ApplicantID = %s",
        (applicant_id,),
    )


"""
app/managers/application_manager.py
=====================================
CRUD for Applications. Uses stored procedures for create/update.
"""


VALID_STATUSES = ("Pending", "Reviewed", "Shortlisted", "Rejected", "Accepted")


def list_applications(
    job_id: str | None = None,
    applicant_id: int | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """Liệt kê hồ sơ ứng tuyển sử dụng Stored Procedure."""
    rows = callproc("sp_list_applications", (job_id, applicant_id, status, page, page_size))
    total = execute_one("SELECT COUNT(*) AS total FROM Applications")["total"]
    return {"data": rows, "total": total, "page": page, "page_size": page_size,
            "total_pages": max(1, (total + page_size - 1) // page_size)}


def get_application(app_id: int) -> dict | None:
    return execute_one(
        """
        SELECT  a.*,
                p.JobTitle, u.UniversityName,
                ap.ApplicantName, ap.Email
        FROM    Applications a
        JOIN    Positions   p  ON a.JobID        = p.ID
        JOIN    University  u  ON p.ID_University = u.ID_University
        JOIN    Applicants  ap ON a.ApplicantID   = ap.ApplicantID
        WHERE   a.ApplicationID = %s
        """,
        (app_id,),
    )


def apply_for_job(job_id: str, applicant_id: int, cover_letter: str = "") -> list[dict]:
    """Call sp_apply_for_job stored procedure."""
    return callproc("sp_apply_for_job", (job_id, applicant_id, cover_letter))


def update_status(app_id: int, status: str, notes: str = "") -> list[dict]:
    """
    Call sp_update_application_status.

    Parameters
    ----------
    status : str
        One of: Pending, Reviewed, Shortlisted, Rejected, Accepted
    """
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status '{status}'. Must be one of {VALID_STATUSES}")
    return callproc("sp_update_application_status", (app_id, status, notes))


def funnel_stats() -> list[dict]:
    """Return application count grouped by status."""
    return execute_query(
        """
        SELECT  Status, COUNT(*) AS count
        FROM    Applications
        GROUP BY Status
        ORDER BY FIELD(Status, 'Pending','Reviewed','Shortlisted','Accepted','Rejected')
        """
    )


def top_jobs_by_applications(limit: int = 10) -> list[dict]:
    return execute_query(
        """
        SELECT  p.ID, p.JobTitle, u.UniversityName,
                COUNT(*) AS application_count
        FROM    Applications a
        JOIN    Positions   p ON a.JobID        = p.ID
        JOIN    University  u ON p.ID_University = u.ID_University
        GROUP BY a.JobID
        ORDER BY application_count DESC
        LIMIT %s
        """,
        (limit,),
    )


"""
app/reports/job_report.py
==========================
Automated job statistics reports.
"""



def job_overview() -> dict:
    """Return headline KPIs for job postings."""
    total     = execute_one("SELECT COUNT(*) AS n FROM Positions")["n"]
    active    = execute_one("SELECT COUNT(*) AS n FROM Positions WHERE IsAlive=1 AND JobStatus=1")["n"]
    expired   = execute_one("SELECT COUNT(*) AS n FROM Positions WHERE IsAlive=0")["n"]
    avg_days  = execute_one(
        "SELECT ROUND(AVG(DATEDIFF(Deadline, DateofPost)),1) AS avg_d "
        "FROM Positions WHERE Deadline IS NOT NULL AND DateofPost IS NOT NULL"
    )
    return {
        "total":    total,
        "active":   active,
        "expired":  expired,
        "pending":  total - active - expired,
        "avg_open_days": avg_days["avg_d"] if avg_days else 0,
    }


def jobs_by_country(limit: int = 10) -> list[dict]:
    return execute_query(
        """
        SELECT  c.CountryName, COUNT(*) AS total,
                SUM(p.IsAlive) AS active
        FROM    Positions p
        JOIN    Country c ON p.ID_Country = c.ID_Country
        GROUP BY p.ID_Country
        ORDER BY total DESC
        LIMIT %s
        """,
        (limit,),
    )


def by_research_area() -> list[dict]:
    return execute_query(
        """
        SELECT  ra.ResearchArea,
                COUNT(DISTINCT pra.ID) AS job_count,
                ROUND(AVG(pra.Weight), 4) AS avg_weight
        FROM    PositionsResearchAreas pra
        JOIN    ResearchArea ra ON pra.ID_ResearchArea = ra.ID_ResearchArea
        GROUP BY pra.ID_ResearchArea
        ORDER BY job_count DESC
        """
    )


def by_position_type() -> list[dict]:
    return execute_query(
        """
        SELECT  pt.PositionTitle,
                COUNT(DISTINCT jpt.ID) AS job_count,
                ROUND(AVG(jpt.Weight), 4) AS avg_weight
        FROM    JobPositionType jpt
        JOIN    PositionType pt ON jpt.ID_PositionType = pt.ID_Position
        GROUP BY jpt.ID_PositionType
        ORDER BY job_count DESC
        """
    )


def recent_trend(days: int = 30) -> list[dict]:
    return execute_query(
        """
        SELECT  DATE(DateofPost) AS post_date,
                COUNT(*) AS postings
        FROM    Positions
        WHERE   DateofPost >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
        GROUP BY DATE(DateofPost)
        ORDER BY post_date
        """,
        (days,),
    )


def working_time_distribution() -> list[dict]:
    return execute_query(
        """
        SELECT  COALESCE(WorkingTime, 'Unknown') AS working_time,
                COUNT(*) AS count
        FROM    Positions
        GROUP BY WorkingTime
        ORDER BY count DESC
        """
    )


"""
app/reports/employer_report.py
================================
Employer activity statistics.
"""



def employer_overview() -> dict:
    total    = execute_one("SELECT COUNT(*) AS n FROM University")["n"]
    active   = execute_one("SELECT COUNT(*) AS n FROM University WHERE Status=1")["n"]
    with_jobs= execute_one(
        "SELECT COUNT(DISTINCT ID_University) AS n FROM Positions WHERE IsAlive=1"
    )["n"]
    return {"total": total, "active": active, "with_active_jobs": with_jobs}


def top_employers(limit: int = 10) -> list[dict]:
    return execute_query(
        """
        SELECT  u.ID_University, u.UniversityName, u.ShortName,
                c.CountryName, u.NumberofRecentPositions,
                COUNT(p.ID) AS total_postings,
                SUM(p.IsAlive) AS active_postings
        FROM    University u
        LEFT JOIN Country   c ON u.ID_Country    = c.ID_Country
        LEFT JOIN Positions p ON u.ID_University = p.ID_University
        WHERE   u.Status = 1
        GROUP BY u.ID_University
        ORDER BY total_postings DESC
        LIMIT %s
        """,
        (limit,),
    )


def employers_by_country(limit: int = 15) -> list[dict]:
    return execute_query(
        """
        SELECT  c.CountryName, cont.name AS continent,
                COUNT(*) AS employer_count,
                SUM(u.NumberofRecentPositions) AS active_jobs
        FROM    University u
        JOIN    Country     c    ON u.ID_Country       = c.ID_Country
        JOIN    Continents  cont ON c.continent_code   = cont.code
        WHERE   u.Status = 1
        GROUP BY u.ID_Country
        ORDER BY employer_count DESC
        LIMIT %s
        """,
        (limit,),
    )


def by_continent() -> list[dict]:
    return execute_query(
        """
        SELECT  cont.name AS continent,
                COUNT(DISTINCT u.ID_University) AS employer_count
        FROM    University  u
        JOIN    Country     c    ON u.ID_Country       = c.ID_Country
        JOIN    Continents  cont ON c.continent_code   = cont.code
        WHERE   u.Status = 1
        GROUP BY cont.code
        ORDER BY employer_count DESC
        """
    )


def recently_active(limit: int = 10) -> list[dict]:
    return execute_query(
        """
        SELECT  u.UniversityName, u.ShortName, c.CountryName,
                MAX(p.DateofPost) AS latest_post,
                COUNT(p.ID) AS total_posts
        FROM    University u
        JOIN    Positions p ON u.ID_University = p.ID_University
        JOIN    Country   c ON u.ID_Country    = c.ID_Country
        GROUP BY u.ID_University
        ORDER BY latest_post DESC
        LIMIT %s
        """,
        (limit,),
    )


"""
app/reports/application_report.py
====================================
Application performance statistics.
"""



def application_overview() -> dict:
    total    = execute_one("SELECT COUNT(*) AS n FROM Applications")["n"]
    pending  = execute_one("SELECT COUNT(*) AS n FROM Applications WHERE Status='Pending'")["n"]
    accepted = execute_one("SELECT COUNT(*) AS n FROM Applications WHERE Status='Accepted'")["n"]
    rejected = execute_one("SELECT COUNT(*) AS n FROM Applications WHERE Status='Rejected'")["n"]
    applicants = execute_one("SELECT COUNT(*) AS n FROM Applicants WHERE IsActive=1")["n"]
    return {
        "total": total, "pending": pending,
        "accepted": accepted, "rejected": rejected,
        "active_applicants": applicants,
        "response_rate": round((total - pending) / total * 100, 1) if total else 0,
    }


def funnel() -> list[dict]:
    """Lấy dữ liệu thống kê phễu tuyển dụng từ View."""
    return execute_query("SELECT * FROM vw_application_funnel")


def top_jobs_report(limit: int = 10) -> list[dict]:
    """Lấy danh sách các công việc hot nhất từ View."""
    return execute_query("SELECT * FROM vw_top_jobs_reporting LIMIT %s", (limit,))


def monthly_trend(months: int = 6) -> list[dict]:
    """Lấy xu hướng ứng tuyển hàng tháng từ View."""
    return execute_query("SELECT * FROM vw_monthly_application_trend LIMIT %s", (months,))


def status_by_employer(limit: int = 10) -> list[dict]:
    """Lấy thống kê hiệu quả tuyển dụng của các trường từ View."""
    return execute_query("SELECT * FROM vw_employer_application_stats LIMIT %s", (limit,))


