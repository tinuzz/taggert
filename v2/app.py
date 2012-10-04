#!/usr/bin/python
import os
import pyexiv2
from gi.repository import GtkClutter     # apt-get install gir1.2-clutter-1.0
from gi.repository import Clutter
from gi.repository import Gtk, GtkChamplain
from gi.repository import Champlain
from gi.repository import GdkPixbuf
#from gi.repository import GObject
from gi.repository import Gio, GLib
from pprint import pprint

#GObject.threads_init()
GtkClutter.init([])

START  = Clutter.BinAlignment.START
CENTER = Clutter.BinAlignment.CENTER
END    = Clutter.BinAlignment.END

class App(object):

    def __init__(self):
        self.marker_lat = 0
        self.marker_lon = 0
        self.imagedir   = '/home/martijn/Pictures/2012'
        self.filelist_locked = False
        self.home_location = (51.44823, 5.47262, 17)  # lat, lon, zoom
        self.clicked_lat = 0.0
        self.clicked_lon = 0.0
        self.marker_location = (0.0, 0.0)
        self.marker_size = 18
        self.map_id = 'osm-mapnik'
        self.bookmarks = {}
        self.last_clicked_bookmark = None

    def main(self):
        self.read_settings()
        self.setup_gui()
        self.init_map_sources()
        self.init_combobox1()
        self.init_treeview1()
        self.setup_map()
        self.setup_gui_signals()
        self.populate_store1()
        self.update_adjustment1()
        self.reload_bookmarks()
        self.window.set_title('Taggert')
        self.window.show_all()
        Gtk.main()

    def read_settings(self):
        self.settings = Gio.Settings.new('com.tinuzz.taggert')

        v = self.settings.get_value('bookmarks-names')
        for i in range(v.n_children()):
            val = v.get_child_value(i)
            key = val.get_child_value(0).get_string()
            value = val.get_child_value(1).get_string()
            self.bookmarks[key] = {}
            self.bookmarks[key]['name'] = value

        v = self.settings.get_value('bookmarks-latitudes')
        for i in range(v.n_children()):
            val = v.get_child_value(i)
            key = val.get_child_value(0).get_string()
            value = val.get_child_value(1).get_double()
            self.bookmarks[key]['latitude'] = value

        v = self.settings.get_value('bookmarks-longitudes')
        for i in range(v.n_children()):
            val = v.get_child_value(i)
            key = val.get_child_value(0).get_string()
            value = val.get_child_value(1).get_double()
            self.bookmarks[key]['longitude'] = value

    def setup_gui(self):
        self.builder = Gtk.Builder()
        self.builder.add_from_file("taggert.glade")
        self.window = self.builder.get_object("window1")
        self.window.set_default_size(1200, 768)
        self.window.set_position(Gtk.WindowPosition.CENTER)
        #chooser = self.builder.get_object ("filechooserdialog1")
        #chooser.add_button("OK", Gtk.ResponseType.OK)
        #chooser.add_button("Cancel", Gtk.ResponseType.CANCEL)
        self.statusbar = self.builder.get_object("statusbar1")

    def setup_gui_signals(self):

        handlers = {
            "window1_delete_event": self.quit,
            "imagemenuitem5_activate": self.quit, # File -> Quit
            "imagemenuitem2_activate": self.select_dir,
            "imagemenuitem1_activate": self.go_home,
            "combobox1_changed": self.combobox_changed,
            "checkmenuitem1_toggled": self.populate_store1,
            "treeview-selection2_changed": self.treeselect_changed,
            "menuitem6_activate": self.map_add_marker,
            "menuitem7_activate": self.center_map_here,
            "button2_clicked": self.go_to_marker,
            "image4_button_press_event": self.map_zoom_out,
            "image5_button_press_event": self.map_zoom_in,
            "eventbox1_button_press_event": self.map_zoom_out,
            "eventbox2_button_press_event": self.map_zoom_in,
            "adjustment1_value_changed": self.adjust_zoom,
            "button5_clicked": self.add_bookmark_dialog,
            "menuitem8_activate": self.delete_bookmark,
            "button1_clicked": self.tag_selected_from_marker
        }
        self.builder.connect_signals(handlers)

    def setup_map(self):
        widget = GtkChamplain.Embed()
        #widget.set_size_request(640, 480)

        box = self.builder.get_object("box2")
        box.pack_start(widget, True, True, 0)

        self.osm = widget.get_view()

        # A marker layer
        self.markerlayer = Champlain.MarkerLayer()
        self.osm.add_layer(self.markerlayer)

        # A map scale
        scale = Champlain.Scale()
        scale.connect_view(self.osm)
        self.osm.bin_layout_add(scale, START, END)

        # The label showing the coordinates at the top
        self.clabel = Clutter.Text()
        self.clabel.set_color(Clutter.Color.new(255, 255, 0, 255))

        # The box containing the label
        cbox = Clutter.Box()
        cbox.set_layout_manager(Clutter.BinLayout())
        cbox.set_color(Clutter.Color.new(0, 0, 0, 96))
        self.osm.bin_layout_add(cbox, START, START)
        cbox.get_layout_manager().add(self.clabel, CENTER, CENTER)
        self.osm.connect('notify::width', lambda *ignore: cbox.set_size(self.osm.get_width(), 30))

        widget.connect("realize", self.handle_map_event)
        widget.connect("button-release-event", self.handle_map_event)
        self.osm.connect("layer-relocated", self.handle_map_event)
        widget.connect("button-press-event", self.handle_map_mouseclick)
        self.osm.connect("notify::zoom", self.on_map_zoom_changed)

        self.go_home()

    def init_combobox1(self):
        combobox = self.builder.get_object("combobox1")
        renderer = Gtk.CellRendererText()
        combobox.pack_start(renderer, True)
        combobox.add_attribute(renderer, "text", 1)
        combobox.set_active(0)

    def init_treeview1(self):
        renderer = Gtk.CellRendererText()
        col0 = Gtk.TreeViewColumn("Filename", renderer, text=0)
        col1 = Gtk.TreeViewColumn("EXIF DateTime", renderer, text=1)
        col2 = Gtk.TreeViewColumn("Latitude", renderer, text=3)
        col3 = Gtk.TreeViewColumn("Longitude", renderer, text=4)

        col0.set_sort_column_id(0)
        col1.set_sort_column_id(1)
        col2.set_sort_column_id(3)
        col3.set_sort_column_id(4)

        tree = self.builder.get_object("treeview1")
        tree.append_column(col0)
        tree.append_column(col1)
        tree.append_column(col2)
        tree.append_column(col3)

        #treeselect = tree.get_selection()
        #self.sig1 = treeselect.connect('changed', self.treeselect_changed)

    def update_adjustment1(self):
        ms = self.map_sources[self.map_id]
        cur_zoom = self.osm.get_zoom_level()
        min_zoom = ms.get_min_zoom_level()
        max_zoom = ms.get_max_zoom_level()
        adj =  self.builder.get_object("adjustment1")
        adj.set_lower(min_zoom)
        adj.set_upper(max_zoom)
        adj.set_value(cur_zoom)

    def quit(self, _window, _event=None):
        print "Exit."
        Gtk.main_quit()

    def populate_store1(self, widget=None):

        menuitem = self.builder.get_object("checkmenuitem1")
        checked = menuitem.get_active()

        self.filelist_locked = True
        shown = 0
        notshown = 0

        try:
            #print "Going to scan %s" % self.imagedir
            store = self.builder.get_object("liststore1")
            store.clear()
            if self.imagedir:
                for fl in os.listdir(self.imagedir):
                    fname = os.path.join(self.imagedir, fl)
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
                            if not checked or imglat == '' or imglon == '':
                                store.append([fl, dt, rot, imglat, imglon])
                                shown += 1
                            else:
                                notshown += 1
        finally:
            self.filelist_locked = False

        msg = "%d images" % shown
        if notshown > 0:
            msg = "%s, %d already tagged images not shown" % (msg, notshown)
        self.statusbar.push(0, msg)

    def init_map_sources(self):
        self.map_sources = {}
        self.map_sources_names = {}

        self.mapstore = self.builder.get_object("liststore3")

        for map_desc in [
            ['osm-mapnik', 'OpenStreetMap Mapnik', 0, 18, 256,
            'Map data is CC-BY-SA 2.0 OpenStreetMap contributors',
            'http://creativecommons.org/licenses/by-sa/2.0/',
            'http://tile.openstreetmap.org/#Z#/#X#/#Y#.png'],

            ['osm-cyclemap', 'OpenStreetMap Cycle Map', 0, 18, 256,
            'Map data is CC-BY-SA 2.0 OpenStreetMap contributors',
            'http://creativecommons.org/licenses/by-sa/2.0/',
            'http://a.tile.opencyclemap.org/cycle/#Z#/#X#/#Y#.png'],

            ['osm-transport', 'OpenStreetMap Transport Map', 0, 18, 256,
            'Map data is CC-BY-SA 2.0 OpenStreetMap contributors',
            'http://creativecommons.org/licenses/by-sa/2.0/',
            'http://tile.xn--pnvkarte-m4a.de/tilegen/#Z#/#X#/#Y#.png'],

            ['mapquest-osm', 'MapQuest OSM', 0, 18, 256,
            'Map data provided by MapQuest, Open Street Map and contributors',
            'http://creativecommons.org/licenses/by-sa/2.0/',
            'http://otile1.mqcdn.com/tiles/1.0.0/osm/#Z#/#X#/#Y#.png'],

            ['mapquest-sat', 'MapQuest Open Aerial', 0, 11, 256,
            'Map data provided by MapQuest, Open Street Map and contributors',
            'http://creativecommons.org/licenses/by-sa/2.0/',
            'http://oatile1.mqcdn.com/tiles/1.0.0/sat/#Z#/#X#/#Y#.jpg'],

            ['mff-relief', 'Maps for Free Relief', 0, 11, 256,
            'Map data available under GNU Free Documentation license, v1.2 or later',
            'http://www.gnu.org/copyleft/fdl.html',
            'http://maps-for-free.com/layer/relief/z#Z#/row#Y#/#Z#_#X#-#Y#.jpg'],

            ['google-maps', 'Google Maps', 0, 19, 256,
            'Map data Copyright 2011 Google and 3rd party suppliers',
            'https://developers.google.com/maps/terms?hl=en',
            'http://mt1.google.com/vt/lyrs=m@110&hl=pl&x=#X#&y=#Y#&z=#Z#'],

            ['google-aerial', 'Google Aerial', 0, 22, 256,
            'Map data Copyright 2011 Google and 3rd party suppliers',
            'https://developers.google.com/maps/terms?hl=en',
            'http://mt1.google.com/vt/lyrs=s&hl=pl&x=#X#&y=#Y#&z=#Z#'],

            ['google-aerial-streets', 'Google Aerial with streets', 0, 22, 256,
            'Map data Copyright 2011 Google and 3rd party suppliers',
            'https://developers.google.com/maps/terms?hl=en',
            'http://mt1.google.com/vt/lyrs=y&hl=pl&x=#X#&y=#Y#&z=#Z#'],

            ['google-terrain', 'Google Terrain', 0, 15, 256,
            'Map data Copyright 2011 Google and 3rd party suppliers',
            'https://developers.google.com/maps/terms?hl=en',
            'http://mt1.google.com/vt/lyrs=t&hl=pl&x=#X#&y=#Y#&z=#Z#'],

            ['google-terrain-streets', 'Google Terrain with streets', 0, 15, 256,
            'Map data Copyright 2011 Google and 3rd party suppliers',
            'https://developers.google.com/maps/terms?hl=en',
            'http://mt1.google.com/vt/lyrs=p&hl=pl&x=#X#&y=#Y#&z=#Z#'],
            ]:
            mapid, name, min_zoom, max_zoom, size, lic, lic_uri, tile_uri = map_desc

            c = Champlain.MapSourceChain()
            c.push(Champlain.MapSourceFactory.dup_default().create_error_source(size))

            c.push(Champlain.NetworkTileSource.new_full(
                mapid, name, lic, lic_uri, min_zoom, max_zoom,
                size, Champlain.MapProjection.MAP_PROJECTION_MERCATOR,
                tile_uri, Champlain.ImageRenderer()))

            c.push(Champlain.FileCache.new_full(1e8, None, Champlain.ImageRenderer()))
            c.push(Champlain.MemoryCache.new_full(100,     Champlain.ImageRenderer()))
            self.map_sources[mapid] = c
            self.map_sources_names[mapid] = name
            self.mapstore.append([mapid, name])

    def combobox_changed(self, combobox):
        model = combobox.get_model()
        active = combobox.get_active_iter()
        if active != None:
            self.map_id = model[active][0]
            self.osm.set_map_source(self.map_sources[self.map_id])
            self.update_adjustment1()

#    def treeview_size_allocate(self, widget, allocation):
#        pprint(allocation.width)
#        paned = self.builder.get_object("paned1")
#        #paned.set_attribute ("position", allocation.width)
#        paned.position = allocation.width

    def treeselect_changed (self, treeselect):
        #pprint(self.osm.get_center_latitude())
        if self.filelist_locked:
            return
        if treeselect:
            model,pathlist = treeselect.get_selected_rows()
            if pathlist:
                # Get the first selected picture
                p = pathlist[0]
                tree_iter = model.get_iter(p)
                value = model.get_value(tree_iter,0)
                orientation = model.get_value(tree_iter,2)
                filename = os.path.join(self.imagedir, value)

                pb = GdkPixbuf.Pixbuf.new_from_file_at_size(filename, 300, 200)
                if orientation == '6':
                    pb = pb.rotate_simple(GdkPixbuf.PixbufRotation.CLOCKWISE)
                elif orientation == '8':
                    pb = pb.rotate_simple(GdkPixbuf.PixbufRotation.COUNTERCLOCKWISE)

                # If, after rotating, the image is bigger than 300x200, resize it
                w = pb.get_width()
                h = pb.get_height()
                fw = float(w)
                fh = float(h)
                nw = fw
                nh = fh
                if w > 300:
                    nw = 300
                    nh = int((nw / fw) * h)
                if nh > 200:
                    nh = 200
                    nw = int((nh / fh) * w)
                if nh != h or nw != w:
                    pb = pb.scale_simple(nw, nh, 2)

                preview = self.builder.get_object("image1")
                #preview.set_from_pixbuf(pb)
                preview.set_from_pixbuf(pb)

    def select_dir(self, widget):
        #chooser = gtk.FileChooserDialog(title='Select folder',action=gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
        #    buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK))
        #chooser = Gtk.FileChooserDialog("Select image folder", None, )

        print "Choose dir"
        chooser = self.builder.get_object ("filechooserdialog1")

        # If the current dir is local (i.e. it starts with a '/'),
        # make the filechooser start there
        if self.imagedir[0] == '/':
            chooser.set_current_folder_uri('file://%s' % self.imagedir)

        response = chooser.run()
        chooser.hide()
        if response == Gtk.ResponseType.OK:   # http://developer.gnome.org/gtk3/3.4/GtkDialog.html#GtkResponseType
            #print "Dir chosen: %s" % self.imagedir
            self.imagedir = chooser.get_filename()
            self.populate_store1 ()

    def go_to_location(self, lat, lon, zoom=None):
        self.osm.center_on(lat, lon)
        if zoom:
            self.osm.set_zoom_level(zoom)

    def go_home(self, _widget=None):
        self.add_marker_at(*self.home_location)
        self.go_to_location(*self.home_location)

    def go_to_marker(self, _widget=None):
        try:
            m = self.markerlayer.get_markers()[0]
            lat, lon = (m.get_latitude(), m.get_longitude())
            self.osm.center_on(lat, lon)
        except IndexError:
            pass

    def latlon_to_text(self,lat,lon):
        return "%s %.5f, %s %.5f" % (
                'N' if lat >= 0 else 'S', abs(lat),
                'E' if lon >= 0 else 'W', abs(lon)
            )

    def handle_map_event(self, _widget, _ignore=None):
        lat = self.osm.get_center_latitude()
        lon = self.osm.get_center_longitude()
        text = self.latlon_to_text(lat,lon)
        self.clabel.set_text (text)
        self.update_adjustment1()

    def handle_map_mouseclick(self, _widget, event):
        if event.button == 3:
            menu = self.builder.get_object("menu6")
            menu.popup(None, None, None, None, event.button, event.time)
            self.clicked_lat, self.clicked_lon = self.osm.y_to_latitude(event.y), self.osm.x_to_longitude(event.x)
            #self.statusbar.push(0, "LAT: %s, LON: %s" % (lat,lon))

    def add_marker_at(self, lat, lon, zoom=None):
        self.markerlayer.remove_all()
        point = Champlain.Point()
        point.set_location(lat, lon)
        point.set_color(Clutter.Color.new(255, 0, 0, 255))
        point.set_size(self.marker_size)
        point.set_draggable(True)
        self.markerlayer.add_marker(point)

    def map_add_marker(self, _widget):
        self.add_marker_at(self.clicked_lat, self.clicked_lon)

    def center_map_here(self, _widget):
        self.osm.center_on(self.clicked_lat, self.clicked_lon)

    def map_zoom_in(self, widget=None, event=None):
        self.osm.zoom_in()
        self.update_adjustment1()

    def map_zoom_out(self, widget=None, event=None):
        self.osm.zoom_out()
        self.update_adjustment1()

    def adjust_zoom(self, adj, _map=None):
        zoom = adj.get_value()
        cur_zoom = self.osm.get_zoom_level()
        if zoom != cur_zoom:
            self.osm.set_zoom_level(zoom)
            self.update_adjustment1()

    def on_map_zoom_changed(self):
        print (self.osm.get_zoom_level())
        self.update_adjustment1()

    def add_bookmark_dialog(self, widget):
        try:
            m = self.markerlayer.get_markers()[0]
            lat, lon = (m.get_latitude(), m.get_longitude())
            self.go_to_marker()
        except IndexError:
            lat = self.osm.get_center_latitude()
            lon = self.osm.get_center_longitude()

        self.builder.get_object("entry1").set_text(self.latlon_to_text(lat,lon))
        self.builder.get_object("entry2").set_text("%.5f" % lat)
        self.builder.get_object("entry3").set_text("%.5f" % lon)
        dialog = self.builder.get_object("dialog1")
        response = dialog.run()
        dialog.hide()
        if response == Gtk.ResponseType.OK:
            bm_id = "bookmark%d" % (len(self.bookmarks) + 1)
            bookmark = {
                 "name":      self.builder.get_object("entry1").get_text(),
                 "latitude":  float(self.builder.get_object("entry2").get_text()),
                 "longitude": float(self.builder.get_object("entry3").get_text())
            }
            self.bookmarks[bm_id] = bookmark

        self.reload_bookmarks()
        self.save_bookmarks()

    def reload_bookmarks(self):
        # First remove all bookmarks, i.e. all MenuItems after the first separator
        menu = self.builder.get_object("menu5")
        sep_found = False
        for entry in menu.get_children():
            if type(entry) == Gtk.SeparatorMenuItem:
                sep_found = True
                continue
            if not sep_found:
                continue
            entry.destroy()

        # Now add bookmarks as menuitems
        for bm_id, bm in self.bookmarks.items():
            item = Gtk.MenuItem()
            item.set_label(bm['name'])
            item.set_name(bm_id)
            item.connect("button-press-event", self.handle_bookmark_click)
            #item.connect("activate", self.go_to_bookmark)
            menu.append(item)
            item.show()

    def save_bookmarks(self):
        names = {}
        latitudes = {}
        longitudes = {}
        for key,bm in self.bookmarks.items():
            names[key] = bm['name']
            latitudes[key] = bm['latitude']
            longitudes[key] = bm['longitude']
        v1 = GLib.Variant('a{ss}', names)
        v2 = GLib.Variant('a{sd}', latitudes)
        v3 = GLib.Variant('a{sd}', longitudes)
        self.settings.set_value("bookmarks-names", v1)
        self.settings.set_value("bookmarks-latitudes", v2)
        self.settings.set_value("bookmarks-longitudes", v3)

    def go_to_bookmark(self, widget):
        bm_id = widget.get_name()
        self.add_marker_at(self.bookmarks[bm_id]['latitude'], self.bookmarks[bm_id]['longitude'])
        self.go_to_marker()

    def handle_bookmark_click(self, widget, event):
        if event.button == 3: # right click
            self.last_clicked_bookmark = widget
            popup = self.builder.get_object("menu7")
            popup.popup(None, widget, None, None, event.button, event.time)
            return True
        else:
            self.go_to_bookmark(widget)

    def delete_bookmark(self, widget):
        bm_id = self.last_clicked_bookmark.get_name()
        self.last_clicked_bookmark.destroy()
        del self.bookmarks[bm_id]
        self.save_bookmarks()

    def tag_selected_from_marker(self, widget):
        treeselect = self.builder.get_object("treeview1").get_selection()
        model,pathlist = treeselect.get_selected_rows()
        if pathlist:
            try:
                m = self.markerlayer.get_markers()[0]
                lat, lon = (m.get_latitude(), m.get_longitude())
                for p in pathlist:
                    tree_iter = model.get_iter(p)
                    model[tree_iter][3] = str(lat)
                    model[tree_iter][4] = str(lon)
            except IndexError:
                pass
