# Hệ Sinh Thái POD Idea Generator (Công cụ Tìm Ý Tưởng Bán Áo)

Thư mục này chứa các đoạn mã tự động hoá quy trình "Spy" đối thủ và tìm kiếm ý tưởng thiết kế ngách thể thao Mỹ.

## 1. Công cụ quét mẫu mới BreakingT (`breakingt_scraper.py`)

Đoạn mã này tự động lấy 100 sản phẩm mới lên kệ của BreakingT và hiển thị chúng dưới dạng lưới (Pinterest-style) trực tiếp trên máy của bạn để lướt xem cực nhanh mỗi sáng.

### Cách chạy thủ công bằng tay:
1. Mở ứng dụng **Terminal** trên Mac.
2. Di chuyển vào thư mục chứa công cụ bằng lệnh sau:
   ```bash
   cd ~/Desktop/pod-research-tools
   ```
3. Khởi chạy file code:
   ```bash
   python3 breakingt_scraper.py
   ```
4. Bảng điều khiển (Dashboard) Ý tưởng sẽ tự động bật lên trên trình duyệt web của bạn!

### Cách đặt lịch để máy Mac tự chạy mỗi sáng (Ví dụ: 8h00 mỗi ngày):
Nếu bạn muốn ngủ dậy là đã có danh sách thiết kế sẵn sàng, hãy gài lịch tự động cho máy Mac (Cron job):

1. Mở ứng dụng **Terminal**.
2. Gõ `crontab -e` và nhấn Enter (Để mở phần cài đặt lịch).
3. Bấm phím `i` trên bàn phím để chuyển qua chế độ gõ chữ (Insert mode).
4. Dán dòng này vào:
   ```bash
   0 8 * * * /usr/bin/python3 /Users/mac/Desktop/pod-research-tools/breakingt_scraper.py
   ```
5. Bấm phím `Esc` để thoát chế độ gõ chữ.
6. Gõ `:wq` và nhấn Enter để lưu lại và thoát.

*Từ nay, cứ đều đặn 8h00 sáng, danh sách mẫu áo mới sẽ tự được tải về máy tính để bạn xem rồi nhé!*
