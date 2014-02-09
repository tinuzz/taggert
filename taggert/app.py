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

from __future__ import print_function

import os
import fractions
import time
from math import modf

import pytz
from gi.repository import GtkClutter     # apt-get install gir1.2-clutter-1.0
from gi.repository import Clutter
from gi.repository import Gtk
from gi.repository import GtkChamplain
from gi.repository import Champlain
from gi.repository import GdkPixbuf
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gdk
from gi.repository import GExiv2
from pprint import pprint

from iso8601 import parse_date as parse_xml_date
import gpxfile
import polygon
import tsettings
import imagemarker
import constants
import tdata
import tfunctions
import version

GtkClutter.init([])

START  = Clutter.BinAlignment.START
CENTER = Clutter.BinAlignment.CENTER
END    = Clutter.BinAlignment.END

class App(object):
    """Main application class"""

    filelist_locked = False
    latlon_buffer = ('', '', '')
    clicked_lat = 0.0
    clicked_lon = 0.0
    default_map_id = 'osm-mapnik'
    bookmarks = {}
    #cameras = {}
    last_clicked_bookmark = None
    modified = {}
    show_tracks = True
    show_camera = False
    gpx = None
    highlighted_tracks = []
    imagemarker_opacity = 128

    def __init__(self, data_dir, args):
        """
        Constructor, initializes command line arguments and TData object
        """
        self.data_dir = data_dir
        self.args = args
        self.data = tdata.TData()
        self.gpx = gpxfile.GPXfile(self.data_dir)

    def main(self):
        """
        Application entry point, initializes the GUI and starts the Gtk main loop
        """
        self.init_builder()
        self.read_settings()
        self.setup_gui()
        self.init_map_sources()
        self.setup_map()
        self.window.show_all()
        self.init_treeview1()
        self.init_combobox1()
        idx = self.init_timezonepre()
        self.init_combobox2and3(idx)
        self.setup_gui_signals()
        self.setup_data_signals()
        self.populate_store1()
        self.update_adjustment1()
        self.reload_bookmarks()
        self.init_treeview2()
        Gtk.main()

    def init_builder(self):
        """
        Initialize the GUI with Gtk.Builder
        """
        self.builder = Gtk.Builder()
        self.builder.add_from_file(os.path.join(self.data_dir, "taggert.glade"))
        self.window = self.builder.get_object("window1")

    def read_settings(self):
        """
        Initializes a TSettings object and processes all settings, some read
        explicitly and some initialized via TSettings bindings
        """
        self.settings = tsettings.TSettings('com.tinuzz.taggert')

        # Bookmarks
        bm_names = self.settings.get_unpacked('bookmarks-names')
        bm_latitudes = self.settings.get_unpacked('bookmarks-latitudes')
        bm_longitudes = self.settings.get_unpacked('bookmarks-longitudes')

        for key, name in bm_names.items():
            self.bookmarks[key] = {
                "name": name,
                "latitude": bm_latitudes[key],
                "longitude": bm_longitudes[key]
                }

        # Home location
        self.home_location = self.settings.get_unpacked('home-location')

        # Colors
        self.marker_color = self.settings.get_color('marker-color')
        self.track_default_color = self.settings.get_color('normal-track-color')
        self.track_highlight_color = self.settings.get_color('selected-track-color')
        self.imagemarker_color = self.settings.get_color('image-marker-color')

        # TSettings bindings. This stores the values from self.settings in self.data
        self.settings.bind('last-image-dir', self.data, 'imagedir')
        self.settings.bind('last-track-folder', self.data, 'lasttrackfolder')
        self.settings.bind('track-line-width', self.data, 'trackwidth')
        self.settings.bind('marker-size', self.data, 'markersize')
        self.settings.bind('image-marker-size', self.data, 'imagemarkersize')
        self.settings.bind('track-timezone', self.data, 'tracktimezone')
        self.settings.bind('always-this-timezone', self.data, 'alwaysthistimezone')
        self.settings.bind('map-source-id', self.data, 'mapsourceid')

        # TSettings bindings for widgets' properties
        self.settings.bind('pane-position', self.builder.get_object("paned1"), 'position')
        self.settings.bind('show-untagged-only', self.builder.get_object("checkmenuitem1"), 'active')
        self.settings.bind('show-elevation-column', self.builder.get_object("checkmenuitem3"), 'active')
        self.settings.bind('show-map-coords', self.builder.get_object("checkmenuitem9"), 'active')
        self.settings.bind('show-image-markers', self.builder.get_object("menuitem35"), 'active')
        self.settings.bind('image-markers-draggable', self.builder.get_object("checkmenuitem10"), 'active')

        if not os.path.isdir(self.data.imagedir):
            self.data.imagedir = ""

    def setup_gui(self):
        """
        Initialize some GUI elements that depend on settings and which are
        not bound to TSettings directly
        """
        # Set window title
        self.window.set_title('Taggert')

        # Restore window size
        wh = self.settings.get_unpacked('window-size')
        self.window_size = wh
        self.window.set_default_size(*wh)

        self.builder.get_object("checkmenuitem2").set_active(self.show_tracks)
        self.builder.get_object("checkmenuitem37").set_active(self.show_camera)
        self.builder.get_object("checkbutton1").set_active(self.data.alwaysthistimezone)
        self.window.set_position(Gtk.WindowPosition.CENTER)
        self.statusbar = self.builder.get_object("statusbar1")
        self.builder.get_object("colorbutton1").set_color(self.marker_color)
        self.builder.get_object("colorbutton2").set_color(self.track_default_color)
        self.builder.get_object("colorbutton3").set_color(self.track_highlight_color)
        self.builder.get_object("colorbutton4").set_color(self.imagemarker_color)
        self.builder.get_object("aboutdialog1").set_version('v' + str(version.VERSION))
        self.builder.get_object("adjustment2").set_value(self.data.markersize)
        self.builder.get_object("adjustment3").set_value(self.data.trackwidth)
        self.builder.get_object("adjustment4").set_value(self.data.imagemarkersize)

    def setup_gui_signals(self):
        """
        Set up all event handlers for the Gtk.Builder GUI
        """
        handlers = {
            "window1_delete_event": self.quit,
            "window1_configure_event": self.update_window_size,
            "imagemenuitem1_activate": self.go_home,
            "imagemenuitem2_activate": self.select_dir,
            "imagemenuitem3_activate": self.save_all,
            "imagemenuitem4_activate": self.open_gpx,
            "imagemenuitem5_activate": self.quit, # File -> Quit
            "imagemenuitem7_activate": self.copy_tag,
            "imagemenuitem8_activate": self.paste_tag,
            "imagemenuitem9_activate": self.delete_tag_from_selected,
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
            "menuitem27_activate": self.go_to_marker,
            "menuitem28_activate": self.go_to_image,
            "menuitem30_activate": self.map_zoom_in,
            "menuitem31_activate": self.map_zoom_out,
            "menuitem33_activate": self.add_bookmark_dialog,
            "menuitem35_toggled": self.toggle_imagemarkers,
            "combobox1_changed": self.combobox_changed,
            "combobox2_changed": self.combobox2_changed,
            "checkmenuitem1_toggled": self.populate_store1,
            "checkmenuitem2_toggled": self.toggle_tracks,
            "checkmenuitem3_toggled": self.toggle_elevation,
            "checkmenuitem9_toggled": self.toggle_overlay,
            "checkmenuitem10_toggled": self.toggle_imagemarker_draggable,
            "checkmenuitem37_toggled": self.toggle_camera_column,
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

    def setup_data_signals(self):
        """
        Set up all handlers for notify::property signals from TData object,
        using a dictionary that maps TData properties to handler methods.
        """
        handlers = {
            "markersize": self.redraw_marker,
            "imagemarkersize": self.update_imagemarker_appearance,
            "trackwidth": lambda *ignore: self.with_all_tracks_do(self.update_track_appearance),
            'mapsourceid': self.update_map,
        }
        self.data.connect_signals(handlers)

    def setup_map(self):
        """
        Initialize the map, add layers and setup signal handlers
        """
        widget = GtkChamplain.Embed()

        box = self.builder.get_object("box2")
        box.pack_start(widget, True, True, 0)

        self.osm = widget.get_view()

        # Set the map source
        self.osm.set_map_source(self.map_sources[self.data.mapsourceid])
        self.update_adjustment1()

        # A marker layer
        self.markerlayer = Champlain.MarkerLayer()
        self.osm.add_layer(self.markerlayer)

        # An image layer
        self.imagelayer = Champlain.MarkerLayer()
        self.osm.add_layer(self.imagelayer)

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
        if not self.builder.get_object("checkmenuitem9").get_active():
            self.cbox.hide()

        widget.connect("realize", self.handle_map_event)
        widget.connect("button-release-event", self.handle_map_event)
        self.osm.connect("layer-relocated", self.handle_map_event)
        widget.connect("button-press-event", self.handle_map_mouseclick)

        # This signal doesn't seem to occur (at all):
        self.osm.connect("notify::zoom", self.on_map_zoom_changed)

        self.go_home()

    def init_combobox1(self):
        """
        Initialize the map source chooser
        """
        combobox = self.builder.get_object("combobox1")
        renderer = Gtk.CellRendererText()
        combobox.pack_start(renderer, True)
        combobox.add_attribute(renderer, "text", 1)

        self.combobox1_set_map_id()
        #combobox.set_active(0)

    def init_treeview1(self):
        """
        Initialize the treeview displaying the list of images
        """
        self.builder.get_object("liststore1").set_sort_column_id(constants.images.columns.filename,
                                                                 Gtk.SortType.ASCENDING)
        renderer = Gtk.CellRendererText()
        renderer.set_property('cell-background', 'yellow')
        col0 = Gtk.TreeViewColumn("Filename", renderer,
            text=constants.images.columns.filename,
            cell_background_set=constants.images.columns.modified)
        col1 = Gtk.TreeViewColumn("EXIF DateTime", renderer,
            text=constants.images.columns.datetime,
            cell_background_set=constants.images.columns.modified)
        col2 = Gtk.TreeViewColumn("Latitude", renderer,
            text=constants.images.columns.latitude,
            cell_background_set=constants.images.columns.modified)
        col3 = Gtk.TreeViewColumn("Longitude", renderer,
            text=constants.images.columns.longitude,
            cell_background_set=constants.images.columns.modified)
        col4 = Gtk.TreeViewColumn("Elevation", renderer,
            text=constants.images.columns.elevation,
            cell_background_set=constants.images.columns.modified)
        col5 = Gtk.TreeViewColumn("Camera", renderer,
            text=constants.images.columns.camera,
            cell_background_set=constants.images.columns.modified)

        col0.set_sort_column_id(constants.images.columns.filename)
        col1.set_sort_column_id(constants.images.columns.datetime)
        col2.set_sort_column_id(constants.images.columns.latitude)
        col3.set_sort_column_id(constants.images.columns.longitude)
        col4.set_sort_column_id(constants.images.columns.elevation)
        col5.set_sort_column_id(constants.images.columns.camera)

        tree = self.builder.get_object("treeview1")
        tree.append_column(col0)
        tree.append_column(col1)
        tree.append_column(col5)
        tree.append_column(col2)
        tree.append_column(col3)
        tree.append_column(col4)

        col4.set_visible(self.builder.get_object("checkmenuitem3").get_active())
        col5.set_visible(self.builder.get_object("checkmenuitem37").get_active())

    def update_adjustment1(self):
        """
        Update the Gtk.Adjustment that controls the zoom widget, using the map
        source for minimum and maximum values
        """
        ms = self.map_sources[self.data.mapsourceid]
        cur_zoom = self.osm.get_zoom_level()
        min_zoom = ms.get_min_zoom_level()
        max_zoom = ms.get_max_zoom_level()
        adj =  self.builder.get_object("adjustment1")
        adj.set_lower(min_zoom)
        adj.set_upper(max_zoom)
        adj.set_value(cur_zoom)

    def quit(self, _window=None, _event=None):
        """
        Quit the Gtk main loop and the application
        """
        if self.save_modified_dialog():
            Gtk.main_quit()
        else:
            return False

    def populate_store1(self, widget=None):
        """
        Populate a liststore with images, reading them from a filesystem
        directory, reading EXIF information and adding a 'modified' flag
        """
        show_untagged_only = self.builder.get_object("checkmenuitem1").get_active()
        self.filelist_locked = True
        shown = 0
        notshown = 0

        try:
            store = self.builder.get_object("liststore1")
            store.clear()
            if self.data.imagedir:
                # Clear all image markers
                self.imagelayer.remove_all()
                for fl in os.listdir(self.data.imagedir):
                    fname = os.path.join(self.data.imagedir, fl)
                    if not os.path.isdir(fname):
                        #if os.path.splitext(fname)[1].lower() == ".jpg":
                        data = None
                        modf = False
                        try:
                            metadata = GExiv2.Metadata(fname)
                            # Get the camera make/model
                            try:
                                camera = metadata.get_camera_model() or ''
                            except AttributeError:
                                camera = ''
                            # Get EXIF DateTime
                            dtobj = metadata.get_date_time()
                            if dtobj != None:
                                dt = dtobj.strftime("%Y-%m-%d %H:%M:%S")
                            else:
                                dt = ''
                            # Get image orientation
                            rot = metadata.get_orientation()

                            # Get GPS info
                            try:
                                data = self.modified[fl]
                                imglat = data['latitude']
                                imglon = data['longitude']
                                imgele = data['elevation']
                                modf = True
                            except KeyError:
                                if 'Exif.GPSInfo.GPSLatitude' in metadata.get_tags():
                                    imglon, imglat, imgele = [round(x,5) for x in metadata.get_gps_info()]
                                else:
                                    imglon = ''
                                    imglat = ''
                                    imgele = ''

                            if (not show_untagged_only) or imglat == '' or imglon == '' or data:
                                treeiter = store.append([fl, dt, rot, str(imglat), str(imglon),
                                    modf, camera, dtobj, str(imgele)])
                                shown += 1
                                if imglat and imglon:
                                    self.add_imagemarker_at(treeiter, fl, imglat, imglon)
                                #if camera not in self.cameras:
                                #    self.cameras[camera] = []
                                #self.cameras[camera].append(treeiter)
                            else:
                                notshown += 1

                        except GObject.GError:
                            # Unsupported file format
                            pass
                        except IOError:
                            # Unsupported file format
                            pass
        finally:
            self.filelist_locked = False

        self.raise_layers()
        msg = "%s: %d images" % (self.data.imagedir, shown)
        if notshown > 0:
            msg = "%s, %d already tagged images not shown" % (msg, notshown)
        self.statusbar.push(0, msg)

    def init_map_sources(self):
        """
        Initialize a list of map sources and setup Champlain map source chains
        for all of them
        """
        self.map_sources = {}
        self.map_sources_names = {}

        self.mapstore = self.builder.get_object("liststore3")

        sources = [
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

            ['mapbox-streets', 'Mapbox Streets', 0, 19, 256,
            'Mapbox',
            'http://www.gnu.org/copyleft/fdl.html',
            'http://a.tiles.mapbox.com/v3/examples.map-vyofok3q/#Z#/#X#/#Y#.png'],

            ['mapbox-terrain', 'Mapbox Terrain', 0, 19, 256,
            'Mapbox',
            'http://www.gnu.org/copyleft/fdl.html',
            'http://a.tiles.mapbox.com/v3/examples.map-9ijuk24y/#Z#/#X#/#Y#.png'],

            ['mapbox-satellite', 'Mapbox Satellite', 0, 19, 256,
            'Mapbox',
            'http://www.gnu.org/copyleft/fdl.html',
            'http://a.tiles.mapbox.com/v3/examples.map-qfyrx5r8/#Z#/#X#/#Y#.png'],

            ['stamen-watercolor', 'Stamen Watercolor', 0, 17, 256,
            'Map tiles by Stamen Design, under CC BY 3.0. Data by OpenStreetMap, under CC BY SA',
            'http://creativecommons.org/licenses/by-sa/3.0/',
            'http://tile.stamen.com/watercolor/#Z#/#X#/#Y#.jpg'],

            #['cloudmade-fresh', 'Cloudmade Fresh 997', 0, 18, 256,
            #'(C) 2008-2012 CloudMade. Map data (C) 2012 OpenStreetMap.org contributors',
            #'http://creativecommons.org/licenses/by-sa/3.0/',
            #'http://b.tile.cloudmade.com/8ee2a50541944fb9bcedded5165f09d9/997/256/#Z#/#X#/#Y#.png'],
        ]

        # Usage of these sources is in violation of Google's terms of service,
        # see http://maps.google.com/help/terms_maps.html
        if self.args.google:
            sources.extend([
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
            ])

        for map_desc in sources:
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

        if not self.data.mapsourceid in self.map_sources:
            self.data.mapsourceid = self.default_map_id

    def combobox_changed(self, combobox):
        """
        Handler for 'changed' event from map source chooser, changes the
        actual map source on the ChamplainView, stores the chosen value
        in TSettings and updates the zoom widget
        """
        model = combobox.get_model()
        active = combobox.get_active_iter()
        if active != None:
            self.data.mapsourceid = model[active][0]

    def update_map(self, _data=None, _prop=None):
        try:
            self.osm.set_map_source(self.map_sources[self.data.mapsourceid])
            self.update_adjustment1()
        except KeyError:
            self.data.mapsourceid = self.default_map_id

    def treeselect_changed (self, treeselect):
        """
        Handler for 'changed' event on the TreeSelection of the images list,
        loads a preview of the currently selected image
        """
        if self.filelist_locked:
            return
        if treeselect:
            model,pathlist = treeselect.get_selected_rows()
            if pathlist:
                # Get the first selected picture
                p = pathlist[0]
                tree_iter = model.get_iter(p)
                value = model.get_value(tree_iter, constants.images.columns.filename)
                orientation = model.get_value(tree_iter, constants.images.columns.rotation)
                filename = os.path.join(self.data.imagedir, value)

                pb = GdkPixbuf.Pixbuf.new_from_file_at_size(filename, 300, 200)
                if orientation == GExiv2.Orientation.ROT_90:
                    pb = pb.rotate_simple(GdkPixbuf.PixbufRotation.CLOCKWISE)
                elif orientation == GExiv2.Orientation.ROT_270:
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
                preview.set_from_pixbuf(pb)

    def save_modified_dialog(self):
        """
        Displays a MessageDialog, offering to save any unsaved changes and
        handle the result
        """
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
        """
        Display a FileChooserDialog to select a new image folder and store the
        result in TData object
        """
        if self.save_modified_dialog():
            chooser = Gtk.FileChooserDialog("Select image folder", self.window, Gtk.FileChooserAction.SELECT_FOLDER,
                (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, "Select", Gtk.ResponseType.OK))
            chooser.set_create_folders(False)

            if self.data.imagedir and os.path.isdir(self.data.imagedir):
                chooser.set_current_folder_uri('file://%s' % self.data.imagedir)

            response = chooser.run()
            chooser.hide()
            if response == Gtk.ResponseType.OK:   # http://developer.gnome.org/gtk3/3.4/GtkDialog.html#GtkResponseType
                self.data.set_property("imagedir", chooser.get_filename())
                self.modified = {}
                self.populate_store1()
            chooser.destroy()

    def go_to_location(self, lat, lon, zoom=None):
        """
        Center the map view on the specified coordinates and change the zoom
        level if requested
        """
        self.osm.center_on(lat, lon)
        if zoom:
            self.osm.set_zoom_level(zoom)

    def go_home(self, _widget=None):
        """
        Move the marker to the user's home location and show it on the map
        """
        self.add_marker_at(*self.home_location)
        self.go_to_location(*self.home_location)

    def go_to_marker(self, _widget=None):
        """
        Center the map view on the current location of the marker
        """
        try:
            m = self.markerlayer.get_markers()[0]
            lat, lon = (m.get_latitude(), m.get_longitude())
            self.osm.center_on(lat, lon)
        except IndexError:
            pass

    def handle_map_event(self, _widget, _ignore=None):
        """
        Handler for several map events that indicate that the center of the
        map has moved, changes the coordinates displayed in the map overlay
        and updates the zoom widget
        """
        lat = self.osm.get_center_latitude()
        lon = self.osm.get_center_longitude()
        text = tfunctions.latlon_to_text(lat,lon)
        self.clabel.set_text (text)
        self.update_adjustment1()

    def handle_map_mouseclick(self, _widget, event):
        """
        Handler for right-click event on the map, opens the map context menu
        and stores the coordinates of the clicked location
        """
        if event.button == 3:
            menu = self.builder.get_object("menu6")
            menu.popup(None, None, None, None, event.button, event.time)
            self.clicked_lat, self.clicked_lon = self.osm.y_to_latitude(event.y), self.osm.x_to_longitude(event.x)

    def add_marker_at(self, lat, lon, _zoom=None):
        """
        Reset the marker on the map to the specified coordinates
        """
        self.markerlayer.remove_all()
        point = Champlain.Point()
        point.set_location(lat, lon)
        point.set_color(tfunctions.clutter_color(self.marker_color))
        point.set_size(self.data.get_property("markersize"))
        point.set_draggable(True)
        self.markerlayer.add_marker(point)

    def add_imagemarker_at(self, treeiter, filename, lat, lon):
        """
        Place an ImageMarker on the map at the specified coordinates
        """
        eventmap = {
            "button-press": self.imagemarker_clicked,
            "drag-finish": self.imagemarker_dragged,
        }
        point = imagemarker.ImageMarker(treeiter, filename, float(lat), float(lon), eventmap)
        point.set_color(tfunctions.clutter_color(self.imagemarker_color, self.imagemarker_opacity))
        point.set_size(self.data.imagemarkersize)
        point.set_draggable(self.builder.get_object("checkmenuitem10").get_active())
        self.imagelayer.add_marker(point)

    def map_add_marker(self, _widget):
        """
        Reset the marker on the map to the location that was last
        right-clicked
        """
        self.add_marker_at(self.clicked_lat, self.clicked_lon)

    def redraw_marker(self, _data=None, _prop=None):
        """
        Redraw the marker on the map, for when its size or color should change
        """
        try:
            m = self.markerlayer.get_markers()[0]
            lat, lon = (m.get_latitude(), m.get_longitude())
            self.add_marker_at(lat,lon)
        except IndexError:
            pass

    def center_map_here(self, _widget):
        """
        Center the map view on the location that was last right-clicked
        """
        self.osm.center_on(self.clicked_lat, self.clicked_lon)
        #self.osm.go_to(self.clicked_lat, self.clicked_lon)

    def map_zoom_in(self, widget=None, event=None):
        """
        Zoom in on the map view and update the zoom widget
        """
        self.osm.zoom_in()
        self.update_adjustment1()

    def map_zoom_out(self, widget=None, event=None):
        """
        Zoom out from the map view and update the zoom widget
        """
        self.osm.zoom_out()
        self.update_adjustment1()

    def adjust_zoom(self, adj, _map=None):
        """
        Set the zoom level of the map view to the value of the zoom widget's
        Gtk.Adjustment
        """
        zoom = adj.get_value()
        cur_zoom = self.osm.get_zoom_level()
        if zoom != cur_zoom:
            self.osm.set_zoom_level(zoom)
            self.update_adjustment1()

    def on_map_zoom_changed(self):
        """
        Handler for the "notify::zoom" signal from the map view, updates the
        zoom widget.
        """
        self.update_adjustment1()

    def add_bookmark_dialog(self, widget):
        """
        Open a dialog offering to add a bookmark for the current marker
        location and store the result
        """
        try:
            m = self.markerlayer.get_markers()[0]
            lat, lon = (m.get_latitude(), m.get_longitude())
            self.go_to_marker()
        except IndexError:
            lat = self.osm.get_center_latitude()
            lon = self.osm.get_center_longitude()

        self.builder.get_object("entry1").set_text(tfunctions.latlon_to_text(lat,lon))
        self.builder.get_object("entry2").set_text("%.5f" % lat)
        self.builder.get_object("entry3").set_text("%.5f" % lon)
        dialog = self.builder.get_object("dialog1")
        self.builder.get_object("entry1").grab_focus()
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
        """
        Reload the bookmarks menu by first removing all entries after the
        first SeparatorMenuItem and then recreating menuitems from all
        bookmarks, after sorting the list case-insensitively by name
        """
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

        # Now add bookmarks as menuitems, sorted by name
        for bm_id, bm in sorted(self.bookmarks.items(), key=lambda (k,v): (v["name"].lower(),k)):
            item = Gtk.MenuItem()
            item.set_label(bm['name'])
            item.set_name(bm_id)
            item.connect("button-press-event", self.handle_bookmark_click)
            menu.append(item)
            item.show()

    def save_bookmarks(self):
        """
        Save bookmarks to TSettings
        """
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
        """
        Reset the marker to the specified bookmark's coordinates and center
        the map view on it
        """
        bm_id = widget.get_name()
        self.add_marker_at(self.bookmarks[bm_id]['latitude'], self.bookmarks[bm_id]['longitude'])
        self.go_to_marker()

    def go_to_image(self, widget):
        """
        If the first selected image in the list is tagged, reset the marker to
        it and center the map view on it
        """
        treeselect = self.builder.get_object("treeview1").get_selection()
        model,pathlist = treeselect.get_selected_rows()
        if pathlist:
            # Get the first selected picture
            p = pathlist[0]
            tree_iter = model.get_iter(p)
            lat = model.get_value(tree_iter, constants.images.columns.latitude)
            lon = model.get_value(tree_iter, constants.images.columns.longitude)
            if lat and lon:
                self.add_marker_at(float(lat),float(lon))
                self.go_to_marker()

    def handle_bookmark_click(self, widget, event):
        """
        Handler for 'button-press-event' signal from bookmark menu item, open
        a context pop-up if it's a right-click, go to the selected bookmark
        otherwise
        """
        if event.button == 3: # right click
            self.last_clicked_bookmark = widget
            popup = self.builder.get_object("menu7")
            popup.popup(None, widget, None, None, event.button, event.time)
            return True
        else:
            self.go_to_bookmark(widget)

    def delete_bookmark(self, widget):
        """
        Delete the bookmark that was last right-clicked on
        """
        bm_id = self.last_clicked_bookmark.get_name()
        self.last_clicked_bookmark.destroy()
        del self.bookmarks[bm_id]
        self.save_bookmarks()

    def tag_selected_from_marker(self, widget):
        """
        Add a geotag using the marker's location to all selected images
        """
        try:
            m = self.markerlayer.get_markers()[0]
            lat, lon = (m.get_latitude(), m.get_longitude())
            ele = 0.0
            self.tag_selected(lat,lon,ele)
        except IndexError:
            pass

    def tag_selected_from_track(self, widget):
        """
        If any tracks are available, add a geotag using coordinates from the
        tracks to all selected images
        """
        # Any tracks available?
        if not len(self.gpx.tracks):
            self.show_infobar ("No tracks loaded, cannot tag images")
            return
        treeselect = self.builder.get_object("treeview1").get_selection()
        model,pathlist = treeselect.get_selected_rows()
        if pathlist:
            try:
                i=0
                for p in pathlist:
                    tree_iter = model.get_iter(p)
                    filename = model[tree_iter][constants.images.columns.filename]
                    dt = model[tree_iter][constants.images.columns.dtobject]
                    if dt:
                        lat, lon, ele = self.gpx.find_coordinates(dt)
                        if lat and lon:
                            #print("%s %.5f %.5f" % (filename, lat, lon))
                            # Modify the coordinates
                            model[tree_iter][constants.images.columns.latitude] = "%.5f" % lat
                            model[tree_iter][constants.images.columns.longitude] = "%.5f" % lon
                            model[tree_iter][constants.images.columns.elevation] = "%.2f" % ele
                            model[tree_iter][constants.images.columns.modified] = True
                            self.move_imagemarker(tree_iter, filename, lat, lon)
                            self.modified[filename] = {'latitude': "%.5f" % lat, 'longitude': "%.5f" % lon, 'elevation': "%.2f" % ele}
                            i += 1
                self.show_infobar ("Tagged %d image%s" % (i, '' if i == 1 else 's'))
            except IndexError:
                pass

    def tag_selected(self, lat, lon, ele):
        """
        Add a geotag with specified coordinates and elevation to all selected
        images
        """
        arg_ele = ele
        treeselect = self.builder.get_object("treeview1").get_selection()
        model,pathlist = treeselect.get_selected_rows()
        if pathlist:
            i=0
            for p in pathlist:
                tree_iter = model.get_iter(p)
                filename = model[tree_iter][constants.images.columns.filename]
                if arg_ele == None:
                    ele = float(model[tree_iter][constants.images.columns.elevation])
                try:
                    model[tree_iter][constants.images.columns.latitude] = "%.5f" % float(lat)
                    model[tree_iter][constants.images.columns.longitude] = "%.5f" % float(lon)
                    model[tree_iter][constants.images.columns.elevation] = "%.2f" % float(ele)
                except ValueError:  # could not convert to float
                    model[tree_iter][constants.images.columns.latitude] = ''
                    model[tree_iter][constants.images.columns.longitude] = ''
                    model[tree_iter][constants.images.columns.elevation] = ''
                model[tree_iter][constants.images.columns.modified] = True
                self.move_imagemarker(tree_iter, filename, lat, lon)
                self.modified[filename] = {'latitude': "%.5f" % lat, 'longitude': "%.5f" % lon, 'elevation': "%.2f" % ele}
                i += 1
            self.show_infobar ("Tagged %d image%s" % (i, '' if i == 1 else 's'))

    def delete_tag_from_selected(self, widget):
        """
        If the images list is currently visible, remove any geotags from all
        selected images
        """
        # Don't do this out of sight
        if self.builder.get_object('notebook1').get_current_page() != 0:
            return
        treeselect = self.builder.get_object("treeview1").get_selection()
        model,pathlist = treeselect.get_selected_rows()
        i=0
        if pathlist:
            for p in pathlist:
                tree_iter = model.get_iter(p)
                lat = model.get_value(tree_iter, constants.images.columns.latitude)
                lon = model.get_value(tree_iter, constants.images.columns.longitude)
                if lat or lon:
                    filename = model[tree_iter][constants.images.columns.filename]
                    model[tree_iter][constants.images.columns.latitude] = ''
                    model[tree_iter][constants.images.columns.longitude] = ''
                    model[tree_iter][constants.images.columns.elevation] = ''
                    model[tree_iter][constants.images.columns.modified] = True
                    self.remove_imagemarker(filename)
                    self.modified[filename] = {'latitude': '', 'longitude': '', 'elevation': ''}
                    i += 1
        self.show_infobar ("Deleted tags from %d image%s" % (i, '' if i == 1 else 's'))

    def save_all(self, widget=None):
        """
        Save all modified images, repopulate the images list with only untagged
        images if so desired
        """
        model = self.builder.get_object('treeview1').get_model()
        self.savecounter = 0
        model.foreach(self.treestore_save_modified, None)

        # If we only want to see untagged images, repopulate the treeview
        if self.builder.get_object("checkmenuitem1").get_active():
            self.populate_store1()
        self.show_infobar("%d image%s saved" % (self.savecounter, '' if self.savecounter == 1 else 's'))

    def treestore_save_modified(self, model, path, tree_iter, userdata):
        """
        For all modified images, read the metadata from the file, update it
        with our changes and write it back to the file
        """
        fl = model.get_value(tree_iter, constants.images.columns.filename)
        if model.get_value(tree_iter, constants.images.columns.modified):
            fname = os.path.join(self.data.imagedir, fl)
            metadata = GExiv2.Metadata(fname)
            try:
                lat = float(model.get_value(tree_iter, constants.images.columns.latitude))
                lon = float(model.get_value(tree_iter, constants.images.columns.longitude))
                ele = float(model.get_value(tree_iter, constants.images.columns.elevation))
                metadata.set_gps_info(lon, lat, ele)
            # If the tag is empty, the conversion to float will fail with a ValueError
            except ValueError:
                metadata.delete_gps_info()

            metadata.save_file()
            model[tree_iter][5] = False  # saved => not modified
            del self.modified[fl]
            self.savecounter += 1
            self.update_gtk()

    def show_infobar(self, text, timeout=5):
        """
        Show the specified text in the infobar and hide the infobar after the
        specified amount of time
        """
        self.builder.get_object("label9").set_text(text)
        self.builder.get_object("infobar1").show()
        GLib.timeout_add_seconds(timeout, self.hide_infobar)

    def hide_infobar(self, widget=None):
        """
        Hide the infobar
        """
        self.builder.get_object("infobar1").hide()
        # return False to cancel the timer
        return False

    def combobox1_set_map_id(self):
        """
        Iterate over the map source chooser liststore and activate the current
        map source
        """
        model = self.builder.get_object("liststore3")
        model.foreach(self.find_and_set_map_id, self.data.mapsourceid)

    def find_and_set_map_id(self, model, path, tree_iter, string):
        """
        For the specified map source chooser entry, match the map_id against
        the currently selected map_id, and activate the entry if it matches
        """
        map_id = model.get_value(tree_iter, constants.mapsources.columns.mapid)
        if map_id == string:
            self.builder.get_object("combobox1").set_active_iter(tree_iter)
            return True
        return False

    def set_home_location(self, widget=None):
        """
        Set the home location from the location of the marker
        """
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
        """
        Handler for the 'toggled' signal from a checkmenuitem, shows or hides the
        coordinates overlay on the map accordingly
        """
        if self.builder.get_object("checkmenuitem9").get_active():
            self.cbox.show()
        else:
            self.cbox.hide()

    def process_gpx(self, filename, tz):
        """
        Import a GPX file draw all the tracks in it on the map, using a
        different Polygon for each track, and add the track to the liststore
        for the tracks list
        """
        idx, msg = self.gpx.import_gpx(filename, tz)
        if idx is False:
            errmsg = ("Importing file '%s' failed with the following error:\n\n%s\n\n" +
                "Please check if your file is a valid GPX file.") % (filename, msg)

            dialog = Gtk.MessageDialog(self.window, 0, Gtk.MessageType.ERROR,
                Gtk.ButtonsType.OK, "Import error")
            dialog.format_secondary_text(errmsg)
            dialog.run()
            dialog.destroy()
            return False
        store = self.builder.get_object("liststore2")
        i = 0
        for tid, tobj in self.gpx.get_tracks(idx).iteritems():
            trk = tobj.trk
            # Create a tracklayer for each track
            tracklayer = polygon.Polygon(width=self.data.get_property("trackwidth"))
            tracklayer.set_stroke_color(tfunctions.clutter_color(self.track_default_color))
            t0, tx = tobj.get_timestamps()
            p = 0

            for point in tobj.get_points():
                p += 1
                tracklayer.append_point(float(point.get('lat')), float(point.get('lon')))

            store.append([
                tobj.get_name(),
                t0.strftime("%Y-%m-%d %H:%M:%S"),
                tx.strftime("%Y-%m-%d %H:%M:%S"),
                p, tid, tracklayer, tobj.get_distance()
            ])
            self.osm.add_layer(tracklayer)
            if not self.show_tracks:
                tracklayer.hide()
            i += 1
            self.raise_layers()
            self.update_gtk()

        # Store the directory of the file for next time
        self.data.set_property('lasttrackfolder', os.path.dirname(filename))
        return i

    def init_treeview2(self):
        """
        Initialize the tracks list
        """
        self.builder.get_object("liststore2").set_sort_column_id(1,  Gtk.SortType.ASCENDING)
        renderer = Gtk.CellRendererText()
        #renderer.set_property('cell-background', 'yellow')
        col0 = Gtk.TreeViewColumn("Name", renderer, text=0)
        col1 = Gtk.TreeViewColumn("Start time", renderer, text=1)
        col2 = Gtk.TreeViewColumn("End time", renderer, text=2)
        col3 = Gtk.TreeViewColumn("Points", renderer, text=3)
        col4 = Gtk.TreeViewColumn("Distance", renderer, text=6)

        col0.set_sort_column_id(0)
        col1.set_sort_column_id(1)
        col2.set_sort_column_id(2)
        col3.set_sort_column_id(3)
        col4.set_sort_column_id(4)

        tree = self.builder.get_object("treeview2")
        tree.append_column(col0)
        tree.append_column(col1)
        tree.append_column(col2)
        tree.append_column(col3)
        tree.append_column(col4)

    def open_gpx(self, widget=None):
        """
        Display a FileChooserDialog for selecting one or more GPX files to
        open. Process the result, asking for the timezone of the images if
        necessary
        """
        filefilter = Gtk.FileFilter()
        filefilter.set_name("GPX files")
        filefilter.add_pattern('*.gpx')
        filefilter.add_pattern('*.GPX')

        chooser = Gtk.FileChooserDialog("Open GPX file", self.window, Gtk.FileChooserAction.OPEN,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
        chooser.set_select_multiple(True)
        chooser.add_filter(filefilter)
        if self.data.lasttrackfolder and os.path.isdir(self.data.lasttrackfolder):
            chooser.set_current_folder_uri('file://%s' % self.data.lasttrackfolder)
        response = chooser.run()
        chooser.hide()
        if response == Gtk.ResponseType.OK:   # http://developer.gnome.org/gtk3/3.4/GtkDialog.html#GtkResponseType
            filenames = chooser.get_filenames()
            if not self.data.alwaysthistimezone:
                self.set_timezone_dialog()
            i = 0
            self.builder.get_object('notebook1').set_current_page(1)
            self.update_gtk()
            start = time.time()
            for filename in filenames:
                # self.process_gpx returns the number of tracks or False in case of errors
                i0 = self.process_gpx(filename, self.data.tracktimezone)
                if i0 == False:
                    continue
                else:
                    i += i0
            end = time.time()
            if (len(filenames) == 1):
                msg = os.path.basename(filename)
            else:
                msg = "%d files" % len(filenames)
            self.show_infobar ("%d %stracks added from '%s' in %.2f seconds" % (i, 'hidden ' if not self.show_tracks else '', msg, end - start))
        chooser.destroy()

    def set_timezone_dialog(self, widget=None):
        """
        Display a dialog window for choosing a timezone and optionally setting
        to always use this timezone from now on. Store the result in TData.
        """
        dialog = self.builder.get_object ("dialog2")
        resp2 = dialog.run()
        dialog.hide()
        self.data.tracktimezone, self.data.alwaysthistimezone = self.get_timezonedialog_result()

    def toggle_tracks(self, widget=None):
        """
        Iterate over all tracks and show or hide the corresponding tracklayer
        """
        checked = self.builder.get_object("checkmenuitem2").get_active()
        self.show_tracks = checked
        model = self.builder.get_object("liststore2")
        model.foreach(self.show_tracklayer, checked)

    def toggle_imagemarkers(self, widget=None):
        """
        Handler for the 'toggled' signal from a checkmenuitem, shows or hides
        imagemarkers on the map accordingly
        """
        checked = self.builder.get_object("menuitem35").get_active()
        if checked:
            self.imagelayer.show()
        else:
            self.imagelayer.hide()

    def show_tracklayer(self, model, path, tree_iter, show):
        """
        Look up a tracklayer in the specified model and show or hide it as
        specified
        """
        tracklayer = model.get_value(tree_iter, constants.tracks.columns.layer)
        if show:
            tracklayer.show()
        else:
            tracklayer.hide()

    def handle_treeview1_click(self, widget, event):
        """
        Handler for right-click event on the images list, opens the context
        menu
        """
        if event.button == 3: # right click
            popup = self.builder.get_object("menu9")
            popup.popup(None, widget, None, None, event.button, event.time)
            return True

    def handle_treeview2_click(self, widget, event):
        """
        Handler for right-click event on the tracks list, opens the context
        menu
        """
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
        """
        Get the composed bounding box for all selected tracks and make sure it
        is visible on the map
        """
        treeselect = self.builder.get_object("treeview2").get_selection()
        model, pathlist = treeselect.get_selected_rows()
        i = 0
        box = None
        if pathlist:
            for p in pathlist:
                tree_iter = model.get_iter(p)
                tracklayer = model.get_value(tree_iter, constants.tracks.columns.layer)
                if box:
                    box.compose(tracklayer.get_bounding_box())
                else:
                    box = tracklayer.get_bounding_box()
                i += 1
            self.osm.ensure_visible(box, False)
            self.show_infobar ("Showing %d tracks" % i)

    def remove_selected_track(self, widget):
        """
        Remove the selected tracks from the tracks list and from the map
        """
        treeselect = self.builder.get_object("treeview2").get_selection()
        model, pathlist = treeselect.get_selected_rows()
        if pathlist:
            pathlist.reverse()
            for p in pathlist:
                tree_iter = model.get_iter(p)
                tracklayer = model.get_value(tree_iter, constants.tracks.columns.layer)
                tracklayer.destroy()
                tid = model.get_value(tree_iter, constants.tracks.columns.tid)
                self.gpx.remove_track(tid)
                model.remove(tree_iter)
            self.show_infobar("%d tracks removed" % len(pathlist))

    def treeselect2_changed(self, treeselect):
        """
        Handler for 'changed' event on the TreeSelection of the tracks list,
        highlights the selected track(s) on the map
        """
        if treeselect:
            # First, reset the color of the previously selected tracks
            for t in self.highlighted_tracks:
                t.set_stroke_color(tfunctions.clutter_color(self.track_default_color))
            self.highlighted_tracks = []

            model,pathlist = treeselect.get_selected_rows()
            if pathlist:
                for p in pathlist:
                    tree_iter = model.get_iter(p)
                    tracklayer = model.get_value(tree_iter, constants.tracks.columns.layer)
                    tracklayer.set_stroke_color(tfunctions.clutter_color(self.track_highlight_color))
                    # Move the layer to the top
                    # raise_top() is deprecated since v1.10 but the set_child_above_sibling() construct doesn't seem to work
                    #tracklayer.get_parent().set_child_above_sibling(tracklayer, None)
                    tracklayer.raise_top()
                    self.highlighted_tracks.append(tracklayer)
        self.raise_layers()

    def treeview2_select_all(self, widget=None):
        """
        Select all tracks
        """
        self.builder.get_object("treeview2").get_selection().select_all()

    def treeview2_select_none(self, widget=None):
        """
        Select no tracks
        """
        self.builder.get_object("treeview2").get_selection().unselect_all()

    def init_timezonepre(self):
        """
        Initialize the liststore for the prefix combobox for timezone selection
        from pytz.common_timezones
        """
        store = self.builder.get_object("liststore4")
        cur_a, _ignore = tfunctions.timezone_split(self.data.tracktimezone)

        zones = {}
        i = 0
        cur_idx = 0
        for tz in pytz.common_timezones:
            a,b =  tfunctions.timezone_split(tz)
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
        """
        Initialize both timezone selection comboboxes
        """
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
        """
        Handler for the 'changed' event on the timezone prefix selector, loads
        the liststore of the timezone postfix selector with corresponding
        values from pytz.common_timezones
        """
        model = combobox.get_model()
        active = combobox.get_active_iter()
        _ignore, cur_b = tfunctions.timezone_split(self.data.tracktimezone)
        i = 0
        cur_idx = 0
        if active != None:
            tzpre = model[active][0]
            store = self.builder.get_object("liststore5")
            store.clear()
            for tz in pytz.common_timezones:
                a,b = tfunctions.timezone_split(tz)
                if a == tzpre:
                    store.append([b])
                    if b == cur_b:
                        cur_idx = i
                    i += 1
        self.builder.get_object("combobox3").set_active(cur_idx)

    def get_timezonedialog_result(self):
        """
        Return the results from the timezone selection dialog
        """
        model1  = self.builder.get_object("liststore4")
        model2  = self.builder.get_object("liststore5")

        iter1 = self.builder.get_object("combobox2").get_active_iter()
        iter2 = self.builder.get_object("combobox3").get_active_iter()

        if iter1 and iter2:
            pre = model1.get_value(iter1,0)
            post = model2.get_value(iter2,0)

        always = self.builder.get_object("checkbutton1").get_active()

        return ("%s%s" % (pre, '/' + post if post else ''), always)

    def images_select_all_from_camera(self, widget=None):
        """
        Select all images from the same camera. Not implemented.
        """
        treeselect = self.builder.get_object("treeview1").get_selection()
        model,pathlist = treeselect.get_selected_rows()
        if len(pathlist) > 1:
            self.show_infobar("Cannot select by camera from multiple images.")
        else:
            tree_iter = model.get_iter(pathlist[0])
            camera = model.get_value(tree_iter, constants.images.columns.camera)
            self.with_all_images_do(self.select_from_camera, camera)

    def images_select_all(self, widget=None):
        """
        Select all images
        """
        #pprint(Gtk.Buildable.get_name(widget))
        self.builder.get_object("treeview1").get_selection().select_all()

    def images_select_none(self, widget=None):
        """
        Select no images
        """
        self.builder.get_object("treeview1").get_selection().unselect_all()

    def select_from_camera(self, model, path, tree_iter, camera):
        """
        Callback function to select a given tree_iter if the value for
        the 'camera' field matches the given camera value
        """
        treeselect = self.builder.get_object("treeview1").get_selection()
        if model.get_value(tree_iter, constants.images.columns.camera) == camera:
            treeselect.select_path(path)
            self.update_gtk()

    def settings_dialog(self, widget=None):
        """
        Display the settings dialog and process the response, storing the
        settings in TData or writing them to TSettings and updating the GUI
        """
        dialog = self.builder.get_object("dialog3")
        response = dialog.run()
        dialog.hide()
        if response == Gtk.ResponseType.OK:
            # set values locally
            self.marker_color = self.builder.get_object("colorbutton1").get_color()
            self.track_default_color = self.builder.get_object("colorbutton2").get_color()
            self.track_highlight_color = self.builder.get_object("colorbutton3").get_color()
            self.imagemarker_color = self.builder.get_object("colorbutton4").get_color()
            self.data.set_property("markersize", self.builder.get_object("adjustment2").get_value())
            self.data.set_property("trackwidth", self.builder.get_object("adjustment3").get_value())
            self.data.set_property("imagemarkersize", self.builder.get_object("adjustment4").get_value())

            # save settings
            self.settings.set_value('marker-color', GLib.Variant('(iii)', tfunctions.color_tuple(self.marker_color)))
            self.settings.set_value('normal-track-color', GLib.Variant('(iii)', tfunctions.color_tuple(self.track_default_color)))
            self.settings.set_value('selected-track-color', GLib.Variant('(iii)', tfunctions.color_tuple(self.track_highlight_color)))
            self.settings.set_value('image-marker-color', GLib.Variant('(iii)', tfunctions.color_tuple(self.imagemarker_color)))

            # update GUI appearance
            self.markerlayer.get_markers()[0].set_color(tfunctions.clutter_color(self.marker_color))
            self.treeselect2_changed(self.builder.get_object("treeview2").get_selection())
        else:
            # Reset preferences window
            self.builder.get_object("colorbutton1").set_color(self.marker_color)
            self.builder.get_object("colorbutton2").set_color(self.track_default_color)
            self.builder.get_object("colorbutton3").set_color(self.track_highlight_color)
            self.builder.get_object("colorbutton4").set_color(self.imagemarker_color)
            self.builder.get_object("adjustment2").set_value(self.data.markersize)
            self.builder.get_object("adjustment3").set_value(self.data.trackwidth)
            self.builder.get_object("adjustment4").set_value(self.data.imagemarkersize)

    def with_all_images_do (self, callback, userdata=None):
        """
        Iterate over all tracks and call the specified function on each of them
        """
        model = self.builder.get_object("liststore1")
        model.foreach(callback, userdata)

    def with_all_tracks_do (self, callback, userdata=None):
        """
        Iterate over all tracks and call the specified function on each of them
        """
        model = self.builder.get_object("liststore2")
        model.foreach(callback, userdata)

    def update_track_appearance(self, model, path, tree_iter, userdata):
        """
        Update the color and stroke width of a track on the map according to
        current settings
        """
        tracklayer = model.get_value(tree_iter, constants.tracks.columns.layer)
        tracklayer.set_stroke_color(tfunctions.clutter_color(self.track_default_color))
        tracklayer.set_stroke_width(self.data.trackwidth)

    def update_imagemarker_appearance(self, _data=None, _prop=None):
        for m in self.imagelayer.get_markers():
            m.set_color(tfunctions.clutter_color(self.imagemarker_color, self.imagemarker_opacity))
            m.set_size(self.data.imagemarkersize)
            m.set_draggable(self.builder.get_object("checkmenuitem10").get_active())

    def treeview_x_select_all(self, widget=None):
        """
        Select all images or tracks, depending on which page is currently
        visible
        """
        page = self.builder.get_object('notebook1').get_current_page()
        if page == constants.notebook.pages.images:
            self.images_select_all()
        elif page == constants.notebook.pages.tracks:
            self.treeview2_select_all()

    def about_box(self, widget=None):
        """
        Display the about box
        """
        d = self.builder.get_object('aboutdialog1')
        d.run()
        d.hide()

    def copy_tag(self, widget=None):
        """
        Copy coordinates from a single selected image to a buffer
        """
        treeselect = self.builder.get_object("treeview1").get_selection()
        model,pathlist = treeselect.get_selected_rows()
        if len(pathlist) > 1:
            self.show_infobar("Cannot copy from multiple images. Select only one.")
        else:
            tree_iter = model.get_iter(pathlist[0])
            lat = model.get_value(tree_iter, constants.images.columns.latitude)
            lon = model.get_value(tree_iter, constants.images.columns.longitude)
            ele = model.get_value(tree_iter, constants.images.columns.elevation)
            self.latlon_buffer = (lat, lon, ele)
            if lat and lon:
            #    self.latlon_buffer = (lat, lon, '')
                msg = "coordinates %s,%s" % (lat,lon)
            else:
                msg = "empty coordinates"
            self.show_infobar("Copied %s" % msg)

    def paste_tag(self, widget=None):
        """
        If the images list is visible, paste the contents of the coordinate
        buffer to all currently selected images
        """
        # Only do this if the images tab is active
        if self.builder.get_object('notebook1').get_current_page() != constants.notebook.pages.images:
            return
        lat, lon, ele = self.latlon_buffer
        self.tag_selected(lat,lon,ele)

    def toggle_elevation(self, widget=None):
        """
        Handler for the 'toggled' signal from a checkmenuitem, shows or hides the
        elevation column in the images list accordingly
        """
        checked = self.builder.get_object("checkmenuitem3").get_active()
        self.builder.get_object("treeview1").get_column(5).set_visible(checked)

    def toggle_camera_column(self, widget=None):
        """
        Handler for the 'toggled' signal from a checkmenuitem, shows or hides the
        camera ID column in the images list accordingly
        """
        checked = self.builder.get_object("checkmenuitem37").get_active()
        self.show_camera = checked
        self.builder.get_object("treeview1").get_column(2).set_visible(checked)

    def update_gtk(self):
        """
        Run Gtk main iterations for as long as events are pending
        """
        while Gtk.events_pending():
            Gtk.main_iteration()

    def update_window_size(self, window, userdata):
        """
        Handler for 'configure_event' on the main window, saves the window size
        to TSettings
        """
        size = window.get_size()
        if size != self.window_size:
            self.window_size = size
            self.settings.set_value('window-size', GLib.Variant('(ii)', size))

    def raise_layers(self):
        """
        Move markerlayer and then imagelayer to the top
        raise_top() is deprecated since v1.10 but this set_child_above_sibling()
        construct doesn't seem to work:
        tracklayer.get_parent().set_child_above_sibling(tracklayer, None)
        """
        self.markerlayer.raise_top()
        self.imagelayer.raise_top()

    def imagemarker_clicked(self, marker, clutterevent, userdata=None):
        """
        Handler for the 'clicked' signal from an ImageMarker, selects the
        corresponding image in the images list
        """
        treeselect = self.builder.get_object("treeview1").get_selection()
        # Control-key used? Expand or reduce selection.
        if clutterevent.get_state() & Clutter.ModifierType.CONTROL_MASK:
            if treeselect.iter_is_selected(marker.treeiter):
                treeselect.unselect_iter(marker.treeiter)
            else:
                treeselect.select_iter(marker.treeiter)
        else:
            treeselect.unselect_all()
            treeselect.select_iter(marker.treeiter)

    def imagemarker_dragged(self, marker, clutterevent, userdata=None):
        # Make sure this is the only image selected, even if the CTRL key was used
        treeselect = self.builder.get_object("treeview1").get_selection()
        treeselect.unselect_all()
        treeselect.select_iter(marker.treeiter)
        lat, lon = (marker.get_latitude(), marker.get_longitude())
        self.tag_selected(lat,lon,None)

    def move_imagemarker(self, tree_iter, filename, lat, lon):
        """
        Move the ImageMarker for the specified image by first removing it and
        then adding a new one.
        TODO: ImageMarkers can be moved by just giving them a new location with
        ImageMarker.set_location(lat, lon)
        so:
            m = get_imagemarker_by_filename(filename)
            if m:
                m.set_location(lat, lon)
        """
        self.remove_imagemarker(filename)
        self.add_imagemarker_at(tree_iter, filename, lat, lon)

    def remove_imagemarker(self, filename):
        """
        Find an ImageMarker by filename and remove (destroy) it
        """
        for m in self.imagelayer.get_markers():
            if m.filename == filename:
                m.destroy()
                break

    def get_imagemarker_by_filename(self, filename):
        """
        Find an ImageMarker by filename and return it. Return None if no marker
        could be found
        """
        for m in self.imagelayer.get_markers():
            if m.filename == filename:
                return m
        return None

    def toggle_imagemarker_draggable(self, widget=None):
        self.update_imagemarker_appearance()
