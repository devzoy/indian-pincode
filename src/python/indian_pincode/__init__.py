import json
import sqlite3
import os
import math
from functools import lru_cache
from typing import List, Dict, Union, Optional

# Path configuration
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR = os.path.join(_BASE_DIR, "data")
_COMPRESSED_JSON_PATH = os.path.join(_DATA_DIR, "pincodes.compressed.json")
_DB_PATH = os.path.join(_DATA_DIR, "pincodes.sqlite")

# Lazy loading for validation data
_VALIDATION_DATA = None

def _load_validation_data():
    global _VALIDATION_DATA
    if _VALIDATION_DATA is None:
        try:
            with open(_COMPRESSED_JSON_PATH, "r") as f:
                _VALIDATION_DATA = json.load(f)
        except FileNotFoundError:
            _VALIDATION_DATA = {}
    return _VALIDATION_DATA

def validate(pincode: Union[str, int]) -> bool:
    """
    Validate if a pincode exists in the database.
    
    Args:
        pincode: The 6-digit pincode to validate (str or int).
        
    Returns:
        bool: True if valid and exists, False otherwise.
    """
    pincode = str(pincode).strip()
    if len(pincode) != 6 or not pincode.isdigit():
        return False
    
    prefix = pincode[:3]
    suffix = int(pincode[3:])
    
    data = _load_validation_data()
    if prefix in data:
        # Binary search could be faster if lists are huge, but for simple lists 'in' is O(N)
        # The lists are sorted, so we could use bisect, but 'in' is fast enough for small lists.
        # Actually, the suffixes are integers in the JSON.
        return suffix in data[prefix]
    
    return False

def _dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def lookup(pincode: Union[str, int]) -> List[Dict]:
    """
    Get details for a pincode.
    
    Args:
        pincode: The 6-digit pincode.
        
    Returns:
        List[Dict]: A list of post office details associated with the pincode.
    """
    pincode = str(pincode).strip()
    if not validate(pincode):
        return []
        
    try:
        conn = sqlite3.connect(_DB_PATH)
        conn.row_factory = _dict_factory
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM pincodes WHERE pincode = ?", (pincode,))
        results = cursor.fetchall()
        conn.close()
        return results
    except sqlite3.Error:
        return []

def search_districts(query: str, fuzzy: bool = True) -> List[str]:
    """
    Search for districts matching the query.
    
    Args:
        query: The search query string.
        fuzzy: If True, performs a partial match (LIKE %query%).
        
    Returns:
        List[str]: List of matching district names.
    """
    query = query.strip()
    if not query:
        return []
        
    try:
        conn = sqlite3.connect(_DB_PATH)
        cursor = conn.cursor()
        
        if fuzzy:
            sql = "SELECT DISTINCT district FROM pincodes WHERE district LIKE ? ORDER BY district"
            params = (f"%{query}%",)
        else:
            sql = "SELECT DISTINCT district FROM pincodes WHERE district = ? ORDER BY district"
            params = (query,)
            
        cursor.execute(sql, params)
        results = [row[0] for row in cursor.fetchall()]
        conn.close()
        return results
    except sqlite3.Error:
        return []

def _haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) * math.sin(dlat / 2) +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) * math.sin(dlon / 2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    d = R * c
    return d

def find_nearby(lat: float, lng: float, radius_km: float = 5.0) -> List[Dict]:
    """
    Find pincodes within a given radius of a coordinate.
    
    Args:
        lat: Latitude.
        lng: Longitude.
        radius_km: Radius in kilometers.
        
    Returns:
        List[Dict]: List of nearby post offices with distance.
    """
    try:
        conn = sqlite3.connect(_DB_PATH)
        conn.row_factory = _dict_factory
        cursor = conn.cursor()
        
        # 1. Bounding box filter (approximate)
        # 1 degree lat ~= 111 km
        # 1 degree lng ~= 111 km * cos(lat)
        
        lat_change = radius_km / 111.0
        lng_change = radius_km / (111.0 * math.cos(math.radians(lat)))
        
        min_lat = lat - lat_change
        max_lat = lat + lat_change
        min_lng = lng - lng_change
        max_lng = lng + lng_change
        
        cursor.execute("""
            SELECT * FROM pincodes 
            WHERE latitude BETWEEN ? AND ? 
            AND longitude BETWEEN ? AND ?
        """, (min_lat, max_lat, min_lng, max_lng))
        
        candidates = cursor.fetchall()
        conn.close()
        
        results = []
        for item in candidates:
            try:
                p_lat = float(item['latitude'])
                p_lng = float(item['longitude'])
                dist = _haversine(lat, lng, p_lat, p_lng)
                
                if dist <= radius_km:
                    item['distance_km'] = round(dist, 2)
                    results.append(item)
            except (ValueError, TypeError):
                continue
                
        # Sort by distance
        results.sort(key=lambda x: x['distance_km'])
        return results
        
    except sqlite3.Error:
        return []
