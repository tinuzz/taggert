from gi.repository import Champlain

class ImageMarker(Champlain.Point):

    def __init__(self, treeiter, filename, lat, lon, clicked):
        Champlain.Point.__init__(self)
        self.filename = filename
        self.treeiter = treeiter
        self.set_location(lat, lon)
        self.set_selectable(True)
        #self.set_draggable(True)
        self.set_property('reactive', True)
        self.connect('button-press', clicked)
