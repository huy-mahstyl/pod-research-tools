"""
idea_generator.py — POD Idea Generator
Tổng hợp Google Trends + Reddit + Etsy → Sinh design brief + Gemini prompt sẵn sàng dùng.
"""
import os
import re
import sys
import json
import time
import urllib.request
import urllib.parse
import webbrowser
from datetime import datetime, date, timedelta

# ========================================
#  HISTORY CONFIG
# ========================================
HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ideas_history.json')
COOLDOWN_DAYS = 7   # Keyword không xuất hiện lại trong 7 ngày


def load_history():
    """Đọc file lịch sử ideas."""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {'keyword_last_seen': {}, 'runs': []}


def save_history(history, shown_keywords):
    """Lưu keywords vừa hiển thị vào lịch sử."""
    today = date.today().isoformat()
    kls = history.setdefault('keyword_last_seen', {})
    for kw in shown_keywords:
        kls[kw.lower().strip()] = today
    # Ghi log từng lần chạy
    history.setdefault('runs', []).append({
        'date': today,
        'time': datetime.now().strftime('%H:%M:%S'),
        'keywords': list(shown_keywords),
    })
    # Chỉ giữ 30 lần chạy gần nhất
    history['runs'] = history['runs'][-30:]
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    print(f"  💾 Đã lưu lịch sử: {len(shown_keywords)} keywords → ideas_history.json")


def is_fresh(keyword, history, cooldown=COOLDOWN_DAYS):
    """True nếu keyword chưa xuất hiện trong N ngày gần nhất."""
    kw = keyword.lower().strip()
    last_seen_str = history.get('keyword_last_seen', {}).get(kw)
    if not last_seen_str:
        return True  # Chưa từng xuất hiện → mới hoàn toàn
    try:
        last_date = date.fromisoformat(last_seen_str)
        return (date.today() - last_date).days >= cooldown
    except Exception:
        return True


def reset_history():
    """Xóa toàn bộ lịch sử (dùng khi chạy với --reset)."""
    if os.path.exists(HISTORY_FILE):
        os.remove(HISTORY_FILE)
    print('  🗑  Đã xóa lịch sử ideas. Lần chạy này sẽ hiển thị tất cả.')

# ========================================
#  DATABASE ĐỘI BÓNG MỸ
# ========================================
TEAMS_DB = {
    # ── NBA ──
    "lakers":      {"city": "Los Angeles", "colors": ["purple", "gold"],           "sport": "NBA",  "slogan": "Showtime",        "mascot": "lake waves and palm trees"},
    "celtics":     {"city": "Boston",      "colors": ["green", "white"],            "sport": "NBA",  "slogan": "Lucky #17",       "mascot": "lucky shamrock with basketball"},
    "warriors":    {"city": "Golden State","colors": ["royal blue", "gold"],        "sport": "NBA",  "slogan": "Strength In Numbers","mascot": "warrior with basketball"},
    "bulls":       {"city": "Chicago",     "colors": ["red", "black"],              "sport": "NBA",  "slogan": "Chi-Town Faithful","mascot": "charging bull"},
    "heat":        {"city": "Miami",       "colors": ["red", "black", "gold"],      "sport": "NBA",  "slogan": "Heat Nation",     "mascot": "flaming basketball"},
    "knicks":      {"city": "New York",    "colors": ["blue", "orange"],            "sport": "NBA",  "slogan": "New York New York","mascot": "NYC skyline silhouette"},
    "nuggets":     {"city": "Denver",      "colors": ["navy", "gold"],             "sport": "NBA",  "slogan": "Mile High",        "mascot": "mountain with basketball"},
    "thunder":     {"city": "Oklahoma City","colors": ["blue", "orange"],           "sport": "NBA",  "slogan": "Thunder Up",       "mascot": "lightning bolt with basketball"},
    "bucks":       {"city": "Milwaukee",   "colors": ["green", "cream"],            "sport": "NBA",  "slogan": "Fear The Deer",   "mascot": "deer with antlers"},
    "cavaliers":   {"city": "Cleveland",   "colors": ["wine", "gold"],             "sport": "NBA",  "slogan": "Believe In Cleveland","mascot": "sword and shield"},
    "suns":        {"city": "Phoenix",     "colors": ["purple", "orange"],          "sport": "NBA",  "slogan": "Valley",           "mascot": "sun rising over desert"},
    "76ers":       {"city": "Philadelphia","colors": ["red", "blue"],              "sport": "NBA",  "slogan": "Trust The Process","mascot": "liberty bell with basketball"},
    # ── NFL ──
    "chiefs":      {"city": "Kansas City", "colors": ["red", "gold"],              "sport": "NFL",  "slogan": "Kingdom",          "mascot": "arrowhead with crown"},
    "eagles":      {"city": "Philadelphia","colors": ["midnight green", "silver"], "sport": "NFL",  "slogan": "Fly Eagles Fly",   "mascot": "eagle in flight with football"},
    "cowboys":     {"city": "Dallas",      "colors": ["navy", "silver"],           "sport": "NFL",  "slogan": "America's Team",   "mascot": "lone star with football"},
    "49ers":       {"city": "San Francisco","colors": ["scarlet", "gold"],         "sport": "NFL",  "slogan": "Faithful",         "mascot": "gold miner with football helmet"},
    "ravens":      {"city": "Baltimore",   "colors": ["purple", "black"],          "sport": "NFL",  "slogan": "Rise Up",          "mascot": "raven with football"},
    "bills":       {"city": "Buffalo",     "colors": ["royal blue", "red"],        "sport": "NFL",  "slogan": "Bills Mafia",      "mascot": "charging buffalo"},
    "packers":     {"city": "Green Bay",   "colors": ["green", "gold"],            "sport": "NFL",  "slogan": "Go Pack Go",       "mascot": "vintage football with G logo"},
    "bengals":     {"city": "Cincinnati",  "colors": ["orange", "black"],          "sport": "NFL",  "slogan": "Who Dey",          "mascot": "bengal tiger with football"},
    "steelers":    {"city": "Pittsburgh",  "colors": ["black", "gold"],            "sport": "NFL",  "slogan": "Here We Go",       "mascot": "steel beam with football"},
    "dolphins":    {"city": "Miami",       "colors": ["aqua", "orange"],           "sport": "NFL",  "slogan": "Fins Up",          "mascot": "dolphin leaping with football"},
    # ── MLB ──
    "dodgers":     {"city": "Los Angeles", "colors": ["dodger blue", "white"],     "sport": "MLB",  "slogan": "Think Blue",       "mascot": "baseball with palm trees"},
    "yankees":     {"city": "New York",    "colors": ["navy", "white"],            "sport": "MLB",  "slogan": "Bronx Bombers",    "mascot": "pinstripe NY logo with baseball bat"},
    "red sox":     {"city": "Boston",      "colors": ["red", "navy"],              "sport": "MLB",  "slogan": "Boston Strong",    "mascot": "red socks with baseball"},
    "cubs":        {"city": "Chicago",     "colors": ["blue", "red"],              "sport": "MLB",  "slogan": "North Siders Forever","mascot": "bear cub with baseball"},
    "astros":      {"city": "Houston",     "colors": ["navy", "orange"],           "sport": "MLB",  "slogan": "Houston Strong",   "mascot": "star with baseball"},
    "braves":      {"city": "Atlanta",     "colors": ["navy", "red"],              "sport": "MLB",  "slogan": "Chop On",          "mascot": "tomahawk chop design"},
    "mets":        {"city": "New York",    "colors": ["blue", "orange"],           "sport": "MLB",  "slogan": "Let's Go Mets",    "mascot": "NYC skyline with baseball"},
    "guardians":   {"city": "Cleveland",   "colors": ["navy", "red"],              "sport": "MLB",  "slogan": "Go Guardians",     "mascot": "guardian statue with baseball"},
    # ── NHL ──
    "bruins":      {"city": "Boston",      "colors": ["black", "gold"],            "sport": "NHL",  "slogan": "Bruins Nation",    "mascot": "angry bear with hockey stick"},
    "rangers":     {"city": "New York",    "colors": ["royal blue", "red"],        "sport": "NHL",  "slogan": "Broadway Blues",   "mascot": "shield with hockey skates"},
    "penguins":    {"city": "Pittsburgh",  "colors": ["black", "gold"],            "sport": "NHL",  "slogan": "Let's Go Pens",    "mascot": "penguin with hockey stick"},
    "lightning":   {"city": "Tampa Bay",   "colors": ["blue", "white"],            "sport": "NHL",  "slogan": "Bolts Nation",     "mascot": "lightning bolt with puck"},
    "maple leafs": {"city": "Toronto",     "colors": ["blue", "white"],            "sport": "NHL",  "slogan": "Leafs Nation",     "mascot": "maple leaf with hockey stick"},
    "blackhawks":  {"city": "Chicago",     "colors": ["red", "black"],             "sport": "NHL",  "slogan": "Hawks Faithful",   "mascot": "native warrior with hockey stick"},
    # ── NCAA ──
    # ── NCAA Men's Basketball (NCAAB) ──
    "crimson tide":{"city": "Alabama",      "colors": ["crimson", "white"],         "sport": "NCAAF","slogan": "Roll Tide",             "mascot": "elephant with football helmet"},
    "wolverines":  {"city": "Michigan",     "colors": ["maize", "blue"],            "sport": "NCAAF","slogan": "Go Blue",               "mascot": "wolverine with helmeted M"},
    "wolverines basketball":{"city": "Michigan","colors": ["maize", "blue"],       "sport": "NCAAB","slogan": "Go Blue Basketball",     "mascot": "block M basketball with motion lines"},
    "michigan basketball":{"city": "Michigan","colors": ["maize", "blue"],         "sport": "NCAAB","slogan": "Go Blue",               "mascot": "wolverine dunking a basketball"},
    "michigan men's basketball":{"city": "Michigan","colors": ["maize", "blue"],   "sport": "NCAAB","slogan": "Go Blue",               "mascot": "wolverine with basketball"},
    "buckeyes":    {"city": "Ohio State",   "colors": ["scarlet", "silver gray"],   "sport": "NCAAF","slogan": "O-H-I-O",               "mascot": "brutus buckeye with football"},
    "longhorns":   {"city": "Texas",        "colors": ["burnt orange", "white"],    "sport": "NCAAF","slogan": "Hook Em Horns",          "mascot": "longhorn bull with football"},
    "tar heels":   {"city": "North Carolina","colors": ["carolina blue", "white"],  "sport": "NCAAB","slogan": "Go Heels",              "mascot": "ram mascot with basketball"},
    "blue devils": {"city": "Duke",         "colors": ["royal blue", "white"],      "sport": "NCAAB","slogan": "Duke Brotherhood",       "mascot": "devil mascot with basketball"},
    "jayhawks":    {"city": "Kansas",       "colors": ["crimson", "blue"],          "sport": "NCAAB","slogan": "Rock Chalk",             "mascot": "jayhawk bird with basketball"},
    "hoosiers":    {"city": "Indiana",      "colors": ["crimson", "cream"],         "sport": "NCAAB","slogan": "Indiana Faithful",       "mascot": "basketball with stripes"},
    "illini":      {"city": "Illinois",     "colors": ["orange", "navy"],           "sport": "NCAAB","slogan": "Lock It In",             "mascot": "chief with basketball"},
    "wildcats":    {"city": "Kentucky",     "colors": ["royal blue", "white"],      "sport": "NCAAB","slogan": "BBN Forever",            "mascot": "wildcat with basketball"},
    "gators":      {"city": "Florida",      "colors": ["orange", "blue"],           "sport": "NCAAB","slogan": "Go Gators",             "mascot": "alligator with basketball"},
    "spartans":    {"city": "Michigan State","colors": ["green", "white"],          "sport": "NCAAB","slogan": "Spartan Nation",          "mascot": "spartan warrior with basketball"},
    # ── UCLA ──
    "ucla":        {"city": "Los Angeles",  "colors": ["blue", "gold"],             "sport": "NCAAB","slogan": "Go Bruins",             "mascot": "bear mascot with basketball"},
    "ucla bruins": {"city": "Los Angeles",  "colors": ["blue", "gold"],             "sport": "NCAAB","slogan": "Go Bruins",             "mascot": "UCLA bear mascot slam dunk"},
    "ucla women":  {"city": "Los Angeles",  "colors": ["blue", "gold"],             "sport": "NCAAW","slogan": "Bruin Women Rise",       "mascot": "UCLA bear mascot dribbling basketball"},
    "ucla women's basketball":{"city": "Los Angeles","colors": ["blue", "gold"],    "sport": "NCAAW","slogan": "Go Bruins Women",        "mascot": "bear with women's basketball trophy"},
    # ── More NCAAB Teams ──
    "auburn tigers":{"city": "Auburn",     "colors": ["orange", "navy"],            "sport": "NCAAB","slogan": "War Eagle",             "mascot": "tiger with basketball"},
    "auburn":      {"city": "Auburn",       "colors": ["orange", "navy"],            "sport": "NCAAB","slogan": "War Eagle",             "mascot": "war eagle soaring over basketball court"},
    "uconn huskies":{"city": "Connecticut","colors": ["navy", "white"],             "sport": "NCAAB","slogan": "Husky Nation",          "mascot": "husky dog with basketball"},
    "tennessee volunteers":{"city": "Tennessee","colors": ["orange", "white"],      "sport": "NCAAB","slogan": "Vol Nation",             "mascot": "hound dog with basketball"},
    "florida gators basketball":{"city": "Florida","colors": ["orange", "blue"],    "sport": "NCAAB","slogan": "Go Gators",             "mascot": "alligator with basketball trophy"},
    "nc state":    {"city": "NC State",     "colors": ["red", "white"],             "sport": "NCAAB","slogan": "Go Pack",               "mascot": "wolfpack howling with basketball"},
    "wolfpack":    {"city": "NC State",     "colors": ["red", "white"],             "sport": "NCAAB","slogan": "Go Pack",               "mascot": "wolf with basketball"},
    "iowa hawkeyes":{"city": "Iowa",        "colors": ["gold", "black"],            "sport": "NCAAB","slogan": "Hawkeye Nation",         "mascot": "hawkeye bird with basketball"},
    "houston cougars":{"city": "Houston",  "colors": ["red", "white"],             "sport": "NCAAB","slogan": "Coogs",                 "mascot": "cougar with basketball"},
    "gonzaga bulldogs":{"city": "Gonzaga", "colors": ["navy", "red"],              "sport": "NCAAB","slogan": "Zag Nation",             "mascot": "bulldog with basketball"},
    "purdue boilermakers":{"city": "Purdue","colors": ["old gold", "black"],        "sport": "NCAAB","slogan": "Hammer Down",           "mascot": "boilermaker engineer with basketball"},
    "march madness": {"city": "NCAA",      "colors": ["royal blue", "gold"],       "sport": "NCAAB","slogan": "One Shining Moment",    "mascot": "basketball tournament bracket design"},
    "final four":  {"city": "NCAA",         "colors": ["royal blue", "gold"],       "sport": "NCAAB","slogan": "Final Four Dreams",    "mascot": "final four logo with basketball"},
    # ── NCAA Women's Basketball (NCAAW) ──
    "south carolina gamecocks":{"city": "South Carolina","colors": ["garnet", "black"],"sport": "NCAAW","slogan": "Gamecocks Nation",   "mascot": "gamecock with women's basketball"},
    "south carolina women":{"city": "South Carolina","colors": ["garnet", "black"], "sport": "NCAAW","slogan": "Undefeated Mindset",   "mascot": "gamecock champion with trophy"},
    "uconn women": {"city": "Connecticut", "colors": ["navy", "white"],             "sport": "NCAAW","slogan": "Husky Women Reign",     "mascot": "husky with women's basketball"},
    "uconn women's basketball":{"city": "Connecticut","colors": ["navy", "white"],  "sport": "NCAAW","slogan": "Husky Nation",          "mascot": "husky holding championship trophy"},
    "iowa hawkeyes women":{"city": "Iowa",  "colors": ["gold", "black"],            "sport": "NCAAW","slogan": "Hawkeye Nation",         "mascot": "hawkeye bird with women's basketball"},
    "caitlin clark":{"city": "Iowa",        "colors": ["gold", "black"],            "sport": "NCAAW","slogan": "22 Forever",             "mascot": "basketball with number 22 and hawkeye logo"},
    "lsu tigers women":{"city": "Baton Rouge","colors": ["purple", "gold"],         "sport": "NCAAW","slogan": "Geaux Tigers Women",    "mascot": "tiger with women's basketball"},
    "lsu women's basketball":{"city": "Baton Rouge","colors": ["purple", "gold"],   "sport": "NCAAW","slogan": "Geaux Tigers",          "mascot": "tiger mascot with gold basketball trophy"},
    "tennessee lady vols":{"city": "Tennessee","colors": ["orange", "white"],       "sport": "NCAAW","slogan": "Lady Vol Nation",      "mascot": "lady volunteer with basketball trophy"},
    "texas longhorns women":{"city": "Texas","colors": ["burnt orange", "white"],   "sport": "NCAAW","slogan": "Hook Em Women",        "mascot": "longhorn with women's basketball"},
    "ncaaw":       {"city": "NCAA Women",   "colors": ["royal blue", "gold"],        "sport": "NCAAW","slogan": "Women Hoops",          "mascot": "women basketball player silhouette"},
    "women's basketball":{"city": "NCAA",   "colors": ["royal blue", "gold"],        "sport": "NCAAW","slogan": "Women Ball Is Life",  "mascot": "female basketball player with crown"},
    "women's march madness":{"city": "NCAA","colors": ["royal blue", "pink"],        "sport": "NCAAW","slogan": "Her March Madness",    "mascot": "women's tournament bracket with basketball"},
}

# ========================================
#  RSS / DATA FETCHERS
# ========================================
def fetch_trending_from_rss():
    """Lấy Google Trends Daily RSS."""
    print("  📡 Đang lấy Google Trends RSS...")
    url = "https://trends.google.com/trending/rss?geo=US"
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    })
    trending = []
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        xml = resp.read().decode('utf-8')
        items = re.findall(r'<item>(.*?)</item>', xml, re.DOTALL)
        for item in items:
            tm = re.search(r'<title>(.*?)</title>', item)
            vm = re.search(r'<ht:approx_traffic>(.*?)</ht:approx_traffic>', item)
            title = tm.group(1).strip() if tm else ''
            traffic = vm.group(1).strip() if vm else ''
            for old, new in [('&amp;', '&'), ('&lt;', '<'), ('&gt;', '>'),
                              ('&#39;', "'"), ('&quot;', '"'),
                              ('<![CDATA[', ''), (']]>', '')]:
                title = title.replace(old, new)
            if title:
                trending.append({'query': title, 'traffic': traffic})
        print(f"  ✅ Google Trends: {len(trending)} xu hướng")
    except Exception as e:
        print(f"  ⚠ Google Trends RSS lỗi: {e}")
    return trending


def fetch_reddit_sports():
    """Lấy hot posts từ các subreddit thể thao."""
    print("  📱 Đang lấy Reddit sports hot posts...")
    SUBS = [
        # ── Major Leagues ──
        "nba", "nfl", "baseball", "hockey", "sports",
        # ── NCAA Men's Basketball ──
        "CollegeBasketball", "CFB", "MarchMadness",
        "WolverineNation", "MichiganWolverines",
        "UCLA", "uclasports",
        "UNCbbMBB", "KUbball",
        # ── NCAA Women's Basketball ──
        "WomensBasketball", "NCAAW",
        # ── NBA Teams ──
        "nbamemes", "nflmemes",
        "lakers", "NYKnicks", "warriors", "bostonceltics",
        # ── NFL Teams ──
        "cowboys", "eagles", "KansasCityChiefs",
        # ── MLB Teams ──
        "Dodgers", "NYYankees",
    ]
    all_posts = []
    for sub in SUBS:
        url = f"https://www.reddit.com/r/{sub}/hot/.rss?limit=15"
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
        })
        try:
            resp = urllib.request.urlopen(req, timeout=12)
            xml = resp.read().decode('utf-8')
            entries = re.findall(r'<entry>(.*?)</entry>', xml, re.DOTALL)
            for entry in entries:
                tm = re.search(r'<title[^>]*>(.*?)</title>', entry)
                lm = re.search(r'<link[^>]*href="([^"]*)"', entry)
                title = tm.group(1).strip() if tm else ''
                link  = lm.group(1).strip() if lm else ''
                for old, new in [('&amp;', '&'), ('&lt;', '<'), ('&gt;', '>'),
                                  ('&#39;', "'"), ('&quot;', '"'),
                                  ('<![CDATA[', ''), (']]>', '')]:
                    title = title.replace(old, new)
                if title and len(title) > 4:
                    all_posts.append({'title': title, 'link': link, 'sub': sub})
            time.sleep(0.8)
        except Exception:
            pass
    print(f"  ✅ Reddit: {len(all_posts)} bài hot")
    return all_posts


def load_etsy_data():
    """Đọc dữ liệu Etsy nếu đã chạy etsy_spy.py."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'etsy_data.json')
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"  ✅ Etsy data: {sum(len(d.get('items',[])) for d in data)} listings loaded")
            return data
        except Exception:
            pass
    print("  ℹ️  Etsy data chưa có (chạy etsy_spy.py trước để có thêm dữ liệu)")
    return []

# ========================================
#  SCORING ENGINE
# ========================================
def parse_traffic(traffic_str):
    """Chuyển '500K+', '1M+' → số."""
    try:
        s = traffic_str.replace('+', '').replace(',', '').upper()
        if 'M' in s:
            return int(float(s.replace('M', '')) * 1_000_000)
        if 'K' in s:
            return int(float(s.replace('K', '')) * 1_000)
        return int(s)
    except Exception:
        return 0


def match_team_from_text(text):
    """Tìm team trong text, trả về (team_key, team_info) hoặc None."""
    text_lower = text.lower()
    for key, info in TEAMS_DB.items():
        if key in text_lower or info['city'].lower() in text_lower:
            return key, info
    return None, None


def score_reddit_for_keyword(keyword, reddit_posts):
    """Đếm số bài Reddit có nhắc đến keyword."""
    kw = keyword.lower()
    count = 0
    for post in reddit_posts:
        if kw in post['title'].lower() or kw in post['sub'].lower():
            count += 1
    return min(count * 5, 30)  # max 30 points


def calculate_opportunity_score(trend_traffic, reddit_score, etsy_count):
    """
    Tính Opportunity Score (0-100):
    - Trend Traffic  → 0–40 điểm
    - Reddit Buzz    → 0–30 điểm
    - Low Etsy comp  → 0–30 điểm
    """
    # Trend score
    if trend_traffic >= 1_000_000:
        t = 40
    elif trend_traffic >= 500_000:
        t = 32
    elif trend_traffic >= 100_000:
        t = 22
    elif trend_traffic >= 10_000:
        t = 12
    else:
        t = 6 if trend_traffic > 0 else 0

    # Etsy competition (ít listing = cơ hội cao)
    if etsy_count < 0:
        e = 15  # unknown → neutral
    elif etsy_count < 300:
        e = 30
    elif etsy_count < 800:
        e = 24
    elif etsy_count < 2000:
        e = 16
    elif etsy_count < 5000:
        e = 8
    else:
        e = 2

    return min(t + reddit_score + e, 100)


def build_opportunities(trending, reddit_posts, etsy_data, history=None):
    """Xây dựng danh sách opportunities với score, lọc trùng lặp từ lịch sử."""
    if history is None:
        history = {}

    # Tạo etsy competition lookup từ etsy_data
    etsy_competition = {}
    for entry in etsy_data:
        kw = entry.get('keyword', '').lower()
        etsy_competition[kw] = entry.get('competition_count', -1)

    all_results  = []   # Tất cả (chưa lọc history)
    seen = set()

    for item in trending:
        query = item['query']
        if query.lower() in seen:
            continue

        team_key, team_info = match_team_from_text(query)

        # Tìm etsy competition
        etsy_count = -1
        for ek, ec in etsy_competition.items():
            if any(word in ek for word in query.lower().split()):
                etsy_count = ec
                break

        traffic_num = parse_traffic(item.get('traffic', ''))
        reddit_s    = score_reddit_for_keyword(query, reddit_posts)
        opp_score   = calculate_opportunity_score(traffic_num, reddit_s, etsy_count)
        sport_type  = team_info['sport'] if team_info else detect_sport(query)

        all_results.append({
            'keyword': query,
            'traffic': item.get('traffic', ''),
            'traffic_num': traffic_num,
            'reddit_score': reddit_s,
            'etsy_count': etsy_count,
            'opportunity_score': opp_score,
            'team_key': team_key,
            'team_info': team_info,
            'sport': sport_type,
            'source': 'Google Trends',
        })
        seen.add(query.lower())

    # Thêm từ Reddit nếu có team match mà chưa có
    for post in reddit_posts:
        team_key, team_info = match_team_from_text(post['title'])
        if team_key and team_key not in seen:
            reddit_s  = score_reddit_for_keyword(team_key, reddit_posts)
            opp_score = calculate_opportunity_score(0, reddit_s, -1)
            if opp_score >= 20:
                all_results.append({
                    'keyword': team_info['city'] + ' ' + team_key.title(),
                    'traffic': '',
                    'traffic_num': 0,
                    'reddit_score': reddit_s,
                    'etsy_count': -1,
                    'opportunity_score': opp_score,
                    'team_key': team_key,
                    'team_info': team_info,
                    'sport': team_info['sport'],
                    'source': 'Reddit Hot',
                })
                seen.add(team_key)

    all_results.sort(key=lambda x: x['opportunity_score'], reverse=True)

    # ── Lọc lịch sử: chỉ giữ keywords CHƯA xuất hiện trong COOLDOWN_DAYS ngày ──
    fresh   = [r for r in all_results if is_fresh(r['keyword'], history)]
    skipped = [r for r in all_results if not is_fresh(r['keyword'], history)]

    print(f"  🆕 Mới hoàn toàn: {len(fresh)} | ⏭ Đã bỏ qua (đã thấy <{COOLDOWN_DAYS}d): {len(skipped)}")

    # Nếu quá ít ideas mới, thêm ideas cũ nhất (đã lâu nhất kể từ cooldown) để bù
    if len(fresh) < 5 and skipped:
        kls = history.get('keyword_last_seen', {})
        skipped.sort(
            key=lambda r: kls.get(r['keyword'].lower().strip(), '2000-01-01')
        )  # Cũ nhất trước
        extra_needed = max(5 - len(fresh), 0)
        extras = skipped[:extra_needed]
        print(f"  ⚠  Ít ideas mới — thêm {len(extras)} idea cũ nhất để bù.")
        fresh.extend(extras)

    return fresh[:30], skipped  # (new_opportunities, skipped_list)


def detect_sport(text):
    """Phát hiện môn thể thao từ text."""
    t = text.lower()
    if any(w in t for w in ['basketball', 'nba', 'ncaab', 'dunk', 'court', 'hoop', 'baller']):
        return 'Basketball'
    if any(w in t for w in ['football', 'nfl', 'touchdown', 'super bowl', 'ncaaf', 'gridiron', 'quarterback']):
        return 'Football'
    if any(w in t for w in ['baseball', 'mlb', 'world series', 'pitcher', 'home run', 'batting']):
        return 'Baseball'
    if any(w in t for w in ['hockey', 'nhl', 'stanley cup', 'puck', 'goalie', 'ice rink']):
        return 'Hockey'
    return None  # Trả về None nếu không phải sports rõ ràng


def detect_niche(keyword, team_info):
    """
    Phân loại xu hướng vào các Niche khác nhau:
    - Sports (nếu có team_info hoặc detect_sport ra kết quả)
    - Entertainment (Movies / TV Shows)
    - Pop Culture / Lifestyle
    """
    if team_info or detect_sport(keyword):
        return 'Sports'
    
    t = keyword.lower()
    # Entertainment keywords
    if any(w in t for w in [
        'euphoria', 'netflix', 'hbo', 'show', 'movie', 'film', 'star wars', 
        'marvel', 'avengers', 'cast', 'season', 'episode', 'series', 'trailer',
        'oscars', 'actor', 'actress', 'cinema'
    ]):
        return 'Entertainment'
    
    # Music keywords
    if any(w in t for w in ['concert', 'tour', 'album', 'song', 'lyrics', 'rapper', 'singer', 'band']):
        return 'Music'
        
    return 'Pop Culture'


# ========================================
#  SLOGAN & TEMPLATE LIBRARY
# ========================================
SLOGAN_TEMPLATES = {
    'Sports': [
        "Faithful Since Est. '{year}",
        "{city} Pride — Game Day Ready",
        "Property of {city} {sport} Nation",
        "Eat. Sleep. {sport}. Repeat.",
        "True Fan Since Day One",
        "Victory Theory: {slogan}",
        "Defined by the Game"
    ],
    'Entertainment': [
        "Property of the Fandom",
        "Not Everyone Gets The Reference",
        "Iconic Moment — {keyword}",
        "In My {keyword} Era",
        "Obsessed Since Season 1",
        "Official Fan Theory Squad",
        "{keyword} Culture"
    ],
    'Music': [
        "The Tour Essentials — {year}",
        "Lyrics That Live Forever",
        "In My Concert Era",
        "Front Row Energy",
        "Vibe Curator — {keyword}",
        "Official Fan Merch"
    ],
    'Pop Culture': [
        "Aesthetic Vibe — {keyword}",
        "Main Character Energy",
        "Vibe Check: {keyword}",
        "Emotional Support {keyword}",
        "If You Know You Know",
        "Defined by {keyword}"
    ]
}

# ========================================
#  GEMINI PROMPT GENERATOR
# ========================================
SPORT_ELEMENTS = {
    'Basketball': 'basketball with dynamic motion lines',
    'Football':   'american football with laces detail',
    'Baseball':   'baseball with stitching detail',
    'Hockey':     'hockey puck and crossed sticks',
    'Sports':     'sports ball dynamic composition',
    'NBA':        'basketball with dynamic motion lines',
    'NFL':        'american football with laces detail',
    'MLB':        'baseball with stitching detail',
    'NHL':        'hockey puck and crossed sticks',
    'NCAAB':      'basketball with college pennant',
    'NCAAF':      'football with goalposts',
}

def build_gemini_prompt(keyword, team_info, concept_num, concept_data):
    """
    Tạo Gemini prompt cho thiết kế áo chuyên nghiệp:
    - SQUARE 1:1 composition
    - PURE WHITE background (dễ tách nền)
    - THICK BLACK OUTLINES (ưu tiên in áo tối màu)
    """
    colors = team_info['colors'][:2] if team_info else ['navy', 'white']
    color1 = colors[0]
    color2 = colors[1] if len(colors) > 1 else 'white'

    c = concept_data
    main_text = c['main_text']
    sub_text  = c['sub_text']
    style_desc = c['style_desc']
    graphic    = c['graphic']

    prompt = f"""Create a high-end, professional t-shirt design centered in a SQUARE 1:1 format on a PURE WHITE BACKGROUND.

CONCEPT: {style_desc}
MAIN TEXT: "{main_text}"
SUB TEXT: "{sub_text}"
GRAPHIC ELEMENT: {graphic}

COLOR PALETTE: Primary — {color1}. Accent — {color2}. Outlines — black. Highlights — white.

TECHNICAL REQUIREMENTS FOR PROFESSIONAL PRINTING:
• COMPOSITION: Perfectly centered SQUARE 1:1 aspect ratio.
• BACKGROUND: Absolute PURE WHITE (#FFFFFF) only. No textures, no gradients, no grey wash.
• OUTLINES: All graphic elements and text MUST have THICK BOLD BLACK OUTLINES (3-5pt stroke). This is critical for easy background removal and visibility on dark fabrics.
• STYLE: Flat vector art, screen-print ready. Absolutely NO 3D effects, NO shadows, NO gradients, NO glow.
• TEXT: Bold, heavy typography. Ensure all text is legible and has strong contrast.
• EDGES: Crisp, clean, sharp edges only.

The result should look like a premium vector sticker/decal ready for high-quality apparel printing. Every element must be contained within the square frame with enough margin from the edges."""

    return prompt


def generate_concepts(opp):
    """Tạo 3 design concepts KHÁC BIỆT và ĐÚNG NICHE cho một opportunity."""
    import random
    
    team_info = opp.get('team_info')
    keyword   = opp['keyword']
    niche     = detect_niche(keyword, team_info)
    sport     = opp.get('sport') or detect_sport(keyword) or 'Sports'
    
    team_key  = opp.get('team_key', '')
    city      = team_info['city']      if team_info else ''
    slogan    = team_info['slogan']    if team_info else keyword.upper()
    mascot    = team_info.get('mascot', 'iconic graphic') if team_info else f'{niche.lower()} illustration'
    colors    = team_info['colors'][:2] if team_info else ['#58a6ff', '#8b949e']
    team_name = team_key.replace('-', ' ').title() if team_key else keyword
    
    current_year = datetime.now().year
    short_year   = str(current_year)[-2:]
    
    # Lấy slogans phù hợp niche
    pool = SLOGAN_TEMPLATES.get(niche, SLOGAN_TEMPLATES['Pop Culture'])
    
    # Chọn 3 slogan khác nhau
    selected_slogans = random.sample(pool, 3)
    
    def format_slogan(s):
        return s.format(
            year=short_year, 
            city=city.upper() if city else 'LEGENDARY', 
            sport=sport.upper(), 
            slogan=slogan.upper(),
            keyword=keyword.upper() if len(keyword) < 20 else 'TREND'
        )

    # Styles theo Niche
    if niche == 'Sports':
        styles = [
            ('🏆 Vintage Badge', 'Vintage athletics mascot badge with circular frame and distressed texture', f'{mascot} inside circular collegiate border'),
            ('⚡ Bold Statement', 'Oversized heavy typography with aggressive layout', f'Modern clean {sport} gear graphic'),
            ('🎨 Retro Script', 'Retro 90s style script lettering with underline tail', f'Dynamic {sport} motion illustration')
        ]
    elif niche == 'Entertainment':
        styles = [
            ('🎬 Cinematic Art', 'Poster-style aesthetic with dramatic lighting and character silhouettes', f'Artistic representation of {keyword} mood'),
            ('💬 Iconic Quote', 'Minimalist typography focused on a famous line or phrase', 'Small symbolic icon related to the show'),
            ('📺 Fan Club', 'Y2K retro fan-club badge with vibrant colors', f'Collage of {keyword} aesthetic elements')
        ]
    else:
        styles = [
            ('✨ Modern Aesthetic', 'Clean minimalist line art with elegant serif typography', 'Abstract geometric symbol or minimal line art'),
            ('🔥 Streetwear', 'Bold edgy typography with large graphic on back style', 'Graffiti-style spray paint elements'),
            ('Retro Vibe', '70s/80s warm color palette with wavy typography', 'Sun burst with retro sunset vibes')
        ]

    concepts = []
    for i in range(3):
        title, style_desc, graphic = styles[i]
        concepts.append({
            'title':      title,
            'style_name': title,
            'style_desc': style_desc,
            'main_text':  team_name.upper() if i != 1 or niche != 'Sports' else slogan.upper(),
            'sub_text':   format_slogan(selected_slogans[i]),
            'graphic':    graphic,
            'color_hint': f'{colors[0]} and {colors[1] if len(colors)>1 else "white"}',
        })

    # Thêm Gemini prompt cho từng concept
    for c in concepts:
        c['gemini_prompt'] = build_gemini_prompt(keyword, team_info, 0, c)

    return concepts

# ========================================
#  HTML GENERATOR
# ========================================
def score_color(score):
    if score >= 80: return ('#ff7b72', '🔥')
    if score >= 60: return ('#ffa657', '⚡')
    if score >= 40: return ('#d29922', '🌟')
    return ('#8b949e', '💡')


def etsy_competition_display(count):
    if count < 0:   return ('❓', '#8b949e', 'Unknown')
    if count < 500: return ('🟢', '#3fb950', f'LOW ({count:,})')
    if count < 2000: return ('🟡', '#d29922', f'MED ({count:,})')
    if count < 5000: return ('🟠', '#ffa657', f'HIGH ({count:,})')
    return ('🔴', '#ff7b72', f'V.HIGH ({count:,})')


def generate_html(opportunities, now, skipped=None, history=None):
    cards_html = ''

    for idx, opp in enumerate(opportunities):
        score = opp['opportunity_score']
        score_col, score_icon = score_color(score)
        team_info = opp.get('team_info')
        team_colors = team_info['colors'][:2] if team_info else ['#58a6ff', '#8b949e']
        etsy_icon, etsy_col, etsy_label = etsy_competition_display(opp['etsy_count'])
        source_badge = opp.get('source', 'Research')
        traffic_display = opp.get('traffic', '') or '—'

        concepts = generate_concepts(opp)

        # Build concept tabs
        tab_buttons = ''
        tab_panels  = ''
        for ci, concept in enumerate(concepts):
            active_btn   = 'tab-btn-active' if ci == 0 else ''
            active_panel = 'tab-panel-active' if ci == 0 else ''
            prompt_escaped = concept['gemini_prompt'].replace('`', '&#96;').replace('\\', '\\\\')

            tab_buttons += f"""<button class="tab-btn {active_btn}" onclick="switchTab(this, 'panel-{idx}-{ci}')">{concept['title']}</button>"""

            tab_panels += f"""
            <div id="panel-{idx}-{ci}" class="tab-panel {active_panel}">
                <div class="concept-header">
                    <span class="concept-style-badge">{concept['style_name']}</span>
                    <span class="concept-color-hint">🎨 {concept['color_hint']}</span>
                </div>
                <div class="concept-details">
                    <div class="detail-row"><span class="detail-label">MAIN TEXT</span><span class="detail-value">"{concept['main_text']}"</span></div>
                    <div class="detail-row"><span class="detail-label">SUB TEXT</span><span class="detail-value">"{concept['sub_text']}"</span></div>
                    <div class="detail-row"><span class="detail-label">GRAPHIC</span><span class="detail-value">{concept['graphic']}</span></div>
                </div>
                <div class="prompt-section">
                    <div class="prompt-header">
                        <span class="prompt-label">✨ Gemini Image Prompt</span>
                        <div class="prompt-actions">
                            <button class="copy-btn" onclick="copyPrompt('prompt-{idx}-{ci}', this)">📋 Copy Prompt</button>
                            <a class="gemini-btn" href="https://gemini.google.com" target="_blank">🔮 Open Gemini</a>
                        </div>
                    </div>
                    <textarea id="prompt-{idx}-{ci}" class="prompt-text" readonly>{concept['gemini_prompt']}</textarea>
                </div>
            </div>"""

        cards_html += f"""
        <div class="opp-card" id="card-{idx}">
            <div class="card-header">
                <div class="card-title-row">
                    <span class="rank-badge">#{idx+1}</span>
                    <h3 class="opp-name">{opp['keyword']}</h3>
                    <div class="score-badge" style="background:{score_col}22; border:1px solid {score_col}; color:{score_col};">
                        {score_icon} {score}/100
                    </div>
                </div>
                <div class="card-meta-row">
                    <span class="meta-chip source-chip">{source_badge}</span>
                    <span class="meta-chip" style="color:{score_col};">📈 Trend: {traffic_display}</span>
                    <span class="meta-chip reddit-chip">💬 Reddit: +{opp['reddit_score']}</span>
                    <span class="meta-chip" style="color:{etsy_col};">{etsy_icon} Etsy: {etsy_label}</span>
                    {'<span class="meta-chip sport-chip">' + opp.get("sport","") + '</span>' if opp.get("sport") else ''}
                </div>
            </div>
            <div class="concept-tabs">
                <div class="tab-buttons">{tab_buttons}</div>
                {tab_panels}
            </div>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>💡 POD Idea Generator</title>
    <style>
        :root {{
            --bg: #0d1117; --card: #161b22; --card2: #1c2333; --border: #30363d;
            --text: #c9d1d9; --muted: #8b949e;
            --red: #ff7b72; --orange: #ffa657; --green: #3fb950;
            --blue: #58a6ff; --yellow: #d29922; --purple: #bc8cff;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
            background: var(--bg); color: var(--text); min-height: 100vh;
        }}
        /* ── HEADER ── */
        header {{
            background: linear-gradient(135deg, #010409 0%, #0d1117 100%);
            border-bottom: 1px solid var(--border);
            padding: 1.5rem 2rem; text-align: center;
        }}
        h1 {{
            font-size: 2.2rem; font-weight: 900;
            background: linear-gradient(90deg, #ffa657, #ff7b72, #bc8cff);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        }}
        .subtitle {{ color: var(--muted); font-size: 0.85rem; margin-top: 0.4rem; }}
        /* ── HOW TO USE ── */
        .howto {{
            background: #1c2333; border: 1px solid var(--border); border-left: 3px solid var(--orange);
            border-radius: 8px; padding: 1rem 1.5rem;
            margin: 1.2rem auto; max-width: 1100px;
            font-size: 0.78rem; color: #ffa657; line-height: 1.7;
        }}
        .howto strong {{ color: #fff; }}
        /* ── STATS BAR ── */
        .stats-bar {{
            display: flex; gap: 1rem; flex-wrap: wrap; justify-content: center;
            padding: 0.8rem 2rem; background: var(--card);
            border-bottom: 1px solid var(--border);
        }}
        .stat-item {{
            font-size: 0.75rem; color: var(--muted);
        }}
        .stat-item strong {{ color: #fff; font-size: 0.9rem; }}
        /* ── CONTAINER ── */
        .container {{ max-width: 1150px; margin: 0 auto; padding: 1.5rem; }}
        /* ── OPPORTUNITY CARD ── */
        .opp-card {{
            background: var(--card); border: 1px solid var(--border); border-radius: 12px;
            margin-bottom: 1.5rem; overflow: hidden;
            transition: border-color 0.2s, box-shadow 0.2s;
        }}
        .opp-card:hover {{ border-color: #444d56; box-shadow: 0 4px 20px rgba(0,0,0,0.3); }}
        .card-header {{ padding: 1rem 1.2rem 0.8rem; border-bottom: 1px solid var(--border); }}
        .card-title-row {{
            display: flex; align-items: center; gap: 0.8rem; flex-wrap: wrap;
            margin-bottom: 0.6rem;
        }}
        .rank-badge {{
            background: var(--card2); color: var(--muted); font-size: 0.7rem;
            font-weight: 700; padding: 2px 8px; border-radius: 6px; min-width: 32px; text-align: center;
        }}
        .opp-name {{ font-size: 1.1rem; font-weight: 700; color: #fff; flex: 1; }}
        .score-badge {{
            font-size: 0.8rem; font-weight: 800; padding: 3px 12px;
            border-radius: 20px; white-space: nowrap;
        }}
        .card-meta-row {{ display: flex; gap: 0.5rem; flex-wrap: wrap; }}
        .meta-chip {{
            font-size: 0.65rem; padding: 2px 8px; border-radius: 10px;
            background: var(--card2); color: var(--muted);
        }}
        .source-chip {{ color: var(--blue); }}
        .reddit-chip {{ color: var(--orange); }}
        .sport-chip  {{ color: var(--purple); }}
        /* ── TABS ── */
        .concept-tabs {{ padding: 1rem 1.2rem; }}
        .tab-buttons {{ display: flex; gap: 0.4rem; margin-bottom: 1rem; flex-wrap: wrap; }}
        .tab-btn {{
            background: var(--card2); border: 1px solid var(--border); color: var(--muted);
            font-size: 0.72rem; font-weight: 600; padding: 0.4rem 0.9rem;
            border-radius: 20px; cursor: pointer; transition: all 0.2s;
        }}
        .tab-btn:hover {{ border-color: var(--orange); color: var(--orange); }}
        .tab-btn-active {{ background: var(--orange) !important; border-color: var(--orange) !important; color: #000 !important; }}
        .tab-panel {{ display: none; }}
        .tab-panel-active {{ display: block; }}
        /* ── CONCEPT CONTENT ── */
        .concept-header {{
            display: flex; align-items: center; gap: 1rem; margin-bottom: 0.8rem; flex-wrap: wrap;
        }}
        .concept-style-badge {{
            font-size: 0.7rem; font-weight: 700; padding: 3px 10px;
            background: #1f6feb; color: #fff; border-radius: 10px;
        }}
        .concept-color-hint {{ font-size: 0.7rem; color: var(--muted); }}
        .concept-details {{
            background: var(--card2); border-radius: 8px; padding: 0.8rem 1rem;
            margin-bottom: 0.8rem;
        }}
        .detail-row {{
            display: flex; gap: 0.8rem; align-items: baseline;
            font-size: 0.72rem; padding: 0.25rem 0;
            border-bottom: 1px solid var(--border);
        }}
        .detail-row:last-child {{ border-bottom: none; }}
        .detail-label {{
            color: var(--muted); font-size: 0.62rem; font-weight: 700;
            text-transform: uppercase; letter-spacing: 0.05em; min-width: 75px;
        }}
        .detail-value {{ color: #fff; flex: 1; line-height: 1.4; }}
        /* ── PROMPT ── */
        .prompt-section {{ }}
        .prompt-header {{
            display: flex; justify-content: space-between; align-items: center;
            margin-bottom: 0.5rem; flex-wrap: wrap; gap: 0.5rem;
        }}
        .prompt-label {{ font-size: 0.75rem; font-weight: 700; color: var(--yellow); }}
        .prompt-actions {{ display: flex; gap: 0.5rem; }}
        .copy-btn {{
            background: #238636; color: #fff; border: none; border-radius: 6px;
            font-size: 0.7rem; font-weight: 700; padding: 0.4rem 0.9rem;
            cursor: pointer; transition: background 0.2s;
        }}
        .copy-btn:hover {{ background: #2ea043; }}
        .copy-btn.copied {{ background: #1f6feb; }}
        .gemini-btn {{
            background: var(--card2); color: var(--blue); border: 1px solid var(--border);
            border-radius: 6px; font-size: 0.7rem; font-weight: 700;
            padding: 0.4rem 0.9rem; text-decoration: none; transition: all 0.2s;
        }}
        .gemini-btn:hover {{ border-color: var(--blue); color: #fff; background: #1f2d3d; }}
        .prompt-text {{
            width: 100%; height: 160px; background: #010409;
            border: 1px solid var(--border); border-radius: 8px;
            color: #c9d1d9; font-size: 0.7rem; font-family: "SF Mono", "Consolas", monospace;
            line-height: 1.5; padding: 0.8rem; resize: vertical;
            transition: border-color 0.2s;
        }}
        .prompt-text:focus {{ outline: none; border-color: var(--blue); }}
        /* ── EMPTY STATE ── */
        .empty-state {{
            text-align: center; padding: 3rem; color: var(--muted);
        }}
        /* ── SCROLLBAR ── */
        ::-webkit-scrollbar {{ width: 6px; }}
        ::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 3px; }}
    </style>
</head>
<body>
    <header>
        <h1>💡 POD Idea Generator</h1>
        <p class="subtitle">Opportunities ranked by score · Design briefs ready · Gemini prompts copy-paste — Generated at {now}</p>
    </header>

    <div class="howto">
        <strong>🚀 Quy trình 4 bước:</strong><br>
        1️⃣ Xem bảng xếp hạng bên dưới — chọn opportunity có score cao + Etsy 🟢 LOW<br>
        2️⃣ Chọn concept phù hợp (Vintage Badge / Bold Statement / Mascot Art)<br>
        3️⃣ Nhấn <strong>📋 Copy Prompt</strong> → paste vào <strong>Gemini</strong> (hoặc Imagen 3)<br>
        4️⃣ Tải ảnh về → xóa nền trắng → in lên áo tối màu → <strong>BÁN!</strong>
    </div>

    <div class="stats-bar">
        <div class="stat-item">🔥 <strong>{len(opportunities)}</strong> New Ideas</div>
        <div class="stat-item">⚡ Top Score: <strong>{opportunities[0]['opportunity_score'] if opportunities else 0}/100</strong></div>
        <div class="stat-item">📅 <strong>{now}</strong></div>
        <div class="stat-item">🎨 <strong>{len(opportunities) * 3}</strong> Prompts Ready</div>
        <div class="stat-item">⏭ <strong>{len(skipped) if skipped else 0}</strong> Skipped (seen recently)</div>
        <div class="stat-item">🕓 Cooldown: <strong>{COOLDOWN_DAYS} days</strong></div>
    </div>

    <div class="container">
        {''.join([cards_html]) if opportunities else '<div class="empty-state"><p>Không có ideas mới hôm nay — tất cả đã xuất hiện gần đây. Thử lại ngày mai hoặc chạy với flag --reset để xóa lịch sử!</p></div>'}
        {_build_history_section(history, skipped)}
    </div>

    <script>
        function switchTab(btn, panelId) {{
            // Deactivate all buttons and panels in same card
            const card = btn.closest('.opp-card');
            card.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('tab-btn-active'));
            card.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('tab-panel-active'));
            // Activate selected
            btn.classList.add('tab-btn-active');
            document.getElementById(panelId).classList.add('tab-panel-active');
        }}

        function copyPrompt(textareaId, btn) {{
            const ta = document.getElementById(textareaId);
            ta.select();
            navigator.clipboard.writeText(ta.value).then(() => {{
                const orig = btn.textContent;
                btn.textContent = '✅ Copied!';
                btn.classList.add('copied');
                setTimeout(() => {{
                    btn.textContent = orig;
                    btn.classList.remove('copied');
                }}, 2000);
            }}).catch(() => {{
                document.execCommand('copy');
                btn.textContent = '✅ Copied!';
                setTimeout(() => btn.textContent = '📋 Copy Prompt', 2000);
            }});
        }}
    </script>
</body>
</html>"""


def _build_history_section(history, skipped):
    """Tạo section lịch sử các lần chạy trước."""
    if not history:
        return ''

    runs = history.get('runs', [])
    if len(runs) <= 1 and not skipped:
        return ''

    # Bảng skipped keywords
    skipped_html = ''
    if skipped:
        skipped_items = ''.join(
            f'<span style="display:inline-block;background:#1c2333;border:1px solid #30363d;'
            f'border-radius:10px;font-size:0.62rem;padding:2px 10px;margin:2px;color:#8b949e;">'
            f'{r["keyword"]} <span style="color:#d29922;">({r["opportunity_score"]})</span></span>'
            for r in skipped[:40]
        )
        skipped_html = f"""
        <div style="margin-bottom:1.5rem;">
            <p style="font-size:0.75rem;color:#8b949e;margin-bottom:0.5rem;">⏭ <strong style="color:#fff;">Bỏ qua lần này</strong> (đã hiện trong {COOLDOWN_DAYS} ngày qua):</p>
            <div>{skipped_items}</div>
        </div>"""

    # Bảng lịch sử các lần chạy
    runs_html = ''
    for run in reversed(runs[-10:]):  # 10 lần gần nhất
        kws_display = ', '.join(run.get('keywords', [])[:8])
        if len(run.get('keywords', [])) > 8:
            kws_display += f' (+{len(run["keywords"])-8} more)'
        runs_html += f"""
        <div style="border-bottom:1px solid #30363d;padding:0.5rem 0;font-size:0.68rem;">
            <span style="color:#58a6ff;min-width:140px;display:inline-block;">{run['date']} {run.get('time','')} </span>
            <span style="color:#8b949e;">{kws_display or 'No data'}</span>
        </div>"""

    return f"""
    <details style="margin-top:2rem;">
        <summary style="cursor:pointer;font-size:0.85rem;font-weight:700;color:#8b949e;padding:0.8rem;
            background:#161b22;border:1px solid #30363d;border-radius:8px;list-style:none;
            display:flex;align-items:center;gap:0.5rem;">
            📜 Lịch sử các lần chạy trước (click để xem)
        </summary>
        <div style="background:#161b22;border:1px solid #30363d;border-top:none;
            border-radius:0 0 8px 8px;padding:1rem 1.2rem;">
            {skipped_html}
            <p style="font-size:0.75rem;color:#fff;font-weight:700;margin-bottom:0.5rem;">📋 Lần chạy gần nhất:</p>
            {runs_html}
            <p style="font-size:0.65rem;color:#484f58;margin-top:0.8rem;">
                💡 Muốn reset lịch sử? Chạy: <code style="background:#0d1117;padding:2px 6px;border-radius:4px;">python3 idea_generator.py --reset</code>
            </p>
        </div>
    </details>"""


def main():
    print("==================================================")
    print("  💡 POD IDEA GENERATOR — Intelligence Engine    ")
    print("  Trends + Reddit + Etsy → Design Briefs Ready  ")
    print("==================================================")

    # ── Xử lý flag --reset ──
    if '--reset' in sys.argv:
        reset_history()
    print()

    # ── Load lịch sử ──
    history = load_history()
    total_seen = len(history.get('keyword_last_seen', {}))
    total_runs = len(history.get('runs', []))
    print(f"  📚 Lịch sử: {total_seen} keywords đã thấy | {total_runs} lần chạy trước")
    print()

    # 1. Thu thập dữ liệu
    trending     = fetch_trending_from_rss()
    time.sleep(1)
    reddit_posts = fetch_reddit_sports()
    time.sleep(0.5)
    etsy_data    = load_etsy_data()

    # 2. Tính opportunities + lọc lịch sử
    print("\n🧠 Đang tính Opportunity Scores + lọc lịch sử...")
    opportunities, skipped = build_opportunities(trending, reddit_posts, etsy_data, history)

    print(f"\n📊 Tổng kết:")
    print(f"  🆕 Ideas MỚI hôm nay: {len(opportunities)}")
    print(f"  ⏭  Đã bỏ qua (trùng lặp): {len(skipped)}")
    print(f"  🎨 Design prompts ready: {len(opportunities) * 3}")
    if opportunities:
        top = opportunities[0]
        print(f"  🔥 Top: '{top['keyword']}' — Score {top['opportunity_score']}/100")

    # 3. Lưu lịch sử
    shown_kws = [opp['keyword'] for opp in opportunities]
    save_history(history, shown_kws)

    # 4. Sinh HTML
    now = datetime.now().strftime("%H:%M:%S — %d/%m/%Y")
    html_content = generate_html(opportunities, now, skipped=skipped, history=history)
    output_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ideas_dashboard.html')
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"\n✅ Dashboard: ideas_dashboard.html")
    webbrowser.open(f"file://{output_file}")
    print("🎉 Hoàn tất! Mở dashboard và bắt đầu copy prompts!")
    print(f"\n💡 Tip: Chạy 'python3 idea_generator.py --reset' để xóa lịch sử nếu muốn.")


if __name__ == '__main__':
    main()
