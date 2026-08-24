# -*- coding: utf-8 -*-
"""设置对话框：宠物 / 时间 / 互动 / 声音 四个分组。"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                              QLabel, QLineEdit, QComboBox, QSpinBox, QCheckBox,
                              QSlider, QPushButton, QGroupBox, QGridLayout,
                              QTabWidget, QWidget, QTimeEdit, QListWidget,
                              QInputDialog, QMessageBox)
from PySide6.QtGui import QGuiApplication

from config import SIZE_PRESETS, AREA_PRESETS
from state import Settings


class SettingsDialog(QDialog):
    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("双猫桌面宠物 · 设置")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setMinimumWidth(420)

        tabs = QTabWidget()
        tabs.addTab(self._tab_pet(), "宠物")
        tabs.addTab(self._tab_time(), "时间")
        tabs.addTab(self._tab_inter(), "互动")
        tabs.addTab(self._tab_sound(), "声音")

        btns = QHBoxLayout()
        ok = QPushButton("保存"); ok.clicked.connect(self.accept)
        cancel = QPushButton("取消"); cancel.clicked.connect(self.reject)
        btns.addStretch(1); btns.addWidget(cancel); btns.addWidget(ok)

        lay = QVBoxLayout(self)
        lay.addWidget(tabs); lay.addLayout(btns)

    def _tab_pet(self):
        w = QWidget(); f = QFormLayout(w)
        self.catA_name = QLineEdit(self.settings.cat_a_name)
        self.catB_name = QLineEdit(self.settings.cat_b_name)
        self.size = QComboBox(); self.size.addItems(list(SIZE_PRESETS.keys()))
        self.size.setCurrentText(self.settings.pet_size)
        self.speed = QSpinBox(); self.speed.setRange(10, 300); self.speed.setValue(self.settings.walk_speed)
        self.speed.setSuffix(" px/s")
        self.area = QComboBox(); self.area.addItems(list(AREA_PRESETS.keys()))
        self.area.setCurrentText(self.settings.area_preset)
        self.monitor = QComboBox()
        for i, sc in enumerate(QGuiApplication.screens()):
            self.monitor.addItem(f"{i}: {sc.name()}")
        self.monitor.setCurrentIndex(min(self.settings.monitor_index, self.monitor.count()-1))
        f.addRow("猫A 名称", self.catA_name)
        f.addRow("猫B 名称", self.catB_name)
        f.addRow("宠物大小", self.size)
        f.addRow("行走速度", self.speed)
        f.addRow("活动范围", self.area)
        f.addRow("显示器", self.monitor)
        return w

    def _tab_time(self):
        w = QWidget(); f = QFormLayout(w)
        self.drink_reminders = QListWidget(); self.drink_reminders.setMaximumHeight(120)
        for r in self.settings.drink_reminders:
            self.drink_reminders.addItem(r)
        dr_btns = QHBoxLayout()
        dr_add = QPushButton("添加"); dr_add.clicked.connect(lambda: self._add_time(self.drink_reminders))
        dr_rm = QPushButton("删除"); dr_rm.clicked.connect(lambda: self.drink_reminders.takeItem(self.drink_reminders.currentRow()))
        dr_btns.addWidget(dr_add); dr_btns.addWidget(dr_rm); dr_btns.addStretch()
        f.addRow("喝水提醒", self._wrap(self.drink_reminders, dr_btns))

        self.feed_schedule = QListWidget(); self.feed_schedule.setMaximumHeight(120)
        for r in self.settings.feed_schedule:
            self.feed_schedule.addItem(r)
        fs_btns = QHBoxLayout()
        fs_add = QPushButton("添加"); fs_add.clicked.connect(lambda: self._add_time(self.feed_schedule))
        fs_rm = QPushButton("删除"); fs_rm.clicked.connect(lambda: self.feed_schedule.takeItem(self.feed_schedule.currentRow()))
        fs_btns.addWidget(fs_add); fs_btns.addWidget(fs_rm); fs_btns.addStretch()
        f.addRow("喂食时间", self._wrap(self.feed_schedule, fs_btns))

        ss = QHBoxLayout()
        self.sleep_start = QLineEdit(self.settings.sleep_start)
        self.sleep_end = QLineEdit(self.settings.sleep_end)
        ss.addWidget(QLabel("从")); ss.addWidget(self.sleep_start)
        ss.addWidget(QLabel("到")); ss.addWidget(self.sleep_end)
        f.addRow("睡眠时间", ss)
        return w

    def _tab_inter(self):
        w = QWidget(); f = QFormLayout(w)
        self.inter_on = QCheckBox("双猫互动"); self.inter_on.setChecked(self.settings.interaction_enabled)
        self.click_on = QCheckBox("用户点击互动"); self.click_on.setChecked(self.settings.click_enabled)
        self.drag_on = QCheckBox("拖动"); self.drag_on.setChecked(self.settings.drag_enabled)
        f.addRow(self.inter_on); f.addRow(self.click_on); f.addRow(self.drag_on)
        return w

    def _tab_sound(self):
        w = QWidget(); f = QFormLayout(w)
        self.sound_on = QCheckBox("开启声音（预留，暂无素材）"); self.sound_on.setChecked(self.settings.sound_enabled)
        self.vol = QSlider(Qt.Horizontal); self.vol.setRange(0, 100); self.vol.setValue(self.settings.sound_volume)
        f.addRow(self.sound_on); f.addRow("音量", self.vol)
        return w

    def _wrap(self, *items):
        c = QWidget(); l = QVBoxLayout(c); l.setContentsMargins(0,0,0,0)
        from PySide6.QtWidgets import QLayout
        for it in items:
            if isinstance(it, QLayout):
                l.addLayout(it)
            else:
                l.addWidget(it)
        return c

    def _add_time(self, lst):
        from PySide6.QtWidgets import QInputDialog
        t, ok = QInputDialog.getText(self, "时间", "格式 HH:MM，多个用逗号分隔")
        if ok and t:
            for part in t.replace("，", ",").split(","):
                part = part.strip()
                if part:
                    lst.addItem(part)

    def apply_to(self, settings: Settings):
        settings.cat_a_name = self.catA_name.text().strip() or "小橘"
        settings.cat_b_name = self.catB_name.text().strip() or "小灰"
        settings.pet_size = self.size.currentText()
        settings.walk_speed = self.speed.value()
        settings.area_preset = self.area.currentText()
        settings.monitor_index = self.monitor.currentIndex()
        settings.drink_reminders = [self.drink_reminders.item(i).text() for i in range(self.drink_reminders.count())]
        settings.feed_schedule = [self.feed_schedule.item(i).text() for i in range(self.feed_schedule.count())]
        settings.sleep_start = self.sleep_start.text().strip() or "23:30"
        settings.sleep_end = self.sleep_end.text().strip() or "07:30"
        settings.interaction_enabled = self.inter_on.isChecked()
        settings.click_enabled = self.click_on.isChecked()
        settings.drag_enabled = self.drag_on.isChecked()
        settings.sound_enabled = self.sound_on.isChecked()
        settings.sound_volume = self.vol.value()

    def accept(self):
        self.apply_to(self.settings)
        super().accept()
