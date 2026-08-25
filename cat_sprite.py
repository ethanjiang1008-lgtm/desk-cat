# -*- coding: utf-8 -*-
"""CatSprite：单只猫的渲染组件。
基于 Pillow 解码 WebP 逐帧动画（不依赖 Qt WebP 插件，PyInstaller 打包后更可靠），
按目标尺寸缩放、按朝向水平翻转，自绘 alpha。
缓存当前显示帧 QImage，供窗口做逐像素点击穿透判定。"""
from PySide6.QtCore import Qt, Signal, QRectF, QPointF, QTimer
from PySide6.QtGui import QPixmap, QPainter, QTransform, QImage
from PySide6.QtWidgets import QWidget

from config import asset_path, SIZE_PRESETS
from PIL import Image, ImageSequence


class CatSprite(QWidget):
    clicked = Signal()
    double_clicked = Signal()
    drag_started = Signal(QPointF)
    drag_moved = Signal(QPointF)
    drag_ended = Signal()
    right_clicked = Signal(QPointF)

    def __init__(self, group: str, parent=None):
        super().__init__(parent)
        self.group = group
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WA_OpaquePaintEvent, False)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setFocusPolicy(Qt.NoFocus)

        self._frames = {}            # action -> [(QImage, duration_ms), ...]
        self._cur_action = None
        self._frame_idx = 0
        self._facing = 1
        self._display_h = SIZE_PRESETS["medium"]
        self._display_w = 140
        self._pix = None             # 当前源帧 QImage（原始尺寸）
        self._disp_img = QImage()    # 缓存的显示帧（含 alpha，display 尺寸）
        self._dragging = False
        self._drag_press = None
        self._last_click_ts = 0
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(120)
        self._anim_timer.timeout.connect(self._advance_frame)
        self.resize(self._display_w, self._display_h)

    # —— WebP 加载（Pillow 解码，不依赖 Qt WebP 插件）——
    def _load_action(self, action: str):
        path = str(asset_path(self.group, action))
        try:
            img = Image.open(path)
        except Exception as e:
            print(f"[sprite] 无法加载动画 {path}: {e}")
            return None
        frames = []
        for frame in ImageSequence.Iterator(img):
            rgba = frame.convert("RGBA")
            data = rgba.tobytes()
            w, h = rgba.size
            # QImage 不复制 data 缓冲，必须 .copy() 深拷贝防止 Python bytes 被回收
            qimg = QImage(data, w, h, QImage.Format_RGBA8888).copy()
            duration = frame.info.get("duration", 120)
            frames.append((qimg, max(40, duration)))
        return frames if frames else None

    def set_display_height(self, h: int):
        self._display_h = h
        if self._cur_action and self._cur_action in self._frames:
            frames = self._frames[self._cur_action]
            if frames:
                qimg = frames[0][0]
                if qimg.height() > 0:
                    self._display_w = int(h * qimg.width() / qimg.height())
        self.resize(self._display_w, self._display_h)
        self._rebuild_disp_img()
        self.update()

    def set_action(self, action: str, facing: int = 1):
        self._facing = facing
        if action == self._cur_action and action in self._frames:
            self.update()
            return
        if action not in self._frames:
            frames = self._load_action(action)
            if frames is None:
                print(f"[sprite] 动画加载失败: {action}")
                return
            self._frames[action] = frames
        self._anim_timer.stop()
        self._cur_action = action
        frames = self._frames[action]
        self._frame_idx = 0
        if frames:
            qimg = frames[0][0]
            if qimg.height() > 0:
                self._display_w = int(self._display_h * qimg.width() / qimg.height())
        self.resize(self._display_w, self._display_h)
        self._pix = frames[0][0] if frames else None
        self._rebuild_disp_img()
        self._anim_timer.setInterval(frames[0][1] if frames else 120)
        self._anim_timer.start()
        self.update()

    def _advance_frame(self):
        frames = self._frames.get(self._cur_action)
        if not frames:
            return
        self._frame_idx = (self._frame_idx + 1) % len(frames)
        qimg, duration = frames[self._frame_idx]
        self._pix = qimg
        self._rebuild_disp_img()
        self._anim_timer.setInterval(duration)
        self.update()

    def _rebuild_disp_img(self):
        """构建当前显示帧（缩放+翻转）的 QImage，供点击穿透用。"""
        if self._pix is None or self._pix.isNull():
            self._disp_img = QImage()
            return
        pix = self._pix
        if self._facing < 0:
            t = QTransform()
            t.scale(-1, 1)
            t.translate(-self._display_w, 0)
            pix = pix.transformed(t, Qt.SmoothTransformation)
        self._disp_img = pix.scaled(
            self._display_w, self._display_h,
            Qt.IgnoreAspectRatio, Qt.SmoothTransformation)

    def opaque_at(self, local_pt) -> bool:
        """local_pt 为 sprite 内部坐标，返回该点是否为不透明像素。"""
        img = self._disp_img
        if img is None or img.isNull():
            return False
        x, y = int(local_pt.x()), int(local_pt.y())
        if x < 0 or y < 0 or x >= img.width() or y >= img.height():
            return False
        px = img.pixel(x, y)
        a = (px >> 24) & 0xFF
        return a > 40

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        if self._pix is None or self._pix.isNull():
            return
        pix = self._pix
        tgt = QRectF(0, 0, self._display_w, self._display_h)
        if self._facing < 0:
            t = QTransform()
            t.scale(-1, 1)
            t.translate(-self._display_w, 0)
            pix_t = pix.transformed(t, Qt.SmoothTransformation)
            p.drawImage(tgt, pix_t, QRectF(0, 0, pix_t.width(), pix_t.height()))
        else:
            p.drawImage(tgt, pix, QRectF(0, 0, pix.width(), pix.height()))
        p.end()

    # —— 鼠标 ——
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_press = e.globalPosition()
        elif e.button() == Qt.RightButton:
            self.right_clicked.emit(e.globalPosition())

    def mouseMoveEvent(self, e):
        if self._drag_press is not None and (e.buttons() & Qt.LeftButton):
            dist = (e.globalPosition() - self._drag_press).manhattanLength()
            if dist > 6 and not self._dragging:
                self._dragging = True
                self.drag_started.emit(e.position())
            if self._dragging:
                self.drag_moved.emit(e.globalPosition())

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.LeftButton:
            return
        if self._dragging:
            self._dragging = False
            self._drag_press = None
            self.drag_ended.emit()
            return
        self._drag_press = None
        now = e.timestamp()
        if now and now - self._last_click_ts < 350:
            self.double_clicked.emit()
            self._last_click_ts = 0
        else:
            self._last_click_ts = now or 1
            self.clicked.emit()
