#!/usr/bin/python
#
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

import os
import pyexiv2
import fractions
import time
import pytz
from math import modf
from gi.repository import GtkClutter     # apt-get install gir1.2-clutter-1.0
from gi.repository import Clutter
from gi.repository import Gtk, GtkChamplain
from gi.repository import Champlain
from gi.repository import GdkPixbuf
from gi.repository import Gio, GLib
from gi.repository import Gdk
from pprint import pprint
import xml.dom.minidom as minidom
from iso8601 import parse_date as parse_xml_date
from gpxfile import GPXfile
from polygon import Polygon

#GObject.threads_init()
GtkClutter.init([])

VERSION = 1.0

START  = Clutter.BinAlignment.START
CENTER = Clutter.BinAlignment.CENTER
END    = Clutter.BinAlignment.END

class App(object):

    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.imagedir   = ''
        self.filelist_locked = False
        self.home_location = (51.50063, -0.12456, 12)  # lat, lon, zoom
        self.clicked_lat = 0.0
        self.clicked_lon = 0.0
        self.marker_size = 18
        self.map_id = 'osm-mapnik'
        self.bookmarks = {}
        self.last_clicked_bookmark = None
        self.modified = {}
        self.show_untagged_only = False
        self.show_map_coords = True
        self.show_tracks = True
        self.gpx = GPXfile()
        self.last_track_folder = None
        self.track_highlight_color = Gdk.Color(0,0,65535)
        self.track_default_color = Gdk.Color(65535,0,0)
        self.marker_color = Gdk.Color(0,65535,0)
        self.last_highlighted_track = None
        self.highlighted_tracks = []
        self.track_timezone = 'Europe/Amsterdam'
        self.always_this_timezone = False

    def main(self):
        self.read_settings()
        self.setup_gui()
        self.init_map_sources()
        self.init_treeview1()
        self.setup_map()
        self.init_combobox1()
        idx = self.init_timezonepre()
        self.init_combobox2and3(idx)
        self.setup_gui_signals()
        self.populate_store1()
        self.update_adjustment1()
        self.reload_bookmarks()
        self.window.set_title('Taggert')
        self.window.show_all()
        self.init_treeview2()
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

        self.map_id = self.settings.get_value('map-source-id').get_string()

        homeloc = self.settings.get_value('home-location')
        self.home_location = (
            homeloc.get_child_value(0).get_double(),
            homeloc.get_child_value(1).get_double(),
            homeloc.get_child_value(2).get_int32(),
        )

        self.show_map_coords = self.settings.get_value('show-map-coords').get_boolean()
        self.show_untagged_only = self.settings.get_value('show-untagged-only').get_boolean()
        self.imagedir = self.settings.get_value('last-image-dir').get_string()
        self.last_track_folder = self.settings.get_value('last-track-folder').get_string()
        self.track_timezone = self.settings.get_value('track-timezone').get_string()
        self.always_this_timezone = self.settings.get_value('always-this-timezone').get_boolean()

        # Colors
        self.marker_color = self.get_color_from_settings('marker-color')
        self.track_default_color = self.get_color_from_settings('normal-track-color')
        self.track_highlight_color = self.get_color_from_settings('selected-track-color')

    def get_color_from_settings(self, key):
        color = self.settings.get_value(key)
        return Gdk.Color(
            color.get_child_value(0).get_int32(),
            color.get_child_value(1).get_int32(),
            color.get_child_value(2).get_int32()
        )

    def clutter_color (self, gdkcolor):
        return Clutter.Color.new(
            *[x / 256 for x in [gdkcolor.red, gdkcolor.green, gdkcolor.blue, 65535]])

    def color_tuple (self, gdkcolor):
        return (gdkcolor.red, gdkcolor.green, gdkcolor.blue)

    def setup_gui(self):
        self.builder = Gtk.Builder()
        self.builder.add_from_file(os.path.join(self.data_dir, "taggert.glade"))
        self.window = self.builder.get_object("window1")

        # Restore window size
        s = self.settings.get_value('window-size')
        self.window.set_default_size(s.get_child_value(0).get_int32(), s.get_child_value(1).get_int32())

        self.builder.get_object("checkmenuitem1").set_active(self.show_untagged_only)
        self.builder.get_object("checkmenuitem9").set_active(self.show_map_coords)
        self.builder.get_object("checkmenuitem2").set_active(self.show_tracks)
        self.builder.get_object("checkbutton1").set_active(self.always_this_timezone)
        self.window.set_position(Gtk.WindowPosition.CENTER)
        self.statusbar = self.builder.get_object("statusbar1")
        self.builder.get_object("colorbutton1").set_color(self.marker_color)
        self.builder.get_object("colorbutton2").set_color(self.track_default_color)
        self.builder.get_object("colorbutton3").set_color(self.track_highlight_color)
        self.builder.get_object("aboutdialog1").set_version('v' + str(VERSION))

    def setup_gui_signals(self):

        handlers = {
            "window1_delete_event": self.quit,
            "imagemenuitem1_activate": self.go_home,
            "imagemenuitem2_activate": self.select_dir,
            "imagemenuitem3_activate": self.save_all,
            "imagemenuitem4_activate": self.open_gpx,
            "imagemenuitem5_activate": self.quit, # File -> Quit
            "imagemenuitem9_activate": self.delete_tag_from_selected, # File -> Quit
            "imagemenuitem10_activate": self.about_box,
            "menuitem6_activate": self.map_add_marker,
            "menuitem7_activate": self.center_map_here,
            "menuitem8_activate": self.delete_bookmark,
            "menuitem9_activate": self.view_selected_track,
            "menuitem10_activate": self.remove_selected_track,
            "menuitem11_activate": self.treeview2_select_all,
            "menuitem12_activate": self.treeview2_select_none,
            "menuitem22_activate": self.set_timezone_dialog,
            "menuitem15_activate": self.images_select_all_from_camera,
            "menuitem16_activate": self.images_select_all,
            "menuitem17_activate": self.images_select_none,
            "menuitem18_activate": self.tag_selected_from_marker,
            "menuitem19_activate": self.tag_selected_from_track,
            "menuitem21_activate": self.go_to_image,
            "menuitem22_activate": self.set_timezone_dialog,
            "menuitem23_activate": self.settings_dialog,
            "menuitem25_activate": self.treeview_x_select_all,
            "combobox1_changed": self.combobox_changed,
            "combobox2_changed": self.combobox2_changed,
            "checkmenuitem1_toggled": self.populate_store1,
            "checkmenuitem2_toggled": self.toggle_tracks,
            "checkmenuitem9_toggled": self.toggle_overlay,
            "treeview-selection1_changed": self.treeselect_changed,
            "treeview-selection2_changed": self.treeselect2_changed,
            "treeview1_button_press_event": self.handle_treeview1_click,
            "treeview2_button_press_event": self.handle_treeview2_click,
            "image4_button_press_event": self.map_zoom_out,
            "image5_button_press_event": self.map_zoom_in,
            "eventbox1_button_press_event": self.map_zoom_out,
            "eventbox2_button_press_event": self.map_zoom_in,
            "adjustment1_value_changed": self.adjust_zoom,
            "button1_clicked": self.tag_selected_from_marker,
            "button2_clicked": self.go_to_marker,
            "button3_clicked": self.tag_selected_from_track,
            "button4_clicked": self.go_to_image,
            "button5_clicked": self.add_bookmark_dialog,
            "button6_clicked": self.save_all,
            "button14_clicked": self.hide_infobar,
            "button15_clicked": self.set_home_location
        }
        self.builder.connect_signals(handlers)

    def setup_map(self):
        widget = GtkChamplain.Embed()
        #widget.set_size_request(640, 480)

        box = self.builder.get_object("box2")
        box.pack_start(widget, True, True, 0)

        self.osm = widget.get_view()

        # Set the map source
        self.osm.set_map_source(self.map_sources[self.map_id])
        self.update_adjustment1()

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
        self.cbox = Clutter.Box()
        self.cbox.set_layout_manager(Clutter.BinLayout())
        self.cbox.set_color(Clutter.Color.new(0, 0, 0, 96))
        self.osm.bin_layout_add(self.cbox, START, START)
        self.cbox.get_layout_manager().add(self.clabel, CENTER, CENTER)
        self.osm.connect('notify::width', lambda *ignore: self.cbox.set_size(self.osm.get_width(), 30))
        if not self.show_map_coords:
            self.cbox.hide()

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

        self.combobox1_set_map_id(self.map_id)
        #combobox.set_active(0)

    def init_treeview1(self):
        self.builder.get_object("liststore1").set_sort_column_id(0,  Gtk.SortType.ASCENDING)
        renderer = Gtk.CellRendererText()
        renderer.set_property('cell-background', 'yellow')
        col0 = Gtk.TreeViewColumn("Filename", renderer, text=0, cell_background_set=5)
        col1 = Gtk.TreeViewColumn("EXIF DateTime", renderer, text=1, cell_background_set=5)
        col2 = Gtk.TreeViewColumn("Latitude", renderer, text=3, cell_background_set=5)
        col3 = Gtk.TreeViewColumn("Longitude", renderer, text=4, cell_background_set=5)

        col0.set_sort_column_id(0)
        col1.set_sort_column_id(1)
        col2.set_sort_column_id(3)
        col3.set_sort_column_id(4)

        tree = self.builder.get_object("treeview1")
        tree.append_column(col0)
        tree.append_column(col1)
        tree.append_column(col2)
        tree.append_column(col3)

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
        if self.save_modified_dialog():
            self.save_settings()
            Gtk.main_quit()
        else:
            return False

    def populate_store1(self, widget=None):

        self.show_untagged_only = self.builder.get_object("checkmenuitem1").get_active()
        self.settings.set_value("show-untagged-only", GLib.Variant('b', self.show_untagged_only))
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
                            data = None
                            modf = False
                            metadata = pyexiv2.ImageMetadata(fname)
                            metadata.read()
                            # Get the camera make/model
                            try:
                                make = metadata['Exif.Image.Make'].value
                                model = metadata['Exif.Image.Model'].value
                                # Remove the 'make' from the 'model' if present
                                camera = "%s %s" % (make, model.replace(make, '',1).strip())
                            except KeyError:
                                camera = ''
                            # Get EXIF DateTime
                            try:
                                dtobj = metadata['Exif.Image.DateTime'].value
                                #dt = metadata['Exif.Image.DateTime'].raw_value
                                dt = dtobj.strftime("%Y-%m-%d %H:%M:%S")
                            except KeyError:
                                dtobj = None
                                dt = ''
                            # Get image orientation
                            try:
                                rot =  metadata['Exif.Image.Orientation'].raw_value
                            except KeyError:
                                rot = '1'
                            # Get GPS info
                            try:
                                data =  self.modified[fl]
                                imglat = data['latitude']
                                modf = True
                            except KeyError:
                                try:
                                    args1 = metadata['Exif.GPSInfo.GPSLatitude'].value
                                    args2 = metadata['Exif.GPSInfo.GPSLatitudeRef'].value
                                    args3 = args1 + [args2]
                                    imglat = self.dms_to_decimal(*args3)
                                except KeyError:
                                    imglat = ''
                            try:
                                data =  self.modified[fl]
                                imglon = data['longitude']
                            except KeyError:
                                try:
                                    args1 = metadata['Exif.GPSInfo.GPSLongitude'].value
                                    args2 = metadata['Exif.GPSInfo.GPSLongitudeRef'].value
                                    args3 = args1 + [args2]
                                    imglon = self.dms_to_decimal(*args3)
                                except KeyError:
                                    imglon = ''
                            if not self.show_untagged_only or imglat == '' or imglon == '' or data:
                                store.append([fl, dt, rot, str(imglat), str(imglon), modf, camera, dtobj])
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
            self.settings.set_value("map-source-id", GLib.Variant('s', self.map_id))
            self.osm.set_map_source(self.map_sources[self.map_id])
            self.update_adjustment1()

    def treeselect_changed (self, treeselect):
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


    def save_modified_dialog(self):
        if self.modified:
            dialog = self.builder.get_object('messagedialog1')
            result = dialog.run()
            dialog.hide()
            if result == Gtk.ResponseType.CANCEL:
                return False
            elif result == Gtk.ResponseType.YES:  # Save all
                self.save_all()
        return True

    def select_dir(self, widget):
        if self.save_modified_dialog():
            chooser = self.builder.get_object ("filechooserdialog1")
            chooser.set_title("Select image folder")
            chooser.set_action(Gtk.FileChooserAction.SELECT_FOLDER)

            if self.imagedir and os.path.isdir(self.imagedir):
                chooser.set_current_folder_uri('file://%s' % self.imagedir)

            response = chooser.run()
            chooser.hide()
            if response == Gtk.ResponseType.OK:   # http://developer.gnome.org/gtk3/3.4/GtkDialog.html#GtkResponseType
                self.imagedir = chooser.get_filename()
                self.settings.set_value("last-image-dir", GLib.Variant('s', self.imagedir))
                self.modified = {}
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

    def add_marker_at(self, lat, lon, zoom=None):
        self.markerlayer.remove_all()
        point = Champlain.Point()
        point.set_location(lat, lon)
        point.set_color(self.clutter_color(self.marker_color))
        point.set_size(self.marker_size)
        point.set_draggable(True)
        self.markerlayer.add_marker(point)

    def map_add_marker(self, _widget):
        self.add_marker_at(self.clicked_lat, self.clicked_lon)

    def center_map_here(self, _widget):
        self.osm.center_on(self.clicked_lat, self.clicked_lon)
        #self.osm.go_to(self.clicked_lat, self.clicked_lon)

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

    def go_to_image(self, widget):
        treeselect = self.builder.get_object("treeview1").get_selection()
        model,pathlist = treeselect.get_selected_rows()
        if pathlist:
            # Get the first selected picture
            p = pathlist[0]
            tree_iter = model.get_iter(p)
            lat = model.get_value(tree_iter,3)
            lon = model.get_value(tree_iter,4)
            if lat and lon:
                self.add_marker_at(float(lat),float(lon))
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
                i=0
                m = self.markerlayer.get_markers()[0]
                lat, lon = (m.get_latitude(), m.get_longitude())
                for p in pathlist:
                    tree_iter = model.get_iter(p)
                    filename = model[tree_iter][0]
                    model[tree_iter][3] = "%.5f" % lat
                    model[tree_iter][4] = "%.5f" % lon
                    model[tree_iter][5] = True
                    self.modified[filename] = {'latitude': lat, 'longitude': lon}
                    i += 1
                self.show_infobar ("Tagged %d image%s" % (i, '' if i == 1 else 's'))
            except IndexError:
                pass

    def tag_selected_from_track(self, widget):
        # Any tracks available?
        if not len(self.gpx.gpxfiles):
            self.show_infobar ("No tracks loaded, cannot tag images")
            return
        treeselect = self.builder.get_object("treeview1").get_selection()
        model,pathlist = treeselect.get_selected_rows()
        if pathlist:
            try:
                i=0
                for p in pathlist:
                    tree_iter = model.get_iter(p)
                    filename = model[tree_iter][0]
                    dt = model[tree_iter][7]
                    if dt:
                        lat, lon, ele = self.gpx.find_coordinates(dt)
                        if lat and lon:
                            #print "%s %.5f %.5f" % (filename, lat, lon)
                            # Modify the coordinates
                            model[tree_iter][3] = "%.5f" % lat
                            model[tree_iter][4] = "%.5f" % lon
                            model[tree_iter][5] = True
                            self.modified[filename] = {'latitude': lat, 'longitude': lon}
                            i += 1
                self.show_infobar ("Tagged %d image%s" % (i, '' if i == 1 else 's'))
            except IndexError:
                pass

    def delete_tag_from_selected(self, widget):
        # Don't do this out of sight
        if self.builder.get_object('notebook1').get_current_page() != 0:
            return
        treeselect = self.builder.get_object("treeview1").get_selection()
        model,pathlist = treeselect.get_selected_rows()
        i=0
        if pathlist:
            for p in pathlist:
                tree_iter = model.get_iter(p)
                lat = model.get_value(tree_iter,3)
                lon = model.get_value(tree_iter,4)
                if lat or lon:
                    filename = model[tree_iter][0]
                    model[tree_iter][3] = ''
                    model[tree_iter][4] = ''
                    model[tree_iter][5] = True
                    self.modified[filename] = {'latitude': '', 'longitude': ''}
                    i += 1
        self.show_infobar ("Deleted tags from %d image%s" % (i, '' if i == 1 else 's'))

    def dms_to_decimal(self, degrees, minutes, seconds, sign=' '):
        return (-1 if sign[0] in 'SWsw' else 1) * (
            float(degrees)        +
            float(minutes) / 60   +
            float(seconds) / 3600
        )

    def decimal_to_dms(self, decimal):
        remainder, degrees = modf(abs(decimal))
        remainder, minutes = modf(remainder * 60)
        return [fractions.Fraction.from_float(n).limit_denominator(99999) for n in (degrees, minutes, remainder * 60)]

    def save_all(self, widget=None):
        model = self.builder.get_object('treeview1').get_model()
        self.savecounter = 0
        model.foreach(self.treestore_save_modified, None)

        # If we only want to see untagged images, repopulate the treeview
        if self.show_untagged_only:
            self.populate_store1()
        self.show_infobar("%d image%s saved" % (self.savecounter, '' if self.savecounter == 1 else 's'))

    def treestore_save_modified(self, model, path, tree_iter, userdata):
        fl = model.get_value(tree_iter,0)
        if model.get_value(tree_iter,5): # "modified"
            fname = os.path.join(self.imagedir, fl)
            metadata = pyexiv2.ImageMetadata(fname)
            metadata.read()
            try:
                lat = float(model.get_value(tree_iter,3))
                lon = float(model.get_value(tree_iter,4))
                metadata['Exif.GPSInfo.GPSLatitude'] = self.decimal_to_dms(lat)
                metadata['Exif.GPSInfo.GPSLongitude'] = self.decimal_to_dms(lon)
                metadata['Exif.GPSInfo.GPSLatitudeRef'] = 'N' if lat >= 0 else 'S'
                metadata['Exif.GPSInfo.GPSLongitudeRef'] = 'E' if lon >= 0 else 'W'
                metadata['Exif.GPSInfo.GPSMapDatum'] = 'WGS-84'
            # If the tag is empty, the conversion to float will fail with a ValueError
            except ValueError:
                try:
                    del metadata['Exif.GPSInfo.GPSLatitude']
                    del metadata['Exif.GPSInfo.GPSLongitude']
                    del metadata['Exif.GPSInfo.GPSLatitudeRef']
                    del metadata['Exif.GPSInfo.GPSLongitudeRef']
                    del metadata['Exif.GPSInfo.GPSMapDatum']
                except KeyError:
                    pass
            metadata.write()
            model[tree_iter][5] = False  # saved => not modified
            del self.modified[fl]
            self.savecounter += 1

    def show_infobar(self, text, timeout=5):
        self.builder.get_object("label9").set_text(text)
        self.builder.get_object("infobar1").show()
        GLib.timeout_add_seconds(timeout, self.hide_infobar)

    def hide_infobar(self, widget=None):
        self.builder.get_object("infobar1").hide()
        # return False to cancel the timer
        return False

    def save_settings(self):
        value = self.builder.get_object("window1").get_size()
        self.settings.set_value('window-size', GLib.Variant('(ii)', value))

    def combobox1_set_map_id(self, string):
        model = self.builder.get_object("liststore3")
        model.foreach(self.find_and_set_map_id, self.map_id)

    def find_and_set_map_id(self, model, path, tree_iter, string):
        map_id = model.get_value(tree_iter,0)
        if map_id == string:
            self.builder.get_object("combobox1").set_active_iter(tree_iter)
            return True
        return False

    def set_home_location(self, widget=None):
            try:
                m = self.markerlayer.get_markers()[0]
                lat, lon = (m.get_latitude(), m.get_longitude())
                zoom = self.osm.get_zoom_level()
                self.home_location = (lat, lon, zoom)
                self.settings.set_value("home-location", GLib.Variant('(ddi)', (lat, lon, zoom)))
                self.show_infobar ("Set home location to %.5f, %.5f at zoomlevel %d" % (lat, lon, zoom))
            except IndexError:
                pass

    def toggle_overlay(self, widget=None):
        checked = self.builder.get_object("checkmenuitem9").get_active()
        self.show_map_coords = checked
        self.settings.set_value("show-map-coords", GLib.Variant('b', checked))
        #box = self.osm.get_children()[0]
        if checked:
            self.cbox.show()
        else:
            self.cbox.hide()

    def process_gpx(self, filename, tz):
        store = self.builder.get_object("liststore2")
        idx = self.gpx.import_gpx(filename, tz)
        i = 0
        for trk in self.gpx.gpxfiles[idx]['tracks']:
            # Create a tracklayer for each track
            tracklayer = Polygon()
            tracklayer.set_stroke_color(self.clutter_color(self.track_default_color))
            t0 = trk["segments"][0]["points"][0]["time"]
            tx = trk["segments"][-1]["points"][-1]["time"]
            p = 0
            for segment in trk["segments"]:
                for point in segment["points"]:
                    p += 1
                    tracklayer.append_point(point["lat"], point["lon"])
            store.append([
                trk['name'],
                t0.strftime("%Y-%m-%d %H:%M:%S"),
                tx.strftime("%Y-%m-%d %H:%M:%S"),
                p, trk["uuid"], tracklayer
            ])
            self.osm.add_layer(tracklayer)
            if not self.show_tracks:
                tracklayer.hide()
            i += 1

        self.markerlayer.raise_top()
        # Store the directory of the file for next time
        self.last_track_folder = os.path.dirname(filename)
        self.settings.set_value("last-track-folder", GLib.Variant('s', self.last_track_folder))
        return i

    def init_treeview2(self):
        self.builder.get_object("liststore2").set_sort_column_id(1,  Gtk.SortType.ASCENDING)
        renderer = Gtk.CellRendererText()
        #renderer.set_property('cell-background', 'yellow')
        col0 = Gtk.TreeViewColumn("Name", renderer, text=0)
        col1 = Gtk.TreeViewColumn("Start time", renderer, text=1)
        col2 = Gtk.TreeViewColumn("End time", renderer, text=2)
        col3 = Gtk.TreeViewColumn("Points", renderer, text=3)

        col0.set_sort_column_id(0)
        col1.set_sort_column_id(1)
        col2.set_sort_column_id(2)
        col3.set_sort_column_id(3)

        tree = self.builder.get_object("treeview2")
        tree.append_column(col0)
        tree.append_column(col1)
        tree.append_column(col2)
        tree.append_column(col3)

    def open_gpx(self, widget=None):
            filefilter = Gtk.FileFilter()
            filefilter.set_name("GPX files")
            filefilter.add_pattern('*.gpx')
            filefilter.add_pattern('*.GPX')
            chooser = self.builder.get_object ("filechooserdialog1")
            chooser.set_title("Open GPX file")
            chooser.set_select_multiple(True)
            chooser.set_action(Gtk.FileChooserAction.OPEN)
            chooser.add_filter(filefilter)
            if self.last_track_folder and os.path.isdir(self.last_track_folder):
                chooser.set_current_folder_uri('file://%s' % self.last_track_folder)
            response = chooser.run()
            chooser.hide()
            chooser.remove_filter(filefilter)
            if response == Gtk.ResponseType.OK:   # http://developer.gnome.org/gtk3/3.4/GtkDialog.html#GtkResponseType
                filenames = chooser.get_filenames()
                if not self.always_this_timezone:
                    self.set_timezone_dialog()
                i = 0
                for filename in filenames:
                    # self.process_gpx returns the number of tracks
                    i += self.process_gpx(filename, self.track_timezone)
                if (len(filenames) == 1):
                    msg = os.path.basename(filename)
                else:
                    msg = "%d files" % len(filenames)
                self.show_infobar ("%d %stracks added from '%s'" % (i, 'hidden ' if not self.show_tracks else '', msg))
            chooser.set_select_multiple(False)

    def set_timezone_dialog(self, widget=None):
        dialog = self.builder.get_object ("dialog2")
        resp2 = dialog.run()
        dialog.hide()
        self.track_timezone, self.always_this_timezone = self.get_timezonedialog_result()
        self.settings.set_value("track-timezone", GLib.Variant('s', self.track_timezone))
        self.settings.set_value("always-this-timezone", GLib.Variant('b', self.always_this_timezone))

    def toggle_tracks(self, widget=None):
        checked = self.builder.get_object("checkmenuitem2").get_active()
        self.show_tracks = checked
        model = self.builder.get_object("liststore2")
        model.foreach(self.show_tracklayer, checked)

    def show_tracklayer(self, model, path, tree_iter, show):
        # The tracklayer object is in the 5th column
        tracklayer = model.get_value(tree_iter,5)
        if show:
            tracklayer.show()
        else:
            tracklayer.hide()

    def handle_treeview1_click(self, widget, event):
        if event.button == 3: # right click
            popup = self.builder.get_object("menu9")
            popup.popup(None, widget, None, None, event.button, event.time)
            return True

    def handle_treeview2_click(self, widget, event):
        if event.button == 3: # right click
            #treeview = self.builder.get_object("treeview2")
            #selection = treeview.get_selection()
            # If no path is found at the cursor position, get_path_at_pos returns None
            #try:
            #    path,column,cx,cy = treeview.get_path_at_pos(event.x, event.y)
            #except TypeError: # NoneType
            #    return True
            #if path:
            #    selection.unselect_all()
            #    selection.select_path(path)
            popup = self.builder.get_object("menu8")
            popup.popup(None, widget, None, None, event.button, event.time)
            return True

    def view_selected_track(self, widget):
        treeselect = self.builder.get_object("treeview2").get_selection()
        model, pathlist = treeselect.get_selected_rows()
        i = 0
        box = None
        if pathlist:
            for p in pathlist:
                tree_iter = model.get_iter(p)
                tracklayer = model.get_value(tree_iter, 5)
                if box:
                    box.compose(tracklayer.get_bounding_box())
                else:
                    box = tracklayer.get_bounding_box()
                i += 1
            self.osm.ensure_visible(box, False)
            self.show_infobar ("Showing %d tracks" % i)

    def remove_selected_track(self, widget):
        treeselect = self.builder.get_object("treeview2").get_selection()
        model, pathlist = treeselect.get_selected_rows()
        if pathlist:
            pathlist.reverse()
            for p in pathlist:
                tree_iter = model.get_iter(p)
                tracklayer = model.get_value(tree_iter, 5)
                tracklayer.destroy()
                model.remove(tree_iter)
                # TODO: remove track entry from self.gpx.gpxfiles[idx]['tracks']
                #       problem: how to do this without iterating?
            self.show_infobar("%d tracks removed" % len(pathlist))

    def treeselect2_changed(self, treeselect):
        if treeselect:
            # First, reset the color of the previously selected tracks
            for t in self.highlighted_tracks:
                t.set_stroke_color(self.clutter_color(self.track_default_color))
            self.highlighted_tracks = []

            model,pathlist = treeselect.get_selected_rows()
            if pathlist:
                for p in pathlist:
                    tree_iter = model.get_iter(p)
                    tracklayer = model.get_value(tree_iter, 5)
                    tracklayer.set_stroke_color(self.clutter_color(self.track_highlight_color))
                    # Move the layer to the top
                    # raise_top() is deprecated since v1.10 but the set_child_above_sibling() construct doesn't seem to work
                    #tracklayer.get_parent().set_child_above_sibling(tracklayer, None)
                    tracklayer.raise_top()
                    self.highlighted_tracks.append(tracklayer)
        self.markerlayer.raise_top()

    def treeview2_select_all(self, widget=None):
        self.builder.get_object("treeview2").get_selection().select_all()

    def treeview2_select_none(self, widget=None):
        self.builder.get_object("treeview2").get_selection().unselect_all()

    def init_timezonepre(self):
        store = self.builder.get_object("liststore4")
        cur_a, _ignore = self.timezone_split(self.track_timezone)

        zones = {}
        i = 0
        cur_idx = 0
        for tz in pytz.common_timezones:
            a,b =  self.timezone_split(tz)
            if not zones.has_key(a):
                zones[a] = []
                store.append([a])
                if a == cur_a:
                    cur_idx = i
                i += 1
        # Return the index in the liststore of the current timezone
        # so combobox2 can be set to that entry
        return cur_idx

    def init_combobox2and3(self, idx=0):
        combobox = self.builder.get_object("combobox2")
        renderer = Gtk.CellRendererText()
        combobox.pack_start(renderer, True)
        combobox.add_attribute(renderer, "text", 0)
        combobox.set_active(idx)
        self.combobox2_changed(combobox)

        combobox = self.builder.get_object("combobox3")
        renderer = Gtk.CellRendererText()
        combobox.pack_start(renderer, True)
        combobox.add_attribute(renderer, "text", 0)

    def combobox2_changed(self, combobox):
        model = combobox.get_model()
        active = combobox.get_active_iter()
        _ignore, cur_b = self.timezone_split(self.track_timezone)
        i = 0
        cur_idx = 0
        if active != None:
            tzpre = model[active][0]
            store = self.builder.get_object("liststore5")
            store.clear()
            for tz in pytz.common_timezones:
                a,b = self.timezone_split(tz)
                if a == tzpre:
                    store.append([b])
                    if b == cur_b:
                        cur_idx = i
                    i += 1
        self.builder.get_object("combobox3").set_active(cur_idx)

    def get_timezonedialog_result(self):
        model1  = self.builder.get_object("liststore4")
        model2  = self.builder.get_object("liststore5")

        iter1 = self.builder.get_object("combobox2").get_active_iter()
        iter2 = self.builder.get_object("combobox3").get_active_iter()

        if iter1 and iter2:
            pre = model1.get_value(iter1,0)
            post = model2.get_value(iter2,0)

        always = self.builder.get_object("checkbutton1").get_active()

        #print "%s/%s" % (pre, post)
        return ("%s%s" % (pre, '/' + post if post else ''), always)

    def timezone_split(self, tz):
        # return a 2-tuple containing the timezone in two parts
        # 'Europe/Amsterdam' => ('Europe', 'Amsterdam')
        # 'UTC'              => ('UTC', '')
        if tz.find('/') >= 0:
            a,b = tz.split('/', 1)
        else:
            a = tz
            b = ''
        return (a,b)

    def images_select_all_from_camera(self, widget=None):
        return

    def images_select_all(self, widget=None):
        self.builder.get_object("treeview1").get_selection().select_all()

    def images_select_none(self, widget=None):
        self.builder.get_object("treeview1").get_selection().unselect_all()

    def settings_dialog(self, widget=None):
        dialog = self.builder.get_object("dialog3")
        response = dialog.run()
        dialog.hide()
        if response == Gtk.ResponseType.OK:
            self.marker_color = self.builder.get_object("colorbutton1").get_color()
            self.track_default_color = self.builder.get_object("colorbutton2").get_color()
            self.track_highlight_color = self.builder.get_object("colorbutton3").get_color()
            self.settings.set_value('marker-color', GLib.Variant('(iii)', self.color_tuple(self.marker_color)))
            self.settings.set_value('normal-track-color', GLib.Variant('(iii)', self.color_tuple(self.track_default_color)))
            self.settings.set_value('selected-track-color', GLib.Variant('(iii)', self.color_tuple(self.track_highlight_color)))
            self.markerlayer.get_markers()[0].set_color(self.clutter_color(self.marker_color))
            self.with_all_tracks_do(self.set_track_color)
            self.treeselect2_changed(self.builder.get_object("treeview2").get_selection())
        else:
            self.builder.get_object("colorbutton1").set_color(self.marker_color)
            self.builder.get_object("colorbutton2").set_color(self.track_default_color)
            self.builder.get_object("colorbutton3").set_color(self.track_highlight_color)

    def with_all_tracks_do (self, callback, userdata=None):
        model = self.builder.get_object("liststore2")
        model.foreach(callback, userdata)

    def set_track_color(self, model, path, tree_iter, userdata):
        tracklayer = model.get_value(tree_iter,5)
        tracklayer.set_stroke_color(self.clutter_color(self.track_default_color))

    def treeview_x_select_all(self, widget=None):
        page = self.builder.get_object('notebook1').get_current_page()
        if page == 0:
            self.images_select_all()
        elif page == 1:
            self.treeview2_select_all()

    def about_box(self, widget=None):
        d = self.builder.get_object('aboutdialog1')
        d.run()
        d.hide()