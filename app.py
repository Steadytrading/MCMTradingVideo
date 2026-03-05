from flask import Flask, request, send_file, render_template
import math, random, tempfile, os, re

from PIL import Image, ImageDraw, ImageFont
import imageio

app = Flask(__name__)

# TikTok branding (edit here)
TIKTOK_HANDLE = "@mcm_trading"
LANDING_URL = "mcmtrading.netlify.app"

WIDTH, HEIGHT = 1080, 1920
FPS = 30
SECONDS = 5

TITLE = "XAUUSD LIVE TRADE"
SUBTITLE = "Today's Result"
FOLLOW = "Follow for daily XAUUSD profits"

def _load_font(name: str, size: int):
    try:
        return ImageFont.truetype(name, size)
    except Exception:
        return ImageFont.load_default()

F_TITLE  = _load_font("DejaVuSans-Bold.ttf", 90)
F_PROFIT = _load_font("DejaVuSans-Bold.ttf", 150)
F_SUB    = _load_font("DejaVuSans-Bold.ttf", 66)
F_UI     = _load_font("DejaVuSans-Bold.ttf", 54)
F_SMALL  = _load_font("DejaVuSans.ttf", 40)

def _clean_profit(profit_value: str) -> str:
    p = (profit_value or "").strip().replace(",", ".")
    if p.startswith("+"):
        p = p[1:]
    p = re.sub(r"[^0-9.]", "", p)
    if not p:
        p = "0.00"
    # Trim to 2 decimals when possible
    try:
        val = float(p)
        p = f"{val:.2f}"
    except Exception:
        pass
    return p

def generate_video(profit_value: str, session: str) -> str:
    p = _clean_profit(profit_value)
    profit_text = f"+{p}%"
    session_label = "London session" if session == "london" else "NY session"

    # Fake candle data
    num_candles = 22
    base = HEIGHT * 0.70
    candles = []
    price = base
    for _ in range(num_candles):
        change = random.randint(-150, 150)
        o = price
        c = price + change
        hi = max(o, c) + random.randint(30, 100)
        lo = min(o, c) - random.randint(30, 100)
        candles.append((o, c, hi, lo))
        price = c

    frames = []
    total_frames = FPS * SECONDS

    for i in range(total_frames):
        img = Image.new("RGB", (WIDTH, HEIGHT), (8, 10, 18))
        d = ImageDraw.Draw(img)

        # animated glow
        glow = 205 + int(60 * math.sin(i / 7.5))
        gold = (glow, max(glow - 70, 0), 12)

        # background candles animation
        cw = WIDTH // (num_candles + 4)
        offset = cw * 2
        shift = i * 3

        for idx, (o, c, hi, lo) in enumerate(candles):
            x = offset + idx * cw
            o2 = o - shift
            c2 = c - shift
            hi2 = hi - shift
            lo2 = lo - shift

            color = (0, 230, 140) if c2 < o2 else (230, 70, 70)
            d.line((x + cw // 2, hi2, x + cw // 2, lo2), fill=(220, 220, 220), width=3)

            top = min(o2, c2)
            bottom = max(o2, c2)
            d.rectangle((x, top, x + cw - 4, bottom), fill=color)

        # header: title + session tag
        tb = d.textbbox((0, 0), TITLE, font=F_TITLE)
        d.text(((WIDTH - (tb[2]-tb[0]))/2, 110), TITLE, font=F_TITLE, fill=(235, 235, 235))

        # session pill
        pill_text = session_label.upper()
        pb = d.textbbox((0, 0), pill_text, font=F_SMALL)
        pill_w = (pb[2]-pb[0]) + 32
        pill_h = (pb[3]-pb[1]) + 18
        pill_x = WIDTH - pill_w - 40
        pill_y = 230
        d.rounded_rectangle((pill_x, pill_y, pill_x + pill_w, pill_y + pill_h), radius=18,
                            fill=(15, 22, 40), outline=(40, 60, 110), width=2)
        d.text((pill_x + pill_w/2, pill_y + pill_h/2), pill_text, font=F_SMALL, fill=(210, 220, 245), anchor="mm")

        # ENTRY → TP HIT pop animation around 1.0s–2.5s
        entry_text = "ENTRY  →  TP HIT"
        start = int(1.0 * FPS)
        end = int(2.6 * FPS)
        if start <= i <= end:
            t = (i - start) / max((end - start), 1)
            # bounce scale: quick pop, then settle
            scale = 1.0 + 0.22 * math.exp(-4.0 * t) * math.sin(18.0 * t)
            size = max(44, int(62 * scale))
            try:
                f_entry = ImageFont.truetype("DejaVuSans-Bold.ttf", size)
            except Exception:
                f_entry = F_UI

            eb = d.textbbox((0, 0), entry_text, font=f_entry)
            ex = (WIDTH - (eb[2]-eb[0]))/2
            ey = 330
            # shadow
            d.text((ex+3, ey+3), entry_text, font=f_entry, fill=(0,0,0))
            d.text((ex, ey), entry_text, font=f_entry, fill=(235, 235, 235))

        # subtitle
        sb = d.textbbox((0, 0), SUBTITLE, font=F_SUB)
        d.text(((WIDTH - (sb[2]-sb[0]))/2, 430), SUBTITLE, font=F_SUB, fill=(200, 200, 200))

        # profit pulse
        scale = 1 + 0.03 * math.sin(i / 4)
        try:
            profit_font = ImageFont.truetype("DejaVuSans-Bold.ttf", int(150 * scale))
        except Exception:
            profit_font = F_PROFIT

        prb = d.textbbox((0, 0), profit_text, font=profit_font)
        d.text(((WIDTH - (prb[2]-prb[0]))/2, 560), profit_text, font=profit_font, fill=gold)

        # CTA bottom
        fb = d.textbbox((0, 0), FOLLOW, font=F_UI)
        d.text(((WIDTH - (fb[2]-fb[0]))/2, HEIGHT - 320), FOLLOW, font=F_UI, fill=(240, 240, 240))

        # watermark + landing (always visible)
        wm = f"{TIKTOK_HANDLE}  •  {LANDING_URL}"
        wmb = d.textbbox((0,0), wm, font=F_SMALL)
        d.text(((WIDTH - (wmb[2]-wmb[0]))/2, HEIGHT - 230), wm, font=F_SMALL, fill=(175, 185, 210))

        frames.append(img)

    fd, out_path = tempfile.mkstemp(suffix=".mp4")
    os.close(fd)
    imageio.mimsave(out_path, frames, fps=FPS)
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
    if not (profit or "").strip():
        return render_template("index.html", error="Skriv in en profit, t.ex. 4.12", handle=TIKTOK_HANDLE, landing=LANDING_URL)

    out_path = generate_video(profit, session)
    filename = f"xauusd_{session}_{_clean_profit(profit)}.mp4"
    return send_file(out_path, as_attachment=True, download_name=filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
