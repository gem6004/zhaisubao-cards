#!/usr/bin/env python3
"""宅速報 每日字卡產生器（1080x1080）

用法：python3 zhaisubao_card.py spec.json out.png
spec.json 範例：
{
  "date": "2026.10.17",
  "kicker": "房市重點",
  "lines": ["AI 把錢吸走了", "廠房商辦熱", "住宅用地冷!?"],
  "character": "busy"
}
character 可用：busy 忙碌 / nope 沒法度 / why 為什麼 / headache 傷腦筋 /
               thanks 辛苦了 / congrats 恭喜 / great 超爽的 / ok 了解 / finally 久等了
角色圖放在 chars/ 資料夾（IMG_80xx.PNG，LINE 貼圖原檔，透明底）。
"""
import json, sys, os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
CHARS = {
    "busy": "IMG_8072.PNG", "nope": "IMG_8083.PNG", "why": "IMG_8082.PNG",
    "headache": "IMG_8069.PNG", "thanks": "IMG_8066.PNG", "congrats": "IMG_8084.PNG",
    "great": "IMG_8065.PNG", "ok": "IMG_8062.PNG", "finally": "IMG_8063.PNG",
}
W = H = 1080
BG = (17, 17, 17)
YEL = (245, 197, 24)
WHITE = (245, 245, 240)
GREY = (150, 150, 150)
FONT_BLACK = "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc"
FONT_BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
FONT_REG = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
TC = 3  # index of Traditional Chinese face in Noto CJK .ttc files


def font(path, size):
    for idx in (TC, 0):
        try:
            return ImageFont.truetype(path, size, index=idx)
        except Exception:
            continue
    return ImageFont.load_default()


def hazard(draw, y0, y1, step=46):
    draw.rectangle([0, y0, W, y1], fill=YEL)
    h = y1 - y0
    x = -h
    while x < W + h:
        draw.polygon([(x, y1), (x + step / 2, y1), (x + step / 2 + h, y0), (x + h, y0)], fill=(20, 20, 20))
        x += step


def fit(draw, text, path, max_w, start, min_size=60):
    size = start
    while size > min_size:
        f = font(path, size)
        if draw.textlength(text, font=f) <= max_w:
            return f
        size -= 4
    return font(path, min_size)


def make(spec, out):
    im = Image.new("RGBA", (W, H), BG + (255,))
    d = ImageDraw.Draw(im)

    # hazard tape top & bottom
    hazard(d, 0, 34)
    hazard(d, H - 34, H)

    # tag 軍の短評
    tag_font = font(FONT_BLACK, 40)
    tw = d.textlength("軍の短評", font=tag_font)
    d.rounded_rectangle([60, 78, 60 + tw + 48, 146], radius=12, fill=YEL)
    d.text((84, 84), "軍の短評", font=tag_font, fill=(20, 20, 20))

    # date top-right
    df = font(FONT_BOLD, 34)
    date = spec.get("date", "")
    d.text((W - 60 - d.textlength(date, font=df), 92), date, font=df, fill=GREY)

    # kicker
    kf = font(FONT_BOLD, 40)
    kicker = spec.get("kicker", "房市重點")
    d.text((62, 200), "▍" + kicker, font=kf, fill=YEL)

    # title lines
    lines = spec["lines"][:3]
    y = 265
    for i, line in enumerate(lines):
        last = i == len(lines) - 1
        f = fit(d, line, FONT_BLACK, W - 130, 104)
        d.text((60, y), line, font=f, fill=YEL if last else WHITE)
        y += int(f.size * 1.32)

    # character badge bottom-right
    key = spec.get("character", "busy")
    cp = os.path.join(HERE, "chars", CHARS.get(key, CHARS["busy"]))
    ch = Image.open(cp).convert("RGBA")
    scale = 320 / ch.width
    ch = ch.resize((int(ch.width * scale), int(ch.height * scale)), Image.LANCZOS)
    cx, cy = W - ch.width - 60, H - ch.height - 95
    badge = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(badge)
    r = 172
    ccx, ccy = cx + ch.width // 2, cy + ch.height // 2 + 10
    bd.ellipse([ccx - r, ccy - r, ccx + r, ccy + r], fill=(238, 236, 228, 255))
    im.alpha_composite(badge)
    im.alpha_composite(ch, (cx, cy))

    # footer
    ff = font(FONT_BOLD, 34)
    d.text((60, H - 110), "@力信建築 江軍", font=ff, fill=WHITE)
    sf = font(FONT_REG, 26)
    d.text((60, H - 68), "宅速報｜每日不動產短評", font=sf, fill=GREY)

    # 量化成 64 色 PNG：檔案約 40KB，方便上傳 Google Drive
    im.convert("RGB").quantize(colors=64, method=Image.Quantize.MEDIANCUT).save(out, "PNG", optimize=True)


if __name__ == "__main__":
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    make(spec, sys.argv[2])
    print("saved", sys.argv[2])
