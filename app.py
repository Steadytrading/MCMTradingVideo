from flask import Flask, request, send_file, render_template
import math, random, tempfile, os, re
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import imageio

app = Flask(__name__)

# Branding
TIKTOK_HANDLE = "@mcm_trading"
LANDING_URL = "mcmtrading.netlify.app"

# ✅ Render Free-safe settings
WIDTH, HEIGHT = 720, 1280          # MUCH lower RAM than 1080x1920
FPS = 20                           # lower CPU/RAM pressure
SECONDS = 5

TITLE = "XAUUSD LIVE TRADE"
SUBTITLE = "Today's Result"
FOLLOW = "Follow for daily XAUUSD profits"

def load_font(name, size):
    try:
        return ImageFont.truetype(name, size)
    except:
        return ImageFont.load_default()

# Scale fonts for 720x1280
F_TITLE  = load_font("DejaVuSans-Bold.ttf", 62)
F_PROFIT = load_font("DejaVuSans-Bold.ttf", 105)
F_SUB    = load_font("DejaVuSans-Bold.ttf", 46)
F_UI     = load_font("DejaVuSans-Bold.ttf", 38)
F_SMALL  = load_font("DejaVuSans.ttf", 28)

def clean_profit(p):
    p = (p or "").strip().replace(",", ".")
    if p.startswith("+"):
        p = p[1:]
    p = re.sub(r"[^0-9.]", "", p)
    if not p:
        p = "0.00"
    try:
        p = f"{float(p):.2f}"
    except:
        pass
    return p

def generate_video(profit_value, session):
    p = clean_profit(profit_value)
    profit_text = f"+{p}%"
    session_label = "London session" if session == "london" else "NY session"

    # Fake candles
    num_candles = 18
    base = HEIGHT * 0.72
    candles = []
    price = base
    for _ in range(num_candles):
        change = random.randint(-120, 120)
        o = price
        c = price + change
        hi = max(o, c) + random.randint(20, 70)
        lo = min(o, c) - random.randint(20, 70)
        candles.append((o, c, hi, lo))
        price = c

    fd, out_path = tempfile.mkstemp(suffix=".mp4")
    os.close(fd)

    total_frames = FPS * SECONDS

    # ✅ Encode settings: faster + lighter
    writer = imageio.get_writer(
        out_path,
        fps=FPS,
        codec="libx264",
        bitrate="1800k",
        ffmpeg_params=["-preset", "ultrafast", "-pix_fmt", "yuv420p"],
        macro_block_size=1,   # avoid resizing
    )

    try:
        for i in range(total_frames):
            img = Image.new("RGB", (WIDTH, HEIGHT), (8, 10, 18))
            d = ImageDraw.Draw(img)

            glow = 205 + int(55 * math.sin(i / 7.5))
            gold = (glow, max(glow - 70, 0), 12)

            # candles move
            cw = WIDTH // (num_candles + 4)
            offset = cw * 2
            shift = i * 2

            for idx, (o, c, hi, lo) in enumerate(candles):
                x = offset + idx * cw
                o2 = o - shift
                c2 = c - shift
                hi2 = hi - shift
                lo2 = lo - shift

                color = (0, 230, 140) if c2 < o2 else (230, 70, 70)

                d.line((x + cw // 2, hi2, x + cw // 2, lo2), fill=(220, 220, 220), width=2)
                top = min(o2, c2)
                bottom = max(o2, c2)
                d.rectangle((x, top, x + cw - 3, bottom), fill=color)

            # Title
            tb = d.textbbox((0, 0), TITLE, font=F_TITLE)
            d.text(((WIDTH - (tb[2]-tb[0]))/2, 70), TITLE, font=F_TITLE, fill=(235, 235, 235))

            # Session pill
            pill_text = session_label.upper()
            pb = d.textbbox((0, 0), pill_text, font=F_SMALL)
            pill_w = (pb[2]-pb[0]) + 22
            pill_h = (pb[3]-pb[1]) + 12
            pill_x = WIDTH - pill_w - 24
            pill_y = 150
            d.rounded_rectangle((pill_x, pill_y, pill_x + pill_w, pill_y + pill_h),
                                radius=14, fill=(15, 22, 40), outline=(40, 60, 110), width=2)
            d.text((pill_x + pill_w/2, pill_y + pill_h/2), pill_text,
                   font=F_SMALL, fill=(210, 220, 245), anchor="mm")

            # ENTRY → TP HIT pop (1.0s–2.6s)
            entry_text = "ENTRY  →  TP HIT"
            start = int(1.0 * FPS)
            end = int(2.6 * FPS)
            if start <= i <= end:
                t = (i - start) / max((end - start), 1)
                scale = 1 + 0.22 * math.exp(-4.0*t) * math.sin(18.0*t)
                size = max(28, int(44 * scale))
                try:
                    f_entry = ImageFont.truetype("DejaVuSans-Bold.ttf", size)
                except:
                    f_entry = F_UI
                eb = d.textbbox((0, 0), entry_text, font=f_entry)
                ex = (WIDTH - (eb[2]-eb[0]))/2
                ey = 190
                d.text((ex+2, ey+2), entry_text, font=f_entry, fill=(0, 0, 0))
                d.text((ex, ey), entry_text, font=f_entry, fill=(235, 235, 235))

            # Subtitle
            sb = d.textbbox((0, 0), SUBTITLE, font=F_SUB)
            d.text(((WIDTH - (sb[2]-sb[0]))/2, 260), SUBTITLE, font=F_SUB, fill=(200, 200, 200))

            # Profit
            scale = 1 + 0.03 * math.sin(i / 4)
            try:
                profit_font = ImageFont.truetype("DejaVuSans-Bold.ttf", int(105 * scale))
            except:
                profit_font = F_PROFIT
            prb = d.textbbox((0, 0), profit_text, font=profit_font)
            d.text(((WIDTH - (prb[2]-prb[0]))/2, 340), profit_text, font=profit_font, fill=gold)

            # CTA + watermark
            fb = d.textbbox((0, 0), FOLLOW, font=F_UI)
            d.text(((WIDTH - (fb[2]-fb[0]))/2, HEIGHT - 160), FOLLOW, font=F_UI, fill=(240, 240, 240))

            wm = f"{TIKTOK_HANDLE}  •  {LANDING_URL}"
            wmb = d.textbbox((0, 0), wm, font=F_SMALL)
            d.text(((WIDTH - (wmb[2]-wmb[0]))/2, HEIGHT - 110), wm, font=F_SMALL, fill=(175, 185, 210))

            writer.append_data(np.asarray(img, dtype=np.uint8))
    finally:
        writer.close()

    return out_path

@app.get("/")
def home():
    return render_template("index.html", handle=TIKTOK_HANDLE, landing=LANDING_URL)

@app.post("/generate")
def generate():
    profit = request.form.get("profit", "")
    session = request.form.get("session", "london")
    if session not in ("london", "ny"):
        session = "london"
    if not profit.strip():
        return render_template("index.html", error="Skriv in en profit, t.ex. 4.12",
                               handle=TIKTOK_HANDLE, landing=LANDING_URL)

    video = generate_video(profit, session)
    filename = f"xauusd_{session}_{clean_profit(profit)}.mp4"
    return send_file(video, as_attachment=True, download_name=filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
