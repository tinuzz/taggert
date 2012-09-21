pygtk-geotagger
===============

PyGTK Geotagging application

This application is intended to become an easy-to-use geotagging application.
It is written in Python, using PyGTK [1], osm-gps-map [2] and pyexiv2 [3]. It
will support multiple online maps, like OpenStreetMap, OpenCycleMap and
maybe even Google Maps.

The idea is simple:
1. Select a directory containing JPG files
2. Optionally, select a GPX file containing a GPS track
3. Select a file, place a marker on the map
4. Repeat 3 until done
5. Save changes, updating the EXIF tags on the files

Please refer to the changelog below to see what has been implemented so far.
This project also serves as a learning excercise for me as a programmer. This
is my first PyGTK program. The first code is based on the 'mapviewer.py'
example that comes with osm-gps-map [4].

This program was created by Martijn Grendelman <m@rtijn.net>
Mapviewer.py is copyright (C) Hadley Rich 2008 <hads@nice.net.nz>


[1] http://pygtk.org/
[2] http://www.johnstowers.co.nz/blog/index.php/tag/osmgpsmap/
[3] http://tilloy.net/dev/pyexiv2/index.html
[4] https://github.com/nzjrs/osm-gps-map/blob/master/examples/mapviewer.py


Changelog:

2012-09-21 - Create a second column in the file list, displaying the EXIF
             DateTime
2012-09-20 - Take 'mapviewer.py' and add some GTK widgets, like menubar and file
					   list. The directory with JPG files is hardcoded, until a
             'Open directory' dialog has been added.
