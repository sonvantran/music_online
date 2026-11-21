"""
Quét thư mục nhạc của bạn, copy vào ./music (tên file đã chuyển sang không dấu
để link online không bị lỗi) và tạo library.json cho trang web.
Chạy: python build.py
"""
import hashlib
import json
import os
import re
import shutil
import sys
import unicodedata

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ====== SỬA CHỖ NÀY ======
# Thư mục CHA chứa các thư mục nhạc (giống MUSIC_DIR trong app.py của bản local)
SOURCE_DIR = r"C:\Users\SON\Downloads\EXE\music_player\music"

# Thứ tự hiển thị các mục (giống bản local)
PREFERRED_ORDER = [
    "Nhạc đón khách",
    "Nhạc MC giới thiệu",
    "Nhạc chú rể lên sân khấu",
    "Nhạc cô dâu lên sân khấu",
    "Nhạc bố mẹ lên sân khấu",
    "Nhạc nghi thức cưới",
    "Nhạc dâng rượu, giao bôi",
    "Nhạc nâng ly khai tiệc",
    "Nhạc dùng tiệc",
]
# =========================

OUT_DIR = os.path.join(BASE_DIR, "music")
AUDIO_EXT = {".mp3", ".m4a", ".wav", ".ogg", ".flac", ".aac"}
MAX_FILE_MB = 95        # GitHub từ chối file từ 100 MB trở lên
WARN_TOTAL_MB = 900     # repo nên giữ dưới khoảng 1 GB


def norm(s):
    return unicodedata.normalize("NFC", s).lower()


def natural_key(s):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", norm(s))]


def slugify(s):
    s = unicodedata.normalize("NFC", s).replace("đ", "d").replace("Đ", "D")
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s[:80].strip("-")


def unique(base, used):
    s, n = base, 2
    while s in used:
        s = f"{base}-{n}"
        n += 1
    used.add(s)
    return s


def main():
    if not os.path.isdir(SOURCE_DIR):
        print("Không tìm thấy thư mục nhạc:", SOURCE_DIR)
        print("Hãy sửa SOURCE_DIR trong build.py.")
        sys.exit(1)

    order_index = {norm(n): i for i, n in enumerate(PREFERRED_ORDER)}
    os.makedirs(OUT_DIR, exist_ok=True)

    sections = []
    expected = set()
    used_folders = set()
    total_bytes = 0
    copied = 0
    big_files = []

    for name in os.listdir(SOURCE_DIR):
        src_folder = os.path.join(SOURCE_DIR, name)
        if not os.path.isdir(src_folder):
            continue
        files = [f for f in os.listdir(src_folder)
                 if os.path.splitext(f)[1].lower() in AUDIO_EXT]
        if not files:
            continue
        files.sort(key=natural_key)

        fslug = unique(slugify(name) or "muc", used_folders)
        used_files = set()
        songs = []

        for f in files:
            base, ext = os.path.splitext(f)
            ext = ext.lower()
            sslug = unique(slugify(base) or "bai", used_files)
            src = os.path.join(src_folder, f)
            dst = os.path.join(OUT_DIR, fslug, sslug + ext)
            expected.add(os.path.abspath(dst))

            st = os.stat(src)
            need = True
            if os.path.exists(dst):
                ds = os.stat(dst)
                if ds.st_size == st.st_size and int(ds.st_mtime) == int(st.st_mtime):
                    need = False
            if need:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
                copied += 1

            if st.st_size >= MAX_FILE_MB * 1024 * 1024:
                big_files.append((f, st.st_size / 1024 / 1024))
            total_bytes += st.st_size

            v = hashlib.sha1(f"{st.st_size}-{int(st.st_mtime)}".encode()).hexdigest()[:8]
            songs.append({
                "title": base,
                "url": f"music/{fslug}/{sslug}{ext}?v={v}",
                "size": st.st_size,
            })

        sections.append({"name": name, "songs": songs})

    sections.sort(key=lambda s: (order_index.get(norm(s["name"]), 999), natural_key(s["name"])))

    # Xóa file/thư mục thừa trong ./music (bài đã bị xóa ở thư mục gốc)
    removed = 0
    for root, dirs, files in os.walk(OUT_DIR, topdown=False):
        for fn in files:
            p = os.path.abspath(os.path.join(root, fn))
            if p not in expected:
                os.remove(p)
                removed += 1
        if root != OUT_DIR and not os.listdir(root):
            os.rmdir(root)

    with open(os.path.join(BASE_DIR, "library.json"), "w", encoding="utf-8") as fp:
        json.dump({"sections": sections}, fp, ensure_ascii=False, indent=1)

    # Báo GitHub Pages không xử lý Jekyll (nhanh và ít lỗi hơn)
    open(os.path.join(BASE_DIR, ".nojekyll"), "w").close()

    n_songs = sum(len(s["songs"]) for s in sections)
    total_mb = total_bytes / 1024 / 1024
    print(f"Xong: {len(sections)} mục, {n_songs} bài, tổng {total_mb:.0f} MB")
    print(f"Đã copy mới/cập nhật {copied} file, xóa {removed} file thừa.")
    if big_files:
        print("\n⚠ File quá lớn cho GitHub (cần dưới 100 MB), hãy nén bớt:")
        for f, mb in big_files:
            print(f"   - {f}: {mb:.0f} MB")
    if total_mb > WARN_TOTAL_MB:
        print(f"\n⚠ Tổng dung lượng {total_mb:.0f} MB, gần giới hạn khuyến nghị 1 GB của repo.")


if __name__ == "__main__":
    main()