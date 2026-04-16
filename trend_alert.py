import os
import re
import json
import time
import urllib.request
import urllib.parse
import webbrowser
from datetime import datetime

# ============================================================
# CẤU HÌNH
# ============================================================

# Subreddits để quét — chia thành 2 nhóm để batch request
SUBREDDITS = {
    "NBA": ["nba", "nbamemes"],
    "NFL": ["nfl", "nflmemes"],
    "MLB": ["baseball", "mlb"],
    "NHL": ["hockey", "nhl"],
    "NCAA": ["CollegeBasketball", "CFB"],
    "POD": ["printondemand", "MerchByAmazon"],
    "General": ["sports"],
}

# Search queries — tìm bài liên quan áo/fan trực tiếp
SEARCH_QUERIES = [
    "shirt fan",
    "need this on a shirt",
    "someone make this",
    "meme viral",
    "trash talk quote",
]

ESPN_FEEDS = [
    {"name": "NBA", "sport": "NBA", "url": "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/news?limit=8"},
    {"name": "NFL", "sport": "NFL", "url": "https://site.api.espn.com/apis/site/v2/sports/football/nfl/news?limit=8"},
    {"name": "MLB", "sport": "MLB", "url": "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/news?limit=8"},
    {"name": "NHL", "sport": "NHL", "url": "https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/news?limit=8"},
]

# Từ khoá viral → tăng POD score
VIRAL_KEYWORDS = [
    # Quotes / Viral moments
    "quote", "said", "told", "says", "called", "yelled", "screamed",
    "interview", "press conference", "postgame", "post-game",
    # Meme-able emotions
    "funny", "hilarious", "moment", "iconic", "legendary", "goat",
    "meme", "lol", "crying", "insane", "crazy", "wild", "epic",
    "savage", "brutal", "roasted", "destroyed", "demolished",
    "believe", "unbelievable", "incredible", "shocking",
    # Peak sports moments
    "clutch", "game winner", "walk off", "buzzer beater", "overtime",
    "championship", "playoff", "eliminated", "upset", "underdog",
    "record", "history", "first time", "never before", "all-time",
    "no-hitter", "perfect game", "triple double", "hat trick",
    # Shirt-worthy signals
    "trash talk", "celebration", "reaction", "chant", "slogan",
    "mvp", "rookie", "debut", "retirement", "farewell", "comeback",
    "dynasty", "rivalry", "revenge", "redemption", "curse",
    # Explicit merch signals
    "shirt", "tee", "hoodie", "merch", "design", "print",
    "need this on a shirt", "someone make", "i want", "shut up and take",
    "buying", "selling", "trending", "viral", "blowing up",
]

# Flair/tag cao giá trị cho POD
HOT_FLAIRS = ["highlight", "meme", "shitpost", "humor", "game thread",
              "post game", "breaking", "news", "discussion"]


# ============================================================
# FETCH HELPERS
# ============================================================
def _fetch_json(url, timeout=30):
    """Fetch JSON from URL with error handling."""
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                       'AppleWebKit/537.36 (KHTML, like Gecko) '
                       'Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'application/json',
    })
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        return None


def _unescape(text):
    """Unescape HTML entities."""
    if not text:
        return ''
    for old, new in [('&amp;', '&'), ('&lt;', '<'), ('&gt;', '>'),
                     ('&#39;', "'"), ('&apos;', "'"), ('&quot;', '"')]:
        text = text.replace(old, new)
    return text


# ============================================================
# REDDIT VIA PULLPUSH API
# ============================================================
def fetch_reddit():
    """Lấy top posts từ Reddit qua Pullpush API (có đầy đủ engagement data)."""
    print("\n📱 Đang quét Reddit via Pullpush API...")
    all_posts = []

    for sport, subs in SUBREDDITS.items():
        for sub in subs:
            print(f"  → r/{sub} ({sport})...")
            url = (f"https://api.pullpush.io/reddit/search/submission/"
                   f"?subreddit={sub}&sort=score&sort_type=desc&size=15&score=>50")
            data = _fetch_json(url, timeout=30)

            if data and 'data' in data:
                posts = data['data']
                for p in posts:
                    title = _unescape(p.get('title', ''))
                    if not title or len(title) < 5:
                        continue

                    score = p.get('score', 0)
                    comments = p.get('num_comments', 0)
                    ratio = p.get('upvote_ratio', 0)
                    awards = p.get('total_awards_received', 0)
                    flair = p.get('link_flair_text', '') or ''
                    thumb = p.get('thumbnail', '')
                    permalink = p.get('permalink', '')
                    author = p.get('author', '')

                    # Clean thumbnail
                    if thumb in ('self', 'default', 'nsfw', 'spoiler', '', None):
                        thumb = ''

                    link = f"https://reddit.com{permalink}" if permalink else ''

                    all_posts.append({
                        'title': title,
                        'score': score,
                        'comments': comments,
                        'upvote_ratio': ratio,
                        'awards': awards,
                        'flair': flair,
                        'thumbnail': thumb,
                        'link': link,
                        'author': author,
                        'source': f"r/{sub}",
                        'sport': sport,
                        'type': 'reddit',
                    })
                print(f"    ✅ {len(posts)} posts found")
            else:
                print(f"    ⚠ No data")

            time.sleep(2)  # Rate limiting

    # Search queries
    print("\n🔍 Searching Reddit for POD keywords...")
    for query in SEARCH_QUERIES:
        q_enc = urllib.parse.quote_plus(query)
        url = (f"https://api.pullpush.io/reddit/search/submission/"
               f"?q={q_enc}&sort=score&sort_type=desc&size=10&score=>20")
        data = _fetch_json(url, timeout=30)

        if data and 'data' in data:
            for p in data['data']:
                title = _unescape(p.get('title', ''))
                if not title:
                    continue
                sub = p.get('subreddit', 'unknown')
                permalink = p.get('permalink', '')
                link = f"https://reddit.com{permalink}" if permalink else ''

                all_posts.append({
                    'title': title,
                    'score': p.get('score', 0),
                    'comments': p.get('num_comments', 0),
                    'upvote_ratio': p.get('upvote_ratio', 0),
                    'awards': p.get('total_awards_received', 0),
                    'flair': p.get('link_flair_text', '') or '',
                    'thumbnail': '',
                    'link': link,
                    'author': p.get('author', ''),
                    'source': f"r/{sub}",
                    'sport': 'Search',
                    'type': 'reddit_search',
                })
            print(f"  → '{query}': {len(data['data'])} results")
        time.sleep(2)

    # Deduplicate by title
    seen = set()
    unique = []
    for p in all_posts:
        key = p['title'].lower()[:60]
        if key not in seen:
            seen.add(key)
            unique.append(p)

    print(f"\n  📊 Tổng: {len(unique)} unique Reddit posts")
    return unique


# ============================================================
# ESPN NEWS
# ============================================================
def fetch_espn():
    """Lấy tin nóng từ ESPN API."""
    print("\n📺 Đang quét ESPN Headlines...")
    all_news = []

    for feed in ESPN_FEEDS:
        print(f"  → ESPN {feed['name']}...")
        data = _fetch_json(feed['url'], timeout=15)
        if not data:
            print(f"    ⚠ No data")
            continue

        articles = data.get('articles', [])
        for a in articles:
            title = a.get('headline', '')
            desc = a.get('description', '')
            link = a.get('links', {}).get('web', {}).get('href', '#')
            images = a.get('images', [])
            image = images[0].get('url', '') if images else ''

            all_news.append({
                'title': title,
                'description': desc,
                'link': link,
                'image': image,
                'source': f"ESPN {feed['name']}",
                'sport': feed['sport'],
                'type': 'espn',
            })
        print(f"    ✅ {len(articles)} articles")
        time.sleep(0.5)

    return all_news


# ============================================================
# GOOGLE TRENDS INTEGRATION
# ============================================================
def load_google_trends():
    """Load dữ liệu từ Google Trends JSON nếu có."""
    json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             'google_trends_data.json')
    if not os.path.exists(json_path):
        print("\n📈 Google Trends data: không tìm thấy (chạy google_trends.py trước)")
        return []

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        trends = data.get('trends', [])
        pod_trends = [t for t in trends if t.get('is_pod')]
        print(f"\n📈 Google Trends: {len(pod_trends)} POD-relevant trends loaded")
        return pod_trends
    except Exception as e:
        print(f"\n📈 Google Trends: lỗi đọc file ({e})")
        return []


# ============================================================
# POD SCORING SYSTEM
# ============================================================
def calculate_pod_score(item):
    """Tính POD potential score cho mỗi item."""
    score = 0.0
    title_lower = item.get('title', '').lower()

    # 1. Engagement score (Reddit)
    upvotes = item.get('score', 0)
    comments = item.get('comments', 0)
    awards = item.get('awards', 0)

    score += min(upvotes / 500, 10)   # Max 10 points from upvotes
    score += min(comments / 100, 5)    # Max 5 from comments
    score += min(awards * 2, 6)        # Max 6 from awards

    # 2. Viral keyword score
    viral_hits = 0
    for kw in VIRAL_KEYWORDS:
        if kw in title_lower:
            viral_hits += 1
    score += min(viral_hits * 1.5, 10)  # Max 10 from keywords

    # 3. Quote detection bonus
    if re.search(r'["\u201c\u201d].{5,60}["\u201c\u201d]', item.get('title', '')):
        score += 5  # Quoted text = likely meme-able

    # 4. ALL CAPS detection bonus
    words = item.get('title', '').split()
    caps_words = [w for w in words if w.isupper() and len(w) > 2]
    if len(caps_words) >= 3:
        score += 3  # ALL CAPS = hype/meme

    # 5. Hot flair bonus
    flair = (item.get('flair', '') or '').lower()
    for hot in HOT_FLAIRS:
        if hot in flair:
            score += 3
            break

    # 6. Explicit merch/shirt request
    merch_patterns = ['need this on a shirt', 'someone make', 'want this',
                      'shirt', 'merch', 'print this']
    for mp in merch_patterns:
        if mp in title_lower:
            score += 5
            break

    return round(score, 1)


def score_label(score):
    """Return badge class and label for a POD score."""
    if score >= 15:
        return 'fire', '🔥🔥 FIRE'
    elif score >= 8:
        return 'hot', '🔥 HOT'
    elif score >= 3:
        return 'warm', '⚡ WARM'
    else:
        return 'cold', '❄️'


# ============================================================
# GENERATE HTML DASHBOARD
# ============================================================
def generate_html(reddit_posts, espn_news, google_trends):
    now = datetime.now().strftime("%H:%M — %d/%m/%Y")

    # Calculate POD scores
    for p in reddit_posts:
        p['pod_score'] = calculate_pod_score(p)
    for n in espn_news:
        n['pod_score'] = calculate_pod_score(n)

    # Sort by POD score
    reddit_posts.sort(key=lambda x: x['pod_score'], reverse=True)
    espn_news.sort(key=lambda x: x['pod_score'], reverse=True)

    # Top POD opportunities = high-score items from all sources
    top_pod = sorted(
        [p for p in reddit_posts if p['pod_score'] >= 3],
        key=lambda x: x['pod_score'], reverse=True
    )[:30]

    # Stats
    total_items = len(reddit_posts) + len(espn_news)
    fire_count = sum(1 for p in reddit_posts + espn_news if p['pod_score'] >= 15)
    hot_count = sum(1 for p in reddit_posts + espn_news if 8 <= p['pod_score'] < 15)

    # Collect all sports for filter
    all_sports = sorted(set(p.get('sport', '') for p in reddit_posts if p.get('sport')))

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🔥 POD Trend Alert v2.0</title>
    <meta name="description" content="Multi-source social media trend scanner for Print-on-Demand research">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg: #0a0e17; --bg2: #0f1420; --card: #141b2d;
            --card-hover: #1a2338; --border: #1e2a42; --border-light: #2a3a5c;
            --text: #e2e8f0; --muted: #64748b; --dim: #475569;
            --red: #ef4444; --green: #22c55e; --orange: #f59e0b;
            --blue: #3b82f6; --purple: #a855f7; --cyan: #06b6d4;
            --fire-bg: rgba(239,68,68,0.12); --hot-bg: rgba(245,158,11,0.12);
            --warm-bg: rgba(59,130,246,0.1);
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: 'Inter', -apple-system, sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; }}

        header {{ text-align: center; padding: 2rem 1rem 1.5rem; background: linear-gradient(180deg, #12182a 0%, var(--bg) 100%); border-bottom: 1px solid var(--border); position: relative; overflow: hidden; }}
        header::before {{ content: ''; position: absolute; top: -50%; left: 50%; transform: translateX(-50%); width: 700px; height: 700px; background: radial-gradient(circle, rgba(239,68,68,0.06) 0%, transparent 70%); pointer-events: none; }}
        h1 {{ font-size: 2.2rem; font-weight: 900; letter-spacing: -0.03em; background: linear-gradient(135deg, #ef4444 0%, #f59e0b 50%, #22c55e 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }}
        .subtitle {{ color: var(--muted); font-size: 0.85rem; margin-top: 0.4rem; font-weight: 500; }}
        .stats-bar {{ display: flex; justify-content: center; gap: 1.5rem; margin-top: 1rem; flex-wrap: wrap; }}
        .stat {{ display: flex; align-items: center; gap: 0.4rem; font-size: 0.8rem; font-weight: 600; padding: 0.35rem 0.8rem; border-radius: 20px; background: var(--card); border: 1px solid var(--border); }}

        .filters {{ display: flex; justify-content: center; gap: 0.5rem; margin-top: 1rem; flex-wrap: wrap; }}
        .filter-btn {{ padding: 0.3rem 0.8rem; font-size: 0.7rem; font-weight: 600; border-radius: 16px; border: 1px solid var(--border); background: transparent; color: var(--muted); cursor: pointer; transition: all 0.2s; font-family: inherit; }}
        .filter-btn:hover, .filter-btn.active {{ background: var(--blue); color: #fff; border-color: var(--blue); }}

        .layout {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1.2rem; padding: 1.2rem; max-width: 1500px; margin: 0 auto; }}
        @media (max-width: 900px) {{ .layout {{ grid-template-columns: 1fr; }} }}

        .section {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; }}
        .section-head {{ display: flex; align-items: center; justify-content: space-between; padding: 1rem 1.2rem; border-bottom: 1px solid var(--border); }}
        .section-title {{ font-size: 1rem; font-weight: 700; display: flex; align-items: center; gap: 0.5rem; }}
        .section-badge {{ font-size: 0.65rem; font-weight: 600; padding: 2px 8px; border-radius: 10px; }}
        .section-body {{ max-height: 78vh; overflow-y: auto; }}
        .section-body::-webkit-scrollbar {{ width: 5px; }}
        .section-body::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 3px; }}

        /* Post card */
        .post {{ display: flex; gap: 0.7rem; padding: 0.8rem 1.2rem; border-bottom: 1px solid rgba(30,42,66,0.5); transition: background 0.15s; animation: fadeIn 0.3s ease-out both; }}
        .post:hover {{ background: var(--card-hover); }}
        @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(6px); }} to {{ opacity: 1; transform: translateY(0); }} }}

        .post-thumb {{ width: 48px; height: 48px; border-radius: 8px; object-fit: cover; flex-shrink: 0; background: var(--bg2); border: 1px solid var(--border); }}
        .post-body {{ flex: 1; min-width: 0; }}
        .post-top {{ display: flex; align-items: center; gap: 0.4rem; flex-wrap: wrap; margin-bottom: 0.25rem; }}
        .post-title {{ font-size: 0.8rem; font-weight: 600; color: var(--text); display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }}
        .post-title a {{ color: inherit; text-decoration: none; }} .post-title a:hover {{ color: var(--blue); }}

        .metrics {{ display: flex; gap: 0.6rem; margin-top: 0.3rem; flex-wrap: wrap; align-items: center; }}
        .metric {{ font-size: 0.65rem; color: var(--muted); font-weight: 500; }}
        .metric-val {{ font-weight: 700; color: var(--text); }}

        .badge {{ font-size: 0.55rem; font-weight: 700; padding: 2px 7px; border-radius: 6px; white-space: nowrap; }}
        .badge-fire {{ background: var(--red); color: #fff; box-shadow: 0 0 10px rgba(239,68,68,0.3); animation: pulse 2s infinite; }}
        @keyframes pulse {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.8; }} }}
        .badge-hot {{ background: var(--orange); color: #fff; }}
        .badge-warm {{ background: rgba(59,130,246,0.2); color: var(--blue); }}
        .badge-cold {{ background: rgba(100,116,139,0.15); color: var(--dim); }}
        .badge-source {{ background: rgba(100,116,139,0.15); color: var(--muted); }}
        .badge-sport {{ background: rgba(34,197,94,0.12); color: var(--green); }}
        .badge-score {{ background: rgba(168,85,247,0.15); color: var(--purple); font-weight: 800; }}

        .post-actions {{ display: flex; gap: 0.4rem; margin-top: 0.3rem; }}
        .act {{ font-size: 0.58rem; font-weight: 600; color: var(--dim); text-decoration: none; padding: 2px 6px; border-radius: 4px; border: 1px solid var(--border); transition: all 0.15s; }}
        .act:hover {{ color: var(--blue); border-color: rgba(59,130,246,0.4); background: rgba(59,130,246,0.08); }}

        /* ESPN card */
        .espn {{ display: flex; gap: 0.7rem; padding: 0.8rem 1.2rem; border-bottom: 1px solid rgba(30,42,66,0.5); }}
        .espn:hover {{ background: var(--card-hover); }}
        .espn-img {{ width: 80px; height: 55px; border-radius: 6px; object-fit: cover; flex-shrink: 0; }}
        .espn-body {{ flex: 1; }}
        .espn-title {{ font-size: 0.8rem; font-weight: 600; color: var(--text); margin-bottom: 0.2rem; }}
        .espn-title a {{ color: inherit; text-decoration: none; }} .espn-title a:hover {{ color: var(--cyan); }}
        .espn-desc {{ font-size: 0.68rem; color: var(--muted); display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }}

        /* Google Trends mini */
        .trend-chip {{ display: inline-flex; align-items: center; gap: 0.3rem; padding: 0.3rem 0.7rem; margin: 0.2rem; border-radius: 16px; background: var(--card); border: 1px solid var(--border); font-size: 0.7rem; font-weight: 600; color: var(--text); text-decoration: none; transition: all 0.15s; }}
        .trend-chip:hover {{ border-color: var(--cyan); color: var(--cyan); }}
        .trend-traffic {{ font-size: 0.6rem; color: var(--orange); font-weight: 700; }}

        .empty {{ padding: 2rem; text-align: center; color: var(--muted); font-size: 0.85rem; }}
        footer {{ text-align: center; padding: 1.5rem; color: var(--dim); font-size: 0.7rem; border-top: 1px solid var(--border); }}
        footer a {{ color: var(--blue); text-decoration: none; }}
    </style>
    <script>
    function openSearch(url, evt) {{
        if (evt) evt.preventDefault();
        var w = window.open('about:blank', '_blank');
        if (w) {{ w.location.href = url; }} else {{ window.location.href = url; }}
        return false;
    }}
    function filterSport(sport) {{
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        event.target.classList.add('active');
        document.querySelectorAll('.post[data-sport]').forEach(p => {{
            p.style.display = (!sport || p.dataset.sport === sport) ? '' : 'none';
        }});
    }}
    </script>
</head>
<body>
    <header>
        <h1>🔥 POD Trend Alert v2.0</h1>
        <p class="subtitle">Multi-source viral sports scanner — Reddit + ESPN + Google Trends</p>
        <div class="stats-bar">
            <div class="stat" style="color:var(--red)">📊 {total_items} items scanned</div>
            <div class="stat" style="color:var(--orange)">🔥 {fire_count} FIRE + {hot_count} HOT</div>
            <div class="stat" style="color:var(--blue)">🕐 {now}</div>
        </div>
        <div class="filters">
            <button class="filter-btn active" onclick="filterSport('')">All</button>
"""

    for sport in all_sports:
        html += f'            <button class="filter-btn" onclick="filterSport(\'{sport}\')">{sport}</button>\n'

    html += """
        </div>
    </header>

    <div class="layout">
"""

    # ── COLUMN 1: Top POD Opportunities ──
    html += f"""
        <div class="section">
            <div class="section-head">
                <div class="section-title" style="color:var(--red)">🏆 Top POD Opportunities</div>
                <span class="section-badge" style="background:var(--fire-bg);color:var(--red)">{len(top_pod)} found</span>
            </div>
            <div class="section-body">
"""

    if top_pod:
        for i, p in enumerate(top_pod):
            html += _render_reddit_card(i, p)
    else:
        html += '<div class="empty">Không tìm thấy cơ hội POD nổi bật.</div>'

    html += """
            </div>
        </div>
"""

    # ── COLUMN 2: ESPN News + Google Trends ──
    html += f"""
        <div class="section">
            <div class="section-head">
                <div class="section-title" style="color:var(--cyan)">📺 ESPN + 📈 Google Trends</div>
                <span class="section-badge" style="background:var(--warm-bg);color:var(--blue)">{len(espn_news)} articles</span>
            </div>
            <div class="section-body">
"""

    # Google Trends chips
    if google_trends:
        html += '<div style="padding:0.8rem 1.2rem;border-bottom:1px solid var(--border)">'
        html += '<div style="font-size:0.75rem;font-weight:700;color:var(--cyan);margin-bottom:0.5rem">📈 Google Trends — POD Keywords</div>'
        for t in google_trends[:10]:
            q = t.get('query', '')
            traffic = t.get('traffic', '')
            q_enc = urllib.parse.quote_plus(q)
            html += f'<a class="trend-chip" href="https://www.google.com/search?q={q_enc}+t+shirt&amp;tbm=isch" onclick="return openSearch(this.href, event)">{q} <span class="trend-traffic">{traffic}</span></a>'
        html += '</div>'

    # ESPN articles
    for n in espn_news:
        lbl, txt = score_label(n['pod_score'])
        img_html = f'<img class="espn-img" src="{n["image"]}" loading="lazy" onerror="this.style.display=\'none\'">' if n.get('image') else ''
        q_enc = urllib.parse.quote_plus(n['title'])

        html += f"""
                <div class="espn">
                    {img_html}
                    <div class="espn-body">
                        <div class="post-top">
                            <span class="badge badge-source">{n['source']}</span>
                            <span class="badge badge-{lbl}">{txt}</span>
                            <span class="badge badge-score">POD {n['pod_score']}</span>
                        </div>
                        <div class="espn-title"><a href="{n['link']}" target="_blank" rel="noopener">{n['title']}</a></div>
                        <div class="espn-desc">{n.get('description', '')[:120]}</div>
                        <div class="post-actions" style="margin-top:0.3rem">
                            <a class="act" href="https://www.google.com/search?q={q_enc}+t+shirt&amp;tbm=isch" onclick="return openSearch(this.href, event)">👕 POD Search</a>
                        </div>
                    </div>
                </div>"""

    if not espn_news:
        html += '<div class="empty">Không có dữ liệu ESPN.</div>'

    html += """
            </div>
        </div>
    </div>
"""

    html += f"""
    <footer>
        Data: <a href="https://reddit.com" target="_blank">Reddit</a> via Pullpush API +
        <a href="https://espn.com" target="_blank">ESPN</a> +
        <a href="https://trends.google.com" target="_blank">Google Trends</a>
        — Scan lúc {now}
    </footer>
</body>
</html>"""

    output_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'trend_alert.html')
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    return output_file


def _render_reddit_card(index, p):
    """Render 1 Reddit post card."""
    lbl, txt = score_label(p['pod_score'])
    q_enc = urllib.parse.quote_plus(p['title'][:80])

    thumb = ''
    if p.get('thumbnail') and p['thumbnail'].startswith('http'):
        thumb = f'<img class="post-thumb" src="{p["thumbnail"]}" loading="lazy" onerror="this.style.display=\'none\'">'

    flair_badge = f'<span class="badge badge-source">[{p["flair"]}]</span>' if p.get('flair') else ''

    score_k = f"{p['score']/1000:.1f}K" if p['score'] >= 1000 else str(p['score'])
    comments_k = f"{p['comments']/1000:.1f}K" if p['comments'] >= 1000 else str(p['comments'])
    ratio_pct = f"{int(p.get('upvote_ratio', 0) * 100)}%" if p.get('upvote_ratio') else ''

    delay = index * 0.03

    return f"""
                <div class="post" data-sport="{p.get('sport','')}" style="animation-delay:{delay:.2f}s">
                    {thumb}
                    <div class="post-body">
                        <div class="post-top">
                            <span class="badge badge-{lbl}">{txt}</span>
                            <span class="badge badge-score">POD {p['pod_score']}</span>
                            <span class="badge badge-sport">{p.get('sport','')}</span>
                            {flair_badge}
                        </div>
                        <div class="post-title"><a href="{p['link']}" target="_blank" rel="noopener">{p['title']}</a></div>
                        <div class="metrics">
                            <span class="metric">⬆ <span class="metric-val">{score_k}</span></span>
                            <span class="metric">💬 <span class="metric-val">{comments_k}</span></span>
                            <span class="metric">📊 <span class="metric-val">{ratio_pct}</span></span>
                            <span class="metric">🏅 <span class="metric-val">{p.get('awards',0)}</span></span>
                            <span class="badge badge-source">{p['source']}</span>
                        </div>
                        <div class="post-actions">
                            <a class="act" href="https://www.google.com/search?q={q_enc}+t+shirt&amp;tbm=isch" onclick="return openSearch(this.href, event)">👕 POD</a>
                            <a class="act" href="https://www.google.com/search?q={q_enc}&amp;tbm=isch" onclick="return openSearch(this.href, event)">🖼 Images</a>
                            <a class="act" href="{p['link']}" target="_blank" rel="noopener">📱 Reddit</a>
                        </div>
                    </div>
                </div>"""


# ============================================================
# EXPORT JSON
# ============================================================
def export_json(reddit_posts, espn_news, google_trends):
    """Lưu dữ liệu ra JSON."""
    output_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               'trend_alert_data.json')
    data = {
        'generated_at': datetime.now().isoformat(),
        'reddit_posts': len(reddit_posts),
        'espn_news': len(espn_news),
        'google_trends': len(google_trends),
        'top_pod': sorted(
            [p for p in reddit_posts if p.get('pod_score', 0) >= 3],
            key=lambda x: x.get('pod_score', 0), reverse=True
        )[:30],
        'all_reddit': reddit_posts,
        'all_espn': espn_news,
    }
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  💾 Đã lưu JSON: {output_file}")


# ============================================================
# MAIN
# ============================================================
def main():
    print("=" * 58)
    print("  🔥 POD TREND ALERT v2.0 — Multi-Source Scanner")
    print("  📱 Reddit + 📺 ESPN + 📈 Google Trends")
    print("=" * 58)

    # Fetch data
    reddit_posts = fetch_reddit()
    espn_news = fetch_espn()
    google_trends = load_google_trends()

    # Calculate POD scores
    for p in reddit_posts:
        p['pod_score'] = calculate_pod_score(p)

    # Stats
    fire = [p for p in reddit_posts if p['pod_score'] >= 15]
    hot = [p for p in reddit_posts if 8 <= p['pod_score'] < 15]
    warm = [p for p in reddit_posts if 3 <= p['pod_score'] < 8]

    print(f"\n📊 Tổng kết:")
    print(f"  📱 Reddit: {len(reddit_posts)} posts")
    print(f"  📺 ESPN:   {len(espn_news)} articles")
    print(f"  📈 Trends: {len(google_trends)} POD keywords")
    print(f"\n🎯 POD Potential:")
    print(f"  🔥🔥 FIRE: {len(fire)} posts")
    print(f"  🔥 HOT:  {len(hot)} posts")
    print(f"  ⚡ WARM: {len(warm)} posts")

    if fire:
        print(f"\n🏆 Top FIRE opportunities:")
        for p in fire[:5]:
            print(f"  → [{p['pod_score']}] {p['title'][:65]}")
            print(f"    ⬆{p['score']:,} 💬{p['comments']:,} | {p['source']}")

    # Export
    export_json(reddit_posts, espn_news, google_trends)

    # Generate HTML
    output = generate_html(reddit_posts, espn_news, google_trends)
    print(f"\n✅ Trend Alert Dashboard đã tạo xong!")
    print(f"   Mở file: {output}")
    if not os.environ.get('CI'):
        webbrowser.open(f"file://{output}")


if __name__ == '__main__':
    main()
