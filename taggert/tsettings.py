from gi.repository import Gio

class TSettings(Gio.Settings):

    def __init___(self, schema):
        Gio.Settings.__init__(self, schema)

    # Convenience method, taken from GottenGeography
    def bind(self, key, widget, prop=None, flags=Gio.SettingsBindFlags.DEFAULT):
        Gio.Settings.bind(self, key, widget, prop or key, flags)
