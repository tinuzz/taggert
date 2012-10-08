Taggert
=======

Taggert is a GTK+ geotagging application, written in Python. It uses PyGObject
and as such needs GTK+ >= 3.0. Taggert is not compatible with GTK+ 2.x.

Usage
-----

The idea behind Taggert is fairly simple:
1. Select a directory containing image files that you want to geo-tag
2. Select a location on the map by setting a marker
3. Select one ore more images in the list
4. Click a button to add the marker's location to the selected images
5. Save your changes

Features
--------

* Offers different free maps to work on, like different Openstreetmap maps,
  MapQuest maps and satellite images and maps-for-free
* Shows a preview of selected images, so you know what you're doing
* Lets you create bookmarks for locations, so you can easily go back to the
	locations that you frequently visit
* Lets you remove tags from images, too
* Uses GSettings to store runtime configuration options

Prerequisites
-------------

The following software is needed to run Taggert:

* Python (developed and currently only tested with v2.7)
* PyGObject    (Debian: python-gi)
* pyexiv2      (Debian: python-pyexiv2, homepage: http://tilloy.net/dev/pyexiv2/)

and the following PyGObject introspection libraries:

* Gtk          (Debian: gir1.2-gtk-3.0:)
* GtkChamplain (Debian: gir1.2-gtkchamplain-0.12)
* Champlain    (Debian: gir1.2-champlain-0.12)
* Clutter      (Debian: gir1.2-clutter-1.0)
* GtkClutter   (Debian: gir1.2-gtkclutter-1.0)
* GLib / Gio   (Debian: gir1.2-glib-2.0)
* GdkPixbuf    (Debian: gir1.2-gdkpixbuf-2.0)

and of course all of the dependencies of these packages, like libexiv2,
libclutter, libchamplain, etc.

Because Taggert uses 'pyexiv2', which hasn't been ported to Python 3, Taggert
requires Python 2.7. Compatibility with Python 2.6 is untested.

Installation
------------

Taggert is not packaged in any form yet, you have to checkout the source code
from Github and you can run it straight from the checked out directory. The
only thing that needs to be installed is the GSettings Schema.

On Debian, copy 'com.tinuzz.taggert.gschema.xml' to /usr/share/glib-2.0/schemas/
and (as root) run 'glib-compile-schemas /usr/share/glib-2.0/schemas'. That
program is part of the 'libglib2.0-bin' package.

When all prerequisites are installed, you should be able to run Taggert:

    ./taggert

Credits
-------

Taggert is written and maintained by Martijn Grendelman <m@rtijn.net>. It was
inspired heavily by GottenGeography [1], written by Robert Bruce Park, and his
code was used as a starting point on some occasions.

The first incarnation of Taggert was based on osm-gps-map [2] rather than
libchamplain and its code was based on the bundled mapviewer example [3],
written by Hadley Rich.

[1] <https://github.com/robru/gottengeography>
[2] <http://nzjrs.github.com/osm-gps-map/>
[3] <https://github.com/nzjrs/osm-gps-map/blob/master/examples/mapviewer.py>


Roadmap
-------

* GPX track support, so you can bulk-tag images from tracks
* Altitude support. So far, EXIF tags dealing with altitude are completely ignored.
* Packaging for Debian and maybe Ubuntu
* Python 3 support

Robert Bruce Park, who created GottenGeography, also created GObject
Introspection data for 'gexiv2', making this GObject wrapper usable from
Python, including version 3. His work has been merged with upstream gexiv2
and should appear in gexiv2 version 0.5.0.

When gexiv2 v0.5.0 or greater is available for Debian, Taggert will be
rewritten to use that, rather than pyexiv2.

[4] <http://redmine.yorba.org/projects/gexiv2/wiki>
