# -*- coding: utf-8 -*-
"""CatController：每只猫独立的角色控制器。
管理状态机推进、属性衰减、走动移动、用户交互。
对应规格中的 CatBehaviorController_A / _B。"""
import math
import time
import random

from config import (ACTION_WALK, BOWL_POS, HUNGER_DECAY, THIRST_DECAY,
                   ENERGY_ACTIVE_DECAY, ENERGY_SLEEP_GAIN, MOOD_DECAY,
                   AFFECTION_DECAY, MOOD_INTERACT_GAIN, clamp)
from behavior import CatState, BehaviorScheduler, Stats, LOOP_STATES
from state import CatState as CatData


class CatController:
    def __init__(self, data: CatData, seed=None):
        self.data = data
        self.scheduler = BehaviorScheduler(seed)
        self.current: CatState = CatState.SIT
        # 还原上次状态
        try:
            self.current = CatState(self.data.last_state) if self.data.last_state in CatState._value2member_map_ else CatState.SIT
        except Exception:
            self.current = CatState.SIT
        self.phase_timer = self.scheduler.duration_for(self.current)
        self.walk_target = None         # (x,y) 相对坐标
        self.walk_speed = 0.12          # 相对坐标/秒（会被外部按尺寸修正）
        self.interacting = False        # 互动期间由导演接管
        self._rng = random.Random(seed)

    # —— 属性 ——
    def stats(self, relationship: float, is_sleep_time: bool) -> Stats:
        return Stats(self.data.hunger, self.data.thirst, self.data.energy,
                     self.data.mood, self.data.affection, relationship,
                     is_sleep_time)

    def advance(self, dt: float, relationship: float, is_sleep_time: bool,
                other_pos=None, activity_rect=None):
        """每帧推进。dt 秒。"""
        if self.interacting:
            return
        # —— 属性衰减 ——
        active = self.current in (CatState.WALK, CatState.ROLL, CatState.GROOM,
                                  CatState.EAT, CatState.DRINK, CatState.STRETCH)
        sleeping = self.current == CatState.SLEEP
        m = dt / 60.0
        self.data.hunger = clamp(self.data.hunger - HUNGER_DECAY * m)
        self.data.thirst = clamp(self.data.thirst - THIRST_DECAY * m)
        if sleeping:
            self.data.energy = clamp(self.data.energy + ENERGY_SLEEP_GAIN * m)
        elif active:
            self.data.energy = clamp(self.data.energy - ENERGY_ACTIVE_DECAY * m)
        else:
            self.data.energy = clamp(self.data.energy - ENERGY_ACTIVE_DECAY * 0.3 * m)
        self.data.mood = clamp(self.data.mood - MOOD_DECAY * m)
        self.data.affection = clamp(self.data.affection - AFFECTION_DECAY * m)

        # —— 走动移动 ——
        if self.current == CatState.WALK and self.walk_target is not None:
            self._move_toward(self.walk_target, dt, activity_rect)
            if self._reached(self.walk_target):
                self.walk_target = None

        # —— 状态计时 ——
        # 睡觉不按短计时器切换，直到精力恢复或睡眠时段结束
        if self.current == CatState.SLEEP:
            self.phase_timer -= dt
            # 精力恢复够了 或 不在睡眠时段 且 计时结束 → 醒来
            wake = (self.data.energy > 85) or (
                (not is_sleep_time) and self.phase_timer <= 0)
            if wake:
                # 睡醒优先伸懒腰，然后由调度器接管
                self._transition(CatState.STRETCH)
            return

        self.phase_timer -= dt
        if self.phase_timer <= 0 and self.walk_target is None:
            # 选择下一个状态
            nxt = self._choose_next(relationship, is_sleep_time)
            self._transition(nxt)

    def _choose_next(self, relationship, is_sleep_time):
        st = self.stats(relationship, is_sleep_time)
        nxt = self.scheduler.next_state(self.current, st)
        # 如果选了走动，先决定目标
        if nxt == CatState.WALK:
            self.walk_target = self._pick_walk_target(relationship, is_sleep_time)
        return nxt

    def _transition(self, nxt: CatState):
        self.current = nxt
        self.data.last_state = nxt.value
        if nxt == CatState.WALK and self.walk_target is None:
            # 已在外部设置
            pass
        self.phase_timer = self.scheduler.duration_for(nxt)

    def _pick_walk_target(self, relationship, is_sleep_time):
        # 随机点 / 食碗 / 水碗
        self._rng = random.Random()
        r = self._rng.random()
        if self.data.hunger < 35 and r < 0.5:
            return BOWL_POS["food"]
        if self.data.thirst < 40 and r < 0.5:
            return BOWL_POS["water"]
        return (self._rng.uniform(0.05, 0.95), self._rng.uniform(0.55, 0.92))

    def _move_toward(self, target, dt, activity_rect=None):
        tx, ty = target
        dx = tx - self.data.x
        dy = ty - self.data.y
        dist = math.hypot(dx, dy)
        if dist < 1e-4:
            return
        # 朝向
        self.data.facing = 1 if dx >= 0 else -1
        # 步长（相对坐标），限制不超过距离
        step = self.walk_speed * dt
        if step >= dist:
            self.data.x, self.data.y = tx, ty
        else:
            self.data.x += dx / dist * step
            self.data.y += dy / dist * step
        # 限制在活动区域内
        self.data.x = max(0.0, min(1.0, self.data.x))
        self.data.y = max(0.0, min(1.0, self.data.y))

    def _reached(self, target, eps=0.02):
        return math.hypot(self.data.x - target[0], self.data.y - target[1]) < eps

    # —— 用户交互 ——
    def feed(self):
        """用户喂食 → 走向食碗 → 吃饭。"""
        if self.interacting:
            return
        self.walk_target = BOWL_POS["food"]
        self._transition(CatState.WALK)
        # 到达后自动转 eat（由 PetWindow 监测到达触发 _arrive_eat）
        self._pending_arrive = "eat"

    def water(self):
        if self.interacting:
            return
        self.walk_target = BOWL_POS["water"]
        self._transition(CatState.WALK)
        self._pending_arrive = "drink"

    def on_arrive_target(self):
        """走动到达目标后调用。"""
        pending = getattr(self, "_pending_arrive", None)
        if pending == "eat":
            self._pending_arrive = None
            self._transition(CatState.EAT)
            self.data.hunger = clamp(self.data.hunger + 45)
            self.data.mood = clamp(self.data.mood + 8)
        elif pending == "drink":
            self._pending_arrive = None
            self._transition(CatState.DRINK)
            self.data.thirst = clamp(self.data.thirst + 45)
            self.data.mood = clamp(self.data.mood + 6)
        else:
            # 普通走动结束 → 调度下一动作
            pass

    def on_click(self):
        """单击：随机简单反应。"""
        self.data.mood = clamp(self.data.mood + 3)
        self.data.last_interaction_ts = time.time()
        r = self._rng.random()
        if r < 0.4:
            self._transition(CatState.SIT)
        elif r < 0.7:
            # 轻微移动
            self.walk_target = (self._rng.uniform(0.05, 0.95),
                                self._rng.uniform(0.55, 0.92))
            self._transition(CatState.WALK)
        else:
            self._transition(CatState.GROOM)

    def on_double_click(self):
        """双击：短暂兴奋 / 翻滚 / 跑开。"""
        self.data.mood = clamp(self.data.mood + 6)
        self.data.last_interaction_ts = time.time()
        r = self._rng.random()
        if r < 0.4:
            self._transition(CatState.ROLL)
        elif r < 0.7:
            self.walk_target = (self._rng.uniform(0.05, 0.95),
                                self._rng.uniform(0.55, 0.92))
            self._transition(CatState.WALK)
        else:
            self._transition(CatState.STRETCH)

    def on_drag_end(self):
        """拖动结束 → 坐下或走开。"""
        self.data.mood = clamp(self.data.mood + 2)
        if self._rng.random() < 0.5:
            self._transition(CatState.SIT)
        else:
            self.walk_target = (self._rng.uniform(0.05, 0.95),
                                self._rng.uniform(0.55, 0.92))
            self._transition(CatState.WALK)
