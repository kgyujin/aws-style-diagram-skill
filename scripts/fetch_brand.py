"""Simple Icons(CC0, 버전 고정)에서 기술 로고를 받아 assets/brands/에 넣고 brands.json에 색을 적는다.

사용:
  python3 -I fetch_brand.py redis mongodb          # slug로 받기
  python3 -I fetch_brand.py --find "spring boot"   # slug 찾기
  python3 -I fetch_brand.py mylogo --file a.svg --hex "#112233" --title "My Logo" --license "확인한 라이선스"
                                                   # Simple Icons에 없는 로고(공식 SVG 한 개 path 기준)
  python3 -I fetch_brand.py mylogo --file a.svg --hex "#112233" --local
                                                   # 저장소 대신 로컬 폴더(~/.config/aws-style-diagram/brands)에 넣기

받은 색은 타일 배경색이 된다. 흰 글리프와 대비가 낮은 밝은 색(예: React #61DAFB)은
자동으로 어두운 배경(#20232A)에 브랜드색 글리프로 바꿔 적는다.
"""
import argparse
import json
import os
import pathlib
import re
import unicodedata
import urllib.request

SI = "16.33.0"
BASE = f"https://cdn.jsdelivr.net/npm/simple-icons@{SI}"
ROOT = pathlib.Path(__file__).resolve().parent.parent
BRANDS = ROOT / "assets" / "brands"
LOCAL = pathlib.Path(os.environ.get("AWS_STYLE_DIAGRAM_BRANDS",
                                    pathlib.Path.home() / ".config" / "aws-style-diagram" / "brands"))


def get(url):
    with urllib.request.urlopen(url, timeout=30) as r:
        return r.read()


def title_to_slug(title):
    t = title.lower().replace("+", "plus").replace(".", "dot").replace("&", "and")
    t = unicodedata.normalize("NFD", t)
    return re.sub(r"[^a-z0-9]", "", t)


def luminance(hexcolor):
    h = hexcolor.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def colors_for(hexcolor):
    hexcolor = "#" + hexcolor.lstrip("#").upper()
    # 흰 글리프 대비가 2.5:1 미만이면 어두운 바탕에 브랜드색 글리프로 바꾼다.
    # AWS 자체 아이콘도 주황(#ED7100, 약 2.9:1) 위에 흰 글리프를 쓰므로 그보다 조금 낮게 잡았다.
    if (1.05) / (luminance(hexcolor) + 0.05) < 2.5:
        return {"bg": "#20232A", "fg": hexcolor}
    return {"bg": hexcolor, "fg": "#FFFFFF"}


def load_table():
    table = BRANDS / "brands.json"
    return json.loads(table.read_text()) if table.exists() else {}


def save_table(t):
    (BRANDS / "brands.json").write_text(json.dumps(t, ensure_ascii=False, indent=1, sort_keys=True))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slugs", nargs="*")
    ap.add_argument("--find")
    ap.add_argument("--file")
    ap.add_argument("--hex")
    ap.add_argument("--title")
    ap.add_argument("--license")
    ap.add_argument("--source")
    ap.add_argument("--local", action="store_true", help="저장소가 아닌 로컬 로고 폴더에 넣는다")
    a = ap.parse_args()
    global BRANDS
    if a.local:
        BRANDS = LOCAL
    BRANDS.mkdir(parents=True, exist_ok=True)
    table = load_table()

    if a.file:
        slug = a.slugs[0]
        svg = pathlib.Path(a.file).read_text()
        svg = re.sub(r"<script.*?</script>", "", svg, flags=re.S)
        (BRANDS / f"{slug}.svg").write_text(svg)
        table[slug] = {**colors_for(a.hex), "title": a.title or slug,
                       "license": a.license or "확인 못 함", "source": a.source or a.file}
        save_table(table)
        print("saved", slug)
        return

    data = json.loads(get(f"{BASE}/data/simple-icons.json"))
    if isinstance(data, dict):
        data = data.get("icons", [])
    by_slug = {e.get("slug") or title_to_slug(e["title"]): e for e in data}
    if a.find:
        q = a.find.lower().replace(" ", "")
        for s, e in by_slug.items():
            if q in s or q in e["title"].lower().replace(" ", ""):
                print(f"{s:30} {e['title']}")
        return
    for slug in a.slugs:
        e = by_slug.get(slug)
        if not e:
            print(f"없음: {slug} (--find로 찾아보기)")
            continue
        (BRANDS / f"{slug}.svg").write_bytes(get(f"{BASE}/icons/{slug}.svg"))
        lic = (e.get("license") or {}).get("type", "CC0-1.0")
        table[slug] = {**colors_for(e["hex"]), "title": e["title"], "license": lic,
                       "source": e.get("source"), "guidelines": e.get("guidelines")}
        print(f"saved {slug:20} {e['hex']}  {lic}")
    save_table(table)


if __name__ == "__main__":
    main()
