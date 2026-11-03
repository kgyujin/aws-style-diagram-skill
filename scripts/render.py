"""AWS 아키텍처 아이콘 스타일 구성도를 spec JSON으로 그린다(벡터 SVG, 벡터 PDF, PNG).

사용:
  python3 -I render.py <spec.json> <출력폴더> [--scale 3] [--strict] [--no-pdf]
  python3 -I render.py --icons eks          # 아이콘 이름 찾기

spec 형식은 SKILL.md의 'spec 쓰는 법'에 있다. 그린 뒤 배치 검사를 돌려 문제를 출력한다.
--strict를 주면 문제가 하나라도 있을 때 종료 코드 1로 끝난다.

- AWS 서비스, 그룹, 일반 리소스 아이콘은 assets/aws/(공식 AWS Architecture Icons)를 그대로 넣는다.
- AWS가 아닌 기술 로고는 assets/brands/의 글리프를 AWS 서비스 아이콘과 같은 정사각형 타일로 만든다.
- PNG와 PDF는 Chrome(또는 Chromium) headless로 만든다. 경로는 CHROME_PATH 환경 변수로 바꿀 수 있다.

깨짐 방지:
- 모든 글자는 함께 넣은 Pretendard(OFL) 글꼴의 윤곽선(path)으로 바꿔 넣는다. 보는 컴퓨터에
  글꼴이 없어도 모양과 폭이 같고, 배치 검사도 실제 글자 폭으로 잰다(fontTools 사용).
- 아이콘은 <image>로 끼우지 않고 벡터 도형을 그대로 펼쳐 넣는다. id는 아이콘마다 앞머리를 붙여
  겹치지 않게 한다. 화살촉도 marker 대신 삼각형 도형으로 그린다.
- 그래서 SVG에는 글꼴, 외부 파일, 내장 이미지가 하나도 없다. 브라우저, Inkscape, CairoSVG,
  PowerPoint, Word 어디서 열어도 같은 모양이고 확대해도 깨지지 않는다.
"""
import argparse
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

try:
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.transformPen import TransformPen
    from fontTools.ttLib import TTFont
except ImportError:  # 설치 안내를 먼저 보여 준다
    sys.exit("fontTools가 필요하다. `python3 -m pip install fonttools`로 설치한다.")

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
FONT_FILES = {False: ASSETS / "fonts" / "Pretendard-Regular.otf", True: ASSETS / "fonts" / "Pretendard-Bold.otf"}
SVG_NS, XLINK_NS = "http://www.w3.org/2000/svg", "http://www.w3.org/1999/xlink"

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


def icon_svg_text(name):
    kind, key = find_icon(name)
    if kind == "aws":
        return (ASSETS / AWS_INDEX[key]).read_text(encoding="utf-8")
    return brand_tile(key)


_INLINE_COUNT = [0]
_ROOT_PAINT = ("fill", "stroke", "stroke-width", "fill-rule", "clip-rule", "opacity")


def inline_icon(name, x, y, size):
    """아이콘 SVG를 벡터 그룹으로 펼친다. id와 url(#…) 참조에 아이콘마다 다른 앞머리를 붙인다."""
    root = ET.fromstring(icon_svg_text(name))
    _INLINE_COUNT[0] += 1
    pre = f"i{_INLINE_COUNT[0]}-"
    ids = {}
    for el in root.iter():
        el.tag = el.tag.split("}")[-1]
        for k in list(el.attrib):
            v = el.attrib.pop(k)
            nk = "xlink:href" if k == f"{{{XLINK_NS}}}href" else k.split("}")[-1]
            el.attrib[nk] = v
        if "id" in el.attrib:
            new = pre + re.sub(r"[^A-Za-z0-9_-]", "_", el.attrib["id"])
            ids[el.attrib["id"]] = new
            el.attrib["id"] = new
    for el in root.iter():
        for k, v in list(el.attrib.items()):
            if "url(#" in v:
                v = re.sub(r"url\(#([^)]+)\)", lambda m: f"url(#{ids.get(m.group(1), m.group(1))})", v)
            if k in ("href", "xlink:href") and v.startswith("#"):
                v = "#" + ids.get(v[1:], v[1:])
            el.attrib[k] = v
        for t in [c for c in el if c.tag in ("title", "desc")]:
            el.remove(t)
    vb = root.get("viewBox")
    if vb:
        vx, vy, vw, vh = (float(v) for v in vb.replace(",", " ").split())
    else:
        vx, vy = 0.0, 0.0
        vw = float(re.sub(r"[^0-9.]", "", root.get("width", "80")))
        vh = float(re.sub(r"[^0-9.]", "", root.get("height", "80")))
    s = min(size / vw, size / vh)
    ox, oy = x + (size - vw * s) / 2 - vx * s, y + (size - vh * s) / 2 - vy * s
    paint = "".join(f' {k}="{root.get(k)}"' for k in _ROOT_PAINT if root.get(k) is not None)
    inner = "".join(ET.tostring(c, encoding="unicode") for c in root)
    return f'<g transform="translate({ox:.3f} {oy:.3f}) scale({s:.5f})"{paint}>{inner}</g>'


# ---------------------------------------------------------------- 글자 폭 어림
class OutlineFont:
    """글꼴 윤곽선으로 글자 폭을 재고 글자를 path로 바꾼다."""

    def __init__(self, path):
        font = TTFont(str(path))
        self.glyphs = font.getGlyphSet()
        self.cmap = font.getBestCmap()
        self.upm = font["head"].unitsPerEm
        self.hmtx = font["hmtx"]
        self.missing = set()

    def _glyph(self, ch):
        g = self.cmap.get(ord(ch))
        if g is None:
            self.missing.add(ch)
            return ".notdef"
        return g

    def width(self, text, px):
        return sum(self.hmtx[self._glyph(c)][0] for c in text) * px / self.upm

    def path(self, text, x, baseline, px, anchor="start"):
        w = self.width(text, px)
        cx = x - w / 2 if anchor == "middle" else x - w if anchor == "end" else x
        pen = SVGPathPen(self.glyphs, ntos=lambda v: f"{v:.2f}".rstrip("0").rstrip("."))
        s = px / self.upm
        for c in text:
            g = self._glyph(c)
            self.glyphs[g].draw(TransformPen(pen, (s, 0, 0, -s, cx, baseline)))
            cx += self.hmtx[g][0] * s
        return pen.getCommands()


_FONTS = {}


def font(bold=False):
    if bold not in _FONTS:
        _FONTS[bold] = OutlineFont(FONT_FILES[bold])
    return _FONTS[bold]


def text_w(t, px, bold=False):
    return font(bold).width(t, px)


def text_svg(t, x, baseline, px, fill, bold=False, anchor="start"):
    d = font(bold).path(t, x, baseline, px, anchor)
    return f'<path aria-label="{esc(t)}" fill="{fill}" d="{d}"/>' if d else ""


def arrow_head(tip, prev, sw):
    """선 끝(tip)에 삼각형 화살촉을 그리고, 선이 화살촉 밖으로 삐져나오지 않게 줄인 끝점을 돌려준다."""
    length, half = (13, 6) if sw > 2 else (11, 5)
    dx, dy = tip[0] - prev[0], tip[1] - prev[1]
    n = (dx * dx + dy * dy) ** 0.5 or 1
    ux, uy = dx / n, dy / n
    bx, by = tip[0] - ux * length, tip[1] - uy * length
    px, py = -uy * half, ux * half
    poly = f"{tip[0]:.2f},{tip[1]:.2f} {bx + px:.2f},{by + py:.2f} {bx - px:.2f},{by - py:.2f}"
    short = (tip[0] - ux * length * 0.7, tip[1] - uy * length * 0.7)
    return f'<polygon points="{poly}" fill="{LINE}"/>', short


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
    lw = text_w(n["label"], LABEL_PX, bold=True)
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
            s.append(inline_icon(icon, x, y, 30))
            tx = x + 38
        title = g.get("title", "")
        s.append(text_svg(title, tx, y + 21, GROUP_PX, color, bold=True))
        out_groups.append("".join(s))
        group_titles.append(Rect(x, y, tx + text_w(title, GROUP_PX, bold=True) + 4, y + 30, f"그룹 '{title}' 제목"))
        group_rects.append((Rect(x, y, x + w, y + h, f"그룹 '{title}'"), g))
        if x < 0 or y < 0 or x + w > W or y + h > H:
            problems.append(f"그룹 '{title}'이 캔버스 밖으로 나간다")

    all_icon, all_text = [], []
    for n in spec["nodes"]:
        cx, top = n["cx"], n["top"]
        s = [inline_icon(n["icon"], cx - ICON / 2, top, ICON),
             text_svg(n["label"], cx, top + ICON + 22, LABEL_PX, INK, bold=True, anchor="middle")]
        if n.get("sub"):
            s.append(text_svg(n["sub"], cx, top + ICON + 41, SUB_PX, SUB, anchor="middle"))
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
        draw = list(pts)
        head, draw[-1] = arrow_head(pts[-1], pts[-2], sw)
        heads = [head]
        if e.get("both"):
            head0, draw[0] = arrow_head(pts[0], pts[1], sw)
            heads.append(head0)
        d = "M" + " L".join(f"{x:.2f} {y:.2f}" for x, y in draw)
        out_edges.append(f'<path d="{d}" fill="none" stroke="{LINE}" stroke-width="{sw}"{da}/>' + "".join(heads))
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
                                  + text_svg(ln, x, yy + 5, EDGE_PX, INK, anchor="middle"))
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

    body = "".join(out_groups + out_edges + out_nodes + out_labels)
    title = esc(spec.get("title") or spec.get("name") or "diagram")
    svg = (f'<svg xmlns="{SVG_NS}" xmlns:xlink="{XLINK_NS}" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
           f'<title>{title}</title><rect width="{W}" height="{H}" fill="#fff"/>{body}</svg>')
    for bold in (False, True):
        for ch in sorted(font(bold).missing):
            problems.append(f"글꼴에 없는 글자 '{ch}'가 있다(빈 상자로 나온다). 다른 글자로 바꾼다")
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
    ap.add_argument("--no-pdf", action="store_true", help="PDF를 만들지 않는다")
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
    svg_path = out / f"{name}.svg"
    svg_path.write_text(svg, encoding="utf-8")
    print("saved", svg_path)
    W, H = spec["canvas"]["width"], spec["canvas"]["height"]
    html = out / f"{name}.html"
    # @page를 그림 크기에 맞춰 PDF 한 장에 그림 하나가 벡터 그대로 들어가게 한다
    html.write_text('<!doctype html><meta charset="utf-8"><style>'
                    f'@page{{size:{W}px {H}px;margin:0}}html,body{{margin:0;padding:0;background:#fff}}'
                    f'svg{{display:block;width:{W}px;height:{H}px}}</style>' + svg, encoding="utf-8")
    chrome = find_chrome()
    if chrome:
        base = [chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars"]
        png = out / f"{name}.png"
        subprocess.run(base + [f"--force-device-scale-factor={a.scale}", f"--window-size={W},{H}",
                               f"--screenshot={png}", html.as_uri()], check=True, capture_output=True)
        print("saved", png)
        if not a.no_pdf:
            pdf = out / f"{name}.pdf"
            subprocess.run(base + ["--no-pdf-header-footer", "--print-to-pdf-no-header",
                                   f"--print-to-pdf={pdf}", html.as_uri()], check=True, capture_output=True)
            print("saved", pdf)
    else:
        print("Chrome을 찾지 못해 PNG와 PDF는 만들지 않았다(CHROME_PATH로 지정). 벡터 SVG는 저장했다.")
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
