#!/usr/bin/env python3
"""ACI 工程管理教學網「藍圖」字卡產生器（1080x1080 PNG）

給 FB 粉專「建築室內營造工程管理教學」（aci-easylearn.com）用的工程圖面風格字卡：
深藍底＋細格線、雙線圖框、DWG NO. 圖號列、兩行大標（白／黃）、尺寸線副標、
2~6 格附角標的說明框、左下大數字（或一句重點）、右下工程圖標題欄。

用法：
    python3 fb_blueprint_card.py spec.json out.png

spec.json 欄位（* 為必填）：
{
  "dwg_no":   "ACI-1021",            * 圖號，顯示為黃色
  "rev":      "2026",                  版次（預設 2026）
  "tag":      "EXAM",                  圖號列最後的黃色標籤（預設 NEW）
  "headline": ["第一行（白）", "第二行（黃）"],   * 兩行大標，自動縮字到同一字級
  "subtitle": "尺寸線中間的短副標",     * 畫成 |——— text ———|
  "lead":     "副標下方的一句說明",       選填，白色一行（太長會縮字或換兩行）
  "boxes": [                           * 2~6 格；2/4 格排 2 欄，3/6 格排 3 欄，5 格排 3+2
    {"code": "TF = LS - ES",           黃色等寬小標（可含中文，會自動換用中文字型）
     "title": "總浮時",                 白色粗體標題（單行，自動縮字）
     "note": "最多可晚幾天開始…",        淺灰說明（自動換行，最多 3 行）
     "highlight": false}               選填，true 時框線改黃色強調
  ],
  "big": {                             選填，左下大數字區（有 big 時不畫 takeaway）
    "value":   "4 天",                  黃色超大字
    "label":   "總浮時 TF",             白色粗體，接在大字右側
    "caption": "答案 (1)・TF＝9－5"      灰色小字，在 label 下方
  },
  "takeaway": "一句重點",               選填，沒有 big 時畫在左下（自動換行，最多 3 行）
  "project":  "建築室內營造工程管理教學",  標題欄 PROJECT（預設值如左）
  "scale":    "1:1",                    標題欄 SCALE
  "url":      "aci-easylearn.com"        標題欄 URL
}

所有文字皆會依所在區塊自動縮字／換行，不會溢出或彼此重疊；
縮到下限仍放不下時會在 stderr 印出 WARNING，請縮短文字。
輸出為 128 色量化、optimize 的 PNG。
"""
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

W = H = 1080
BG = (18, 50, 95)            # #12325f
BOX_FILL = (14, 40, 80, 150)
YEL = (245, 197, 24)          # #F5C518
WHITE = (246, 248, 252)
GREY = (160, 176, 200)
NOTE = (196, 208, 226)
LINE = (214, 224, 238)
BRACKET = (236, 216, 150)

NOTO = "/usr/share/fonts/opentype/noto/NotoSansCJK-{}.ttc"
MONO_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/dejavu/DejaVuSansMono.ttf",
]

# layout constants
FRAME_OUT, FRAME_IN = 54, 64
L, R = 104, W - 104
TB_W, TB_ROW = 396, 44           # title block width / row height
TB_BOTTOM = H - FRAME_IN - 34
TB_TOP = TB_BOTTOM - 3 * TB_ROW
WARN = []

_font_cache = {}


def cjk(weight, size):
    key = (weight, size)
    if key not in _font_cache:
        path = NOTO.format(weight)
        f = None
        for idx in (3, 0):
            try:
                f = ImageFont.truetype(path, size, index=idx)
                break
            except Exception:
                continue
        if f is None:
            raise SystemExit("Cannot load font " + path)
        _font_cache[key] = f
    return _font_cache[key]


def _mono_path():
    for p in MONO_CANDIDATES:
        if os.path.exists(p):
            return p
    try:
        import subprocess
        out = subprocess.run(["fc-list", ":family=DejaVu Sans Mono", "file"],
                             capture_output=True, text=True).stdout
        for line in out.splitlines():
            p = line.split(":")[0].strip()
            if p:
                return p
    except Exception:
        pass
    raise SystemExit("DejaVu Sans Mono not found (apt-get install fonts-dejavu-core)")


MONO_PATH = _mono_path()


def mono(size):
    key = ("mono", size)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(MONO_PATH, size)
    return _font_cache[key]


# ---------------------------------------------------------------- text utils
def is_cjk(ch):
    return ord(ch) >= 0x2E80


def mixed_runs(text, size, tracking=0):
    """Split text into (substr, font) runs: mono for Latin, CJK Regular for CJK."""
    runs, cur, cur_cjk = [], "", None
    for ch in text:
        c = is_cjk(ch)
        if cur and c != cur_cjk:
            runs.append((cur, cjk("Medium", size) if cur_cjk else mono(size)))
            cur = ""
        cur += ch
        cur_cjk = c
    if cur:
        runs.append((cur, cjk("Medium", size) if cur_cjk else mono(size)))
    return runs


def mono_width(text, size, tracking):
    w = 0
    for s, f in mixed_runs(text, size):
        for ch in s:
            w += f.getlength(ch) + tracking
    return max(0, w - tracking)


def draw_mono(d, xy, text, size, fill, tracking):
    """Monospace with letter spacing; CJK falls back to Noto. xy is top of em box."""
    x, y = xy
    for s, f in mixed_runs(text, size):
        for ch in s:
            d.text((x, y), ch, font=f, fill=fill)
            x += f.getlength(ch) + tracking
    return x


def text_w(text, f):
    return f.getlength(text)


NO_START = set("，。、；：？！）」』》〉】,.;:?!)]%")


BREAK_AFTER = set("，。、；：？！）」』,;:?!)")


def _score(lines, f, max_w):
    """Higher is better: breaks after punctuation, no orphans, even line lengths."""
    if len(lines) <= 1:
        return 0
    sc = 0.0
    for ln in lines[:-1]:
        if ln and ln[-1] in BREAK_AFTER:
            sc += 10
        elif ln and ln[-1].isascii() and ln[-1].isalnum():
            sc += 2
    if len(lines[-1].strip()) <= 2:
        sc -= 30
    widths = [text_w(l, f) for l in lines]
    sc -= 6 * (max(widths) - min(widths)) / max_w
    return sc


def wrap(text, f, max_w):
    """Nice wrap: honours explicit \n; among all widths that give the minimum number
    of lines, picks the layout that breaks after punctuation and avoids 1-2 char
    orphans on the last line."""
    out = []
    for para in str(text).split("\n"):
        base = _wrap(para, f, max_w)
        n = len(base)
        best, best_sc = base, _score(base, f, max_w)
        if n > 1:
            w = max_w
            while w > max_w * 0.45:
                cand = _wrap(para, f, w)
                if len(cand) > n:
                    break
                sc = _score(cand, f, max_w)
                if sc > best_sc + 1e-6:
                    best, best_sc = cand, sc
                w -= 3
        out.extend(best)
    return out


def _wrap(text, f, max_w):
    """Character-level wrap for CJK; keeps Latin words together; no leading punct."""
    tokens, buf = [], ""
    for ch in text:
        if ch.isascii() and (ch.isalnum() or ch in ".-_/:%"):
            buf += ch
        else:
            if buf:
                tokens.append(buf)
                buf = ""
            tokens.append(ch)
    if buf:
        tokens.append(buf)
    lines, cur = [], ""
    for t in tokens:
        if text_w(cur + t, f) <= max_w or not cur:
            cur += t
        else:
            if t in NO_START or (len(t) == 1 and t in NO_START):
                # pull last char down instead of starting a line with punctuation
                if len(cur) > 1:
                    lines.append(cur[:-1])
                    cur = cur[-1] + t
                    continue
            # prefer breaking right after punctuation if it is in the latter part
            cut = max((i for i, ch in enumerate(cur) if ch in BREAK_AFTER), default=-1)
            if 0 <= cut < len(cur) - 1 and cut + 1 >= len(cur) * 0.4:
                lines.append(cur[:cut + 1])
                cur = cur[cut + 1:].lstrip() + t
                continue
            lines.append(cur.rstrip())
            cur = t.lstrip() if t != " " else ""
    if cur:
        lines.append(cur)
    return lines


def ink_box(f, text):
    """(top_offset, height) of the ink relative to draw y."""
    b = f.getbbox(text)
    return b[1], b[3] - b[1]


def fit_single(text, weight, max_size, min_size, max_w, max_h=None, warn=True):
    s = max_size
    while s >= min_size:
        f = cjk(weight, s)
        ok = text_w(text, f) <= max_w
        if ok and max_h is not None:
            ok = ink_box(f, text)[1] <= max_h
        if ok:
            return f
        s -= 1
    if warn:
        WARN.append("min size reached for: " + text)
    return None if not warn else cjk(weight, min_size)


# ---------------------------------------------------------------- drawing
def draw_background(img):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    minor, major = 22, 110
    off = (W - (W // minor) * minor) // 2
    for i in range(0, W // minor + 1):
        p = off + i * minor
        a = 34 if (p - off) % major == 0 else 14
        w = 1
        d.line([(p, 0), (p, H)], fill=(190, 210, 240, a), width=w)
        d.line([(0, p), (W, p)], fill=(190, 210, 240, a), width=w)
    img.alpha_composite(ov)
    d = ImageDraw.Draw(img)
    d.rectangle([FRAME_OUT, FRAME_OUT, W - FRAME_OUT, H - FRAME_OUT], outline=LINE + (230,), width=2)
    d.rectangle([FRAME_IN, FRAME_IN, W - FRAME_IN, H - FRAME_IN], outline=LINE + (150,), width=1)


def draw_header(d, spec, y):
    size, tr = 21, 3
    segs = [("DWG NO. ", GREY), (spec["dwg_no"], YEL), (" · REV ", GREY),
            (str(spec.get("rev", "2026")), GREY), (" · ", GREY), (spec.get("tag", "NEW"), YEL)]
    total = sum(mono_width(s, size, tr) + tr for s, _ in segs)
    while total > R - L and size > 14:
        size -= 1
        total = sum(mono_width(s, size, tr) + tr for s, _ in segs)
    x = L
    for s, c in segs:
        x = draw_mono(d, (x, y), s, size, c, tr)
    return y + size + 4


def draw_headline(d, lines, y):
    lines = (list(lines) + ["", ""])[:2]
    s = 80
    while s > 40:
        f = cjk("Black", s)
        if all(text_w(t, f) <= R - L for t in lines):
            break
        s -= 1
    else:
        WARN.append("headline at min size")
    f = cjk("Black", s)
    lh = int(s * 1.18)
    # align ink top with y
    top_off = f.getbbox("工")[1]
    d.text((L - 2, y - top_off), lines[0], font=f, fill=WHITE)
    d.text((L - 2, y - top_off + lh), lines[1], font=f, fill=YEL)
    return y + lh + f.getbbox("工")[3] - top_off


def draw_dimension(d, text, y):
    seg, gap, tick = 104, 16, 9
    s = 25
    while True:
        f = cjk("Regular", s)
        tw = text_w(text, f)
        if 2 * (seg + gap) + tw <= R - L or s <= 16:
            break
        s -= 1
    if 2 * (seg + gap) + tw > R - L:
        seg = max(30, int((R - L - tw) / 2 - gap))
    top, h = ink_box(f, "工")
    cy = y + h // 2 + 1
    x0 = L
    x1 = x0 + seg
    d.line([(x0, cy), (x1, cy)], fill=LINE, width=2)
    d.line([(x0, cy - tick), (x0, cy + tick)], fill=LINE, width=2)
    tx = x1 + gap
    d.text((tx, y - top), text, font=f, fill=NOTE)
    x2 = tx + tw + gap
    x3 = x2 + seg
    d.line([(x2, cy), (x3, cy)], fill=LINE, width=2)
    d.line([(x3, cy - tick), (x3, cy + tick)], fill=LINE, width=2)
    return y + h


def draw_lead(d, text, y):
    s = 30
    while s > 24:
        f = cjk("Medium", s)
        if text_w(text, f) <= R - L:
            break
        s -= 1
    f = cjk("Medium", s)
    lines = wrap(text, f, R - L)[:2]
    top, h = ink_box(f, "工")
    lh = int(s * 1.45)
    for i, ln in enumerate(lines):
        d.text((L, y - top + i * lh), ln, font=f, fill=WHITE)
    return y + (len(lines) - 1) * lh + h


def row_plan(n, cols=None):
    if cols:
        return [cols] * (n // cols) + ([n % cols] if n % cols else [])
    return {1: [1], 2: [2], 3: [3], 4: [2, 2], 5: [3, 2], 6: [3, 3]}.get(n, [3] * (n // 3) + [n % 3])


def draw_brackets(d, x0, y0, x1, y1, color):
    o, k, w = 7, 16, 2
    d.line([(x0 - o, y0 - o), (x0 - o + k, y0 - o)], fill=color, width=w)
    d.line([(x0 - o, y0 - o), (x0 - o, y0 - o + k)], fill=color, width=w)
    d.line([(x1 + o, y1 + o), (x1 + o - k, y1 + o)], fill=color, width=w)
    d.line([(x1 + o, y1 + o), (x1 + o, y1 + o - k)], fill=color, width=w)


def layout_box(b, bw, bh):
    """Find sizes at which code/title/note fit inside the box. Code and title shrink
    on their own to fit the width; the overall scale only drops for height/lines."""
    padx, pady = 22, 18
    iw, ih = bw - 2 * padx, bh - 2 * pady
    title, code, note = b.get("title", ""), b.get("code", ""), b.get("note", "")
    scale = 1.0
    while True:
        tr = 2
        cs = int(20 * scale)
        while cs > 12 and mono_width(code, cs, tr) > iw:
            cs -= 1
        ts = int(38 * scale)
        while ts > 18 and text_w(title, cjk("Bold", ts)) > iw:
            ts -= 1
        ns = int(23 * scale)
        tf, nf = cjk("Bold", ts), cjk("Regular", ns)
        note_lines = wrap(note, nf, iw) if note else []
        g = max(10, int(16 * ts / 38))
        nlh = int(ns * 1.42)
        n_h = ink_box(nf, "工")[1]
        t_h = ink_box(tf, "工")[1]
        total = cs + g + t_h + (g - 2 + (len(note_lines) - 1) * nlh + n_h if note_lines else 0)
        fits = (mono_width(code, cs, tr) <= iw and text_w(title, tf) <= iw
                and len(note_lines) <= 3 and total <= ih
                and all(text_w(l, nf) <= iw for l in note_lines))
        if fits or scale <= 0.5:
            if not fits:
                WARN.append("box overflow: " + title)
            return dict(cs=cs, tf=tf, nf=nf, total=total)
        scale -= 0.03


def draw_boxes(d, img, boxes, y0, y1, cols=None):
    plan = row_plan(len(boxes), cols)
    gx, gy = 30, 26
    rows = len(plan)
    bh = int((y1 - y0 - gy * (rows - 1)) / rows)
    bh = min(bh, 250)  # do not stretch boxes into tall empty slabs
    y0 += ((y1 - y0) - (bh * rows + gy * (rows - 1))) // 2  # center the grid
    # compute a common scale per card: lay out all boxes, use the smallest scale result
    idx = 0
    placed = []
    for r, n in enumerate(plan):
        bw = int((R - L - gx * (n - 1)) / n)
        for c in range(n):
            x = L + c * (bw + gx)
            y = y0 + r * (bh + gy)
            placed.append((boxes[idx], x, y, bw, bh))
            idx += 1
    lays = [layout_box(b, bw, bh) for b, x, y, bw, bh in placed]
    # unify sizes: use the smallest title/note sizes across boxes for visual consistency
    min_ts = min(l["tf"].size for l in lays)
    min_ns = min(l["nf"].size for l in lays)
    min_cs = min(l["cs"] for l in lays)
    # keep hierarchy: title must stay clearly larger than note / code
    min_ns = min(min_ns, max(14, int(min_ts * 0.66)))
    min_cs = min(min_cs, max(12, int(min_ts * 0.58)))
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    for (b, x, y, bw, bh) in placed:
        od.rectangle([x, y, x + bw, y + bh], fill=BOX_FILL)
    img.alpha_composite(ov)
    d = ImageDraw.Draw(img)
    for (b, x, y, bw, bh) in placed:
        hl = b.get("highlight")
        d.rectangle([x, y, x + bw, y + bh], outline=YEL if hl else LINE, width=3 if hl else 2)
        draw_brackets(d, x, y, x + bw, y + bh, YEL if hl else BRACKET)
        padx, pady = 22, 18
        iw = bw - 2 * padx
        tf = cjk("Bold", min_ts)
        nf = cjk("Regular", min_ns)
        lines = wrap(b.get("note", ""), nf, iw) if b.get("note") else []
        g = max(10, int(16 * min_ts / 38))
        nlh = int(min_ns * 1.42)
        t_top, t_h = ink_box(tf, "工")
        n_top, n_h = ink_box(nf, "工")
        total = min_cs + g + t_h + (g - 2 + (len(lines) - 1) * nlh + n_h if lines else 0)
        cy = y + pady + max(0, (bh - 2 * pady - total) // 2)
        draw_mono(d, (x + padx, cy - 2), b.get("code", ""), min_cs, YEL, 2)
        cy += min_cs + g
        d.text((x + padx, cy - t_top), b.get("title", ""), font=tf, fill=WHITE)
        cy += t_h + g - 2
        for i, ln in enumerate(lines):
            d.text((x + padx, cy - n_top + i * nlh), ln, font=nf, fill=NOTE)
    return d


def draw_title_block(d, spec):
    x1 = R
    x0 = x1 - TB_W
    y0, y1 = TB_TOP, TB_BOTTOM
    lab_w = 104
    d.rectangle([x0, y0, x1, y0 + TB_ROW], fill=(12, 34, 70))
    d.rectangle([x0, y0, x1, y1], outline=LINE, width=2)
    for i in (1, 2):
        d.line([(x0, y0 + i * TB_ROW), (x1, y0 + i * TB_ROW)], fill=LINE, width=1)
    d.line([(x0 + lab_w, y0), (x0 + lab_w, y1)], fill=LINE, width=1)
    rows = [("PROJECT", spec.get("project", "建築室內營造工程管理教學"), "cjk", WHITE),
            ("SCALE", spec.get("scale", "1:1"), "mono", WHITE),
            ("URL", spec.get("url", "aci-easylearn.com"), "mono", YEL)]
    vw = TB_W - lab_w - 28
    for i, (lab, val, kind, col) in enumerate(rows):
        ry = y0 + i * TB_ROW
        ls = 16
        draw_mono(d, (x0 + 14, ry + (TB_ROW - ls) // 2 - 2), lab, ls, GREY, 2)
        if kind == "cjk":
            f = fit_single(val, "Bold", 22, 14, vw)
            top, h = ink_box(f, "工")
            d.text((x0 + lab_w + 14, ry + (TB_ROW - h) // 2 - top), val, font=f, fill=col)
        else:
            s, tr = 22 if lab == "URL" else 20, 1
            while mono_width(val, s, tr) > vw and s > 12:
                s -= 1
            # center mono glyph ink vertically
            top, h = ink_box(mono(s), "Ag")
            draw_mono(d, (x0 + lab_w + 14, ry + (TB_ROW - h) // 2 - top), val, s, col, tr)


def draw_big(d, big, x0, x1, y0, y1):
    """Big yellow value bottom-left; label + caption (caption may wrap to 2 lines)
    stacked to its right. The value shrinks first so the side text stays legible."""
    aw, ah = x1 - x0, y1 - y0
    value, label, caption = big.get("value", ""), big.get("label", ""), big.get("caption", "")
    gap = 22
    vs = 132
    chosen = None
    while vs >= 56:
        vf = cjk("Black", vs)
        vtop, vh = ink_box(vf, value)
        vw = text_w(value, vf)
        avail = aw - vw - gap
        if avail >= 120 and vh <= ah:
            ls = max(24, min(36, int(vs * 0.28)))
            lf = fit_single(label, "Bold", ls, 22, avail, warn=False) if label else None
            cap_lines, cf = [], None
            if caption:
                for cs in range(max(17, min(22, int(vs * 0.17))), 15, -1):
                    f = cjk("Regular", cs)
                    lines = wrap(caption, f, avail)
                    if len(lines) <= 2:
                        cf, cap_lines = f, lines
                        break
            if (lf or not label) and (cf or not caption):
                chosen = (vf, vtop, vh, vw, lf, cf, cap_lines)
                break
        vs -= 2
    if chosen is None:
        WARN.append("big block overflow: shorten big.label / big.caption")
        vf = cjk("Black", 56)
        vtop, vh = ink_box(vf, value)
        vw = text_w(value, vf)
        lf = cjk("Bold", 22) if label else None
        cf = cjk("Regular", 16) if caption else None
        cap_lines = wrap(caption, cf, aw - vw - gap)[:2] if caption else []
        chosen = (vf, vtop, vh, vw, lf, cf, cap_lines)
    vf, vtop, vh, vw, lf, cf, cap_lines = chosen
    d.text((x0 - vf.getbbox(value)[0], y1 - vh - vtop), value, font=vf, fill=YEL)
    rx = x0 + vw + gap
    parts = []
    if lf:
        parts.append((label, lf, WHITE, 14))
    for i, ln in enumerate(cap_lines):
        parts.append((ln, cf, NOTE, 8))
    heights = [ink_box(f, "工")[1] for _, f, _, _ in parts]
    total = sum(heights) + sum(g for _, _, _, g in parts[:-1])
    cy = y1 - total
    for (t, f, c, g), h in zip(parts, heights):
        d.text((rx, cy - ink_box(f, "工")[0]), t, font=f, fill=c)
        cy += h + g


def draw_takeaway(d, text, x0, x1, y0, y1):
    aw, ah = x1 - x0, y1 - y0
    draw_mono(d, (x0, y0), "NOTE ▸", 17, YEL, 3)
    ty = y0 + 34
    s = 34
    while True:
        f = cjk("Bold", s)
        lines = wrap(text, f, aw)
        lh = int(s * 1.38)
        top, h = ink_box(f, "工")
        total = (len(lines) - 1) * lh + h
        if (len(lines) <= 3 and total <= y1 - ty) or s <= 18:
            if not (len(lines) <= 3 and total <= y1 - ty):
                WARN.append("takeaway overflow")
            break
        s -= 1
    for i, ln in enumerate(lines):
        d.text((x0, ty - top + i * lh), ln, font=f, fill=WHITE)


def render(spec, out):
    img = Image.new("RGBA", (W, H), BG + (255,))
    draw_background(img)
    d = ImageDraw.Draw(img)
    y = draw_header(d, spec, 100)
    y = draw_headline(d, spec["headline"], y + 26)
    y = draw_dimension(d, spec["subtitle"], y + 34)
    if spec.get("lead"):
        y = draw_lead(d, spec["lead"], y + 26)
    boxes_top = y + 40
    boxes_bottom = TB_TOP - 40
    d = draw_boxes(d, img, spec["boxes"], boxes_top, boxes_bottom, spec.get("cols"))
    draw_title_block(d, spec)
    bx0, bx1 = L, R - TB_W - 34
    if spec.get("big"):
        draw_big(d, spec["big"], bx0, bx1, TB_TOP - 4, TB_BOTTOM)
    elif spec.get("takeaway"):
        draw_takeaway(d, spec["takeaway"], bx0, bx1, TB_TOP, TB_BOTTOM)
    rgb = img.convert("RGB")
    q = rgb.quantize(colors=128, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    q.save(out, optimize=True)
    for w in WARN:
        print("WARNING:", w, file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    with open(sys.argv[1], encoding="utf-8") as fh:
        render(json.load(fh), sys.argv[2])
    print("saved", sys.argv[2])
