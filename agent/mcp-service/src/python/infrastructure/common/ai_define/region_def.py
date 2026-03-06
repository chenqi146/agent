from dataclasses import dataclass


@dataclass
class CVQuadrangleRegionDef:
    x1: float
    y1: float
    x2: float
    y2: float
    x3: float
    y3: float
    x4: float
    y4: float

@dataclass
class CVRectangleRegionDef:
    x: float
    y: float
    width: float
    height: float
