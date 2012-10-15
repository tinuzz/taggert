# polygon.py - Extend a Champlain.PathLayer to automate appending points
# This code was taken from GottenGeography
# Copyright (C) 2010 Robert Bruce Park
# This code is licensed under the GNU GENERAL PUBLIC LICENSE version 3

from gi.repository import Champlain

class Polygon(Champlain.PathLayer):
    """Extend a Champlain.PathLayer to automate appending points.

    >>> poly = Polygon()
    >>> coord = poly.append_point(49.899754, -97.137494, None)
    >>> (coord.lat, coord.lon, coord.ele)
    (49.899754, -97.137494, 0.0)
    >>> coord = poly.append_point(53.529201, -113.499324, 1000)
    >>> (coord.lat, coord.lon, coord.ele)
    (53.529201, -113.499324, 1000.0)
    """

    def __init__(self):
        Champlain.PathLayer.__init__(self)
        self.set_stroke_width(4)

    def append_point(self, latitude, longitude, elevation=None):
        """Simplify appending a point onto a polygon."""
        coord = Champlain.Coordinate.new_full(latitude, longitude)
        coord.lat = latitude
        coord.lon = longitude
        try:
            coord.ele = float(elevation)
        except (ValueError, TypeError):
            coord.ele = 0.0
        self.add_node(coord)
        return coord
