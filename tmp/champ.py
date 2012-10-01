#!/usr/bin/env python

# To run this example, you need to set the GI_TYPELIB_PATH environment
# variable to point to the gir directory:
#
# export GI_TYPELIB_PATH=$GI_TYPELIB_PATH:/usr/local/lib/girepository-1.0/

from gi.repository import GtkClutter, Clutter   # apt-get install gir1.2-clutter-1.0
GtkClutter.init([])
from gi.repository import GObject, Gtk, GtkChamplain, Champlain  # apt-get install gir1.2-gtkchamplain-0.12
from gi.repository import Pango

black = Clutter.Color().new(0x00, 0x00, 0x00, 0xff)
red = Clutter.Color().new(0xFF, 0x00, 0x00, 0xff)
blue = Clutter.Color().new(0x00, 0x00, 0xFF, 0xff)

GObject.threads_init()
GtkClutter.init([])

window = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
window.connect("destroy", Gtk.main_quit)

widget = GtkChamplain.Embed()
widget.set_size_request(640, 480)

view = widget.get_view()
view.center_on(51.436035, 5.47840)
view.set_zoom_level(10)
#view.set_property("animate-zoom", False)

markerlayer = Champlain.MarkerLayer()
markerlayer.set_opacity(128)
markerlayer.show()
label = Champlain.Label()
label.set_text('Hallo dan hoe gaat ie daaro en met henk en ze vrouw enzo, gaat ie daar ook goed mee')
label.set_color(red)
label.set_selectable(True)
label.set_draggable(True)
label.set_property("font-name", "Sans 8")
#label.set_property("draw-background", False)
label.set_property("text-color", blue)
label.set_property("ellipsize", Pango.EllipsizeMode.END)
#label.set_property("single-line-mode", False)
#label.set_property("wrap", True)
markerlayer.set_opacity(180)
markerlayer.add_marker(label)
label.set_location(51.436035, 5.47840)
view.add_layer(markerlayer)
#label.set_size(500,500)
#label.animate_in()

window.add(widget)
window.show_all()

h,w = label.get_size()
a,b = label.get_preferred_width(-1)
print "%s %s" % (h,w)
print "%s %s" % (a,b)

Gtk.main()


class MarkerLayer(Champlain.Layer):

    def __init__(self):
        champlain.Layer.__init__(self)
        self.orange = clutter.Color(0xf3, 0x94, 0x07, 0xbb)

        #RGBA
        self.white = clutter.Color(0xff, 0xff, 0xff, 0xff)
        self.black = clutter.Color(0x00, 0x00, 0x00, 0xff)

        self.hide()

    def add_marker(self, text, latitude, longitude, bg_color=None, text_color=None, font="Airmole 8"):
        if not text_color:
            text_color = self.black

        if not bg_color:
            bg_color = self.orange

        marker = champlain.marker_new_with_text(text, font, text_color, bg_color)

        #marker.set_position(38.575935, -7.921326)
        marker.set_position(latitude, longitude)
        self.add(marker)
        return marker
