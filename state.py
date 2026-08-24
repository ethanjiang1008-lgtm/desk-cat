# -*- coding: utf-8 -*-
"""持久化：保存/加载所有猫咪状态与用户设置，重启后按真实时间差重算属性。"""
import json
import time
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, Tuple

from config import (HUNGER_DECAY, THIRST_DECAY, ENERGY_ACTIVE_DECAY,
                   ENERGY_SLEEP_GAIN, MOOD_DECAY, AFFECTION_DECAY,
                   RELATIONSHIP_DECAY, STAT_MIN, STAT_MAX)


def clamp(v):
    return max(STAT_MIN, min(STAT_MAX, v))


@dataclass
class CatState:
    name: str = ""
    # 属性 0~100
    hunger: float = 80.0
    thirst: float = 80.0
    energy: float = 80.0
    mood: float = 70.0
    affection: float = 50.0
    # 位置（活动区域相对坐标 0~1）
    x: float = 0.3
    y: float = 0.6
    facing: int = 1            # 1=朝右, -1=朝左
    last_state: str = "sit"
    last_interaction_ts: float = 0.0


@dataclass
class Settings:
    cat_a_name: str = "小橘"
    cat_b_name: str = "小灰"
    pet_size: str = "medium"          # small/medium/large
    walk_speed: int = 60              # px/s
    area_preset: str = "bottom"
    area_custom: Optional[Dict] = None
    monitor_index: int = 0
    drink_reminders: list = field(default_factory=lambda: ["09:30", "13:30", "17:30", "19:30"])
    feed_schedule: list = field(default_factory=lambda: ["08:00", "12:30", "18:30"])
    sleep_start: str = "23:30"
    sleep_end: str = "07:30"
    interaction_enabled: bool = True
    click_enabled: bool = True
    drag_enabled: bool = True
    sound_enabled: bool = False
    sound_volume: int = 40
    activity_paused: bool = False
    reminders_paused: bool = False
    pets_visible: bool = True
    relationship: float = 50.0
    last_save_ts: float = 0.0


def default_state() -> Tuple[CatState, CatState, Settings]:
    a = CatState(name="小橘", x=0.30, y=0.62, facing=1, last_state="sit")
    b = CatState(name="小灰", x=0.62, y=0.66, facing=-1, last_state="sit")
    s = Settings()
    return a, b, s


def save_file() -> Path:
    home = Path.home()
    d = home / ".dualcat"
    d.mkdir(exist_ok=True)
    return d / "state.json"


def save(cat_a: CatState, cat_b: CatState, settings: Settings):
    settings.last_save_ts = time.time()
    data = {
        "cat_a": asdict(cat_a),
        "cat_b": asdict(cat_b),
        "settings": asdict(settings),
        "saved_at": time.time(),
    }
    try:
        save_file().write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[state] 保存失败: {e}")


def load():
    """加载状态；不存在则返回默认。若存在则按真实时间差重算属性。"""
    f = save_file()
    if not f.exists():
        return default_state()
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
        ca = CatState(**data["cat_a"])
        cb = CatState(**data["cat_b"])
        st = Settings(**data["settings"])
        now = time.time()
        dt_min = max(0.0, (now - st.last_save_ts) / 60.0)
        if dt_min > 0:
            for c in (ca, cb):
                # 关闭期间：猫大概率在睡觉/静坐，按睡眠恢复精力、缓慢衰减饥渴/心情
                sleeping = _is_sleep_time(st, now)
                c.hunger = clamp(c.hunger - HUNGER_DECAY * dt_min)
                c.thirst = clamp(c.thirst - THIRST_DECAY * dt_min)
                if sleeping:
                    c.energy = clamp(c.energy + ENERGY_SLEEP_GAIN * dt_min * 0.5)
                else:
                    c.energy = clamp(c.energy - ENERGY_ACTIVE_DECAY * dt_min * 0.3)
                c.mood = clamp(c.mood - MOOD_DECAY * dt_min)
                c.affection = clamp(c.affection - AFFECTION_DECAY * dt_min)
            st.relationship = clamp(st.relationship - RELATIONSHIP_DECAY * dt_min)
        return ca, cb, st
    except Exception as e:
        print(f"[state] 加载失败，使用默认: {e}")
        return default_state()


def _is_sleep_time(settings: Settings, now: float = None) -> bool:
    import datetime
    now = now or time.time()
    t = datetime.datetime.fromtimestamp(now).time()
    sh, sm = map(int, settings.sleep_start.split(":"))
    eh, em = map(int, settings.sleep_end.split(":"))
    start_min = sh * 60 + sm
    end_min = eh * 60 + em
    cur = t.hour * 60 + t.minute
    if start_min == end_min:
        return False
    if start_min < end_min:
        return start_min <= cur < end_min
    # 跨夜
    return cur >= start_min or cur < end_min
