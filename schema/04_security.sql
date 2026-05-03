-- ============================================================
--  AcademicGate Database
--  FILE 04 — SECURITY
--  Contents: Roles & Permissions (Section 12)
--            + Performance Notes (Section 13)
--            + Backup & Recovery (Section 14)
--  Requires: Run LAST – after 01, 02, 03
--  Execute with DBA / root privileges
--  MySQL 8.0+
-- ============================================================
--
--  PYTHON IMPORT INTEGRATION
--  ─────────────────────────
--  The Python import script (import_data.py) connects with the credentials
--  defined in config.py (DB_CONFIG).  Grant that user 'role_importer'
--  so it has only the permissions it needs and nothing more.
--
--  After import finishes, call the maintenance procedure:
--    CALL sp_refresh_university_counts();
-- ============================================================
-- ============================================================

USE AcademicGateDB;

-- ============================================================
--  SECTION 12 – SECURITY: ROLES & PERMISSIONS
-- ============================================================

-- NOTE: Execute as a DBA / root user.
--       Adjust host patterns to match your deployment environment.

-- 12.1  Create roles
CREATE ROLE IF NOT EXISTS 'role_admin';
CREATE ROLE IF NOT EXISTS 'role_employer';
CREATE ROLE IF NOT EXISTS 'role_applicant';
CREATE ROLE IF NOT EXISTS 'role_readonly';
-- role_importer: used exclusively by the Python import pipeline (import_data.py)
CREATE ROLE IF NOT EXISTS 'role_importer';

-- 12.2  Admin role – full access to all tables
GRANT ALL PRIVILEGES ON AcademicGateDB.* TO 'role_admin';

-- 12.3  Employer role – manage own postings and view applications
GRANT SELECT, INSERT, UPDATE
    ON AcademicGateDB.Positions        TO 'role_employer';
GRANT SELECT
    ON AcademicGateDB.Applications     TO 'role_employer';
GRANT EXECUTE
    ON PROCEDURE AcademicGateDB.sp_post_job           TO 'role_employer';
GRANT EXECUTE
    ON PROCEDURE AcademicGateDB.sp_close_job          TO 'role_employer';
GRANT EXECUTE
    ON PROCEDURE AcademicGateDB.sp_update_application_status TO 'role_employer';
GRANT SELECT
    ON AcademicGateDB.vw_active_jobs       TO 'role_employer';
GRANT SELECT
    ON AcademicGateDB.vw_employer_summary  TO 'role_employer';
GRANT SELECT
    ON AcademicGateDB.vw_application_summary TO 'role_employer';

-- 12.4  Applicant role – search jobs and manage own applications
GRANT SELECT
    ON AcademicGateDB.vw_active_jobs       TO 'role_applicant';
GRANT SELECT, INSERT
    ON AcademicGateDB.Applications     TO 'role_applicant';
GRANT SELECT, INSERT, UPDATE
    ON AcademicGateDB.Applicants       TO 'role_applicant';
GRANT EXECUTE
    ON PROCEDURE AcademicGateDB.sp_apply_for_job  TO 'role_applicant';
GRANT EXECUTE
    ON PROCEDURE AcademicGateDB.sp_search_jobs    TO 'role_applicant';

-- 12.5  Read-only role – public browsing / reporting
GRANT SELECT
    ON AcademicGateDB.vw_active_jobs          TO 'role_readonly';
GRANT SELECT
    ON AcademicGateDB.vw_jobs_by_country      TO 'role_readonly';
GRANT SELECT
    ON AcademicGateDB.vw_jobs_by_researcharea TO 'role_readonly';
GRANT SELECT
    ON AcademicGateDB.vw_jobs_by_positiontype TO 'role_readonly';
GRANT SELECT
    ON AcademicGateDB.PositionType        TO 'role_readonly';
GRANT SELECT
    ON AcademicGateDB.ResearchArea        TO 'role_readonly';
GRANT SELECT
    ON AcademicGateDB.Country             TO 'role_readonly';
GRANT SELECT
    ON AcademicGateDB.Continents          TO 'role_readonly';
GRANT EXECUTE
    ON PROCEDURE AcademicGateDB.sp_search_jobs TO 'role_readonly';

-- 12.6  Importer role – used by the Python CSV import pipeline
--        Needs INSERT on all 8 source tables and EXECUTE on the
--        post-import counter refresh procedure.
GRANT INSERT, SELECT
    ON AcademicGateDB.Continents              TO 'role_importer';
GRANT INSERT, SELECT
    ON AcademicGateDB.Country                 TO 'role_importer';
GRANT INSERT, SELECT
    ON AcademicGateDB.PositionType            TO 'role_importer';
GRANT INSERT, SELECT
    ON AcademicGateDB.ResearchArea            TO 'role_importer';
GRANT INSERT, SELECT
    ON AcademicGateDB.University              TO 'role_importer';
GRANT INSERT, SELECT
    ON AcademicGateDB.Positions               TO 'role_importer';
GRANT INSERT, SELECT
    ON AcademicGateDB.PositionsResearchAreas  TO 'role_importer';
GRANT INSERT, SELECT
    ON AcademicGateDB.JobPositionType         TO 'role_importer';
GRANT EXECUTE
    ON PROCEDURE AcademicGateDB.sp_refresh_university_counts TO 'role_importer';
-- Needed for TRUNCATE (when --truncate flag is used)
GRANT DROP
    ON AcademicGateDB.*                       TO 'role_importer';

-- 12.7  Sample user accounts (change passwords before production!)
-- CREATE USER IF NOT EXISTS 'admin_user'@'localhost'     IDENTIFIED BY 'StrongP@ss#01!';
-- CREATE USER IF NOT EXISTS 'employer_user'@'%'          IDENTIFIED BY 'StrongP@ss#02!';
-- CREATE USER IF NOT EXISTS 'applicant_user'@'%'         IDENTIFIED BY 'StrongP@ss#03!';
-- CREATE USER IF NOT EXISTS 'report_reader'@'localhost'  IDENTIFIED BY 'StrongP@ss#04!';
-- CREATE USER IF NOT EXISTS 'importer_user'@'localhost'  IDENTIFIED BY 'StrongP@ss#05!';

-- GRANT 'role_admin'    TO 'admin_user'@'localhost';
-- GRANT 'role_employer' TO 'employer_user'@'%';
-- GRANT 'role_applicant'TO 'applicant_user'@'%';
-- GRANT 'role_readonly' TO 'report_reader'@'localhost';
-- GRANT 'role_importer' TO 'importer_user'@'localhost';

-- SET DEFAULT ROLE 'role_admin'     TO 'admin_user'@'localhost';
-- SET DEFAULT ROLE 'role_employer'  TO 'employer_user'@'%';
-- SET DEFAULT ROLE 'role_applicant' TO 'applicant_user'@'%';
-- SET DEFAULT ROLE 'role_readonly'  TO 'report_reader'@'localhost';
-- SET DEFAULT ROLE 'role_importer'  TO 'importer_user'@'localhost';

FLUSH PRIVILEGES;


-- ============================================================
--  SECTION 13 – PERFORMANCE OPTIMISATION NOTES
--  (Embedded as SQL comments / configuration guidance)
-- ============================================================

/*
═══════════════════════════════════════════════════════════════
  PERFORMANCE OPTIMISATION RECOMMENDATIONS
═══════════════════════════════════════════════════════════════

1. InnoDB Buffer Pool
   ─────────────────
   The JobPositionType table alone holds 1.6 M rows.
   Set the buffer pool to at least 2 GB on production:

     SET GLOBAL innodb_buffer_pool_size = 2147483648;   -- 2 GB

   Add to my.cnf (permanent):
     [mysqld]
     innodb_buffer_pool_size      = 4G
     innodb_buffer_pool_instances = 4

2. Query Cache / Optimizer
   ───────────────────────
   - Use EXPLAIN / EXPLAIN ANALYZE on every stored procedure query.
   - For sp_search_jobs, ensure the FULLTEXT index is hit:
       EXPLAIN SELECT ... WHERE MATCH(JobTitle,...) AGAINST(? IN BOOLEAN MODE);

3. Partitioning  (for Positions at scale)
   ──────────────────────────────────────────
   Partition by RANGE on DateofPost (yearly partitions):

     ALTER TABLE Positions
     PARTITION BY RANGE (YEAR(DateofPost)) (
         PARTITION p2020 VALUES LESS THAN (2021),
         PARTITION p2021 VALUES LESS THAN (2022),
         PARTITION p2022 VALUES LESS THAN (2023),
         PARTITION p2023 VALUES LESS THAN (2024),
         PARTITION p2024 VALUES LESS THAN (2025),
         PARTITION p_future VALUES LESS THAN MAXVALUE
     );

4. Archiving Expired Rows
   ───────────────────────
   Move expired jobs to an archive table monthly to keep
   Positions lean. Use the sp_expire_overdue_jobs procedure
   in a scheduled event:

     CREATE EVENT evt_daily_expire
     ON SCHEDULE EVERY 1 DAY
     STARTS CURRENT_TIMESTAMP
     DO CALL sp_expire_overdue_jobs(@n);

5. Connection Pooling
   ───────────────────
   - max_connections = 200 (web tier uses pooled connections)
   - Use ProxySQL or application-level pooling (HikariCP / pgBouncer).

6. Slow Query Log
   ───────────────
     SET GLOBAL slow_query_log    = ON;
     SET GLOBAL long_query_time   = 1;          -- flag queries > 1 s
     SET GLOBAL slow_query_log_file = '/var/log/mysql/slow.log';
*/


-- ============================================================
--  SECTION 14 – BACKUP & RECOVERY PROCEDURES
-- ============================================================

/*
═══════════════════════════════════════════════════════════════
  BACKUP & RECOVERY STRATEGY
═══════════════════════════════════════════════════════════════

FULL LOGICAL BACKUP  (daily – off-peak hours)
─────────────────────────────────────────────
  mysqldump \
    --single-transaction \
    --routines \
    --triggers \
    --events \
    --set-gtid-purged=OFF \
    -u root -p AcademicGateDB \
    | gzip > /backups/academicgate_$(date +%F).sql.gz

INCREMENTAL BACKUP  (via binary logs – every hour)
───────────────────────────────────────────────────
  1. Enable binary logging in my.cnf:
       log_bin           = /var/log/mysql/mysql-bin.log
       binlog_format     = ROW
       expire_logs_days  = 14
       server_id         = 1

  2. Flush logs hourly (cron):
       mysqladmin -u root -p flush-logs

  3. Archive bin-logs to object storage (S3 / GCS) hourly.

POINT-IN-TIME RECOVERY
───────────────────────
  1. Restore the latest full backup:
       gunzip < /backups/academicgate_2025-01-01.sql.gz \
       | mysql -u root -p AcademicGateDB

  2. Replay binary logs up to the desired moment:
       mysqlbinlog --stop-datetime="2025-01-02 14:30:00" \
           /var/log/mysql/mysql-bin.000042 \
           | mysql -u root -p AcademicGateDB

PHYSICAL BACKUP  (InnoDB hot backup via Percona XtraBackup)
────────────────────────────────────────────────────────────
  xtrabackup --backup --target-dir=/backups/xb_$(date +%F) \
             --user=root --password=...
  xtrabackup --prepare --target-dir=/backups/xb_2025-01-01
  # Restore: copy files to MySQL datadir, fix permissions

BACKUP SCHEDULE
───────────────
  • Daily full  – retained 30 days
  • Weekly full – retained 12 weeks
  • Binary logs – retained 14 days
  • Off-site (S3/tape) – retained 1 year

TESTING
───────
  Perform monthly restore drills on a staging server.
  Validate record counts and stored-procedure execution
  post-restore before sign-off.
*/


-- ============================================================
--  END OF FILE 04_security.sql
-- ============================================================
-- To verify full installation:
--   SHOW TABLES;
--   SELECT TABLE_NAME, TABLE_ROWS, ENGINE
--   FROM   information_schema.TABLES
--   WHERE  TABLE_SCHEMA = 'AcademicGateDB'
--   ORDER BY TABLE_NAME;
-- ============================================================
