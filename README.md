# TechHire AI – Sàng lọc hồ sơ ứng viên tuân thủ EU AI Act

Proof-of-Concept minh họa quy trình tuân thủ **EU AI Act** và **GDPR** cho một hệ thống AI tuyển dụng thuộc nhóm
**rủi ro cao** (Phụ lục III, Mục 4(a)). Hệ thống chỉ **tham mưu**; quyết định cuối cùng luôn do nhân sự (HR) đưa ra.

| Tài liệu | Nội dung |
|---|---|
| [docs/SYSTEM_DESIGN.md](docs/SYSTEM_DESIGN.md) | Kiến trúc, cấu trúc thư mục, dữ liệu, ánh xạ điều luật, bảo mật, kết quả thực nghiệm, hạn chế |
| [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md) | Kịch bản trình bày từng bước |

## Cài đặt

Yêu cầu: Python 3.10+ (đã kiểm thử với 3.11), chạy hoàn toàn trên CPU.

```powershell
cd techhire-ai
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

Trên macOS / Linux, thay `.venv\Scripts\python` bằng `.venv/bin/python`.

## Chạy

```powershell
.venv\Scripts\python -m streamlit run app.py
```

Mở http://localhost:8501.

| Biến môi trường | Mặc định | Ý nghĩa |
|---|---|---|
| `TECHHIRE_DATASET_PATH` | (không đặt) – dùng dữ liệu mô phỏng | File CSV đầu vào cùng lược đồ |
| `TECHHIRE_AUDIT_LOG_PATH` | `data/audit/audit_log.jsonl` | File nhật ký kiểm toán |

## Kiểm thử

```powershell
.venv\Scripts\python -m pytest
```
