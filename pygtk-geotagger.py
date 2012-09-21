#!/usr/bin/python

"""
Copyright (C) Hadley Rich 2008 <hads@nice.net.nz>
based on main.c - with thanks to John Stowers

This is free software: you can redistribute it and/or modify it
under the terms of the GNU General Public License
as published by the Free Software Foundation; version 2.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, see <http://www.gnu.org/licenses/>.
"""

import sys
import os.path
import os
import gtk.gdk
import gobject
import pyexiv2  # apt-get install python-pyexiv2

gobject.threads_init()
gtk.gdk.threads_init()

#Try static lib first
mydir = os.path.dirname(os.path.abspath(__file__))
libdir = os.path.abspath(os.path.join(mydir, "..", "python", ".libs"))
sys.path.insert(0, libdir)

import osmgpsmap
print "using library: %s (version %s)" % (osmgpsmap.__file__, osmgpsmap.__version__)

assert osmgpsmap.__version__ == "0.7.3"

class DummyMapNoGpsPoint(osmgpsmap.GpsMap):
    def do_draw_gps_point(self, drawable):
        pass
gobject.type_register(DummyMapNoGpsPoint)

class DummyLayer(gobject.GObject, osmgpsmap.GpsMapLayer):
    def __init__(self):
        gobject.GObject.__init__(self)

    def do_draw(self, gpsmap, gdkdrawable):
        pass

    def do_render(self, gpsmap):
        pass

    def do_busy(self):
        return False

    def do_button_press(self, gpsmap, gdkeventbutton):
        return False
gobject.type_register(DummyLayer)

class UI(gtk.Window):
    def __init__(self):
        gtk.Window.__init__(self, gtk.WINDOW_TOPLEVEL)

        self.set_default_size(800, 600)
        self.set_position(gtk.WIN_POS_CENTER)
        self.connect('destroy', lambda x: gtk.main_quit())
        self.set_title('PyGTK Geotagger')

        self.vbox0 = gtk.VBox(False,0)
        self.add(self.vbox0)

        mb = gtk.MenuBar()
        filemenu = gtk.Menu()
        filem = gtk.MenuItem("File")
        filem.set_submenu(filemenu)

        openm = gtk.ImageMenuItem(gtk.STOCK_OPEN)
        openm.connect("activate", self.select_dir)
        filemenu.append(openm)

        sep = gtk.SeparatorMenuItem()
        filemenu.append(sep)

        #exit = gtk.MenuItem("Exit")
        exit = gtk.ImageMenuItem(gtk.STOCK_QUIT)
        exit.connect("activate", gtk.main_quit)
        filemenu.append(exit)

        mb.append(filem)
        self.vbox0.pack_start(mb, False, False, 0)

        self.hbox0 = gtk.HBox(False, 0)
        self.vbox0.pack_start(self.hbox0)

        mydir='/home/martijn/Data/images/foto-video/iphion'

        store = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)

        for fl in os.listdir(mydir):
            if not fl[0] == '.':
                fname = os.path.join(mydir, fl)
                if not os.path.isdir(fname):
                    if os.path.splitext(fname)[1].lower() == ".jpg":
                        metadata = pyexiv2.ImageMetadata(fname)
                        metadata.read()
                        dt = metadata['Exif.Image.DateTime'].raw_value
                        store.append([fl, dt])

        treeview = gtk.TreeView(model=store)
        treeview.set_grid_lines(gtk.TREE_VIEW_GRID_LINES_HORIZONTAL)

        cell = gtk.CellRendererText()
        #cell.set_property('cell-background', 'cyan')
        col0 = gtk.TreeViewColumn('Filename', cell, text=0)
        col0.set_min_width(180)
        col0.set_sort_column_id(0)
        treeview.append_column(col0)

        cell = gtk.CellRendererText()
        #cell.set_property('cell-background', 'cyan')
        col1 = gtk.TreeViewColumn('EXIF DateTime', cell, text=1)
        col1.set_min_width(180)
        col1.set_sort_column_id(1)
        treeview.append_column(col1)

        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_ALWAYS)
        self.hbox0.pack_start(sw, False)
        #sw.show()

        #self.hbox0.pack_start(treeview, False)
        sw.add(treeview)

        self.vbox = gtk.VBox(False, 0)
        self.hbox0.pack_start(self.vbox)

        #self.vbox1 = gtk.VBox(False, 0)
        #self.hbox0.pack_start(self.vbox1)

        #valign = gtk.Alignment(0, 0, 0, 0)
        #self.vbox1.pack_start(valign)

        #ok = gtk.Button("OK")
        #ok.set_size_request(70, 30)
        #self.vbox1.pack_start(ok)

        if 0:
            self.osm = DummyMapNoGpsPoint()
        else:
            self.osm = osmgpsmap.GpsMap()
        self.osm.layer_add(
                    osmgpsmap.GpsMapOsd(
                        show_dpad=True,
                        show_zoom=True))
        self.osm.layer_add(
                    DummyLayer())

        self.osm.connect('button_release_event', self.map_clicked)

        #connect keyboard shortcuts
        self.osm.set_keyboard_shortcut(osmgpsmap.KEY_FULLSCREEN, gtk.gdk.keyval_from_name("F11"))
        self.osm.set_keyboard_shortcut(osmgpsmap.KEY_UP, gtk.gdk.keyval_from_name("Up"))
        self.osm.set_keyboard_shortcut(osmgpsmap.KEY_DOWN, gtk.gdk.keyval_from_name("Down"))
        self.osm.set_keyboard_shortcut(osmgpsmap.KEY_LEFT, gtk.gdk.keyval_from_name("Left"))
        self.osm.set_keyboard_shortcut(osmgpsmap.KEY_RIGHT, gtk.gdk.keyval_from_name("Right"))

        #connect to tooltip
        self.osm.props.has_tooltip = True
        self.osm.connect("query-tooltip", self.on_query_tooltip)

        self.latlon_entry = gtk.Entry()

        zoom_in_button = gtk.Button(stock=gtk.STOCK_ZOOM_IN)
        zoom_in_button.connect('clicked', self.zoom_in_clicked)
        zoom_out_button = gtk.Button(stock=gtk.STOCK_ZOOM_OUT)
        zoom_out_button.connect('clicked', self.zoom_out_clicked)
        home_button = gtk.Button(stock=gtk.STOCK_HOME)
        home_button.connect('clicked', self.home_clicked)
        cache_button = gtk.Button('Cache')
        cache_button.connect('clicked', self.cache_clicked)

        self.vbox.pack_start(self.osm)
        hbox = gtk.HBox(False, 0)
        hbox.pack_start(zoom_in_button)
        hbox.pack_start(zoom_out_button)
        hbox.pack_start(home_button)
        hbox.pack_start(cache_button)

        #add ability to test custom map URIs
        ex = gtk.Expander("<b>Map Repository URI</b>")
        ex.props.use_markup = True
        vb = gtk.VBox()
        self.repouri_entry = gtk.Entry()
        # Use http://mt1.google.com/vt/lyrs=m@110&hl=pl&x=#X&y=#Y&z=#Z for Google maps
        # Use http://otile1.mqcdn.com/tiles/1.0.0/osm/#Z/#X/#Y.jpg for Mapquest-OSM
        # Use http://oatile1.mqcdn.com/tiles/1.0.0/sat/#Z/#X/#Y.jpg for Mapquest Open Aerial satellite images
        # Use http://c.tile.opencyclemap.org/cycle/#Z/#X/#Y.png for Opencyclemap
        self.repouri_entry.set_text(self.osm.props.repo_uri)
        self.image_format_entry = gtk.Entry()
        self.image_format_entry.set_text(self.osm.props.image_format)

        lbl = gtk.Label(
"""
Enter an repository URL to fetch map tiles from in the box below. Special metacharacters may be included in this url

<i>Metacharacters:</i>
\t#X\tMax X location
\t#Y\tMax Y location
\t#Z\tMap zoom (0 = min zoom, fully zoomed out)
\t#S\tInverse zoom (max-zoom - #Z)
\t#Q\tQuadtree encoded tile (qrts)
\t#W\tQuadtree encoded tile (1234)
\t#U\tEncoding not implemeted
\t#R\tRandom integer, 0-4""")
        lbl.props.xalign = 0
        lbl.props.use_markup = True
        lbl.props.wrap = True

        ex.add(vb)
        vb.pack_start(lbl, False)

        hb = gtk.HBox()
        hb.pack_start(gtk.Label("URI: "), False)
        hb.pack_start(self.repouri_entry, True)
        vb.pack_start(hb, False)

        hb = gtk.HBox()
        hb.pack_start(gtk.Label("Image Format: "), False)
        hb.pack_start(self.image_format_entry, True)
        vb.pack_start(hb, False)

        gobtn = gtk.Button("Load Map URI")
        gobtn.connect("clicked", self.load_map_clicked)
        vb.pack_start(gobtn, False)

        self.show_tooltips = False
        cb = gtk.CheckButton("Show Location in Tooltips")
        cb.props.active = self.show_tooltips
        cb.connect("toggled", self.on_show_tooltips_toggled)
        self.vbox.pack_end(cb, False)

        cb = gtk.CheckButton("Disable Cache")
        cb.props.active = False
        cb.connect("toggled", self.disable_cache_toggled)
        self.vbox.pack_end(cb, False)

        self.vbox.pack_end(ex, False)
        self.vbox.pack_end(self.latlon_entry, False)
        self.vbox.pack_end(hbox, False)

        gobject.timeout_add(500, self.print_tiles)

    def select_dir(self, widget):
        #md = gtk.MessageDialog(self,
        #    gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_INFO,
        #    gtk.BUTTONS_CLOSE, "Download completed")
        #md.run()
        #md.destroy()
        chooser = gtk.FileChooserDialog(title='Select folder',action=gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
            buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK))
        chooser.run()
        chooser.destroy()

    def disable_cache_toggled(self, btn):
        if btn.props.active:
            self.osm.props.tile_cache = osmgpsmap.CACHE_DISABLED
        else:
            self.osm.props.tile_cache = osmgpsmap.CACHE_AUTO

    def on_show_tooltips_toggled(self, btn):
        self.show_tooltips = btn.props.active

    def load_map_clicked(self, button):
        uri = self.repouri_entry.get_text()
        format = self.image_format_entry.get_text()
        if uri and format:
            if self.osm:
                #remove old map
                self.vbox.remove(self.osm)
            try:
                self.osm = osmgpsmap.GpsMap(
                    repo_uri=uri,
                    image_format=format
                )
            except Exception, e:
                print "ERROR:", e
                self.osm = osmgpsmap.GpsMap()

            self.vbox.pack_start(self.osm, True)
            self.osm.connect('button_release_event', self.map_clicked)
            self.osm.show()

    def print_tiles(self):
        if self.osm.props.tiles_queued != 0:
            print self.osm.props.tiles_queued, 'tiles queued'
        return True

    def zoom_in_clicked(self, button):
        self.osm.set_zoom(self.osm.props.zoom + 1)

    def zoom_out_clicked(self, button):
        self.osm.set_zoom(self.osm.props.zoom - 1)

    def home_clicked(self, button):
        self.osm.set_center_and_zoom(51.436035, 5.47840, 13)

    def on_query_tooltip(self, widget, x, y, keyboard_tip, tooltip, data=None):
        if keyboard_tip:
            return False

        if self.show_tooltips:
            p = osmgpsmap.point_new_degrees(0.0, 0.0)
            self.osm.convert_screen_to_geographic(x, y, p)
            lat,lon = p.get_degrees()
            tooltip.set_markup("%+.4f, %+.4f" % p.get_degrees())
            return True

        return False

    def cache_clicked(self, button):
        bbox = self.osm.get_bbox()
        self.osm.download_maps(
            *bbox,
            zoom_start=self.osm.props.zoom,
            zoom_end=self.osm.props.max_zoom
        )

    def map_clicked(self, osm, event):
        lat,lon = self.osm.get_event_location(event).get_degrees()
        if event.button == 1:
            self.latlon_entry.set_text(
                'Map Centre: latitude %s longitude %s' % (
                    self.osm.props.latitude,
                    self.osm.props.longitude
                )
            )
        elif event.button == 2:
            self.osm.gps_add(lat, lon, heading=osmgpsmap.INVALID);
        elif event.button == 3:
            self.osm.image_remove_all()
            pb = gtk.gdk.pixbuf_new_from_file_at_size ("poi.png", 24,24)
            self.osm.image_add(lat,lon,pb)
            self.latlon_entry.set_text(
                'Marker: latitude %s longitude %s' % (lat, lon)
            )

if __name__ == "__main__":
    u = UI()
    u.show_all()
    if os.name == "nt": gtk.gdk.threads_enter()
    gtk.main()
    if os.name == "nt": gtk.gdk.threads_leave()

