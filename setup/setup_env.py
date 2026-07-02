import os
import sys
import subprocess
from pathlib import Path

def print_header(msg):
    print(f"\n{'='*50}\n{msg}\n{'='*50}")

def install_requirements():
    print_header("Bước 1: Cài đặt thư viện (Dependencies)")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Cài đặt thư viện thành công!")
    except subprocess.CalledProcessError:
        print("❌ Lỗi khi cài đặt thư viện. Vui lòng kiểm tra lại môi trường Python.")
        sys.exit(1)

def setup_env_file():
    print_header("Bước 2: Thiết lập môi trường (Vector DB & Redis)")
    
    env_vars = {}
    
    print("Bạn muốn sử dụng Vector Database nào?")
    print("1. ChromaDB (Local, Miễn phí, Dễ cài đặt nhất)")
    print("2. Pinecone (Cloud, Dành cho doanh nghiệp/Multi-Agent)")
    choice = input("Nhập lựa chọn (1/2) [Mặc định: 1]: ").strip()
    
    if choice == '2':
        env_vars['VECTOR_STORE'] = 'pinecone'
        pinecone_key = input("Nhập PINECONE_API_KEY: ").strip()
        openai_key = input("Nhập OPENAI_API_KEY (Dùng cho Embeddings): ").strip()
        pinecone_index = input("Nhập tên Pinecone Index [Mặc định: hia-wiki]: ").strip() or "hia-wiki"
        
        env_vars['PINECONE_API_KEY'] = pinecone_key
        env_vars['OPENAI_API_KEY'] = openai_key
        env_vars['PINECONE_INDEX'] = pinecone_index
    else:
        env_vars['VECTOR_STORE'] = 'chroma'
        print("✅ Đã chọn ChromaDB (Local).")

    print("\nThiết lập Khóa Phân Tán (Distributed Lock) để chạy nhiều Agent cùng lúc?")
    redis_url = input("Nhập REDIS_URL (Ví dụ: redis://localhost:6379/0) hoặc Bỏ trống để dùng FileLock nội bộ: ").strip()
    if redis_url:
        env_vars['REDIS_URL'] = redis_url
        print("✅ Đã ghi nhận Redis URL.")
    else:
        print("✅ Đã chọn FileLock (Local).")

    # Ghi ra file .env
    env_path = Path(".env")
    with open(env_path, "w", encoding="utf-8") as f:
        for k, v in env_vars.items():
            f.write(f"{k}={v}\n")
    print(f"\n✅ Đã lưu cấu hình vào file {env_path.absolute()}")

def init_wiki():
    print_header("Bước 3: Khởi tạo Cấu trúc Bộ Nhớ")
    wiki_dir = input("Nhập tên thư mục chứa bộ nhớ Wiki [Mặc định: .wiki]: ").strip() or ".wiki"
    script_path = Path(__file__).parent.parent / "scripts" / "init_wiki.py"
    try:
        subprocess.check_call([sys.executable, str(script_path), "--dir", wiki_dir])
        print(f"✅ Khởi tạo thư mục Wiki tại '{wiki_dir}' thành công!")
    except subprocess.CalledProcessError:
        print("❌ Lỗi khi khởi tạo thư mục Wiki.")

def main():
    print_header("Hia Wiki Memory - Trình Cài Đặt Tự Động")
    install_requirements()
    setup_env_file()
    init_wiki()
    print_header("🎉 CÀI ĐẶT HOÀN TẤT 🎉")
    print("Bây giờ bạn có thể ném file 'AGENT_INSTRUCTIONS.md' cho AI để bắt đầu sử dụng hệ thống!")

if __name__ == "__main__":
    main()
