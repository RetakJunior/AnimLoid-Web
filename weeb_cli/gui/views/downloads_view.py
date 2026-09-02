"""Downloads & Queue View for AnimLoid GUI."""

import os
import subprocess
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar, 
    QMessageBox, QFrame
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QCursor, QColor

from weeb_cli.config import config
from weeb_cli.services.downloader import queue_manager
from weeb_cli.services.database import db


class DownloadsView(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

        # Timer for polling queue
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_queue)
        self.timer.start(1500)

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(14)

        # Title & Top Actions
        top_row = QHBoxLayout()
        title_label = QLabel("İndirme Yöneticisi ve Kuyruk")
        title_label.setStyleSheet("color: #FFFFFF; font-size: 18px; font-weight: bold;")
        top_row.addWidget(title_label)
        top_row.addStretch()

        self.start_btn = QPushButton("▶ Kuyruğu Başlat")
        self.start_btn.setProperty("class", "SuccessButton")
        self.start_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.start_btn.clicked.connect(self._start_queue)
        top_row.addWidget(self.start_btn)

        self.retry_btn = QPushButton("🔄 Başarısızları Dene")
        self.retry_btn.setProperty("class", "SecondaryButton")
        self.retry_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.retry_btn.clicked.connect(self._retry_failed)
        top_row.addWidget(self.retry_btn)

        self.clear_btn = QPushButton("🧹 Temizle")
        self.clear_btn.setProperty("class", "SecondaryButton")
        self.clear_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.clear_btn.clicked.connect(self._clear_completed)
        top_row.addWidget(self.clear_btn)

        self.open_folder_btn = QPushButton("📁 Klasörü Aç")
        self.open_folder_btn.setProperty("class", "SecondaryButton")
        self.open_folder_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.open_folder_btn.clicked.connect(self._open_download_folder)
        top_row.addWidget(self.open_folder_btn)

        main_layout.addLayout(top_row)

        # Queue Status Info Bar
        self.info_label = QLabel("Kuyruk durumu yükleniyor...")
        self.info_label.setStyleSheet("color: #94A3B8; font-size: 12px;")
        main_layout.addWidget(self.info_label)

        # Downloads Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Anime", "Bölüm", "Durum", "İlerleme", "Hız / Kalan", "İşlem"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self.table.horizontalHeader().resizeSection(3, 160)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)

        main_layout.addWidget(self.table, stretch=1)

        self.refresh_queue()

    def _start_queue(self):
        queue_manager.start_queue()
        self.refresh_queue()

    def _retry_failed(self):
        count = queue_manager.retry_failed()
        QMessageBox.information(self, "Yeniden Deneniyor", f"{count} başarısız indirme kuyruğa alındı.")
        self.refresh_queue()

    def _clear_completed(self):
        db.clear_completed_queue()
        self.refresh_queue()

    def _open_download_folder(self):
        dl_dir = config.get("download_dir")
        if not dl_dir:
            dl_dir = os.path.expanduser("~/weeb-downloads")
        os.makedirs(dl_dir, exist_ok=True)

        try:
            subprocess.Popen(["xdg-open", dl_dir])
        except Exception as e:
            QMessageBox.warning(self, "Klasör Açılamadı", f"İndirme klasörü açılamadı: {e}")

    def refresh_queue(self):
        items = queue_manager.queue
        active_count = len([i for i in items if i.get("status") == "processing"])
        pending_count = len([i for i in items if i.get("status") == "pending"])
        failed_count = len([i for i in items if i.get("status") == "failed"])
        completed_count = len([i for i in items if i.get("status") == "completed"])

        status_text = f"Aktif: {active_count} | Bekleyen: {pending_count} | Tamamlanan: {completed_count} | Başarısız: {failed_count}"
        self.info_label.setText(status_text)

        self.table.setRowCount(len(items))

        for row, item in enumerate(items):
            # Anime Title
            title_item = QTableWidgetItem(item.get("anime_title", "Anime"))
            title_item.setForeground(QColor("#FFFFFF"))
            self.table.setItem(row, 0, title_item)

            # Episode
            ep_item = QTableWidgetItem(f"Bölüm {item.get('episode_number', 1)}")
            ep_item.setTextAlignment(Qt.AlignCenter)
            ep_item.setForeground(QColor("#CBD5E1"))
            self.table.setItem(row, 1, ep_item)

            # Status Badge
            status = item.get("status", "pending")
            status_item = QTableWidgetItem()
            status_item.setTextAlignment(Qt.AlignCenter)

            if status == "completed":
                status_item.setText("Tamamlandı ✓")
                status_item.setForeground(QColor("#10B981"))
            elif status == "processing":
                status_item.setText("İndiriliyor ⬇")
                status_item.setForeground(QColor("#60A5FA"))
            elif status == "failed":
                status_item.setText("Hata ✕")
                status_item.setForeground(QColor("#EF4444"))
            elif status == "cancelled":
                status_item.setText("İptal Edildi")
                status_item.setForeground(QColor("#64748B"))
            else:
                status_item.setText("Bekliyor ⏱")
                status_item.setForeground(QColor("#F59E0B"))

            self.table.setItem(row, 2, status_item)

            # Progress Bar
            progress_val = int(item.get("progress", 0))
            p_bar = QProgressBar()
            p_bar.setRange(0, 100)
            p_bar.setValue(progress_val)
            self.table.setCellWidget(row, 3, p_bar)

            # Speed & ETA
            speed = item.get("speed") or ""
            eta = item.get("eta") or ""
            speed_text = f"{speed} ({eta})" if speed and eta != "?" else (eta if eta != "?" else "-")
            speed_item = QTableWidgetItem(speed_text)
            speed_item.setTextAlignment(Qt.AlignCenter)
            speed_item.setForeground(QColor("#94A3B8"))
            self.table.setItem(row, 4, speed_item)

            # Action Button
            action_btn = QPushButton("✕ İptal" if status in ["pending", "processing"] else "Sil")
            action_btn.setProperty("class", "DangerButton" if status in ["pending", "processing"] else "SecondaryButton")
            action_btn.setCursor(QCursor(Qt.PointingHandCursor))
            ep_id = item.get("episode_id")
            action_btn.clicked.connect(lambda checked, eid=ep_id, st=status: self._handle_item_action(eid, st))
            self.table.setCellWidget(row, 5, action_btn)

    def _handle_item_action(self, episode_id: str, status: str):
        if status in ["pending", "processing"]:
            db.update_queue_item(episode_id, status="cancelled")
        else:
            with db._conn() as conn:
                conn.execute("DELETE FROM download_queue WHERE episode_id = ?", (episode_id,))
        self.refresh_queue()
