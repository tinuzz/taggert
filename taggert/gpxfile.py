#!/usr/bin/python

# gpximport.py - Used to import GPX XML files into applications
# This file was taken from GPX Viewer and modified for Taggert
# Later it was rewritten to use lxml.etree instead of xml.dom.minidom
# Used and relicensed with explicit permission from copyright holder
# GPX Viewer homepage: http://andrewgee.org/blog/projects/gpxviewer/
#
# Original code copyright (C) 2009 Andrew Gee
# Modifications copyright (C) 2012 Martijn Grendelman
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
import uuid
from pytz import timezone   # apt-get install python-tz
import os.path

class GPXfile(object):

    gpxfiles = []
    delta = None  # a timedelta object
    tz = None     # a pytz timezone object

    #def __init__(self):

    def import_gpx(self, filename, tz):
        self.tz = timezone(tz)
        self.delta = None

        ## minidom
        #doc = minidom.parse(filename)
        #doce = doc.documentElement
        #if doce.nodeName != "gpx":
        #    raise Exception

        # lxml
        tree = etree.parse(filename)
        root = tree.getroot()
        if root.xpath('local-name()') != "gpx":
            raise Exception

        trace = {}
        trace['filename'] = filename
        trace['tracks'] = []

        for node in root:
            nodeName = node.xpath('local-name()')
            if nodeName == "metadata":
                trace['metadata'] = self.fetch_metadata(node)
            if nodeName == "trk":
                track = self.fetch_track(node)
                if not track["name"]:
                    track["name"] =  "%s [%d]" % (os.path.basename(filename), len(trace['tracks']) +1 )
                trace['tracks'].append(track)
        self.gpxfiles.append(trace)

        # return the index of the just-added file, so the app can process it
        return len(self.gpxfiles) - 1

    def find_coordinates(self, dt):
        lat = None
        lon = None
        ele = None
        for f in self.gpxfiles:
            for t in f["tracks"]:
                for s in t["segments"]:
                    try:
                        s_start = s["points"][0]['time'].replace(tzinfo=None)
                        s_end = s["points"][-1]['time'].replace(tzinfo=None)
                        if dt >= s_start and dt <= s_end:
                            # we have found an appropriate segment
                            tx = s_start
                            latx = s["points"][0]['lat']
                            lonx = s["points"][0]['lon']
                            elex = s["points"][0]['ele']
                            for p in s["points"]:
                                t0 = p["time"].replace(tzinfo=None)
                                if t0 >= dt:
                                    # The point's time is greater than what we need
                                    lat = (latx + p["lat"]) / 2
                                    lon = (lonx + p["lon"]) / 2
                                    ele = (elex + p["ele"]) / 2
                                    break
                                else:
                                    latx = p["lat"]
                                    lonx = p["lon"]
                                    elex = p["ele"]
                    except KeyError:
                        pass
        return (lat,lon,ele)

    def fetch_track(self,node):
        track = {}
        track['segments'] = []
        track['name'] = ''
        track['uuid'] = str(uuid.uuid4())
        for tnode in node:
            nodeName = tnode.xpath('local-name()')
            if nodeName == "trkseg":
                track_segment = self.fetch_track_segment(tnode)
                if len(track_segment['points']) > 0:
                    track['segments'].append(track_segment)
            elif nodeName == "name":
                track["name"] = tnode.text
        return track

    def fetch_track_segment(self, tnode):
        trkseg = {}
        trkseg['points'] = []
        for tsnode in tnode:
            nodeName = tsnode.xpath('local-name()')
            if nodeName == "trkpt":
                trkseg['points'].append(self.fetch_track_point(tsnode))
        return trkseg

    def fetch_track_point(self, tsnode):
        point = {}
        if tsnode.get("lat") != "" and tsnode.get("lon") != "":
            point['lat'] = float(tsnode.get("lat"))
            point['lon'] = float(tsnode.get("lon"))

        for tpnode in tsnode:
            nodeName = tpnode.xpath('local-name()')
            if nodeName == "ele":
                point['ele'] = float(tpnode.text)
            elif nodeName == "desc":
                point['description'] = tpnode.text
            elif nodeName == "time":
                t0 = parse_xml_date(tpnode.text)
                if not self.delta:
                    # Use is_dst = False; this may give incorrect results if the first
                    # trackpoint's time ambiguous due to a DST transition
                    # Also, strip the timezone information for calculating the delta
                    self.delta = self.tz.utcoffset(t0.replace(tzinfo=None), False)
                point['time'] = t0 + self.delta
            elif nodeName == "name":
                point['name'] = tpnode.text
        if not 'ele' in point:
            point['ele'] = 0.0
        return point

    def fetch_metadata(self, node):
        metadata = {}
        for mnode in node:
            nodeName = mnode.xpath('local-name()')
            if nodeName == "name":
                metadata['name'] = mnode.text

            elif nodeName == "desc":
                try:
                    metadata['description'] = mnode.text
                except:
                    metadata['description'] = "" #no description

            elif nodeName == "time":
                metadata['time'] = mnode.text

            elif nodeName == "author":
                metadata['author'] = {}
                for anode in mnode:
                    anodeName = anode.xpath('local-name()')
                    if anodeName == "name":
                        metadata['author']['name'] = anode.text
                    elif anodeName == "email":
                        metadata['author']['email'] = anode.text
                    elif anodeName == "link":
                        metadata['author']['link'] = anode.text

            elif nodeName == "copyright":
                metadata['copyright'] = {}
                if mnode.get("author") != "":
                    metadata['copyright']['author'] = mnode.get("author")
                for cnode in mnode:
                    cnodeName = cnode.xpath('local-name()')
                    if cnodeName == "year":
                        metadata['copyright']['year'] = cnode.text
                    elif cnodeName == "license":
                        metadata['copyright']['license'] = cnode.text

            elif nodeName == "link":
                metadata['link'] = {}
                if mnode.get("href") != "":
                    metadata['link']['href'] = mnode.get("href")
                for lnode in mnode:
                    lnodeName = lnode.xpath('local-name()')
                    if lnodeName == "text":
                        metadata['link']['text'] = lnode.text
                    elif lnodeName == "type":
                        metadata['link']['type'] = lnode.text

            elif nodeName == "time":
                metadata['time'] = parse_xml_date(mnode.text)

            elif nodeName == "keywords":
                metadata['keywords'] = mnode.text

        return metadata
