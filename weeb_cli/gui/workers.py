"""Asynchronous workers and background threads for AnimLoid GUI."""

import os
import threading
from PyQt5.QtCore import QThread, pyqtSignal, QObject, QSize, Qt, QUrl
from PyQt5.QtGui import QImage
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest

from weeb_cli.config import config
from weeb_cli.providers import get_provider
from weeb_cli.services.details import get_details
from weeb_cli.services.watch import get_streams
from weeb_cli.services.player import player
from weeb_cli.services.dependency_manager import dependency_manager
from weeb_cli.services.downloader import queue_manager

# QPixmap is a GUI-only resource in Qt.  Keep decoded images as QImage here,
# because QImage may safely be created and resized in a worker thread.  The
# view turns it into a QPixmap only after the signal reaches the GUI thread.
_IMAGE_CACHE: dict = {}
_IMAGE_CACHE_LOCK = threading.Lock()
_LIVE_WORKERS = set()


def start_background_worker(owner, worker):
    """Start a QThread without letting a view destroy it while it is running.

    A user can start another search or leave a detail page while a provider is
    still waiting for a network timeout.  Keeping a reference until `finished`
    prevents Qt's fatal "QThread: Destroyed while thread is still running"
    shutdown path.  It also lets old requests finish harmlessly instead of
    force-stopping them with QThread.terminate().
    """
    active_workers = getattr(owner, "_active_workers", None)
    if active_workers is None:
        active_workers = set()
        owner._active_workers = active_workers

    # A view can be closed or replaced before a slow provider request returns.
    # QThread must outlive its native thread in that case, so do not let Qt
    # destroy it as a child of the view.
    worker.setParent(None)
    active_workers.add(worker)
    _LIVE_WORKERS.add(worker)

    def clean_up():
        active_workers.discard(worker)
        _LIVE_WORKERS.discard(worker)
        worker.deleteLater()

    # QThread subclasses emit from run().  Force this housekeeping callback
    # onto the GUI queue as well; relying on AutoConnection differs between
    # Qt/PyQt builds and can otherwise execute Python cleanup in the worker.
    worker.finished.connect(clean_up, Qt.QueuedConnection)
    worker.start()
    return worker


class ImageLoaderWorker(QObject):
    """Event-driven poster loader that never starts a Python worker thread."""
    image_loaded = pyqtSignal(str, QImage)
    image_failed = pyqtSignal(str)

    def __init__(self, url: str, target_size=None, parent=None):
        super().__init__(parent)
        self.url = url
        self.target_size = target_size
        self._network = QNetworkAccessManager(self)
        self._reply = None

    def start(self):
        if not self.url:
            self.image_failed.emit(self.url or "")
            return

        width = self.target_size.width() if self.target_size else 0
        height = self.target_size.height() if self.target_size else 0
        cache_key = (self.url, width, height)
        with _IMAGE_CACHE_LOCK:
            cached_image = _IMAGE_CACHE.get(cache_key)
        if cached_image is not None:
            self.image_loaded.emit(self.url, cached_image)
            return

        request = QNetworkRequest(QUrl(self.url))
        request.setHeader(
            QNetworkRequest.UserAgentHeader,
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        )
        # Do not advertise AVIF: many Qt5 builds cannot decode it even when
        # the URL has a .jpg extension, so CDNs may return an image Qt shows
        # as an empty poster.
        request.setRawHeader(b"Accept", b"image/jpeg,image/png,image/*,*/*;q=0.8")
        self._reply = self._network.get(request)
        self._reply.finished.connect(self._finished)

    def _finished(self):
        reply = self._reply
        self._reply = None
        try:
            content = bytes(reply.readAll()) if reply else b""
            if not reply or reply.error() != reply.NoError or len(content) > 15 * 1024 * 1024:
                self.image_failed.emit(self.url)
                return
            image = QImage()
            if not content or not image.loadFromData(content):
                self.image_failed.emit(self.url)
                return
            width = self.target_size.width() if self.target_size else 0
            height = self.target_size.height() if self.target_size else 0
            if width > 0 and height > 0:
                image = image.scaled(QSize(width, height), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            with _IMAGE_CACHE_LOCK:
                _IMAGE_CACHE[(self.url, width, height)] = image
            self.image_loaded.emit(self.url, image)
        finally:
            if reply:
                reply.deleteLater()




class SearchWorker(QThread):
    results_ready = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, query: str, source_name: str = None):
        super().__init__()
        self.query = query
        self.source_name = source_name

    def run(self):
        try:
            # Each request owns its scraper instance.  Changing global config
            # from a QThread can race with a detail/stream request and make
            # its result come from a different source.
            from weeb_cli.services.scraper import Scraper
            results = Scraper(self.source_name).search(self.query)
            
            # Standardize results into dicts
            formatted_results = []
            if results:
                for r in results:
                    if hasattr(r, '__dict__'):
                        formatted_results.append({
                            "id": r.id,
                            "slug": r.id,
                            "title": getattr(r, "title", "Anime"),
                            "name": getattr(r, "title", "Anime"),
                            "type": getattr(r, "type", "series"),
                            "cover": getattr(r, "cover", None),
                            "year": getattr(r, "year", None),
                            "playable": getattr(r, "playable", None),
                        })
                    elif isinstance(r, dict):
                        formatted_results.append(r)
            
            self.results_ready.emit(formatted_results)
        except Exception as e:
            self.error_occurred.emit(str(e))


class DetailsWorker(QThread):
    details_ready = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, slug: str, source_name: str = None):
        super().__init__()
        self.slug = slug
        self.source_name = source_name

    def run(self):
        try:
            details = get_details(self.slug, self.source_name)
            if details:
                self.details_ready.emit(details)
            else:
                self.error_occurred.emit("Anime detayları alınamadı veya kaynak yanıt vermedi.")
        except Exception as e:
            self.error_occurred.emit(str(e))


class StreamsWorker(QThread):
    streams_ready = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, anime_id: str, episode_id: str, source_name: str = None):
        super().__init__()
        self.anime_id = anime_id
        self.episode_id = episode_id
        self.source_name = source_name

    def run(self):
        try:
            stream_data = get_streams(self.anime_id, self.episode_id, self.source_name)
            if stream_data and "data" in stream_data and "links" in stream_data["data"]:
                links = stream_data["data"]["links"]
                self.streams_ready.emit(links)
            else:
                self.error_occurred.emit("Yayın bağlantısı bulunamadı.")
        except Exception as e:
            self.error_occurred.emit(str(e))


class PlayWorker(QThread):
    play_finished = pyqtSignal(bool)

    def __init__(self, url: str, title: str = None, headers: dict = None, anime_title: str = None, episode_number: int = None, total_episodes: int = None):
        super().__init__()
        self.url = url
        self.title = title
        self.headers = headers
        self.anime_title = anime_title
        self.episode_number = episode_number
        self.total_episodes = total_episodes

    def run(self):
        try:
            res = player.play(
                url=self.url,
                title=self.title,
                headers=self.headers,
                anime_title=self.anime_title,
                episode_number=self.episode_number,
                total_episodes=self.total_episodes
            )
            self.play_finished.emit(res)
        except Exception:
            self.play_finished.emit(False)


class DependencyCheckWorker(QThread):
    status_ready = pyqtSignal(dict)

    def run(self):
        deps = ["mpv", "ffmpeg", "yt-dlp", "aria2"]
        results = {}
        for dep in deps:
            path = dependency_manager.check_dependency(dep)
            results[dep] = {
                "installed": path is not None,
                "path": path or ""
            }
        self.status_ready.emit(results)


class InstallDependencyWorker(QThread):
    install_finished = pyqtSignal(str, bool)

    def __init__(self, dep_name: str):
        super().__init__()
        self.dep_name = dep_name

    def run(self):
        try:
            res = dependency_manager.install_dependency(self.dep_name)
            self.install_finished.emit(self.dep_name, bool(res))
        except Exception:
            self.install_finished.emit(self.dep_name, False)
