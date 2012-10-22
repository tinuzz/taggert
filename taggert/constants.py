class ImagesColumns(object):
    filename  = 0
    datetime  = 1
    rotation  = 2
    latitude  = 3
    longitude = 4
    modified  = 5
    camera    = 6
    dtobject  = 7
    elevation = 8

class images(object):
    columns = ImagesColumns()

class TracksColumns(object):
    name      = 0
    starttime = 1
    endtime   = 2
    numpoints = 3
    uuid      = 4
    layer     = 5

class tracks(object):
    columns = TracksColumns()

class NotebookPages(object):
    images    = 0
    tracks    = 1
    points    = 2

class notebook(object):
    pages = NotebookPages()
