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
    subgraph Manifests ["Quản lý vòng đời (Manifests)"]
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

## 🛠 4. Cách cài đặt & Cấp quyền cho Agent (Tự động 100%)

Bạn không cần phải tự gõ từng dòng lệnh hay loay hoay thiết lập thư viện. Hệ thống đã có sẵn **Setup Wizard** để tự động lo mọi thứ cho bạn.

**Bước 1: Cài đặt tự động**
- Nếu dùng **Windows**: Chỉ cần click đúp vào file `setup/install.bat`.
- Nếu dùng **Mac/Linux**: Chạy file `setup/install.sh` (`bash setup/install.sh`).

*Trình cài đặt sẽ tự động:*
1. Cài đặt các thư viện Python (pip install).
2. Hỏi bạn muốn dùng Vector DB Miễn phí (Local) hay Trả phí (Pinecone Cloud).
3. Hỏi cấu hình Khóa Phân Tán (Redis) và tự động sinh file `.env`.
4. Tự động tạo thư mục Bộ nhớ (`.wiki`).

**Bước 2: Cấp quyền cho AI Agent**
Sau khi cài đặt xong, bạn chỉ cần mở file `docs/AGENT_INSTRUCTIONS.md`, copy đoạn văn bản trong đó và ném cho Agent của bạn (Claude, GPT, AutoGen, CrewAI...). Agent sẽ tự động hiểu cách sử dụng bộ não này mà bạn không cần giải thích gì thêm!

*(Mở rộng cho DevOps: Bạn cũng có thể thiết lập Cloud API Server bằng Docker, vui lòng xem file `Dockerfile` có sẵn)*

---

## 🌐 5. Sẵn sàng cho Multi-Agent & Cloud-Native (Quy mô Enterprise)

Hệ thống đã xây dựng sẵn bộ Lock vật lý (`FileLock`) và **Khóa Phân Tán (Redis Lock)** nên nó chịu được môi trường Multi-Agent phân tán. Để phát huy tối đa sức mạnh mà không làm nghẽn cổ chai DB, Skill hỗ trợ hoàn hảo **Mô hình Ủy quyền (Hierarchical Proxy Pattern)** và **Kiến trúc Cloud-Native**:

- **Khóa Phân Tán (Distributed Lock)**: Tự động dùng Redis nếu có `REDIS_URL`, hoặc lùi về FileLock nội bộ.
- **Vector DB Đa nền tảng (Pluggable)**: Hỗ trợ ChromaDB (Mặc định/Local) và Pinecone (Cloud). Thay đổi linh hoạt bằng biến `VECTOR_STORE=pinecone`.
- **Đồng bộ Tăng dần (Incremental Sync)**: Hệ thống sử dụng `.sync_state.json` để theo dõi Hash mã băm của từng file. Khi đồng bộ, chỉ các nội dung bị thay đổi mới được đẩy lên Vector DB, tiết kiệm tối đa API Cost.
- **Mô hình Ủy quyền**: Chỉ cần cấp quyền truy cập các file trong `scripts/` cho **1 Agent duy nhất** đóng vai trò **Librarian (Thủ thư)**. Hàng chục Agent thợ (Worker) bên ngoài cứ việc code và test. Khi có thông tin quan trọng, chúng tự động báo cáo cho Quản lý (Main Agent). Main Agent sẽ ra lệnh cho Librarian gọi `update_wiki.py`. Mọi thao tác đều an toàn nhờ cơ chế Lock đa tầng.

---

## 📚 7. Tài liệu nâng cao (Advanced Guides)

Nếu bạn muốn scale hệ thống này lên quy mô khổng lồ, hãy tham khảo các tài liệu chuyên sâu trong thư mục `docs/`:
- 📖 **[platform_integration.md](docs/platform_integration.md):** Hướng dẫn chi tiết cách tích hợp Librarian Agent vào các nền tảng như OpenClaw, CrewAI, AutoGen, Claude Code (Kèm sẵn Prompt mẫu để copy-paste).

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

## 💰 9. Đánh giá Tiêu thụ Token (Token Economics)

Tại sao lại cần hệ thống này trong khi bạn có thể đưa tất cả tài liệu vào Context Window của AI? Dưới đây là bài toán kinh tế giả định cho một dự án có **50 tài liệu** (trung bình 1,000 tokens/tài liệu = **50,000 tokens** tổng dung lượng bộ nhớ kiến thức).

| Trạng thái (Hành vi) | ❌ Không dùng Skill (Nhồi nhét Context) | ✅ Dùng Hia Wiki Memory Skill | Mức độ Tiết kiệm |
| :--- | :--- | :--- | :--- |
| **Lần đầu gặp (Truy xuất kiến thức)** | Mất **50,000 tokens** ở phần Prompt để nạp toàn bộ lịch sử và tài liệu dự án cho Agent đọc. | Hệ thống sử dụng công cụ `search_wiki` (Vector RAG). Chỉ trích xuất 3 đoạn text liên quan nhất = Mất khoảng **1,500 tokens**. | Tiết kiệm **~97%** tokens khởi tạo. |
| **Lần thứ 2 (Và các lượt chat tiếp theo)** | Do Chat History lưu lại bối cảnh cũ, mỗi tin nhắn bạn gửi đi AI phải load lại toàn bộ 50,000 tokens. Qua 10 lượt chat, bạn đốt **hơn 500,000 tokens**. | Các đoạn tài liệu lấy từ Wiki không bị kẹt vĩnh viễn trong trí nhớ. Agent chỉ tốn **~2,000 tokens** duy trì mỗi lượt. Trải qua 10 lượt chat chỉ tốn **20,000 tokens**. | Tiết kiệm **~96%** Token dài hạn (Ngăn chặn Context Bloat). |
| **Lưu trữ dữ liệu cơ bản** | AI phải in ra toàn bộ nội dung tài liệu mới vào màn hình chat (Đốt token đầu ra Output rất đắt). Dễ bị lưu trùng lặp. | Agent gọi script `update_wiki.py` (Chỉ tốn lượng cực nhỏ Token gọi hàm). Hệ thống tự băm (Hash) và kiểm tra trùng lặp (Duplication Check). | Chi phí ghi **giảm 99%**. |

> **Kết luận:** Khi dự án vượt quá 20 files, việc không sử dụng Hia Wiki Memory sẽ khiến chi phí API của bạn tăng theo cấp số nhân. Với cấu trúc *Flat Storage + Manifest Tiering*, Skill này biến bài toán chi phí từ O(N) trở thành O(1).

---
*Built for the future of Multi-Agent Systems. Code smarter, remember forever.*
