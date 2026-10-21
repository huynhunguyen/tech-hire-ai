# Kịch bản demo – TechHire AI

Thời lượng: khoảng 10–12 phút. Số liệu bên dưới ứng với dữ liệu mặc định (seed cố định), nên mỗi lần chạy đều giống nhau.

## Chuẩn bị

1. Xóa `data\audit\audit_log.jsonl` (nếu có) để nhật ký bắt đầu trống.
2. Mở terminal 1 và chạy app:
   ```powershell
   cd techhire-ai
   .venv\Scripts\python -m streamlit run app.py
   ```
3. Mở sẵn terminal 2 ở thư mục `techhire-ai` cho phần 4.

## Phần 1 – Khu vực 1: Kiểm toán dữ liệu (Điều 10), khoảng 3 phút

| Thao tác | Nói gì |
|---|---|
| Chỉ vào hộp đỏ **"CẢNH BÁO THIÊN KIẾN"** và DIR = **0,44** | "Dữ liệu tuyển dụng quá khứ có tỷ lệ chọn nữ chỉ bằng 44% so với nam, dưới ngưỡng 0,80. Đây chính là kịch bản của Amazon 2018." |
| Cuộn tới mục **1.2** | "Bước 1: ẩn giới tính, tuổi, sắc tộc khỏi đầu vào mô hình. Bước 2: cân bằng lại trọng số mẫu, sau đó DIR có trọng số = 1,00." |
| Mục **1.3**: so sánh hai thẻ mô hình | "Mô hình chưa tuân thủ không chỉ học lại mà còn khuếch đại thiên kiến: DIR từ 0,44 xuống 0,15. Chỉ cần đổi giới tính là 34% kết quả bị đảo. Mô hình đã tuân thủ đạt DIR 0,88, tỷ lệ đảo 0%." |
| Chỉ vào hộp xanh về độ chính xác | "Độ chính xác giảm khoảng 5 điểm, nhưng được đo trên nhãn lịch sử vốn thiên lệch, nên phần giảm là do mô hình từ chối lặp lại phân biệt đối xử." |
| Mở expander **"Bảng phân tích chi tiết (ablation)"** | "Chỉ ẩn cột vẫn trượt ngưỡng về sắc tộc (0,73) vì có biến đại diện (proxy), nên bước cân bằng trọng số là bắt buộc." |

## Phần 2 – Khu vực 2: Đánh giá và giải thích (Điều 13, GDPR 22), khoảng 3 phút

| Thao tác | Nói gì |
|---|---|
| Chọn ứng viên **C-00002** | "HR chỉ thấy các thuộc tính năng lực; giới tính, tuổi, sắc tộc đã bị ẩn. Hệ thống chấm 6,7%, khuyến nghị 'Cần xem xét thêm', thời gian xử lý dưới 2 giây." |
| Chỉ vào biểu đồ thác nước | "Mỗi thanh cho biết một thuộc tính cộng hay trừ bao nhiêu điểm, ví dụ điểm kỹ năng 56/100 trừ 11,2 điểm. Hệ thống chỉ giải thích từng hồ sơ, không công bố trọng số toàn cục, nhờ đó bảo vệ bí mật kinh doanh." |
| Chỉ vào ô **lời giải thích cho ứng viên** | "Đây là đoạn văn HR gửi cho ứng viên, đáp ứng quyền được giải thích theo GDPR Điều 22." |
| Mở expander **"Chế độ kiểm toán viên"** | "Cùng một hồ sơ, chỉ đổi giới tính: mô hình chưa tuân thủ giảm từ 25,7% xuống 4,7%, còn mô hình đã tuân thủ giữ nguyên 6,7%." |
| Chọn **"Nhập hồ sơ mới"**, nhập **Điểm kỹ năng = 500**, bấm *Đánh giá hồ sơ* | "Lớp kiểm tra đầu vào từ chối dữ liệu bất thường, theo yêu cầu bền vững của Điều 15." Sau đó quay lại **"Hồ sơ trong tập đánh giá"** và chọn lại C-00002. |

## Phần 3 – Khu vực 3: HR phê duyệt và nhật ký (Điều 14, 12), khoảng 3 phút

Ứng viên C-00002, AI khuyến nghị "Cần xem xét thêm".

1. **Hệ thống chặn việc duyệt cho có.** Lần lượt thử:

   | Mã HR | Lý do | Ô xác nhận | Kết quả |
   |---|---|---|---|
   | `HR-999` | `Đồng ý` | Không tick | Bị chặn với 3 lỗi: không có quyền, chưa xác nhận, lý do quá ngắn |
   | `HR-001` | `Tôi đồng ý hoàn toàn với đề xuất mà hệ thống AI đưa ra.` | Tick | Bị chặn: lý do không nêu căn cứ năng lực |
   | `HR-001` | `Kinh nghiệm tốt nhưng ứng viên là phụ nữ nên không phù hợp.` | Tick | Bị chặn: viện dẫn thuộc tính được bảo vệ |

2. **Quyền phủ quyết (Override).** Mã `HR-001`, chọn **"Mời phỏng vấn"**: cảnh báo phủ quyết hiện ra. Nhập lý do:
   > Ứng viên có 8,5 năm kinh nghiệm thực tế dù điểm kỹ năng chỉ 56, cần phỏng vấn trực tiếp để đánh giá năng lực chuyên môn.

   Tick ô xác nhận rồi bấm *Xác nhận quyết định*. Màn hình báo thành công kèm mã băm.
3. Cuộn xuống **bảng nhật ký**: "Mỗi quyết định ghi đủ thời gian, mã HR, điểm AI, quyết định, cờ Override, lý do và phiên bản
   mô hình. Nhật ký không lưu giới tính, tuổi hay sắc tộc."
4. Chọn thêm 1–2 ứng viên khác ở Khu vực 2 và ghi quyết định. Mỗi lần dùng lý do **khác nhau**, có nhắc tới kinh nghiệm,
   kỹ năng, phỏng vấn hoặc chứng chỉ; hệ thống chặn lý do sao chép.

## Phần 4 – Bảo mật nhật ký (Điều 12), khoảng 1,5 phút

Ở terminal 2:
```powershell
.venv\Scripts\python scripts\simulate_log_tampering.py
```
Quay lại trình duyệt và bấm **F5**: Khu vực 3 hiện **"PHÁT HIỆN CAN THIỆP NHẬT KÝ: Dòng 1: nội dung bản ghi đã bị sửa đổi"**.
Nói: "Nếu một người nội bộ sửa quyết định trong file, chuỗi băm SHA-256 phát hiện ngay."

Khôi phục nhật ký gốc:
```powershell
.venv\Scripts\python scripts\simulate_log_tampering.py --restore
```

## Phần 5 (tùy chọn) – Dữ liệu bị đầu độc (Điều 15), khoảng 1 phút

Dừng app ở terminal 1 (`Ctrl + C`), rồi chạy:
```powershell
.venv\Scripts\python scripts\generate_synthetic_data.py --output data\raw\poisoned.csv --inject-invalid 150
$env:TECHHIRE_DATASET_PATH = "data\raw\poisoned.csv"; .venv\Scripts\python -m streamlit run app.py
```
Khu vực 1 báo **150 bản ghi bị cách ly**. Nói: "Đây là lớp phòng thủ đầu tiên, chỉ bắt được dữ liệu sai miền giá trị; kiểu
đầu độc tinh vi như đảo nhãn vẫn lọt qua, và đó là hạn chế nhóm nêu trong báo cáo."

Quay về dữ liệu mặc định: `Remove-Item Env:TECHHIRE_DATASET_PATH`, rồi chạy lại app.

## Kết bài (30 giây)

"Mô-đun nhận diện cảm xúc bị loại bỏ ngay từ thiết kế theo Điều 5. Mô-đun chấm hồ sơ còn lại đáp ứng 4 trụ cột: Điều 10, 13,
14 và 12. AI chỉ tham mưu, con người quyết định và chịu trách nhiệm, và mọi quyết định đều truy vết được."
