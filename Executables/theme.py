#
# NEW FILE: theme.py
#
# This file centralizes all your styling.
# All other UI files (login, register, dashboard, chat)
# should import from this file.
#

COLOR_BACKGROUND = "#1A1B2E"
COLOR_PANE_LEFT = "#272540"  # BG for cards, sidebars
COLOR_CARD_BG = "#272540"  # Add this line
COLOR_CARD = "#3E3C6E"      # BG for inputs # BG for cards, sidebars
COLOR_CARD = "#3E3C6E"      # BG for inputs
COLOR_TEXT = "#F0F0F5"
COLOR_TEXT_SUBTLE = "#A9A8C0"
COLOR_GOLD = "#D4AF37"
COLOR_GOLD_HOVER = "#F0C44F"
COLOR_GOLD_PRESSED = "#B8860B"
COLOR_RED = "#ed4956"
COLOR_RED_HOVER = "#ff7d6e"
COLOR_RED_PRESSED = "#e63946"

def input_style(radius=22):
    """Returns the QSS for a standard QLineEdit."""
    return f"""
        QLineEdit {{
            font-family: "Segoe UI";
            font-size: 14px;
            padding: 10px 20px;
            background-color: {COLOR_CARD};
            color: {COLOR_TEXT};
            border: 2px solid {COLOR_GOLD};
            border-radius: {radius}px;
        }}
        QLineEdit:focus {{
            border: 2px solid {COLOR_GOLD_HOVER};
        }}
    """

def button_style(base=COLOR_GOLD, 
                   hover=COLOR_GOLD_HOVER, 
                   pressed=COLOR_GOLD_PRESSED, 
                   text_color=COLOR_PANE_LEFT, 
                   radius=22):
    """Returns the QSS for a standard QPushButton."""
    return f"""
        QPushButton {{
            background-color: {base};
            color: {text_color};
            padding: 10px;
            border: none;
            border-radius: {radius}px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: {hover};
        }}
        QPushButton:pressed {{
            background-color: {pressed};
        }}
        QPushButton:disabled {{
            background-color: #504E8A;
            color: {COLOR_TEXT_SUBTLE};
        }}
    """

def link_style():
    """Returns the QSS for a link-style QPushButton."""
    return f"""
        QPushButton {{
            background-color: transparent;
            color: {COLOR_TEXT_SUBTLE};
            font-size: 9pt;
            font-weight: normal;
            border: none;
            text-decoration: underline;
            padding: 5px;
        }}
        QPushButton:hover {{
            color: {COLOR_TEXT};
        }}
    """