from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class PagodaUncertainty:
    height_uncertainty_pct: float = 0.02
    diameter_uncertainty_pct: float = 0.03
    E_uncertainty_pct: float = 0.10
    joint_k_uncertainty_pct: float = 0.20


@dataclass
class PagodaModel:
    name: str
    dynasty: str
    country: str
    height: float
    floor_count: int
    structural_type: str
    floor_heights: List[float]
    floor_diameters: List[float]
    inner_diameters: List[float]
    wall_thickness: List[float]
    timber_properties: Dict[str, float]
    joint_properties: Dict[str, float]
    seismic_philosophy: str
    shinbashira: bool = False
    shinbashira_diameter: float = 0.0
    data_sources: List[str] = field(default_factory=list)
    calibration_year: Optional[int] = None
    uncertainty: PagodaUncertainty = field(default_factory=PagodaUncertainty)


DynastyPagodaModel = PagodaModel
