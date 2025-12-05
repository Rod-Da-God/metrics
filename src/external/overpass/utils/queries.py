from typing import List
import logging

logger = logging.getLogger(__name__)


def build_city_area_query(city_name: str) -> str:
    """
    Построить Overpass QL для поиска relations районов города.
    
    Стратегия:
    1. Поиск города через area по названию
    2. Поиск всех административных районов (admin_level=9) внутри этой области
    
    Args:
        city_name: Название города (Хабаровск, Владивосток)
    
    Returns:
        Overpass QL запрос
    """
    query = f"""
[out:json][timeout:120];
area["name"="{city_name}"]->.a;
(
  relation(area.a)["boundary"="administrative"]["admin_level"="9"];
);
out tags;
"""
    return query.strip()


def build_city_boundary_query(city_name: str) -> str:
    """
    Построить Overpass QL для поиска границ самого города.
    
    Используется как фолбек для мелких городов без районов.
    Ищет relation с place=city и возвращает его геометрию напрямую.
    
    Args:
        city_name: Название города (Благовещенск, Магадан)
    
    Returns:
        Overpass QL запрос
    """
    query = f"""
[out:json][timeout:120];
(
  relation["place"="city"]["name"="{city_name}"];
  relation["boundary"="administrative"]["admin_level"="6"]["name"="{city_name}"];
);
out geom;
"""
    return query.strip()


def build_districts_geometry_query(relation_ids: List[int]) -> str:
    """
    Построить Overpass QL для получения outer ways районов.
    
    Args:
        relation_ids: Список OSM relation ID районов
    
    Returns:
        Overpass QL запрос
    """
    ids_str = ",".join(map(str, relation_ids))
    query = f"""
[out:json][timeout:180];
relation(id:{ids_str})->.rels;
way(r.rels:"outer")->.outerWays;
.outerWays out tags geom;
"""
    return query.strip()