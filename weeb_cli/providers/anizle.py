import re
import json
from typing import List, Optional, Dict, Any
from difflib import SequenceMatcher
from concurrent.futures import ThreadPoolExecutor, as_completed

from weeb_cli.providers.base import (
    BaseProvider,
    AnimeResult,
    AnimeDetails,
    Episode,
    StreamLink
)
from weeb_cli.providers.registry import register_provider

try:
    from curl_cffi import requests as curl_requests
    HAS_CURL_CFFI = True
except ImportError:
    import requests as std_requests
    HAS_CURL_CFFI = False

BASE_URL = "https://anizle.org"
API_BASE_URL = "https://anizle.org"
ANIME_LIST_URL = f"{BASE_URL}/getAnimeListForSearch"
PLAYER_BASE_URL = "https://anizmplayer.com"

_anime_database: List[Dict[str, Any]] = []
_database_loaded: bool = False
_session = None
_poster_cache: Dict[int, str] = {}

DEFAULT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
}


def _get_session():
    global _session
    if _session is None:
        if HAS_CURL_CFFI:
            _session = curl_requests.Session(impersonate="chrome120")
        else:
            _session = std_requests.Session()
    return _session


def _http_get(url: str, headers: Dict = None, timeout: int = 60):
    session = _get_session()
    h = {**DEFAULT_HEADERS}
    if headers:
        h.update(headers)
    
    try:
        return session.get(url, headers=h, timeout=timeout)
    except Exception:
        return None


def _http_post(url: str, headers: Dict = None, data: Dict = None, timeout: int = 60):
    session = _get_session()
    h = {**DEFAULT_HEADERS, "X-Requested-With": "XMLHttpRequest", "Accept": "application/json"}
    if headers:
        h.update(headers)
    
    try:
        return session.post(url, headers=h, data=data, timeout=timeout)
    except Exception:
        return None


def _strip_html(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'&[a-zA-Z]+;', ' ', text)
    text = re.sub(r'&#\d+;', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def _load_database() -> List[Dict[str, Any]]:
    global _anime_database, _database_loaded
    
    if _database_loaded:
        return _anime_database
    
    try:
        response = _http_get(ANIME_LIST_URL, timeout=120)
        if response and response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                _anime_database = data
                _database_loaded = True
    except Exception:
        pass
    
    return _anime_database


def _resolve_anilist_posters(anime_items: List[Dict[str, Any]]) -> None:
    """Populate a poster cache from AniList in one bounded request.

    Aniizle currently serves ``anizm.pro/uploads/img`` behind a bot check,
    which returns an HTML 403 page to Qt instead of an image.  Its search
    payload already includes MAL ids, so AniList gives us a stable image CDN
    without doing one slow request per result.
    """
    ids = []
    for item in anime_items:
        try:
            mal_id = int(item.get("info_malid") or 0)
        except (TypeError, ValueError):
            continue
        if mal_id and mal_id not in _poster_cache:
            ids.append(mal_id)

    if not ids:
        return

    query = (
        "query ($ids: [Int]) { Page(perPage: 50) { "
        "media(idMal_in: $ids, type: ANIME) { "
        "idMal coverImage { large medium } } } }"
    )
    try:
        # curl_cffi and requests both accept json=, but _http_post is kept
        # form-oriented for Aniizle's own endpoints.  Send this request here
        # directly so the GraphQL body remains valid JSON.
        session = _get_session()
        headers = {**DEFAULT_HEADERS, "Content-Type": "application/json"}
        response = session.post(
            "https://graphql.anilist.co",
            headers=headers,
            json={"query": query, "variables": {"ids": ids[:50]}},
            timeout=10,
        )
        if not response or response.status_code != 200:
            return
        media = response.json().get("data", {}).get("Page", {}).get("media", [])
        for item in media:
            mal_id = item.get("idMal")
            cover = (item.get("coverImage") or {}).get("large") or (item.get("coverImage") or {}).get("medium")
            if mal_id and cover:
                _poster_cache[int(mal_id)] = cover
    except Exception:
        # Covers are optional UI data.  Never make a provider search fail if
        # the public image mirror happens to be unavailable.
        return


def _unpack_js(p: str, a: int, c: int, k: List[str]) -> str:
    def e(c: int, a: int) -> str:
        first = '' if c < a else e(c // a, a)
        c = c % a
        if c > 35:
            second = chr(c + 29)
        elif c > 9:
            second = chr(c + 87)
        else:
            second = str(c)
        return first + second
    
    d = {}
    temp_c = c
    while temp_c:
        temp_c -= 1
        key = e(temp_c, a)
        d[key] = k[temp_c] if temp_c < len(k) and k[temp_c] else key
    
    def replace_func(match):
        return d.get(match.group(0), match.group(0))
    
    return re.sub(r'\b\w+\b', replace_func, p)


def _extract_fireplayer_id(player_html: str) -> Optional[str]:
    eval_match = re.search(
        r"eval\(function\(p,a,c,k,e,d\)\{.*?\}return p\}\('(.*?)',(\d+),(\d+),'([^']+)'\.split\('\|'\),0,\{\}\)\)",
        player_html, re.S
    )
    
    if eval_match:
        p = eval_match.group(1)
        a = int(eval_match.group(2))
        c = int(eval_match.group(3))
        k = eval_match.group(4).split('|')
        
        try:
            decoded = _unpack_js(p, a, c, k)
            id_match = re.search(r'FirePlayer\s*\(\s*["\']([a-f0-9]{32})["\']', decoded)
            if id_match:
                return id_match.group(1)
        except Exception:
            pass
    
    fp_direct = re.search(r'FirePlayer\s*\(["\']([a-f0-9]{32})["\']', player_html)
    if fp_direct:
        return fp_direct.group(1)
    
    return None


@register_provider("anizle", lang="tr", region="TR")
class AnizleProvider(BaseProvider):
    
    def __init__(self):
        super().__init__()
    
    def search(self, query: str) -> List[AnimeResult]:
        database = _load_database()
        if not database:
            return []
        
        matches = []
        for anime in database:
            scores = [
                self._similarity(query, anime.get("info_title", "")),
                self._similarity(query, anime.get("info_titleoriginal", "")),
                self._similarity(query, anime.get("info_titleenglish", "")),
            ]
            max_score = max(scores)
            
            if max_score > 0.3:
                year_str = anime.get("info_year", "")
                year = int(year_str) if year_str and str(year_str).isdigit() else None
                
                matches.append((max_score, anime, year))
        
        matches.sort(key=lambda x: x[0], reverse=True)
        matches = matches[:20]
        _resolve_anilist_posters([anime for _, anime, _ in matches])
        return [
            AnimeResult(
                id=anime.get("info_slug", ""),
                title=anime.get("info_title", ""),
                cover=self._get_poster_url(anime.get("info_poster", ""), anime.get("info_malid")),
                year=year,
            )
            for _, anime, year in matches
        ]
    
    def get_details(self, anime_id: str) -> Optional[AnimeDetails]:
        database = _load_database()
        anime_data = None
        
        for anime in database:
            if anime.get("info_slug") == anime_id:
                anime_data = anime
                break
        
        episodes = self.get_episodes(anime_id)
        
        if not anime_data:
            return AnimeDetails(
                id=anime_id,
                title=anime_id.replace("-", " ").title(),
                episodes=episodes,
                total_episodes=len(episodes)
            )

        _resolve_anilist_posters([anime_data])

        categories = []
        for cat in anime_data.get("categories", []):
            if isinstance(cat, dict) and "tag_title" in cat:
                categories.append(cat["tag_title"])
        
        year_str = anime_data.get("info_year", "")
        year = int(year_str) if year_str and str(year_str).isdigit() else None
        
        description = _strip_html(anime_data.get("info_summary", ""))
        
        return AnimeDetails(
            id=anime_id,
            title=anime_data.get("info_title", ""),
            description=description,
            cover=self._get_poster_url(anime_data.get("info_poster", ""), anime_data.get("info_malid")),
            genres=categories,
            year=year,
            episodes=episodes,
            total_episodes=len(episodes)
        )
    
    def get_episodes(self, anime_id: str) -> List[Episode]:
        url = f"{BASE_URL}/{anime_id}"
        response = _http_get(url)
        
        if not response or response.status_code != 200:
            return []
        
        html = response.text
        episodes = []
        seen = set()
        
        pattern1 = r'href="/?([^"]+?-bolum[^"]*)"[^>]*data-order="(\d+)"[^>]*>([^<]+)'
        matches1 = re.findall(pattern1, html, re.IGNORECASE)
        
        for ep_slug, order, title in matches1:
            ep_slug = ep_slug.strip('/').replace('https://anizm.pro/', '').replace('https://anizle.org/', '')
            try:
                order_num = int(order)
                if order_num not in seen:
                    seen.add(order_num)
                    episodes.append(Episode(
                        id=ep_slug,
                        number=order_num,
                        title=title.strip()
                    ))
            except ValueError:
                pass
        
        pattern2 = r'href="/?([^"]+?-(\d+)-bolum[^"]*)"[^>]*>([^<]*)'
        matches2 = re.findall(pattern2, html, re.IGNORECASE)
        
        for ep_slug, ep_num, title in matches2:
            ep_slug = ep_slug.strip('/').replace('https://anizm.pro/', '').replace('https://anizle.org/', '')
            try:
                order_num = int(ep_num)
                if order_num not in seen:
                    seen.add(order_num)
                    final_title = title.strip() if title.strip() else f"{ep_num}. Bölüm"
                    episodes.append(Episode(
                        id=ep_slug,
                        number=order_num,
                        title=final_title
                    ))
            except ValueError:
                pass
        
        episodes.sort(key=lambda x: x.number)
        return episodes
    
    def get_streams(self, anime_id: str, episode_id: str) -> List[StreamLink]:
        translators = self._get_translators(episode_id)
        if not translators:
            return []
        
        all_videos = []
        for tr in translators:
            videos = self._get_translator_videos(tr["url"])
            for v in videos:
                all_videos.append({
                    "url": v["url"],
                    "name": v["name"],
                    "fansub": tr["name"]
                })
        
        if not all_videos:
            return []
        
        streams = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(self._process_video, v): v for v in all_videos[:8]}
            for future in as_completed(futures, timeout=60):
                try:
                    result = future.result(timeout=30)
                    if result:
                        streams.append(result)
                except Exception:
                    pass
        
        return streams
    
    def _similarity(self, query: str, text: str) -> float:
        if not text:
            return 0.0
        q = query.lower()
        t = text.lower()
        if q == t:
            return 1.0
        if q in t:
            return 0.9
        return SequenceMatcher(None, q, t).ratio()
    
    def _get_poster_url(self, poster: str, mal_id: Any = None) -> str:
        try:
            cached = _poster_cache.get(int(mal_id or 0), "")
        except (TypeError, ValueError):
            cached = ""
        if cached:
            return cached

        # Do not return Aniizle's current image host as a fallback: it serves
        # a Cloudflare 403 HTML page to Qt, yielding a permanently blank card.
        return poster if poster.startswith("http") else ""
    
    def _get_translators(self, episode_slug: str) -> List[Dict[str, str]]:
        clean_slug = episode_slug.strip('/')
        if clean_slug.startswith("http"):
            url = clean_slug
        else:
            url = f"{BASE_URL}/{clean_slug}"
        
        response = _http_get(url)
        if not response or response.status_code != 200:
            return []
        
        html = response.text
        translators = []
        pattern = r'translator="([^"]+)"[^>]*data-fansub-name="([^"]*)"'
        matches = re.findall(pattern, html)
        
        seen = set()
        for tr_url, fansub in matches:
            if tr_url not in seen:
                seen.add(tr_url)
                translators.append({"url": tr_url, "name": fansub or "Fansub"})
        
        return translators
    
    def _get_translator_videos(self, translator_url: str) -> List[Dict[str, str]]:
        response = _http_get(
            translator_url,
            headers={
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "application/json",
                "Referer": "https://anizle.co/",
            }
        )
        
        if not response or response.status_code != 200:
            return []
        
        try:
            data = response.json()
            html = data.get("data", "")
            
            videos = []
            pattern = r'video="([^"]+)"[^>]*data-video-name="([^"]*)"'
            matches = re.findall(pattern, html)
            
            for video_url, video_name in matches:
                videos.append({"url": video_url, "name": video_name or "Player"})
            
            if not videos:
                pattern2 = r'data-video-name="([^"]*)"[^>]*video="([^"]+)"'
                matches2 = re.findall(pattern2, html)
                for video_name, video_url in matches2:
                    videos.append({"url": video_url, "name": video_name or "Player"})
            
            return videos
        except Exception:
            return []
    
    def _process_video(self, video_info: Dict[str, str]) -> Optional[StreamLink]:
        try:
            video_url = video_info["url"]
            fansub = video_info.get("fansub", "Fansub")
            name = video_info.get("name", "Player")
            
            response = _http_get(
                video_url,
                headers={
                    "X-Requested-With": "XMLHttpRequest",
                    "Accept": "application/json",
                    "Referer": "https://anizle.co/",
                }
            )
            
            if not response or response.status_code != 200:
                return None
            
            data = response.json()
            player_html = data.get("player", "")
            
            iframe_src_match = re.search(r'src=[\"\']([^\"\']+)[\"\']', player_html)
            if not iframe_src_match:
                return None
            
            player_page_url = iframe_src_match.group(1)
            if player_page_url.startswith("//"):
                player_page_url = "https:" + player_page_url
            
            # Fetch player frame page with Referer
            player_response = _http_get(
                player_page_url,
                headers={"Referer": "https://anizle.co/"}
            )
            
            if not player_response or player_response.status_code != 200:
                return None
            
            p_text = player_response.text

            # Aniizle's current player does not expose a media URL in the
            # page.  It embeds a FirePlayer id and the browser POSTs that id
            # to the player API to obtain a short-lived HLS URL.  The former
            # provider only looked for static <source>/<iframe> tags, so every
            # current Aniizle stream was incorrectly reported as unavailable.
            fireplayer_id = _extract_fireplayer_id(p_text)
            if fireplayer_id:
                stream = self._get_fireplayer_stream(
                    fireplayer_id,
                    player_response.url or player_page_url,
                    fansub,
                    name,
                )
                if stream:
                    return stream
            
            # Check for direct video sources (mp4, m3u8)
            direct_src = re.findall(r'(?:source|file)\s*(?::|=)\s*[\"\'](https?://[^\"\']+\.(?:mp4|m3u8)[^\"\']*)[\"\']', p_text, re.IGNORECASE)
            if direct_src:
                return StreamLink(url=direct_src[0], quality="auto", server=f"{fansub} - {name}")
            
            # Check for external embeds like Sibnet, Sendvid, Vidmoly, MP4Upload
            external_iframes = re.findall(r'src=[\"\'](https?://(?:video\.sibnet\.ru|sendvid\.com|vidmoly\.[a-z]+|mp4upload\.com|dood\.[a-z]+|streamtape\.com|uqload\.[a-z]+)/[^\"\']+)[\"\']', p_text)
            if external_iframes:
                return StreamLink(url=external_iframes[0], quality="auto", server=f"{fansub} - {name}")
            
            # Check for Sibnet og:url
            sibnet_match = re.search(r'property="og:url"\s+content="([^"]*sibnet\.ru[^"]*)"', p_text)
            if sibnet_match:
                return StreamLink(url=sibnet_match.group(1), quality="auto", server=f"{fansub} - {name} (Sibnet)")

            # Check for generic iframe src inside player page
            inner_iframe = re.search(r'<iframe[^>]+src=[\"\'](https?://[^\"\']+)[\"\']', p_text)
            if inner_iframe:
                return StreamLink(url=inner_iframe.group(1), quality="auto", server=f"{fansub} - {name}")

            return None
            
        except Exception:
            return None

    def _get_fireplayer_stream(
        self, player_id: str, referer: str, fansub: str, player_name: str
    ) -> Optional[StreamLink]:
        """Resolve Aniizle's current FirePlayer API response to an HLS URL."""
        endpoint = f"{PLAYER_BASE_URL}/player/index.php?data={player_id}&do=getVideo"
        response = _http_post(
            endpoint,
            headers={
                "Referer": referer,
                "Origin": PLAYER_BASE_URL,
            },
            data={"hash": player_id, "r": referer},
            timeout=20,
        )
        if not response or response.status_code != 200:
            return None

        try:
            data = response.json()
        except (ValueError, TypeError):
            return None

        stream_url = data.get("videoSource") or data.get("securedLink")
        if not stream_url:
            sources = data.get("videoSources") or []
            if sources and isinstance(sources[0], dict):
                stream_url = sources[0].get("file")
        if not stream_url or not isinstance(stream_url, str):
            return None

        return StreamLink(
            url=stream_url.replace("\\/", "/"),
            quality="auto",
            server=f"{fansub} - {player_name}",
            headers={"Referer": referer},
        )
