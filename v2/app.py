#!/usr/bin/python
import os
import pyexiv2
from gi.repository import Gtk
from pprint import pprint

class App(object):

    def __init__(self):
        #gobject.threads_init()
        #gtk.gdk.threads_init()

        self.marker_lat = 0
        self.marker_lon = 0
        self.imagedir   = '/home/martijn/Pictures/2012'

        #self.imagestore = Gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING,
        #    gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING)
        #self.populate_store(self.imagestore, self.imagedir)

    def main(self):
        self.setup_gui()
        self.setup_gui_events()
        self.populate_store1(self.imagedir)
        Gtk.main()

    def setup_gui(self):
        self.builder = Gtk.Builder()
        self.builder.add_from_file("taggert.glade")
        self.window = self.builder.get_object("window1")
        self.window.set_position(Gtk.WindowPosition.CENTER)
        self.window.show_all()

    def setup_gui_events(self):
        # X
        self.window.connect("delete-event", self.quit)
        # File -> Quit
        quit = self.builder.get_object("imagemenuitem5")
        quit.connect("activate", self.quit, False)

    def quit(self, _window, _event):
        print "bla"
        Gtk.main_quit()

    def populate_store1(self, imagedir):
        store = self.builder.get_object("liststore1")
        store.clear()
        if imagedir:
            for fl in os.listdir(imagedir):
                if not fl[0] == '.':
                    fname = os.path.join(imagedir, fl)
                    if not os.path.isdir(fname):
                        if os.path.splitext(fname)[1].lower() == ".jpg":
                            metadata = pyexiv2.ImageMetadata(fname)
                            metadata.read()
                            try:
                                dt = metadata['Exif.Image.DateTime'].raw_value
                            except KeyError:
                                dt = ''
                            try:
                                rot =  metadata['Exif.Image.Orientation'].raw_value
                            except KeyError:
                                rot = '1'
                            try:
                                imglat = metadata['Exif.GPSInfo.GPSLatitude'].human_value
                            except KeyError:
                                imglat = ''
                            try:
                                imglon = metadata['Exif.GPSInfo.GPSLongitude'].human_value
                            except KeyError:
                                imglon = ''
                            store.append([fl, dt, rot, imglat, imglon])
