#   Copyright 2012 Martijn Grendelman <m@rtijn.net>
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

"""tfunctions module, defines Taggert's general purpose functions"""

import fractions
from math import modf
from gi.repository import Clutter

def float_to_fraction(value):
    """
    Return a Fraction for a floating point value
    """
    return fractions.Fraction.from_float(value).limit_denominator(99999)

def dms_to_decimal(degrees, minutes, seconds, sign=' '):
    """
    Return a decimal representation of a coordinate specified in degrees,
    minutes and seconds
    """
    return (-1 if sign[0] in 'SWsw' else 1) * (
        float(degrees)        +
        float(minutes) / 60   +
        float(seconds) / 3600
    )

def decimal_to_dms(decimal):
    """
    Return a list of fractions representing degrees, minutes and seconds
    of a coordinate specified in a decimal value
    """
    remainder, degrees = modf(abs(decimal))
    remainder, minutes = modf(remainder * 60)
    return [float_to_fraction(n) for n in (degrees, minutes, remainder * 60)]

def clutter_color (gdkcolor, opacity=256):
    """
    Convert a Gdk.Color into a Clutter.Color
    """
    return Clutter.Color.new(
        *[x / 256 for x in [gdkcolor.red, gdkcolor.green, gdkcolor.blue, (256 * opacity) -1]])

def color_tuple (gdkcolor):
    """
    Return a 3-tuple of RGB values from a Gdk.Color
    """
    return (gdkcolor.red, gdkcolor.green, gdkcolor.blue)


def latlon_to_text(lat, lon):
    """
    Return a formatted string for a pair of coordinates
    """
    return "%s %.5f, %s %.5f" % (
            'N' if lat >= 0 else 'S', abs(lat),
            'E' if lon >= 0 else 'W', abs(lon)
        )


def timezone_split(tz):
    """
    Return a 2-tuple containing the timezone in two parts
    'Europe/Amsterdam' => ('Europe', 'Amsterdam')
    'UTC'              => ('UTC', '')
    """
    if tz.find('/') >= 0:
        a,b = tz.split('/', 1)
    else:
        a = tz
        b = ''
    return (a,b)
