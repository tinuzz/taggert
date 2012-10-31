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

"""tsettings module, defines the TSettings class"""

from gi.repository import Gio
from gi.repository import Gdk

class TSettings(Gio.Settings):
    """
    Subclass Gio.Settings to add some convenience methods
    """

    def __init___(self, schema):
        """Constructor, does nothing special"""
        Gio.Settings.__init__(self, schema)

    def bind(self, key, widget, prop=None, flags=Gio.SettingsBindFlags.DEFAULT):
        """
        Bind GObject properties to GSettings key/values, using default flags.
        The GSettings key is used as the name of the property if not specified
        explicitly. This is merely a convenience method, that was taken from
        GottenGeography.
        """
        Gio.Settings.bind(self, key, widget, prop or key, flags)

    def get_color(self, key):
        """
        Returns a Gdk.Color using the values from the specified setting, which
        should be a 3-tuple of RGB values
        """
        return Gdk.Color(*self.get_value(key).unpack())

    def get_unpacked(self, key):
        """
        Return the unpacked value of the specified setting
        """
        return self.get_value(key).unpack()
