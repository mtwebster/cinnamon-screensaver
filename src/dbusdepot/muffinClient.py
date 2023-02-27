#!/usr/bin/python3

from gi.repository import GLib, Gio, GObject, CScreensaver, Gdk

import status
from util import trackers

# TODO
# self.monitors, etc.. replace or at least prefer this over CsScreen, as it will be more accurate.
# Nothing currently listens to muffin-config-changed. This class is only used to initialize the event filters.

class MonitorInfo:
    def __init__(self, number, primary, x, y, device_width, device_height, scale, connectors):
        self.number = number
        self.primary = primary
        self.x = x
        self.y = y
        self.device_width = device_width
        self.device_height = device_height
        self.scale = scale
        self.connectors = connectors

        self.width = int(self.device_width / self.scale)
        self.height = int(self.device_height / self.scale)

    def __repr__(self):
        return f"Logical monitor {self.number}, Is primary: {'Yes' if self.primary else 'No'} Position: {self.x},{self.y}, Physical size: {self.width}x{self.height}, Scale factor: {self.scale}"

    def __eq__(self, other):
        for k in self.__dict__.keys():
            if self.__dict__[k] != other.__dict__[k]:
                return False

        return True

    def __neq__(self, other):
        return not self == other

class MuffinClient(GObject.Object):
    MUFFIN_SERVICE = "org.cinnamon.Muffin.DisplayConfig"
    MUFFIN_PATH    = "/org/cinnamon/Muffin/DisplayConfig"

    __gsignals__ = {
        'muffin-config-changed': (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self):
        GObject.Object.__init__(self)

        self.proxy = None
        self.using_fractional_scaling = False
        self.infos = []
        self.screen_width = 0
        self.screen_height = 0
        self.global_scale = 1

        # trackers.con_tracker_get().connect(status.screen,
        #                                    "size-changed",
        #                                    self.on_cs_config_changed)

        # trackers.con_tracker_get().connect(status.screen,
        #                                    "monitors-changed",
        #                                    self.on_cs_config_changed)

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
            print("Could not connect to Muffin's DisplayConfig service", flush=True)

    def on_monitors_changed(self, proxy):
        if self.update():
            self.emit("muffin-config-changed")

    def on_name_owner_changed(self, proxy, pspec):
        if proxy.get_name_owner() is not None:
            self.on_monitors_changed(self.proxy)
        else:
            self.emit("muffin-config-changed")

    def on_cs_config_changed(self, screen, data=None):
        if self.muffin_active():
            return

        self.emit("muffin-config-changed")

    def muffin_active(self):
         return self.proxy.get_name_owner() is not None

    def update(self):
        if not self.muffin_active():
            return

        try:
            serial, monitors, logical_monitors, properties = self.proxy.call_get_current_state_sync(None)
        except GLib.Error as e:
            print("Could not read current state from Muffin: %s" % e.message, flush=True)
            self.using_fractional_scaling = False
            return self.using_fractional_scaling != old_scaling

        try:
            global_scale = properties["legacy-ui-scaling-factor"]
        except KeyError:
            global_scale = 1

        new_infos, is_fractional = self.new_monitor_info_list(monitors, logical_monitors)
        monitors_changed = len(new_infos) != len(self.infos)

        total = Gdk.Rectangle()
        for i in range(0, len(new_infos)):
            info = new_infos[i]
            mrect = Gdk.Rectangle()
            mrect.x = info.x
            mrect.y = info.y
            mrect.width = info.width
            mrect.height = info.height
            total = total.union(mrect)
            monitors_changed = monitors_changed or info != self.infos[i]

        new_screen_width = total.width
        new_screen_height = total.height

        if global_scale != self.global_scale or \
               monitors_changed or \
               new_screen_width != self.screen_width or \
               new_screen_height != self.screen_height:
            self.global_scale = global_scale
            self.infos = new_infos
            self.screen_width = new_screen_width
            self.screen_height = new_screen_height
            self.using_fractional_scaling = is_fractional
            print("Fractional scaling active: %r" % self.using_fractional_scaling, flush=True)

            return True

        return False

    def new_monitor_info_list(self, monitors, logical_monitors):
        new_infos = []
        is_fractional = False

        connected_monitors = monitors.unpack()

        index = 0
        first_scale = 0
        for monitor in logical_monitors.unpack():
            x, y, scale, transform, primary, real_monitors, properties = monitor
            is_fractional = is_fractional or int(scale) != scale
            if first_scale == 0:
                first_scale = scale
            elif first_scale != scale:
                is_fractional = is_fractional

            device_width, device_height, connectors = self.get_device_pixels_for_logical_monitor(connected_monitors, real_monitors)

            info = MonitorInfo(index, primary, x, y, device_width, device_height, scale, connectors)
            print(info)
            index += 1
            new_infos.append(info)

        return new_infos, is_fractional

    def get_device_pixels_for_logical_monitor(self, connected_monitors, used_real_monitors):
        total_width = 0
        total_height = 0
        connectors = []

        for used_real_monitor in used_real_monitors:
            used_connector, vendor, product, serial = used_real_monitor
            connectors.append(used_connector)

            for connected_monitor in connected_monitors:
                (connected_connector, vendor, product, serial), modes, properties = connected_monitor

                if connected_connector != used_connector:
                    continue

                for mode in modes:
                    mode_id, width, height, refresh, preferred_scale, supported_scales, props = mode

                    for key in props.keys():
                        if key == "is-current" and props[key] == True:
                            total_width += width
                            total_height += height

        if total_width == 0:
            raise Exception("No matching info found")

        return total_width, total_height, connectors

    def get_using_fractional_scaling(self):
        return self.using_fractional_scaling

    def get_n_monitors(self):
        if self.muffin_active():
            return len(self.infos)
        else:
            return status.screen.get_n_monitors()

    def _get_x11_mouse_gdk_monitor(self):
        mm = status.screen.get_mouse_monitor()

        gdk_monitor = Gdk.Display.get_default().get_monitor(mm)
        return gdk_monitor

    def get_mouse_monitor(self):
        gdk_monitor = self._get_x11_mouse_gdk_monitor()

        for i in range(0, len(self.infos)):
            info = self.infos[i]

            if gdk_monitor.get_model() in info.connectors:
                return i

        return 0

    def get_monitor_geometry(self, index):
        ret = Gdk.Rectangle()
        ret.x = self.infos[index].x
        ret.y = self.infos[index].y
        ret.width = self.infos[index].width
        ret.height = self.infos[index].height

        return ret

    def get_low_res_mode(self):
        return status.screen.get_low_res_mode()

    def get_smallest_monitor_sizes(self):
        return status.screen.get_smallest_monitor_sizes()

    def place_pointer_in_primary_monitor(self):
        if self.muffin_active():
            for info in self.infos:
                if info.primary:
                    display = Gdk.Display.get_default()
                    seat = display.get_default_seat()
                    pointer = seat.get_pointer()
                    pointer.warp(display.get_default_screen(),
                                 info.x + info.width * .5,
                                 info.y + info.height * .75)
        else:
            status.screen.place_pointer_in_primary_monitor()

    def get_screen_geometry(self):
        if self.muffin_active:
            rect = Gdk.Rectangle()
            rect.x = rect.y = 0
            rect.width = self.screen_width + 1
            rect.height = self.screen_height + 1

            return rect

        return status.screen.get_screen_geometry()
