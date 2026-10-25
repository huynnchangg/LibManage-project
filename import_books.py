"""Import sach tu file CSV Goodreads vao database.

Cac van de duoc xu ly:
  - Description bi nhan doi (phan dau = phan cuoi) -> giu nua dau
  - Description bi mojibake (UTF-8 decode sai thanh Latin-1) -> fix encoding
  - HTML entities (&amp; &#39; ...) -> decode
  - Khoang trang thua, newline thua -> strip + normalize
  - Mo ta qua ngan hoac vo nghia (< 20 ky tu) -> bo qua
  - Tac gia nhieu nguoi -> lay nguoi dau tien + "et al."
  - Title hoac author chua ky tu dac biet HTML -> decode

Dung:
    NHỚ DÙNG CÁI NÀY NHÉ: python import_books.py goodreads_books.csv
    Hoặc 500 thôi cho đỡ nặng: python import_books.py goodreads_books.csv --limit 500
    python import_books.py goodreads_books.csv --copies 3
    python import_books.py goodreads_books.csv --reset    # xoa sach cu roi import lai
"""
import csv
import html
import io
import re
import sys

# Force stdout/stderr UTF-8 (tranh loi encode tren Windows console)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from app import create_app
from app.extensions import db
from app.models import Book, Category

# ---------------------------------------------------------------------------
# Anh xa genre Goodreads -> category trong DB
# Thu tu uu tien: khop truoc dung truoc
# ---------------------------------------------------------------------------
GENRE_MAP = [
    (r"Computer|Programming|Software|Technology|Engineering|Science.?Fiction.*Tech", "Công nghệ thông tin"),
    (r"Business|Economics|Finance|Money|Investing|Management|Marketing",             "Kinh tế"),
    (r"History|Biography|Memoir|True.?Crime|Historical",                             "Lịch sử"),
    (r"Self.?Help|Psychology|Philosophy|Personal.?Development|Motivat",              "Kỹ năng sống"),
    (r"Textbook|Education|Academic|School|Reference",                                "Giáo khoa"),
    (r"Science(?!.*Fiction)|Nature|Math|Physics|Chemistry|Biology",                  "Khoa học"),
    # Tat ca fiction, the loai ky ao, kinh di, tho, comics -> Van hoc (mac dinh)
    (r".*", "Văn học"),
]

MAX_DESC_CHARS = 1500   # do dai toi da description luu vao DB
MIN_DESC_CHARS = 20     # ngan hon thi bo (vo nghia)
MAX_AUTHOR_CHARS = 120  # gioi han cot author trong model


# ---------------------------------------------------------------------------
# Ham xu ly tung truong
# ---------------------------------------------------------------------------

def fix_mojibake(text: str) -> str:
    """
    Mo ta trong CSV bi encode sai: UTF-8 bytes bi doc bang Latin-1.
    Ky hieu nhan biet: Ã, Â, â, å, ... xuat hien lieu linh.
    Thu decode lai: encode bang latin-1 roi decode bang utf-8.
    Neu that bai giu nguyen ban goc.
    """
    if not text:
        return text
    # Neu khong co ky hieu dac trung cua mojibake thi bo qua
    if not re.search(r"[ÃÂâåÅæÆø]", text):
        return text
    try:
        fixed = text.encode("latin-1").decode("utf-8")
        return fixed
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text


def deduplicate_description(text: str) -> str:
    """
    CSV Goodreads: field description = [preview bi cat] + [full description].
    Preview la phan dau bi cat cua full description.
    
    Thuat toan:
    Chia text tai moi diem hop le (dau cau + khoang, hoac nhieu khoang trang).
    Voi moi diem chia: neu phan sau (p2) CHUA phan truoc (p1) trong no
    => p2 chinh la full description (p1 chi la preview).
    Bo sung: chi chap nhan neu p1 ngan hon p2 dang ke (p1 < 55% cua p2).
    """
    if not text or len(text) < 80:
        return text

    length = len(text)

    for m in re.finditer(r'[.!?,;]\s+[A-Z]|\s{2,}[A-Z]', text):
        pos = m.end() - 1  # vi tri chu hoa dau tien cua p2
        if not (length * 0.1 < pos < length * 0.75):
            continue
        p1 = text[:pos].strip()
        p2 = text[pos:].strip()
        if len(p1) < 15 or len(p2) < 40:
            continue
        # p1 phai ngan hon p2 (preview < full)
        if len(p1) >= len(p2) * 0.55:
            continue
        # Kiem tra p1 co la substring cua p2 khong
        # De giam false positive, chi kiem tra 30 ky tu giua p1
        check_start = min(10, len(p1) // 4)
        check = p1[check_start:check_start + 40]
        if len(check) >= 15 and check in p2:
            return p2

    return text


def clean_description(raw: str) -> str:
    """Lam sach toan dien mo ta sach."""
    if not raw:
        return ""

    text = raw.strip()

    # 1. Fix mojibake truoc
    text = fix_mojibake(text)

    # 2. Decode HTML entities (&amp; &lt; &#39; ...)
    text = html.unescape(text)

    # 3. Loai bo duplicate
    text = deduplicate_description(text)

    # 4. Chuan hoa khoang trang
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()

    # 5. Cat phan dau bi cat con lai sau dedup (chay toi da 4 lan)
    for _ in range(4):
        head_match = re.match(r"^(.{3,80}?)\s+([A-Z][a-z])", text)
        if not head_match:
            break
        head = head_match.group(1)
        rest = text[head_match.start(2):]
        if re.search(r"[.!?]$", head.rstrip()):
            break
        check = head[5:30] if len(head) > 30 else head[3:]
        if len(check) >= 8 and check in rest:
            text = rest.strip()
        else:
            break

    # Pass thu hai: xu ly fragment cuc ngan bi cat giua tu (vi du: "enco When", "getti Since")
    short_frag = re.match(r"^([a-z]{2,6})\s+([A-Z][a-z])", text)
    if short_frag:
        rest = text[short_frag.start(2):]
        stem = short_frag.group(1)[:4]
        if len(stem) >= 3 and stem in rest:
            text = rest.strip()

    # 6. Cat neu qua dai, uu tien cat tai ranh gioi cau
    if len(text) > MAX_DESC_CHARS:
        cut = text[:MAX_DESC_CHARS]
        last_sentence = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
        if last_sentence > MAX_DESC_CHARS * 0.7:
            text = cut[:last_sentence + 1]
        else:
            text = cut.rsplit(" ", 1)[0] + "..."

    # 7. Kiem tra do dai toi thieu
    if len(text) < MIN_DESC_CHARS:
        return ""

    # 8. Validation cuoi: loai bo neu con dau hieu ban ro rang
    # Chi reject khi co dau hieu CHAC CHAN la rac, tranh over-reject:

    # 8a. Fragment bi cat o dau: bat dau bang tu VIET THUONG ngan (2-6 ky tu)
    #     ngay truoc chu hoa, khong co dau cau o truoc
    #     Vi du: "enco When", "getti Since", "wa With", "to he Forensic"
    if re.match(r"^[a-z]{2,6}\s+[A-Z]", text):
        return None

    # 8b. Phat hien double-content ro rang: mot cum 5+ tu xuat hien 2 lan
    #     trong 400 ky tu dau (khac voi 3+ lan cua 1 tu don vi de bi false positive)
    head400 = text[:400]
    for m in re.finditer(r"\b(\w{5,}\s+\w{5,}\s+\w{4,})\b", head400):
        phrase = m.group(1)
        if head400.count(phrase) >= 2:
            return None

    return text


def clean_author(raw: str) -> str:
    """
    Tac gia co the la nhieu nguoi ngan cach bang dau phay.
    Giu nguoi dau tien, them 'et al.' neu co nhieu hon 2 nguoi.
    """
    if not raw:
        return "Unknown"
    text = html.unescape(raw.strip())
    # Tach theo dau phay, loai bo cac phan tu rong
    parts = [p.strip() for p in text.split(",") if p.strip()]
    if len(parts) <= 2:
        result = ", ".join(parts)
    else:
        result = f"{parts[0]} et al."
    return result[:MAX_AUTHOR_CHARS]


def clean_title(raw: str) -> str:
    """Decode HTML entities, cat phan series kieu '(Series #N)' neu muon."""
    if not raw:
        return ""
    text = html.unescape(raw.strip())
    # Khong cat series de giu nguyen thong tin
    return text[:200]  # gioi han cot title trong model


def parse_year(date_str: str) -> int | None:
    """Trich xuat nam tu chuoi nhu 'January 1st 2007', '1997', 'November 1924'."""
    if not date_str:
        return None
    m = re.search(r"\b(1[5-9]\d{2}|20\d{2})\b", date_str)
    return int(m.group(1)) if m else None


def pick_category(genre_str: str) -> str:
    """Tra ve ten category phu hop nhat."""
    if not genre_str:
        return "Văn học"
    for pattern, cat in GENRE_MAP:
        if re.search(pattern, genre_str, re.IGNORECASE):
            return cat
    return "Văn học"


def get_or_create_category(name: str, cache: dict) -> Category:
    if name in cache:
        return cache[name]
    cat = Category.query.filter_by(name=name).first()
    if not cat:
        cat = Category(name=name)
        db.session.add(cat)
        db.session.flush()
    cache[name] = cat
    return cat


# ---------------------------------------------------------------------------
# Ham chinh
# ---------------------------------------------------------------------------

def is_english(text: str) -> bool:
    """
    Kiem tra mo ta co phai tieng Anh khong.
    Dung hai tieu chi ket hop:
    1. Ti le ky tu ngoai ASCII (ord > 127) <= 3% (tieng Duc/French thuong 5-15%).
    2. Co chua it nhat 3 trong so cac stopword tieng Anh pho bien.
    Neu khong co description -> cho qua (True).
    """
    if not text:
        return True

    # Tieu chi 1: ky tu non-ASCII khong qua 3%
    non_ascii = sum(1 for c in text if ord(c) > 127)
    if (non_ascii / len(text)) > 0.03:
        return False

    # Tieu chi 2: phai co it nhat 3 stopword tieng Anh
    stopwords = re.findall(
        r"\b(the|and|of|to|in|is|was|that|for|with|his|her|"
        r"he|she|they|this|have|from|not|but|be|as|at|an|by|"
        r"are|had|has|it|its|or|on|we|you|who|when|their|been)\b",
        text, re.IGNORECASE
    )
    if len(stopwords) < 3:
        return False

    return True


def import_csv(filepath: str, limit: int | None, copies: int, reset: bool) -> None:
    app = create_app()
    with app.app_context():
        db.create_all()

        if reset:
            print("Reset: xoa toan bo sach cu...")
            Book.query.delete()
            db.session.commit()
            print("Xoa xong.\n")

        cat_cache: dict[str, Category] = {}
        added = skipped = rejected = 0
        reject_log = []

        with open(filepath, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                if limit and i >= limit:
                    break

                # --- Lay va lam sach cac truong chinh ---
                title = clean_title(row.get("title") or "")
                author = clean_author(row.get("author") or "")

                # Bo qua neu khong co title hoac author
                if not title:
                    rejected += 1
                    reject_log.append(f"  [{i+1}] Khong co title")
                    continue
                if not author or author == "Unknown":
                    rejected += 1
                    reject_log.append(f"  [{i+1}] Khong co author: {title[:40]}")
                    continue

                isbn = html.unescape((row.get("isbn") or row.get("isbn13") or "").strip()) or None
                publisher = html.unescape((row.get("publisher") or "").strip()) or None
                year = parse_year(row.get("date_published") or "")
                description = clean_description(row.get("description") or "")

                # clean_description tra ve None neu description qua ban -> bo qua sach
                if description is None:
                    rejected += 1
                    reject_log.append(f"  [{i+1}] Description ban (khong the sua): {title[:40]}")
                    continue

                description = description or None  # chuoi rong -> None (sach khong co mo ta)

                # Bo qua neu description khong phai tieng Anh
                if description and not is_english(description):
                    rejected += 1
                    reject_log.append(f"  [{i+1}] Description khong phai tieng Anh: {title[:40]}")
                    continue

                genre_str = row.get("genre_and_votes") or ""
                cat_name = pick_category(genre_str)
                category = get_or_create_category(cat_name, cat_cache)

                book = Book(
                    title=title,
                    author=author,
                    isbn=isbn,
                    publisher=publisher,
                    year=year,
                    description=description,
                    total_copies=copies,
                    available_copies=copies,
                    category_id=category.id,
                )
                db.session.add(book)
                added += 1

                if added % 100 == 0:
                    db.session.commit()
                    print(f"  ... da them {added} cuon")

        db.session.commit()

        print(f"\n--- Ket qua ---")
        print(f"  Them moi  : {added} cuon")
        print(f"  Bo qua    : {skipped} cuon (da ton tai)")
        print(f"  Tu choi   : {rejected} dong (thieu title/loi)")
        if reject_log:
            print("\n  Chi tiet tu choi:")
            for line in reject_log[:20]:
                print(line)
            if len(reject_log) > 20:
                print(f"  ... va {len(reject_log) - 20} dong khac")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    args = sys.argv[1:]
    if not args or args[0].startswith("-"):
        print("Dung: python import_books.py <file.csv> [--limit N] [--copies N] [--reset]")
        sys.exit(1)

    filepath = args[0]
    limit = None
    copies = 2
    reset = False

    i = 1
    while i < len(args):
        if args[i] == "--limit" and i + 1 < len(args):
            limit = int(args[i + 1])
            i += 2
        elif args[i] == "--copies" and i + 1 < len(args):
            copies = int(args[i + 1])
            i += 2
        elif args[i] == "--reset":
            reset = True
            i += 1
        else:
            i += 1

    print(f"Import tu: {filepath}")
    if limit:
        print(f"  Gioi han : {limit} dong")
    print(f"  So ban/sach: {copies}")
    if reset:
        print("  [--reset] Se xoa toan bo sach truoc khi import!")
    print()

    import_csv(filepath, limit, copies, reset)


if __name__ == "__main__":
    main()
