# 🎓 AcademicGate - Academic Jobs Database

AcademicGate là một Hệ thống Cơ sở Dữ liệu và Giao diện Web toàn diện được thiết kế để quản lý các tin tuyển dụng học thuật (Academic Jobs), Trường Đại học (Employers), và Hồ sơ Ứng viên (Applicants).

Dự án này được xây dựng với mục tiêu cung cấp một giải pháp quản lý dữ liệu khổng lồ (hơn 40.000 tin tuyển dụng) với hiệu năng cao, bảo mật chặt chẽ thông qua phân quyền (RBAC) và thân thiện với người dùng cuối.

---

## 🌟 Tính năng Nổi bật (Features)

1. **Giao diện Web tương tác (Streamlit):**
   - **Dashboard (`app.py`):** Hiển thị các chỉ số thống kê (KPIs), biểu đồ xu hướng đăng việc làm và phễu ứng tuyển.
   - **Quản lý Trường học (Employers):** Xem, tìm kiếm và thêm mới thông tin các Trường Đại học.
   - **Quản lý Việc làm (Jobs):** Danh sách hàng chục nghìn vị trí (PhD, Postdoc, Lecturer...). Hỗ trợ Nhà tuyển dụng đăng tin mới.
   - **Quản lý Ứng viên (Applicants):** Danh sách chi tiết thông tin ứng viên (Tuổi, Giới tính, Chuyên ngành...).
   - **Theo dõi Hồ sơ (Applications):** Nhà tuyển dụng dễ dàng thay đổi trạng thái đơn nộp (Pending, Accepted, Rejected).

2. **Giả lập Phân quyền (Role-Based Access Control):**
   - **Admin:** Toàn quyền hệ thống.
   - **Employer:** Chỉ được đăng tin và duyệt đơn. Bị chặn xem thông tin nội bộ của hệ thống.
   - **Applicant:** Chỉ được tìm việc và nộp đơn. Giao diện đăng tin tự động bị ẩn.

3. **Gợi ý việc làm Thông minh (Smart Suggest):**
   - Hệ thống đối chiếu Chuyên ngành (`Major`) và Công việc mong muốn (`Wanted_Job`) của ứng viên với hàng ngàn tin tuyển dụng. Sử dụng thuật toán trích xuất từ khóa (Keyword Extraction) của Python để tính điểm và đưa ra Top 10 gợi ý phù hợp nhất cực kỳ nhanh chóng.

4. **Kiến trúc Cơ sở dữ liệu Cứng cáp (MySQL):**
   - Xử lý Business Logic ngay tại Database thông qua **Stored Procedures** và **Triggers**.
   - Tối ưu hóa **Indexing** giúp tăng tốc độ JOIN, Lọc và Sắp xếp trên khối lượng dữ liệu khổng lồ mà không gây trễ web.

---

## 🛠 Công nghệ sử dụng (Tech Stack)
- **Database:** MySQL 8.0+
- **Backend/Frontend:** Python 3.10+, Streamlit
- **Data Processing:** Pandas
- **Fake Data Generator:** Faker

---

## 🚀 Hướng dẫn Cài đặt & Chạy dự án (Setup & Run)

### 1. Cài đặt thư viện
Mở Terminal tại thư mục dự án và chạy:
```bash
pip install -r requirements.txt
pip install faker
```

### 2. Thiết lập Cơ sở dữ liệu (MySQL)
1. Mở MySQL Workbench.
2. Chạy lần lượt các file SQL trong thư mục `schema/` theo đúng thứ tự từ `01` đến `04` để tạo Bảng, Hàm, Index và Phân quyền.
3. Mở file `config.py` và sửa thông tin `DB_CONFIG` (user, password) cho khớp với máy tính của bạn.

### 3. Nạp dữ liệu vào Database
Chạy file import để tự động làm sạch và đẩy dữ liệu từ các file CSV vào MySQL:
```bash
python import_data.py --truncate
```

### 4. Sinh dữ liệu Ứng viên ảo
Tạo hàng loạt hồ sơ ứng viên bằng AI Faker để thử nghiệm:
```bash
python generate_applicants.py
```

### 5. Khởi chạy Giao diện Web
Khởi động hệ thống Web bằng lệnh:
```bash
streamlit run app.py
```
*(Trình duyệt sẽ tự động mở lên tại địa chỉ http://localhost:8501)*

---

## 📂 Cấu trúc thư mục (Folder Structure)
```text
AcaGate/
│
├── app.py                      # Trang chủ Dashboard Streamlit
├── auth.py                     # Module giả lập phân quyền Sidebar
├── database.py                 # Tầng giao tiếp (CRUD) kết nối Python và MySQL
├── config.py                   # Cấu hình DB và đường dẫn file import
├── import_data.py              # Script nạp dữ liệu từ CSV vào MySQL
├── csv_utils.py                # Hàm xử lý lỗi Pandas khi đọc file
├── generate_applicants.py      # Script tự động thêm cột và sinh ứng viên ảo
├── clean_applicants.py         # Script dọn dẹp dữ liệu cũ bị lỗi
│
├── pages/                      # Các trang menu của Streamlit
│   ├── 1_🏢_Employers.py
│   ├── 2_📋_Jobs.py
│   ├── 3_👤_Applicants.py
│   └── 4_📨_Applications.py
│
├── raw data/                   # Thư mục chứa các file CSV gốc
└── schema/                     # Mã nguồn CSDL MySQL (Bảng, Hàm, Index, Bảo mật)
```

**Chúc bạn đạt điểm A+ với đồ án này! 🎓**
