import logging
from typing import List, Optional

from shapely.geometry import MultiPolygon, Polygon, LineString, MultiLineString
from shapely.ops import linemerge, polygonize, unary_union


logger = logging.getLogger(__name__)


def parse_districts_metadata(data: dict) -> List[dict]:
    """
    Извлечь metadata районов из ответа Overpass.
    
    Ищет relations с boundary=administrative и admin_level=9.
    
    Args:
        data: JSON ответ Overpass API
    
    Returns:
        Список районов:
        [
          {"osm_relation_id": 123, "name": "Центральный район", "osm_type": "relation"},
          {"osm_relation_id": 456, "name": "Кировский район", "osm_type": "relation"},
          ...
        ]
    """
    elements = data.get("elements", [])
    districts = []
    
    logger.info("Получено %d elements от Overpass", len(elements))

    for elem in elements:
        elem_type = elem.get("type")
        elem_id = elem.get("id")
        tags = elem.get("tags", {})
        
        if elem_type != "relation":
            continue
        
        if tags.get("boundary") != "administrative":
            continue
        
        if tags.get("admin_level") not in ["9", "10"]:
            continue
        
        name = (
            tags.get("name") or 
            tags.get("name:ru") or 
            tags.get("official_name") or
            tags.get("alt_name")
        )
        
        if not name:
            logger.debug(
                "Relation %s без name, теги: %s",
                elem_id,
                tags
            )
            continue
        
        districts.append({
            "osm_relation_id": elem_id,
            "osm_type": elem_type,
            "name": name,
        })
    
    logger.info("Распарсено %d районов из Overpass ответа", len(districts))
    return districts


def parse_ways_to_geometry(ways: List[dict]) -> Optional[object]:
    """
    Собрать геометрию района из outer ways используя shapely.ops.
    
    Подход:
    1. Создаем LineString из каждого way
    2. Используем linemerge для соединения связанных линий
    3. Используем polygonize для создания полигонов из замкнутых линий
    
    Args:
        ways: Список элементов type=way с geometry=[{lat, lon}, ...]
    
    Returns:
        shapely Polygon/MultiPolygon или None при ошибке
    """
    if not ways:
        logger.warning("Пустой список ways")
        return None
    
    lines = []
    for way in ways:
        if way.get("type") != "way":
            continue
        
        geometry = way.get("geometry", [])
        if len(geometry) < 2:
            continue
        
        coords = [(node["lon"], node["lat"]) for node in geometry]
        
        line = LineString(coords)
        if line.is_valid and not line.is_empty:
            lines.append(line)

    
    if not lines:
        logger.warning("Не удалось создать LineString из ways")
        return None
    
    logger.debug("Создано %d LineString из %d ways", len(lines), len(ways))
    
    multiline = MultiLineString(lines)
    
    merged = linemerge(multiline)
    
    if isinstance(merged, LineString):
        logger.debug("linemerge вернул одну линию")
        merged_lines = [merged]
    elif isinstance(merged, MultiLineString):
        logger.debug("linemerge вернул %d линий", len(merged.geoms))
        merged_lines = list(merged.geoms)
    else:
        logger.warning("linemerge вернул неожиданный тип: %s", type(merged))
        merged_lines = lines
    
    polygons = list(polygonize(merged_lines))
    
    if not polygons:
        logger.warning("polygonize не смог создать полигоны")
        
        longest = max(merged_lines, key=lambda l: l.length)
        if longest.is_ring or (longest.coords[0] == longest.coords[-1]):
            poly = Polygon(longest.coords)
            if poly.is_valid:
                logger.info("Создан полигон из самой длинной линии (fallback)")
                return poly

        
        return None
    
    logger.debug("polygonize создал %d полигонов", len(polygons))
    
    valid_polygons = []
    for poly in polygons:
        if not poly.is_valid:
            logger.debug("Полигон невалиден, применяем buffer(0)")
            poly = poly.buffer(0)
        
        if poly.is_valid and not poly.is_empty:
            valid_polygons.append(poly)
        else:
            logger.warning("Полигон остался невалидным или пустым")
    
    if not valid_polygons:
        logger.warning("Нет валидных полигонов после очистки")
        return None
    
    if len(valid_polygons) == 1:
        logger.info("Создан 1 полигон из %d ways", len(ways))
        return valid_polygons[0]
    else:
        logger.info("Создано %d полигонов из %d ways, объединяем", len(valid_polygons), len(ways))
        
        result = unary_union(valid_polygons)
        
        if isinstance(result, Polygon):
            logger.debug("unary_union объединил в один полигон")
            return result
        elif isinstance(result, MultiPolygon):
            logger.debug("unary_union вернул MultiPolygon из %d частей", len(result.geoms))
            return result
        else:
            logger.warning("unary_union вернул неожиданный тип: %s", type(result))
            return MultiPolygon(valid_polygons)