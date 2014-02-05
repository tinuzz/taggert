"""ISO 8601 date time string parsing

Basic usage:
>>> import iso8601
>>> iso8601.parse_date("2007-01-25T12:00:00Z")
datetime.datetime(2007, 1, 25, 12, 0, tzinfo=<iso8601.iso8601.Utc ...>)
>>>

Copyright (c) 2007 - 2013 Michael Twomey

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be included
in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""

from datetime import (
    datetime,
    timedelta,
    tzinfo
)
from decimal import Decimal
import logging
import sys
import re

__all__ = ["parse_date", "ParseError"]

LOG = logging.getLogger(__name__)

if sys.version_info >= (3, 0, 0):
    _basestring = str
else:
    _basestring = basestring


# Adapted from http://delete.me.uk/2005/03/iso8601.html
ISO8601_REGEX = re.compile(
    r"""
    (?P<year>[0-9]{4})
    (-{0,1}(?P<month>[0-9]{1,2})){1}
    (-{0,1}(?P<day>[0-9]{1,2})){1}
    (
        (?P<separator>[ T])
        (?P<hour>[0-9]{2})
        (:{0,1}(?P<minute>[0-9]{2})){0,1}
        (
            :{0,1}(?P<second>[0-9]{1,2})
            (\.(?P<second_fraction>[0-9]+)){0,1}
        ){0,1}
        (?P<timezone>
            Z
            |
            (
                (?P<tz_sign>[-+])
                (?P<tz_hour>[0-9]{2})
                :{0,1}
                (?P<tz_minute>[0-9]{2}){0,1}
            )
        ){0,1}
    ){0,1}
    """,
    re.VERBOSE
)

class ParseError(Exception):
    """Raised when there is a problem parsing a date string"""

# Yoinked from python docs
ZERO = timedelta(0)
class Utc(tzinfo):
    """UTC

    """
    def utcoffset(self, dt):
        return ZERO

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return ZERO

UTC = Utc()

class FixedOffset(tzinfo):
    """Fixed offset in hours and minutes from UTC

    """
    def __init__(self, offset_hours, offset_minutes, name):
        self.__offset_hours = offset_hours  # Keep for later __getinitargs__
        self.__offset_minutes = offset_minutes  # Keep for later __getinitargs__
        self.__offset = timedelta(hours=offset_hours, minutes=offset_minutes)
        self.__name = name

    def __eq__(self, other):
        if isinstance(other, FixedOffset):
            return (
                (other.__offset == self.__offset)
                and
                (other.__name == self.__name)
            )
        if isinstance(other, tzinfo):
            return other == self
        return False

    def __getinitargs__(self):
        return (self.__offset_hours, self.__offset_minutes, self.__name)

    def utcoffset(self, dt):
        return self.__offset

    def tzname(self, dt):
        return self.__name

    def dst(self, dt):
        return ZERO

    def __repr__(self):
        return "<FixedOffset %r %r>" % (self.__name, self.__offset)

def to_int(d, key, default_to_zero=False, default=None):
    """Pull a value from the dict and convert to int

    :param default_to_zero: If the value is None or empty, treat it as zero
    :param default: If the value is missing in the dict use this default

    """
    value = d.get(key, default)
    LOG.debug("Got %r for %r with default %r", value, key, default)
    if (value in ["", None]) and default_to_zero:
        return 0
    if value is None:
        raise ParseError("Unable to read %s from %s" % (key, d))
    return int(value)

def parse_timezone(matches, default_timezone=UTC):
    """Parses ISO 8601 time zone specs into tzinfo offsets

    """

    if matches["timezone"] == "Z":
        return UTC
    # This isn't strictly correct, but it's common to encounter dates without
    # timezones so I'll assume the default (which defaults to UTC).
    # Addresses issue 4.
    if matches["timezone"] is None:
        return default_timezone
    sign = matches["tz_sign"]
    hours = to_int(matches, "tz_hour")
    minutes = to_int(matches, "tz_minute", default_to_zero=True)
    description = "%s%02d:%02d" % (sign, hours, minutes)
    if sign == "-":
        hours = -hours
        minutes = -minutes
    return FixedOffset(hours, minutes, description)

def parse_date(datestring, default_timezone=UTC):
    """Parses ISO 8601 dates into datetime objects

    The timezone is parsed from the date string. However it is quite common to
    have dates without a timezone (not strictly correct). In this case the
    default timezone specified in default_timezone is used. This is UTC by
    default.
    """
    if not isinstance(datestring, _basestring):
        raise ParseError("Expecting a string %r" % datestring)
    m = ISO8601_REGEX.match(datestring)
    if not m:
        raise ParseError("Unable to parse date string %r" % datestring)
    groups = m.groupdict()
    LOG.debug("Parsed %s into %s with default timezone %s", datestring, groups, default_timezone)

    tz = parse_timezone(groups, default_timezone=default_timezone)

    groups["second_fraction"] = int(Decimal("0.%s" % (groups["second_fraction"] or 0)) * Decimal("1000000.0"))

    try:
        return datetime(
            year=to_int(groups, "year"),
            month=to_int(groups, "month"),
            day=to_int(groups, "day"),
            hour=to_int(groups, "hour", default_to_zero=True),
            minute=to_int(groups, "minute", default_to_zero=True),
            second=to_int(groups, "second", default_to_zero=True),
            microsecond=groups["second_fraction"],
            tzinfo=tz,
        )
    except Exception as e:
        raise ParseError(e)
