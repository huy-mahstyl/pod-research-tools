import urllib.request
import json
import os
import webbrowser
from datetime import datetime

STORES = [
    {
        'name': 'BreakingT',
        'url': 'https://breakingt.com/products.json?limit=40',
        'base_link': 'https://breakingt.com/products/'
    },
    {
        'name': 'RotoWear',
        'url': 'https://rotowear.com/products.json?limit=40',
        'base_link': 'https://rotowear.com/products/'
    },
    {
        'name': 'Obvious Shirts',
        'url': 'https://obviousshirts.com/products.json?limit=40',
        'base_link': 'https://obviousshirts.com/products/'
    },
    {
        'name': '500 Level',
        'url': 'https://www.500level.com/products.json?limit=40',
        'base_link': 'https://www.500level.com/products/'
    },
    {
        'name': 'Smack Apparel',
        'url': 'https://www.smackapparel.com/products.json?limit=40',
        'base_link': 'https://www.smackapparel.com/products/'
    }
]

def fetch_products(store_url):
    req = urllib.request.Request(store_url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        response = urllib.request.urlopen(req, timeout=15)
        data = json.loads(response.read())
        return data.get('products', [])
    except Exception as e:
        print(f"Error fetching data from {store_url}: {e}")
        return []

def generate_html(all_store_data):
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>POD Idea Generator</title>
        <style>
            :root {{
                --bg-color: #0d1117;
                --text-color: #c9d1d9;
                --card-bg: #161b22;
                --card-border: #30363d;
                --accent-color: #58a6ff;
                --hover-accent: #3182ce;
            }}
            * {{ box-sizing: border-box; margin: 0; padding: 0; }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
                background-color: var(--bg-color);
                color: var(--text-color);
                height: 100vh;
                display: flex;
                flex-direction: column;
                overflow: hidden;
            }}
            header {{
                text-align: center;
                padding: 1rem;
                background: #010409;
                border-bottom: 1px solid var(--card-border);
                flex-shrink: 0;
            }}
            h1 {{
                font-size: 1.8rem;
                font-weight: 800;
                margin-bottom: 0.2rem;
                background: linear-gradient(90deg, #58a6ff, #1f6feb);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }}
            p.subtitle {{ font-size: 0.9rem; color: #8b949e; }}
            .dashboard-container {{
                display: flex;
                flex: 1;
                overflow: hidden;
                padding: 1.5rem;
                gap: 1.5rem;
            }}
            .col-left {{
                flex: 1;
                overflow-y: auto;
                padding-right: 1rem;
            }}
            .col-google {{
                flex: 1;
                overflow-y: auto;
                background: var(--card-bg);
                border: 1px solid var(--card-border);
                border-radius: 12px;
                padding: 1.5rem;
                box-shadow: -4px 0 15px rgba(0,0,0,0.2);
            }}
            .store-section {{
                margin-bottom: 3rem;
                padding-bottom: 2rem;
                border-bottom: 1px dashed #30363d;
            }}
            .store-header {{
                margin-bottom: 1.5rem;
                font-size: 1.5rem;
                color: #ffffff;
                display: flex;
                align-items: center;
                gap: 10px;
            }}
            .grid {{
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
                gap: 1rem;
            }}
            .card {{
                background-color: var(--card-bg);
                border: 1px solid var(--card-border);
                border-radius: 8px;
                overflow: hidden;
                transition: transform 0.2s ease, border-color 0.2s;
                display: flex;
                flex-direction: column;
            }}
            .card:hover {{
                transform: translateY(-3px);
                border-color: var(--accent-color);
            }}
            .card-img-wrapper {{
                width: 100%;
                padding-top: 100%;
                position: relative;
                background-color: #ffffff;
            }}
            .card-img {{
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                object-fit: contain;
                padding: 0.5rem;
            }}
            .card-content {{
                padding: 0.8rem;
                display: flex;
                flex-direction: column;
                justify-content: space-between;
                flex-grow: 1;
            }}
            .card-title {{
                font-size: 0.85rem;
                font-weight: 600;
                margin-bottom: 0.5rem;
                color: #ffffff;
                display: -webkit-box;
                -webkit-line-clamp: 2;
                -webkit-box-orient: vertical;
                overflow: hidden;
                line-height: 1.3;
            }}
            .card-btn {{
                text-align: center;
                padding: 0.4rem;
                background-color: var(--accent-color);
                color: #ffffff;
                text-decoration: none;
                border-radius: 4px;
                font-size: 0.75rem;
                font-weight: 600;
            }}
            .card-btn:hover {{ background-color: var(--hover-accent); }}
            .date-badge {{
                display: inline-block;
                background: #238636;
                color: #fff;
                padding: 2px 6px;
                border-radius: 8px;
                font-size: 0.6rem;
                font-weight: bold;
                margin-bottom: 5px;
            }}
            /* Custom Scrollbar */
            ::-webkit-scrollbar {{ width: 8px; }}
            ::-webkit-scrollbar-track {{ background: transparent; }}
            ::-webkit-scrollbar-thumb {{ background: #30363d; border-radius: 4px; }}
            ::-webkit-scrollbar-thumb:hover {{ background: #484f58; }}
        </style>
    </head>
    <body>
        <header>
            <h1>POD Idea Generator</h1>
            <p class="subtitle">Multi-Store Intelligence - Gathered on {datetime.now().strftime("%Y-%m-%d %H:%M")}</p>
        </header>
        <div class="dashboard-container">
            <div class="col-left">
    """
    
    for store_data in all_store_data:
        store_name = store_data['name']
        products = store_data['products']
        
        html_content += f"""
                <div class="store-section">
                    <h2 class="store-header">🔥 {store_name} <span style="font-size:0.9rem; color:#8b949e; font-weight:normal;">({len(products)} latest)</span></h2>
                    <div class="grid">
        """
        
        for product in products:
            title = product.get('title', 'Unknown Title')
            handle = product.get('handle', '')
            link = store_data['base_link'] + handle
            
            images = product.get('images', [])
            image_src = images[0].get('src', 'https://via.placeholder.com/150?text=No+Image') if images else 'https://via.placeholder.com/150?text=No+Image'
            
            pub_date_str = product.get('published_at', '')
            is_today = False
            if pub_date_str:
                try:
                    date_obj = datetime.strptime(pub_date_str[:19], "%Y-%m-%dT%H:%M:%S")
                    if date_obj.date() == datetime.now().date():
                        is_today = True
                except:
                    pass
                    
            badge_html = '<span class="date-badge">NEW</span>' if is_today else ''

            html_content += f"""
                        <div class="card">
                            <div class="card-img-wrapper">
                                <img src="{image_src}" alt="{title}" class="card-img" loading="lazy">
                            </div>
                            <div class="card-content">
                                <div>
                                    {badge_html}
                                    <h3 class="card-title">{title}</h3>
                                </div>
                                <a href="{link}" target="_blank" class="card-btn">View Hit</a>
                            </div>
                        </div>
            """
            
        html_content += """
                    </div>
                </div>
        """
        
    html_content += """
            </div>
            <div class="col-google" id="google-spy-container">
                <!-- GOOGLE_SPY_CONTENT_START -->
                <h2 style="color: #ff7b72; margin-bottom: 1rem; font-size: 1.4rem;">Google Spy (Last 24h)</h2>
                <p style="color: #8b949e; font-size: 0.9rem;">Waiting for Google Spy module to load...</p>
                <!-- GOOGLE_SPY_CONTENT_END -->
            </div>
        </div>
    </body>
    </html>
    """
    
    output_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'daily_ideas.html')
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
        
    return output_file

def main():
    print("Initiating Multi-Store Scraper...")
    all_store_data = []
    
    for store in STORES:
        print(f"Fetching from {store['name']}...")
        products = fetch_products(store['url'])
        if products:
            products.sort(key=lambda x: x.get('published_at', ''), reverse=True)
            all_store_data.append({
                'name': store['name'],
                'base_link': store['base_link'],
                'products': products
            })
            
    if all_store_data:
        output_file = generate_html(all_store_data)
        if output_file:
            print("Multi-Store Base Dashboard generated successfully!")
    else:
        print("Failed to fetch products from any store.")

if __name__ == '__main__':
    main()
