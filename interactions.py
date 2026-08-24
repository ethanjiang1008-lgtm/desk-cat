# -*- coding: utf-8 -*-
"""InteractionDirector：双猫互动导演。
决定何时触发 互相蹭 / 一起睡觉 / 互相打闹，并临时接管两只猫的位置与动画。"""
import math
import random
import time

from config import (ACTION_RUB, ACTION_SLEEP_TOGETHER, ACTION_PLAYFIGHT,
                   MOOD_INTERACT_GAIN, clamp)
from behavior import CatState


class InteractionDirector:
    """两个 CatController + 一个渲染钩子。"""

    def __init__(self, cat_a, cat_b, settings_ref, render_hook, seed=None):
        self.cat_a = cat_a
        self.cat_b = cat_b
        self.settings = settings_ref      # Settings 可变对象
        self.render_hook = render_hook    # callback(action, x, y) 用于显示双猫精灵
        self.rng = random.Random(seed)
        self.active = None                 # 当前互动 action key
        self.active_timer = 0.0
        self.cooldown = 30.0               # 互动冷却（秒）
        self._t = 0.0

    def _distance(self):
        ax, ay = self.cat_a.data.x, self.cat_a.data.y
        bx, by = self.cat_b.data.x, self.cat_b.data.y
        return math.hypot(ax - bx, ay - by)

    def _both_free(self):
        return not self.cat_a.interacting and not self.cat_b.interacting and not self.active

    def advance(self, dt: float, is_sleep_time: bool):
        self._t += dt
        if self.active:
            self.active_timer -= dt
            if self.active_timer <= 0:
                self._end_interaction()
            return

        self.cooldown -= dt
        if self.cooldown > 0:
            return
        if not self.settings.interaction_enabled:
            return
        if not self._both_free():
            return

        a, b = self.cat_a, self.cat_b
        rel = self.settings.relationship
        # —— 一起睡觉 ——
        if (is_sleep_time and a.data.energy < 40 and b.data.energy < 40
                and rel > 45 and self._distance() < 0.4 and self.rng.random() < 0.25):
            self._start(ACTION_SLEEP_TOGETHER, (50, 70))
            self.settings.relationship = clamp(rel + 3)
            return
        # —— 互相蹭 ——
        if (rel > 40 and self._distance() < 0.45 and self.rng.random() < 0.35):
            self._start(ACTION_RUB, (8, 14))
            self.settings.relationship = clamp(rel + 2)
            a.data.mood = clamp(a.data.mood + MOOD_INTERACT_GAIN)
            b.data.mood = clamp(b.data.mood + MOOD_INTERACT_GAIN)
            return
        # —— 互相打闹（稀有）——
        if (rel > 50 and a.data.energy > 55 and b.data.energy > 55
                and a.data.mood > 55 and b.data.mood > 55
                and self._distance() < 0.5 and self.rng.random() < 0.10):
            self._start(ACTION_PLAYFIGHT, (10, 16))
            self.settings.relationship = clamp(rel + self.rng.randint(-1, 2))
            a.data.mood = clamp(a.data.mood + 4)
            b.data.mood = clamp(b.data.mood + 4)
            a.data.energy = clamp(a.data.energy - 10)
            b.data.energy = clamp(b.data.energy - 10)
            return

    def _start(self, action, dur_range):
        self.active = action
        self.active_timer = self.rng.uniform(*dur_range)
        self.cat_a.interacting = True
        self.cat_b.interacting = True
        # 两猫聚拢到中点
        mx = (self.cat_a.data.x + self.cat_b.data.x) / 2
        my = (self.cat_a.data.y + self.cat_b.data.y) / 2
        self.cat_a.data.x = mx - 0.12
        self.cat_a.data.y = my
        self.cat_b.data.x = mx + 0.12
        self.cat_b.data.y = my
        self._mid = (mx, my)
        self.cat_a.current = CatState.INTERACT
        self.cat_b.current = CatState.INTERACT
        if self.render_hook:
            self.render_hook("start", action, self._mid)

    def _end_interaction(self):
        action = self.active
        self.active = None
        self.cat_a.interacting = False
        self.cat_b.interacting = False
        # 分开走开
        mx, my = self._mid
        self.cat_a.walk_target = (max(0.05, mx - self.rng.uniform(0.15, 0.3)),
                                  self.rng.uniform(0.55, 0.9))
        self.cat_b.walk_target = (min(0.95, mx + self.rng.uniform(0.15, 0.3)),
                                  self.rng.uniform(0.55, 0.9))
        self.cat_a._transition(CatState.WALK)
        self.cat_b._transition(CatState.WALK)
        self.cooldown = self.rng.uniform(45, 90)
        if self.render_hook:
            self.render_hook("end", action, self._mid)
