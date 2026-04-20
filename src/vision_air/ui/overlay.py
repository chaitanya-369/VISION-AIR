import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget
from PyQt5.QtCore import Qt, QTimer, QPoint, QRectF
from PyQt5.QtGui import QPainter, QColor, QPen, QFont, QBrush

class OverlayWindow(QMainWindow):
    def __init__(self, desk_dims):
        super().__init__()
        self.desk_w, self.desk_h = desk_dims
        
        # Transparent, Frameless, Topmost, Click-through
        self.setWindowFlags(
            Qt.FramelessWindowHint | 
            Qt.WindowStaysOnTopHint | 
            Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Match screen size
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)
        
        self.kb_layout = None
        self.hand_data = []
        self.mode = "MOUSE"
        
        # Colors - Minimalist Pro
        self.color_accent = QColor(0, 200, 255, 180) # Teal/Cyan
        self.color_bg = QColor(20, 20, 25, 60) # Super faint glass
        self.color_hit = QColor(255, 255, 255, 200) # White highlight
        
    def update_data(self, mode, hand_data, kb_layout=None):
        self.mode = mode
        self.hand_data = hand_data
        self.kb_layout = kb_layout
        self.update() # Triggers repaint

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if self.mode == "KEYBOARD" and self.kb_layout:
            self.draw_keyboard(painter)
            
        self.draw_cursors(painter)

    def draw_keyboard(self, painter):
        w, h = self.width(), self.height()
        
        # Draw keys
        for char, bbox in self.kb_layout.keys.items():
            x1, y1, x2, y2 = bbox
            px1, py1 = x1 * w, y1 * h
            px2, py2 = x2 * w, y2 * h
            
            rect = QRectF(px1, py1, px2 - px1, py2 - py1)
            
            # Key background
            painter.setBrush(QBrush(self.color_bg))
            painter.setPen(QPen(QColor(255, 255, 255, 40), 1))
            painter.drawRoundedRect(rect, 5, 5)
            
            # Label
            painter.setPen(QPen(QColor(255, 255, 255, 100)))
            painter.setFont(QFont("Segoe UI", 10))
            painter.drawText(rect, Qt.AlignCenter, char)

    def draw_cursors(self, painter):
        w, h = self.width(), self.height()
        
        for hand in self.hand_data:
            # Normalized desk coords -> Screen pixels
            sx, sy, sz = hand['smooth']
            # Note: sx, sy are expected in desk pixel range 0-1280.
            # Convert back to normalized for mapping to actual screen size.
            # Or just use the already defined mapping logic.
            
            # For the overlay, we map normalized desk coords to screen size
            # Since desk_w/desk_h are fixed, we just divide.
            rx = sx / self.desk_w
            ry = sy / self.desk_h
            
            px, py = rx * w, ry * h
            
            # Cursor Ring
            # Fixed radius for better stability, no longer pulsing with 'sz'
            radius = 18
            
            # Highlight color when in mouse pose
            color = self.color_accent if hand.get('mouse_pose') else QColor(130, 130, 130, 100)
            
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(color, 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            painter.drawEllipse(QPoint(int(px), int(py)), int(radius), int(radius))
            
            # Center dot
            painter.setBrush(QBrush(color))
            painter.drawEllipse(QPoint(int(px), int(py)), 4, 4)

def run_overlay_app(desk_dims, data_queue):
    app = QApplication(sys.argv)
    window = OverlayWindow(desk_dims)
    window.show()
    
    # Timer to poll the queue from the main process
    def poll_queue():
        if not data_queue.empty():
            data = data_queue.get()
            window.update_data(data['mode'], data['hand_data'], data.get('kb_layout'))
            
    timer = QTimer()
    timer.timeout.connect(poll_queue)
    timer.start(16) # ~60fps UI refresh
    
    sys.exit(app.exec_())
