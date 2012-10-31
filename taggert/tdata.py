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

"""tdata module, defines the TData class"""

from gi.repository import GObject

class TData(GObject.GObject):
    """
    Subclass GObject for storing runtime variables. Properties of this object
    can be bound to GSettings for transparent persistence, and handlers can
    be connected to property change notifications, for updating the GUI, etc.
    """

    imagedir           = GObject.property(type=str)
    lasttrackfolder    = GObject.property(type=str)
    tracktimezone      = GObject.property(type=str)
    alwaysthistimezone = GObject.property(type=bool, default=False)
    markersize         = GObject.property(type=int)
    trackwidth         = GObject.property(type=int)
    imagemarkersize    = GObject.property(type=int)
    mapsourceid        = GObject.property(type=str)

    def __init__(self):
        """Constructor, does nothing special"""
        GObject.GObject.__init__(self)

    def __repr__(self):
        return repr(self.__dict__)

    def connect_signals(self, handlers):
        """
        Connect specified handler to notify signal for specified properties.
        Argument is a dictionary, where the key is the property name and the
        value is the signal handler for the change notification.
        """
        for prop, handler in handlers.items():
            self.connect("notify::%s" % prop, handler)

GObject.type_register(TData)
