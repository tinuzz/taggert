import gtk.gdk
import osmgpsmap

class UI(gtk.Window):

    def __init__(self):

        gtk.Window.__init__(self, gtk.WINDOW_TOPLEVEL)
        self.set_default_size(1024, 768)
        self.set_position(gtk.WIN_POS_CENTER)
        self.connect('destroy', lambda x: gtk.main_quit())
        self.set_title('Taggert')

        # main VBox, containing menubar, main window and statusbar
        self.vbox0()

    def vbox0(self):
        self.vbox0 = gtk.VBox(False,0)
        self.add(self.vbox0)

        self.menubar()
        self.vbox0.pack_start(self.menubar, False, False, 0)

        # main HBox, containg filelist on the left and map+controls on the right
        self.hbox0()
        self.vbox0.pack_start(self.hbox0)

        self.statusbar()
        self.vbox0.pack_end(self.statusbar, False)

    def hbox0(self):
        self.hbox0 = gtk.HBox(False, 0)

        self.notebook()
        self.hbox0.pack_start(self.notebook, False)

        # VBox1, containing map selector, map and controls area
        self.vbox1()
        self.hbox0.pack_start(self.vbox1)

    def vbox1(self):
        self.vbox1 = gtk.VBox(False, 0)
        self.combobox0()
        self.vbox1.pack_start(self.combobox0, False, False)
        self.osm()
        self.vbox1.pack_start(self.osm)
        self.hbox1()
        self.vbox1.pack_end(self.hbox1, False)

    def hbox1(self):
        self.hbox1 = gtk.HBox(False, 0)

        self.frame0()
        self.hbox1.pack_start(self.frame0, False)

        self.frame1()
        self.hbox1.pack_start(self.frame1, True)

    def menubar(self):
        self.menubar = gtk.MenuBar()

        self.menubaritem0 = gtk.MenuItem("File")
        self.menubar.append(self.menubaritem0)
        self.filemenu()

        self.menubaritem1 = gtk.MenuItem("Bookmarks")
        self.menubar.append(self.menubaritem1)
        self.bookmarksmenu()

        self.menubaritem2 = gtk.MenuItem("Help")
        self.menubar.append(self.menubaritem2)
        self.helpmenu()

    def filemenu(self):

        self.filemenu = gtk.Menu()
        self.menubaritem0.set_submenu(self.filemenu)

        menuitem = gtk.ImageMenuItem(gtk.STOCK_DIRECTORY)
        menuitem.set_label("Select image folder")
        self.filemenu.append(menuitem)

        sep = gtk.SeparatorMenuItem()
        self.filemenu.append(sep)

        menuitem = gtk.ImageMenuItem(gtk.STOCK_QUIT)
        menuitem.connect("activate", gtk.main_quit)
        self.filemenu.append(menuitem)

    def bookmarksmenu(self):
        self.bookmarksmenu = gtk.Menu()
        self.menubaritem1.set_submenu(self.bookmarksmenu)

        menuitem = gtk.ImageMenuItem(gtk.STOCK_HOME)
        self.bookmarksmenu.append(menuitem)

        sep = gtk.SeparatorMenuItem()
        self.bookmarksmenu.append(sep)

    def helpmenu(self):
        self.helpmenu = gtk.Menu()
        self.menubaritem2.set_submenu(self.helpmenu)

    def notebook(self):
        self.treeview0()

        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        sw.add(self.treeview0)

        label0 = gtk.Label("Images")

        self.notebook = gtk.Notebook()
        self.notebook.set_tab_pos(gtk.POS_TOP)
        #self.notebook.set_size_request(360, -1)
        self.notebook.append_page(sw, label0)

    def treeview0(self):
        self.treeview0 = gtk.TreeView()
        self.treeview0_selection = self.treeview0.get_selection()
        self.treeview0_selection.set_mode(gtk.SELECTION_MULTIPLE)
        self.treeview0.set_grid_lines(gtk.TREE_VIEW_GRID_LINES_HORIZONTAL)

        cell = gtk.CellRendererText()
        #cell.set_property('cell-background', 'cyan')
        col0 = gtk.TreeViewColumn('Filename', cell, text=0)
        col0.set_min_width(180)
        col0.set_sort_column_id(0)
        self.treeview0.append_column(col0)

        cell = gtk.CellRendererText()
        #cell.set_property('cell-background', 'cyan')
        col1 = gtk.TreeViewColumn('EXIF DateTime', cell, text=1)
        col1.set_min_width(140)
        col1.set_sort_column_id(1)
        self.treeview0.append_column(col1)

        cell = gtk.CellRendererText()
        col3 = gtk.TreeViewColumn('Lat', cell, text=3)
        self.treeview0.append_column(col3)

        cell = gtk.CellRendererText()
        col4 = gtk.TreeViewColumn('Lon', cell, text=4)
        self.treeview0.append_column(col4)

    def combobox0(self):
        self.combobox0 = gtk.combo_box_new_text()
        self.combobox0.append_text("OpenStreetMap")
        self.combobox0.append_text("Google Maps")
        self.combobox0.append_text("MapQuest OSM")
        self.combobox0.append_text("MapQuest Open Aerial")
        self.combobox0.append_text("OpenCycleMap")
        self.combobox0.append_text("Google Aerial")
        self.combobox0.append_text("Google Aerial with streets")
        self.combobox0.append_text("Google Terrain")
        self.combobox0.append_text("Google Terrain with streets")
        self.combobox0.set_active(0)

    def osm(self):
        self.osm = osmgpsmap.GpsMap()

    def statusbar(self):
        self.statusbar = gtk.Statusbar()
        self.statusbar.set_has_resize_grip(False)

    def frame0(self):
        self.frame0 = gtk.Frame('Image preview')
        self.frame0.set_size_request(314, 225)
        self.frame0.set_border_width(3)

        self.preview = gtk.image_new_from_stock(gtk.STOCK_MISSING_IMAGE, gtk.ICON_SIZE_LARGE_TOOLBAR)
        self.preview.set_padding(2,2)
        self.frame0.add(self.preview)

    def frame1(self):
        self.frame1 = gtk.Frame('Actions')
        self.frame1.set_border_width(3)
        self.hbox2()
        self.frame1.add(self.hbox2)

    def hbox2(self):
        self.hbox2 = gtk.HBox()
        self.actionbuttons()
        self.hbox2.pack_start(self.vbox2)
        self.hbox2.pack_start(self.vbox3)

    def actionbuttons(self):
        self.vbox2 = gtk.VBox()
        self.vbox3 = gtk.VBox()

        self.button0 = gtk.Button("Tag manually")
        self.button0.set_border_width(3)
        self.button0.set_sensitive(False)
        self.vbox2.pack_start(self.button0, False, False)

        button1 = gtk.Button("Remove tags")
        button1.set_border_width(3)
        self.vbox3.pack_start(button1, False, False)

        self.button2 = gtk.Button("Go to target")
        self.button2.set_border_width(3)
        self.button2.set_sensitive(False)
        self.vbox2.pack_start(self.button2, False, False)

