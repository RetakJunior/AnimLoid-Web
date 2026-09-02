"""Settings View for AnimLoid GUI - Fixed layout conflicts."""

import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QCheckBox, QSpinBox, QFileDialog, QScrollArea,
    QFrame, QMessageBox, QGridLayout, QSizePolicy
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCursor

from weeb_cli.config import config
from weeb_cli.services.database import db
from weeb_cli.services.scraper import scraper
from weeb_cli.services.dependency_manager import dependency_manager
from weeb_cli.gui.workers import DependencyCheckWorker, InstallDependencyWorker


CARD_STYLE = """
    QFrame#settingsCard {
        background-color: #151824;
        border: 1px solid #232738;
        border-radius: 10px;
    }
"""


def make_card(title: str):
    """Create a styled card QFrame and return (card, inner_layout) pair."""
    card = QFrame()
    card.setObjectName("settingsCard")
    card.setStyleSheet(CARD_STYLE)
    card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

    outer = QVBoxLayout(card)
    outer.setContentsMargins(16, 12, 16, 14)
    outer.setSpacing(10)

    title_lbl = QLabel(title)
    title_lbl.setStyleSheet("color: #FFFFFF; font-size: 14px; font-weight: bold;")
    outer.addWidget(title_lbl)

    return card, outer


class SettingsView(QWidget):
    def __init__(self):
        super().__init__()
        self.check_worker = None
        self.install_workers = {}
        self.dep_grid = None
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(16)

        title_label = QLabel("Ayarlar ve Yapılandırma")
        title_label.setStyleSheet("color: #FFFFFF; font-size: 18px; font-weight: bold;")
        main_layout.addWidget(title_label)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        content.setStyleSheet("background-color: transparent;")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 4, 0)
        layout.setSpacing(14)

        # ── 1. Genel Ayarlar ──────────────────────────────────────────────
        general_card, g_layout = make_card("⚙️  Genel Ayarlar")

        src_row = QHBoxLayout()
        src_lbl = QLabel("Varsayılan Anime Kaynağı:")
        src_lbl.setStyleSheet("color: #CBD5E1; min-width: 200px;")
        src_row.addWidget(src_lbl)

        self.source_combo = QComboBox()
        providers = scraper.get_available_sources()
        current_source = config.get("scraping_source", "animecix")
        for i, p in enumerate(providers):
            flag = "🇹🇷" if p.get("lang") == "tr" else "🌐"
            self.source_combo.addItem(f"{flag} {p['name'].capitalize()}", p["name"])
            if p["name"] == current_source:
                self.source_combo.setCurrentIndex(i)
        self.source_combo.currentIndexChanged.connect(self._save_source)
        src_row.addWidget(self.source_combo)
        src_row.addStretch()
        g_layout.addLayout(src_row)

        lang_row = QHBoxLayout()
        lang_lbl = QLabel("Arayüz ve Arama Dili:")
        lang_lbl.setStyleSheet("color: #CBD5E1; min-width: 200px;")
        lang_row.addWidget(lang_lbl)

        self.lang_combo = QComboBox()
        self.lang_combo.addItem("🇹🇷 Türkçe", "tr")
        self.lang_combo.addItem("🇬🇧 English", "en")
        current_lang = config.get("language", "tr")
        self.lang_combo.setCurrentIndex(0 if current_lang == "tr" else 1)
        self.lang_combo.currentIndexChanged.connect(self._save_lang)
        lang_row.addWidget(self.lang_combo)
        lang_row.addStretch()
        g_layout.addLayout(lang_row)

        self.discord_check = QCheckBox("Discord Rich Presence (RPC) Entegrasyonu")
        self.discord_check.setChecked(bool(config.get("discord_rpc_enabled", False)))
        self.discord_check.toggled.connect(lambda val: config.set("discord_rpc_enabled", val))
        g_layout.addWidget(self.discord_check)

        layout.addWidget(general_card)

        # ── 2. İndirme Ayarları ───────────────────────────────────────────
        dl_card, dl_layout = make_card("📥  İndirme ve Depolama Ayarları")

        dir_row = QHBoxLayout()
        dir_lbl = QLabel("İndirme Klasörü:")
        dir_lbl.setStyleSheet("color: #CBD5E1; min-width: 200px;")
        dir_row.addWidget(dir_lbl)

        self.dir_input_lbl = QLabel(config.get("download_dir") or os.path.expanduser("~/weeb-downloads"))
        self.dir_input_lbl.setStyleSheet(
            "color: #94A3B8; background-color: #1A1D2B; padding: 6px 12px; border-radius: 6px; border: 1px solid #2D3247;"
        )
        self.dir_input_lbl.setWordWrap(False)
        dir_row.addWidget(self.dir_input_lbl, stretch=1)

        change_dir_btn = QPushButton("Gözat...")
        change_dir_btn.setProperty("class", "SecondaryButton")
        change_dir_btn.setCursor(QCursor(Qt.PointingHandCursor))
        change_dir_btn.clicked.connect(self._browse_dir)
        dir_row.addWidget(change_dir_btn)
        dl_layout.addLayout(dir_row)

        con_row = QHBoxLayout()
        con_lbl = QLabel("Eşzamanlı İndirme Sayısı:")
        con_lbl.setStyleSheet("color: #CBD5E1; min-width: 200px;")
        con_row.addWidget(con_lbl)

        self.con_spin = QSpinBox()
        self.con_spin.setRange(1, 10)
        self.con_spin.setValue(int(config.get("max_concurrent_downloads", 3)))
        self.con_spin.valueChanged.connect(lambda val: config.set("max_concurrent_downloads", val))
        con_row.addWidget(self.con_spin)
        con_row.addStretch()
        dl_layout.addLayout(con_row)

        layout.addWidget(dl_card)

        # ── 3. Bağımlılıklar ──────────────────────────────────────────────
        dep_card, self.dep_outer_layout = make_card("🔧  Sistem Araçları ve Bağımlılıklar")

        self.dep_grid = QGridLayout()
        self.dep_grid.setSpacing(10)
        self.dep_grid.setColumnStretch(2, 1)
        self.dep_outer_layout.addLayout(self.dep_grid)

        check_all_btn = QPushButton("🔍 Bağımlılıkları Kontrol Et")
        check_all_btn.setProperty("class", "SecondaryButton")
        check_all_btn.setCursor(QCursor(Qt.PointingHandCursor))
        check_all_btn.clicked.connect(self.check_dependencies)
        self.dep_outer_layout.addWidget(check_all_btn)

        layout.addWidget(dep_card)

        # ── 4. Veritabanı ─────────────────────────────────────────────────
        db_card, db_layout = make_card("💾  Veritabanı ve Yedekleme")

        db_btn_row = QHBoxLayout()
        backup_btn = QPushButton("💾 Veritabanını Yedekle")
        backup_btn.setProperty("class", "SecondaryButton")
        backup_btn.setCursor(QCursor(Qt.PointingHandCursor))
        backup_btn.clicked.connect(self._backup_database)
        db_btn_row.addWidget(backup_btn)

        restore_btn = QPushButton("📂 Yedekten Geri Yükle")
        restore_btn.setProperty("class", "SecondaryButton")
        restore_btn.setCursor(QCursor(Qt.PointingHandCursor))
        restore_btn.clicked.connect(self._restore_database)
        db_btn_row.addWidget(restore_btn)
        db_btn_row.addStretch()
        db_layout.addLayout(db_btn_row)

        layout.addWidget(db_card)
        layout.addStretch()

        scroll_area.setWidget(content)
        main_layout.addWidget(scroll_area, stretch=1)

        self.check_dependencies()

    # ── Slots ──────────────────────────────────────────────────────────────

    def _save_source(self):
        source = self.source_combo.currentData()
        if source:
            config.set("scraping_source", source)

    def _save_lang(self):
        lang = self.lang_combo.currentData()
        if lang:
            config.set("language", lang)

    def _browse_dir(self):
        current = config.get("download_dir") or os.path.expanduser("~/weeb-downloads")
        selected = QFileDialog.getExistingDirectory(self, "İndirme Klasörü Seç", current)
        if selected:
            config.set("download_dir", selected)
            self.dir_input_lbl.setText(selected)

    def check_dependencies(self):
        # Clear grid
        while self.dep_grid.count():
            item = self.dep_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.check_worker = DependencyCheckWorker()
        self.check_worker.status_ready.connect(self._on_dependencies_checked)
        self.check_worker.start()

    def _on_dependencies_checked(self, results: dict):
        tool_names = {
            "mpv":   "MPV Medya Oynatıcı",
            "ffmpeg": "FFmpeg Video Araçları",
            "yt-dlp": "yt-dlp Yayın Yakalayıcı",
            "aria2":  "Aria2 Çoklu İndirici",
        }

        for row, (dep_key, name) in enumerate(tool_names.items()):
            info = results.get(dep_key, {})
            installed = info.get("installed", False)
            path = info.get("path", "")

            name_lbl = QLabel(name)
            name_lbl.setStyleSheet("color: #FFFFFF; font-weight: 500;")
            self.dep_grid.addWidget(name_lbl, row, 0)

            if installed:
                status_lbl = QLabel("✓ Yüklü")
                status_lbl.setStyleSheet("color: #10B981; font-weight: bold;")
                self.dep_grid.addWidget(status_lbl, row, 1)

                path_lbl = QLabel(path)
                path_lbl.setStyleSheet("color: #64748B; font-size: 11px;")
                path_lbl.setWordWrap(False)
                self.dep_grid.addWidget(path_lbl, row, 2)
            else:
                status_lbl = QLabel("✕ Eksik")
                status_lbl.setStyleSheet("color: #EF4444; font-weight: bold;")
                self.dep_grid.addWidget(status_lbl, row, 1)

                install_btn = QPushButton("Yükle")
                install_btn.setProperty("class", "PrimaryButton")
                install_btn.setCursor(QCursor(Qt.PointingHandCursor))
                install_btn.setFixedWidth(90)
                install_btn.clicked.connect(lambda checked, d=dep_key: self._install_dep(d))
                self.dep_grid.addWidget(install_btn, row, 2)

    def _install_dep(self, dep_name: str):
        worker = InstallDependencyWorker(dep_name)
        worker.install_finished.connect(self._on_dep_install_finished)
        self.install_workers[dep_name] = worker
        worker.start()
        QMessageBox.information(self, "Yükleniyor", f"'{dep_name}' arka planda yükleniyor. Tamamlandığında bildirim alacaksınız.")

    def _on_dep_install_finished(self, dep_name: str, success: bool):
        if success:
            QMessageBox.information(self, "Başarılı", f"'{dep_name}' başarıyla yüklendi!")
        else:
            QMessageBox.warning(
                self, "Yükleme Başarısız",
                f"'{dep_name}' otomatik yüklenemedi.\n\nManüel kurulum için:\n  sudo apt install {dep_name}"
            )
        self.check_dependencies()

    def _backup_database(self):
        dest, _ = QFileDialog.getSaveFileName(self, "Veritabanını Yedekle", "weeb_backup.db", "SQLite Veritabanı (*.db)")
        if dest:
            if db.backup_database(dest):
                QMessageBox.information(self, "Yedekleme Başarılı", f"Veritabanı yedeklendi:\n{dest}")
            else:
                QMessageBox.warning(self, "Hata", "Yedekleme sırasında bir sorun oluştu.")

    def _restore_database(self):
        src, _ = QFileDialog.getOpenFileName(self, "Yedekten Geri Yükle", "", "SQLite Veritabanı (*.db)")
        if src:
            if db.restore_database(src):
                QMessageBox.information(self, "Geri Yükleme Başarılı", "Veritabanı başarıyla geri yüklendi. Uygulamayı yeniden başlatın.")
            else:
                QMessageBox.warning(self, "Hata", "Veritabanı geri yüklenemedi.")
