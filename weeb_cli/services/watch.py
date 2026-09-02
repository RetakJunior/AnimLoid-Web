from typing import Optional, Dict, List
from weeb_cli.services.scraper import Scraper, scraper
from weeb_cli.services.logger import debug


def get_streams(anime_id: str, episode_id: str, source_name: Optional[str] = None) -> Optional[Dict]:
    client = Scraper(source_name) if source_name else scraper
    debug(f"[WATCH] Getting streams for {anime_id} - {episode_id}")
    streams = client.get_streams(anime_id, episode_id)
    debug(f"[WATCH] Scraper returned {len(streams) if streams else 0} streams")
    
    if not streams:
        debug(f"[WATCH] No streams found, last_error: {client.last_error}")
        return None
    
    result = {
        "data": {
            "links": [
                {
                    "url": s.url,
                    "quality": s.quality,
                    "server": s.server,
                    # Some providers return short-lived HLS links that only
                    # work with the originating player page as Referer.  The
                    # old GUI bridge discarded these headers, so a stream
                    # looked valid in the provider but failed as soon as MPV
                    # opened it.
                    "headers": dict(s.headers or {}),
                }
                for s in streams
            ]
        }
    }
    debug(f"[WATCH] Returning {len(result['data']['links'])} links")
    return result
