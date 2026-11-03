"""AWS 아키텍처 아이콘 스타일 구성도를 spec JSON으로 그린다(SVG, HTML, 3배 PNG).

사용:
  python3 -I render.py <spec.json> <출력폴더> [--scale 3] [--strict]
  python3 -I render.py --icons eks          # 아이콘 이름 찾기

spec 형식은 SKILL.md의 'spec 쓰는 법'에 있다. 그린 뒤 배치 검사를 돌려 문제를 출력한다.
--strict를 주면 문제가 하나라도 있을 때 종료 코드 1로 끝난다.

- AWS 서비스, 그룹, 일반 리소스 아이콘은 assets/aws/(공식 AWS Architecture Icons)를 그대로 넣는다.
- AWS가 아닌 기술 로고는 assets/brands/의 글리프를 AWS 서비스 아이콘과 같은 정사각형 타일로 만든다.
- PNG는 Chrome(또는 Chromium) headless로 찍는다. 경로는 CHROME_PATH 환경 변수로 바꿀 수 있다.
"""
import argparse
import base64
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
AWS_INDEX = json.loads((ASSETS / "aws" / "index.json").read_text())
BRANDS = json.loads((ASSETS / "brands" / "brands.json").read_text())
BRAND_DIR = {k: ASSETS / "brands" for k in BRANDS}
# 저장소에 올리지 않을 로고(라이선스 미확인, 사내 로고 등)는 로컬 폴더에 둔다. 같은 이름이면 로컬이 이긴다.
LOCAL_BRANDS = pathlib.Path(os.environ.get("AWS_STYLE_DIAGRAM_BRANDS",
                                           pathlib.Path.home() / ".config" / "aws-style-diagram" / "brands"))
if (LOCAL_BRANDS / "brands.json").exists():
    _local = json.loads((LOCAL_BRANDS / "brands.json").read_text())
    BRANDS.update(_local)
    BRAND_DIR.update({k: LOCAL_BRANDS for k in _local})

ICON = 52            # 노드 아이콘 한 변(px)
LABEL_PX, SUB_PX = 17, 14
EDGE_PX, GROUP_PX = 15, 15
BLOCK_H = ICON + 48  # 아이콘 + 이름 + 부제. 아래쪽 연결점은 이 아래에서 나간다
INK, SUB, LINE = "#232F3E", "#545B64", "#545B64"
FONT = "Apple SD Gothic Neo, AppleSDGothicNeo, Noto Sans KR, Malgun Gothic, sans-serif"

# AWS 그룹 표기(색, 선 모양, 바탕, 기본 아이콘). AWS 공식 그룹 규칙을 따른다.
GROUP_STYLE = {
    "aws-cloud": ("#232F3E", False, "none", "group-aws-cloud-logo"),
    "region": ("#00A4A6", True, "none", "group-region"),
    "vpc": ("#8C4FFF", False, "none", "group-virtual-private-cloud-vpc"),
    "private-subnet": ("#00A4A6", False, "#E6F6F7", "group-private-subnet"),
    "public-subnet": ("#7AA116", False, "#F2F6E8", "group-public-subnet"),
    "account": ("#E7157B", False, "none", "group-aws-account"),
    "eks": ("#ED7100", True, "none", "eks"),
    "auto-scaling": ("#ED7100", True, "none", "group-auto-scaling-group"),
    "datacenter": ("#7D8998", False, "none", "group-corporate-data-center"),
    "box": ("#7D8998", False, "none", None),
    "box-dashed": ("#7D8998", True, "none", None),
}


# ---------------------------------------------------------------- 아이콘
def find_icon(name):
    if name.startswith("brand:"):
        return ("brand", name[6:])
    if name.startswith("aws:"):
        return ("aws", name[4:])
    if name in AWS_INDEX:
        return ("aws", name)
    if name in BRANDS:
        return ("brand", name)
    raise SystemExit(f"아이콘 '{name}'을 찾지 못했다. `render.py --icons {name}`로 찾거나 "
                     f"fetch_brand.py로 기술 로고를 받는다.")


def brand_tile(slug, size=80):
    meta = BRANDS[slug]
    svg = (BRAND_DIR[slug] / f"{slug}.svg").read_text()
    vb = [float(v) for v in re.search(r'viewBox="([^"]+)"', svg).group(1).split()]
    paths = re.findall(r'<path[^>]*\sd="([^"]+)"', svg)
    w, h = vb[2], vb[3]
    s = size * 0.62 / max(w, h)
    tx = (size - w * s) / 2 - vb[0] * s
    ty = (size - h * s) / 2 - vb[1] * s
    ps = "".join(f'<path d="{d}"/>' for d in paths)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}">'
            f'<rect width="{size}" height="{size}" fill="{meta["bg"]}"/>'
            f'<g fill="{meta["fg"]}" fill-rule="evenodd" transform="translate({tx:.2f} {ty:.2f}) scale({s:.4f})">'
            f'{ps}</g></svg>')


def icon_href(name):
    kind, key = find_icon(name)
    if kind == "aws":
        raw = (ASSETS / AWS_INDEX[key]).read_bytes()
    else:
        raw = brand_tile(key).encode()
    return "data:image/svg+xml;base64," + base64.b64encode(raw).decode()


# ---------------------------------------------------------------- 글자 폭 어림
def text_w(t, px):
    return sum(px * (1.0 if ord(c) > 0x2E80 else 0.58) for c in t)


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ---------------------------------------------------------------- 모양 계산
class Rect:
    def __init__(self, x0, y0, x1, y1, what):
        self.x0, self.y0, self.x1, self.y1, self.what = x0, y0, x1, y1, what

    def hits(self, o, pad=0):
        return not (self.x1 + pad <= o.x0 or o.x1 + pad <= self.x0 or
                    self.y1 + pad <= o.y0 or o.y1 + pad <= self.y0)

    def hits_seg(self, a, b, pad=0):
        (x0, y0), (x1, y1) = a, b
        if x0 == x1:
            lo, hi = sorted((y0, y1))
            return self.x0 - pad < x0 < self.x1 + pad and lo < self.y1 + pad and hi > self.y0 - pad
        if y0 == y1:
            lo, hi = sorted((x0, x1))
            return self.y0 - pad < y0 < self.y1 + pad and lo < self.x1 + pad and hi > self.x0 - pad
        # 사선은 몇 점을 찍어 본다
        for i in range(1, 20):
            x, y = x0 + (x1 - x0) * i / 20, y0 + (y1 - y0) * i / 20
            if self.x0 - pad < x < self.x1 + pad and self.y0 - pad < y < self.y1 + pad:
                return True
        return False


def node_rects(n):
    cx, top = n["cx"], n["top"]
    icon = Rect(cx - ICON / 2, top, cx + ICON / 2, top + ICON, f"{n['id']} 아이콘")
    lw = text_w(n["label"], LABEL_PX)
    texts = [Rect(cx - lw / 2, top + ICON + 6, cx + lw / 2, top + ICON + 27, f"{n['id']} 이름")]
    if n.get("sub"):
        sw = text_w(n["sub"], SUB_PX)
        texts.append(Rect(cx - sw / 2, top + ICON + 29, cx + sw / 2, top + ICON + 46, f"{n['id']} 부제"))
    return icon, texts


def anchor(spec_nodes, ref):
    """'api.r', 'api.t+25' 같은 연결점을 좌표로 바꾼다. l/r은 아이콘 가운데 높이, t는 아이콘 위,
    b는 부제 아래. +N/-N은 t/b면 x를, l/r이면 y를 옮긴다."""
    if not isinstance(ref, str):
        return tuple(ref)
    m = re.fullmatch(r"([\w-]+)\.([lrtb])([+-]\d+)?", ref)
    if not m:
        raise SystemExit(f"연결점 '{ref}'의 형식이 틀렸다(예: api.r, api.t+25)")
    n = spec_nodes.get(m.group(1))
    if not n:
        raise SystemExit(f"연결점 '{ref}': 노드 '{m.group(1)}'이 없다")
    off = int(m.group(3) or 0)
    cx, top = n["cx"], n["top"]
    cy = top + ICON / 2
    return {
        "l": (cx - ICON / 2 - 2, cy + off),
        "r": (cx + ICON / 2 + 2, cy + off),
        "t": (cx + off, top - 4),
        "b": (cx + off, top + BLOCK_H),
    }[m.group(2)]


# ---------------------------------------------------------------- 그리기
def render(spec):
    W, H = spec["canvas"]["width"], spec["canvas"]["height"]
    nodes = {n["id"]: n for n in spec["nodes"]}
    out_groups, out_edges, out_nodes, out_labels = [], [], [], []
    problems = []
    group_titles, group_rects = [], []

    for g in spec.get("groups", []):
        color, dash, fill, default_icon = GROUP_STYLE[g.get("type", "box")]
        color = g.get("color", color)
        icon = g.get("icon", default_icon)
        x, y, w, h = g["x"], g["y"], g["w"], g["h"]
        da = ' stroke-dasharray="6 4"' if dash else ""
        s = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{color}" stroke-width="1.6"{da}/>']
        tx = x + 10
        if icon:
            s.append(f'<image href="{icon_href(icon)}" x="{x}" y="{y}" width="30" height="30"/>')
            tx = x + 38
        title = g.get("title", "")
        s.append(f'<text x="{tx}" y="{y + 21}" font-size="{GROUP_PX}" font-weight="700" fill="{color}">{esc(title)}</text>')
        out_groups.append("".join(s))
        group_titles.append(Rect(x, y, tx + text_w(title, GROUP_PX) + 4, y + 30, f"그룹 '{title}' 제목"))
        group_rects.append((Rect(x, y, x + w, y + h, f"그룹 '{title}'"), g))
        if x < 0 or y < 0 or x + w > W or y + h > H:
            problems.append(f"그룹 '{title}'이 캔버스 밖으로 나간다")

    all_icon, all_text = [], []
    for n in spec["nodes"]:
        cx, top = n["cx"], n["top"]
        s = [f'<image href="{icon_href(n["icon"])}" x="{cx - ICON / 2}" y="{top}" width="{ICON}" height="{ICON}"/>',
             f'<text x="{cx}" y="{top + ICON + 22}" text-anchor="middle" font-size="{LABEL_PX}" '
             f'font-weight="700" fill="{INK}">{esc(n["label"])}</text>']
        if n.get("sub"):
            s.append(f'<text x="{cx}" y="{top + ICON + 41}" text-anchor="middle" font-size="{SUB_PX}" '
                     f'fill="{SUB}">{esc(n["sub"])}</text>')
        out_nodes.append("".join(s))
        icon, texts = node_rects(n)
        all_icon.append((icon, n["id"]))
        all_text.extend((t, n["id"]) for t in texts)
        for t in [icon] + texts:
            if t.x0 < 0 or t.y0 < 0 or t.x1 > W or t.y1 > H:
                problems.append(f"{t.what}이 캔버스 밖으로 나간다")
        # 노드가 그룹 테두리에 걸치면 어느 그룹 소속인지 헷갈린다
        for gr, g in group_rects:
            for t in [icon] + texts:
                inside = gr.x0 <= t.x0 and t.x1 <= gr.x1 and gr.y0 <= t.y0 and t.y1 <= gr.y1
                if gr.hits(t) and not inside:
                    problems.append(f"{t.what}이 {gr.what} 테두리에 걸친다")
        for gt in group_titles:
            for t in [icon] + texts:
                if gt.hits(t, pad=2):
                    problems.append(f"{t.what}이 {gt.what}과 겹친다")

    label_rects, edge_segs = [], []
    for i, e in enumerate(spec.get("edges", [])):
        pts = [anchor(nodes, p) for p in e["path"]]
        ends = {p.split(".")[0] for p in (e["path"][0], e["path"][-1]) if isinstance(p, str)}
        style = e.get("style", "solid")
        da = ' stroke-dasharray="6 5"' if style == "dashed" else ""
        sw = 2.2 if e.get("bold") else 1.6
        d = "M" + " L".join(f"{x:g} {y:g}" for x, y in pts)
        both = ' marker-start="url(#ah)"' if e.get("both") else ""
        out_edges.append(f'<path d="{d}" fill="none" stroke="{LINE}" stroke-width="{sw}"{da}{both} marker-end="url(#ah)"/>')
        segs = list(zip(pts, pts[1:]))
        name = e.get("label") or f"{e['path'][0]}→{e['path'][-1]}"
        for a, b in segs:
            if a[0] != b[0] and a[1] != b[1]:
                problems.append(f"선 '{name}'에 사선 구간이 있다({a}→{b}). 꺾이는 점을 넣어 직각으로 만든다")
            edge_segs.append((a, b, i, name))
            for r, nid in all_icon:
                # 끝점 노드는 빼고, 좌표로 준 끝점은 아이콘에서 6px 안쪽이면 끝점으로 본다
                if nid in ends:
                    continue
                if any(r.x0 - 6 <= p[0] <= r.x1 + 6 and r.y0 - 6 <= p[1] <= r.y1 + 6 for p in (pts[0], pts[-1])):
                    continue
                if r.hits_seg(a, b, pad=-2):
                    problems.append(f"선 '{name}'이 {r.what}을 지난다")
            for r, nid in all_text:
                if r.hits_seg(a, b, pad=1):
                    problems.append(f"선 '{name}'이 {r.what} 글자를 지난다")
            for gt in group_titles:
                if gt.hits_seg(a, b):
                    problems.append(f"선 '{name}'이 {gt.what}을 지난다")
        if e.get("label"):
            if "at" in e:
                x, y = e["at"]
            else:
                a, b = max(segs, key=lambda s: abs(s[0][0] - s[1][0]) + abs(s[0][1] - s[1][1]))
                x, y = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
            lines = e["label"].split("\n")
            for k, ln in enumerate(lines):
                yy = y + (k - (len(lines) - 1) / 2) * 18
                tw = text_w(ln, EDGE_PX) + 10
                out_labels.append(f'<rect x="{x - tw / 2:.1f}" y="{yy - 10}" width="{tw:.1f}" height="20" fill="#fff"/>'
                                  f'<text x="{x}" y="{yy + 5}" text-anchor="middle" font-size="{EDGE_PX}" fill="{INK}">{esc(ln)}</text>')
                label_rects.append((Rect(x - tw / 2, yy - 10, x + tw / 2, yy + 10, f"선 라벨 '{ln}'"), i))

    for k, (r, i) in enumerate(label_rects):
        for r2, _ in all_icon:
            if r.hits(r2):
                problems.append(f"{r.what}이 {r2.what}을 가린다")
        for r2, _ in all_text:
            if r.hits(r2):
                problems.append(f"{r.what}이 {r2.what}과 겹친다")
        for r2, j in label_rects[k + 1:]:
            if j != i and r.hits(r2, pad=2):
                problems.append(f"{r.what}과 {r2.what}이 겹친다")
        for a, b, j, name in edge_segs:
            if j != i and r.hits_seg(a, b):
                problems.append(f"{r.what}이 다른 선 '{name}'을 가린다")
        for gt in group_titles:
            if r.hits(gt):
                problems.append(f"{r.what}이 {gt.what}과 겹친다")
        for gr, _ in group_rects:
            inside = gr.x0 < r.x0 and r.x1 < gr.x1 and gr.y0 < r.y0 and r.y1 < gr.y1
            if gr.hits(r) and not inside:
                problems.append(f"{r.what}이 {gr.what} 테두리에 걸친다")
        if r.x0 < 0 or r.x1 > W or r.y0 < 0 or r.y1 > H:
            problems.append(f"{r.what}이 캔버스 밖으로 나간다")

    defs = ('<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" '
            f'orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="{LINE}"/></marker></defs>')
    body = "".join(out_groups + out_edges + out_nodes + out_labels)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
           f'font-family="{FONT}"><rect width="{W}" height="{H}" fill="#fff"/>{defs}{body}</svg>')
    return svg, sorted(set(problems))


def find_chrome():
    cands = [os.environ.get("CHROME_PATH"),
             "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
             "/Applications/Chromium.app/Contents/MacOS/Chromium",
             shutil.which("google-chrome"), shutil.which("chromium"), shutil.which("chromium-browser"),
             r"C:\Program Files\Google\Chrome\Application\chrome.exe"]
    for c in cands:
        if c and pathlib.Path(c).exists():
            return c
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec", nargs="?")
    ap.add_argument("out", nargs="?")
    ap.add_argument("--scale", type=float, default=3)
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--icons", help="이름에 이 글자가 든 아이콘을 찾는다")
    a = ap.parse_args()

    if a.icons:
        q = a.icons.lower()
        for k in sorted(AWS_INDEX):
            if q in k:
                print(f"aws    {k}")
        for k in sorted(BRANDS):
            if q in k or q in BRANDS[k]["title"].lower():
                print(f"brand  {k:20} {BRANDS[k]['title']}")
        return

    spec_path = pathlib.Path(a.spec).resolve()
    out = pathlib.Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    spec = json.loads(spec_path.read_text())
    name = spec.get("name") or spec_path.stem.split(".")[0]
    svg, problems = render(spec)
    (out / f"{name}.svg").write_text(svg)
    html = out / f"{name}.html"
    html.write_text('<!doctype html><meta charset="utf-8"><style>html,body{margin:0;background:#fff}</style>' + svg)
    chrome = find_chrome()
    if chrome:
        W, H = spec["canvas"]["width"], spec["canvas"]["height"]
        png = out / f"{name}.png"
        subprocess.run([chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        f"--force-device-scale-factor={a.scale}", f"--window-size={W},{H}",
                        f"--screenshot={png}", html.as_uri()], check=True, capture_output=True)
        print("saved", png)
    else:
        print("Chrome을 찾지 못해 PNG는 만들지 않았다. CHROME_PATH를 지정한다. SVG/HTML은 저장했다.")
    print("saved", out / f"{name}.svg")
    if problems:
        print(f"\n배치 검사: 문제 {len(problems)}건")
        for p in problems:
            print("  -", p)
    else:
        print("\n배치 검사: 문제 0건")
    if a.strict and problems:
        sys.exit(1)


if __name__ == "__main__":
    main()
