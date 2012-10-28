from gi.repository import GObject

class TData(GObject.GObject):

    imagedir           = GObject.property(type=str)
    lasttrackfolder    = GObject.property(type=str)
    tracktimezone      = GObject.property(type=str)
    alwaysthistimezone = GObject.property(type=bool, default=False)
    markersize         = GObject.property(type=int)
    trackwidth         = GObject.property(type=int)

    def __init__(self):
        GObject.GObject.__init__(self)

    def connect_signals(self, handlers):
        for prop, handler in handlers.items():
            self.connect("notify::%s" % prop, handler)

GObject.type_register(TData)
