#!/usr/bin/python

# gpximport.py - Used to import GPX XML files into applications
# This file was taken from GPX Viewer and modified for Taggert
# GPX Viewer homepage: http://andrewgee.org/blog/projects/gpxviewer/
#
# Original code copyright (C) 2009 Andrew Gee
# Modifications copyright (C) 2012 Martijn Grendelman

from pprint import pprint
import xml.dom.minidom as minidom
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
        doc = minidom.parse(filename)
        doce = doc.documentElement
        if doce.nodeName != "gpx":
            raise Exception

        trace = {}
        trace['filename'] = filename
        trace['tracks'] = []

        e = doce.childNodes
        for node in e:
            if node.nodeName == "metadata":
                trace['metadata'] = self.fetch_metadata(node)
            if node.nodeName == "trk":
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
        for tnode in node.childNodes:
            if tnode.nodeName == "trkseg":
                track_segment = self.fetch_track_segment(tnode)
                if len(track_segment['points']) > 0:
                    #track['segments'].append(self.fetch_track_segment(tnode))
                    track['segments'].append(track_segment)
            elif tnode.nodeName == "name":
                track["name"] = tnode.childNodes[0].nodeValue
        return track

    def fetch_track_segment(self, tnode):
        trkseg = {}
        trkseg['points'] = []
        for tsnode in tnode.childNodes:
            if tsnode.nodeName == "trkpt":
                trkseg['points'].append(self.fetch_track_point(tsnode))
        return trkseg

    def fetch_track_point(self, tsnode):
        point = {}
        if tsnode.attributes["lat"] != "" and tsnode.attributes["lon"] != "":
            point['lat'] = float(tsnode.attributes["lat"].value)
            point['lon'] = float(tsnode.attributes["lon"].value)

        for tpnode in tsnode.childNodes:
            if tpnode.nodeName == "ele":
                point['ele'] = float(tpnode.childNodes[0].nodeValue)
            elif tpnode.nodeName == "desc":
                point['description'] = tpnode.childNodes[0].nodeValue
            elif tpnode.nodeName == "time":
                t0 = parse_xml_date(tpnode.childNodes[0].nodeValue)
                if not self.delta:
                    # Use is_dst = False; this may give incorrect results if the first
                    # trackpoint's time ambiguous due to a DST transition
                    # Also, strip the timezone information for calculating the delta
                    self.delta = self.tz.utcoffset(t0.replace(tzinfo=None), False)
                point['time'] = t0 + self.delta
            elif tpnode.nodeName == "name":
                point['name'] = tpnode.childNodes[0].nodeValue
        if not 'ele' in point:
            point['ele'] = 0.0
        return point


    def fetch_metadata(self, node):
        metadata = {}
        for mnode in node.childNodes:
            if mnode.nodeName == "name":
                metadata['name'] = mnode.childNodes[0].nodeValue

            elif mnode.nodeName == "desc":
                try:
                    metadata['description'] = mnode.childNodes[0].nodeValue
                except:
                    metadata['description'] = "" #no description

            elif mnode.nodeName == "time":
                metadata['time'] = mnode.childNodes[0].nodeValue

            elif mnode.nodeName == "author":
                metadata['author'] = {}
                for anode in mnode.childNodes:
                    if anode.nodeName == "name":
                        metadata['author']['name'] = anode.childNodes[0].nodeValue
                    elif anode.nodeName == "email":
                        metadata['author']['email'] = anode.childNodes[0].nodeValue
                    elif anode.nodeName == "link":
                        metadata['author']['link'] = anode.childNodes[0].nodeValue

            elif mnode.nodeName == "copyright":
                metadata['copyright'] = {}
                if mnode.attributes["author"].value != "":
                    metadata['copyright']['author'] = mnode.attributes["author"].value
                for cnode in mnode.childNodes:
                    if cnode.nodeName == "year":
                        metadata['copyright']['year'] = cnode.childNodes[0].nodeValue
                    elif cnode.nodeName == "license":
                        metadata['copyright']['license'] = cnode.childNodes[0].nodeValue

            elif mnode.nodeName == "link":
                metadata['link'] = {}
                if mnode.attributes["href"].value != "":
                    metadata['link']['href'] = mnode.attributes["href"].value
                for lnode in mnode.childNodes:
                    if lnode.nodeName == "text":
                        metadata['link']['text'] = lnode.childNodes[0].nodeValue
                    elif lnode.nodeName == "type":
                        metadata['link']['type'] = lnode.childNodes[0].nodeValue

            elif mnode.nodeName == "time":
                metadata['time'] = parse_xml_date(mnode.childNodes[0].nodeValue)

            elif mnode.nodeName == "keywords":
                metadata['keywords'] = mnode.childNodes[0].nodeValue

        return metadata
