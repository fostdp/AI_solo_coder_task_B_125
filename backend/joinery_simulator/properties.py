import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ExperimentalSource:
    institution: str
    year: int
    sample_count: int
    timber_species: str
    test_method: str
    paper_ref: str


@dataclass
class ParameterUncertainty:
    stiffness_cv: float = 0.20
    yield_moment_cv: float = 0.25
    ultimate_moment_cv: float = 0.28
    yield_rotation_cv: float = 0.18
    ductility_cv: float = 0.30


PARAMETER_VALID_RANGES = {
    "elastic_stiffness": (1.0e6, 5.0e9),
    "yield_moment": (1.0e3, 5.0e7),
    "ultimate_moment": (5.0e3, 1.0e8),
    "yield_rotation": (0.001, 0.030),
    "ultimate_rotation": (0.005, 0.150),
    "damping_ratio": (0.01, 0.20),
    "pinching_factor": (0.05, 0.90),
    "ductility_factor": (1.5, 20.0),
}


@dataclass
class JoineryProperties:
    name: str
    chinese_name: str
    category: str
    elastic_stiffness: float
    yield_moment: float
    ultimate_moment: float
    yield_rotation: float
    ultimate_rotation: float
    damping_ratio: float
    pinching_factor: float
    model_type: str
    gap: float = 0.0
    torsional_stiffness: float = 0.0
    vertical_load_effect: bool = False
    experimental_source: Optional[ExperimentalSource] = None
    calibration_year: Optional[int] = None
    uncertainty: ParameterUncertainty = field(default_factory=ParameterUncertainty)
    validation_status: str = "unverified"


MortiseTenonProperties = JoineryProperties
