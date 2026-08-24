# -*- coding: utf-8 -*-
"""CatSprite：单只猫的渲染组件。
基于 QMovie 逐帧取图，按目标尺寸缩放、按朝向水平翻转，自绘 alpha。
缓存当前显示帧 QImage，供窗口做逐像素点击穿透判定。"""
from PySide6.QtCore import Qt, Signal, QRectF, QPointF
from PySide6.QtGui import QMovie, QPixmap, QPainter, QTransform, QImage
from PySide6.QtWidgets import QWidget

from config import asset_path, SIZE_PRESETS


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

        self.movies = {}
        self._cur_action = None
        self._facing = 1
        self._display_h = SIZE_PRESETS["medium"]
        self._display_w = 140
        self._pix = None               # 当前源帧 QPixmap
        self._disp_img = QImage()      # 缓存的显示帧（含 alpha，display 尺寸）
        self._dragging = False
        self._drag_press = None
        self._last_click_ts = 0
        self.resize(self._display_w, self._display_h)

    def set_display_height(self, h: int):
        self._display_h = h
        if self._cur_action and self._cur_action in self.movies:
            m = self.movies[self._cur_action]
            sz = m.frameRect().size()
            if sz.height() > 0:
                self._display_w = int(h * sz.width() / sz.height())
        self.resize(self._display_w, self._display_h)
        self._rebuild_disp_img()
        self.update()

    def set_action(self, action: str, facing: int = 1):
        self._facing = facing
        if action == self._cur_action and action in self.movies:
            self.update()
            return
        if action not in self.movies:
            path = str(asset_path(self.group, action))
            m = QMovie(path)
            if not m.isValid():
                print(f"[sprite] 无效动画: {path}")
                return
            m.setCacheMode(QMovie.CacheAll)
            self.movies[action] = m
        if self._cur_action and self._cur_action in self.movies:
            try:
                self.movies[self._cur_action].frameChanged.disconnect(self._on_frame)
            except Exception:
                pass
            self.movies[self._cur_action].stop()
        self._cur_action = action
        m = self.movies[action]
        sz = m.frameRect().size()
        if sz.height() > 0:
            self._display_w = int(self._display_h * sz.width() / sz.height())
        self.resize(self._display_w, self._display_h)
        m.frameChanged.connect(self._on_frame)
        m.start()
        self.update()

    def _on_frame(self):
        m = self.movies.get(self._cur_action)
        if m is None:
            return
        self._pix = m.currentPixmap()
        self._rebuild_disp_img()
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
        self._disp_img = pix.toImage().scaled(
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
            p.drawPixmap(tgt, pix_t, QRectF(0, 0, pix_t.width(), pix_t.height()))
        else:
            p.drawPixmap(tgt, pix, QRectF(0, 0, pix.width(), pix.height()))
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
