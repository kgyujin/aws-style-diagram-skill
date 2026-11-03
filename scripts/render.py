"""AWS 아키텍처 아이콘 스타일 구성도를 spec JSON으로 그린다(벡터 SVG, 벡터 PDF, PNG).

사용:
  python3 -I render.py <spec.json> <출력폴더> [--scale 4] [--strict] [--no-pdf]
  python3 -I render.py --icons eks          # 아이콘 이름 찾기

spec 형식은 SKILL.md의 'spec 쓰는 법'에 있다. 그린 뒤 배치 검사를 돌려 문제를 출력한다.
--strict를 주면 문제가 하나라도 있을 때 종료 코드 1로 끝난다.

- AWS 서비스, 그룹, 일반 리소스 아이콘은 assets/aws/(공식 AWS Architecture Icons)를 그대로 넣는다.
- AWS가 아닌 기술 로고는 assets/brands/의 글리프를 AWS 서비스 아이콘과 같은 정사각형 타일로 만든다.
- PNG와 PDF는 Chrome(또는 Chromium) headless로 만든다. 경로는 CHROME_PATH 환경 변수로 바꿀 수 있다.
- PNG는 기본 4배로 찍는다. 좌표가 4px 격자이고 선 굵기가 0.5의 배수라 4배면 선 가장자리가 픽셀 경계에
  딱 맞아 흐린 회색 테두리가 생기지 않는다(3배처럼 홀수 배율은 1px 선이 반 픽셀에 걸쳐 번진다).
  PNG에는 해상도(배율 × 96dpi)를 적어 문서에 넣을 때 그림 크기 그대로 고해상도로 들어가게 한다.

양식(기본 테마 editorial):
- diagram-design(cathrynlavery/diagram-design, MIT)의 편집 디자인 체계를 따른다. 색은 역할 토큰
  (paper, ink, muted, soft, accent, link)으로만 쓰고, accent는 그림당 1~2곳(focal)에만 쓴다.
- 글자는 Geist(이름), Geist Mono(기술 값, 영문 라벨), 한글은 Pretendard로 이어 쓴다.
- 선은 직각으로 꺾되 모서리를 r=8로 둥글린다. 라벨은 선 위가 아니라 선에서 8px 떨어진 자리에
  바탕색 상자를 깔고 놓는다. 쓰인 선 종류가 둘 이상이면 아래에 범례 띠를 붙인다.
- 좌표와 크기는 4px 격자에 맞춘다(배치 검사가 확인).
- theme: "aws"를 주면 예전 AWS 공식 그룹 색(보라 VPC, 청록 서브넷 등)으로 그린다.

깨짐 방지:
- 모든 글자는 함께 넣은 OFL 글꼴의 윤곽선(path)으로 바꿔 넣는다. 보는 컴퓨터에 글꼴이 없어도
  모양과 폭이 같고, 배치 검사도 실제 글자 폭으로 잰다(fontTools 사용).
- 아이콘은 <image>로 끼우지 않고 벡터 도형을 그대로 펼쳐 넣는다. id는 아이콘마다 앞머리를 붙여
  겹치지 않게 한다. 화살촉도 marker 대신 삼각형 도형으로, 반투명 색은 rgba 대신 opacity 속성으로 쓴다.
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
import unicodedata
import xml.etree.ElementTree as ET

try:
    from fontTools.pens.recordingPen import DecomposingRecordingPen
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

ICON = 48            # 노드 아이콘 한 변(px). 가운데가 4px 격자에 오도록 4의 배수
BLOCK_H = ICON + 48  # 아이콘 + 이름 + 부제. 아래쪽 연결점은 이 아래에서 나간다
LEGEND_H = 56        # 범례 띠 높이. 캔버스 아래에 자동으로 붙는다
LABEL_GAP = 8        # 라벨 상자와 자기 선 사이 간격(diagram-design 규칙 6~10px)
SVG_NS, XLINK_NS = "http://www.w3.org/2000/svg", "http://www.w3.org/1999/xlink"

# 색 역할 토큰. diagram-design 기본 skin과 같은 값이며 모든 글자 색은 paper 위에서 4.5:1 이상이다.
TOKENS = {
    "paper": "#f5f5f5", "ink": "#2d3142", "muted": "#4f5d75", "soft": "#5a6580",
    "accent": "#bf4520", "link": "#2e5aa8",
}
EDGE_COLOR = {"default": "muted", "primary": "accent", "link": "link"}

# editorial 그룹: (선 불투명도, 점선, 바탕 불투명도, 선 굵기, 기본 아이콘). 색은 모두 ink다.
EDITORIAL_GROUP = {
    "aws-cloud": (0.60, None, 0, 1.5, "group-aws-cloud-logo"),
    "region": (0.45, "4 4", 0, 1, "group-region"),
    "vpc": (0.50, None, 0, 1, "group-virtual-private-cloud-vpc"),
    "private-subnet": (0.25, None, 0.035, 1, "group-private-subnet"),
    "public-subnet": (0.25, None, 0.035, 1, "group-public-subnet"),
    "account": (0.50, None, 0, 1, "group-aws-account"),
    "eks": (0.45, "4 3", 0, 1, "eks"),
    "auto-scaling": (0.45, "4 3", 0, 1, "group-auto-scaling-group"),
    "datacenter": (0.45, None, 0, 1, "group-corporate-data-center"),
    "box": (0.35, None, 0, 1, None),
    "box-dashed": (0.40, "4 3", 0, 1, None),
}
# aws 테마 그룹(AWS 공식 그룹 색): (색, 점선 여부, 바탕, 기본 아이콘)
AWS_GROUP = {
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
DEFAULT_LEGEND = {
    "focal": "핵심 구성 요소",
    "primary": "주 요청 흐름",
    "link": "외부 호출, API",
    "default": "내부 연결",
    "dashed": "비동기, 가끔 쓰는 흐름",
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
# ---------------------------------------------------------------- 글꼴과 글자
FONT_FILES = {
    "geist-400": "Geist-Regular.otf", "geist-500": "Geist-Medium.otf", "geist-600": "Geist-SemiBold.otf",
    "mono-400": "GeistMono-Regular.otf", "mono-500": "GeistMono-Medium.otf",
    "pre-400": "Pretendard-Regular.otf", "pre-500": "Pretendard-Medium.otf", "pre-600": "Pretendard-SemiBold.otf",
}
# 글자 역할: (글꼴 순서, 크기 px, 자간 em, 대문자로 바꿀지). 한글은 Geist에 없으므로 Pretendard로 넘어간다.
TEXT_ROLES = {
    "name": (("geist-600", "pre-600"), 17, 0, False),          # 노드 이름
    "sub": (("geist-400", "pre-400"), 14, 0, False),           # 한글이 든 부제
    "sub-mono": (("mono-400", "pre-400"), 13, 0, False),       # 포트, 서비스 이름 같은 기술 값
    "label": (("geist-500", "pre-500"), 14, 0, False),         # 한글이 든 선 라벨
    "label-mono": (("mono-500", "pre-500"), 12.5, 0.06, True), # 영문 선 라벨(대문자, 자간)
    "eyebrow": (("geist-600", "pre-600"), 14, 0, False),       # 한글이 든 그룹 제목
    "eyebrow-mono": (("mono-500", "pre-500"), 12, 0.14, True), # 영문 그룹 제목(대문자, 자간)
    "legend": (("geist-400", "pre-400"), 13, 0, False),
    "legend-head": (("mono-500",), 11, 0.18, True),
}


class OutlineFont:
    """글꼴 하나의 글리프 폭과 윤곽선."""

    def __init__(self, path):
        font = TTFont(str(path))
        self.glyphs = font.getGlyphSet()
        self.cmap = font.getBestCmap()
        self.upm = font["head"].unitsPerEm
        self.hmtx = font["hmtx"]


_FONTS = {}
MISSING = set()


def _font(key):
    if key not in _FONTS:
        _FONTS[key] = OutlineFont(ASSETS / "fonts" / FONT_FILES[key])
    return _FONTS[key]


def is_wide(t):
    """한글, 한자처럼 전각 글자가 있으면 mono/대문자 자리 대신 sans 자리를 쓴다."""
    return any(unicodedata.east_asian_width(c) in ("W", "F") for c in t)


def _glyph_runs(text, keys):
    """글자마다 그 글자가 있는 첫 글꼴을 고른다."""
    for c in text:
        if unicodedata.category(c) in ("Mn", "Me", "Cf"):
            continue
        for k in keys:
            f = _font(k)
            g = f.cmap.get(ord(c))
            if g is not None:
                yield f, g
                break
        else:
            MISSING.add(c)
            f = _font(keys[-1])
            yield f, ".notdef"


def _prep(role, t):
    keys, px, track, upper = TEXT_ROLES[role]
    return keys, px, track * px, (t.upper() if upper else t)


def text_w(role, t):
    keys, px, track, t = _prep(role, t)
    runs = list(_glyph_runs(t, keys))
    w = sum(f.hmtx[g][0] * px / f.upm for f, g in runs)
    return w + track * max(len(runs) - 1, 0)


def text_svg(role, t, x, baseline, fill, anchor="start", opacity=None):
    keys, px, track, t = _prep(role, t)
    w = text_w(role, t)
    cx = x - w / 2 if anchor == "middle" else x - w if anchor == "end" else x
    pen = SVGPathPen(None, ntos=lambda v: f"{v:.2f}".rstrip("0").rstrip("."))
    for f, g in _glyph_runs(t, keys):
        s = px / f.upm
        rec = DecomposingRecordingPen(f.glyphs)   # 합성 글리프도 낱낱의 윤곽선으로 푼다
        f.glyphs[g].draw(rec)
        rec.replay(TransformPen(pen, (s, 0, 0, -s, cx, baseline)))
        cx += f.hmtx[g][0] * s + track
    d = pen.getCommands()
    op = f' fill-opacity="{opacity}"' if opacity is not None else ""
    return f'<path aria-label="{esc(t)}" fill="{fill}"{op} d="{d}"/>' if d else ""


def sub_role(t):
    return "sub" if is_wide(t) else "sub-mono"


def label_role(t):
    return "label" if is_wide(t) else "label-mono"


def eyebrow_role(t):
    return "eyebrow" if is_wide(t) else "eyebrow-mono"


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


# ---------------------------------------------------------------- 선
def arrow_head(tip, prev, color):
    """선 끝(tip)에 삼각형 화살촉을 그리고, 선이 화살촉 밖으로 삐져나오지 않게 줄인 끝점을 돌려준다."""
    length, half = 11, 4.5
    dx, dy = tip[0] - prev[0], tip[1] - prev[1]
    n = (dx * dx + dy * dy) ** 0.5 or 1
    ux, uy = dx / n, dy / n
    bx, by = tip[0] - ux * length, tip[1] - uy * length
    px, py = -uy * half, ux * half
    poly = f"{tip[0]:.2f},{tip[1]:.2f} {bx + px:.2f},{by + py:.2f} {bx - px:.2f},{by - py:.2f}"
    short = (tip[0] - ux * length * 0.7, tip[1] - uy * length * 0.7)
    return f'<polygon points="{poly}" fill="{color}"/>', short


def rounded_path(pts, r=8):
    """직각 꺾임마다 반지름 r의 사분원을 넣는다(diagram-design 커넥터 규칙 1)."""
    f = lambda p: f"{p[0]:.2f} {p[1]:.2f}"
    d = [f"M{f(pts[0])}"]
    for a, b, c in zip(pts, pts[1:], pts[2:]):
        v1 = (b[0] - a[0], b[1] - a[1])
        v2 = (c[0] - b[0], c[1] - b[1])
        l1 = (v1[0] ** 2 + v1[1] ** 2) ** 0.5 or 1
        l2 = (v2[0] ** 2 + v2[1] ** 2) ** 0.5 or 1
        u1, u2 = (v1[0] / l1, v1[1] / l1), (v2[0] / l2, v2[1] / l2)
        cross = u1[0] * u2[1] - u1[1] * u2[0]
        if abs(cross) < 1e-6:
            d.append(f"L{f(b)}")
            continue
        rr = min(r, l1 / 2, l2 / 2)
        p = (b[0] - u1[0] * rr, b[1] - u1[1] * rr)
        q = (b[0] + u2[0] * rr, b[1] + u2[1] * rr)
        d.append(f"L{f(p)} A{rr:.2f} {rr:.2f} 0 0 {1 if cross > 0 else 0} {f(q)}")
    d.append(f"L{f(pts[-1])}")
    return " ".join(d)


def _seg_dist(p, a, b):
    (x, y), (x0, y0), (x1, y1) = p, a, b
    dx, dy = x1 - x0, y1 - y0
    t = 0 if dx == dy == 0 else max(0, min(1, ((x - x0) * dx + (y - y0) * dy) / (dx * dx + dy * dy)))
    return ((x - x0 - t * dx) ** 2 + (y - y0 - t * dy) ** 2) ** 0.5


def place_label(segs, at, side, w, h):
    """라벨 상자의 가운데를 정한다. 선 위가 아니라 선에서 LABEL_GAP만큼 떨어진 자리다.
    가로 구간이면 위(side='below'면 아래), 세로 구간이면 오른쪽(side='left'면 왼쪽)에 둔다."""
    if at:
        a, b = min(segs, key=lambda s: _seg_dist(at, *s))
    else:
        a, b = max(segs, key=lambda s: abs(s[0][0] - s[1][0]) + abs(s[0][1] - s[1][1]))
    if a[1] == b[1]:   # 가로 구간
        lo, hi = sorted((a[0], b[0]))
        x = at[0] if at else (lo + hi) / 2
        x = min(max(x, lo + w / 2), hi - w / 2) if hi - lo > w else (lo + hi) / 2
        y = a[1] + (LABEL_GAP + h / 2) * (1 if side == "below" else -1)
    else:              # 세로 구간
        lo, hi = sorted((a[1], b[1]))
        y = at[1] if at else (lo + hi) / 2
        y = min(max(y, lo + h / 2), hi - h / 2) if hi - lo > h else (lo + hi) / 2
        x = a[0] + (LABEL_GAP + w / 2) * (-1 if side == "left" else 1)
    return x, y


def up4(v):
    return -(-v // 4) * 4


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
    lw = text_w("name", n["label"])
    texts = [Rect(cx - lw / 2, top + ICON + 6, cx + lw / 2, top + ICON + 27, f"{n['id']} 이름")]
    if n.get("sub"):
        sw = text_w(sub_role(n["sub"]), n["sub"])
        texts.append(Rect(cx - sw / 2, top + ICON + 29, cx + sw / 2, top + ICON + 46, f"{n['id']} 부제"))
    return icon, texts


def focal_box(n):
    """focal 노드를 감싸는 강조 상자(x0, y0, x1, y1). 폭은 아이콘과 글자 중 넓은 쪽 + 24를 4의 배수로 올린 값."""
    _, texts = node_rects(n)
    bw = up4(max([ICON] + [t.x1 - t.x0 for t in texts]) + 24)
    return n["cx"] - bw / 2, n["top"] - 12, n["cx"] + bw / 2, n["top"] + BLOCK_H + 4


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
    if n.get("focal"):   # 강조 상자가 있으면 선은 상자 테두리에서 끝난다
        x0, y0, x1, y1 = focal_box(n)
        return {"l": (x0 - 2, cy + off), "r": (x1 + 2, cy + off),
                "t": (cx + off, y0 - 2), "b": (cx + off, y1 + 2)}[m.group(2)]
    return {
        "l": (cx - ICON / 2 - 4, cy + off),
        "r": (cx + ICON / 2 + 4, cy + off),
        "t": (cx + off, top - 4),
        "b": (cx + off, top + BLOCK_H),
    }[m.group(2)]


# ---------------------------------------------------------------- 그리기
def _off_grid(what, *vals):
    bad = [v for v in vals if isinstance(v, (int, float)) and v % 4]
    return [f"4px 격자에 맞지 않는다: {what} {bad}"] if bad else []


def render(spec):
    W, H = spec["canvas"]["width"], spec["canvas"]["height"]
    theme = spec.get("theme", "editorial")
    paper = "#ffffff" if spec.get("background") == "white" or theme == "aws" else TOKENS["paper"]
    ink, soft = TOKENS["ink"], TOKENS["soft"]
    nodes = {n["id"]: n for n in spec["nodes"]}
    out_groups, out_focal, out_edges, out_nodes, out_labels = [], [], [], [], []
    problems, advice = [], []
    group_titles, group_rects = [], []
    used = set()
    MISSING.clear()

    problems += _off_grid("캔버스", W, H)
    for g in spec.get("groups", []):
        x, y, w, h = g["x"], g["y"], g["w"], g["h"]
        title = g.get("title", "")
        problems += _off_grid(f"그룹 '{title}' x,y,w,h", x, y, w, h)
        gtype = g.get("type", "box")
        if theme == "aws":
            color, dash, fill, default_icon = AWS_GROUP[gtype]
            color = g.get("color", color)
            da = ' stroke-dasharray="6 4"' if dash else ""
            s = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{color}" stroke-width="1.5"{da}/>']
            icon, ix, iy, isz, tx = g.get("icon", default_icon), x, y, 30, x + 10
            tcolor, topacity = color, None
        else:
            alpha, dash, fill_a, sw, default_icon = EDITORIAL_GROUP[gtype]
            da = f' stroke-dasharray="{dash}"' if dash else ""
            fill = f'"{ink}" fill-opacity="{fill_a}"' if fill_a else '"none"'
            s = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill={fill} '
                 f'stroke="{g.get("color", ink)}" stroke-opacity="{alpha}" stroke-width="{sw}"{da}/>']
            icon, ix, iy, isz, tx = g.get("icon", default_icon), x + 10, y + 8, 22, x + 12
            tcolor, topacity = soft, None
        if icon:
            s.append(inline_icon(icon, ix, iy, isz))
            tx = ix + isz + 8
        role = eyebrow_role(title)
        s.append(text_svg(role, title, tx, y + 24 if theme != "aws" else y + 21, tcolor, opacity=topacity))
        out_groups.append("".join(s))
        group_titles.append(Rect(x, y, tx + text_w(role, title) + 4, y + 32, f"그룹 '{title}' 제목"))
        group_rects.append((Rect(x, y, x + w, y + h, f"그룹 '{title}'"), g))
        if x < 0 or y < 0 or x + w > W or y + h > H:
            problems.append(f"그룹 '{title}'이 캔버스 밖으로 나간다")

    all_icon, all_text = [], []
    focal = [n for n in spec["nodes"] if n.get("focal")]
    if len(focal) > 2:
        problems.append(f"focal 노드가 {len(focal)}개다. 강조는 그림당 1~2곳만 쓴다")
    for n in spec["nodes"]:
        cx, top = n["cx"], n["top"]
        problems += _off_grid(f"노드 '{n['id']}' cx,top", cx, top)
        icon, texts = node_rects(n)
        if n.get("focal"):
            used.add("focal")
            x0, y0, x1, y1 = focal_box(n)
            out_focal.append(f'<rect x="{x0}" y="{y0}" width="{x1 - x0}" height="{y1 - y0}" rx="8" '
                             f'fill="{TOKENS["accent"]}" fill-opacity="0.08" stroke="{TOKENS["accent"]}" stroke-width="1.5"/>')
        s = [inline_icon(n["icon"], cx - ICON / 2, top, ICON),
             text_svg("name", n["label"], cx, top + ICON + 22, ink, anchor="middle")]
        if n.get("sub"):
            s.append(text_svg(sub_role(n["sub"]), n["sub"], cx, top + ICON + 41, soft, anchor="middle"))
        out_nodes.append("".join(s))
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
        for p in e["path"]:
            if not isinstance(p, str):
                problems += _off_grid(f"선 좌표", *p)
        ends = {p.split(".")[0] for p in (e["path"][0], e["path"][-1]) if isinstance(p, str)}
        kind = e.get("kind") or ("primary" if e.get("bold") else "default")
        color = TOKENS[EDGE_COLOR[kind]]
        dashed = e.get("style") == "dashed"
        used.add(kind)
        if dashed:
            used.add("dashed")
        draw = list(pts)
        head, draw[-1] = arrow_head(pts[-1], pts[-2], color)
        heads = [head]
        if e.get("both"):
            head0, draw[0] = arrow_head(pts[0], pts[1], color)
            heads.append(head0)
        da = ' stroke-dasharray="5 4"' if dashed else ""
        sw = 2 if kind == "primary" else 1.5   # 0.5의 배수라야 PNG 4배에서 선이 픽셀에 맞는다
        out_edges.append(f'<path d="{rounded_path(draw)}" fill="none" stroke="{color}" stroke-width="{sw}" '
                         f'stroke-linecap="round" stroke-linejoin="round"{da}/>' + "".join(heads))
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
            lines = e["label"].split("\n")
            roles = [label_role(ln) for ln in lines]
            if any(not is_wide(ln) and len(ln) > 14 for ln in lines):
                advice.append(f"영문 라벨 '{e['label']}'이 14자를 넘는다. 줄이면 더 깔끔하다")
            lh = 20 if any(r == "label" for r in roles) else 18
            w = up4(max(text_w(r, ln) for r, ln in zip(roles, lines)) + 12)
            h = lh * len(lines)
            at = tuple(e["at"]) if "at" in e else None
            if at:
                problems += _off_grid(f"선 라벨 '{e['label']}' at", *at)
            x, y = place_label(segs, at, e.get("labelSide"), w, h)
            out_labels.append(f'<rect x="{x - w / 2:.1f}" y="{y - h / 2:.1f}" width="{w}" height="{h}" rx="2" fill="{paper}"/>')
            for k, (r, ln) in enumerate(zip(roles, lines)):
                base = y - h / 2 + lh * k + lh / 2 + (5 if r == "label" else 4.5)
                out_labels.append(text_svg(r, ln, x, base, color if kind != "default" else soft, anchor="middle"))
            label_rects.append((Rect(x - w / 2, y - h / 2, x + w / 2, y + h / 2, f"선 라벨 '{e['label']}'"), i))

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
            if j == i and r.hits_seg(a, b, pad=-1):
                problems.append(f"{r.what}이 자기 선에 닿는다(선에서 6px 이상 띄운다)")
        for gt in group_titles:
            if r.hits(gt):
                problems.append(f"{r.what}이 {gt.what}과 겹친다")
        for gr, _ in group_rects:
            inside = gr.x0 < r.x0 and r.x1 < gr.x1 and gr.y0 < r.y0 and r.y1 < gr.y1
            if gr.hits(r) and not inside:
                problems.append(f"{r.what}이 {gr.what} 테두리에 걸친다")
        if r.x0 < 0 or r.x1 > W or r.y0 < 0 or r.y1 > H:
            problems.append(f"{r.what}이 캔버스 밖으로 나간다")

    # 범례: 쓰인 종류가 둘 이상이거나 focal이 있을 때만 붙인다(diagram-design: 쓰인 것만, 아래 띠로)
    legend_cfg = spec.get("legend", True)
    order = [k for k in ("focal", "primary", "link", "default", "dashed") if k in used]
    legend = []
    if legend_cfg is not False and (len(order) >= 2 or "focal" in order):
        names = dict(DEFAULT_LEGEND, **(legend_cfg if isinstance(legend_cfg, dict) else {}))
        y0 = H + 4
        legend.append(f'<line x1="24" y1="{y0}" x2="{W - 24}" y2="{y0}" stroke="{ink}" stroke-opacity="0.12" stroke-width="1"/>')
        by = y0 + 32
        legend.append(text_svg("legend-head", "legend", 24, by, TOKENS["muted"]))
        x = 24 + text_w("legend-head", "legend") + 28
        for k in order:
            if k == "focal":
                legend.append(f'<rect x="{x}" y="{by - 11}" width="24" height="14" rx="3" fill="{TOKENS["accent"]}" '
                              f'fill-opacity="0.08" stroke="{TOKENS["accent"]}" stroke-width="1.5"/>')
            else:
                c = TOKENS["muted"] if k == "dashed" else TOKENS[EDGE_COLOR[k]]
                da = ' stroke-dasharray="5 4"' if k == "dashed" else ""
                head, end = arrow_head((x + 32, by - 4), (x, by - 4), c)
                legend.append(f'<path d="M{x} {by - 4} L{end[0]:.2f} {end[1]:.2f}" stroke="{c}" stroke-width="1.5"{da}/>' + head)
            legend.append(text_svg("legend", names[k], x + 40, by, ink))
            x += 40 + text_w("legend", names[k]) + 32
        if x > W:
            problems.append("범례가 캔버스 폭을 넘는다. 범례 이름을 줄이거나 캔버스를 넓힌다")
    total_h = H + (LEGEND_H if legend else 0)

    n_primary = sum(1 for e in spec.get("edges", []) if (e.get("kind") or ("primary" if e.get("bold") else "")) == "primary")
    if n_primary > 3:
        advice.append(f"주 흐름(강조색) 선이 {n_primary}개다. 강조색은 핵심 경로 하나에만 쓰는 편이 눈에 잘 띈다")
    if len(spec["nodes"]) > 9:
        advice.append(f"노드가 {len(spec['nodes'])}개다. 9개를 넘으면 전체도와 상세도 두 장으로 나누는 편이 읽기 쉽다")
    if len(spec.get("edges", [])) > 12:
        advice.append(f"선이 {len(spec['edges'])}개다. 12개를 넘으면 두 장으로 나누는 편이 읽기 쉽다")

    slug = re.sub(r"[^A-Za-z0-9_-]", "-", spec.get("name") or "diagram")
    title = esc(spec.get("title") or spec.get("name") or "diagram")
    desc = esc(spec.get("desc") or f"구성 요소 {len(spec['nodes'])}개와 연결 {len(spec.get('edges', []))}개로 된 아키텍처 구성도")
    body = "".join(out_groups + out_focal + out_edges + out_nodes + out_labels + legend)
    svg = (f'<svg xmlns="{SVG_NS}" xmlns:xlink="{XLINK_NS}" width="{W}" height="{total_h}" viewBox="0 0 {W} {total_h}" '
           f'role="img" aria-labelledby="{slug}-title {slug}-desc">'
           f'<title id="{slug}-title">{title}</title><desc id="{slug}-desc">{desc}</desc>'
           f'<rect width="{W}" height="{total_h}" fill="{paper}"/>{body}</svg>')
    for ch in sorted(MISSING):
        problems.append(f"글꼴에 없는 글자 '{ch}'가 있다(빈 상자로 나온다). 다른 글자로 바꾼다")
    return svg, sorted(set(problems)), advice, (W, total_h, paper)


def set_png_dpi(path, dpi):
    """PNG에 pHYs(해상도)를 넣는다. 없으면 72dpi로 여겨 문서에 너무 크게 들어갔다가 줄며 뭉개진다."""
    import struct
    import zlib
    b = path.read_bytes()
    ppm = round(dpi / 0.0254)
    body = b"pHYs" + struct.pack(">IIB", ppm, ppm, 1)
    chunk = struct.pack(">I", 9) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)
    out, i = [b[:8]], 8
    while i < len(b):
        n = struct.unpack(">I", b[i:i + 4])[0]
        kind = b[i + 4:i + 8]
        if kind != b"pHYs":
            out.append(b[i:i + 12 + n])
        if kind == b"IHDR":
            out.append(chunk)
        i += 12 + n
    path.write_bytes(b"".join(out))


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
    ap.add_argument("--scale", type=int, default=4, help="PNG 배율. 짝수(4, 6, 8)라야 선이 픽셀에 맞는다")
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
    svg, problems, advice, (W, H, paper) = render(spec)
    svg_path = out / f"{name}.svg"
    svg_path.write_text(svg, encoding="utf-8")
    print("saved", svg_path)
    html = out / f"{name}.html"
    # @page를 그림 크기에 맞춰 PDF 한 장에 그림 하나가 벡터 그대로 들어가게 한다
    html.write_text('<!doctype html><meta charset="utf-8"><style>'
                    f'@page{{size:{W}px {H}px;margin:0}}html,body{{margin:0;padding:0;background:{paper}}}'
                    f'svg{{display:block;width:{W}px;height:{H}px}}</style>' + svg, encoding="utf-8")
    chrome = find_chrome()
    if chrome:
        base = [chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars"]
        png = out / f"{name}.png"
        subprocess.run(base + [f"--force-device-scale-factor={a.scale}", f"--window-size={W},{H}",
                               f"--screenshot={png}", html.as_uri()], check=True, capture_output=True)
        set_png_dpi(png, 96 * a.scale)
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
    if advice:
        print("\n권고(고치지 않아도 되지만 고치면 더 깔끔하다):")
        for p in advice:
            print("  -", p)
    if a.strict and problems:
        sys.exit(1)


if __name__ == "__main__":
    main()
