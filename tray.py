# -*- coding: utf-8 -*-
"""系统托盘菜单。"""
from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QAction
from config import resource_path, APP_NAME


class TrayIcon(QSystemTrayIcon):
    def __init__(self, window, on_settings, on_quit):
        super().__init__()
        self.window = window
        self.on_settings = on_settings
        self.on_quit = on_quit
        icon_path = resource_path("assets", "icons", "app.ico")
        try:
            self.setIcon(QIcon(str(icon_path)))
        except Exception:
            self.setIcon(QIcon())
        self.setToolTip(APP_NAME)
        self._build_menu()
        self.activated.connect(self._on_activated)

    def _build_menu(self):
        m = QMenu()
        self.a_show = QAction("显示宠物"); self.a_show.triggered.connect(self.window.show_pets); m.addAction(self.a_show)
        self.a_hide = QAction("隐藏宠物"); self.a_hide.triggered.connect(self.window.hide_pets); m.addAction(self.a_hide)
        m.addSeparator()
        self.a_pause = QAction("暂停活动"); self.a_pause.setCheckable(True)
        self.a_pause.triggered.connect(self._toggle_pause); m.addAction(self.a_pause)
        self.a_reminder = QAction("暂停提醒"); self.a_reminder.setCheckable(True)
        self.a_reminder.triggered.connect(self._toggle_reminder); m.addAction(self.a_reminder)
        m.addSeparator()
        self.a_settings = QAction("设置…"); self.a_settings.triggered.connect(self.on_settings); m.addAction(self.a_settings)
        m.addSeparator()
        self.a_quit = QAction("退出"); self.a_quit.triggered.connect(self.on_quit); m.addAction(self.a_quit)
        self.setContextMenu(m)

    def _on_activated(self, reason):
        # 双击托盘 → 显示/隐藏
        if reason == QSystemTrayIcon.DoubleClick:
            if self.window.settings.pets_visible:
                self.window.hide_pets()
            else:
                self.window.show_pets()

    def _toggle_pause(self, checked):
        self.window.settings.activity_paused = checked

    def _toggle_reminder(self, checked):
        self.window.settings.reminders_paused = checked

    def sync_state(self):
        self.a_pause.setChecked(self.window.settings.activity_paused)
        self.a_reminder.setChecked(self.window.settings.reminders_paused)
