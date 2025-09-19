# utils/compute_natal_degrees.py
"""Starter compute_natal_degrees function for AstraQuant."""

from datetime import datetime

def compute_natal_degrees(birth_iso, lat, lon):
    """Return a dict of planetary degrees for given birth datetime and location.
    Args:
        birth_iso (str): ISO datetime string e.g. '1999-01-01T00:00:00'
        lat (float): latitude
        lon (float): longitude
    Returns:
        dict: placeholder planetary degrees
    """
    try:
        dt = datetime.fromisoformat(birth_iso)
    except Exception:
        raise ValueError('birth_iso must be ISO format: YYYY-MM-DDTHH:MM:SS')

    # TODO: replace with real astro calculations
    return {
        'datetime': dt.isoformat(),
        'location': {'lat': lat, 'lon': lon},
        'sun': 0.0,
        'moon': 0.0,
        'mercury': 0.0,
        'venus': 0.0,
        'mars': 0.0
    }

if __name__ == '__main__':
    print(compute_natal_degrees('1999-01-01T00:00:00', 0.0, 0.0))
