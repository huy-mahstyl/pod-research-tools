import os
import re
import time
import random
import webbrowser
from datetime import datetime

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Lỗi: Thư viện Playwright chưa cài.")
    exit(1)

# ========== DANH SÁCH USER AGENT THẬT ==========
USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15',
]

# Script chống phát hiện bot (inject vào mỗi trang trước khi load)
STEALTH_SCRIPT = """
// Ẩn dấu hiệu webdriver
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});

// Giả lập plugins như Chrome thật
Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3, 4, 5],
});

// Giả lập languages
Object.defineProperty(navigator, 'languages', {
    get: () => ['en-US', 'en'],
});

// Xoá dấu vết automation trong chrome object
window.chrome = {
    runtime: {},
    loadTimes: function() {},
    csi: function() {},
    app: {}
};

// Giả lập permission query (Bot thường fail ở đây)
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) =>
    parameters.name === 'notifications'
        ? Promise.resolve({ state: Notification.permission })
        : originalQuery(parameters);
"""

# ========== CẤU HÌNH ==========
KEYWORDS = [
    "shirt for fans",
    "fans shirt",
    "fan shirt",
    "fan tee",
    "trending shirt",
]

# Bộ lọc Thể thao Mỹ
SPORTS_INCLUDE = [
    "nfl", "nba", "mlb", "nhl", "ncaa", "ncaab", "ncaaw", "mls",
    "baseball", "basketball", "football", "hockey", "soccer",
    # ── NBA ──
    "dodgers", "yankees", "lakers", "bulls", "celtics", "warriors",
    "chiefs", "eagles", "cowboys", "49ers", "packers", "ravens",
    # ── NHL ──
    "bruins", "rangers", "maple leafs", "penguins", "blackhawks",
    # ── MLB ──
    "red sox", "mets", "astros", "braves", "phillies", "padres",
    # ── NBA (more) ──
    "nuggets", "heat", "knicks", "bucks", "thunder", "cavaliers",
    "bengals", "lions", "bills", "dolphins", "steelers", "bears",
    "cardinals", "tigers", "cubs", "giants", "orioles", "guardians",
    # ── NCAA Men's Football ──
    "crimson tide", "wolverines", "buckeyes", "bulldogs",
    "bison", "boilermakers", "panthers", "trojans",
    # ── NCAA Men's Basketball ──
    "ucla", "bruins basketball", "ucla bruins",
    "michigan basketball", "wolverines basketball",
    "wildcats", "tar heels", "blue devils", "spartans", "gators",
    "longhorns", "jayhawks", "hoosiers", "illini",
    "auburn", "war eagle", "uconn", "huskies", "gonzaga", "zags",
    "houston cougars", "purdue", "wolfpack", "nc state",
    "iowa hawkeyes", "tennessee volunteers",
    # ── NCAA Women's Basketball ──
    "ucla women", "ucla women's basketball",
    "south carolina gamecocks", "gamecocks",
    "uconn women", "uconn huskies women",
    "iowa women", "iowa hawkeyes women",
    "lsu women", "lady tigers",
    "tennessee lady vols", "lady vols",
    "texas longhorns women",
    "women's basketball", "women's march madness", "ncaaw",
    # ── Tournament ──
    "march madness", "final four", "elite eight", "sweet sixteen",
    "championship", "playoff", "tournament", "bracket",
    "super bowl", "world series", "stanley cup", "mvp",
    # ── General ──
    "sport", "fan", "team", "jersey", "game day", "stadium",
    "coach", "player", "draft", "athlete", "varsity", "college",
    "slam dunk", "touchdown", "home run", "goal", "pitch",
    "tailgate", "season", "athletic",
]

EXCLUDE_TERMS = [
    "anime", "manga", "naruto", "dragon ball", "one piece", "jojo",
    "kpop", "k-pop", "bts", "blackpink", "taylor swift",
    "trump", "biden", "maga", "political", "democrat", "republican",
    "vote", "election", "liberal", "conservative",
    "cat", "dog", "pet", "minecraft", "roblox", "fortnite",
    "jesus", "bible", "church", "prayer",
    "weed", "cannabis", "420",
    "only fans", "onlyfans", "sexy",
    "monster truck", "wrestling", "wwe",
    "jersey", "replica", "authentic", "official", "licensed",
    "nike", "adidas", "under armour", "new era", "fanatics",
    "stitched", "sewn", "embroidered", "uniform",
    "breathable football", "match kit", "home kit", "away kit",
    "swingman", "vapor", "dri-fit", "dry fit",
]


def human_delay(min_ms=800, max_ms=2500):
    """Delay ngẫu nhiên giống người thật."""
    time.sleep(random.uniform(min_ms / 1000, max_ms / 1000))


def check_captcha(page):
    """Kiểm tra xem trang có đang hiển thị CAPTCHA không."""
    captcha_indicators = [
        'g-recaptcha', 'recaptcha', 'captcha',
        'unusual traffic', "verify you're human",
        'our systems have detected', 'before you continue',
        'nocaptcha', 'hcaptcha',
    ]
    try:
        content = page.content().lower()
        for indicator in captcha_indicators:
            if indicator in content:
                return True
    except Exception:
        pass
    return False


def is_us_sports_related(title):
    """Kiểm tra xem tiêu đề có liên quan đến thể thao Mỹ không."""
    title_lower = title.lower()
    for term in EXCLUDE_TERMS:
        if term in title_lower:
            return False
    for term in SPORTS_INCLUDE:
        if term in title_lower:
            return True
    return False


def scrape_google_images(page, keyword):
    print(f"  🔍 Đang quét Google Images: '{keyword}' (24h)...")
    try:
        url = f"https://www.google.com/search?q={keyword.replace(' ', '+')}&tbm=isch&tbs=qdr:d"
        page.goto(url, timeout=30000, wait_until='domcontentloaded')
        human_delay(2000, 4000)

        # Kiểm tra CAPTCHA ngay sau khi load
        if check_captcha(page):
            print("  ⚠ Phát hiện CAPTCHA! Đợi 30 giây rồi thử lại...")
            time.sleep(30)
            page.goto(url, timeout=30000, wait_until='domcontentloaded')
            human_delay(3000, 5000)
            if check_captcha(page):
                print("  ❌ Vẫn bị CAPTCHA. Bỏ qua keyword này.")
                return []

        # Xử lý consent dialog
        try:
            consent_btn = page.locator(
                'button:has-text("Accept"), button:has-text("Agree"), '
                'button:has-text("Chấp nhận"), button:has-text("Đồng ý")'
            )
            if consent_btn.count() > 0:
                consent_btn.first.click()
                human_delay(1500, 2500)
        except Exception:
            pass

        # Di chuyển chuột ngẫu nhiên như người thật
        try:
            page.mouse.move(random.randint(200, 800), random.randint(200, 600))
            human_delay(300, 700)
            page.mouse.move(random.randint(200, 800), random.randint(200, 600))
        except Exception:
            pass

        # Cuộn từ từ như người thật
        for _ in range(6):
            scroll_amount = random.randint(500, 1200)
            page.evaluate(f"window.scrollBy(0, {scroll_amount})")
            human_delay(600, 1200)

        # Lấy tất cả ảnh
        raw_results = page.evaluate("""
            () => {
                const items = [];
                const allImgs = document.querySelectorAll('img');
                for (const img of allImgs) {
                    const src = img.src || img.getAttribute('data-src') || '';
                    const alt = img.alt || '';
                    const w = img.naturalWidth || img.width || 0;

                    if (alt && alt.length > 5 && (w > 50 || src.startsWith('data:image')) && !src.includes('google.com/images/branding')) {
                        let link = '';
                        const parentA = img.closest('a');

                        if (parentA && parentA.href) {
                            link = parentA.href;
                        } else {
                            const container = img.closest('div');
                            if (container) {
                                const aTags = container.querySelectorAll('a');
                                for (let a of aTags) {
                                    if (a.href && a.href !== '#' && !a.href.startsWith('javascript:')) {
                                        link = a.href;
                                        break;
                                    }
                                }
                            }
                        }

                        if (link.includes('/imgres?')) {
                            const match = link.match(/imgrefurl=([^&]+)/);
                            if (match) link = decodeURIComponent(match[1]);
                        } else if (link.includes('/url?q=')) {
                            const match = link.match(/\/url\?q=([^&]+)/);
                            if (match) link = decodeURIComponent(match[1]);
                        }

                        if (!link || link === '#' || link.startsWith('file://') || link.startsWith('javascript:')) {
                            link = 'https://www.google.com/search?q=' + encodeURIComponent(alt);
                        }

                        items.push({title: alt, image: src, link: link});
                    }
                }
                return items;
            }
        """)
        return raw_results
    except Exception as e:
        print(f"  ⚠ Lỗi khi quét '{keyword}': {e}")
        return []


def update_dashboard(curated_results):
    output_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'daily_ideas.html')

    if not os.path.exists(output_file):
        print(f"File {output_file} not found.")
        return

    with open(output_file, 'r', encoding='utf-8') as f:
        html_content = f.read()

    now = datetime.now().strftime("%H:%M %d/%m/%Y")
    spy_html = f"""
        <h2 style="color: #ff7b72; margin-bottom: 0.5rem; font-size: 1.4rem; border-bottom: 2px solid #30363d; padding-bottom: 0.5rem;">🏆 US Sports Trend Spy</h2>
        <p style="color:#8b949e; font-size:0.75rem; margin-bottom:1.5rem;">Curated at {now} — AI-filtered for US Sports only</p>
        <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 0.8rem;">
    """

    for res in curated_results:
        title = res.get('title', '')[:70]
        image_src = res.get('image', '')
        link = res.get('link', '#')

        spy_html += f"""
            <div style="background: #0d1117; border: 1px solid #30363d; border-radius: 8px; overflow: hidden; transition: transform 0.2s ease, border-color 0.2s;" onmouseover="this.style.borderColor='#58a6ff';this.style.transform='translateY(-3px)'" onmouseout="this.style.borderColor='#30363d';this.style.transform='none'">
                <a href="{link}" target="_blank" style="display: block; width: 100%; padding-top: 100%; position: relative; background-color: #ffffff;">
                    <img src="{image_src}" alt="" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: contain; padding: 0.3rem;" loading="lazy">
                </a>
                <div style="padding: 0.6rem;">
                    <p style="font-size: 0.65rem; color: #c9d1d9; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; line-height: 1.3; margin-bottom: 0.4rem;">{title}</p>
                    <a href="{link}" target="_blank" style="display:block; text-align: center; padding: 0.3rem; background-color: #238636; color: #ffffff; text-decoration: none; border-radius: 4px; font-size: 0.6rem; font-weight: bold;">View Store</a>
                </div>
            </div>
        """

    spy_html += "</div>"

    if not curated_results:
        spy_html += "<p style='color:#ff7b72; margin-top:1rem;'>Không tìm thấy mẫu áo thể thao nào trong 24h qua.</p>"

    new_html = re.sub(
        r'<!-- GOOGLE_SPY_CONTENT_START -->.*?<!-- GOOGLE_SPY_CONTENT_END -->',
        spy_html,
        html_content,
        flags=re.DOTALL
    )

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(new_html)
    print("✅ Dashboard updated!")


def main():
    print("==================================================")
    print("  🏆 US SPORTS TREND SPY (AI-Curated Edition)     ")
    print("  ✅ Stealth mode — Chống CAPTCHA nâng cao        ")
    print("==================================================")

    all_raw = []

    with sync_playwright() as p:
        # Chọn user agent ngẫu nhiên
        chosen_ua = random.choice(USER_AGENTS)
        print(f"  🕵 Dùng User-Agent: ...{chosen_ua[-50:]}")

        browser = p.chromium.launch(
            headless=False,  # headless=False khó bị detect hơn
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-first-run',
                '--no-default-browser-check',
                '--disable-infobars',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-features=IsolateOrigins,site-per-process',
            ]
        )
        context = browser.new_context(
            user_agent=chosen_ua,
            viewport={
                'width': random.choice([1280, 1366, 1440, 1920]),
                'height': random.choice([768, 800, 900, 1080])
            },
            locale='en-US',
            timezone_id='America/New_York',
            geolocation={'latitude': 40.7128, 'longitude': -74.0060},
            permissions=['geolocation'],
        )

        # Inject stealth script vào MỌI trang
        context.add_init_script(STEALTH_SCRIPT)
        page = context.new_page()

        # Truy cập Google homepage trước (tự nhiên hơn)
        print("  🌐 Mở Google homepage trước...")
        page.goto('https://www.google.com', timeout=20000, wait_until='domcontentloaded')
        human_delay(2000, 3500)

        for idx, kw in enumerate(KEYWORDS):
            raw = scrape_google_images(page, kw)
            print(f"  📦 Thu thập thô: {len(raw)} ảnh cho '{kw}'")
            all_raw.extend(raw)

            if idx < len(KEYWORDS) - 1:
                wait = random.uniform(3, 8)
                print(f"  ⏳ Đợi {wait:.1f}s trước keyword tiếp theo...")
                time.sleep(wait)

        browser.close()

    # ========== PHÂN TÍCH & CHỌN LỌC ==========
    print(f"\n🧠 Đang phân tích {len(all_raw)} ảnh thô...")

    # Bước 1: Loại bỏ ảnh trùng lặp
    seen_titles = set()
    unique_results = []
    for r in all_raw:
        title_key = r['title'].lower().strip()
        if title_key not in seen_titles:
            seen_titles.add(title_key)
            unique_results.append(r)
    print(f"  → Sau loại trùng: {len(unique_results)} ảnh")

    # Bước 2: Lọc chỉ giữ lại liên quan Thể thao Mỹ
    sports_only = [r for r in unique_results if is_us_sports_related(r['title'])]
    print(f"  → Sau lọc Thể thao Mỹ: {len(sports_only)} ảnh")

    # Bước 3: Chấm điểm ưu tiên
    def score(item):
        title_lower = item['title'].lower()
        s = 0
        for term in SPORTS_INCLUDE:
            if term in title_lower:
                s += 1
        hot_terms = [
            "fan", "championship", "playoff", "super bowl", "world series",
            "march madness", "stanley cup", "game day", "mvp"
        ]
        for ht in hot_terms:
            if ht in title_lower:
                s += 3
        pod_terms = [
            "funny", "quote", "graphic", "unisex", "vintage", "retro",
            "tee", "t-shirt", "tshirt", "hoodie", "sweatshirt",
            "merch", "apparel", "gift", "humor", "parody",
            "etsy", "teepublic", "redbubble", "teespring", "viralstyle",
            "print", "custom", "design", "artwork", "typography"
        ]
        for pt in pod_terms:
            if pt in title_lower:
                s += 5
        return s

    sports_only.sort(key=score, reverse=True)
    curated = sports_only[:100]
    print(f"  🏆 Kết quả cuối cùng: {len(curated)} mẫu áo thể thao Mỹ 24h qua")

    for i, r in enumerate(curated[:5]):
        print(f"     [{i+1}] {r['title'][:70]}")
    if len(curated) > 5:
        print(f"     ... và {len(curated)-5} mẫu nữa")

    update_dashboard(curated)
    print("\n🎉 US Sports Trend Spy hoàn tất!")
    webbrowser.open(f"file://{os.path.join(os.path.dirname(os.path.abspath(__file__)), 'daily_ideas.html')}")


if __name__ == '__main__':
    main()
