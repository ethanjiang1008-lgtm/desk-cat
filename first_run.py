# -*- coding: utf-8 -*-
"""首次启动向导：命名 → 确认 → 活动区域 → 完成。"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QLineEdit,
                              QPushButton, QComboBox, QHBoxLayout, QStackedWidget,
                              QWidget)
from config import AREA_PRESETS, SIZE_PRESETS
from state import Settings, default_state


class FirstRunWizard(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("欢迎来到你的双猫桌面")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setMinimumWidth(420)
        self.cat_a_name = "小橘"
        self.cat_b_name = "小灰"
        self.area_preset = "bottom"
        self.pet_size = "medium"

        self.stack = QStackedWidget()
        self.stack.addWidget(self._page_welcome())
        self.stack.addWidget(self._page_name_a())
        self.stack.addWidget(self._page_name_b())
        self.stack.addWidget(self._page_area())
        self.stack.addWidget(self._page_done())
        lay = QVBoxLayout(self)
        lay.addWidget(self.stack)
        self.nav = QHBoxLayout()
        self.prev = QPushButton("上一步"); self.prev.clicked.connect(self.go_prev)
        self.next = QPushButton("下一步"); self.next.clicked.connect(self.go_next)
        self.nav.addStretch(1); self.nav.addWidget(self.prev); self.nav.addWidget(self.next)
        lay.addLayout(self.nav)
        self._sync()

    def _page(self, text):
        w = QWidget(); l = QVBoxLayout(w); l.setAlignment(Qt.AlignCenter)
        l.addWidget(QLabel(text))
        return w

    def _page_welcome(self):
        return self._page("<h2>🐱🐱 欢迎来到你的双猫桌面</h2><p>接下来给你的两只猫起个名字，<br/>并选择它们活动的区域。</p>")

    def _page_name_a(self):
        w = QWidget(); l = QVBoxLayout(w)
        l.addWidget(QLabel("<h3>给猫A起个名字</h3>"))
        self.in_a = QLineEdit(self.cat_a_name); l.addWidget(self.in_a)
        return w

    def _page_name_b(self):
        w = QWidget(); l = QVBoxLayout(w)
        l.addWidget(QLabel("<h3>给猫B起个名字</h3>"))
        self.in_b = QLineEdit(self.cat_b_name); l.addWidget(self.in_b)
        return w

    def _page_area(self):
        w = QWidget(); l = QVBoxLayout(w)
        l.addWidget(QLabel("<h3>选择活动区域与大小</h3>"))
        self.cb_area = QComboBox(); self.cb_area.addItems(list(AREA_PRESETS.keys()))
        self.cb_area.setCurrentText(self.area_preset); l.addWidget(self.cb_area)
        self.cb_size = QComboBox(); self.cb_size.addItems(list(SIZE_PRESETS.keys()))
        self.cb_size.setCurrentText(self.pet_size); l.addWidget(self.cb_size)
        return w

    def _page_done(self):
        return self._page("<h2>✅ 设置完成！</h2><p>两只猫马上会从屏幕两侧走进来，<br/>开始它们的桌面生活。</p>")

    def _sync(self):
        i = self.stack.currentIndex()
        self.prev.setEnabled(i > 0)
        self.next.setText("完成" if i == self.stack.count()-1 else "下一步")

    def go_prev(self):
        self._collect()
        if self.stack.currentIndex() > 0:
            self.stack.setCurrentIndex(self.stack.currentIndex()-1)
        self._sync()

    def go_next(self):
        self._collect()
        if self.stack.currentIndex() < self.stack.count()-1:
            self.stack.setCurrentIndex(self.stack.currentIndex()+1)
            self._sync()
        else:
            self.accept()

    def _collect(self):
        i = self.stack.currentIndex()
        if i == 1 and hasattr(self, "in_a"):
            self.cat_a_name = self.in_a.text().strip() or "小橘"
        if i == 2 and hasattr(self, "in_b"):
            self.cat_b_name = self.in_b.text().strip() or "小灰"
        if i == 3 and hasattr(self, "cb_area"):
            self.area_preset = self.cb_area.currentText()
            self.pet_size = self.cb_size.currentText()
