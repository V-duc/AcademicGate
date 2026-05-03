-- ============================================================
--  AcademicGate Database
--  FILE 03 — VIEWS (Khung nhìn)
--  Nội dung: Views (Section 8)
--  Yêu cầu: Chạy sau 01_schema.sql
--  MySQL 8.0+
-- ============================================================

USE AcademicGateDB;

-- ============================================================
--  SECTION 8 – VIEWS
-- ============================================================

-- 8.1  Active Jobs (with university name, country, position type)
CREATE OR REPLACE VIEW vw_active_jobs AS
SELECT
    p.ID,
    p.JobTitle,
    u.UniversityName          AS Employer,
    c.CountryName,
    ct.name                   AS Continent,
    pt.PositionTitle          AS PositionType,
    p.WorkingTime,
    p.ContractType,
    p.Salary,
    p.DateofPost,
    p.Deadline,
    p.OriginalLink,
    p.FavoriteCount
FROM Positions      p
LEFT JOIN University   u  ON p.ID_University = u.ID_University
LEFT JOIN Country      c  ON p.ID_Country    = c.ID_Country
LEFT JOIN Continents   ct ON c.continent_code = ct.code
LEFT JOIN PositionType pt ON p.ID_Position   = pt.ID_Position
WHERE p.IsAlive = 1
  AND p.JobStatus = 1;

-- 8.2  Expired Jobs
CREATE OR REPLACE VIEW vw_expired_jobs AS
SELECT
    p.ID,
    p.JobTitle,
    u.UniversityName  AS Employer,
    c.CountryName,
    p.Deadline,
    p.DateofPost,
    p.JobStatus
FROM Positions   p
LEFT JOIN University u ON p.ID_University = u.ID_University
LEFT JOIN Country    c ON p.ID_Country    = c.ID_Country
WHERE p.IsAlive = 0
   OR p.JobStatus = 9
   OR (p.Deadline IS NOT NULL AND p.Deadline < CURDATE());

-- 8.3  Jobs by Country (active only)
CREATE OR REPLACE VIEW vw_jobs_by_country AS
SELECT
    c.ID_Country,
    c.CountryName,
    ct.name            AS Continent,
    COUNT(p.ID)        AS TotalJobs,
    SUM(p.IsAlive)     AS ActiveJobs,
    SUM(1 - p.IsAlive) AS InactiveJobs
FROM Country     c
LEFT JOIN Continents ct ON c.continent_code = ct.code
LEFT JOIN Positions  p  ON p.ID_Country     = c.ID_Country
GROUP BY c.ID_Country, c.CountryName, ct.name;

-- 8.4  Employer Posting Summary
CREATE OR REPLACE VIEW vw_employer_summary AS
SELECT
    u.ID_University,
    u.UniversityName,
    c.CountryName,
    COUNT(p.ID)             AS TotalPostings,
    SUM(p.IsAlive)          AS ActivePostings,
    SUM(1 - p.IsAlive)      AS InactivePostings,
    MAX(p.DateofPost)       AS MostRecentPost,
    SUM(p.FavoriteCount)    AS TotalFavorites
FROM University u
LEFT JOIN Country   c ON u.ID_Country    = c.ID_Country
LEFT JOIN Positions p ON p.ID_University = u.ID_University
GROUP BY u.ID_University, u.UniversityName, c.CountryName;

-- 8.5  Applications dashboard
CREATE OR REPLACE VIEW vw_application_summary AS
SELECT
    a.ApplicationID,
    a.ApplyDate,
    a.Status                AS AppStatus,
    ap.ApplicantName,
    ap.Email,
    p.JobTitle,
    u.UniversityName        AS Employer,
    c.CountryName
FROM Applications a
JOIN Applicants  ap ON a.ApplicantID  = ap.ApplicantID
JOIN Positions    p ON a.JobID        = p.ID
LEFT JOIN University u ON p.ID_University = u.ID_University
LEFT JOIN Country    c ON p.ID_Country    = c.ID_Country;

-- 8.6  Jobs by Research Area
CREATE OR REPLACE VIEW vw_jobs_by_researcharea AS
SELECT
    ra.ID_ResearchArea,
    ra.ResearchArea,
    COUNT(pr.ID)            AS TotalLinkedJobs,
    AVG(pr.Weight)          AS AvgRelevanceWeight,
    SUM(p.IsAlive)          AS ActiveJobs
FROM ResearchArea             ra
LEFT JOIN PositionsResearchAreas pr ON ra.ID_ResearchArea = pr.ID_ResearchArea
LEFT JOIN Positions               p  ON pr.ID              = p.ID
GROUP BY ra.ID_ResearchArea, ra.ResearchArea;

-- 8.7  Jobs by Position Type
CREATE OR REPLACE VIEW vw_jobs_by_positiontype AS
SELECT
    pt.ID_Position,
    pt.PositionTitle,
    COUNT(jp.ID)            AS TotalLinkedJobs,
    AVG(jp.Weight)          AS AvgConfidenceWeight,
    SUM(p.IsAlive)          AS ActiveJobs
FROM PositionType       pt
LEFT JOIN JobPositionType jp ON pt.ID_Position   = jp.ID_PositionType
LEFT JOIN Positions        p  ON jp.ID             = p.ID
GROUP BY pt.ID_Position, pt.PositionTitle;


-- 8.8  Application Funnel with percentages (for Dashboard)
CREATE OR REPLACE VIEW vw_application_funnel AS
SELECT  
    Status, 
    COUNT(*) AS count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM Applications), 1) AS pct
FROM Applications
GROUP BY Status
ORDER BY FIELD(Status, 'Pending','Reviewed','Shortlisted','Accepted','Rejected');

-- 8.9  Top Jobs by Application count
CREATE OR REPLACE VIEW vw_top_jobs_reporting AS
SELECT  
    p.JobTitle, 
    u.UniversityName, 
    c.CountryName,
    COUNT(*) AS applications,
    SUM(CASE WHEN a.Status = 'Accepted' THEN 1 ELSE 0 END) AS accepted
FROM Applications a
JOIN Positions  p ON a.JobID        = p.ID
JOIN University u ON p.ID_University = u.ID_University
LEFT JOIN Country c ON p.ID_Country  = c.ID_Country
GROUP BY a.JobID, p.JobTitle, u.UniversityName, c.CountryName
ORDER BY applications DESC;

-- 8.10 Monthly Application Trend
CREATE OR REPLACE VIEW vw_monthly_application_trend AS
SELECT  
    DATE_FORMAT(ApplyDate, '%Y-%m') AS month,
    COUNT(*) AS total_applications
FROM Applications
GROUP BY month
ORDER BY month DESC;

-- 8.11 Employer Application Performance
CREATE OR REPLACE VIEW vw_employer_application_stats AS
SELECT  
    u.UniversityName,
    COUNT(*)                           AS total,
    SUM(CASE WHEN a.Status = 'Accepted' THEN 1 ELSE 0 END) AS accepted,
    SUM(CASE WHEN a.Status = 'Rejected' THEN 1 ELSE 0 END) AS rejected,
    SUM(CASE WHEN a.Status = 'Pending'  THEN 1 ELSE 0 END) AS pending
FROM Applications a
JOIN Positions   p ON a.JobID        = p.ID
JOIN University  u ON p.ID_University = u.ID_University
GROUP BY p.ID_University, u.UniversityName
ORDER BY total DESC;

-- ============================================================
--  END OF FILE 03_views.sql
-- ============================================================
