# -*- coding: utf-8 -*-
"""声音系统（预留接口）。目前无素材，先设计接口，默认静音。"""
from PySide6.QtCore import QObject, Signal


class SoundSystem(QObject):
    def __init__(self, settings):
        super().__init__()
        self.settings = settings

    def play(self, kind: str):
        """kind: meow / purr / hungry / happy"""
        if not self.settings.sound_enabled:
            return
        # TODO: 有素材后用 QSoundEffect 播放 assets/sounds/<kind>.wav
        # 当前预留
        pass
