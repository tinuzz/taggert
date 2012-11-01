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

class ImagesColumns(object):
    filename  = 0
    datetime  = 1
    rotation  = 2
    latitude  = 3
    longitude = 4
    modified  = 5
    camera    = 6
    dtobject  = 7
    elevation = 8

class images(object):
    columns = ImagesColumns()

class TracksColumns(object):
    name      = 0
    starttime = 1
    endtime   = 2
    numpoints = 3
    uuid      = 4
    layer     = 5

class tracks(object):
    columns = TracksColumns()

class NotebookPages(object):
    images    = 0
    tracks    = 1
    points    = 2

class notebook(object):
    pages = NotebookPages()

class MapsourceColumns(object):
    mapid     = 0
    name      = 1

class mapsources(object):
    columns = MapsourceColumns()
