# -*- coding: utf-8 -*-
"""InteractionDirector：双猫互动导演。
决定何时触发 互相蹭 / 一起睡觉 / 互相打闹，并临时接管两只猫的位置与动画。

v5 改进：两只猫各有独立活动区域不交叉，互动前先让猫互相走近
（approach 阶段），到达边界后再触发互动。去掉距离门槛检查。
三种互动的概率都提高，确保都能被触发。"""
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
        self.render_hook = render_hook    # callback(action, x, y)
        self.rng = random.Random(seed)
        self.active = None                 # 当前互动 action key
        self.active_timer = 0.0
        self.cooldown = 20.0               # 互动冷却（秒），降低初始等待
        self._t = 0.0
        # —— approach 阶段 ——
        self._approaching = False          # 正在互相靠近
        self._approach_timer = 0.0         # 接近超时（秒）
        self._approach_action = None       # 接近后要触发的互动
        self._approach_dur_range = None    # 互动持续时间范围

    def _distance(self):
        ax, ay = self.cat_a.data.x, self.cat_a.data.y
        bx, by = self.cat_b.data.x, self.cat_b.data.y
        return math.hypot(ax - bx, ay - by)

    def _both_free(self):
        if (self.cat_a.interacting or self.cat_b.interacting
                or self.active or self._approaching):
            return False
        # 不打断正在去吃饭/喝水的猫
        if (getattr(self.cat_a, '_pending_arrive', None)
                or getattr(self.cat_b, '_pending_arrive', None)):
            return False
        return True

    def advance(self, dt: float, is_sleep_time: bool):
        self._t += dt

        # —— 互动进行中 ——
        if self.active:
            self.active_timer -= dt
            if self.active_timer <= 0:
                self._end_interaction()
            return

        # —— approach 阶段：等待猫互相靠近 ——
        if self._approaching:
            self._approach_timer -= dt
            a_done = self.cat_a.walk_target is None
            b_done = self.cat_b.walk_target is None
            if (a_done and b_done) or self._approach_timer <= 0:
                # 两只猫都到达 或 超时 → 触发互动
                action = self._approach_action
                dur_range = self._approach_dur_range
                self._approaching = False
                self.cat_a._director_approach = False
                self.cat_b._director_approach = False
                self._start(action, dur_range)
            return

        # —— 冷却 ——
        self.cooldown -= dt
        if self.cooldown > 0:
            return
        if not self.settings.interaction_enabled:
            return
        if not self._both_free():
            return

        a, b = self.cat_a, self.cat_b
        rel = self.settings.relationship

        # 不打断睡觉
        if a.current == CatState.SLEEP or b.current == CatState.SLEEP:
            return

        # —— 决定触发哪种互动 ——
        action, dur_range = self._decide(rel, is_sleep_time, a, b)
        if action:
            self._start_approach(action, dur_range)

    def _decide(self, rel, is_sleep_time, a, b):
        """根据条件决定触发哪种互动，返回 (action, dur_range) 或 (None, None)。"""
        # —— 一起睡觉（需要睡眠时段 + 双方精力低）——
        if (is_sleep_time and a.data.energy < 50 and b.data.energy < 50
                and rel > 35 and self.rng.random() < 0.35):
            return ACTION_SLEEP_TOGETHER, (40, 65)
        # —— 互相蹭（最常见的互动）——
        if rel > 30 and self.rng.random() < 0.45:
            return ACTION_RUB, (8, 14)
        # —— 互相打闹（需要高精力+好心情）——
        if (rel > 40 and a.data.energy > 45 and b.data.energy > 45
                and a.data.mood > 45 and b.data.mood > 45
                and self.rng.random() < 0.30):
            return ACTION_PLAYFIGHT, (10, 16)
        return None, None

    def _start_approach(self, action, dur_range):
        """让两只猫互相走近，到达后触发互动。"""
        self._approaching = True
        self._approach_timer = 10.0  # 最多等10秒（慢走也能到达）
        self._approach_action = action
        self._approach_dur_range = dur_range
        # 清除可能残留的吃饭/喝水待办
        self.cat_a._pending_arrive = None
        self.cat_b._pending_arrive = None
        # 猫A走向右边界，猫B走向左边界
        a_lo, a_hi = self.cat_a.x_range
        b_lo, b_hi = self.cat_b.x_range
        mid_y = (self.cat_a.data.y + self.cat_b.data.y) / 2
        self.cat_a.walk_target = (a_hi - 0.04, mid_y)
        self.cat_b.walk_target = (b_lo + 0.04, mid_y)
        self.cat_a.data.facing = 1    # 朝右走向猫B
        self.cat_b.data.facing = -1   # 朝左走向猫A
        self.cat_a._transition(CatState.WALK)
        self.cat_b._transition(CatState.WALK)
        self.cat_a._director_approach = True
        self.cat_b._director_approach = True

    def _start(self, action, dur_range):
        self.active = action
        self.active_timer = self.rng.uniform(*dur_range)
        self.cat_a.interacting = True
        self.cat_b.interacting = True
        # 两猫聚拢到中点（猫已在边界附近，只需微调）
        mx = (self.cat_a.data.x + self.cat_b.data.x) / 2
        my = (self.cat_a.data.y + self.cat_b.data.y) / 2
        self.cat_a.data.x = mx - 0.06
        self.cat_a.data.y = my
        self.cat_b.data.x = mx + 0.06
        self.cat_b.data.y = my
        self._mid = (mx, my)
        self.cat_a.current = CatState.INTERACT
        self.cat_b.current = CatState.INTERACT
        # 互动效果
        rel = self.settings.relationship
        if action == ACTION_RUB:
            self.settings.relationship = clamp(rel + 2)
            self.cat_a.data.mood = clamp(self.cat_a.data.mood + MOOD_INTERACT_GAIN)
            self.cat_b.data.mood = clamp(self.cat_b.data.mood + MOOD_INTERACT_GAIN)
        elif action == ACTION_SLEEP_TOGETHER:
            self.settings.relationship = clamp(rel + 3)
        elif action == ACTION_PLAYFIGHT:
            self.settings.relationship = clamp(rel + self.rng.randint(-1, 2))
            self.cat_a.data.mood = clamp(self.cat_a.data.mood + 4)
            self.cat_b.data.mood = clamp(self.cat_b.data.mood + 4)
            self.cat_a.data.energy = clamp(self.cat_a.data.energy - 10)
            self.cat_b.data.energy = clamp(self.cat_b.data.energy - 10)
        if self.render_hook:
            self.render_hook("start", action, self._mid)

    def _end_interaction(self):
        action = self.active
        self.active = None
        self.cat_a.interacting = False
        self.cat_b.interacting = False
        # 各自回到自己的活动区域
        ax_lo, ax_hi = self.cat_a.x_range
        bx_lo, bx_hi = self.cat_b.x_range
        self.cat_a.walk_target = (self.rng.uniform(ax_lo, ax_hi),
                                  self.rng.uniform(0.78, 0.88))
        self.cat_b.walk_target = (self.rng.uniform(bx_lo, bx_hi),
                                  self.rng.uniform(0.78, 0.88))
        self.cat_a._transition(CatState.WALK)
        self.cat_b._transition(CatState.WALK)
        self.cooldown = self.rng.uniform(35, 70)
        if self.render_hook:
            self.render_hook("end", action, self._mid)
