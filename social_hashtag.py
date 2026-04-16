import os
import re
import json
import time
import urllib.request
import urllib.parse
import webbrowser
from datetime import datetime

# ============================================================
# CẤU HÌNH HASHTAGS & TEAMS
# ============================================================

# Hashtags chính để research
CORE_HASHTAGS = [
    "#shirt", "#tshirt", "#tee", "#fanshirt", "#shirtforfan",
    "#shirtformom", "#shirtfordad", "#gameday", "#gamedayshirt",
    "#sportshirt", "#fanmerch", "#sportsfan",
]

# Hashtags theo league
LEAGUE_HASHTAGS = {
    "MLB": {
        "league": ["#mlb", "#baseball", "#baseballseason", "#mlbplayoffs"],
        "teams": {
            "Dodgers": ["#dodgers", "#ladodgers", "#losdodgers"],
            "Yankees": ["#yankees", "#nyy", "#newyorkyankees"],
            "Mets": ["#mets", "#lgm", "#letsgomets"],
            "Astros": ["#astros", "#houstonastros"],
            "Braves": ["#braves", "#atlantabraves", "#chophouse"],
            "Cubs": ["#cubs", "#chicagocubs", "#cubswin"],
            "Red Sox": ["#redsox", "#bostonredsox"],
            "Phillies": ["#phillies", "#ringthebell"],
            "Padres": ["#padres", "#sandiegopadres"],
            "Rangers": ["#texasrangers", "#rangers"],
            "Blue Jays": ["#bluejays", "#torontobluejays"],
            "Orioles": ["#orioles", "#birdland"],
            "Guardians": ["#guardians", "#clevelandguardians"],
        }
    },
    "NFL": {
        "league": ["#nfl", "#football", "#nflseason", "#nflplayoffs"],
        "teams": {
            "Chiefs": ["#chiefs", "#chiefskingdom", "#kcchiefs"],
            "Eagles": ["#eagles", "#flyeaglesfly", "#philadelphiaeagles"],
            "Cowboys": ["#cowboys", "#dallascowboys", "#americasteam"],
            "49ers": ["#49ers", "#sf49ers", "#niners", "#faithfulnation"],
            "Bills": ["#bills", "#buffalobills", "#billsmafia"],
            "Ravens": ["#ravens", "#baltimoreravens", "#flocknation"],
            "Lions": ["#lions", "#detroitlions", "#onepride"],
            "Packers": ["#packers", "#greenbaypackers", "#gopackgo"],
            "Bengals": ["#bengals", "#cincinnatibengals", "#whodey"],
            "Bears": ["#bears", "#chicagobears", "#dabears"],
            "Dolphins": ["#dolphins", "#miamidolphins", "#finsup"],
            "Patriots": ["#patriots", "#newenglandpatriots"],
        }
    },
    "NBA": {
        "league": ["#nba", "#basketball", "#nbaplayoffs", "#nbaseason"],
        "teams": {
            "Lakers": ["#lakers", "#lalakers", "#lakernation", "#lakeshow"],
            "Celtics": ["#celtics", "#bostonceltics", "#bleedgreen"],
            "Warriors": ["#warriors", "#dubsnation", "#gsw"],
            "Knicks": ["#knicks", "#nyknicks", "#newyorkknicks"],
            "Heat": ["#heat", "#miamiheat", "#heatnation"],
            "Nuggets": ["#nuggets", "#denvernuggets", "#milehighbasketball"],
            "Thunder": ["#thunder", "#okcthunder", "#thunderup"],
            "Bucks": ["#bucks", "#milwaukeebucks", "#fearthedeer"],
            "Cavaliers": ["#cavs", "#cavaliers", "#clevelandcavaliers"],
            "Clippers": ["#clippers", "#laclippers"],
            "Suns": ["#suns", "#phoenixsuns", "#valleyofthesun"],
            "76ers": ["#sixers", "#76ers", "#trusttheprocess"],
        }
    },
    "NHL": {
        "league": ["#nhl", "#hockey", "#nhlplayoffs", "#stanleycup"],
        "teams": {
            "Rangers": ["#nyr", "#nyrangers", "#blueshirts"],
            "Bruins": ["#bruins", "#bostonbruins", "#nhlbruins"],
            "Maple Leafs": ["#leafs", "#leafsnation", "#torontomapleleafs"],
            "Oilers": ["#oilers", "#edmontonoilers", "#letsgooilers"],
            "Lightning": ["#lightning", "#gobolts", "#tblightning"],
            "Panthers": ["#flapanthers", "#floridapanthers"],
            "Avalanche": ["#avs", "#goavsgo", "#coloradoavalanche"],
            "Blackhawks": ["#blackhawks", "#chicagoblackhawks"],
            "Penguins": ["#penguins", "#letsgopens"],
            "Golden Knights": ["#vegasgoldenknights", "#vgk", "#goknightsgo"],
        }
    },
}

# Google Suggest — lấy keyword gợi ý miễn phí
def fetch_google_suggest(query, limit=8):
    """Lấy keyword suggestions từ Google Autocomplete (free, no API)."""
    q_enc = urllib.parse.quote_plus(query)
    url = f"https://suggestqueries.google.com/complete/search?client=firefox&q={q_enc}"
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
    })
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read().decode('utf-8'))
        return data[1][:limit] if len(data) > 1 else []
    except:
        return []


def fetch_keyword_ideas():
    """Tìm keyword ideas từ Google Suggest cho mỗi league + shirt."""
    print("\n💡 Đang tìm keyword ideas via Google Suggest...")
    ideas = {}

    queries = [
        ("General", "fan shirt trending 2026"),
        ("General", "sports t-shirt viral"),
        ("NFL", "nfl fan shirt"),
        ("NBA", "nba fan shirt"),
        ("MLB", "mlb fan shirt"),
        ("NHL", "hockey fan shirt"),
    ]

    # Add top teams
    for league, data in LEAGUE_HASHTAGS.items():
        for team in list(data["teams"].keys())[:3]:
            queries.append((league, f"{team} shirt fan"))

    for category, query in queries:
        suggestions = fetch_google_suggest(query)
        if suggestions:
            if category not in ideas:
                ideas[category] = []
            ideas[category].extend(suggestions)
            print(f"  → {query}: {len(suggestions)} suggestions")
        time.sleep(0.5)  # Rate limit

    # Deduplicate per category
    for cat in ideas:
        ideas[cat] = list(dict.fromkeys(ideas[cat]))

    return ideas


def load_existing_trends():
    """Load data from google_trends and trend_alert if available."""
    trends = []

    # Google Trends data
    gt_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           'google_trends_data.json')
    if os.path.exists(gt_path):
        try:
            with open(gt_path, 'r') as f:
                data = json.load(f)
            pod = [t for t in data.get('trends', []) if t.get('is_pod')]
            trends.extend([{'query': t['query'], 'traffic': t.get('traffic', ''),
                           'source': 'Google Trends'} for t in pod])
        except:
            pass

    # Trend Alert data
    ta_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           'trend_alert_data.json')
    if os.path.exists(ta_path):
        try:
            with open(ta_path, 'r') as f:
                data = json.load(f)
            top = data.get('top_pod', [])[:10]
            trends.extend([{'query': t['title'][:60], 'traffic': f"⬆{t.get('score',0)}",
                           'source': f"Reddit {t.get('source','')}"} for t in top])
        except:
            pass

    return trends


# ============================================================
# BUILD SEARCH URLS
# ============================================================
def build_search_url(platform, hashtags, extra=""):
    """Build search URL cho X hoặc Instagram."""
    if platform == "x":
        # X/Twitter search
        query = " ".join(hashtags)
        if extra:
            query += " " + extra
        return f"https://x.com/search?q={urllib.parse.quote_plus(query)}&src=typed_query&f=live"
    elif platform == "instagram":
        # Instagram hashtag explore (chỉ dùng 1 hashtag chính)
        tag = hashtags[0].replace("#", "").replace(" ", "")
        return f"https://www.instagram.com/explore/tags/{tag}/"
    elif platform == "google_images":
        query = " ".join([h.replace("#", "") for h in hashtags])
        if extra:
            query += " " + extra
        return f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}&tbm=isch"
    elif platform == "google_shopping":
        query = " ".join([h.replace("#", "") for h in hashtags])
        if extra:
            query += " " + extra
        return f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}&tbm=shop"
    return "#"


# ============================================================
# GENERATE DASHBOARD HTML
# ============================================================
def generate_html(keyword_ideas, existing_trends):
    now = datetime.now().strftime("%H:%M — %d/%m/%Y")

    # Count total hashtag combos
    total_combos = 0
    for league, data in LEAGUE_HASHTAGS.items():
        total_combos += len(data["teams"]) * len(CORE_HASHTAGS)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🔎 Social Hashtag Research — X & Instagram</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg: #0a0e17; --bg2: #0f1420; --card: #141b2d;
            --card-hover: #1a2338; --border: #1e2a42;
            --text: #e2e8f0; --muted: #64748b; --dim: #475569;
            --red: #ef4444; --green: #22c55e; --orange: #f59e0b;
            --blue: #3b82f6; --purple: #a855f7; --cyan: #06b6d4;
            --pink: #ec4899; --x-blue: #1d9bf0; --ig-pink: #E4405F;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; }}

        header {{ text-align: center; padding: 2rem 1rem 1.5rem; background: linear-gradient(180deg, #12182a 0%, var(--bg) 100%); border-bottom: 1px solid var(--border); }}
        h1 {{ font-size: 2rem; font-weight: 900; background: linear-gradient(135deg, #1d9bf0 0%, #E4405F 50%, #a855f7 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
        .subtitle {{ color: var(--muted); font-size: 0.85rem; margin-top: 0.4rem; }}
        .stats {{ display: flex; justify-content: center; gap: 1.5rem; margin-top: 1rem; flex-wrap: wrap; }}
        .stat {{ font-size: 0.8rem; font-weight: 600; padding: 0.35rem 0.8rem; border-radius: 20px; background: var(--card); border: 1px solid var(--border); }}
        .tip {{ background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 1rem 1.5rem; margin: 1.2rem auto; max-width: 1000px; font-size: 0.78rem; color: var(--orange); line-height: 1.7; }}

        .tabs {{ display: flex; justify-content: center; gap: 0.5rem; margin: 1rem auto; flex-wrap: wrap; max-width: 900px; }}
        .tab {{ padding: 0.4rem 1rem; font-size: 0.75rem; font-weight: 700; border-radius: 20px; border: 1px solid var(--border); background: transparent; color: var(--muted); cursor: pointer; transition: all 0.2s; font-family: inherit; }}
        .tab:hover, .tab.active {{ background: var(--blue); color: #fff; border-color: var(--blue); }}
        .tab[data-league="MLB"].active {{ background: #c41e3a; border-color: #c41e3a; }}
        .tab[data-league="NFL"].active {{ background: #013369; border-color: #013369; }}
        .tab[data-league="NBA"].active {{ background: #c8102e; border-color: #c8102e; }}
        .tab[data-league="NHL"].active {{ background: #000; border-color: #333; }}

        .main {{ max-width: 1400px; margin: 0 auto; padding: 0 1.2rem 2rem; }}

        .league-section {{ display: none; }}
        .league-section.active {{ display: block; }}

        .team-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 1rem; margin-top: 1rem; }}

        .team-card {{ background: var(--card); border: 1px solid var(--border); border-radius: 10px; overflow: hidden; transition: border-color 0.2s; }}
        .team-card:hover {{ border-color: var(--blue); }}
        .team-head {{ display: flex; align-items: center; justify-content: space-between; padding: 0.8rem 1rem; border-bottom: 1px solid var(--border); }}
        .team-name {{ font-size: 0.9rem; font-weight: 700; }}
        .team-league {{ font-size: 0.6rem; font-weight: 600; padding: 2px 7px; border-radius: 10px; }}

        .team-body {{ padding: 0.7rem 1rem; }}
        .hashtag-row {{ display: flex; flex-wrap: wrap; gap: 0.3rem; margin-bottom: 0.5rem; }}
        .hashtag {{ font-size: 0.65rem; font-weight: 600; padding: 3px 8px; border-radius: 12px; background: rgba(59,130,246,0.1); color: var(--blue); border: 1px solid rgba(59,130,246,0.2); }}

        .search-links {{ display: flex; flex-wrap: wrap; gap: 0.4rem; margin-top: 0.5rem; }}
        .search-btn {{ display: inline-flex; align-items: center; gap: 0.3rem; font-size: 0.65rem; font-weight: 600; padding: 5px 10px; border-radius: 8px; text-decoration: none; transition: all 0.2s; border: 1px solid var(--border); }}
        .search-btn:hover {{ transform: translateY(-1px); }}
        .btn-x {{ color: var(--x-blue); }} .btn-x:hover {{ background: rgba(29,155,240,0.1); border-color: var(--x-blue); }}
        .btn-ig {{ color: var(--ig-pink); }} .btn-ig:hover {{ background: rgba(228,64,95,0.1); border-color: var(--ig-pink); }}
        .btn-google {{ color: var(--green); }} .btn-google:hover {{ background: rgba(34,197,94,0.1); border-color: var(--green); }}
        .btn-shop {{ color: var(--orange); }} .btn-shop:hover {{ background: rgba(245,158,11,0.1); border-color: var(--orange); }}

        /* Keyword Ideas section */
        .ideas-section {{ margin-top: 1.5rem; }}
        .idea-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1rem; margin-top: 0.8rem; }}
        .idea-card {{ background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 1rem; }}
        .idea-title {{ font-size: 0.85rem; font-weight: 700; margin-bottom: 0.6rem; color: var(--purple); }}
        .idea-chip {{ display: inline-block; font-size: 0.68rem; font-weight: 500; padding: 4px 10px; margin: 0.15rem; border-radius: 14px; background: var(--bg2); border: 1px solid var(--border); color: var(--text); text-decoration: none; transition: all 0.15s; cursor: pointer; }}
        .idea-chip:hover {{ border-color: var(--cyan); color: var(--cyan); }}

        /* Existing trends */
        .trend-bar {{ display: flex; flex-wrap: wrap; gap: 0.4rem; padding: 1rem 1.2rem; border-bottom: 1px solid var(--border); }}
        .trend-tag {{ font-size: 0.7rem; font-weight: 600; padding: 4px 10px; border-radius: 14px; background: var(--card); border: 1px solid var(--border); color: var(--text); text-decoration: none; transition: 0.15s; }}
        .trend-tag:hover {{ border-color: var(--green); color: var(--green); }}
        .trend-src {{ font-size: 0.55rem; color: var(--dim); }}

        .section-title {{ font-size: 1.1rem; font-weight: 800; padding: 1rem 0 0.5rem; display: flex; align-items: center; gap: 0.5rem; }}

        footer {{ text-align: center; padding: 1.5rem; color: var(--dim); font-size: 0.7rem; border-top: 1px solid var(--border); }}
        footer a {{ color: var(--blue); text-decoration: none; }}
    </style>
    <script>
    function switchLeague(league) {{
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        event.target.classList.add('active');
        document.querySelectorAll('.league-section').forEach(s => {{
            s.classList.toggle('active', s.dataset.league === league || league === 'all');
        }});
    }}
    function openSearch(url, evt) {{
        if (evt) evt.preventDefault();
        var w = window.open('about:blank', '_blank');
        if (w) {{ w.location.href = url; }} else {{ window.location.href = url; }}
        return false;
    }}
    </script>
</head>
<body>
    <header>
        <h1>🔎 Social Hashtag Research</h1>
        <p class="subtitle">X (Twitter) + Instagram + Google — Hashtag POD Research Tool</p>
        <div class="stats">
            <div class="stat" style="color:var(--x-blue)">𝕏 X/Twitter Search</div>
            <div class="stat" style="color:var(--ig-pink)">📸 Instagram Explore</div>
            <div class="stat" style="color:var(--green)">🔍 Google Images</div>
            <div class="stat" style="color:var(--muted)">🕐 {now}</div>
        </div>
    </header>

    <div class="tip">
        💡 <strong>Cách dùng:</strong> Chọn league → Click nút <strong>𝕏 X Search</strong> hoặc <strong>📸 IG</strong> để mở trang search trực tiếp trên nền tảng.
        Tìm bài có <strong>nhiều like/RT/share</strong>, <strong>meme viral</strong>, <strong>câu nói trending</strong>, hoặc <strong>ảnh fan mặc áo</strong>.
        Click <strong>🛍 Shop</strong> để xem đối thủ đang bán gì trên Google Shopping!
    </div>
"""

    # Existing trends bar
    if existing_trends:
        html += '<div style="max-width:1400px;margin:0 auto;padding:0 1.2rem">'
        html += '<div class="section-title" style="color:var(--green)">📈 Trending Now (từ Google Trends + Reddit)</div>'
        html += '<div class="trend-bar">'
        for t in existing_trends[:15]:
            q_enc = urllib.parse.quote_plus(t['query'])
            x_url = f"https://x.com/search?q={q_enc}&src=typed_query&f=live"
            html += f'<a class="trend-tag" href="{x_url}" onclick="return openSearch(this.href, event)">{t["query"]} <span class="trend-src">{t.get("traffic","")} · {t.get("source","")}</span></a>'
        html += '</div></div>'

    # League tabs
    html += """
    <div class="tabs">
        <button class="tab active" onclick="switchLeague('all')">🌐 All</button>
"""
    league_icons = {"MLB": "⚾", "NFL": "🏈", "NBA": "🏀", "NHL": "🏒"}
    for league in LEAGUE_HASHTAGS:
        icon = league_icons.get(league, "🏆")
        html += f'        <button class="tab" data-league="{league}" onclick="switchLeague(\'{league}\')">{icon} {league}</button>\n'

    html += '    </div>\n    <div class="main">\n'

    # Generate team cards per league
    for league, data in LEAGUE_HASHTAGS.items():
        league_tags = data["league"]
        html += f'<div class="league-section active" data-league="{league}">\n'
        html += f'<div class="section-title">{league_icons.get(league,"")} {league} Teams</div>\n'
        html += '<div class="team-grid">\n'

        for team, tags in data["teams"].items():
            # Build search URLs - combine team hashtags with core shirt hashtags
            all_tags = tags + [league_tags[0]]  # team tags + league tag
            shirt_combo = tags[:1] + ["#shirt", "#fanshirt"]

            x_search = build_search_url("x", shirt_combo)
            x_meme = build_search_url("x", tags[:1] + ["#meme"], "viral")
            ig_url = build_search_url("instagram", tags)
            google_img = build_search_url("google_images", tags[:1] + ["fan shirt"], "2026")
            google_shop = build_search_url("google_shopping", [team, "fan shirt"])

            # League badge color
            badge_colors = {"MLB": "#c41e3a", "NFL": "#013369", "NBA": "#c8102e", "NHL": "#333"}
            badge_color = badge_colors.get(league, "#333")

            html += f"""
                <div class="team-card">
                    <div class="team-head">
                        <span class="team-name">{team}</span>
                        <span class="team-league" style="background:{badge_color};color:#fff">{league}</span>
                    </div>
                    <div class="team-body">
                        <div class="hashtag-row">
"""
            for tag in tags:
                html += f'                            <span class="hashtag">{tag}</span>\n'
            html += """                        </div>
                        <div class="search-links">
"""
            html += f'                            <a class="search-btn btn-x" href="{x_search}" onclick="return openSearch(this.href, event)">𝕏 Shirts</a>\n'
            html += f'                            <a class="search-btn btn-x" href="{x_meme}" onclick="return openSearch(this.href, event)">𝕏 Memes</a>\n'
            html += f'                            <a class="search-btn btn-ig" href="{ig_url}" onclick="return openSearch(this.href, event)">📸 IG</a>\n'
            html += f'                            <a class="search-btn btn-google" href="{google_img}" onclick="return openSearch(this.href, event)">🖼 Images</a>\n'
            html += f'                            <a class="search-btn btn-shop" href="{google_shop}" onclick="return openSearch(this.href, event)">🛍 Shop</a>\n'
            html += """                        </div>
                    </div>
                </div>
"""
        html += '</div></div>\n'

    # Keyword Ideas section
    if keyword_ideas:
        html += '<div class="ideas-section">\n'
        html += '<div class="section-title" style="color:var(--purple)">💡 Keyword Ideas (Google Suggest)</div>\n'
        html += '<div class="idea-grid">\n'

        for category, ideas in keyword_ideas.items():
            if not ideas:
                continue
            html += f'<div class="idea-card"><div class="idea-title">{category}</div>'
            for idea in ideas[:12]:
                q_enc = urllib.parse.quote_plus(idea + " t shirt")
                url = f"https://www.google.com/search?q={q_enc}&amp;tbm=isch"
                html += f'<a class="idea-chip" href="{url}" onclick="return openSearch(this.href, event)">{idea}</a>'
            html += '</div>\n'

        html += '</div></div>\n'

    # Core hashtags quick search
    html += """
        <div class="ideas-section">
            <div class="section-title" style="color:var(--cyan)">🏷️ Core Hashtags — Quick Search</div>
            <div class="hashtag-row" style="padding:0.5rem 0">
"""
    for tag in CORE_HASHTAGS:
        tag_clean = tag.replace("#", "")
        x_url = f"https://x.com/search?q=%23{tag_clean}&src=typed_query&f=live"
        ig_url = f"https://www.instagram.com/explore/tags/{tag_clean}/"
        html += f"""
                <div style="display:inline-flex;gap:0.2rem;margin:0.2rem">
                    <span class="hashtag">{tag}</span>
                    <a class="search-btn btn-x" style="font-size:0.6rem;padding:2px 6px" href="{x_url}" onclick="return openSearch(this.href, event)">𝕏</a>
                    <a class="search-btn btn-ig" style="font-size:0.6rem;padding:2px 6px" href="{ig_url}" onclick="return openSearch(this.href, event)">IG</a>
                </div>"""

    html += f"""
            </div>
        </div>
    </div>
    <footer>
        Research tool for POD hashtag analysis on X and Instagram — Scan lúc {now}
    </footer>
</body>
</html>"""

    output_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               'social_hashtag.html')
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    return output_file


# ============================================================
# MAIN
# ============================================================
def main():
    print("=" * 58)
    print("  🔎 SOCIAL HASHTAG RESEARCH — X & Instagram")
    print("  🏷️ POD Fan Shirt Hashtag Scanner")
    print("=" * 58)

    # Fetch keyword ideas from Google Suggest
    keyword_ideas = fetch_keyword_ideas()

    # Load existing trend data
    existing_trends = load_existing_trends()

    # Stats
    total_teams = sum(len(d["teams"]) for d in LEAGUE_HASHTAGS.values())
    total_tags = sum(sum(len(tags) for tags in d["teams"].values()) for d in LEAGUE_HASHTAGS.values())

    print(f"\n📊 Tổng kết:")
    print(f"  🏆 {len(LEAGUE_HASHTAGS)} leagues, {total_teams} teams")
    print(f"  🏷️ {total_tags} team hashtags + {len(CORE_HASHTAGS)} core hashtags")
    print(f"  💡 {sum(len(v) for v in keyword_ideas.values())} keyword ideas")
    print(f"  📈 {len(existing_trends)} existing trends loaded")

    # Generate dashboard
    output = generate_html(keyword_ideas, existing_trends)
    print(f"\n✅ Social Hashtag Dashboard đã tạo xong!")
    print(f"   Mở file: {output}")
    if not os.environ.get('CI'):
        webbrowser.open(f"file://{output}")


if __name__ == '__main__':
    main()
