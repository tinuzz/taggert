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

from gi.repository import Champlain

class ImageMarker(Champlain.Point):

    def __init__(self, treeiter, filename, lat, lon, clicked):
        Champlain.Point.__init__(self)
        self.filename = filename
        self.treeiter = treeiter
        self.set_location(lat, lon)
        self.set_selectable(True)
        #self.set_draggable(True)
        self.set_property('reactive', True)
        self.connect('button-press', clicked)
