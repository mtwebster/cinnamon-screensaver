#!/usr/bin/python3

from gi.repository import Gio, GObject, CScreensaver

from dbusdepot.baseClient import BaseClient
import status

class MuffinClient(BaseClient):
    MUFFIN_SERVICE = "org.cinnamon.Muffin.DisplayConfig"
    MUFFIN_PATH    = "/org/cinnamon/Muffin/DisplayConfig"

    __gsignals__ = {
        'muffin-config-changed': (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self):
        super(MuffinClient, self).__init__(Gio.BusType.SESSION,
                                           CScreensaver.MuffinDisplayConfigProxy,
                                           self.MUFFIN_SERVICE,
                                           self.MUFFIN_PATH)
        self.using_fractional_scaling = False
        # TODO
        # self.monitors, etc.. replace or at least prefer this over CsScreen, as it will be more accurate.


    def on_client_setup_complete(self):
        self.read_current_state()

        self.proxy.connect("monitors-changed", self.on_monitors_changed)
        # cinnamon restart (monitors-changed isn't emitted at muffin startup)
        self.proxy.connect("notify::g-name-owner", self.on_name_owner_changed)

    def on_monitors_changed(self, proxy):
        self.update()

    def on_name_owner_changed(self, proxy, pspec):
        if proxy.get_name_owner() is not None:
            self.update()

    def update(self):
        self.read_current_state()
        self.emit("muffin-config-changed")

    def read_current_state(self, *args):
        try:
            serial, monitors, logical_monitors, properties = self.proxy.call_get_current_state_sync(None)
        except Exception as e:
            print("Could not read current state from Muffin: %s", e.message)
            self.using_fractional_scaling = False

        fractional = False

        for monitor in logical_monitors.unpack():
            x, y, scale, transform, primary, monitors, properties = monitor

            if int(scale) != scale:
                fractional = True
                break

        self.using_fractional_scaling = fractional

        if status.Debug:
            print("Fractional scaling active:", self.using_fractional_scaling)

    def on_failure(self, *args):
        print("Failed to connect to Muffin - screensaver is not able to detect fractional scaling.")

    def get_using_fractional_scaling(self):
        if self.proxy is None:
            return True

        return self.using_fractional_scaling
