"""Detail View for AnimLoid GUI."""

import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QScrollArea, QFrame, QListWidget, QListWidgetItem, 
    QDialog, QComboBox, QMessageBox, QProgressBar
)
from PyQt5.QtCore import Qt, pyqtSignal, QThreadPool, QSize
from PyQt5.QtGui import QPixmap, QCursor, QFont

from weeb_cli.config import config
from weeb_cli.services.progress import progress_tracker
from weeb_cli.services.downloader import queue_manager
from weeb_cli.gui.workers import (
    DetailsWorker, StreamsWorker, PlayWorker, ImageLoaderWorker,
    start_background_worker,
)


class ServerSelectDialog(QDialog):
    def __init__(self, streams, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Yayın Sunucusu Seç")
        self.setFixedSize(380, 200)
        self.setStyleSheet("""
            QDialog {
                background-color: #121316;
                border: 1px solid #292b30;
                border-radius: 10px;
            }
            QLabel {
                color: #FFFFFF;
                font-size: 13px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        info_label = QLabel("Kullanılabilir sunucular arasından seçim yapın:")
        layout.addWidget(info_label)

        self.server_combo = QComboBox()
        for s in streams:
            server_name = s.get("server", "Bilinmeyen Sunucu").upper()
            quality = s.get("quality", "Auto")
            self.server_combo.addItem(f"{server_name} ({quality})", s)
        layout.addWidget(self.server_combo)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("İptal")
        cancel_btn.setProperty("class", "SecondaryButton")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        play_btn = QPushButton("Oynat")
        play_btn.setProperty("class", "PrimaryButton")
        play_btn.clicked.connect(self.accept)
        btn_layout.addWidget(play_btn)

        layout.addLayout(btn_layout)

    def get_selected_stream(self):
        return self.server_combo.currentData()


class EpisodeRowWidget(QFrame):
    play_requested = pyqtSignal(dict)
    download_requested = pyqtSignal(dict)

    def __init__(self, episode_data: dict, is_watched: bool = False):
        super().__init__()
        self.episode_data = episode_data
        self.setStyleSheet("""
            QFrame {
                background-color: #17191d;
                border: 1px solid #303238;
                border-radius: 8px;
                padding: 4px;
            }
            QFrame:hover {
                border-color: #3b82f6;
                background-color: #202436;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(12)

        # Watched Status Icon
        status_icon = QLabel("✓" if is_watched else "●")
        if is_watched:
            status_icon.setStyleSheet("color: #10B981; font-size: 16px; font-weight: bold;")
            status_icon.setToolTip("İzlendi")
        else:
            status_icon.setStyleSheet("color: #64748B; font-size: 12px;")
            status_icon.setToolTip("İzlenmedi")
        layout.addWidget(status_icon)

        # Episode Number & Title
        ep_num = episode_data.get("number") or episode_data.get("ep_num") or 1
        ep_title = episode_data.get("title") or episode_data.get("name") or f"Bölüm {ep_num}"
        
        label_text = f"<b>Bölüm {ep_num}</b>: {ep_title}"
        self.title_label = QLabel(label_text)
        self.title_label.setStyleSheet("color: #F8FAFC; font-size: 13px;")
        layout.addWidget(self.title_label, stretch=1)

        # Download Button
        dl_btn = QPushButton("⬇ İndir")
        dl_btn.setProperty("class", "SecondaryButton")
        dl_btn.setCursor(QCursor(Qt.PointingHandCursor))
        dl_btn.clicked.connect(lambda: self.download_requested.emit(self.episode_data))
        layout.addWidget(dl_btn)

        # Play Button
        play_btn = QPushButton("▶ İzle")
        play_btn.setProperty("class", "PrimaryButton")
        play_btn.setCursor(QCursor(Qt.PointingHandCursor))
        play_btn.clicked.connect(lambda: self.play_requested.emit(self.episode_data))
        layout.addWidget(play_btn)


class DetailView(QWidget):
    back_clicked = pyqtSignal()
    episode_watched = pyqtSignal(str, int)

    def __init__(self):
        super().__init__()
        self.thread_pool = QThreadPool.globalInstance()
        self.current_anime = None
        self.details_data = None
        self.details_worker = None
        self.streams_worker = None
        self.play_worker = None
        self._expected_cover_urls = set()
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 16, 24, 20)
        main_layout.setSpacing(14)

        # Top Navigation Row
        top_row = QHBoxLayout()
        self.back_btn = QPushButton("← Geri Dön")
        self.back_btn.setProperty("class", "SecondaryButton")
        self.back_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.back_btn.clicked.connect(self.back_clicked.emit)
        top_row.addWidget(self.back_btn)

        self.header_title = QLabel("Anime Detayları")
        self.header_title.setStyleSheet("color: #FFFFFF; font-size: 16px; font-weight: bold;")
        top_row.addWidget(self.header_title)
        top_row.addStretch()

        main_layout.addLayout(top_row)

        # Loading Indicator
        self.loading_bar = QProgressBar()
        self.loading_bar.setRange(0, 0)
        self.loading_bar.setFixedHeight(3)
        self.loading_bar.hide()
        main_layout.addWidget(self.loading_bar)

        # Scroll Content
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(16)

        # Header Info Card
        self.header_card = QFrame()
        self.header_card.setProperty("class", "Card")
        header_card_layout = QHBoxLayout(self.header_card)
        header_card_layout.setContentsMargins(16, 16, 16, 16)
        header_card_layout.setSpacing(20)

        # Poster Image
        self.poster_label = QLabel()
        self.poster_label.setFixedSize(160, 230)
        self.poster_label.setAlignment(Qt.AlignCenter)
        self.poster_label.setStyleSheet("background-color: #17191d; border-radius: 6px; color: #737780;")
        self.poster_label.setText("Yükleniyor...")
        self.poster_label.setScaledContents(True)
        header_card_layout.addWidget(self.poster_label)

        # Info Section
        info_layout = QVBoxLayout()
        info_layout.setSpacing(8)

        self.title_label = QLabel("Anime Başlığı")
        self.title_label.setStyleSheet("color: #FFFFFF; font-size: 20px; font-weight: bold;")
        self.title_label.setWordWrap(True)
        info_layout.addWidget(self.title_label)

        # Meta tags
        self.tags_layout = QHBoxLayout()
        self.tags_layout.setSpacing(6)
        info_layout.addLayout(self.tags_layout)

        # Synopsis
        self.desc_label = QLabel("Açıklama yükleniyor...")
        self.desc_label.setStyleSheet("color: #CBD5E1; font-size: 13px; line-height: 1.4;")
        self.desc_label.setWordWrap(True)
        self.desc_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        info_layout.addWidget(self.desc_label, stretch=1)

        header_card_layout.addLayout(info_layout, stretch=1)
        self.content_layout.addWidget(self.header_card)

        # Episodes Section Title
        ep_header = QHBoxLayout()
        self.episodes_count_label = QLabel("Bölümler")
        self.episodes_count_label.setStyleSheet("color: #FFFFFF; font-size: 16px; font-weight: bold;")
        ep_header.addWidget(self.episodes_count_label)
        ep_header.addStretch()

        self.content_layout.addLayout(ep_header)

        # Episodes Container
        self.episodes_container = QVBoxLayout()
        self.episodes_container.setSpacing(8)
        self.content_layout.addLayout(self.episodes_container)

        self.scroll_area.setWidget(self.content_widget)
        main_layout.addWidget(self.scroll_area, stretch=1)

    def load_anime(self, anime_data: dict):
        self.current_anime = anime_data
        self.details_data = None
        self._expected_cover_urls.clear()
        title = anime_data.get("title") or anime_data.get("name") or "Anime"
        self.title_label.setText(title)
        self.header_title.setText(title)
        self.desc_label.setText("Detaylar yükleniyor...")
        self.poster_label.setText("Yükleniyor...")
        self.loading_bar.show()

        # Clear tags
        while self.tags_layout.count():
            item = self.tags_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Clear episodes
        while self.episodes_container.count():
            item = self.episodes_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Load cover immediately if available
        cover_url = anime_data.get("cover")
        if cover_url:
            self._expected_cover_urls.add(cover_url)
            self._image_worker1 = ImageLoaderWorker(cover_url, self.poster_label.size(), parent=self)
            self._image_worker1.image_loaded.connect(self._on_image_loaded)
            self._image_worker1.start()

        # Fetch details
        slug = anime_data.get("slug") or anime_data.get("id")
        source = config.get("scraping_source", "animecix")

        self.details_worker = DetailsWorker(slug, source)
        self.details_worker.details_ready.connect(self._on_details_ready, Qt.QueuedConnection)
        self.details_worker.error_occurred.connect(self._on_details_error, Qt.QueuedConnection)
        start_background_worker(self, self.details_worker)

    def _on_image_loaded(self, url, image):
        if url not in self._expected_cover_urls:
            return
        if not image.isNull():
            self.poster_label.setPixmap(QPixmap.fromImage(image))

    def _on_details_ready(self, details: dict):
        if self.sender() is not self.details_worker:
            return
        self.loading_bar.hide()
        self.details_data = details

        # Description
        desc = details.get("description") or details.get("synopsis") or "Açıklama bulunmuyor."
        self.desc_label.setText(desc)

        # Tags
        while self.tags_layout.count():
            item = self.tags_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        year = details.get("year")
        if year:
            yb = QLabel(f"📅 {year}")
            yb.setStyleSheet("background-color: #202226; color: #a1a1aa; border-radius: 4px; padding: 2px 8px; font-size: 11px;")
            self.tags_layout.addWidget(yb)

        status = details.get("status")
        if status:
            sb = QLabel(f"● {status}")
            sb.setStyleSheet("background-color: rgba(16, 185, 129, 0.2); color: #34D399; border-radius: 4px; padding: 2px 8px; font-size: 11px; font-weight: bold;")
            self.tags_layout.addWidget(sb)

        genres = details.get("genres", [])
        for g in genres[:4]:
            gb = QLabel(str(g))
            gb.setStyleSheet("background-color: #172554; color: #93c5fd; border-radius: 4px; padding: 2px 8px; font-size: 11px;")
            self.tags_layout.addWidget(gb)

        self.tags_layout.addStretch()

        # Update cover if details had a better one
        cover_url = details.get("cover")
        if cover_url:
            self._expected_cover_urls.add(cover_url)
            self._image_worker2 = ImageLoaderWorker(cover_url, self.poster_label.size(), parent=self)
            self._image_worker2.image_loaded.connect(self._on_image_loaded)
            self._image_worker2.start()

        # Episodes
        episodes = details.get("episodes", [])
        self.episodes_count_label.setText(f"Bölümler ({len(episodes)} Bölüm)")

        if not episodes:
            unavailable = QLabel(
                "Bu içerik için seçili kaynakta izlenebilir yayın bulunamadı. "
                "Arama ekranından başka bir kaynak deneyebilirsiniz."
            )
            unavailable.setWordWrap(True)
            unavailable.setStyleSheet("color: #9ca3af; padding: 12px 4px;")
            self.episodes_container.addWidget(unavailable)
            return

        slug = details.get("slug") or details.get("id") or self.current_anime.get("slug")
        progress = progress_tracker.get_anime_progress(slug)
        completed_eps = set(progress.get("completed", []))

        for ep in episodes:
            ep_num = ep.get("number") or ep.get("ep_num") or 1
            is_watched = ep_num in completed_eps
            row = EpisodeRowWidget(ep, is_watched=is_watched)
            row.play_requested.connect(self._on_play_requested)
            row.download_requested.connect(self._on_download_requested)
            self.episodes_container.addWidget(row)

    def _on_details_error(self, err_msg):
        if self.sender() is not self.details_worker:
            return
        self.loading_bar.hide()
        self.desc_label.setText(f"Hata: {err_msg}")

    def _on_play_requested(self, episode_data: dict):
        if not self.details_data:
            return
        anime_id = self.details_data.get("id") or self.current_anime.get("id") or self.current_anime.get("slug")
        ep_id = episode_data.get("id")
        
        self.loading_bar.show()
        source = config.get("scraping_source", "animecix")

        self.streams_worker = StreamsWorker(anime_id, ep_id, source)
        self.streams_worker.streams_ready.connect(self._on_streams_ready, Qt.QueuedConnection)
        self.streams_worker.error_occurred.connect(self._on_streams_error, Qt.QueuedConnection)
        self.streams_worker.setProperty("episode_data", episode_data)
        start_background_worker(self, self.streams_worker)

    def _on_streams_ready(self, links: list):
        worker = self.sender()
        if worker is not self.streams_worker:
            return
        episode_data = worker.property("episode_data") or {}
        self.loading_bar.hide()
        if not links:
            QMessageBox.warning(self, "Yayın Hatası", "Bu bölüm için oynatılabilir bir yayın bağlantısı bulunamadı.")
            return

        selected_stream = links[0]
        if len(links) > 1:
            dialog = ServerSelectDialog(links, self)
            if dialog.exec_() == QDialog.Accepted:
                selected_stream = dialog.get_selected_stream()
            else:
                return

        url = selected_stream.get("url")
        headers = selected_stream.get("headers", {})
        anime_title = self.details_data.get("title") or self.current_anime.get("title")
        ep_num = episode_data.get("number") or 1
        total_eps = self.details_data.get("total_episodes") or len(self.details_data.get("episodes", []))

        # Mark as watched
        slug = self.details_data.get("slug") or self.current_anime.get("slug")
        progress_tracker.mark_watched(slug, ep_num, title=anime_title, total_episodes=total_eps)
        self.episode_watched.emit(slug, ep_num)

        # Launch Player in Background
        self.play_worker = PlayWorker(
            url=url,
            title=f"{anime_title} - Bölüm {ep_num}",
            headers=headers,
            anime_title=anime_title,
            episode_number=ep_num,
            total_episodes=total_eps
        )
        start_background_worker(self, self.play_worker)

    def _on_streams_error(self, err_msg):
        if self.sender() is not self.streams_worker:
            return
        self.loading_bar.hide()
        QMessageBox.warning(self, "Yayın Hatası", f"Yayın alınırken hata oluştu: {err_msg}")

    def _on_download_requested(self, episode_data: dict):
        anime_title = self.details_data.get("title") or self.current_anime.get("title")
        slug = self.details_data.get("slug") or self.current_anime.get("slug")
        
        episodes_to_add = [episode_data]
        added = queue_manager.add_to_queue(anime_title, episodes_to_add, slug)
        
        if added > 0:
            queue_manager.start_queue()
            QMessageBox.information(self, "İndirme Eklendi", f"'{anime_title} - Bölüm {episode_data.get('number')}' indirme kuyruğuna eklendi.")
        else:
            QMessageBox.information(self, "Bilgi", "Bu bölüm zaten indirme kuyruğunda yer alıyor.")
