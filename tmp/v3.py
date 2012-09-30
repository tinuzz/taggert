#!/usr/bin/python
from gi.repository import Gtk

builder = Gtk.Builder()
builder.add_from_file("poging4.glade")

window = builder.get_object("window1")
window.connect("delete-event", Gtk.main_quit)
window.show_all()
Gtk.main()
