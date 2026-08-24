# -*- coding: utf-8 -*-
"""双猫行为系统：独立状态机 + 权重 + 条件 + 随机性。

每只猫各自计算下一步要做什么，不同步。状态转移不写死，
而是根据 hunger/thirst/energy/mood/relationship/时间 动态加权随机选择。"""
import random
from enum import Enum
from dataclasses import dataclass

from config import (ACTION_WALK, ACTION_ROLL, ACTION_GROOM, ACTION_SLEEP,
                   ACTION_STRETCH, ACTION_DRINK, ACTION_EAT, ACTION_SIT,
                   ACTION_RUB, ACTION_SLEEP_TOGETHER, ACTION_PLAYFIGHT)


class CatState(Enum):
    SIT = ACTION_SIT
    WALK = ACTION_WALK
    ROLL = ACTION_ROLL
    GROOM = ACTION_GROOM
    SLEEP = ACTION_SLEEP
    STRETCH = ACTION_STRETCH      # 睡醒伸懒腰
    DRINK = ACTION_DRINK
    EAT = ACTION_EAT
    INTERACT = "interact"          # 互动中（由 InteractionDirector 控制）

    @property
    def action(self) -> str:
        return self.value


# 每个状态的基础停留时长（秒），实际会加随机抖动
STATE_DURATION = {
    CatState.SIT: (3.0, 7.0),
    CatState.WALK: (2.5, 5.0),
    CatState.ROLL: (3.0, 4.0),
    CatState.GROOM: (3.5, 6.0),
    CatState.SLEEP: (40.0, 120.0),
    CatState.STRETCH: (2.5, 3.5),
    CatState.DRINK: (3.0, 4.0),
    CatState.EAT: (3.0, 4.0),
}

# 动作是否循环播放（走路/睡觉等需要循环直到完成）
LOOP_STATES = {CatState.SIT, CatState.WALK, CatState.GROOM, CatState.SLEEP,
               CatState.DRINK, CatState.EAT}


@dataclass
class Stats:
    hunger: float
    thirst: float
    energy: float
    mood: float
    affection: float
    relationship: float
    is_sleep_time: bool = False


class BehaviorScheduler:
    """根据状态与权重，决定一只猫下一个状态。"""

    def __init__(self, seed=None):
        self.rng = random.Random(seed) if seed is not None else random.Random()
        # 记录最近动作，避免机械重复
        self.history: list = []
        self._just_woke = False

    def _base_weights(self, stats: Stats) -> dict:
        """计算各状态的权重。"""
        w = {
            CatState.WALK: 30,
            CatState.SIT: 24,
            CatState.GROOM: 16,
            CatState.ROLL: 6,
            CatState.SLEEP: 10,
            CatState.DRINK: 7,
            CatState.EAT: 7,
            CatState.STRETCH: 4,
        }
        # —— 条件加权 ——
        # 口渴
        if stats.thirst < 25:
            w[CatState.DRINK] += 40 * (1 - stats.thirst / 25)
        if stats.hunger < 30:
            w[CatState.EAT] += 40 * (1 - stats.hunger / 30)
        # 精力低 → 高概率睡觉
        if stats.energy < 25:
            w[CatState.SLEEP] += 50 * (1 - stats.energy / 25)
            w[CatState.WALK] *= 0.4
            w[CatState.ROLL] *= 0.3
        # 睡眠时段 → 强烈倾向睡觉
        if stats.is_sleep_time:
            w[CatState.SLEEP] += 70
            w[CatState.WALK] *= 0.4
            w[CatState.GROOM] *= 0.6
            w[CatState.ROLL] *= 0.2
            w[CatState.EAT] *= 0.5
            w[CatState.DRINK] *= 0.5
        # 心情高 → 更爱打滚/走动
        if stats.mood > 75:
            w[CatState.ROLL] += 6
            w[CatState.WALK] += 6
        elif stats.mood < 35:
            w[CatState.SIT] += 8
            w[CatState.GROOM] += 6
        return w

    def _suppress_repeat(self, weights: dict):
        """降低与上一次相同动作的权重，避免机械循环。"""
        if not self.history:
            return
        last = self.history[-1]
        if last in weights:
            weights[last] *= 0.35
        # 连续两次相同 → 进一步压制
        if len(self.history) >= 2 and self.history[-1] == self.history[-2]:
            weights[last] *= 0.2

    def next_state(self, current: CatState, stats: Stats, force: CatState = None) -> CatState:
        if force is not None:
            self.history.append(force)
            if len(self.history) > 8:
                self.history = self.history[-8:]
            return force

        # 刚睡醒 → 优先伸懒腰
        if current == CatState.SLEEP and self._just_woke:
            self._just_woke = False
            self.history.append(CatState.STRETCH)
            return CatState.STRETCH

        weights = self._base_weights(stats)
        # 当前是走路/吃饭/喝水这类目标行为，完成后倾向于坐下
        if current in (CatState.WALK, CatState.EAT, CatState.DRINK, CatState.ROLL,
                       CatState.GROOM, CatState.STRETCH):
            weights[CatState.SIT] += 14
        # 当前坐着 → 鼓励换个动作
        if current == CatState.SIT:
            weights[CatState.SIT] *= 0.5
            weights[CatState.WALK] += 8

        self._suppress_repeat(weights)

        # 睡觉后醒来标记
        if current == CatState.SLEEP:
            self._just_woke = True

        states = list(weights.keys())
        vals = [max(0.0, weights[s]) for s in states]
        total = sum(vals)
        if total <= 0:
            return CatState.SIT
        r = self.rng.uniform(0, total)
        acc = 0.0
        for s, v in zip(states, vals):
            acc += v
            if r <= acc:
                self.history.append(s)
                if len(self.history) > 8:
                    self.history = self.history[-8:]
                return s
        return self.rng.choice(states)

    def duration_for(self, state: CatState) -> float:
        lo, hi = STATE_DURATION.get(state, (3.0, 5.0))
        return self.rng.uniform(lo, hi)
