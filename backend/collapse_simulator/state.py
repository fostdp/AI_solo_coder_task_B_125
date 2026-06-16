from dataclasses import dataclass


@dataclass
class CollapseState:
    floor: int
    drift_ratio: float
    damage_index: float
    is_collapsed: bool
    collapse_time: float = 0.0
