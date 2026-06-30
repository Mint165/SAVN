# Tài Liệu Ý Tưởng & Phong Cách Dự Án HeartBits

## 1. Tổng Quan Ý Tưởng (Project Overview)
- **Tên dự án**: HeartBits Dashboard
- **Mục tiêu**: Xây dựng một ứng dụng web chuyên nghiệp (Dashboard) hỗ trợ người dùng theo dõi sức khỏe tim mạch và dự đoán sớm nguy cơ đột quỵ dựa trên các chỉ số y tế và bộ quy tắc triệu chứng FAST.
- **Đối tượng sử dụng**: Người dùng cá nhân cần theo dõi sức khỏe hàng ngày, bác sĩ hoặc người nhà bệnh nhân.

## 2. Phong Cách Thiết Kế (UI/UX Style)
- **Chủ đề chính**: Dark Mode (Nền tối) mang lại cảm giác hiện đại, chuyên nghiệp và làm nổi bật các dữ liệu quan trọng.
- **Hiệu ứng trực quan**: 
  - **Glassmorphism**: Các thẻ nội dung (Card) sử dụng hiệu ứng kính mờ (backdrop-filter: blur), viền mỏng và nền bán trong suốt để tạo chiều sâu.
  - **Điểm nhấn màu sắc (Accents)**: Sử dụng các gam màu phản quang (Neon) như Đỏ (Nguy hiểm/Cảnh báo), Xanh dương (Thông tin chuẩn), Vàng cam (Cảnh báo mức độ vừa) trên nền tối `var(--bg-dark): #0F172A`.
  - **Typography**: Phông chữ `Inter` thanh lịch, hiện đại, tối ưu cho việc đọc số liệu trên màn hình kỹ thuật số.

## 3. Các Tính Năng Cốt Lõi (Core Features)
1. **Quản lý Tài Khoản & Hồ Sơ**: Hệ thống đăng nhập/đăng ký bằng SQLite. Trang cá nhân (Profile) hiển thị hồ sơ người dùng và **Chuỗi tập luyện (Streak)** được biểu tượng bởi ngọn lửa (chuỗi tăng 1 khi tập luyện mỗi ngày và về 0 nếu bị ngắt quãng).
2. **Trang Bảng Điều Khiển (Dashboard)**: 
   - Không có mục Patient (Bệnh nhân).
   - Tóm tắt thông tin sức khỏe mới nhất.
   - Hiển thị các biểu đồ theo dõi như đã định: Biểu đồ biến động Huyết áp (Tâm thu/Tâm trương) qua các ngày, và Biểu đồ theo dõi Nguy cơ Đột quỵ (Tính theo %).
3. **Mục Tập Luyện (Exercise)**:
   - Các bài tập hằng ngày để nâng cao sức khỏe tim mạch và huyết áp.
   - Hướng dẫn dễ hiểu, hình ảnh minh họa rõ ràng.
   - Tích hợp nút "Tôi đã tập luyện hôm nay" để duy trì và tăng chuỗi tập luyện.
4. **Mục Báo Cáo (Report)**:
   - Tổng kết sức khỏe của người dùng thông qua dữ liệu nhập hằng ngày và biểu đồ.
   - Đưa ra lời khuyên về chế độ ăn uống, nghỉ ngơi, và tập luyện dựa trên thể trạng.
5. **Mục Lịch (Schedule)**:
   - Cho phép nhập lịch uống thuốc hoặc lịch khám sức khỏe.
   - Giao diện hiển thị trực quan, mượt mà được thiết kế tương tự **Lịch của iPhone**.
6. **Thu Thập Dữ Liệu Hàng Ngày**: Form nhập liệu trực quan, cho phép ghi nhận các chỉ số như Tuổi, BMI, Glucose, Huyết áp, và tự đánh giá các triệu chứng FAST.
7. **Hệ Thống Cảnh Báo "Giờ Vàng Cấp Cứu"**:
   - Khi mô hình AI dự đoán nguy cơ đột quỵ ở mức **RẤT CAO** ($\ge 70\%$).
   - Kích hoạt màn hình làm mờ (Overlay Blur).
   - Hiển thị đồng hồ đếm ngược vòng tròn bắt đầu từ 3 giờ (03:00:00). Sau 3 giây, đồng hồ tự thu nhỏ về góc màn hình để nhắc nhở khẩn cấp mà không cản trở thao tác.

## 4. Công Nghệ Sử Dụng (Tech Stack)
- **Backend**: Python (FastAPI), SQLAlchemy (SQLite Database).
- **Machine Learning**: Scikit-learn (RandomForest), Joblib.
- **Frontend**: HTML5, CSS3 (Vanilla), JavaScript, Jinja2 Templates.
- **Thư viện đồ họa**: Chart.js, FontAwesome.

## 5. Lưu Ý Về Giao Diện (UI/UX References)
- **Giao diện và Màu sắc**: Toàn bộ giao diện, màu sắc, mục menu và các hiệu ứng animation sẽ được copy/sao chép theo đúng trang web tham khảo mà người dùng đã gửi.
- Thiết kế lịch tuân theo giao diện của **Apple iPhone Calendar**.
- Các điểm nhấn tương tác (Nút tập luyện, chuỗi ngọn lửa) cần sinh động.
