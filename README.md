# YouTube RSS Feed Site

A personal static site that aggregates YouTube videos from your favorite channels, organized by tabs. Updated hourly via GitHub Actions and hosted on GitHub Pages.

## How It Works

1. `channels.json` defines your channels organized into tabs
2. `build.py` fetches YouTube RSS feeds and generates a static HTML page with embedded players
3. GitHub Actions runs the build every hour and deploys to GitHub Pages

## Adding Channels

Edit `channels.json` to add new tabs or channels:

```json
{
  "tabs": [
    {
      "label": "Tab Name",
      "channels": [
        {
          "name": "Channel Display Name",
          "url": "https://www.youtube.com/@ChannelHandle"
        }
      ]
    }
  ]
}
```

## Local Development

Run the build script locally to preview:

```bash
python build.py
open docs/index.html
```

## Setup

1. Create a new GitHub repository
2. Push this project to it
3. Go to Settings > Pages > Source: GitHub Actions
4. The site will build and deploy automatically

## Schedule

The site rebuilds every hour. You can also trigger a manual build from the Actions tab.
