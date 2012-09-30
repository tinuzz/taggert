#!/usr/bin/env python

# To run this example, you need to set the GI_TYPELIB_PATH environment
# variable to point to the gir directory:
#
# export GI_TYPELIB_PATH=$GI_TYPELIB_PATH:/usr/local/lib/girepository-1.0/

from gi.repository import GtkClutter   # apt-get install gir1.2-clutter-1.0
GtkClutter.init([])
from gi.repository import GObject, Gtk, GtkChamplain  # apt-get install gir1.2-gtkchamplain-0.12

GObject.threads_init()
GtkClutter.init([])

window = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
window.connect("destroy", Gtk.main_quit)

widget = GtkChamplain.Embed()
widget.set_size_request(640, 480)

view = widget.get_view()
view.center_on(51.436035, 5.47840)
view.set_zoom_level(13)

window.add(widget)
window.show_all()

Gtk.main()
