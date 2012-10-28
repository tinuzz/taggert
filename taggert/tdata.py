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

from gi.repository import GObject

class TData(GObject.GObject):

    imagedir           = GObject.property(type=str)
    lasttrackfolder    = GObject.property(type=str)
    tracktimezone      = GObject.property(type=str)
    alwaysthistimezone = GObject.property(type=bool, default=False)
    markersize         = GObject.property(type=int)
    trackwidth         = GObject.property(type=int)

    def __init__(self):
        GObject.GObject.__init__(self)

    def connect_signals(self, handlers):
        for prop, handler in handlers.items():
            self.connect("notify::%s" % prop, handler)

GObject.type_register(TData)
