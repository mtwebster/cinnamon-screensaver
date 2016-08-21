#! /usr/bin/python3

from gi.repository import Gio, GObject, GLib
import os

import constants as c
import trackers

class UPowerConnectionError(Exception):
    pass

class UPowerProxy(GObject.GObject):
    __gsignals__ = {
        'on-battery-changed': (GObject.SignalFlags.RUN_LAST, None, (bool,)),
        'unlock': (GObject.SignalFlags.RUN_LAST, None, ()),
        'active': (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self):
        super(LogindProxy, self).__init__()

        self.proxy = None

        self.on_battery = False

        try:
            Gio.DBusProxy.new_for_bus(Gio.BusType.SYSTEM, Gio.DBusProxyFlags.NONE, None,
                                      c.UPOWER_SERVICE, c.UPOWER_PATH, c.UPOWER_INTERFACE,
                                      None, self.on_proxy_ready, None)
        except GLib.Error as e:
            print("Could not acquire UPower system proxy", e)
            raise UPowerConnectionError

    def on_proxy_ready(self, object, result, data=None):
        self.proxy = Gio.DBusProxy.new_for_bus_finish(result)
        trackers.con_tracker_get().connect(self.proxy,
                                           "g-signal",
                                           self.on_signal)

        trackers.con_tracker_get().connect(self.proxy,
                                           "g-properties-changed",
                                           self.on_properties_changed)

        self.update_on_battery(self.proxy.OnBattery)

    def on_signal(self, proxy, sender, signal, params):
        return

        if signal == "Unlock":
            self.emit("unlock")
        elif signal == "Lock":
            self.emit("lock")

    def on_properties_changed(self, proxy, changed, invalid):
        on_battery_var = changed.lookup_value("OnBattery", GLib.VariantType("b"))

        if on_battery_var:
            self.update_on_battery(on_battery_var.get_boolean())

    def update_on_battery(self, on_battery):
        self.on_battery = on_battery
        self.emit("on-battery-changed", self.on_battery)

