"""
etsy_spy.py — POD Bestseller Spy
► Dùng Etsy Open API v3 (browser-free, không bao giờ bị block)
► Fallback: Redbubble qua HTTP request đơn giản
► Không dùng Playwright = không bao giờ bị fingerprint
"""
import os
import re
import gzip
import json
import time
import urllib.request
import urllib.parse
import webbrowser
from datetime import datetime

# ========== CONFIG ==========
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, 'config.json')
OUTPUT_JSON = os.path.join(SCRIPT_DIR, 'etsy_data.json')
OUTPUT_HTML = os.path.join(SCRIPT_DIR, 'etsy_spy.html')

ETSY_API_BASE = "https://openapi.etsy.com/v3/application"

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Referer": "https://www.google.com/",
    "Connection": "keep-alive",
}

# Keywords cho Etsy API
ETSY_KEYWORDS = [
    ("sports fan shirt",           "General Sports"),
    ("game day shirt",             "Game Day"),
    ("basketball fan shirt",       "Basketball"),
    ("football fan shirt",         "Football"),
    ("baseball fan tshirt",        "Baseball"),
    ("hockey fan shirt",           "Hockey"),
    ("march madness shirt",        "NCAA Men"),
    ("women basketball shirt",     "NCAA Women"),
    ("final four shirt",           "NCAA Tournament"),
    ("championship tshirt vintage","Championship"),
    ("nba fan graphic tee",        "NBA Fan"),
    ("nfl fan vintage tshirt",     "NFL Fan"),
]

# Keywords fallback cho Redbubble
REDBUBBLE_KEYWORDS = [
    ("sports fan shirt",          "General Sports",  "u-tees"),
    ("game day shirt",            "Game Day",        "u-tees"),
    ("basketball fan",            "Basketball",      "u-tees"),
    ("football fan shirt",        "Football",        "u-tees"),
    ("march madness shirt",       "NCAA Men",        "u-tees"),
    ("ncaa women basketball",     "NCAA Women",      "u-tees"),
    ("championship tshirt",       "Championship",    "u-tees"),
    ("nba fan tshirt",            "NBA Fan",         "u-tees"),
]

EXCLUDED = [
    "jersey", "official", "licensed", "authentic", "replica",
    "nike ", "adidas", "under armour", "fitted", "swingman",
]


# =============================================================
#  LOAD CONFIG
# =============================================================
def load_config():
    """Đọc config.json, trả về dict."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


# =============================================================
#  ETSY OPEN API v3 (không cần browser)
# =============================================================
def etsy_api_request(endpoint, params, api_key):
    """Gọi Etsy API v3 với API key."""
    qs = urllib.parse.urlencode(params, doseq=True)
    url = f"{ETSY_API_BASE}/{endpoint}?{qs}"
    req = urllib.request.Request(url, headers={
        "x-api-key": api_key,
        "User-Agent": "PODResearchTool/2.0",
        "Accept": "application/json",
    })
    try:
        resp = urllib.request.urlopen(req, timeout=20)
        return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        if e.code == 401:
            print("  ❌ API key không hợp lệ. Kiểm tra lại config.json")
        elif e.code == 429:
            print("  ⚠ Rate limit — đợi 5s...")
            time.sleep(5)
        else:
            print(f"  ⚠ HTTP {e.code}: {body[:120]}")
        return None
    except Exception as e:
        print(f"  ⚠ Lỗi: {e}")
        return None


def fetch_etsy_listings(keyword, category, api_key):
    """Lấy listings từ Etsy API, trả về (items, competition_count)."""
    data = etsy_api_request(
        "listings/active",
        {
            "keywords": keyword,
            "limit": 24,
            "sort_on": "score",
            "listing_type": "physical",
            "includes[]": ["Images"],
        },
        api_key,
    )
    if not data:
        return [], -1

    count  = data.get("count", -1)
    items  = []
    for lst in data.get("results", []):
        title = lst.get("title", "")
        # Lọc bỏ hàng licensed
        if any(ex in title.lower() for ex in EXCLUDED):
            continue

        price_obj = lst.get("price", {})
        try:
            price = f"${price_obj['amount'] / price_obj['divisor']:.2f}"
        except Exception:
            price = ""

        views = lst.get("views", 0)
        favs  = lst.get("num_favorers", 0)
        url   = lst.get("url", "")

        # Lấy ảnh đầu tiên
        image = ""
        try:
            imgs  = lst.get("images", [])
            if imgs:
                image = (imgs[0].get("url_570xN")
                         or imgs[0].get("url_170x135")
                         or "")
        except Exception:
            pass

        items.append({
            "title":  title,
            "price":  price,
            "image":  image,
            "link":   url,
            "rating": f"❤ {favs:,}  👁 {views:,}",
            "sold":   "",
        })

    return items, count


# =============================================================
#  REDBUBBLE qua HTTP (fallback, không cần browser)
# =============================================================
def _http_get(url):
    """Simple HTTP GET, handle gzip."""
    req = urllib.request.Request(url, headers=BROWSER_HEADERS)
    try:
        resp = urllib.request.urlopen(req, timeout=20)
        raw  = resp.read()
        if resp.info().get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
        return raw.decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"  ⚠ HTTP error: {e}")
        return ""


def fetch_redbubble_listings(keyword, category, code):
    """Lấy listings từ Redbubble qua HTTP thông thường."""
    slug = keyword.replace(" ", "+")
    url  = f"https://www.redbubble.com/shop/{slug}?sortOrder=top+selling&iaCode={code}"
    print(f"  🔄 [RB/{category}] '{keyword}'...")

    html = _http_get(url)
    if not html:
        return [], -1

    # Thử parse JSON-LD hoặc embedded JSON data
    items = []
    count = -1

    # Tìm số kết quả
    m = re.search(r'"numFound"\s*:\s*(\d+)', html)
    if m:
        count = int(m.group(1))
    else:
        m2 = re.search(r'([\d,]+)\s*result', html, re.IGNORECASE)
        if m2:
            count = int(m2.group(1).replace(",", ""))

    # Tìm JSON-LD product data
    ld_blocks = re.findall(
        r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>',
        html, re.DOTALL
    )
    for block in ld_blocks:
        try:
            obj = json.loads(block.strip())
            # ItemList hoặc Product
            if obj.get("@type") == "ItemList":
                for el in obj.get("itemListElement", []):
                    item_obj = el.get("item", el)
                    title = item_obj.get("name", "")
                    url_  = item_obj.get("url", "")
                    img   = ""
                    try:
                        img = item_obj["image"][0] if isinstance(item_obj["image"], list) else item_obj["image"]
                    except Exception:
                        pass
                    price = ""
                    try:
                        offers = item_obj.get("offers", {})
                        if isinstance(offers, list):
                            offers = offers[0]
                        price = f"${float(offers.get('price', 0)):.2f}"
                    except Exception:
                        pass
                    if title:
                        items.append({"title": title, "price": price, "image": img, "link": url_, "rating": "", "sold": ""})
        except Exception:
            pass

    # Fallback: regex scrape product titles từ metadata
    if not items:
        titles = re.findall(r'"name"\s*:\s*"([^"]{5,80})"', html)
        urls   = re.findall(r'"url"\s*:\s*"(https://www\.redbubble\.com/[^"]+)"', html)
        imgs   = re.findall(r'"thumbnailUrl"\s*:\s*"([^"]+)"', html)
        prices = re.findall(r'"price"\s*:\s*"?(\d+\.?\d*)"?', html)
        for i, t in enumerate(titles[:20]):
            if any(ex in t.lower() for ex in EXCLUDED):
                continue
            items.append({
                "title":  t,
                "price":  f"${prices[i]}" if i < len(prices) else "",
                "image":  imgs[i]  if i < len(imgs)   else "",
                "link":   urls[i]  if i < len(urls)   else "",
                "rating": "",
                "sold":   "",
            })

    print(f"  📦 {len(items)} items | {count:,} results" if count > 0 else f"  📦 {len(items)} items")
    return items[:24], count


# =============================================================
#  COMPETITION LABEL + HTML
# =============================================================
def competition_label(count, source="etsy"):
    """Ngưỡng khác nhau cho Etsy vs Redbubble."""
    if count < 0:
        return "❓", "#8b949e", "Unknown"
    if source == "etsy":
        if count < 200:   return "🟢", "#3fb950", f"LOW ({count:,})"
        if count < 1000:  return "🟡", "#d29922", f"MEDIUM ({count:,})"
        if count < 5000:  return "🟠", "#ffa657", f"HIGH ({count:,})"
        return "🔴", "#ff7b72", f"VERY HIGH ({count:,}+)"
    else:  # redbubble
        if count < 500:   return "🟢", "#3fb950", f"LOW ({count:,})"
        if count < 2000:  return "🟡", "#d29922", f"MEDIUM ({count:,})"
        if count < 8000:  return "🟠", "#ffa657", f"HIGH ({count:,})"
        return "🔴", "#ff7b72", f"VERY HIGH ({count:,}+)"


def save_json(all_data, source):
    export = [
        {"keyword": kw, "category": cat, "source": source, "competition_count": cnt, "items": items}
        for kw, cat, items, cnt in all_data
    ]
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(export, f, ensure_ascii=False, indent=2)
    total = sum(len(d["items"]) for d in export)
    print(f"  💾 Lưu: etsy_data.json ({total} items from {source})")


def generate_html(all_data, now, source_name, has_api_key):
    sections = ""
    src_lower = source_name.lower()

    for keyword, category, items, count in all_data:
        if not items:
            continue
        icon, color, label = competition_label(count, "etsy" if "etsy" in src_lower else "rb")
        cards_html = ""
        for item in items[:24]:
            t = (item.get("title") or "")[:80].replace('"', "&quot;").replace("<", "").replace(">", "")
            img   = item.get("image") or ""
            link  = item.get("link") or "#"
            price = (item.get("price") or "")[:12].replace("<", "").replace(">", "")
            extra = (item.get("rating") or item.get("sold") or "")[:30].replace("<", "").replace(">", "")

            cards_html += f"""
            <div class="card">
                <a href="{link}" target="_blank" class="card-img-wrap">
                    {'<img src="' + img + '" alt="" loading="lazy" onerror="this.parentElement.style.background=\'#1c2333\'">' if img else '<div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);color:#484f58;font-size:1.5rem;">🖼</div>'}
                </a>
                <div class="card-body">
                    <p class="card-title">{t}</p>
                    <div class="card-meta">
                        <span class="card-price">{price}</span>
                        <span class="card-extra">{extra}</span>
                    </div>
                </div>
            </div>"""

        sections += f"""
        <section class="kw-section">
            <div class="kw-header">
                <div class="kw-left">
                    <span class="cat-badge">{category}</span>
                    <span class="kw-name">"{keyword}"</span>
                </div>
                <span class="comp-badge" style="color:{color};">{icon} {label}</span>
            </div>
            <div class="grid">{cards_html}</div>
        </section>"""

    total = sum(len(i) for _, _, i, _ in all_data)

    setup_banner = ""
    if not has_api_key:
        setup_banner = """
    <div class="setup-banner">
        <strong>🔑 Muốn dùng Etsy thay Redbubble?</strong>
        Lấy API key miễn phí tại
        <a href="https://www.etsy.com/developers/register" target="_blank" style="color:#ffa657;">etsy.com/developers/register</a>
        → điền vào <code>config.json</code> → chạy lại tool.
        Etsy API cho phép xem competition count chính xác hơn!
    </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🛒 POD Bestseller Spy</title>
    <style>
        :root {{
            --bg:#0d1117; --card:#161b22; --card2:#1c2333; --border:#30363d;
            --text:#c9d1d9; --muted:#8b949e;
            --orange:#ffa657; --green:#3fb950; --blue:#58a6ff; --red:#ff7b72;
        }}
        *{{ box-sizing:border-box; margin:0; padding:0; }}
        body{{ font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif;
               background:var(--bg); color:var(--text); }}
        header{{ text-align:center; padding:1.5rem 1rem;
                 background:linear-gradient(135deg,#010409,#0d1117);
                 border-bottom:1px solid var(--border); }}
        h1{{ font-size:2rem; font-weight:900;
             background:linear-gradient(90deg,#ffa657,#ff7b72);
             -webkit-background-clip:text; -webkit-text-fill-color:transparent; }}
        .subtitle{{ color:var(--muted); font-size:0.8rem; margin-top:0.3rem; }}
        .source-tag{{ display:inline-block; margin-top:0.6rem;
            background:#1c2333; border:1px solid var(--border); border-radius:10px;
            font-size:0.68rem; padding:3px 14px;
            color:{"var(--green)" if has_api_key else "var(--orange)"}; }}
        .setup-banner{{ background:#1c2333; border:1px solid var(--border);
            border-left:4px solid var(--orange); border-radius:8px;
            padding:0.8rem 1.2rem; margin:1rem auto; max-width:1100px;
            font-size:0.76rem; color:var(--text); line-height:1.7; }}
        .setup-banner code{{ background:#0d1117; padding:2px 6px; border-radius:4px; color:var(--orange); }}
        .stats-bar{{ display:flex; gap:1.5rem; justify-content:center; flex-wrap:wrap;
            padding:0.7rem 2rem; background:var(--card);
            border-bottom:1px solid var(--border);
            font-size:0.75rem; color:var(--muted); }}
        .stats-bar strong{{ color:#fff; }}
        .tip{{ background:#1c2333; border:1px solid var(--border);
            border-left:3px solid var(--orange); border-radius:8px;
            padding:0.8rem 1.2rem; margin:1rem auto; max-width:1100px;
            font-size:0.75rem; color:var(--orange); line-height:1.7; }}
        .tip strong{{ color:#fff; }}
        .container{{ max-width:1600px; margin:0 auto; padding:1rem 1.5rem; }}
        .kw-section{{ margin-bottom:2rem; }}
        .kw-header{{ display:flex; justify-content:space-between; align-items:center;
            margin-bottom:0.8rem; padding-bottom:0.6rem;
            border-bottom:1px solid var(--border); flex-wrap:wrap; gap:0.5rem; }}
        .kw-left{{ display:flex; align-items:center; gap:0.6rem; }}
        .cat-badge{{ font-size:0.62rem; font-weight:700; padding:2px 8px;
            background:#1f6feb; color:#fff; border-radius:8px; }}
        .kw-name{{ font-size:0.9rem; font-weight:700; color:#fff; }}
        .comp-badge{{ font-size:0.68rem; font-weight:700;
            padding:2px 10px; border-radius:10px; background:var(--card2); }}
        .grid{{ display:grid; grid-template-columns:repeat(auto-fill,minmax(135px,1fr)); gap:0.8rem; }}
        .card{{ background:var(--card); border:1px solid var(--border);
            border-radius:10px; overflow:hidden; transition:all 0.2s; }}
        .card:hover{{ border-color:var(--orange); transform:translateY(-3px);
            box-shadow:0 8px 20px rgba(255,166,87,0.12); }}
        .card-img-wrap{{ display:block; width:100%; padding-top:100%; position:relative; background:#fff; }}
        .card-img-wrap img{{ position:absolute; top:0; left:0; width:100%; height:100%;
            object-fit:contain; padding:0.3rem; }}
        .card-body{{ padding:0.5rem 0.6rem; }}
        .card-title{{ font-size:0.6rem; color:var(--text); line-height:1.35;
            display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical;
            overflow:hidden; margin-bottom:0.3rem; }}
        .card-meta{{ display:flex; justify-content:space-between; }}
        .card-price{{ font-size:0.65rem; color:var(--green); font-weight:700; }}
        .card-extra{{ font-size:0.55rem; color:var(--muted); overflow:hidden;
            white-space:nowrap; text-overflow:ellipsis; }}
        ::-webkit-scrollbar{{ width:6px; }}
        ::-webkit-scrollbar-thumb{{ background:var(--border); border-radius:3px; }}
    </style>
</head>
<body>
    <header>
        <h1>🛒 POD Bestseller Spy</h1>
        <p class="subtitle">Top-selling sports t-shirts — {now}</p>
        <span class="source-tag">{'✅ Nguồn: Etsy Open API (chính xác nhất)' if has_api_key else '🔄 Nguồn: Redbubble HTTP (Chưa có Etsy API key)'}</span>
    </header>
    {setup_banner}
    <div class="stats-bar">
        <div>📦 <strong>{total}</strong> Bestsellers</div>
        <div>🔍 <strong>{len(all_data)}</strong> Keywords</div>
        <div>📡 Source: <strong>{source_name}</strong></div>
        <div>🟢 LOW = cơ hội · 🔴 HIGH = bão hòa</div>
    </div>
    <div class="tip">
        <strong>💡 Cách dùng:</strong>
        Click vào ảnh để xem listing gốc. 🟢 LOW = ít người bán → <strong>cơ hội tốt để vào</strong>.
        {'❤ = favorites (nhu cầu) | 👁 = views (traffic) — cao là dấu hiệu tốt!' if has_api_key else 'Dữ liệu này được lưu vào etsy_data.json → dùng bởi Idea Generator.'}
    </div>
    <div class="container">
        {sections or '<p style="text-align:center;padding:3rem;color:#8b949e;">Không tìm được kết quả — kiểm tra kết nối mạng.</p>'}
    </div>
</body>
</html>"""


# =============================================================
#  MAIN
# =============================================================
def main():
    print("══════════════════════════════════════════════════")
    print("  🛒 POD BESTSELLER SPY — API Edition            ")
    print("  Không dùng Browser → Không bao giờ bị block   ")
    print("══════════════════════════════════════════════════")
    print()

    cfg     = load_config()
    api_key = cfg.get("etsy_api_key", "").strip()
    all_data     = []
    source_name  = ""
    has_api_key  = bool(api_key)

    if has_api_key:
        print(f"  🔑 Etsy API key: ...{api_key[-6:]}")
        print(f"  📡 Dùng Etsy Open API v3 (chính xác nhất)")
        print()

        for kw, cat in ETSY_KEYWORDS:
            print(f"  🔍 [{cat}] '{kw}'...")
            items, count = fetch_etsy_listings(kw, cat, api_key)
            icon, _, label = competition_label(count, "etsy")
            print(f"  📦 {len(items)} items | {icon} {label}")
            all_data.append((kw, cat, items, count))
            time.sleep(0.5)  # Polite delay cho API

        source_name = "Etsy"
    else:
        print("  ⚠  Chưa có Etsy API key trong config.json")
        print("  🔄 Dùng Redbubble HTTP (không cần API key)")
        print()
        print("  💡 Để dùng Etsy (tốt hơn):")
        print("     1. Vào https://www.etsy.com/developers/register")
        print("     2. Tạo app → copy API key")
        print("     3. Dán vào config.json → chạy lại tool")
        print()

        for kw, cat, code in REDBUBBLE_KEYWORDS:
            items, count = fetch_redbubble_listings(kw, cat, code)
            all_data.append((kw, cat, items, count))
            time.sleep(1.5)

        source_name = "Redbubble"

    total = sum(len(items) for _, _, items, _ in all_data)
    print(f"\n📊 Tổng: {total} items từ {source_name}")

    save_json(all_data, source_name)

    now = datetime.now().strftime("%H:%M:%S — %d/%m/%Y")
    html = generate_html(all_data, now, source_name, has_api_key)
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\n✅ Dashboard: etsy_spy.html")
    webbrowser.open(f"file://{OUTPUT_HTML}")
    print("🎉 Hoàn tất!")

    if not has_api_key:
        print()
        print("══════════════════════════════════════════════════")
        print("  🔑 Lấy Etsy API key miễn phí (5 phút):")
        print("  → https://www.etsy.com/developers/register")
        print("  → Dán key vào config.json | etsy_api_key")
        print("══════════════════════════════════════════════════")
        webbrowser.open("https://www.etsy.com/developers/register")


if __name__ == "__main__":
    main()
