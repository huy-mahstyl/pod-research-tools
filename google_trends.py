import os
import re
import time
import json
import urllib.request
import urllib.parse
import webbrowser
from datetime import datetime

# ============================================================
# SPORTS / POD KEYWORDS — dùng để lọc xu hướng liên quan
# ============================================================
SPORTS_KEYWORDS = [
    # ── Leagues ──
    "nfl", "nba", "mlb", "nhl", "ncaa", "ncaab", "ncaaw", "mls", "espn",
    "basketball", "football", "baseball", "hockey", "soccer",
    "play-in", "play in", "playoff", "postseason",
    # ── NBA Teams ──
    "lakers", "celtics", "warriors", "bulls", "knicks", "heat", "nuggets",
    "thunder", "bucks", "cavaliers", "cavs", "sixers", "suns", "clippers",
    "nets", "raptors", "rockets", "grizzlies", "pelicans", "spurs",
    "timberwolves", "wolves", "blazers", "trail blazers", "wizards",
    "pistons", "hornets", "magic", "hawks", "pacers", "kings",
    # ── NFL Teams ──
    "chiefs", "eagles", "cowboys", "49ers", "niners", "patriots", "ravens",
    "bills", "bengals", "steelers", "dolphins", "lions", "packers", "bears",
    "jets", "giants", "commanders", "titans", "jaguars", "texans",
    "chargers", "broncos", "raiders", "seahawks", "cardinals", "falcons",
    "saints", "panthers", "buccaneers", "bucs", "colts", "vikings",
    # ── MLB Teams ──
    "dodgers", "yankees", "red sox", "astros", "braves", "mets", "cubs",
    "padres", "phillies", "rangers", "orioles", "guardians", "twins",
    "royals", "white sox", "reds", "pirates", "marlins", "rockies",
    "diamondbacks", "d-backs", "tigers", "angels", "athletics", "blue jays",
    "brewers", "mariners", "rays",
    # ── NHL Teams ──
    "bruins", "maple leafs", "penguins", "lightning", "blackhawks",
    "canadiens", "habs", "flyers", "red wings", "oilers", "flames",
    "canucks", "sharks", "predators", "wild", "avalanche", "blues",
    "hurricanes", "devils", "islanders", "kraken", "jets", "senators",
    "golden knights", "panthers", "stars", "ducks",
    # ── NCAA ──
    "ucla", "auburn", "war eagle", "uconn", "huskies",
    "nc state", "wolfpack", "gonzaga", "purdue", "boilermakers",
    "iowa hawkeyes", "houston cougars", "duke", "blue devils",
    "tar heels", "unc", "jayhawks", "kansas", "wildcats", "kentucky",
    "spartans", "michigan state", "gators", "florida", "illini", "illinois",
    "hoosiers", "indiana", "wolverines", "michigan",
    "south carolina gamecocks", "tennessee volunteers", "vols",
    "lsu tigers", "texas longhorns", "baylor bears",
    "caitlin clark", "march madness", "final four", "elite eight",
    "sweet sixteen", "championship game", "ncaa tournament", "bracket",
    "selection sunday",
    # ── Big Events ──
    "super bowl", "world series", "stanley cup",
    "mvp", "all-star", "nba draft", "nfl draft", "mlb draft",
    "trade deadline", "free agent",
    # ── General Sports / POD ──
    "game day", "gameday", "t-shirt", "tshirt", "hoodie", "merch",
    "roster", "standings", "highlights",
]

# Nguồn tin thể thao — dùng để nhận diện thêm từ news source
SPORTS_SOURCES = [
    "espn", "nba.com", "nfl.com", "mlb.com", "nhl.com",
    "nbcsports", "nbc sports", "sports illustrated", "si.com",
    "bleacher report", "yahoo sports", "fox sports", "cbs sports",
    "the athletic", "sportsnaut", "fantasypros", "heavy.com",
    "true blue", "sfchronicle.com/sports", "nbcsportsbayarea",
    "nbclosangeles", "nypost.com/sports",
]


# ============================================================
# LẤY DỮ LIỆU TỪ GOOGLE TRENDS RSS
# ============================================================
def fetch_trends_rss():
    """Lấy danh sách xu hướng tìm kiếm hôm nay ở Mỹ qua RSS.
    Parse toàn bộ dữ liệu: title, traffic, thumbnail, news items, pubDate.
    """
    print("📡 Đang lấy Google Trends Daily RSS (US)...")
    url = "https://trends.google.com/trending/rss?geo=US"
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                       'AppleWebKit/537.36 (KHTML, like Gecko) '
                       'Chrome/124.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
    })
    try:
        response = urllib.request.urlopen(req, timeout=20)
        xml = response.read().decode('utf-8')

        items = re.findall(r'<item>(.*?)</item>', xml, re.DOTALL)
        trending = []
        for item in items:
            title_m = re.search(r'<title>(.*?)</title>', item)
            traffic_m = re.search(r'<ht:approx_traffic>(.*?)</ht:approx_traffic>', item)
            picture_m = re.search(r'<ht:picture>(.*?)</ht:picture>', item)
            pubdate_m = re.search(r'<pubDate>(.*?)</pubDate>', item)

            # Lấy TẤT CẢ news items (không chỉ cái đầu)
            news_items = []
            news_blocks = re.findall(r'<ht:news_item>(.*?)</ht:news_item>', item, re.DOTALL)
            for nb in news_blocks:
                n_title = re.search(r'<ht:news_item_title>(.*?)</ht:news_item_title>', nb)
                n_url = re.search(r'<ht:news_item_url>(.*?)</ht:news_item_url>', nb)
                n_source = re.search(r'<ht:news_item_source>(.*?)</ht:news_item_source>', nb)
                n_pic = re.search(r'<ht:news_item_picture>(.*?)</ht:news_item_picture>', nb)
                if n_title:
                    news_items.append({
                        'title': _unescape(n_title.group(1).strip()),
                        'url': n_url.group(1).strip() if n_url else '',
                        'source': _unescape(n_source.group(1).strip()) if n_source else '',
                        'picture': n_pic.group(1).strip() if n_pic else '',
                    })

            title = _unescape(title_m.group(1).strip()) if title_m else ''
            traffic = traffic_m.group(1).strip() if traffic_m else ''
            picture = picture_m.group(1).strip() if picture_m else ''
            pubdate = pubdate_m.group(1).strip() if pubdate_m else ''

            if title:
                trending.append({
                    'query': title,
                    'traffic': traffic,
                    'traffic_num': _parse_traffic(traffic),
                    'picture': picture,
                    'pubdate': pubdate,
                    'news_items': news_items,
                    'is_pod': False,  # sẽ tính sau
                })

        # Tính is_pod cho từng item
        for t in trending:
            t['is_pod'] = is_pod_relevant(t)

        print(f"  ✅ Lấy được {len(trending)} xu hướng từ RSS")
        return trending
    except Exception as e:
        print(f"  ⚠ Lỗi RSS: {e}")
        return []


def _unescape(text):
    """Unescape HTML entities trong RSS."""
    replacements = [
        ('&amp;', '&'), ('&lt;', '<'), ('&gt;', '>'),
        ('&#39;', "'"), ('&apos;', "'"), ('&quot;', '"'),
        ('<![CDATA[', ''), (']]>', ''),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def _parse_traffic(traffic_str):
    """Parse traffic string thành số. VD: '5000+' → 5000, '200+' → 200."""
    if not traffic_str:
        return 0
    try:
        s = traffic_str.replace('+', '').replace(',', '').strip()
        if 'M' in s.upper():
            return int(float(s.upper().replace('M', '')) * 1_000_000)
        elif 'K' in s.upper():
            return int(float(s.upper().replace('K', '')) * 1_000)
        else:
            return int(s)
    except (ValueError, TypeError):
        return 0


def _traffic_class(num):
    """Trả về CSS class dựa trên traffic number."""
    if num >= 5000:
        return 'val-hot'
    elif num >= 1000:
        return 'val-high'
    else:
        return 'val-normal'


# ============================================================
# SMART POD / SPORTS DETECTION
# ============================================================
def is_pod_relevant(item):
    """Kiểm tra xem một trend có liên quan Sports/POD không.
    Scan cả: query, news titles, news sources.
    Dùng word-boundary regex để tránh false positive.
    """
    query_text = item['query'].lower()
    news_titles = ' '.join(n.get('title', '').lower() for n in item.get('news_items', []))
    news_sources = ' '.join(n.get('source', '').lower() for n in item.get('news_items', []))

    # Check 1: Sports keywords trong query (quan trọng nhất)
    for kw in SPORTS_KEYWORDS:
        if re.search(r'\b' + re.escape(kw) + r'\b', query_text):
            return True

    # Check 2: Sports keywords trong news titles (dùng word boundary)
    for kw in SPORTS_KEYWORDS:
        if re.search(r'\b' + re.escape(kw) + r'\b', news_titles):
            return True

    # Check 3: News từ nguồn thể thao (chỉ check source, không check title)
    for src in SPORTS_SOURCES:
        if src in news_sources:
            return True

    return False


# ============================================================
# EXPORT JSON
# ============================================================
def export_json(trends):
    """Lưu dữ liệu ra JSON để các tool khác dùng."""
    output_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               'google_trends_data.json')
    export_data = {
        'generated_at': datetime.now().isoformat(),
        'total_trends': len(trends),
        'pod_relevant_count': sum(1 for t in trends if t['is_pod']),
        'trends': trends,
    }
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)
    print(f"  💾 Đã lưu JSON: {output_file}")
    return output_file


# ============================================================
# GENERATE HTML DASHBOARD
# ============================================================
def generate_html(trends):
    now = datetime.now().strftime("%H:%M:%S — %d/%m/%Y")
    pod_trends = [t for t in trends if t['is_pod']]
    other_trends = [t for t in trends if not t['is_pod']]

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="1800">
    <title>📊 Google Trends — POD Monitor</title>
    <meta name="description" content="Real-time Google Trends monitoring for Print-on-Demand keyword research">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg: #0a0e17;
            --bg-subtle: #0f1420;
            --card: #141b2d;
            --card-hover: #1a2338;
            --border: #1e2a42;
            --border-light: #2a3a5c;
            --text: #e2e8f0;
            --text-muted: #64748b;
            --text-dim: #475569;
            --red: #ef4444;
            --red-glow: rgba(239,68,68,0.15);
            --green: #22c55e;
            --green-glow: rgba(34,197,94,0.15);
            --orange: #f59e0b;
            --orange-glow: rgba(245,158,11,0.15);
            --blue: #3b82f6;
            --blue-glow: rgba(59,130,246,0.15);
            --purple: #a855f7;
            --cyan: #06b6d4;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
        }}

        /* ── Header ── */
        header {{
            text-align: center;
            padding: 2rem 1rem 1.5rem;
            background: linear-gradient(180deg, #0f1628 0%, var(--bg) 100%);
            border-bottom: 1px solid var(--border);
            position: relative;
            overflow: hidden;
        }}
        header::before {{
            content: '';
            position: absolute;
            top: -50%;
            left: 50%;
            transform: translateX(-50%);
            width: 600px;
            height: 600px;
            background: radial-gradient(circle, rgba(59,130,246,0.08) 0%, transparent 70%);
            pointer-events: none;
        }}
        h1 {{
            font-size: 2.2rem;
            font-weight: 900;
            letter-spacing: -0.03em;
            background: linear-gradient(135deg, #22c55e 0%, #3b82f6 50%, #a855f7 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        .subtitle {{
            color: var(--text-muted);
            font-size: 0.85rem;
            margin-top: 0.4rem;
            font-weight: 500;
        }}
        .stats-bar {{
            display: flex;
            justify-content: center;
            gap: 2rem;
            margin-top: 1rem;
            flex-wrap: wrap;
        }}
        .stat {{
            display: flex;
            align-items: center;
            gap: 0.4rem;
            font-size: 0.8rem;
            font-weight: 600;
            padding: 0.35rem 0.8rem;
            border-radius: 20px;
            background: var(--card);
            border: 1px solid var(--border);
        }}
        .stat-fire {{ color: var(--red); }}
        .stat-pod {{ color: var(--green); }}
        .stat-time {{ color: var(--blue); }}

        /* ── Refresh Button ── */
        .refresh-btn {{
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            margin-top: 1rem;
            padding: 0.45rem 1.2rem;
            font-size: 0.75rem;
            font-weight: 600;
            color: var(--blue);
            background: rgba(59,130,246,0.1);
            border: 1px solid rgba(59,130,246,0.3);
            border-radius: 20px;
            cursor: pointer;
            transition: all 0.2s;
            text-decoration: none;
        }}
        .refresh-btn:hover {{
            background: rgba(59,130,246,0.2);
            border-color: var(--blue);
            transform: translateY(-1px);
        }}

        /* ── Layout ── */
        .container {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1.2rem;
            padding: 1.2rem;
            max-width: 1400px;
            margin: 0 auto;
        }}
        @media (max-width: 768px) {{
            .container {{ grid-template-columns: 1fr; }}
        }}

        /* ── Section ── */
        .section {{
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 12px;
            overflow: hidden;
        }}
        .section-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 1rem 1.2rem;
            border-bottom: 1px solid var(--border);
        }}
        .section-title {{
            font-size: 1rem;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        .section-count {{
            font-size: 0.7rem;
            font-weight: 600;
            padding: 2px 8px;
            border-radius: 10px;
        }}
        .count-red {{ background: var(--red-glow); color: var(--red); }}
        .count-green {{ background: var(--green-glow); color: var(--green); }}
        .section-body {{
            max-height: 75vh;
            overflow-y: auto;
        }}

        /* ── Trend Card ── */
        .trend-card {{
            display: flex;
            gap: 0.8rem;
            padding: 0.8rem 1.2rem;
            border-bottom: 1px solid rgba(30,42,66,0.5);
            transition: background 0.15s;
            animation: fadeIn 0.3s ease-out both;
        }}
        .trend-card:hover {{
            background: var(--card-hover);
        }}
        .trend-card:last-child {{
            border-bottom: none;
        }}
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(8px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        .trend-thumb {{
            width: 56px;
            height: 56px;
            border-radius: 8px;
            object-fit: cover;
            flex-shrink: 0;
            background: var(--bg-subtle);
            border: 1px solid var(--border);
        }}
        .trend-content {{
            flex: 1;
            min-width: 0;
        }}
        .trend-top {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            margin-bottom: 0.3rem;
        }}
        .trend-rank {{
            font-size: 0.65rem;
            font-weight: 700;
            color: var(--text-dim);
            min-width: 22px;
        }}
        .trend-query {{
            font-size: 0.85rem;
            font-weight: 600;
            color: var(--text);
            text-decoration: none;
            transition: color 0.15s;
        }}
        .trend-query:hover {{
            color: var(--blue);
        }}

        /* ── Badges ── */
        .badge {{
            font-size: 0.6rem;
            font-weight: 700;
            padding: 2px 7px;
            border-radius: 6px;
            white-space: nowrap;
        }}
        .badge-hot {{
            background: var(--red);
            color: #fff;
            box-shadow: 0 0 8px var(--red-glow);
        }}
        .badge-high {{
            background: var(--orange);
            color: #fff;
        }}
        .badge-normal {{
            background: rgba(100,116,139,0.2);
            color: var(--text-muted);
        }}
        .badge-pod {{
            background: rgba(34,197,94,0.15);
            color: var(--green);
            border: 1px solid rgba(34,197,94,0.3);
        }}

        /* ── News items ── */
        .news-list {{
            margin-top: 0.3rem;
        }}
        .news-item {{
            display: flex;
            align-items: flex-start;
            gap: 0.3rem;
            margin-bottom: 0.2rem;
        }}
        .news-bullet {{
            color: var(--text-dim);
            font-size: 0.55rem;
            margin-top: 0.2rem;
            flex-shrink: 0;
        }}
        .news-link {{
            font-size: 0.7rem;
            color: var(--text-muted);
            text-decoration: none;
            display: -webkit-box;
            -webkit-line-clamp: 1;
            -webkit-box-orient: vertical;
            overflow: hidden;
            transition: color 0.15s;
        }}
        .news-link:hover {{
            color: var(--cyan);
        }}
        .news-source {{
            font-size: 0.6rem;
            color: var(--text-dim);
            font-weight: 500;
        }}

        /* ── Action Links ── */
        .trend-actions {{
            display: flex;
            gap: 0.5rem;
            margin-top: 0.35rem;
        }}
        .action-link {{
            font-size: 0.6rem;
            font-weight: 600;
            color: var(--text-dim);
            text-decoration: none;
            padding: 2px 6px;
            border-radius: 4px;
            border: 1px solid var(--border);
            transition: all 0.15s;
        }}
        .action-link:hover {{
            color: var(--blue);
            border-color: rgba(59,130,246,0.4);
            background: var(--blue-glow);
        }}

        /* ── Empty state ── */
        .empty {{
            padding: 2rem;
            text-align: center;
            color: var(--text-muted);
            font-size: 0.85rem;
        }}

        /* ── Scrollbar ── */
        .section-body::-webkit-scrollbar {{ width: 6px; }}
        .section-body::-webkit-scrollbar-track {{ background: transparent; }}
        .section-body::-webkit-scrollbar-thumb {{
            background: var(--border);
            border-radius: 3px;
        }}
        .section-body::-webkit-scrollbar-thumb:hover {{
            background: var(--border-light);
        }}

        /* ── Footer ── */
        footer {{
            text-align: center;
            padding: 1.5rem;
            color: var(--text-dim);
            font-size: 0.7rem;
            border-top: 1px solid var(--border);
        }}
        footer a {{ color: var(--blue); text-decoration: none; }}
        footer a:hover {{ text-decoration: underline; }}
    </style>
    <script>
    // Mở link Google Search an toàn — tránh bị block khi mở từ file://
    function openSearch(url, evt) {{
        if (evt) evt.preventDefault();
        // Tạo cửa sổ mới qua about:blank trước, rồi redirect
        var w = window.open('about:blank', '_blank');
        if (w) {{
            w.location.href = url;
        }} else {{
            // Fallback nếu popup bị chặn
            window.location.href = url;
        }}
        return false;
    }}
    </script>
</head>
<body>
    <header>
        <h1>📊 Google Trends — POD Monitor</h1>
        <p class="subtitle">Real-time trending keywords in the US — for POD research</p>
        <div class="stats-bar">
            <div class="stat stat-fire">🔥 {len(trends)} xu hướng</div>
            <div class="stat stat-pod">🎯 {len(pod_trends)} liên quan Sports/POD</div>
            <div class="stat stat-time">🕐 {now}</div>
        </div>
        <a class="refresh-btn" href="javascript:location.reload()">🔄 Refresh</a>
    </header>

    <div class="container">
"""

    # ── COLUMN 1: Sports / POD Relevant (ĐẶT LÊN TRƯỚC vì quan trọng hơn) ──
    html += f"""
        <div class="section" id="pod-section">
            <div class="section-header">
                <div class="section-title" style="color: var(--green);">
                    🏆 Sports & POD Relevant
                </div>
                <span class="section-count count-green">{len(pod_trends)} found</span>
            </div>
            <div class="section-body">
"""
    if pod_trends:
        for i, item in enumerate(pod_trends):
            html += _render_trend_card(i, item, show_why=True)
    else:
        html += '<div class="empty">Không tìm thấy xu hướng liên quan Sports/POD hôm nay.</div>'

    html += """
            </div>
        </div>
"""

    # ── COLUMN 2: All Trending ──
    html += f"""
        <div class="section" id="all-section">
            <div class="section-header">
                <div class="section-title" style="color: var(--red);">
                    🔥 All Trending Today
                </div>
                <span class="section-count count-red">{len(trends)} total</span>
            </div>
            <div class="section-body">
"""
    if trends:
        for i, item in enumerate(trends):
            html += _render_trend_card(i, item, show_why=False)
    else:
        html += '<div class="empty">Không có dữ liệu. Thử lại sau.</div>'

    html += """
            </div>
        </div>
"""

    html += """
    </div>
"""

    # ── Footer ──
    html += f"""
    <footer>
        Dữ liệu từ <a href="https://trends.google.com/trending?geo=US" target="_blank">Google Trends RSS</a>
        — Không cần API key, không bị CAPTCHA
        — Auto-refresh mỗi 30 phút
        — Scan lúc {now}
    </footer>
</body>
</html>"""

    output_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               'google_trends.html')
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    return output_file


def _render_trend_card(index, item, show_why=False):
    """Render 1 trend card HTML."""
    q = item['query']
    q_encoded = urllib.parse.quote_plus(q)
    google_link = f"https://www.google.com/search?q={q_encoded}&amp;tbm=isch"
    trends_link = f"https://trends.google.com/trends/explore?q={q_encoded}&amp;geo=US"
    pod_search_link = f"https://www.google.com/search?q={q_encoded}+t+shirt&amp;tbm=isch"

    traffic = item.get('traffic', '')
    traffic_num = item.get('traffic_num', 0)
    picture = item.get('picture', '')
    news_items = item.get('news_items', [])
    is_pod = item.get('is_pod', False)

    # Traffic badge
    tc = _traffic_class(traffic_num)
    badge_class = {'val-hot': 'badge-hot', 'val-high': 'badge-high', 'val-normal': 'badge-normal'}[tc]

    # Thumbnail
    thumb_html = ''
    if picture:
        thumb_html = f'<img class="trend-thumb" src="{picture}" alt="{q}" loading="lazy" onerror="this.style.display=\'none\'">'

    # POD badge
    pod_badge = '<span class="badge badge-pod">POD</span>' if is_pod else ''

    # Traffic badge
    traffic_badge = f'<span class="badge {badge_class}">{traffic}</span>' if traffic else ''

    # News items (max 2)
    news_html = ''
    if news_items:
        news_html = '<div class="news-list">'
        for n in news_items[:2]:
            title = n.get('title', '')
            url = n.get('url', '#')
            source = n.get('source', '')
            source_tag = f' <span class="news-source">— {source}</span>' if source else ''
            news_html += f'''
                <div class="news-item">
                    <span class="news-bullet">▸</span>
                    <a class="news-link" href="{url}" target="_blank" rel="noopener noreferrer">{title}{source_tag}</a>
                </div>'''
        news_html += '</div>'

    # Animation delay
    delay = index * 0.03

    card = f'''
            <div class="trend-card" style="animation-delay: {delay:.2f}s">
                {thumb_html}
                <div class="trend-content">
                    <div class="trend-top">
                        <span class="trend-rank">#{index + 1}</span>
                        <a class="trend-query" href="{google_link}" onclick="return openSearch(this.href, event)">{q}</a>
                        {traffic_badge}
                        {pod_badge}
                    </div>
                    {news_html}
                    <div class="trend-actions">
                        <a class="action-link" href="{google_link}" onclick="return openSearch(this.href, event)">🖼 Images</a>
                        <a class="action-link" href="{trends_link}" onclick="return openSearch(this.href, event)">📈 Trends</a>
                        <a class="action-link" href="{pod_search_link}" onclick="return openSearch(this.href, event)">👕 POD Search</a>
                    </div>
                </div>
            </div>'''
    return card


# ============================================================
# MAIN
# ============================================================
def main():
    print("=" * 55)
    print("  📊 GOOGLE TRENDS — POD KEYWORD MONITOR v2.0")
    print("  ✅ RSS Feed — Không CAPTCHA, Không API Key")
    print("=" * 55)

    # Lấy trending data
    trends = fetch_trends_rss()

    if not trends:
        print("\n⚠ Không lấy được dữ liệu. Kiểm tra kết nối mạng.")
        return

    # Thống kê
    pod_relevant = [t for t in trends if t['is_pod']]

    print(f"\n📊 Tổng kết:")
    print(f"  🔥 Tổng xu hướng hôm nay: {len(trends)}")
    print(f"  🎯 Liên quan Sports/POD: {len(pod_relevant)}")
    if pod_relevant:
        print(f"  📋 POD trends:")
        for t in pod_relevant:
            print(f"     → {t['query']} ({t['traffic']})")

    # Export JSON
    export_json(trends)

    # Generate HTML
    output = generate_html(trends)
    print(f"\n✅ Google Trends Dashboard đã tạo xong!")
    print(f"   Mở file: {output}")
    if not os.environ.get('CI'):
        webbrowser.open(f"file://{output}")


if __name__ == '__main__':
    main()
