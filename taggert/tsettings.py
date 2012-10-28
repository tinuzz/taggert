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

from gi.repository import Gio

class TSettings(Gio.Settings):

    def __init___(self, schema):
        Gio.Settings.__init__(self, schema)

    # Convenience method, taken from GottenGeography
    def bind(self, key, widget, prop=None, flags=Gio.SettingsBindFlags.DEFAULT):
        Gio.Settings.bind(self, key, widget, prop or key, flags)
