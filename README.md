# Hia Wiki Memory Skill 🧠

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

**Hia Wiki Memory Skill** là một hệ thống "Não bộ" lưu trữ kiến thức dài hạn, chuẩn Enterprise, được xây dựng sẵn thành các script Python thực thi trực tiếp dành cho các AI Agent (như AutoGen, Claude Code, CrewAI, v.v.). 

Thay vì bắt AI tự nhớ mọi thứ trong ngữ cảnh (Context) giới hạn, Skill này tự động quản lý vòng đời dữ liệu thông qua hệ thống phân tầng ổ cứng vật lý và Vector Database.

---

## 📂 1. Cấu trúc thư mục được Skill tạo ra (Folder Architecture)

Khi Agent chạy lệnh khởi tạo, hệ thống sẽ tự động sinh ra cấu trúc thư mục sau để làm "Bộ não":

```text
wiki_directory/
│
├── index.md              # 📍 MASTER MAP: Bản đồ tổng, chỉ chứa link đến các nhánh.
├── branches/             # 🌿 BRANCH MAPS: Các bản đồ con chia theo domain (Frontend, DB...).
│   └── auth_index.md     # (Ví dụ: Bản đồ chuyên về logic Đăng nhập)
│
├── manifests/            # 📜 LOGICAL TIERS: Các file danh sách điều hướng dữ liệu.
│   ├── hot_index.md      # 🔴 HOT (Đang xử lý): Chứa path của các file đang code/sửa đổi.
│   ├── warm_index.md     # 🟡 WARM (Đã xong): Các file cũ (< 90 ngày).
│   ├── cold_index.md     # 🔵 COLD (Kho lạnh): File quá cũ, ít dùng.
│   └── review_index.md   # 🟠 REVIEW: File cần Agent đọc lại để làm mới (Rewarm).
│
├── raw/                  # 🍃 FLAT STORAGE: Nơi chứa vật lý TẤT CẢ các file Markdown.
│   ├── api_login.md      # File nội dung thực tế 1
│   └── db_schema.md      # File nội dung thực tế 2
│
├── .chroma_db/           # 🧠 Não bộ AI (Vector Database - ChromaDB).
└── .chroma_db.lock       # 🔒 FileLock chống ghi đè khi nhiều Agent cùng truy cập.
```

---

## ⚙️ 2. Cách thức các Script hoạt động

Hệ thống không nói lý thuyết suông. Mọi thứ được tự động hóa bằng các công cụ Python có sẵn trong thư mục `scripts/`:

> [!NOTE] 
> **Cơ chế chống chết Link (Anti Link-Rot):** Mọi file kiến thức khi tạo ra đều nằm "chết" ở thư mục `raw/`. Các script Python không bao giờ di chuyển file vật lý, chúng chỉ di chuyển các đường dẫn (path) bên trong các file `manifests/`. Do đó, các đường link liên kết nội bộ không bao giờ bị hỏng.

```mermaid
flowchart TD
    subgraph Manifests [Quản lý vòng đời (Manifests)]
        HOT(hot_index.md)
        WARM(warm_index.md)
        COLD(cold_index.md)
    end

    subgraph Storage [Lưu trữ vật lý]
        RAW(Thư mục raw/)
    end

    subgraph RAG [Não bộ AI]
        DB[(Chroma Vector DB)]
    end

    HOT -.Được trỏ tới.-> RAW
    WARM -.Được trỏ tới.-> RAW
    COLD -.Được trỏ tới.-> RAW

    HOT ==search_wiki.py lấy dữ liệu==> DB
    WARM ==search_wiki.py lấy dữ liệu==> DB
    COLD -.->|Bị ẩn đi bởi bộ lọc Vector| DB
```

Nhờ kiến trúc này, tool `search_wiki.py` hoạt động ở tốc độ **Zero-Latency**. Nó không phải quét toàn bộ ổ cứng (os.walk) mà chỉ nhìn vào các file đã index.

---

## 🚀 3. Vòng đời dữ liệu thực tế (Được Script xử lý tự động)

Dưới đây là cách bộ Skill tự động xử lý một file kiến thức mới từ lúc sinh ra đến lúc "nghỉ hưu":

1. **Kiểm tra trùng lặp (`check_duplication.py`):** 
   Trước khi ghi, Agent gọi lệnh này để soi vào Vector DB. Nếu nội dung chuẩn bị ghi đã tồn tại > 80% (Semantic Similarity), script sẽ chặn lại để tránh sinh ra dữ liệu rác.
2. **Ghi và Khóa (`update_wiki.py`):** 
   Agent gọi lệnh ghi. Script này tự động tạo `FileLock` để khóa ổ cứng (chống 2 Agent ghi đè nhau), thả file vào thư mục `raw/`, cập nhật YAML frontmatter, ghi danh vào `hot_index.md`, và **tự động Git Commit**. Nếu Git lỗi, script sẽ trả lỗi về cho Agent biết.
3. **Truy vấn lai (`search_wiki.py`):** 
   Khi Agent cần tìm lại code cũ, lệnh này kết hợp tìm kiếm Vector (ChromaDB) + lọc theo thẻ (Tags/Metadata) để moi đúng đoạn code cần thiết ra, tránh nổ Context Window. (Tích hợp sẵn Chunking). 
   *Đặc biệt: Hệ thống áp dụng **Bộ lọc Vector Động (Dynamic Vector Filtering)**. Mặc định, các file trong kho lạnh (`cold`) sẽ bị ẩn khỏi kết quả tìm kiếm để chống nhiễu RAG. Tuy nhiên, Agent có thể chủ động gắn cờ `--include-cold` để tháo bộ lọc và lặn xuống kho lạnh tìm kiếm.*
4. **Đóng băng và Xóa rác (`rotate_wiki.py`):** 
   Được chạy định kỳ. Script tự động tính số ngày tuổi của file. Quá 7 ngày -> chuyển từ Hot sang Warm. Quá 90 ngày -> đẩy xuống kho lạnh (Cold) để bị ẩn đi bởi Bộ lọc Vector Động. File nào bị dán mác `deprecated` quá 30 ngày sẽ bị xóa sổ hoàn toàn khỏi ổ cứng.

---

## 🛠 4. Cách Agent tự động cài đặt

Bạn không cần tự thiết lập gì cả. 

**Bước 1:** Đảm bảo máy tính đã có các thư viện nền:
```bash
pip install -r requirements.txt
```

**Bước 2:** Copy nguyên đoạn Prompt dưới đây ném cho Agent của bạn (Claude, GPT, AutoGen...):

> *"Chào AI, đây là thư mục `hia-wiki-memory-skill`. Hệ thống này cung cấp cho bạn các công cụ Python để tự động hóa trí nhớ dài hạn. 
> 1. Hãy đọc file `SKILL.md` để lấy danh sách các tool và hiểu về vai trò quản trị của bạn.
> 2. Chạy `scripts/init_wiki.py --dir <thư_mục_bạn_chọn>` để hệ thống tự động bung cấu trúc thư mục (raw, manifests, branches).
> 3. Từ nay, hãy chủ động dùng `update_wiki.py` và `search_wiki.py` để ghi nhớ và lấy lại thông tin kiến trúc dự án thay vì dựa vào trí nhớ Context mặc định.
> 4. Hãy chủ động nhắc nhở tôi thực hiện bảo trì (`rotate_wiki.py`) khi kết thúc một tính năng lớn, và sẵn sàng mở Dashboard cho tôi xem bất cứ khi nào tôi yêu cầu."*

---

## 🌐 5. Sẵn sàng cho Multi-Agent (Quy mô Enterprise)

Hệ thống đã xây dựng sẵn bộ Lock vật lý (`FileLock`) nên nó chịu được môi trường Multi-Agent. Để phát huy tối đa sức mạnh mà không làm nghẽn cổ chai DB, Skill hỗ trợ hoàn hảo **Mô hình Ủy quyền (Hierarchical Proxy Pattern)**:

- Chỉ cần cấp quyền truy cập các file trong `scripts/` cho **1 Agent duy nhất** đóng vai trò **Librarian (Thủ thư)**.
- Hàng chục Agent thợ (Worker) bên ngoài cứ việc code và test. Khi có thông tin quan trọng, chúng tự động báo cáo cho Quản lý (Main Agent). Main Agent sẽ ra lệnh cho Librarian gọi `update_wiki.py`. 
- Mô hình này đã được chứng minh là ngăn chặn 100% rác dữ liệu ở quy mô dự án lớn.

---

## 📚 7. Tài liệu nâng cao (Advanced Guides)

Nếu bạn muốn scale hệ thống này lên quy mô khổng lồ, hãy tham khảo các tài liệu chuyên sâu trong thư mục `advanced_guides/`:
- 📖 **[platform_integration.md](advanced_guides/platform_integration.md):** Hướng dẫn chi tiết cách tích hợp Librarian Agent vào các nền tảng như OpenClaw, CrewAI, AutoGen, Claude Code (Kèm sẵn Prompt mẫu để copy-paste).
- ☁️ **[cloud_api_migration.md](advanced_guides/cloud_api_migration.md):** Bản thiết kế kiến trúc nâng cấp từ Local Script lên Cloud API Server (Microservice) bằng FastAPI và Redis Lock.

---

## 🧹 8. Cơ chế bảo trì & Dashboard tự động

Hệ thống được thiết kế để tự động hóa 99%. AI (Librarian) được trang bị "ý thức" để **tự động nhắc nhở** bạn thực hiện bảo trì sau các đợt code lớn. Khi được bạn cho phép, AI sẽ chạy các script sau:

### Lịch trình đề xuất (AI tự động nhắc nhở):
- **Đóng băng & Dọn rác (`rotate_wiki.py`):** Đẩy các file cũ xuống kho lạnh (Cold) để ẩn đi trong các truy vấn thông thường, dọn dẹp các file rác (deprecated), giữ cho bộ não AI luôn tập trung.
- **Quét Link Hỏng (`check_links.py`):** Quét toàn bộ Map (`index.md`) xem có link nào trỏ vào file đã xóa không và tự đánh dấu ❌.
- **Khôi phục thảm họa (`rebuild_db.py`):** Xóa trắng não bộ Vector (ChromaDB) để hệ thống đọc và index lại từ đầu dựa trên file Markdown.

### 📊 Xem Dashboard Trực Quan
Bạn có thể ra lệnh cho AI: *"Mở Dashboard hệ thống cho tôi xem"*.
Lập tức, AI sẽ tự động chạy 2 lệnh dưới đây:
```bash
python scripts/export_memory_state.py --dir <wiki_dir>
python scripts/build_dashboard.py --dir <wiki_dir>
```
Kết quả sinh ra là một file HTML siêu đẹp hiển thị biểu đồ tròn, cột thống kê số lượng file ở các Tier. Trực quan như một ứng dụng Web thực thụ.

---
*Built for the future of Multi-Agent Systems. Code smarter, remember forever.*
