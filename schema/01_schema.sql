-- ============================================================
--  AcademicGate Database
--  FILE 01 — SCHEMA
--  Contents : Database init + Tables (Section 0–6) + Indexes (Section 7)
--  MySQL 8.0+
-- ============================================================
--
--  PYTHON IMPORT INTEGRATION
--  ─────────────────────────
--  This schema is loaded by the Python import pipeline:
--    config.py      – TABLE_CONFIG defines the 8 tables and their CSV sources
--    import_data.py – entry point; run:  python import_data.py
--
--  Load order must match the GROUP numbers in config.py TABLE_CONFIG:
--    Group 1 → Continents, PositionType, ResearchArea   (no FK deps)
--    Group 2 → Country                                  (depends on Group 1)
--    Group 3 → University                               (depends on Group 2)
--    Group 4 → Positions                                (depends on Groups 1-3)
--    Group 5 → PositionsResearchAreas, JobPositionType  (junction tables)
--
--  During bulk import the Python script sets these session variables:
--    SET FOREIGN_KEY_CHECKS = 0;   -- skip FK validation for speed
--    SET @bulk_import_mode  = 1;   -- suppress expensive AFTER INSERT triggers
--  Both are restored to their defaults when import finishes.
-- ============================================================


-- ============================================================
--  SECTION 0 – DATABASE SETUP
-- ============================================================
DROP DATABASE IF EXISTS AcademicGateDB;
CREATE DATABASE AcademicGateDB
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE AcademicGateDB;

-- Disable FK checks during schema creation (re-enabled at end of file)
SET FOREIGN_KEY_CHECKS = 0;
-- Python importer also sets this; initialise here for safety
SET @bulk_import_mode = 0;

-- ============================================================
--  SECTION 1 – CORE LOOKUP TABLES
--  Python import GROUP 1  (no FK dependencies – loaded first)
--  CSV sources: tbl_continents_*, tbl_positiontype_*, tbl_researcharea_*
-- ============================================================

-- 1.1 Continents
-- Python columns: ["code", "name"]
CREATE TABLE Continents (
    code        VARCHAR(2)   NOT NULL,
    name        VARCHAR(20)  NOT NULL,
    -- ── Constraints ──────────────────────────────────────────
    CONSTRAINT pk_continents PRIMARY KEY (code),
    CONSTRAINT chk_continent_code CHECK (code IN ('AF','AN','AS','EU','NA','OC','SA'))
) ENGINE=InnoDB COMMENT='Reference table – 7 continents';

-- 1.2 Countries
-- Python import GROUP 2  (depends on Continents)
-- Python columns: ["ID_Country","code","CountryName","full_name","number","continent_code","display_order"]
CREATE TABLE Country (
    ID_Country      VARCHAR(10)  NOT NULL,
    code            CHAR(2)      NOT NULL,          -- ISO 3166-1 alpha-2
    CountryName     VARCHAR(100) NOT NULL,
    full_name        VARCHAR(200)  NULL,
    number          SMALLINT UNSIGNED NULL,          -- ISO numeric code
    continent_code  VARCHAR(2)    NULL,
    display_order   SMALLINT      NULL DEFAULT 0,
    -- ── Constraints ──────────────────────────────────────────
    CONSTRAINT pk_country      PRIMARY KEY (ID_Country),
    CONSTRAINT uq_country_code UNIQUE      (code),
    CONSTRAINT fk_country_cont FOREIGN KEY (continent_code)
        REFERENCES Continents(code)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB COMMENT='246 countries with ISO codes';

-- 1.3 Position Types  (job categories / academic roles)
-- Python import GROUP 1
-- Python columns: ["ID_Position","PositionTitle","Description","SortNumber"]
-- NOTE: SortNumber is NOT NULL DEFAULT 99; INSERT IGNORE with a NULL value
--       will store the DEFAULT (99) – safe with MySQL's IGNORE behaviour.
CREATE TABLE PositionType (
    ID_Position    VARCHAR(10)  NOT NULL,
    PositionTitle  VARCHAR(50)  NOT NULL,
    Description    TEXT          NULL,
    SortNumber     TINYINT UNSIGNED NOT NULL DEFAULT 99,
    -- ── Constraints ──────────────────────────────────────────
    CONSTRAINT pk_positiontype PRIMARY KEY (ID_Position),
    CONSTRAINT chk_pos_sort    CHECK (SortNumber >= 0)
) ENGINE=InnoDB COMMENT='10 academic position categories (PROF, PHD, POSTDOC …)';

-- 1.4 Research Areas  (academic disciplines)
-- Python import GROUP 1
-- Python columns: ["ID_ResearchArea","ResearchArea","Description"]
CREATE TABLE ResearchArea (
    ID_ResearchArea VARCHAR(10)  NOT NULL,
    ResearchArea    VARCHAR(50)  NOT NULL,
    Description     TEXT          NULL,
    -- ── Constraints ──────────────────────────────────────────
    CONSTRAINT pk_researcharea PRIMARY KEY (ID_ResearchArea)
) ENGINE=InnoDB COMMENT='25 research fields (MEDIC, ENGINEER, COMPUTER …)';


-- ============================================================
--  SECTION 2 – EMPLOYERS / UNIVERSITIES
--  Python import GROUP 3  (depends on Country)
--  CSV source: tbl_university_*
-- ============================================================
-- Python columns: ["ID_University","UniversityName","ShortName","UniversityAddr",
--                  "UniversityLogo","logo_path","Website","ContactEmail",
--                  "ID_Country","ID_State","NumberofRecentPositions",
--                  "NumberofLatestNews","NumberofRecentScholarships",
--                  "ProcessingDate","longitude","latitude","Status","IndexID"]
-- NOTE: NumberofRecentPositions is kept in sync by triggers after import.
--       During bulk load the trigger is suppressed via @bulk_import_mode = 1
--       and sp_refresh_university_counts() is called once when import finishes.
CREATE TABLE University (
    ID_University   VARCHAR(20)   NOT NULL,
    UniversityName  VARCHAR(255)  NOT NULL,
    ShortName       VARCHAR(100)   NULL,
    UniversityAddr  VARCHAR(500)   NULL,
    UniversityLogo  VARCHAR(500)   NULL,
    logo_path       VARCHAR(500)   NULL,
    Website         VARCHAR(300)   NULL,
    ContactEmail    VARCHAR(150)   NULL,
    ID_Country      VARCHAR(10)    NULL,
    ID_State        VARCHAR(10)    NULL,
    NumberofRecentPositions    INT UNSIGNED NULL DEFAULT 0,
    NumberofLatestNews         INT UNSIGNED NULL DEFAULT 0,
    NumberofRecentScholarships INT UNSIGNED NULL DEFAULT 0,
    ProcessingDate  DATE           NULL,
    longitude       DECIMAL(10,7)  NULL,
    latitude        DECIMAL(10,7)  NULL,
    Status          TINYINT        NOT NULL DEFAULT 1,
    IndexID         INT            NULL,
    -- ── Constraints ──────────────────────────────────────────
    CONSTRAINT pk_university      PRIMARY KEY (ID_University),
    CONSTRAINT fk_univ_country    FOREIGN KEY (ID_Country)
        REFERENCES Country(ID_Country)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT chk_univ_email     CHECK (ContactEmail IS NULL OR ContactEmail LIKE '%@%'),
    CONSTRAINT chk_univ_status    CHECK (Status IN (0, 1))
) ENGINE=InnoDB COMMENT='3,053 universities – the "Employers" entity';


-- ============================================================
--  SECTION 3 – ACADEMIC JOB POSTINGS
--  Python import GROUP 4  (depends on Country, University, PositionType)
--  CSV source: tbl_positions.csv  (~41,635 rows, ~480 MB)
-- ============================================================
-- Python columns: ["ID","SiteId","Source","ID_Country","ID_University",
--                  "ID_Position","JobTitle","HTMLAdvertisement",
--                  "NonHTMLAdvertisement","OriginalLink","Deadline",
--                  "DateofPost","DateOfPublish","IndexID","IsAlive",
--                  "Keywords","Abstract","FavoriteCount","JobStatus",
--                  "WorkingTime","ContractType","Salary",
--                  "ID_PositionList","PositionList",
--                  "ID_ResearchAreaList","ResearchAreaList"]
-- NOTE: trg_positions_before_insert normalises WorkingTime typos and
--       auto-expires rows whose Deadline is already in the past.
CREATE TABLE Positions (
    ID                      VARCHAR(36)   NOT NULL,   -- UUID PK
    SiteId                  TINYINT       NOT NULL DEFAULT 0,
    Source                  CHAR(1)       NOT NULL DEFAULT 'M',
    ID_Country              VARCHAR(10)    NULL,
    ID_University           VARCHAR(20)    NULL,
    ID_Position             VARCHAR(10)    NULL,       -- primary position type
    JobTitle                TEXT           NULL,
    HTMLAdvertisement       LONGTEXT       NULL,
    NonHTMLAdvertisement    LONGTEXT       NULL,
    OriginalLink            TEXT           NULL,
    Deadline                DATE           NULL,
    DateofPost              DATE           NULL,
    DateOfPublish           DATE           NULL,       -- 100 % empty in source
    IndexID                 INT            NULL,
    IsAlive                 TINYINT(1)    NOT NULL DEFAULT 1,
    Keywords                TEXT           NULL,
    Abstract                TEXT           NULL,
    FavoriteCount           INT UNSIGNED  NOT NULL DEFAULT 0,
    JobStatus               TINYINT       NOT NULL DEFAULT 1,   -- 1=normal, 9=closed
    WorkingTime             VARCHAR(30)    NULL,
    ContractType            VARCHAR(100)   NULL,
    Salary                  VARCHAR(100)   NULL,
    -- Denormalised list columns kept for backward compatibility
    ID_PositionList         TEXT           NULL,
    PositionList            TEXT           NULL,
    ID_ResearchAreaList     TEXT           NULL,
    ResearchAreaList        TEXT           NULL,
    ProcessingDate          DATETIME       NULL,
    -- ── Constraints ──────────────────────────────────────────
    CONSTRAINT pk_positions        PRIMARY KEY (ID),
    CONSTRAINT fk_pos_country      FOREIGN KEY (ID_Country)
        REFERENCES Country(ID_Country)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_pos_university   FOREIGN KEY (ID_University)
        REFERENCES University(ID_University)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_pos_postype      FOREIGN KEY (ID_Position)
        REFERENCES PositionType(ID_Position)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT chk_pos_isalive     CHECK (IsAlive IN (0, 1)),
    CONSTRAINT chk_pos_status      CHECK (JobStatus IN (1, 9)),
    CONSTRAINT chk_pos_deadline    CHECK (Deadline IS NULL OR Deadline >= DateofPost)
) ENGINE=InnoDB COMMENT='41,635 academic job postings';


-- ============================================================
--  SECTION 4 – JUNCTION / BRIDGE TABLES
--  Python import GROUP 5  (loaded last – both fact tables must exist first)
--  CSV sources: tbl_positions_researchareas_*, tbl_job_positiontype_*
-- ============================================================

-- 4.1  Position ↔ Research Area  (many-to-many with weight)
-- Python columns: ["ID_ResearchArea","ID","DateOfPost","Weight"]  (auto_pk=True → IndexID excluded)
CREATE TABLE PositionsResearchAreas (
    IndexID         INT           NOT NULL AUTO_INCREMENT,
    ID_ResearchArea VARCHAR(10)   NOT NULL,
    ID              VARCHAR(36)   NOT NULL,
    DateOfPost      DATETIME       NULL,
    Weight          DECIMAL(5,4)  NOT NULL DEFAULT 0.0000,
    -- ── Constraints ──────────────────────────────────────────
    CONSTRAINT pk_posra        PRIMARY KEY (IndexID),
    CONSTRAINT uq_posra_pair   UNIQUE (ID, ID_ResearchArea),
    CONSTRAINT fk_posra_pos    FOREIGN KEY (ID)
        REFERENCES Positions(ID)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_posra_ra     FOREIGN KEY (ID_ResearchArea)
        REFERENCES ResearchArea(ID_ResearchArea)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT chk_posra_wt    CHECK (Weight BETWEEN 0 AND 1)
) ENGINE=InnoDB COMMENT='97,148 position–research-area links with relevance weight';

-- 4.2  Position ↔ Position Type  (many-to-many with weight)
-- Python columns: ["ID","ID_PositionType","Weight"]  (auto_pk=True → ID_Index excluded)
CREATE TABLE JobPositionType (
    ID_Index        INT           NOT NULL AUTO_INCREMENT,
    ID              VARCHAR(36)   NOT NULL,
    ID_PositionType VARCHAR(10)   NOT NULL,
    Weight          DECIMAL(5,4)  NOT NULL DEFAULT 0.0000,
    -- ── Constraints ──────────────────────────────────────────
    CONSTRAINT pk_jobpt       PRIMARY KEY (ID_Index),
    CONSTRAINT uq_jobpt_pair  UNIQUE (ID, ID_PositionType),
    CONSTRAINT fk_jobpt_pos   FOREIGN KEY (ID)
        REFERENCES Positions(ID)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_jobpt_pt    FOREIGN KEY (ID_PositionType)
        REFERENCES PositionType(ID_Position)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT chk_jobpt_wt   CHECK (Weight BETWEEN 0 AND 1)
) ENGINE=InnoDB COMMENT='1,612,212 position–positiontype links with confidence weight';


-- ============================================================
--  SECTION 5 – APPLICANTS & APPLICATIONS
--  (Assignment-specific entities not in source dataset)
-- ============================================================

-- 5.1 Applicants
CREATE TABLE Applicants (
    ApplicantID     INT UNSIGNED  NOT NULL AUTO_INCREMENT,
    ApplicantName   VARCHAR(200)  NOT NULL,
    Email           VARCHAR(150)  NOT NULL,
    Age             INT            NULL,
    Nationality     VARCHAR(100)   NULL,
    Gender          VARCHAR(10)    NULL,
    Major           VARCHAR(255)   NULL,
    Wanted_Job      VARCHAR(255)   NULL,
    RegisteredAt    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    IsActive        TINYINT(1)    NOT NULL DEFAULT 1,
    -- ── Constraints ──────────────────────────────────────────
    CONSTRAINT pk_applicants     PRIMARY KEY (ApplicantID),
    CONSTRAINT uq_appl_email     UNIQUE      (Email),
    CONSTRAINT chk_appl_email    CHECK (Email LIKE '%@%'),
    CONSTRAINT chk_appl_active   CHECK (IsActive IN (0,1))
) ENGINE=InnoDB COMMENT='Job seekers / applicants';

-- 5.2 Applications  (Applicant applies to Job Posting)
CREATE TABLE Applications (
    ApplicationID   INT UNSIGNED  NOT NULL AUTO_INCREMENT,
    JobID           VARCHAR(36)   NOT NULL,
    ApplicantID     INT UNSIGNED  NOT NULL,
    ApplyDate       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    Status          ENUM('Pending','Reviewed','Shortlisted','Rejected','Accepted')
                                  NOT NULL DEFAULT 'Pending',
    CoverLetter     TEXT           NULL,
    Notes           TEXT           NULL,
    -- ── Constraints ──────────────────────────────────────────
    CONSTRAINT pk_applications    PRIMARY KEY (ApplicationID),
    CONSTRAINT uq_appl_job_appl   UNIQUE (JobID, ApplicantID),   -- one app per job
    CONSTRAINT fk_appl_job        FOREIGN KEY (JobID)
        REFERENCES Positions(ID)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_appl_applicant  FOREIGN KEY (ApplicantID)
        REFERENCES Applicants(ApplicantID)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB COMMENT='Application records linking applicants to job postings';


-- ============================================================
--  SECTION 6 – OPTIONAL CONTENT TABLES
-- ============================================================

CREATE TABLE Blogs (
    BlogID      INT UNSIGNED  NOT NULL AUTO_INCREMENT,
    Title       VARCHAR(400)  NOT NULL,
    AuthorName  VARCHAR(200)  NOT NULL,
    PublishDate DATE           NULL,
    Content     LONGTEXT       NULL,
    Tags        VARCHAR(500)   NULL,
    IsPublished TINYINT(1)   NOT NULL DEFAULT 0,
    CreatedAt   DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_blogs PRIMARY KEY (BlogID)
) ENGINE=InnoDB COMMENT='Optional – blog posts about academic careers';

CREATE TABLE News (
    NewsID      INT UNSIGNED  NOT NULL AUTO_INCREMENT,
    Title       VARCHAR(400)  NOT NULL,
    SourceName  VARCHAR(200)  NOT NULL,
    SourceURL   VARCHAR(500)   NULL,
    PublishDate DATE           NULL,
    Summary     TEXT           NULL,
    ID_Country  VARCHAR(10)    NULL,
    CreatedAt   DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_news      PRIMARY KEY (NewsID),
    CONSTRAINT fk_news_ctry FOREIGN KEY (ID_Country)
        REFERENCES Country(ID_Country)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB COMMENT='Optional – academic/university news aggregator';

SET FOREIGN_KEY_CHECKS = 1;
SET @bulk_import_mode = 0;   -- reset; Python import_data.py manages this per-session


-- ============================================================
--  SECTION 7 – INDEXES
--  Strategy: cover the most common query patterns
--  (job search, employer lookup, application status)
-- ============================================================

-- ── Positions ────────────────────────────────────────────
-- Full-text search on job content
CREATE FULLTEXT INDEX ft_positions_title
    ON Positions (JobTitle, Abstract, Keywords);

-- Filter by country + alive status (browse by country)
CREATE INDEX idx_pos_country_alive
    ON Positions (ID_Country, IsAlive);

-- Filter by university (employer's postings)
CREATE INDEX idx_pos_university
    ON Positions (ID_University);

-- Filter by primary position type
CREATE INDEX idx_pos_postype
    ON Positions (ID_Position);

-- Date-range queries (recent / expiring jobs)
CREATE INDEX idx_pos_dateofpost
    ON Positions (DateofPost DESC);

CREATE INDEX idx_pos_deadline
    ON Positions (Deadline);

-- Status + alive  (lifecycle queries)
CREATE INDEX idx_pos_status_alive
    ON Positions (JobStatus, IsAlive);

-- ── University ────────────────────────────────────────────
CREATE FULLTEXT INDEX ft_univ_name
    ON University (UniversityName, ShortName);

CREATE INDEX idx_univ_country
    ON University (ID_Country);

CREATE INDEX idx_univ_status
    ON University (Status);

-- ── Applications ─────────────────────────────────────────
CREATE INDEX idx_appl_job
    ON Applications (JobID);

CREATE INDEX idx_appl_applicant
    ON Applications (ApplicantID);

CREATE INDEX idx_appl_status
    ON Applications (Status);

CREATE INDEX idx_appl_applydate
    ON Applications (ApplyDate DESC);

-- ── PositionsResearchAreas ───────────────────────────────
CREATE INDEX idx_posra_ra
    ON PositionsResearchAreas (ID_ResearchArea);

CREATE INDEX idx_posra_weight
    ON PositionsResearchAreas (ID_ResearchArea, Weight DESC);

-- ── JobPositionType ─────────────────────────────────────
CREATE INDEX idx_jobpt_type
    ON JobPositionType (ID_PositionType);

CREATE INDEX idx_jobpt_weight
    ON JobPositionType (ID_PositionType, Weight DESC);


-- ============================================================
--  END OF FILE 01_schema.sql
-- ============================================================
