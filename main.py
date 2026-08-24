# -*- coding: utf-8 -*-
"""双猫桌面宠物 · 主入口"""
import sys
import os
import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

from config import APP_NAME
from state import load, save, save_file, default_state
from pet_window import PetWindow
from settings_dialog import SettingsDialog
from first_run import FirstRunWizard
from tray import TrayIcon
from sound import SoundSystem


def ensure_app_id_windows():
    """让 Win10 任务栏不把窗口归到 python.exe，避免分组混乱。"""
    if sys.platform.startswith("win"):
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("dualcat.pet.v1")
        except Exception:
            pass


def main():
    ensure_app_id_windows()
    QApplication.setQuitOnLastWindowClosed(False)
    # Tool 窗口不应抢焦点
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)

    # 加载状态
    cat_a_data, cat_b_data, settings = load()
    is_first_run = (settings.last_save_ts == 0)

    if is_first_run:
        wiz = FirstRunWizard()
        wiz.cat_a_name = "小橘"; wiz.cat_b_name = "小灰"
        if wiz.exec():
            settings.cat_a_name = wiz.cat_a_name
            settings.cat_b_name = wiz.cat_b_name
            settings.area_preset = wiz.area_preset
            settings.pet_size = wiz.pet_size
            cat_a_data.name = wiz.cat_a_name
            cat_b_data.name = wiz.cat_b_name

    window = PetWindow(cat_a_data, cat_b_data, settings)
    sound = SoundSystem(settings)

    def do_save():
        cat_a_data.name = settings.cat_a_name
        cat_b_data.name = settings.cat_b_name
        cat_a_data.last_state = window.cat_a.current.value
        cat_b_data.last_state = window.cat_b.current.value
        save(cat_a_data, cat_b_data, settings)

    window._save_cb = do_save

    def open_settings():
        dlg = SettingsDialog(settings, parent=None)
        if dlg.exec():
            # 应用：改名 / 大小 / 区域 / 显示器 / 速度
            window.apply_area_and_size()
            window.cat_a.data.name = settings.cat_a_name
            window.cat_b.data.name = settings.cat_b_name
            do_save()

    def quit_app():
        do_save()
        app.quit()

    tray = TrayIcon(window, open_settings, quit_app)
    tray.show()

    window.start()

    # 退出时保存
    app.aboutToQuit.connect(do_save)

    # 定期同步托盘状态
    sync = QTimer(); sync.setInterval(2000); sync.timeout.connect(tray.sync_state); sync.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
