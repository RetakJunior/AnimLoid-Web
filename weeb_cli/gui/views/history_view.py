"""History and Watchlist View for AnimLoid GUI."""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QScrollArea, QFrame, QGridLayout, QProgressBar
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QCursor

from weeb_cli.services.progress import progress_tracker


class HistoryCard(QFrame):
    resume_clicked = pyqtSignal(dict)
    detail_clicked = pyqtSignal(dict)

    def __init__(self, anime_info: dict):
        super().__init__()
        self.anime_info = anime_info
        self.setProperty("class", "Card")
        self.setStyleSheet("""
            QFrame.Card {
                background-color: #17191d;
                border: 1px solid #303238;
                border-radius: 10px;
                padding: 12px;
            }
            QFrame.Card:hover {
                border-color: #3b82f6;
                background-color: #202436;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Header: Title & Last watched badge
        header_layout = QHBoxLayout()
        title = anime_info.get("title") or anime_info.get("slug") or "Anime"
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("color: #FFFFFF; font-size: 14px; font-weight: bold;")
        header_layout.addWidget(self.title_label, stretch=1)

        last_watched = anime_info.get("last_watched", 0)
        ep_badge = QLabel(f"Son: Bölüm {last_watched}")
        ep_badge.setStyleSheet("background-color: #172554; color: #93c5fd; border-radius: 4px; padding: 2px 6px; font-size: 11px; font-weight: bold;")
        header_layout.addWidget(ep_badge)
        layout.addLayout(header_layout)

        # Progress bar & stats
        completed_list = anime_info.get("completed", [])
        total_eps = anime_info.get("total_episodes", 0)
        watched_count = len(completed_list)

        progress_layout = QHBoxLayout()
        progress_bar = QProgressBar()
        if total_eps > 0:
            progress_bar.setRange(0, total_eps)
            progress_bar.setValue(min(watched_count, total_eps))
            ratio_text = f"{watched_count} / {total_eps} Bölüm"
        else:
            progress_bar.setRange(0, max(1, watched_count))
            progress_bar.setValue(watched_count)
            ratio_text = f"{watched_count} Bölüm İzlendi"

        progress_layout.addWidget(progress_bar, stretch=1)
        
        ratio_label = QLabel(ratio_text)
        ratio_label.setStyleSheet("color: #94A3B8; font-size: 11px;")
        progress_layout.addWidget(ratio_label)
        layout.addLayout(progress_layout)

        # Date & Action Buttons
        footer_layout = QHBoxLayout()
        date_str = anime_info.get("last_watched_at") or ""
        if date_str and "T" in date_str:
            date_str = date_str.split("T")[0]
        date_label = QLabel(f"📅 {date_str}" if date_str else "")
        date_label.setStyleSheet("color: #64748B; font-size: 11px;")
        footer_layout.addWidget(date_label)
        footer_layout.addStretch()

        detail_btn = QPushButton("Detay")
        detail_btn.setProperty("class", "SecondaryButton")
        detail_btn.setCursor(QCursor(Qt.PointingHandCursor))
        detail_btn.clicked.connect(lambda: self.detail_clicked.emit(self.anime_info))
        footer_layout.addWidget(detail_btn)

        layout.addLayout(footer_layout)


class HistoryView(QWidget):
    anime_selected = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(16)

        # Title & Refresh Row
        top_row = QHBoxLayout()
        title_label = QLabel("İzleme Geçmişi ve İstatistikler")
        title_label.setStyleSheet("color: #FFFFFF; font-size: 18px; font-weight: bold;")
        top_row.addWidget(title_label)
        top_row.addStretch()

        refresh_btn = QPushButton("🔄 Yenile")
        refresh_btn.setProperty("class", "SecondaryButton")
        refresh_btn.setCursor(QCursor(Qt.PointingHandCursor))
        refresh_btn.clicked.connect(self.refresh_history)
        top_row.addWidget(refresh_btn)
        main_layout.addLayout(top_row)

        # Stats Cards Row
        self.stats_row = QHBoxLayout()
        self.stats_row.setSpacing(12)

        self.total_anime_card = self._create_stat_card("Toplam Anime", "0", "📺")
        self.total_episodes_card = self._create_stat_card("İzlenen Bölüm", "0", "🎬")
        self.total_hours_card = self._create_stat_card("İzleme Süresi", "0 saat", "⏱️")

        self.stats_row.addWidget(self.total_anime_card)
        self.stats_row.addWidget(self.total_episodes_card)
        self.stats_row.addWidget(self.total_hours_card)
        main_layout.addLayout(self.stats_row)

        # History Scroll Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.cards_container = QWidget()
        self.cards_container.setStyleSheet("background-color: transparent;")
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 8, 0, 8)
        self.cards_layout.setSpacing(10)
        self.cards_layout.setAlignment(Qt.AlignTop)

        self.scroll_area.setWidget(self.cards_container)
        main_layout.addWidget(self.scroll_area, stretch=1)

        self.refresh_history()

    def _create_stat_card(self, title: str, val: str, icon: str):
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #121316;
                border: 1px solid #292b30;
                border-radius: 8px;
                padding: 10px 14px;
            }
        """)
        l = QVBoxLayout(frame)
        l.setSpacing(2)
        l.setContentsMargins(8, 8, 8, 8)

        t_lbl = QLabel(f"{icon} {title}")
        t_lbl.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 500;")
        l.addWidget(t_lbl)

        v_lbl = QLabel(val)
        v_lbl.setObjectName("StatValue")
        v_lbl.setStyleSheet("color: #FFFFFF; font-size: 18px; font-weight: bold;")
        l.addWidget(v_lbl)
        return frame

    def refresh_history(self):
        # Update Stats
        stats = progress_tracker.get_stats()
        self.total_anime_card.findChild(QLabel, "StatValue").setText(str(stats.get("total_anime", 0)))
        self.total_episodes_card.findChild(QLabel, "StatValue").setText(str(stats.get("total_episodes", 0)))
        self.total_hours_card.findChild(QLabel, "StatValue").setText(f"{stats.get('total_hours', 0)} sa")

        # Clear Cards
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        all_progress = progress_tracker.get_in_progress_anime()
        completed = progress_tracker.get_completed_anime()
        all_list = all_progress + completed

        if not all_list:
            empty_lbl = QLabel("Henüz izlenen bir anime geçmişi bulunmuyor.\nArama sekmesinden bir anime seçip izlemeye başlayabilirsiniz!")
            empty_lbl.setAlignment(Qt.AlignCenter)
            empty_lbl.setStyleSheet("color: #64748B; font-size: 14px; padding: 40px;")
            self.cards_layout.addWidget(empty_lbl)
            return

        for anime_info in all_list:
            card = HistoryCard(anime_info)
            card.detail_clicked.connect(self._on_detail_clicked)
            self.cards_layout.addWidget(card)

    def _on_detail_clicked(self, anime_info: dict):
        anime_data = {
            "id": anime_info.get("slug"),
            "slug": anime_info.get("slug"),
            "title": anime_info.get("title") or anime_info.get("slug"),
            "name": anime_info.get("title") or anime_info.get("slug"),
        }
        self.anime_selected.emit(anime_data)
