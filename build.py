#!/usr/bin/env python3
"""
Fetches YouTube RSS feeds and generates a static HTML site with embedded videos.
Organized by tabs defined in channels.json.
"""

import json
import re
import ssl
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

# Create an SSL context - handle macOS cert issues gracefully
# GitHub Actions won't have this problem, but local macOS Python often does
try:
    import certifi
    _ssl_context = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _ssl_context = ssl._create_unverified_context()


def get_channel_id_from_handle(handle_url: str) -> str | None:
    """Fetch a YouTube channel page and extract the channel ID from metadata."""
    try:
        req = urllib.request.Request(
            handle_url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; RSSBot/1.0)"}
        )
        with urllib.request.urlopen(req, timeout=15, context=_ssl_context) as response:
            html = response.read().decode("utf-8", errors="ignore")

        # Look for channel ID in page source
        patterns = [
            r'"externalId"\s*:\s*"(UC[a-zA-Z0-9_-]{22})"',
            r'"channelId"\s*:\s*"(UC[a-zA-Z0-9_-]{22})"',
            r'<meta\s+itemprop="channelId"\s+content="(UC[a-zA-Z0-9_-]{22})"',
            r'channel_id=(UC[a-zA-Z0-9_-]{22})',
        ]
        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                return match.group(1)
    except Exception as e:
        print(f"  Warning: Could not fetch channel ID from {handle_url}: {e}")
    return None


def fetch_rss_feed(channel_id: str) -> list[dict]:
    """Fetch RSS feed for a YouTube channel and return video entries."""
    feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    try:
        req = urllib.request.Request(
            feed_url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; RSSBot/1.0)"}
        )
        with urllib.request.urlopen(req, timeout=15, context=_ssl_context) as response:
            xml_data = response.read()
    except Exception as e:
        print(f"  Warning: Could not fetch feed for {channel_id}: {e}")
        return []

    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "yt": "http://www.youtube.com/xml/schemas/2015",
        "media": "http://search.yahoo.com/mrss/",
    }

    root = ET.fromstring(xml_data)
    videos = []

    for entry in root.findall("atom:entry", ns):
        video_id_el = entry.find("yt:videoId", ns)
        title_el = entry.find("atom:title", ns)
        published_el = entry.find("atom:published", ns)
        author_el = entry.find("atom:author/atom:name", ns)
        thumbnail_el = entry.find("media:group/media:thumbnail", ns)

        if video_id_el is None or title_el is None:
            continue

        video_id = video_id_el.text
        title = title_el.text or "Untitled"
        published = published_el.text if published_el is not None else ""
        author = author_el.text if author_el is not None else ""
        thumbnail = (
            thumbnail_el.get("url", "")
            if thumbnail_el is not None
            else f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
        )

        # Parse date for sorting
        try:
            pub_date = datetime.fromisoformat(published.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            pub_date = datetime.min

        videos.append({
            "video_id": video_id,
            "title": title,
            "published": published,
            "pub_date": pub_date,
            "author": author,
            "thumbnail": thumbnail,
        })

    return videos



def generate_html(tabs_data: list[dict]) -> str:
    """Generate the full HTML page with tabs and embedded videos."""

    # Build tab buttons
    tab_buttons = ""
    tab_contents = ""

    for i, tab in enumerate(tabs_data):
        active_class = " active" if i == 0 else ""
        tab_buttons += f'    <button class="tab-btn{active_class}" data-tab="tab-{i}">{tab["label"]}</button>\n'

        # Sort all videos by date (newest first)
        all_videos = []
        for channel in tab["channels"]:
            all_videos.extend(channel["videos"])
        all_videos.sort(key=lambda v: v["pub_date"], reverse=True)

        # Build video cards
        video_cards = ""
        for video in all_videos:
            pub_display = ""
            if video["published"]:
                try:
                    dt = datetime.fromisoformat(video["published"].replace("Z", "+00:00"))
                    pub_display = dt.strftime("%b %d, %Y")
                except ValueError:
                    pub_display = video["published"]

            video_cards += f"""
      <div class="video-card">
        <div class="video-embed">
          <iframe
            src="https://www.youtube.com/embed/{video['video_id']}"
            title="{video['title'].replace('"', '&quot;')}"
            frameborder="0"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowfullscreen>
          </iframe>
        </div>
        <div class="video-info">
          <h3>{video['title']}</h3>
          <p class="video-meta">{video['author']} &bull; {pub_display}</p>
        </div>
      </div>"""

        display = "block" if i == 0 else "none"
        tab_contents += f'    <div class="tab-content" id="tab-{i}" style="display: {display};">{video_cards}\n    </div>\n'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>My YouTube Feed</title>
  <style>
    * {{
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }}

    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: #0f0f0f;
      color: #f1f1f1;
      min-height: 100vh;
    }}

    header {{
      background: #1a1a1a;
      padding: 1rem 2rem;
      border-bottom: 1px solid #333;
    }}

    header h1 {{
      font-size: 1.5rem;
      font-weight: 600;
    }}

    .last-updated {{
      color: #aaa;
      font-size: 0.8rem;
      margin-top: 0.25rem;
    }}

    .tabs {{
      display: flex;
      gap: 0;
      background: #1a1a1a;
      padding: 0 2rem;
      border-bottom: 1px solid #333;
      overflow-x: auto;
    }}

    .tab-btn {{
      background: none;
      border: none;
      color: #aaa;
      padding: 0.75rem 1.5rem;
      font-size: 1rem;
      cursor: pointer;
      border-bottom: 3px solid transparent;
      transition: all 0.2s;
      white-space: nowrap;
    }}

    .tab-btn:hover {{
      color: #fff;
    }}

    .tab-btn.active {{
      color: #fff;
      border-bottom-color: #ff0000;
    }}

    .tab-content {{
      padding: 2rem;
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
      gap: 1.5rem;
    }}

    .video-card {{
      background: #1a1a1a;
      border-radius: 12px;
      overflow: hidden;
      transition: transform 0.2s;
    }}

    .video-card:hover {{
      transform: translateY(-2px);
    }}

    .video-embed {{
      position: relative;
      padding-bottom: 56.25%;
      height: 0;
      overflow: hidden;
    }}

    .video-embed iframe {{
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
    }}

    .video-info {{
      padding: 1rem;
    }}

    .video-info h3 {{
      font-size: 0.95rem;
      font-weight: 500;
      line-height: 1.3;
      margin-bottom: 0.5rem;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }}

    .video-meta {{
      color: #aaa;
      font-size: 0.8rem;
    }}

    @media (max-width: 768px) {{
      .tab-content {{
        grid-template-columns: 1fr;
        padding: 1rem;
      }}

      .tabs {{
        padding: 0 1rem;
      }}

      header {{
        padding: 1rem;
      }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>My YouTube Feed</h1>
    <p class="last-updated">Last updated: {datetime.now(timezone.utc).strftime("%B %d, %Y at %H:%M UTC")}</p>
  </header>

  <nav class="tabs">
{tab_buttons}  </nav>

  <main>
{tab_contents}  </main>

  <script>
    document.querySelectorAll('.tab-btn').forEach(btn => {{
      btn.addEventListener('click', () => {{
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.style.display = 'none');
        btn.classList.add('active');
        document.getElementById(btn.dataset.tab).style.display = 'grid';
      }});
    }});
  </script>
</body>
</html>"""

    return html


def main():
    script_dir = Path(__file__).parent
    config_path = script_dir / "channels.json"
    output_path = script_dir / "docs" / "index.html"

    print("Loading channels config...")
    with open(config_path) as f:
        config = json.load(f)

    tabs_data = []

    for tab in config["tabs"]:
        print(f"\nProcessing tab: {tab['label']}")
        tab_info = {"label": tab["label"], "channels": []}

        for channel in tab["channels"]:
            print(f"  Fetching: {channel['name']} ({channel['url']})")

            # Get channel ID from handle
            channel_id = channel.get("channel_id")
            if not channel_id:
                channel_id = get_channel_id_from_handle(channel["url"])

            if not channel_id:
                print(f"  ERROR: Could not resolve channel ID for {channel['name']}")
                tab_info["channels"].append({"name": channel["name"], "videos": []})
                continue

            print(f"  Channel ID: {channel_id}")

            # Fetch videos
            videos = fetch_rss_feed(channel_id)
            print(f"  Found {len(videos)} videos")
            tab_info["channels"].append({"name": channel["name"], "videos": videos})

        tabs_data.append(tab_info)

    # Generate HTML
    print("\nGenerating HTML...")
    html = generate_html(tabs_data)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html)
    print(f"Output written to: {output_path}")


if __name__ == "__main__":
    main()
