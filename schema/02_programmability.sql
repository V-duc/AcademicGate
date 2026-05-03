-- ============================================================
--  AcademicGate Database
--  FILE 02 — PROGRAMMABILITY (FULL & IDEMPOTENT)
-- ============================================================

USE AcademicGateDB;

DELIMITER $$

-- ============================================================
--  SECTION 9 – FUNCTIONS
-- ============================================================

DROP FUNCTION IF EXISTS fn_active_jobs_per_employer$$
CREATE FUNCTION fn_active_jobs_per_employer(p_university_id VARCHAR(20))
RETURNS INT READS SQL DATA DETERMINISTIC
BEGIN
    DECLARE v_count INT;
    SELECT COUNT(*) INTO v_count FROM Positions 
    WHERE ID_University = p_university_id AND IsAlive = 1 AND JobStatus = 1;
    RETURN IFNULL(v_count, 0);
END$$

DROP FUNCTION IF EXISTS fn_total_applications_per_job$$
CREATE FUNCTION fn_total_applications_per_job(p_job_id VARCHAR(36))
RETURNS INT READS SQL DATA DETERMINISTIC
BEGIN
    DECLARE v_count INT;
    SELECT COUNT(*) INTO v_count FROM Applications WHERE JobID = p_job_id;
    RETURN IFNULL(v_count, 0);
END$$

DROP FUNCTION IF EXISTS fn_job_status_label$$
CREATE FUNCTION fn_job_status_label(p_job_id VARCHAR(36))
RETURNS VARCHAR(20) READS SQL DATA DETERMINISTIC
BEGIN
    DECLARE v_alive TINYINT; DECLARE v_status TINYINT; DECLARE v_deadline DATE; DECLARE v_label VARCHAR(20);
    SELECT IsAlive, JobStatus, Deadline INTO v_alive, v_status, v_deadline FROM Positions WHERE ID = p_job_id LIMIT 1;
    IF v_alive IS NULL THEN SET v_label = 'NOT FOUND';
    ELSEIF v_status = 9 THEN SET v_label = 'Closed';
    ELSEIF v_alive = 0 THEN SET v_label = 'Inactive';
    ELSEIF v_deadline < CURDATE() THEN SET v_label = 'Expired';
    ELSE SET v_label = 'Active'; END IF;
    RETURN v_label;
END$$

-- ============================================================
--  SECTION 10 – PROCEDURES
-- ============================================================

DROP PROCEDURE IF EXISTS sp_post_job$$
CREATE PROCEDURE sp_post_job(
    IN p_id VARCHAR(36), IN p_univ_id VARCHAR(20), IN p_pos_type VARCHAR(10),
    IN p_country_id VARCHAR(10), IN p_title TEXT, IN p_desc LONGTEXT,
    IN p_link TEXT, IN p_deadline DATE, IN p_working_time VARCHAR(30),
    IN p_contract VARCHAR(100), IN p_salary VARCHAR(100), IN p_keywords TEXT,
    OUT p_result VARCHAR(100)
)
BEGIN
    INSERT INTO Positions (ID, ID_University, ID_Position, ID_Country, JobTitle, NonHTMLAdvertisement, OriginalLink, Deadline, DateofPost, WorkingTime, ContractType, Salary, Keywords, IsAlive, JobStatus, FavoriteCount)
    VALUES (p_id, p_univ_id, p_pos_type, p_country_id, p_title, p_desc, p_link, p_deadline, CURDATE(), p_working_time, p_contract, p_salary, p_keywords, 1, 1, 0);
    SET p_result = 'SUCCESS';
END$$

DROP PROCEDURE IF EXISTS sp_search_jobs$$
CREATE PROCEDURE sp_search_jobs(
    IN p_keyword VARCHAR(200), IN p_country_id VARCHAR(10), IN p_pos_type VARCHAR(10),
    IN p_page_size INT, IN p_offset INT
)
BEGIN
    SELECT p.*, u.UniversityName, c.CountryName 
    FROM Positions p
    LEFT JOIN University u ON p.ID_University = u.ID_University
    LEFT JOIN Country c ON p.ID_Country = c.ID_Country
    WHERE p.IsAlive = 1 
      AND (p_keyword IS NULL OR p.JobTitle LIKE CONCAT('%', p_keyword, '%'))
      AND (p_country_id IS NULL OR p.ID_Country = p_country_id)
      AND (p_pos_type IS NULL OR p.ID_Position = p_pos_type)
    ORDER BY p.DateofPost DESC
    LIMIT p_offset, p_page_size;
END$$

DROP PROCEDURE IF EXISTS sp_apply_for_job$$
CREATE PROCEDURE sp_apply_for_job(
    IN p_job_id VARCHAR(36), IN p_applicant_id INT, IN p_cover_letter TEXT
)
BEGIN
    INSERT INTO Applications (JobID, ApplicantID, ApplyDate, Status, CoverLetter)
    VALUES (p_job_id, p_applicant_id, NOW(), 'Pending', p_cover_letter);
END$$

DROP PROCEDURE IF EXISTS sp_list_employers$$
CREATE PROCEDURE sp_list_employers(
    IN p_search VARCHAR(100), IN p_country VARCHAR(10), IN p_status TINYINT,
    IN p_page INT, IN p_page_size INT
)
BEGIN
    DECLARE v_offset INT;
    SET v_offset = (IFNULL(p_page, 1) - 1) * IFNULL(p_page_size, 20);
    SELECT u.*, c.CountryName, cont.name AS ContinentName
    FROM University u
    LEFT JOIN Country c ON u.ID_Country = c.ID_Country
    LEFT JOIN Continents cont ON c.continent_code = cont.code
    WHERE (p_search IS NULL OR u.UniversityName LIKE CONCAT('%', p_search, '%') OR u.ShortName LIKE CONCAT('%', p_search, '%'))
      AND (p_country IS NULL OR u.ID_Country = p_country)
      AND (p_status IS NULL OR u.Status = p_status)
    ORDER BY u.NumberofRecentPositions DESC, u.UniversityName
    LIMIT v_offset, p_page_size;
END$$

DROP PROCEDURE IF EXISTS sp_list_applicants$$
CREATE PROCEDURE sp_list_applicants(
    IN p_search VARCHAR(100), IN p_page INT, IN p_page_size INT
)
BEGIN
    DECLARE v_offset INT;
    SET v_offset = (IFNULL(p_page, 1) - 1) * IFNULL(p_page_size, 20);
    SELECT * FROM Applicants
    WHERE (p_search IS NULL OR ApplicantName LIKE CONCAT('%', p_search, '%') OR Email LIKE CONCAT('%', p_search, '%'))
    ORDER BY RegisteredAt DESC
    LIMIT v_offset, p_page_size;
END$$

DROP PROCEDURE IF EXISTS sp_list_applications$$
CREATE PROCEDURE sp_list_applications(
    IN p_job_id VARCHAR(36), IN p_applicant_id INT, IN p_status VARCHAR(20),
    IN p_page INT, IN p_page_size INT
)
BEGIN
    DECLARE v_offset INT;
    SET v_offset = (IFNULL(p_page, 1) - 1) * IFNULL(p_page_size, 20);
    SELECT a.*, p.JobTitle, u.UniversityName, ap.ApplicantName, ap.Email
    FROM Applications a
    JOIN Positions p ON a.JobID = p.ID
    JOIN University u ON p.ID_University = u.ID_University
    JOIN Applicants ap ON a.ApplicantID = ap.ApplicantID
    WHERE (p_job_id IS NULL OR a.JobID = p_job_id)
      AND (p_applicant_id IS NULL OR a.ApplicantID = p_applicant_id)
      AND (p_status IS NULL OR a.Status = p_status)
    ORDER BY a.ApplyDate DESC
    LIMIT v_offset, p_page_size;
END$$

DROP PROCEDURE IF EXISTS sp_update_application_status$$
CREATE PROCEDURE sp_update_application_status(
    IN p_id INT, IN p_status VARCHAR(20), IN p_notes TEXT
)
BEGIN
    UPDATE Applications SET Status = p_status, Notes = p_notes WHERE ApplicationID = p_id;
END$$

DROP PROCEDURE IF EXISTS sp_upsert_university$$
CREATE PROCEDURE sp_upsert_university(
    IN p_id VARCHAR(20), IN p_name TEXT, IN p_short_name VARCHAR(50),
    IN p_addr TEXT, IN p_country_id VARCHAR(10), IN p_website TEXT,
    IN p_email VARCHAR(100), IN p_status TINYINT
)
BEGIN
    INSERT INTO University (ID_University, UniversityName, ShortName, UniversityAddr, ID_Country, Website, ContactEmail, Status)
    VALUES (p_id, p_name, p_short_name, p_addr, p_country_id, p_website, p_email, p_status)
    ON DUPLICATE KEY UPDATE
        UniversityName = p_name, ShortName = p_short_name, UniversityAddr = p_addr,
        ID_Country = p_country_id, Website = p_website, ContactEmail = p_email, Status = p_status;
END$$

DROP PROCEDURE IF EXISTS sp_upsert_applicant$$
CREATE PROCEDURE sp_upsert_applicant(
    IN p_id        INT UNSIGNED,
    IN p_name      VARCHAR(100),
    IN p_email     VARCHAR(100),
    IN p_age       INT,
    IN p_nation    VARCHAR(100),
    IN p_gender    VARCHAR(10),
    IN p_major     VARCHAR(255),
    IN p_wanted    VARCHAR(255),
    IN p_is_active TINYINT
)
BEGIN
    IF p_id IS NULL OR p_id = 0 THEN
        INSERT INTO Applicants (ApplicantName, Email, Age, Nationality, Gender, Major, Wanted_Job, IsActive)
        VALUES (p_name, p_email, p_age, p_nation, p_gender, p_major, p_wanted, p_is_active);
    ELSE
        UPDATE Applicants
        SET ApplicantName = p_name,
            Email         = p_email,
            Age           = p_age,
            Nationality   = p_nation,
            Gender        = p_gender,
            Major         = p_major,
            Wanted_Job    = p_wanted,
            IsActive      = p_is_active
        WHERE ApplicantID = p_id;
    END IF;
END$$

DROP PROCEDURE IF EXISTS sp_close_job$$
CREATE PROCEDURE sp_close_job(IN p_id VARCHAR(36))
BEGIN
    UPDATE Positions SET IsAlive = 0, JobStatus = 9 WHERE ID = p_id;
END$$

DROP PROCEDURE IF EXISTS sp_expire_overdue_jobs$$
CREATE PROCEDURE sp_expire_overdue_jobs()
BEGIN
    UPDATE Positions SET IsAlive = 0, JobStatus = 9 WHERE IsAlive = 1 AND Deadline < CURDATE();
END$$

DROP PROCEDURE IF EXISTS sp_refresh_university_counts$$
CREATE PROCEDURE sp_refresh_university_counts()
BEGIN
    UPDATE University u
    LEFT JOIN (
        SELECT ID_University, COUNT(*) AS active_count
        FROM Positions WHERE IsAlive = 1 AND JobStatus = 1 GROUP BY ID_University
    ) counts ON u.ID_University = counts.ID_University
    SET u.NumberofRecentPositions = IFNULL(counts.active_count, 0);
END$$

-- ============================================================
--  SECTION 11 – TRIGGERS
-- ============================================================

DROP TRIGGER IF EXISTS trg_positions_before_insert$$
CREATE TRIGGER trg_positions_before_insert BEFORE INSERT ON Positions FOR EACH ROW
BEGIN
    IF NEW.DateofPost IS NULL THEN SET NEW.DateofPost = CURDATE(); END IF;
    IF NEW.Deadline < CURDATE() THEN SET NEW.IsAlive = 0; SET NEW.JobStatus = 9; END IF;
END$$

DROP TRIGGER IF EXISTS trg_positions_after_insert$$
CREATE TRIGGER trg_positions_after_insert AFTER INSERT ON Positions FOR EACH ROW
BEGIN
    IF IFNULL(@bulk_import_mode, 0) = 0 THEN
        UPDATE University SET NumberofRecentPositions = fn_active_jobs_per_employer(NEW.ID_University) WHERE ID_University = NEW.ID_University;
    END IF;
END$$

DROP TRIGGER IF EXISTS trg_positions_before_update$$
CREATE TRIGGER trg_positions_before_update BEFORE UPDATE ON Positions FOR EACH ROW
BEGIN
    IF NEW.Deadline < CURDATE() AND OLD.IsAlive = 1 THEN SET NEW.IsAlive = 0; SET NEW.JobStatus = 9; END IF;
END$$

DROP TRIGGER IF EXISTS trg_positions_after_update$$
CREATE TRIGGER trg_positions_after_update AFTER UPDATE ON Positions FOR EACH ROW
BEGIN
    IF (NEW.IsAlive <> OLD.IsAlive OR NEW.JobStatus <> OLD.JobStatus) AND IFNULL(@bulk_import_mode, 0) = 0 THEN
        UPDATE University SET NumberofRecentPositions = fn_active_jobs_per_employer(NEW.ID_University) WHERE ID_University = NEW.ID_University;
    END IF;
END$$

DROP TRIGGER IF EXISTS trg_applicants_before_insert$$
CREATE TRIGGER trg_applicants_before_insert BEFORE INSERT ON Applicants FOR EACH ROW
BEGIN
    SET NEW.Email = LOWER(TRIM(NEW.Email));
END$$

DROP TRIGGER IF EXISTS trg_applicants_before_update$$
CREATE TRIGGER trg_applicants_before_update BEFORE UPDATE ON Applicants FOR EACH ROW
BEGIN
    SET NEW.Email = LOWER(TRIM(NEW.Email));
END$$

DELIMITER ;
