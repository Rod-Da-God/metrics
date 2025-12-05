import logging
from typing import Optional

from shapely.geometry import MultiPolygon, Polygon


logger = logging.getLogger(__name__)


def normalize_geometry(geom) -> Optional[str]:
    """    
    1. Исправить невалидность (buffer(0) ≈ ST_MakeValid)
    2. Привести к MultiPolygon (ST_Multi)
    
    Args:
        geom: shapely Polygon/MultiPolygon
    
    Returns:
        WKT строка MultiPolygon или None при ошибке
    """
    if not geom.is_valid:
        logger.debug("Геометрия невалидна, применяем buffer(0)")
        geom = geom.buffer(0) 
    
    if isinstance(geom, Polygon):
        geom = MultiPolygon([geom])
    elif not isinstance(geom, MultiPolygon):
        logger.error(
            "Геометрия не Polygon/MultiPolygon: %s",
            type(geom).__name__
        )
        return None
    
    return geom.wkt
    

