import json
import sys
from dataclasses import asdict
from pathlib import Path
from urllib.parse import parse_qs, urlparse

CLONE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CLONE_ROOT))

from weeb_cli.providers import list_providers
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
                return _json_response(self, {
                    "error": "Bu provider sonuç döndürmedi.",
                    "provider": provider_name,
                    "detail": scraper.last_error,
                }, 502)
            return _json_response(self, {
                "results": [_serialize(item) for item in results],
                "provider": provider_name,
                "fallback": False,
            })

        if action == "details":
            anime_id = query.get("id", "").strip()
            if not anime_id:
                return _json_response(self, {"error": "Anime kimliği eksik."}, 400)
            details = scraper.get_details(anime_id)
            if not details:
                return _json_response(self, {"error": "Anime detayları alınamadı.", "detail": scraper.last_error}, 502)
            return _json_response(self, {"details": _serialize(details), "provider": provider_name})

        return _json_response(self, {"error": "Geçersiz action."}, 400)

    def log_message(self, *_args):
        return
