# -*- coding: utf-8 -*-
"""全局配置、常量与资源路径解析。"""
import os
import sys
from pathlib import Path

APP_NAME = "双猫桌面宠物"
APP_VERSION = "1.0.0"

# —— 动作 key（与 assets/<group>/<key>.webp 文件名对应）——
ACTION_WALK = "walk"
ACTION_ROLL = "roll"
ACTION_GROOM = "grooming"
ACTION_SLEEP = "sleep"
ACTION_STRETCH = "stretch"
ACTION_DRINK = "drink"
ACTION_EAT = "eat"
ACTION_SIT = "sit"
# 双猫互动
ACTION_RUB = "rub"
ACTION_SLEEP_TOGETHER = "sleep_together"
ACTION_PLAYFIGHT = "playfight"

# 单猫动作集合
SOLO_ACTIONS = [ACTION_WALK, ACTION_ROLL, ACTION_GROOM, ACTION_SLEEP,
               ACTION_STRETCH, ACTION_DRINK, ACTION_EAT, ACTION_SIT]

# —— 猫咪渲染尺寸（像素高度），保持 webp 宽高比 ——
SIZE_PRESETS = {"small": 96, "medium": 140, "large": 190}

# —— 活动区域预设（占屏幕的比例，1.0=全屏）——
AREA_PRESETS = {
    "bottom": {"x": 0.0, "y": 0.72, "w": 1.0, "h": 0.28},   # 屏幕下方 28%
    "full": {"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0},
    "bottom_left": {"x": 0.0, "y": 0.72, "w": 0.5, "h": 0.28},
    "bottom_right": {"x": 0.5, "y": 0.72, "w": 0.5, "h": 0.28},
}

# —— 状态属性范围 ——
STAT_MIN, STAT_MAX = 0, 100

# —— 衰减速率（每分钟）——
HUNGER_DECAY = 0.55      # 饥饿值下降
THIRST_DECAY = 0.70      # 口渴值下降
ENERGY_ACTIVE_DECAY = 0.35   # 活动时精力下降
ENERGY_SLEEP_GAIN = 1.6      # 睡觉时精力恢复
MOOD_DECAY = 0.18        # 心情随时间小幅下降
MOOD_INTERACT_GAIN = 6   # 互动带来心情提升
AFFECTION_DECAY = 0.05
RELATIONSHIP_DECAY = 0.01

# —— 喝水/吃饭地点（在活动区域内的相对位置 0~1）——
# 兼容旧代码的全局碗位置
BOWL_POS = {"food": (0.10, 0.88), "water": (0.90, 0.88)}
# 每只猫各自的食碗/水碗位置（在各自活动区域内，确保可达）
BOWL_POS_A = {"food": (0.08, 0.88), "water": (0.18, 0.88)}   # 猫A左半区内
BOWL_POS_B = {"food": (0.82, 0.88), "water": (0.92, 0.88)}   # 猫B右半区内

# —— 两只猫各自的活动区域（X 范围 0~1，避免交叉导致遮挡/画面叠加）——
CAT_A_X_RANGE = (0.02, 0.48)   # 猫A 左半区
CAT_B_X_RANGE = (0.52, 0.98)   # 猫B 右半区


def clamp(v):
    """把数值限制到 STAT_MIN..STAT_MAX。"""
    return max(STAT_MIN, min(STAT_MAX, v))


def resource_path(*parts: str) -> Path:
    """解析打包/非打包下的资源绝对路径。"""
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", os.path.dirname(sys.executable)))
    else:
        base = Path(__file__).resolve().parent
    return base.joinpath(*parts)


def asset_path(group: str, action: str) -> Path:
    return resource_path("assets", group, f"{action}.webp")


def icon_path(name: str) -> Path:
    return resource_path("assets", "icons", name)
