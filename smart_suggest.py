"""
smart_suggest.py
================
Smart Job Recommendations using Sentence-Transformers (Semantic Search).

Sử dụng mô hình all-MiniLM-L6-v2 để encode hồ sơ ứng viên và tiêu đề công việc
thành vector, sau đó tìm kiếm bằng cosine similarity.

Workflow:
    1. Encode tất cả job đang mở thành vector (lưu cache trên disk)
    2. Encode hồ sơ ứng viên (Major + Wanted_Job) thành vector
    3. Tính cosine similarity → trả về Top-N job phù hợp nhất
"""

import os
import numpy as np
import database as db

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")
EMBEDDINGS_FILE = os.path.join(CACHE_DIR, "job_embeddings.npz")
MODEL_NAME = "all-MiniLM-L6-v2"

# Singleton model
_model = None


def get_model():
    """Load model (chỉ tải 1 lần, dùng lại cho mọi request)."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def build_job_index(force=False):
    """
    Encode tất cả job đang mở thành embedding vectors.
    
    - Lần đầu: encode ~41K jobs (~30s), lưu vào .cache/job_embeddings.npz
    - Các lần sau: đọc từ cache (~1s)
    - force=True: bắt buộc encode lại (khi có job mới)
    
    Returns:
        (embeddings: np.ndarray, job_ids: list[str])
    """
    os.makedirs(CACHE_DIR, exist_ok=True)

    # Nếu có cache và không bắt buộc rebuild → đọc từ cache
    if not force and os.path.exists(EMBEDDINGS_FILE):
        data = np.load(EMBEDDINGS_FILE, allow_pickle=True)
        return data["embeddings"], data["job_ids"].tolist()

    # Lấy tất cả job đang mở
    jobs = db.execute_query("""
        SELECT  p.ID, 
                p.JobTitle, 
                COALESCE(p.Abstract, '') AS Abstract, 
                COALESCE(p.Keywords, '') AS Keywords
        FROM    Positions p
        WHERE   p.IsAlive = 1
    """)

    if not jobs:
        return np.array([]), []

    # Tạo text tổng hợp cho mỗi job (title + abstract + keywords)
    texts = [
        f"{j['JobTitle']} {j['Abstract']} {j['Keywords']}"
        for j in jobs
    ]
    job_ids = [j["ID"] for j in jobs]

    # Encode bằng sentence-transformers
    model = get_model()
    print(f"Encoding {len(texts)} jobs with AI...")
    embeddings = model.encode(texts, show_progress_bar=True, batch_size=256)

    # Lưu cache
    np.savez(EMBEDDINGS_FILE, embeddings=embeddings, job_ids=np.array(job_ids))
    print(f"Saved embeddings cache to {EMBEDDINGS_FILE}")

    return embeddings, job_ids


def recommend(applicant_id: int, limit: int = 10) -> list[dict]:
    """
    Tìm Top-N công việc phù hợp nhất cho ứng viên bằng Semantic Search.

    Parameters
    ----------
    applicant_id : int
        Mã ứng viên.
    limit : int
        Số lượng kết quả trả về (mặc định 10).

    Returns
    -------
    list[dict]
        Danh sách job kèm score, sắp xếp theo độ phù hợp giảm dần.
    """
    from sentence_transformers import util

    # 1. Lấy thông tin ứng viên
    applicant = db.get_applicant(applicant_id)
    if not applicant:
        return []

    profile_text = f"{applicant.get('Major', '')} {applicant.get('Wanted_Job', '')}"
    if not profile_text.strip():
        return []

    # 2. Lấy job embeddings (từ cache hoặc build mới)
    job_embeddings, job_ids = build_job_index()
    if len(job_embeddings) == 0:
        return []

    # 3. Encode hồ sơ ứng viên
    model = get_model()
    profile_embedding = model.encode(profile_text)

    # 4. Tính cosine similarity
    scores = util.cos_sim(profile_embedding, job_embeddings)[0]

    # 5. Lấy top-k indices
    top_indices = scores.argsort(descending=True)[:limit]

    # 6. Lấy chi tiết job từ DB (1 query duy nhất)
    top_job_ids = [job_ids[idx] for idx in top_indices]
    top_scores = [round(scores[idx].item(), 4) for idx in top_indices]

    if not top_job_ids:
        return []

    placeholders = ", ".join(["%s"] * len(top_job_ids))
    jobs = db.execute_query(
        f"""
        SELECT  p.ID, p.JobTitle, p.NonHTMLAdvertisement, 
                u.UniversityName, c.CountryName
        FROM    Positions p
        LEFT JOIN University u ON p.ID_University = u.ID_University
        LEFT JOIN Country    c ON p.ID_Country    = c.ID_Country
        WHERE   p.ID IN ({placeholders})
        """,
        top_job_ids,
    )

    # Map job_id → job detail
    job_map = {j["ID"]: j for j in jobs}

    # 7. Build kết quả với score, giữ nguyên thứ tự xếp hạng
    results = []
    for job_id, score in zip(top_job_ids, top_scores):
        if job_id in job_map:
            job = job_map[job_id]
            job["score"] = score
            results.append(job)

    return results
