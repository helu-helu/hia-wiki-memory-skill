# 🤖 Hướng dẫn cấp quyền Bộ nhớ dài hạn cho AI Agent

Chào bạn! Hệ thống Hia Wiki Memory đã được cài đặt thành công. Thay vì phải chép từng câu lệnh, bạn chỉ cần tải file này lên hộp thoại Chat hoặc ném đoạn Prompt bên dưới cho AI Agent của bạn.

---

### Mẫu Prompt cấp quyền (Copy đoạn dưới đưa cho AI)

```text
Chào AI, tôi đã tích hợp hệ thống "Hia Wiki Memory Skill" vào thư mục `hia-wiki-memory-skill/` để làm bộ nhớ dài hạn cho dự án.

Yêu cầu đối với bạn (Vai trò Thủ thư - Librarian):
1. Hãy chủ động đọc file `hia-wiki-memory-skill/SKILL.md` để tự học cách sử dụng các tool Python có trong thư mục `scripts/`.
2. Từ nay trở đi, KHÔNG ĐƯỢC dùng trí nhớ nội tại mặc định để nhớ cấu trúc thư mục, kiến trúc hay quy trình của dự án. Mọi thứ phải được tìm kiếm thông qua `scripts/search_wiki.py`.
3. Bất cứ khi nào bạn viết xong một đoạn code phức tạp, sửa xong một lỗi bug khó, hay chúng ta vừa thống nhất một quy trình mới, bạn PHẢI tự động gọi `scripts/update_wiki.py` để lưu nó lại vĩnh viễn. Không cần đợi tôi nhắc nhở "Hãy lưu cái này lại".
4. Nếu kết thúc một chặng đường code dài, hãy tự động nhắc nhở tôi để bạn chạy script dọn dẹp `scripts/rotate_wiki.py`.
5. Bạn không được dùng lệnh bash (echo, cat) để sửa file trong kho chứa, chỉ được dùng Python script mà Skill đã cung cấp.

Bây giờ, hãy xác nhận bạn đã hiểu và thử đọc file SKILL.md xem sao!
```
