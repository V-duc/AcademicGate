# AcademicGate - AI-Powered Academic Jobs Platform

AcademicGate is a comprehensive Database System and Web Application designed to manage academic job postings, universities (employers), and applicant profiles.

This project is built to handle a massive dataset (over 40,000 job postings) with high performance, strict role-based access control (RBAC), and an AI-driven semantic recommendation engine.

---

## 🌟 Core Features

1. **Interactive Web Dashboard (Streamlit):**
   - **Dashboard (`app.py`):** Displays statistics, KPIs, trend charts for job postings, and application funnel metrics.
   - **Employers Management:** View, search, and add new universities. Uses server-side pagination for optimal performance.
   - **Jobs Management:** Browse tens of thousands of academic positions. Employers can post new jobs. Includes toggles for active/closed jobs and dynamic pagination.
   - **Applicants Management:** View applicant details (Age, Nationality, Major, etc.). Restricted to Admins and Employers.
   - **Applications Tracking:** Track and update application statuses (Pending, Accepted, Rejected).

2. **Role-Based Access Control (RBAC):**
   - **Admin:** Full system access.
   - **Employer:** Can post jobs, view applicants, and update application statuses. Restricted from candidate tools.
   - **Applicant:** Can apply for jobs and use the AI Smart Suggest tool. Cannot view other applicants or employer-specific tools.

3. **AI Smart Suggest (Semantic Search):**
   - Integrates `sentence-transformers` (`all-MiniLM-L6-v2`) to perform semantic matching.
   - Replaces traditional keyword search (e.g., matching "AI" to "Artificial Intelligence").
   - Utilizes `.npz` caching to ensure sub-second recommendation response times even with 40,000+ jobs.

4. **Robust Database Architecture (MySQL):**
   - Business logic runs at the database layer via **Stored Procedures** and **Triggers**.
   - Highly optimized **Indexing** structure ensures fast JOINs, filtering, and sorting without degrading web performance.
   - Uses `LOAD DATA LOCAL INFILE` for lightning-fast initial data seeding.

---

## 🛠 Tech Stack
- **Database:** MySQL 8.0+
- **Backend/Frontend:** Python 3.10+, Streamlit
- **Data Processing & AI:** Pandas, `sentence-transformers`, NumPy

---

## 🚀 Setup & Installation

### 1. Install Dependencies
Open a Terminal in the project directory and run:
```bash
pip install -r requirements.txt
```
*(Note: To enable fast MySQL data loading, ensure the database user has `local_infile=1` privileges).*

### 2. Configure Database
1. Create a MySQL database and run the SQL scripts in the `schema/` folder sequentially (`01_schema.sql` to `04_security.sql`).
2. Provide your database password to the system by either modifying `config.py` or setting an OS Environment Variable `DB_PASSWORD`.

### 3. High-Speed Data Import
Run the fast import script to ingest data from the CSV files into MySQL. This script uses `LOAD DATA LOCAL INFILE` to process tens of thousands of rows in seconds:
```bash
python fast_import.py
```

### 4. Run the Web Interface
Start the Streamlit application:
```bash
streamlit run app.py
```

---

## 📁 Folder Structure
```text
AcaGate/
│
├── app.py                      # Main Streamlit Dashboard entry point
├── auth.py                     # Authentication and RBAC Sidebar module
├── database.py                 # Core CRUD layer connecting Python and MySQL
├── config.py                   # Database configuration
├── fast_import.py              # High-speed data ingestion script
├── smart_suggest.py            # AI Semantic Recommendation Engine
│
├── pages/                      # Streamlit application pages
│   ├── 1_Employers.py          # Employer and university management
│   ├── 2_Jobs.py               # Job board and application portal
│   ├── 3_Applicants.py         # Candidate tracking system
│   └── 4_Applications.py       # Application status workflow
│
├── raw data/                   # Original CSV data sets for initial seeding
├── schema/                     # MySQL DDL (Tables, Views, Procedures, Security)
└── .cache/                     # Generated AI embeddings (auto-created)
```