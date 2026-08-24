# -*- coding: utf-8 -*-
"""PetWindow：透明、无边框、置顶的桌面宠物窗口。
- 跨越活动区域
- 逐像素点击穿透（透明区域不挡桌面，猫体可点）
- 主循环驱动两只猫 + 互动导演 + 提醒气泡
- 鼠标单击/双击/拖动/右键菜单"""
import math
import sys
import time
import random

from PySide6.QtCore import Qt, QTimer, QRect, QPoint, QPointF, Signal
from PySide6.QtGui import QGuiApplication, QPixmap, QPainter, QColor, QFont
from PySide6.QtWidgets import (QWidget, QLabel, QMenu, QApplication)

from config import (SIZE_PRESETS, AREA_PRESETS, ACTION_WALK, ACTION_SIT,
                   BOWL_POS, clamp, asset_path)
from behavior import CatState
from cat import CatController
from cat_sprite import CatSprite
from interactions import InteractionDirector
from state import Settings, CatState as CatData, _is_sleep_time


def _win():
    return sys.platform.startswith("win")


class Bubble(QLabel):
    """提醒气泡（猫旁边的小提示）。"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QLabel{ background: rgba(255,255,255,235); color:#333;
                    border:2px solid #ffb84d; border-radius:14px;
                    padding:6px 14px; font-size:14px;}
        """)
        self.setAlignment(Qt.AlignCenter)
        self.hide()

    def show_msg(self, text, x, y):
        self.setText(text)
        self.adjustSize()
        self.move(int(x - self.width() / 2), int(y - self.height()))
        self.raise_()
        self.show()


class PetWindow(QWidget):
    request_feed = Signal(object)   # cat
    request_water = Signal(object)
    open_settings = Signal()
    pause_toggled = Signal()

    def __init__(self, cat_a_data: CatData, cat_b_data: CatData, settings: Settings):
        super().__init__()
        self.settings = settings
        self.cat_a = CatController(cat_a_data, seed=101)
        self.cat_b = CatController(cat_b_data, seed=202)

        flags = Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WA_OpaquePaintEvent, False)
        self.setFocusPolicy(Qt.NoFocus)

        # 精灵
        self.sprite_a = CatSprite("catA", self)
        self.sprite_b = CatSprite("catB", self)
        self.inter_sprite = CatSprite("both", self)   # 双猫互动叠加层
        self.inter_sprite.hide()
        self.bubble = Bubble(self)

        # 碰撞避让用
        self._rng = random.Random(7)

        # 互动导演
        self.director = InteractionDirector(
            self.cat_a, self.cat_b, self.settings,
            render_hook=self._on_interaction_event, seed=303)

        # 走动到达监测
        self.cat_a._pending_arrive = None
        self.cat_b._pending_arrive = None

        self._connect_sprite(self.sprite_a, self.cat_a)
        self._connect_sprite(self.sprite_b, self.cat_b)

        # 主循环
        self._last_t = time.time()
        self._timer = QTimer(self)
        self._timer.setInterval(80)
        self._timer.timeout.connect(self._tick)
        self._autosave = QTimer(self)
        self._autosave.setInterval(30000)
        self._autosave.timeout.connect(self._do_autosave)

        self._area_rect = QRect(0, 0, 1920, 540)
        self._first_appear_done = not (settings.last_save_ts == 0)
        self._active = True

    # —— 初始化布局 ——
    def apply_area_and_size(self):
        screen = self._selected_screen()
        geo = screen.availableGeometry()
        preset = self.settings.area_custom or AREA_PRESETS.get(
            self.settings.area_preset, AREA_PRESETS["bottom"])
        ax = int(geo.x() + preset["x"] * geo.width())
        ay = int(geo.y() + preset["y"] * geo.height())
        aw = int(preset["w"] * geo.width())
        ah = int(preset["h"] * geo.height())
        self._area_rect = QRect(ax, ay, aw, ah)
        self.setGeometry(self._area_rect)
        # 走动速度：px/s -> 相对坐标/秒
        sp = self.settings.walk_speed / max(1, aw)
        self.cat_a.walk_speed = sp
        self.cat_b.walk_speed = sp
        h = SIZE_PRESETS.get(self.settings.pet_size, 140)
        self.sprite_a.set_display_height(h)
        self.sprite_b.set_display_height(h)
        # 互动叠加层更大
        self.inter_sprite.set_display_height(int(h * 1.05))

    def _selected_screen(self):
        screens = QGuiApplication.screens()
        idx = min(max(0, self.settings.monitor_index), len(screens) - 1)
        return screens[idx] if screens else QGuiApplication.primaryScreen()

    # —— 精灵信号 ——
    def _connect_sprite(self, sprite, cat):
        sprite.clicked.connect(lambda: self._on_click(cat))
        sprite.double_clicked.connect(lambda: self._on_dblclick(cat))
        sprite.drag_started.connect(lambda pos: self._on_drag_start(cat))
        sprite.drag_moved.connect(lambda gp: self._on_drag(cat, gp))
        sprite.drag_ended.connect(lambda: self._on_drag_end(cat))
        sprite.right_clicked.connect(lambda gp: self._on_right(cat, gp))
        sprite.set_action(cat.current.action, cat.data.facing)

    # —— 主循环 ——
    def start(self):
        self.show()
        self.apply_area_and_size()
        if not self._first_appear_done:
            self._first_appear()
        self._update_sprites()
        self._timer.start()
        self._autosave.start()

    def _tick(self):
        now = time.time()
        dt = min(0.25, now - self._last_t)
        self._last_t = now

        sleeping = _is_sleep_time(self.settings, now)

        if self._active and not self.settings.activity_paused:
            self.cat_a.advance(dt, self.settings.relationship, sleeping, None, self._area_rect)
            self.cat_b.advance(dt, self.settings.relationship, sleeping, None, self._area_rect)
            # 走动到达 → 触发吃饭/喝水
            for cat in (self.cat_a, self.cat_b):
                if (cat.current == CatState.WALK and cat.walk_target is None
                        and getattr(cat, "_pending_arrive", None)):
                    cat.on_arrive_target()
                elif (cat.current == CatState.WALK and cat.walk_target is None
                      and not getattr(cat, "_pending_arrive", None)):
                    cat.on_arrive_target()
            self.director.advance(dt, sleeping)
            # 关系缓慢回升
            self.settings.relationship = clamp(self.settings.relationship + 0.0008 * dt)

        self._avoid_overlap()
        self._update_sprites()
        self._check_reminders(now)

    # —— 渲染位置 ——
    def _rel_to_pixel(self, rx, ry, sprite):
        r = self._area_rect
        cx = r.x() + rx * r.width()
        cy = r.y() + ry * r.height()
        return int(cx - sprite.width() / 2), int(cy - sprite.height())

    def _update_sprites(self):
        # 互动叠加层
        if self.director.active:
            self.sprite_a.hide()
            self.sprite_b.hide()
            mx, my = self.director._mid
            self.inter_sprite.show()
            self.inter_sprite.set_action(self.director.active, 1)
            x, y = self._rel_to_pixel(mx, my, self.inter_sprite)
            # 叠加层以中点为底部中心
            r = self._area_rect
            cx = r.x() + mx * r.width()
            cy = r.y() + my * r.height()
            self.inter_sprite.move(int(cx - self.inter_sprite.width() / 2),
                                   int(cy - self.inter_sprite.height()))
            self.inter_sprite.raise_()
            return
        self.inter_sprite.hide()
        for sprite, cat in ((self.sprite_a, self.cat_a), (self.sprite_b, self.cat_b)):
            sprite.show()
            sprite.set_action(cat.current.action, cat.data.facing)
            x, y = self._rel_to_pixel(cat.data.x, cat.data.y, sprite)
            sprite.move(x, y)
            sprite.raise_()

    # —— 碰撞避让 ——
    def _avoid_overlap(self):
        if self.director.active:
            return
        a, b = self.cat_a.data, self.cat_b.data
        d = math.hypot(a.x - b.x, a.y - b.y)
        min_d = 0.06
        if 0 < d < min_d:
            push = (min_d - d) / 2
            dx = (a.x - b.x) / d if d > 0 else 1
            dy = (a.y - b.y) / d if d > 0 else 0
            a.x = clamp(a.x + dx * push)
            b.x = clamp(b.x - dx * push)
            a.y = clamp(a.y + dy * push)
            b.y = clamp(b.y - dy * push)

    # —— 首次登场动画 ——
    def _first_appear(self):
        # 从两边走入
        self.cat_a.data.x = -0.05
        self.cat_a.data.y = 0.7
        self.cat_a.data.facing = 1
        self.cat_a.walk_target = (0.30, 0.65)
        self.cat_a._transition(CatState.WALK)
        self.cat_b.data.x = 1.05
        self.cat_b.data.y = 0.7
        self.cat_b.data.facing = -1
        self.cat_b.walk_target = (0.62, 0.66)
        self.cat_b._transition(CatState.WALK)
        self._first_appear_done = True

    # —— 用户交互 ——
    def _on_click(self, cat):
        if not self.settings.click_enabled:
            return
        cat.on_click()
        cat.data.mood = clamp(cat.data.mood + 3)

    def _on_dblclick(self, cat):
        if not self.settings.click_enabled:
            return
        cat.on_double_click()

    def _on_drag_start(self, cat):
        if not self.settings.drag_enabled:
            return

    def _on_drag(self, cat, gp: QPointF):
        if not self.settings.drag_enabled:
            return
        r = self._area_rect
        rx = (gp.x() - r.x()) / r.width()
        ry = (gp.y() - r.y()) / r.height()
        cat.data.x = clamp(rx)
        cat.data.y = clamp(ry)
        cat.data.facing = cat.data.facing

    def _on_drag_end(self, cat):
        if not self.settings.drag_enabled:
            return
        cat.on_drag_end()

    def _on_right(self, cat, gp):
        menu = QMenu(self)
        a1 = menu.addAction(f"🍖 喂 {cat.data.name}")
        a2 = menu.addAction(f"💧 喝水")
        a3 = menu.addAction("✋ 抚摸一下")
        menu.addSeparator()
        a4 = menu.addAction("⚙️ 设置…")
        a5 = menu.addAction("⏸️ 暂停活动" if not self.settings.activity_paused else "▶️ 恢复活动")
        a6 = menu.addAction("🙈 隐藏宠物")
        menu.addSeparator()
        a7 = menu.addAction("❌ 退出")
        act = menu.exec(gp.toPoint())
        if act == a1:
            cat.feed()
        elif act == a2:
            cat.water()
        elif act == a3:
            cat.data.mood = clamp(cat.data.mood + 5)
            cat.data.affection = clamp(cat.data.affection + 3)
            cat._transition(CatState.GROOM)
        elif act == a4:
            self.open_settings.emit()
        elif act == a5:
            self.settings.activity_paused = not self.settings.activity_paused
            self.pause_toggled.emit()
        elif act == a6:
            self.settings.pets_visible = False
            self.hide()
        elif act == a7:
            QApplication.instance().quit()

    def _on_interaction_event(self, ev, action, mid):
        # 由导演回调：start/end
        if ev == "start":
            pass
        else:
            # 互动结束，恢复精灵
            pass

    # —— 提醒 ——
    def _check_reminders(self, now):
        import datetime
        if self.settings.reminders_paused:
            return
        t = datetime.datetime.fromtimestamp(now).strftime("%H:%M")
        # 喝水提醒
        if t in (self.settings.drink_reminders or []):
            self._fire_reminder("drink")
        # 喂食时间
        if t in (self.settings.feed_schedule or []):
            self._fire_reminder("feed")
        # 防止同一分钟重复触发：用上次触发记录
        self._last_reminder_min = getattr(self, "_last_reminder_min", "")
        cur_min = datetime.datetime.fromtimestamp(now).strftime("%H:%M")
        if cur_min == self._last_reminder_min:
            return
        self._last_reminder_min = cur_min

    _fired = set()

    def _fire_reminder(self, kind):
        import datetime
        now_min = datetime.datetime.now().strftime("%H:%M")
        key = f"{kind}:{now_min}"
        if key in self._fired:
            return
        self._fired.add(key)
        # 选一只猫提醒
        cat = self.cat_a if self.cat_a.data.hunger < self.cat_b.data.hunger else self.cat_b
        msg = "该喝水啦～" if kind == "drink" else "该吃饭啦～"
        r = self._area_rect
        bx = r.x() + cat.data.x * r.width()
        by = r.y() + cat.data.y * r.height() - 8
        self.bubble.show_msg(msg, bx, by)
        # 猫走向用户（屏幕中下）
        cat.walk_target = (0.5, 0.85) if kind == "drink" else (BOWL_POS["food"][0], BOWL_POS["food"][1])
        cat._transition(CatState.WALK)
        if kind == "drink":
            cat._pending_arrive = "drink"
        else:
            cat._pending_arrive = "eat"
        QTimer.singleShot(6000, self.bubble.hide)

    def _do_autosave(self):
        # 由 App 统一保存
        if hasattr(self, "_save_cb"):
            self._save_cb()

    # —— 显隐 ——
    def show_pets(self):
        self.settings.pets_visible = True
        self.show()
        self._timer.start()

    def hide_pets(self):
        self.settings.pets_visible = False
        self._timer.stop()
        self.hide()

    # —— Windows 逐像素点击穿透 ——
    def nativeEvent(self, eventType, message):
        # eventType 在 Windows 上为 bytes b"windows_generic_MSG"
        try:
            if bytes(eventType) == b"windows_generic_MSG":
                import ctypes
                from ctypes import wintypes
                WM_NCHITTEST = 0x0084
                HTTRANSPARENT = -1
                HTCLIENT = 1
                # message 是 MSG 结构指针（int 地址）
                addr = int(message)
                msg = wintypes.MSG.from_address(addr)
                if msg.message == WM_NCHITTEST:
                    lp = msg.lParam
                    x = ctypes.c_short(lp & 0xFFFF).value
                    y = ctypes.c_short((lp >> 16) & 0xFFFF).value
                    pt = self.mapFromGlobal(QPoint(x, y))
                    child = self.childAt(pt)
                    opaque = False
                    if isinstance(child, CatSprite):
                        local = child.mapFromParent(pt)
                        opaque = child.opaque_at(local)
                    if opaque:
                        return True, HTCLIENT
                    return True, HTTRANSPARENT
        except Exception as e:
            pass
        return super().nativeEvent(eventType, message)
