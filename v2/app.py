#!/usr/bin/python
from gi.repository import Gtk

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
        #self.ui.treeview0.set_model(self.imagestore)
        self.window.connect("delete-event", self.quit)
        #self.ui.menuitem_quit.connect("activate", self.quit)
        Gtk.main()

    def setup_gui(self):
        self.builder = Gtk.Builder()
        self.builder.add_from_file("taggert.glade")
        self.window = self.builder.get_object("window1")
        self.window.show_all()

    def quit(self, _widget, c):
        print "bla"
        Gtk.main_quit()
