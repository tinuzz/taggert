#!/usr/bin/python

# gpxfile.py - Used to import GPX XML files into applications
# GPX files are maintained as a list of lxml.etree ElementTrees
# Copyright (C) 2014 Martijn Grendelman
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

from pprint import pprint
from lxml import etree
from iso8601 import parse_date as parse_xml_date
from datetime import datetime, timedelta
from pytz import timezone   # apt-get install python-tz
from math import radians, sin, cos, atan2, sqrt
import os.path
import copy
import version

minimal_xml = """<gpx xmlns="http://www.topografix.com/GPX/1/1" version="1.1" creator="Taggert v%s">
</gpx>
""" % version.VERSION

class Track(object):
    tid = None
    trk = None
    tz = timezone('UTC')     # a pytz timezone object
    starttime = None
    endtime = None
    distance = None
    ns = '{http://www.topografix.com/GPX/1/1}'

    def __init__(self, tid, trk=None, tz=None):
        self.tid =  tid
        if trk is not None:
            self.set_track(trk)
        if tz is not None:
            self.tz = tz

    def set_track(self, trk):
        self.trk = trk

    def parse_timestamps(self):
        alltimes = self.trk.findall(self.ns + 'trkseg/' + self.ns + 'trkpt/' + self.ns + 'time')
        starttime = parse_xml_date(alltimes[0].text).replace(tzinfo=None)
        endtime = parse_xml_date(alltimes[-1].text).replace(tzinfo=None)
        delta = self.tz.utcoffset(starttime, False)
        self.starttime = starttime + delta
        self.endtime = endtime + delta

    def get_timestamps(self):
        if self.starttime is None:
            self.parse_timestamps()
        return (self.starttime, self.endtime)

    def get_starttime(self):
        if self.starttime is None:
            self.parse_timestamps()
        return self.starttime

    def get_name(self):
        return self.trk.findtext(self.ns + 'name') or \
            self.get_starttime().strftime('%Y-%m-%d %H:%M:%S')

    def get_points(self):
        return self.trk.findall(self.ns + 'trkseg/' + self.ns + 'trkpt')

    def trkpt_distance(self, lat1, lon1, lat2, lon2):
        radius = 6371000 # meter
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2) * sin(dlat/2) + cos(lat1) \
            * cos(lat2) * sin(dlon/2) * sin(dlon/2)
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        d = radius * c
        return d

    def get_distance(self):
        if self.distance is None:
            distance = 0
            oldlat = None
            for trkpt in self.trk.findall(self.ns + 'trkseg/' + self.ns + 'trkpt'):
                lat = float(trkpt.get('lat'))
                lon = float(trkpt.get('lon'))
                if oldlat != None:
                    distance += self.trkpt_distance(oldlat, oldlon, lat, lon)
                oldlat = lat
                oldlon = lon
            self.distance = distance
        return self.distance

class GPXfile(object):

    delta = None  # a timedelta object
    tz = None     # a pytz timezone object
    data_dir = '.'
    tree = etree.ElementTree(etree.fromstring(minimal_xml))
    schemafile = None
    schema = None
    xmlparser = None
    ns = '{http://www.topografix.com/GPX/1/1}'
    tracks = {}

    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.schemafile = os.path.join(self.data_dir, 'gpx.xsd')
        self.schema = etree.XMLSchema(file=self.schemafile)
        self.xmlparser = etree.XMLParser(schema=self.schema)

    def import_gpx(self, filename, tz):
        self.tz = timezone(tz)
        self.delta = None

        # lxml
        try:
           tree = etree.parse(filename, self.xmlparser)
        except etree.XMLSyntaxError as e:
            return (False, e)

        # Use the first file as skeleton
        if self.tree is None:
            self.tree = tree

        root = tree.getroot()
        return (self.parse_tracks(root), 'Success')

    def parse_tracks(self, root):
        dest_root = self.tree.getroot()
        ids = []
        tracks = root.findall(self.ns + 'trk')
        for trk in tracks:
            # Copy the <trk> element to the XML tree
            trk2 = copy.deepcopy(trk)
            dest_root.append(trk2)
            # Compose a Track object
            tid = id(trk2)
            tobj = Track(tid, trk2, self.tz)
            self.tracks[tid] = tobj
            ids.append(tid)
        # Return a list of newly added track ids
        return ids

    # Return a dict of track objects
    def get_tracks(self, id_list):
        return { k: v for k, v in self.tracks.iteritems() if k in id_list }

    # Find the XML tree that contains the track with a given tid
    # and remove the track from it
    def remove_track(self, tid):
        if tid in self.tracks:
            trk = self.tracks[tid].trk
            root = self.tree.getroot()
            root.remove(trk)
            del self.tracks[tid]

    # Dump the currently loaded tracks to a GPX file
    def save_gpx(self, fname=None):
        if fname is None:
            fname = 'zzzzzzzzzzz.gpx'
        self.tree.write(fname, xml_declaration = True, encoding='utf-8')

    def find_coordinates(self, dt):
        lat = None
        lon = None
        ele = None
        for tid, tobj in self.tracks.iteritems():
            if dt >= tobj.starttime and dt <= tobj.endtime:
                pprint(tobj)

