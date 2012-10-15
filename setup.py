#!/usr/bin/env python

from distutils.core import setup

setup(name="taggert",
	version="1.0",
	author="Martijn Grendelman",
	author_email="m@rtijn.net",
	maintainer="Martijn Grendelman",
	maintainer_email="m@rtijn.net",
	description="GTK+ 3 geotagging application",
	long_description="Taggert is an easy-to-use program to geo-tag your photos, using GPS tracks or manually from a map",
	url="http://www.grendelman.net/wp/tag/taggert",
	license="Apache License version 2.0",
#    package_dir={'taggert': 'taggert'},
    packages=['taggert'],
    scripts=['taggert_run'],
    package_data={'taggert': ['data/*']},
    data_files=[
        ('glib-2.0/schemas', ['com.tinuzz.taggert.gschema.xml']),
        ('applications', ['taggert.desktop']),
        ('pixmaps', ['taggert/data/taggert.svg']),
    ],
)
