"""Modern dark theme stylesheets for AnimLoid GUI."""

DARK_THEME_QSS = """
/* Global Application Styles */
QWidget {
    background-color: #0b0c0e;
    color: #d8dadd;
    font-family: 'Inter', 'Segoe UI', 'Ubuntu', 'Noto Sans', sans-serif;
    font-size: 13px;
    selection-background-color: #2563eb;
    selection-color: #FFFFFF;
}

/* Main Window */
QMainWindow {
    background-color: #0b0c0e;
}

/* Sidebar */
QFrame#Sidebar {
    background-color: #101114;
    border-right: 1px solid #26282d;
    min-width: 196px;
    max-width: 196px;
}

QLabel#LogoTitle {
    color: #FFFFFF;
    font-size: 18px;
    font-weight: bold;
    padding-left: 5px;
}

QLabel#LogoSubtitle {
    color: #60a5fa;
    font-size: 11px;
    font-weight: 600;
    padding-left: 5px;
}

/* Nav Buttons */
QPushButton.NavButton {
    background-color: transparent;
    color: #9ca3af;
    border: none;
    border-radius: 6px;
    padding: 9px 12px;
    text-align: left;
    font-size: 13px;
    font-weight: 500;
}

QPushButton.NavButton:hover {
    background-color: #1a1c20;
    color: #FFFFFF;
}

QPushButton.NavButton:checked, QPushButton.NavButton[active="true"] {
    background-color: #2563eb;
    color: #FFFFFF;
    font-weight: bold;
}

/* Header & Top Bar */
QFrame#TopBar {
    background-color: #101114;
    border-bottom: 1px solid #26282d;
    padding: 8px 16px;
}

/* Input Fields */
QLineEdit {
    background-color: #151619;
    border: 1px solid #303238;
    border-radius: 8px;
    color: #F8FAFC;
    padding: 8px 12px;
    font-size: 13px;
}

QLineEdit:focus {
    border: 1px solid #3b82f6;
    background-color: #181a1f;
}

QLineEdit::placeholder {
    color: #737780;
}

/* Buttons */
QPushButton.PrimaryButton {
    background-color: #2563eb;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 8px 18px;
    font-weight: bold;
    font-size: 13px;
}

QPushButton.PrimaryButton:hover {
    background-color: #3b82f6;
}

QPushButton.PrimaryButton:pressed {
    background-color: #1d4ed8;
}

QPushButton.SecondaryButton {
    background-color: #191b1f;
    color: #d1d5db;
    border: 1px solid #303238;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 500;
}

QPushButton.SecondaryButton:hover {
    background-color: #23262c;
    color: #FFFFFF;
    border-color: #4b5563;
}

QPushButton.SecondaryButton:pressed {
    background-color: #121316;
}

QPushButton.DangerButton {
    background-color: #EF4444;
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: bold;
}

QPushButton.DangerButton:hover {
    background-color: #F87171;
}

QPushButton.SuccessButton {
    background-color: #10B981;
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: bold;
}

QPushButton.SuccessButton:hover {
    background-color: #34D399;
}

/* ComboBox */
QComboBox {
    background-color: #151619;
    border: 1px solid #303238;
    border-radius: 8px;
    color: #F8FAFC;
    padding: 6px 12px;
    min-width: 130px;
}

QComboBox:hover {
    border-color: #4b5563;
}

QComboBox:focus {
    border-color: #3b82f6;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #9ca3af;
    margin-right: 8px;
}

QComboBox QAbstractItemView,
QComboBox QListView,
QListView {
    background-color: #151619;
    border: 1px solid #303238;
    selection-background-color: #2563eb;
    selection-color: #FFFFFF;
    color: #F8FAFC;
    padding: 4px;
    outline: none;
}

QComboBox QAbstractItemView::item {
    background-color: #151619;
    color: #F8FAFC;
    padding: 6px 10px;
    min-height: 24px;
    border-radius: 4px;
}

QComboBox QAbstractItemView::item:selected,
QComboBox QAbstractItemView::item:hover {
    background-color: #2563eb;
    color: #FFFFFF;
}

/* Cards & Frames */
QFrame.Card {
    background-color: #121316;
    border: 1px solid #292b30;
    border-radius: 8px;
}

QFrame.Card:hover {
    border: 1px solid #4b5563;
}

QFrame.AnimeCard {
    background-color: #121316;
    border: 1px solid #292b30;
    border-radius: 8px;
}

QFrame.AnimeCard:hover {
    border: 1px solid #3b82f6;
    background-color: #17191d;
}

/* ScrollBars */
QScrollBar:vertical {
    background-color: #0b0c0e;
    width: 8px;
    margin: 0px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background-color: #34373d;
    min-height: 25px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background-color: #3b82f6;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
    background: none;
}

QScrollBar:horizontal {
    background-color: #0b0c0e;
    height: 8px;
    margin: 0px;
    border-radius: 4px;
}

QScrollBar::handle:horizontal {
    background-color: #34373d;
    min-width: 25px;
    border-radius: 4px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #3b82f6;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
    background: none;
}

/* ScrollArea */
QScrollArea {
    background-color: transparent;
    border: none;
}

/* Table Widget */
QTableWidget {
    background-color: #121316;
    border: 1px solid #292b30;
    border-radius: 8px;
    gridline-color: #292b30;
}

QTableWidget::item {
    padding: 8px;
    border-bottom: 1px solid #24262b;
}

QTableWidget::item:selected {
    background-color: #202329;
    color: #FFFFFF;
}

QHeaderView::section {
    background-color: #17191d;
    color: #9ca3af;
    padding: 8px;
    font-weight: bold;
    border: none;
    border-bottom: 1px solid #303238;
}

/* Progress Bar */
QProgressBar {
    background-color: #181a1e;
    border: 1px solid #303238;
    border-radius: 6px;
    text-align: center;
    color: #F8FAFC;
    font-size: 11px;
    font-weight: bold;
    height: 14px;
}

QProgressBar::chunk {
    background-color: #2563eb;
    border-radius: 5px;
}

/* Badges / Tags */
QLabel.Badge {
    background-color: #202226;
    color: #a1a1aa;
    border-radius: 6px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 600;
}

QLabel.BadgeAccent {
    background-color: #172554;
    color: #93c5fd;
    border: 1px solid #1e3a8a;
    border-radius: 6px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: bold;
}

QLabel.BadgeSuccess {
    background-color: rgba(16, 185, 129, 0.2);
    color: #34D399;
    border: 1px solid rgba(16, 185, 129, 0.4);
    border-radius: 6px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: bold;
}

/* CheckBox */
QCheckBox {
    color: #E2E8F0;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1px solid #4b5563;
    border-radius: 4px;
    background-color: #151619;
}

QCheckBox::indicator:checked {
    background-color: #2563eb;
    border-color: #2563eb;
}

/* List Widget */
QListWidget {
    background-color: #121316;
    border: 1px solid #292b30;
    border-radius: 8px;
    padding: 4px;
}

QListWidget::item {
    border-radius: 6px;
    padding: 8px 12px;
    margin: 2px 0px;
}

QListWidget::item:hover {
    background-color: #1c1f24;
}

QListWidget::item:selected {
    background-color: #2563eb;
    color: #FFFFFF;
}

/* Status Bar */
QStatusBar {
    background-color: #101114;
    border-top: 1px solid #26282d;
    color: #737780;
    font-size: 12px;
}
"""
