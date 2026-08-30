"""
@description Folha de estilo (QSS) do app — tema escuro coeso, aplicado em QApplication.
@connects overlay.gallery.main
"""
from __future__ import annotations

# paleta
BG = "#1e1f22"
PANEL = "#232428"
SURFACE = "#2b2d31"
SURFACE_2 = "#35373c"
BORDER = "#3f4147"
INK = "#17181b"
TEXT = "#e3e5e8"
DIM = "#9a9ea6"
MUTED = "#5c5f66"
ACCENT = "#4f8cff"
ACCENT_HOVER = "#6ba0ff"
DANGER = "#f0616d"

APP_QSS = f"""
* {{ font-family: 'Segoe UI', 'Inter', system-ui, sans-serif; font-size: 13px; }}

QMainWindow, QWidget#Root {{ background: {BG}; }}
QWidget {{ color: {TEXT}; }}

/* linha 1: marca + botões da janela (arrastável) */
#TitleBar {{ background: {INK}; }}
#TitleBar QLabel {{ background: transparent; }}
#TitleName {{ font-size: 12.5px; font-weight: 600; color: #cfd3da; letter-spacing: 0.2px; }}

/* linha 2: ações + checkboxes */
#ActionBar {{ background: {PANEL}; border-top: 1px solid #26272b;
              border-bottom: 1px solid {BORDER}; }}
#ActionBar QLabel {{ background: transparent; }}
#BarSep {{ background: #3a3c42; margin: 11px 0; }}

QToolButton#BarBtn {{
    background: transparent; border: 1px solid transparent; border-radius: 6px;
    padding: 6px 10px; color: #d3d6dc; font-size: 12.5px;
}}
QToolButton#BarBtn:hover {{ background: {SURFACE}; }}
QToolButton#BarBtn:pressed {{ background: {SURFACE_2}; }}

QToolButton#WinBtn, QToolButton#WinBtnClose {{
    background: transparent; border: none; border-radius: 0;
}}
QToolButton#WinBtn:hover {{ background: {SURFACE_2}; }}
QToolButton#WinBtn:pressed {{ background: {SURFACE}; }}
QToolButton#WinBtnClose:hover {{ background: #e04552; }}
QToolButton#WinBtnClose:pressed {{ background: #c23b47; }}

#ActionBar QCheckBox {{ color: #c7cad1; spacing: 6px; }}

#HeaderSub {{ color: {DIM}; font-size: 12px; }}

QToolButton, QPushButton {{
    background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 7px;
    padding: 7px 13px; color: {TEXT};
}}
QToolButton:hover, QPushButton:hover {{ background: {SURFACE_2}; border-color: {ACCENT}; }}
QToolButton:pressed, QPushButton:pressed {{ background: {INK}; }}
QToolButton:disabled, QPushButton:disabled {{ color: {MUTED}; border-color: #2f3136;
                                              background: {PANEL}; }}

QPushButton#Primary {{ background: {ACCENT}; border-color: {ACCENT}; color: #fff; font-weight: 600; }}
QPushButton#Primary:hover {{ background: {ACCENT_HOVER}; border-color: {ACCENT_HOVER}; }}
QPushButton#Danger {{ color: {DIM}; }}
QPushButton#Danger:hover {{ border-color: {DANGER}; color: {DANGER}; background: {SURFACE}; }}
QPushButton#Recording {{ background: {DANGER}; border-color: {DANGER}; color: #fff; font-weight: 600; }}

QCheckBox {{ spacing: 7px; color: {TEXT}; }}
QCheckBox::indicator {{ width: 15px; height: 15px; border-radius: 4px;
                        border: 1px solid #565a63; background: {SURFACE}; }}
QCheckBox::indicator:checked {{ background: {ACCENT}; border-color: {ACCENT}; }}
QCheckBox::indicator:hover {{ border-color: {ACCENT}; }}

QListWidget#Film {{ background: {PANEL}; border: none; border-right: 1px solid {BORDER};
                    padding: 6px; outline: none; }}
QListWidget#Film::item {{ border-radius: 8px; padding: 5px; margin: 3px 2px;
                          color: {DIM}; }}
QListWidget#Film::item:hover {{ background: {SURFACE}; }}
QListWidget#Film::item:selected {{ background: {SURFACE}; border: 1px solid {ACCENT};
                                   color: #fff; }}

QScrollArea {{ border: 1px solid {BORDER}; border-radius: 10px; background: {INK}; }}

QPlainTextEdit {{
    background: {INK}; border: 1px solid {BORDER}; border-radius: 10px;
    padding: 10px; color: #cdd0d6; selection-background-color: {ACCENT};
    selection-color: #fff;
}}

#NavLabel {{ color: {DIM}; font-weight: 600; letter-spacing: 0.3px; }}
#Pill {{ background: {PANEL}; border: 1px solid {BORDER}; border-radius: 12px;
         padding: 3px 10px; color: {DIM}; }}

QToolButton#NavChevron {{
    background: rgba(23, 24, 27, 0.62); border: 1px solid {BORDER};
    border-radius: 23px; color: {TEXT}; font-size: 24px; font-weight: 700;
    padding-bottom: 3px;
}}
QToolButton#NavChevron:hover {{ background: {ACCENT}; border-color: {ACCENT}; color: #fff; }}
QToolButton#NavChevron:pressed {{ background: {ACCENT_HOVER}; }}

#ViewerEmpty {{ color: {DIM}; font-size: 13px; background: #0f1012; }}
#ZoomHint {{
    background: rgba(17, 18, 21, 0.82); border: 1px solid {BORDER};
    border-radius: 13px; color: #d3d6dc; font-size: 11px;
    padding: 4px 11px;
}}

#ReversePanel {{ background: {PANEL}; border-left: 1px solid {BORDER}; }}

QStatusBar {{ background: {INK}; color: {DIM}; border-top: 1px solid {BORDER}; }}
QStatusBar::item {{ border: none; }}

QDialog {{ background: {BG}; }}
QLabel#DialogHint {{ color: {DIM}; font-size: 12px; }}
QLabel#RowTitle {{ color: {TEXT}; font-size: 13px; font-weight: 600; }}
QLabel#RowSub {{ color: {DIM}; font-size: 11px; }}

#GameCard {{ background: {PANEL}; border: 1px solid {BORDER}; border-radius: 10px; }}
#GameCard QLineEdit {{ background: {INK}; border: 1px solid {BORDER};
                       border-radius: 6px; padding: 5px 8px; color: {DIM}; }}

QProgressBar {{ background: {INK}; border: 1px solid {BORDER}; border-radius: 6px;
                height: 16px; text-align: center; color: {DIM}; }}
QProgressBar::chunk {{ background: {ACCENT}; border-radius: 5px; }}

QPushButton#KeyField {{
    background: {INK}; border: 1px solid {BORDER}; border-radius: 6px;
    padding: 0 10px; color: {TEXT}; font-weight: 600; letter-spacing: 0.4px;
    text-align: center;
}}
QPushButton#KeyField:hover {{ border-color: {ACCENT}; }}
QPushButton#KeyField[state="empty"] {{ color: {MUTED}; font-weight: 500; letter-spacing: 0; }}
QPushButton#KeyField[state="listening"] {{
    border-color: {ACCENT}; background: rgba(79,140,255,0.12);
    color: {ACCENT}; font-weight: 500; letter-spacing: 0;
}}

QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 5px; min-height: 26px; }}
QScrollBar::handle:vertical:hover {{ background: #4f545c; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {BORDER}; border-radius: 5px; min-width: 26px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
"""
