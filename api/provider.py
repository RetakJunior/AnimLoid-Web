import json
import sys
import urllib.request
import requests
from dataclasses import asdict
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

CLONE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CLONE_ROOT))

from weeb_cli.providers import list_providers
from weeb_cli.providers.base import AnimeResult, AnimeDetails, Episode
from weeb_cli.services.scraper import Scraper


def _json_response(handler, payload, status=200):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _query(handler):
    return {key: values[0] for key, values in parse_qs(urlparse(handler.path).query).items()}


def _serialize(value):
    if value is None:
        return None
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if hasattr(value, "__dataclass_fields__"):
        return {key: _serialize(item) for key, item in asdict(value).items()}
    return value


def _anilist_search(term):
    response = requests.get("https://kitsu.io/api/edge/anime", params={"filter[text]": term, "page[limit]": 20}, headers={"Accept": "application/vnd.api+json", "User-Agent": "AnimLoid-Web"}, timeout=12)
    response.raise_for_status()
    media = response.json().get("data", [])
    return [AnimeResult(
        id=f"kitsu:{item['id']}",
        title=(item.get("attributes") or {}).get("canonicalTitle") or "Untitled anime",
        type=((item.get("attributes") or {}).get("subtype") or "tv").lower(),
        cover=((item.get("attributes") or {}).get("posterImage") or {}).get("large"),
        year=((item.get("attributes") or {}).get("startDate") or "")[:4] or None,
        playable=False,
    ) for item in media]


def _anilist_details(anime_id):
    response = requests.get(f"https://kitsu.io/api/edge/anime/{quote(anime_id)}", headers={"Accept": "application/vnd.api+json", "User-Agent": "AnimLoid-Web"}, timeout=12)
    response.raise_for_status()
    item = response.json().get("data", {}).get("attributes") or {}
    title = item.get("canonicalTitle") or "Anime"
    episode_count = item.get("episodeCount") or 0
    episodes = [Episode(id=f"kitsu:{anime_id}:{number}", number=number, title=f"Bölüm {number}") for number in range(1, episode_count + 1)]
    return AnimeDetails(id=f"kitsu:{anime_id}", title=title, description=item.get("synopsis"), cover=(item.get("posterImage") or {}).get("large"), year=(item.get("startDate") or "")[:4] or None, episodes=episodes, total_episodes=len(episodes))


class handler(__import__("http.server", fromlist=["BaseHTTPRequestHandler"]).BaseHTTPRequestHandler):
    def do_GET(self):
        query = _query(self)
        action = query.get("action", "search")
        provider_name = query.get("provider", "animecix")
        scraper = Scraper(provider_name)

        if action == "providers":
            return _json_response(self, {"providers": list_providers()})

        if action == "search":
            term = query.get("q", "").strip()
            if len(term) < 2:
                return _json_response(self, {"error": "En az 2 karakter yaz."}, 400)
            results = scraper.search(term)
            if not results:
                try:
                    results = _anilist_search(term)
                    return _json_response(self, {"results": [_serialize(item) for item in results], "provider": f"{provider_name} / AniList katalog fallback", "fallback": True})
                except Exception as error:
                    return _json_response(self, {"error": "Provider ve katalog fallback yanıt vermedi.", "provider": provider_name, "detail": str(error) }, 502)
            return _json_response(self, {
                "results": [_serialize(item) for item in results],
                "provider": provider_name,
                "fallback": False,
            })

        if action == "details":
            anime_id = query.get("id", "").strip()
            if not anime_id:
                return _json_response(self, {"error": "Anime kimliği eksik."}, 400)
            if anime_id.startswith("kitsu:"):
                try:
                    details = _anilist_details(anime_id.split(":", 1)[1])
                except Exception as error:
                    return _json_response(self, {"error": "Katalog detayları alınamadı.", "detail": str(error)}, 502)
            else:
                details = scraper.get_details(anime_id)
            if not details:
                return _json_response(self, {"error": "Anime detayları alınamadı.", "detail": scraper.last_error}, 502)
            return _json_response(self, {"details": _serialize(details), "provider": provider_name})

        return _json_response(self, {"error": "Geçersiz action."}, 400)

    def log_message(self, *_args):
        return
