#!/usr/bin/python3

import gi
gi.require_version('CScreensaver', '1.0')
from gi.repository import GLib, Gio, GObject, CScreensaver, Gdk

LOW_RES_MONITOR_WIDTH_THRESHOLD = 1200
LOW_RES_MONITOR_HEIGHT_THRESHOLD = 1000

class Monitor():
    def __init__(self, x, y, width, height, scale, is_primary):
        (x, y, width, height, scale, is_primary)
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.scale = scale
        self.is_primary = is_primary

        self.rect = Gdk.Rectangle()
        self.rect.x = x
        self.rect.y = y
        self.rect.width = width
        self.rect.height = height

    def __eq__(self, other):
        """Overrides the default implementation"""
        if not isinstance(other, Monitor):
            return False

        return self.x == other.x and \
            self.y == other.y and \
            self.width == other.width and \
            self.height == other.height and \
            self.scale == other.scale and \
            self.is_primary == other.is_primary

    def get_geo_rect(self):
        return self.rect

    def contains_point(self, x, y):
        return self.x < x < self.x + self.width and \
               self.y < y < self.y + self.height

class MuffinClient(GObject.Object):
    MUFFIN_SERVICE = "org.cinnamon.Muffin.DisplayConfig"
    MUFFIN_PATH = "/org/cinnamon/Muffin/DisplayConfig"

    __gsignals__ = {
        'muffin-config-changed': (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self):
        GObject.Object.__init__(self)

        self.monitors = []

        self.proxy = None
        self.using_fractional_scaling = False
        self.global_scale = 1

        try:
            self.proxy = CScreensaver.MuffinDisplayConfigProxy.new_for_bus_sync(Gio.BusType.SESSION,
                                                                                Gio.DBusProxyFlags.DO_NOT_LOAD_PROPERTIES |
                                                                                    Gio.DBusProxyFlags.DO_NOT_AUTO_START,
                                                                                self.MUFFIN_SERVICE,
                                                                                self.MUFFIN_PATH,
                                                                                None)
            self.proxy.connect("monitors-changed", self.on_monitors_changed)
            # cinnamon restart (monitors-changed isn't emitted at muffin startup)
            self.proxy.connect("notify::g-name-owner", self.on_name_owner_changed)
            self.update()
        except GLib.Error as e:
            print(f"Could not connect to Muffin's DisplayConfig service: {e}", flush=True)

    def on_monitors_changed(self, proxy):
        self.update()

    def on_name_owner_changed(self, proxy, pspec):
        if proxy.get_name_owner() is not None:
            self.update()

    def update(self):
        if self.read_current_state():
            self.emit("muffin-config-changed")

    def read_current_state(self, *args):
        old_scaling = self.using_fractional_scaling

        if self.proxy.get_name_owner() is None:
            print("Muffin not running, skipping fractional scaling check.")
            return False

        try:
            state = self.proxy.call_get_current_state_sync(None)
        except GLib.Error as e:
            print(f"Could not read current state from Muffin: {e}", flush=True)
            return False

        fractional = False
        previous_scale = -1

        global_props = state[3]
        self.global_scale = global_props["legacy-ui-scaling-factor"]

        monitor_defs = state[1]

        for monitor in state[2].unpack():
            x, y, scale, xform, is_primary, physical_monitors, props = monitor

                        # x /= self.global_scale
                        # y /= self.global_scale

            scaled_width = -1
            scaled_height = -1

            for connector, vendor, product, serial in physical_monitors:
                for (mode_con, mode_vendor, mode_product, mode_serial), modes, props in monitor_defs:
                    if mode_con == connector:
                        for mode in modes:
                            _id, width, height, refresh, preferred_scale, supported_scales, mode_props = mode
                            current = mode_props.get("is-current", False)

                            if not current:
                                continue

                            scaled_width = width / scale
                            scaled_height = height / scale
                            break

                if scaled_height != -1 and scaled_width != -1:
                    break

            x /= self.global_scale
            y /= self.global_scale

            m = Monitor(x, y, scaled_width, scaled_height, scale, is_primary)
            self.monitors.append(m)

            # one or more monitors using some non-integer scale.
            if int(scale) != scale:
                fractional = True

            # multiple monitors with non-identical scales (1.00, 2.00)
            if previous_scale > 0 and scale != previous_scale:
                fractional = True

            previous_scale = scale

        self.using_fractional_scaling = fractional

        print(f"Fractional scaling active: {self.using_fractional_scaling}", flush=True)

        return True

    def get_using_fractional_scaling(self):
        return self.using_fractional_scaling

    def get_monitor_geometry(self, monitor):
        try:
            return self.monitors[monitor].get_geo_rect()
        except:
            return None

    def get_screen_geometry(self):
        width = 0
        height = 0

        r = Gdk.Rectangle()

        for monitor in self.monitors:
            mr = Gdk.Rectangle()
            mr.x = monitor.x
            mr.y = monitor.y
            mr.width = monitor.width
            mr.height = monitor.height

            r = r.union(mr)

        return r

    def get_primary_monitor(self):
        i = 0

        for i in range(len(self.monitors)):
            if self.monitors[i].is_primary:
                return i

        return 0

    def get_n_monitors(self):
        return len(self.monitors)

    def get_mouse_monitor(self):
        seat = Gdk.Display.get_default().get_default_seat()
        pointer = seat.get_pointer()

        screen, x, y = pointer.get_position()

        i = 0
        for i in range(len(self.monitors)):
            if self.monitors[i].contains_point(x, y):
                return i

        return 0

    def get_low_res_mode(self):
        for monitor in self.monitors:
            if monitor.width < LOW_RES_MONITOR_WIDTH_THRESHOLD or \
               monitor.height < LOW_RES_MONITOR_HEIGHT_THRESHOLD:
                return True

        return False

    def get_smallest_monitor_sizes(self):
        width = GLib.MAXINT
        height = GLib.MAXINT

        for monitor in self.monitors:
            width = monitor.width if monitor.width < width else width
            height = monitor.height if monitor.height < height else height

        return (width, height)

    def place_pointer_in_primary_monitor(self):
        seat = Gdk.Display.get_default().get_default_seat()
        pointer = seat.get_pointer()

        for monitor in self.monitors:
            if monitor.is_primary:
                pointer.warp(Gdk.Screen.get_default(), monitor.x + monitor.width / 2, monitor.y + monitor.height / 2)
                break

    def get_global_scale(self):
        return self.global_scale

