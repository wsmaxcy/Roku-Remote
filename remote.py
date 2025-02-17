#!/usr/bin/env python

import sys
import re
import requests
import socket
import subprocess
from scapy.all import ARP, Ether, srp

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, 
    QLabel, QTabWidget, QGridLayout, QLineEdit, QMenu
)
from PyQt5.QtCore import (
    Qt, QRectF, QPropertyAnimation, QEasingCurve, QTimer, QSize
)
from PyQt5.QtGui import (
    QPainter, QColor, QBrush, QFont, QPainterPath, QPen, QLinearGradient, QPixmap, QIcon
)

# --------------------------------------------------------------------
# 1) GlowButton
# --------------------------------------------------------------------
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtGui import QPainter, QColor, QFontMetrics
from PyQt5.QtCore import pyqtProperty, Qt

def interpolate_color(c1, c2, t):
    """Linearly interpolate between two QColor objects in [0..1]."""
    r = c1.red() + (c2.red() - c1.red()) * t
    g = c1.green() + (c2.green() - c1.green()) * t
    b = c1.blue() + (c2.blue() - c1.blue()) * t
    return QColor(int(r), int(g), int(b))

class GlowButton(QPushButton):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._glowStrength = 0.0
        
        # Font, color logic remains the same
        self.setFont(QFont("Arial", 14, QFont.Bold))
        self.inactiveColor = QColor("#808080")
        self.activeColor   = QColor("#eeeeee")
        
        # Darker background gradient
        self.setStyleSheet(
            """
            QPushButton {
                background-color: qlineargradient(
                    spread:pad, x1:0.5, y1:0, x2:0.5, y2:1,
                    stop:0 #444444, stop:1 #222222
                );
                border: 2px solid #333;
                border-radius: 20px;
            }
            QPushButton:pressed {
                background-color: qlineargradient(
                    spread:pad, x1:0.5, y1:0, x2:0.5, y2:1,
                    stop:0 #222222, stop:1 #444444
                );
            }
            """
        )
    

    # glowStrength property
    def getGlowStrength(self):
        return self._glowStrength

    def setGlowStrength(self, value):
        self._glowStrength = value
        self.update()  # re-paint when changed

    @pyqtProperty(float)
    def glowStrength(self):
        return self._glowStrength

    @glowStrength.setter
    def glowStrength(self, value):
        self.setGlowStrength(value)

    # main painting
    def paintEvent(self, event):
        # Paint normal button (background & default text)
        super().paintEvent(event)

        if self._glowStrength > 0 and self.text():
            painter = QPainter(self)
            painter.setRenderHint(QPainter.TextAntialiasing)

            # Interpolate text color
            text_color = interpolate_color(self.inactiveColor, self.activeColor, self._glowStrength)

            fm = painter.fontMetrics()
            text_width = fm.horizontalAdvance(self.text())
            # We'll center the text. Use int() so no TypeError
            x = int((self.width() - text_width) / 2)
            y = int((self.height() + fm.ascent() - fm.descent()) / 2)

            # Subtle glow radius & alpha
            radius = 1  # smaller radius => less intense
            base_alpha = int(100 * self._glowStrength)  # up to 100, not too bright

            # Paint multiple offsets with partial alpha
            for dx in range(-radius, radius+1):
                for dy in range(-radius, radius+1):
                    dist2 = dx*dx + dy*dy
                    if dist2 == 0:
                        continue
                    local_alpha = base_alpha - (dist2 * 20)
                    if local_alpha < 0:
                        continue
                    glow_col = QColor(text_color.red(), text_color.green(), text_color.blue(), local_alpha)
                    painter.setPen(glow_col)
                    painter.drawText(x+dx, y+dy, self.text())

            # Finally, main text on top
            painter.setPen(text_color)
            painter.drawText(x, y, self.text())


# --------------------------------------------------------------------
# 2) AppLaunchButton - Subclass GlowButton to show a right-click QMenu
# --------------------------------------------------------------------
TOP_APPS = [
    ("Netflix", "/launch/12"),
    ("Hulu", "/launch/2285"),
    ("Max", "/launch/61322"),
    ("Apple TV", "/launch/551012"),
    ("Disney+", "/launch/291097"),
    ("Prime Video", "/launch/13"),
    ("YouTube", "/launch/837"),
    ("Paramount+", "/launch/291098"),
    ("Peacock", "/launch/593099"),
    ("ESPN+", "/launch/55270"),
    ("Crunchyroll", "/launch/2595"),
]

APP_ICONS = {
    "Netflix": "./img/netflix.png",
    "Hulu": "./img/hulu.png",
    "Max": "./img/max.png",
    "Apple TV": "./img/apple.png",
    "Disney+": "./img/disney.png",
    "Prime Video": "./img/prime.png",
    "YouTube": "./img/youtube.png",
    "Paramount+": "./img/paramount.png",
    "Peacock": "./img/peacock.png",
    "ESPN+": "./img/espn.png",
    "Crunchyroll": "./img/crunchyroll.png",
}

class AppLaunchButton(GlowButton):
    """
    A GlowButton that can show a custom icon in a 'dim' or 'bright' state,
    depending on glowStrength. Right-click changes self.command_name
    and can also change the image, if desired.
    """
    def __init__(self, text="", command_name="", parent=None):
        super().__init__(text, parent)
        self.command_name = command_name
        
        self._image = None    # We'll store the QPixmap
        self._imageScaled = None  # We'll store a scaled version that fits the button

    def setImage(self, image_path):
        """Load the image from 'image_path' and store it. We'll paint it in paintEvent()."""
        px = QPixmap(image_path)
        if not px.isNull():
            # Scale it to ~70% of the button size (like you do with setIconSize)
            w = int(self.width() * 0.7)
            h = int(self.height() * 0.7)
            self._image = px.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        else:
            self._image = None

        self.update()  # repaint

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            # Show a context menu listing the top apps
            menu = QMenu(self)
            for (app_label, app_cmd) in TOP_APPS:
                action = menu.addAction(app_label)
                def handler(checked=False, cmd=app_cmd, lbl=app_label):
                    self.command_name = cmd
                    icon_path = APP_ICONS.get(lbl)
                    if icon_path:
                        self.setImage(icon_path)
                action.triggered.connect(handler)
            menu.exec_(event.globalPos())
        else:
            # Normal left-click => pass to GlowButton
            super().mousePressEvent(event)

    def paintEvent(self, event):
        # 1) Let the GlowButton draw background + text
        super().paintEvent(event)

        # 2) If we have an image, paint it with partial opacity
        if self._image:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)

            # We'll fade icon from 50% opaqueness to 100% opaqueness
            # as glowStrength goes from 0..1
            alpha_factor = 0.5 + 0.5 * self.glowStrength  # [0.5..1.0]

            painter.setOpacity(alpha_factor)

            # Center the pixmap in the button
            x = (self.width()  - self._image.width())  // 2
            y = (self.height() - self._image.height()) // 2
            painter.drawPixmap(x, y, self._image)
            painter.end()

# --------------------------------------------------------------------
# 3) RokuRemote - the main window
# --------------------------------------------------------------------
class RokuRemote(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setFixedSize(220, 400)
        self.setWindowTitle("Roku Remote")
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.dragging = False  # for window dragging

        self.IP = ""
        self.found = False

        # Keep references to all GlowButtons for fade logic
        self.remote_buttons = []

        # Idle Timers & Animations
        self.idle_timer = QTimer(self)
        self.idle_timer.setInterval(10_000)  # 10s
        self.idle_timer.timeout.connect(self.fade_out_buttons)

        # Main widget
        self.centralWidget = QWidget(self)
        self.setCentralWidget(self.centralWidget)

        # Tab Widget
        self.tabs = QTabWidget(self.centralWidget)
        self.tabs.setGeometry(0, 0, self.width(), self.height())
        self.tabs.setStyleSheet(
            "QTabWidget::pane { border: 0; } "
            "QTabBar::tab { background: #4B0082; color: white; padding: 10px; border-radius: 5px; margin: 2px; } "
            "QTabBar::tab:selected { background: #7c4dff; } "
        )

        # Add tabs
        self.add_remote_tab()
        self.add_typing_tab()
        self.add_connect_tab()

        # Close button top-right corner
        self.close_button = QPushButton(self)
        self.close_button.setFixedSize(20, 20)
        self.close_button.move(self.width() - 25, 5)
        self.close_button.setStyleSheet(
            "QPushButton {"
            "background-color: #808080; border-radius: 10px; color: red; font-weight: bold; text-align: center; "
            "} QPushButton:hover { background-color: #333; }"
        )
        self.close_button.setText("X")
        self.close_button.clicked.connect(self.close)

        # Start with text in dim mode
        self.fade_out_buttons(instant=True)

    # ---------------------------
    # IDLE LOGIC
    # ---------------------------
    def reset_idle_timer(self):
        """User is interacting; fade in the button text and restart the idle timer."""
        self.fade_in_buttons()
        self.idle_timer.start()

    def fade_in_buttons(self):
        """Animate all buttons from current glowStrength to 1.0."""
        for btn in self.remote_buttons:
            anim = QPropertyAnimation(btn, b"glowStrength", self)
            anim.setDuration(500)
            anim.setStartValue(btn.glowStrength)
            anim.setEndValue(1.0)
            anim.setEasingCurve(QEasingCurve.InOutQuad)
            anim.start()
            btn._currentAnim = anim

    def fade_out_buttons(self, instant=False):
        """Animate all buttons to 0.0 after 10s inactivity."""
        for btn in self.remote_buttons:
            if instant:
                btn.glowStrength = 0.0
                continue

            anim = QPropertyAnimation(btn, b"glowStrength", self)
            anim.setDuration(500)
            anim.setStartValue(btn.glowStrength)
            anim.setEndValue(0.0)
            anim.setEasingCurve(QEasingCurve.InOutQuad)
            anim.start()
            btn._currentAnim = anim

    # ---------------------------
    # TABS
    # ---------------------------
    def add_remote_tab(self):
        remote_tab = QWidget()
        layout = QVBoxLayout(remote_tab)
        layout.setContentsMargins(15, 10, 15, 15)
        layout.setSpacing(2)

        # status label
        self.remote_status_label = QLabel("Roku Remote")
        self.remote_status_label.setAlignment(Qt.AlignCenter)
        self.remote_status_label.setStyleSheet("QLabel { color: white; font-size: 10pt; }")
        layout.addWidget(self.remote_status_label, alignment=Qt.AlignCenter)
        

        # Power button
        pwr_btn = self.create_button("⏻", "/keypress/power", size=40)
        layout.addWidget(pwr_btn, alignment=Qt.AlignCenter)

        # Back / Home
        row_bh = QWidget()
        row_bh_layout = QHBoxLayout(row_bh)
        row_bh_layout.setSpacing(5)
        row_bh_layout.setContentsMargins(20, 20, 20, 0)

        back_btn = self.create_button("⏴", "/keypress/back", size=(50, 30))
        home_btn = self.create_button("⌂", "/keypress/home", size=(50, 30))
        row_bh_layout.addWidget(back_btn, alignment=Qt.AlignLeft)
        row_bh_layout.addWidget(home_btn, alignment=Qt.AlignRight)
        layout.addWidget(row_bh, alignment=Qt.AlignCenter)

        ## Nav
        #nav_widget = QWidget()
        #nav_layout = QVBoxLayout(nav_widget)
        #nav_layout.setSpacing(5)
        #nav_layout.setContentsMargins(0, 0, 0, 0)
#
        #up_btn = self.create_button("▲", "/keypress/up")
        #nav_layout.addWidget(up_btn, alignment=Qt.AlignCenter)
#
        #middle_row = QWidget()
        #middle_row_layout = QHBoxLayout(middle_row)
        #middle_row_layout.setSpacing(5)
        #middle_row_layout.setContentsMargins(0, 0, 0, 0)
#
        #left_btn  = self.create_button("◀", "/keypress/left")
        #ok_btn    = self.create_button("OK", "/keypress/select")
        #right_btn = self.create_button("▶", "/keypress/right")
        #middle_row_layout.addWidget(left_btn, alignment=Qt.AlignLeft)
        #middle_row_layout.addWidget(ok_btn, alignment=Qt.AlignCenter)
        #middle_row_layout.addWidget(right_btn, alignment=Qt.AlignRight)
        #nav_layout.addWidget(middle_row)
#
        #down_btn = self.create_button("▼", "/keypress/down")
        #nav_layout.addWidget(down_btn, alignment=Qt.AlignCenter)
#
        #layout.addWidget(nav_widget, alignment=Qt.AlignCenter)

        dpad = DPadCrossWidget(self)
        layout.addWidget(dpad, alignment=Qt.AlignCenter)

        # B1-B4 row
        b_buttons = QWidget()
        b_layout = QGridLayout(b_buttons)
        b_layout.setSpacing(5)
        b_layout.setContentsMargins(20, 5, 20, 5)

        # Create B1
        b1 = self.create_button("", "/launch/2285", size=(50, 30))
        b1.setImage("./img/hulu.png")

        # Create B2
        b2 = self.create_button("", "/launch/12", size=(50, 30))
        b2.setImage("./img/netflix.png")

        # Create B3
        b3 = self.create_button("", "/launch/61322", size=(50, 30))
        b3.setImage("./img/max.png")

        # Create B4
        b4 = self.create_button("", "/launch/551012", size=(50, 30))
        b4.setImage("./img/apple.png")

        b_layout.addWidget(b1, 0, 0)
        b_layout.addWidget(b2, 0, 1)
        b_layout.addWidget(b3, 1, 0)
        b_layout.addWidget(b4, 1, 1)
        layout.addWidget(b_buttons, alignment=Qt.AlignCenter)

        self.tabs.addTab(remote_tab, "Remote")

    def add_typing_tab(self):
        typing_tab = QWidget()
        layout = QVBoxLayout(typing_tab)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        self.text_input = QLineEdit(typing_tab)
        self.text_input.setPlaceholderText("Type your text here...")
        self.text_input.setFixedHeight(30)
        self.text_input.setStyleSheet("background-color: #606060; color: white; border-radius: 5px; padding: 5px;")
        layout.addWidget(self.text_input)

        enter_button = QPushButton("Enter", typing_tab)
        enter_button.setFixedSize(80, 30)
        enter_button.setFont(QFont("Arial", 10, QFont.Bold))
        enter_button.setStyleSheet(
            "QPushButton {"
            "  background-color: #4B0082; color: white; border-radius: 5px;"
            "} QPushButton:pressed { background-color: #7c4dff; }"
        )
        enter_button.clicked.connect(self.on_enter_pressed)
        layout.addWidget(enter_button, alignment=Qt.AlignCenter)

        # self.tabs.addTab(typing_tab, "Search")

    def add_connect_tab(self):
        connect_tab = QWidget()
        connect_layout = QVBoxLayout(connect_tab)
        connect_layout.setSpacing(10)
        connect_layout.setContentsMargins(20, 20, 20, 20)

        self.connect_label = QLabel("Click 'Scan' to find Roku")
        self.connect_label.setStyleSheet("QLabel { color: white; font-size: 12pt; }")
        connect_layout.addWidget(self.connect_label, alignment=Qt.AlignCenter)

        scan_button = QPushButton("Scan")
        scan_button.setFixedSize(80, 30)
        scan_button.setFont(QFont("Arial", 10, QFont.Bold))
        scan_button.setStyleSheet(
            "QPushButton {"
            "  background-color: #4B0082; color: white; border-radius: 5px;"
            "} QPushButton:pressed { background-color: #7c4dff; }"
        )
        scan_button.clicked.connect(self.scan_network_for_roku)
        connect_layout.addWidget(scan_button, alignment=Qt.AlignCenter)

        self.tabs.addTab(connect_tab, "Connect")

    # ---------------------------
    # NETWORK SCAN
    # ---------------------------
    def get_all_subnets(self):
        subnets = []
        try:
            output = subprocess.check_output("ipconfig", text=True).splitlines()
            for line in output:
                if "IPv4 Address" in line or "Subnet Mask" in line:
                    ip_match = re.search(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", line)
                    if ip_match:
                        ip = ip_match.group(1)
                        subnet = '.'.join(ip.split('.')[:-1]) + '.1/24'
                        subnets.append(subnet)
            return list(set(subnets))
        except Exception as e:
            self.connect_label.setText(f"Failed to fetch subnets: {e}")
            self.connect_label.setStyleSheet("color: red;")
            return []

    def scan_network_for_roku(self):
        self.IP = ""
        self.found = False

        subnets = self.get_all_subnets()
        if not subnets:
            self.connect_label.setText("No subnets found to scan")
            self.connect_label.setStyleSheet("color: red;")
            return

        for subnet in subnets:
            self.connect_label.setText(f"Scanning {subnet}...")
            self.connect_label.setStyleSheet("color: white;")
            QApplication.processEvents()

            arp = ARP(pdst=subnet)
            ether = Ether(dst="ff:ff:ff:ff:ff:ff")
            packet = ether / arp
            result = srp(packet, timeout=3, verbose=False)[0]

            devices = []
            for sent, received in result:
                devices.append({'ip': received.psrc, 'mac': received.hwsrc})

            for device in devices:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(1)
                    if sock.connect_ex((device['ip'], 8060)) == 0:
                        self.IP = device['ip']
                        self.found = True
                        self.connect_label.setText(f"""
Roku found at {self.IP}

Make sure the Roku is not in Limited 
or Guest mode.

To fix:
1) On Roku, go to Settings → System → 
    Advanced system settings → 
    External control.
2) Set Network access to 'Default' 
    or 'Permissive' (not 'Limited').
3) If in Guest Mode, sign out of
     Guest Mode.
""")
                        self.connect_label.setStyleSheet("color: green;")
                        sock.close()
                        return
                except Exception:
                    continue

        self.connect_label.setText("No Roku found on the network")
        self.connect_label.setStyleSheet("color: red;")

    # ---------------------------
    # TYPING
    # ---------------------------
    def on_enter_pressed(self):
        text = self.text_input.text()
        print(f"Entered text: {text}")
        self.text_input.clear()

    # ---------------------------
    # COMMAND
    # ---------------------------
    def send_command(self, command):
        self.reset_idle_timer()
        if not self.found:
            self.remote_status_label.setText("Connect Roku first!")
            self.remote_status_label.setStyleSheet("color: red;")
            return
        try:
            url = f"http://{self.IP}:8060{command}"
            requests.post(url)
            self.remote_status_label.setText(f"Command '{command}' sent!")
            self.remote_status_label.setStyleSheet("color: green;")
        except Exception as e:
            self.remote_status_label.setText(f"Error sending '{command}': {e}")
            self.remote_status_label.setStyleSheet("color: red;")

    # ---------------------------
    # DRAW / STYLE
    # ---------------------------
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 1) Draw main gradient background
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0, QColor("#2b2b2b"))
        gradient.setColorAt(1, QColor("#1e1e1e"))
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)

        rect = QRectF(self.rect().adjusted(0, 0, -1, -1))
        path = QPainterPath()
        path.addRoundedRect(rect, 15, 15)
        painter.drawPath(path)

        # 2) Border
        border_pen = QPen(QColor("#1e1e1e"), 2)
        painter.setPen(border_pen)
        painter.drawPath(path)

        # 3) Purple "ribbon" at bottom
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        ribbon_color = QColor("#4B0082")
        painter.setBrush(QBrush(ribbon_color))
        painter.setPen(Qt.NoPen)

        base_y = self.height() - 1
        ribbon_height = 30
        ribbon_width = 80
        left_x = (self.width() - ribbon_width) / 2
        ribbon_rect = QRectF(left_x, base_y, ribbon_width, ribbon_height)
        painter.drawRect(ribbon_rect)

        # 4) "ROKU" text
        painter.setPen(QPen(Qt.white))
        font = QFont("Arial", 10, QFont.Bold)
        painter.setFont(font)
        painter.drawText(ribbon_rect, Qt.AlignCenter, "ROKU")
        painter.restore()

    # ---------------------------
    # DRAG
    # ---------------------------
    def mousePressEvent(self, event):
        self.reset_idle_timer()
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        self.reset_idle_timer()
        if self.dragging and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.reset_idle_timer()
        self.dragging = False
        event.accept()

    # ---------------------------
    # CREATE BUTTON
    # ---------------------------
    def create_button(self, text, command_name, size=40, circular=False):
        btn = AppLaunchButton(text=text, command_name=command_name)
        if isinstance(size, tuple):
            w, h = size
            btn.setFixedSize(w, h)
        else:
            btn.setFixedSize(size, size)

        # 1) Back ("⏴") or Home ("⌂") => normal dark rectangle button
        if text in ["⌂", "⏴"]:
            btn.setStyleSheet("""
                QPushButton {
                    /* Dark gradient background */
                    background-color: qlineargradient(
                        spread:pad, x1:0.5, y1:0, x2:0.5, y2:1,
                        stop:0 #444444, stop:1 #222222
                    );
                    border: 2px solid #333;
                    border-radius: 8px; /* slight rounding, or 0 if fully rectangular */
                    color: #808080;     /* text color */
                    font-weight: bold;
                }
                QPushButton:pressed {
                    /* Invert the gradient for a pressed effect */
                    background-color: qlineargradient(
                        spread:pad, x1:0.5, y1:0, x2:0.5, y2:1,
                        stop:0 #222222, stop:1 #444444
                    );
                }
            """)
    
        # 2) Power ("⏻") => dark circular button
        elif text == "⏻":
            diameter = btn.width()  # e.g. 40 or 45
            radius   = diameter // 2
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: qlineargradient(
                        spread:pad, x1:0.5, y1:0, x2:0.5, y2:1,
                        stop:0 #444444, stop:1 #222222
                    );
                    border: 2px solid #333;
                    border-radius: {radius}px; /* fully circular */
                    color: #808080;
                    font-weight: bold;
                }}
                QPushButton:pressed {{
                    background-color: qlineargradient(
                        spread:pad, x1:0.5, y1:0, x2:0.5, y2:1,
                        stop:0 #222222, stop:1 #444444
                    );
                }}
            """)

        elif text == "OK":
            # Make the OK button a circular 3D purple gradient
            diameter = btn.width()  # e.g. 45
            radius   = diameter // 2
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: qlineargradient(
                        spread:pad, x1:0.5, y1:0, x2:0.5, y2:1,
                        stop:0 #7c4dff, stop:1 #4B0082
                    );
                    border: 2px solid #2e004d;
                    border-radius: {radius}px;
                    color: #808080;
                    font-weight: bold;
                }}
                QPushButton:pressed {{
                    background-color: qlineargradient(
                        spread:pad, x1:0.5, y1:0, x2:0.5, y2:1,
                        stop:0 #4B0082, stop:1 #7c4dff
                    );
                }}
            """)
        elif text in ["▲","▼"]:
            # Make arrow buttons transparent
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: none;
                    color: #808080;
                    font-weight: bold;
                    font-size: 24px;
                }
                QPushButton:pressed {
                    background-color: rgba(255,255,255,0.2);
                }
            """)
        elif text in ["◀","▶"]:
            # Make arrow buttons transparent
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: none;
                    color: #808080;
                    font-weight: bold;
                    font-size: 32px;
                }
                QPushButton:pressed {
                    background-color: rgba(255,255,255,0.2);
                }
            """)
    

        btn.clicked.connect(lambda: self.send_command(btn.command_name))
        self.remote_buttons.append(btn)
        return btn


class DPadCrossWidget(QWidget):
    def __init__(self, remote, parent=None):
        super().__init__(parent)
        self.remote = remote

        self.setFixedSize(150, 150)  # bigger than the space your buttons need

        # We'll use an absolute layout approach for the arrow/OK so
        # we can position them exactly near the center, close together.
        # We'll just remove the QGridLayout entirely for total control.
        self.up_btn = remote.create_button("▲", "/keypress/up", size=45, circular=False)
        self.up_btn.setParent(self)

        self.left_btn = remote.create_button("◀", "/keypress/left", size=45)
        self.left_btn.setParent(self)

        self.ok_btn = remote.create_button("OK", "/keypress/select", size=45)
        self.ok_btn.setParent(self)

        self.right_btn= remote.create_button("▶", "/keypress/right", size=45)
        self.right_btn.setParent(self)

        self.down_btn = remote.create_button("▼", "/keypress/down", size=45)
        self.down_btn.setParent(self)

        # We'll do the margin, corner radius for painting
        self._margin = 4
        self._cornerR = 15

    def resizeEvent(self, event):
        """
        Position the 5 buttons in a tight cluster near the center,
        ignoring any 'leftover' space in the widget, so we can
        paint arms that extend around them.
        """
        super().resizeEvent(event)
        w = self.width()
        h = self.height()
        cx = w // 2
        cy = h // 2

        # Let's cluster them in ~130x130 region in the center
        # For example, the entire center region is from (cx-65, cy-65) to (cx+65, cy+65)
        cluster_side = 130
        cluster_left = cx - cluster_side//2
        cluster_top  = cy - cluster_side//2

        # The OK button goes right in the cluster's center
        # => i.e. at (cx-22, cy-22) if the button is 45x45
        ok_x = cluster_left + (cluster_side - 45)//2
        ok_y = cluster_top  + (cluster_side - 45)//2
        self.ok_btn.move(ok_x, ok_y)

        # The arrow buttons: let's place them around OK with minimal gap
        gap = 3  # how many px to separate each arrow from OK
        # up is above OK
        self.up_btn.move(ok_x, ok_y - 45 + gap)
        # down is below OK
        self.down_btn.move(ok_x, ok_y + 45 - gap)
        # left is to the left of OK
        self.left_btn.move(ok_x - 45 + gap, ok_y)
        # right is to the right of OK
        self.right_btn.move(ok_x + 45 - gap, ok_y)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        fillColor   = QColor("#4B0082")
        borderColor = QColor("#2e004d")
        painter.setBrush(fillColor)
        painter.setPen(QPen(borderColor, 3))

        crossPath = QPainterPath()

        # unify geometry of each arrow/OK button
        for btn in [self.up_btn, self.left_btn, self.ok_btn, self.right_btn, self.down_btn]:
            r = btn.geometry().adjusted(-self._margin, -self._margin, self._margin, self._margin)
            rF = QRectF(r)
            subPath = QPainterPath()
            subPath.addRoundedRect(rF, self._cornerR, self._cornerR)
            crossPath += subPath

        painter.drawPath(crossPath)
        painter.end()



# --------------------------------------------------------------------
# 4) Main Entry
# --------------------------------------------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RokuRemote()
    window.show()
    sys.exit(app.exec_())
