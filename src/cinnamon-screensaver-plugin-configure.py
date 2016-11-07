#!/usr/bin/env python3

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gio, GLib
import sys
import os
import argparse
import signal
import gettext

from util.screensaverPluginConfig import ScreensaverPluginConfig

signal.signal(signal.SIGINT, signal.SIG_DFL)
gettext.install("cinnamon-screensaver", "/usr/share/locale")

class PluginConfigureWindow:
    def __init__(self):
        parser = argparse.ArgumentParser(description="Cinnamon Screensaver Plugin Configurator")
        parser.add_argument("--hack", action="store", help="xscreensaver hack to load")
        self.args = parser.parse_args()

        if (self.args.hack):
            hack = self.args.hack
        else:
            settings = Gio.Settings.new(schema_id="org.cinnamon.desktop.screensaver")
            hack = settings.get_string("xscreensaver-hack")

        self.config = ScreensaverPluginConfig(hack)
        self.hack_help_string = self.load_hack_string(hack)

        self.window = Gtk.Window()
        self.window.set_default_size(800, 600)
        self.window.connect("delete-event", Gtk.main_quit)

        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.window.add(self.box)

        sw = Gtk.ScrolledWindow()
        view = Gtk.TextView()
        view.get_buffer().set_text(self.hack_help_string)
        view.set_editable(False)
        sw.add(view)

        self.box.pack_start(sw, True, True, 2)

        self.hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        self.box.pack_start(self.hbox, False, False, 2)

        label = Gtk.Label()
        label.set_markup("<i><b>%s</b></i>" % hack)

        self.hbox.pack_start(label, False, False, 4)

        self.arg_entry = Gtk.Entry()
        self.arg_entry.set_placeholder_text(_("Construct arguments for %s here...") % hack)
        self.arg_entry.set_text(self.config.get_command_line())

        self.hbox.pack_start(self.arg_entry, True, True, 2)

        self.default_button = Gtk.Button.new_with_label(_("Reset to default"))
        self.default_button.connect("clicked", self.on_default_clicked)
        self.hbox.pack_end(self.default_button, False, False, 2)

        self.save_button = Gtk.Button.new_from_stock("gtk-save")
        self.save_button.connect("clicked", self.on_save_clicked)
        self.hbox.pack_end(self.save_button, False, False, 2)

        self.box.show_all()
        self.window.present()

    def on_save_clicked(self, widget):
        self.config.set_command_line(self.arg_entry.get_text())
        self.config.save()

    def on_default_clicked(self, widget):
        self.config.set_to_default()
        self.config.save()
        self.arg_entry.set_text(self.config.get_command_line())

    def load_hack_string(self, hack):
        ret = ""

        directories = ["/usr/lib/xscreensaver",
                       "/usr/libexec/xscreensaver",
                       "/usr/local/lib/xscreensaver",
                       "/usr/local/libexec/xscreensaver"]

        success = False

        for direc in directories:
            path = os.path.join(direc, hack)

            if os.path.exists(path):
                try:
                    success, stdout, stderr, status = GLib.spawn_command_line_sync("man %s" % hack)
                    ret = stdout.decode()
                    break
                except GLib.Error:
                    print("Could not load manpage")
                    break

        return ret

    def on_terminate(self, data=None):
        Gtk.main_quit()

if __name__ == "__main__":
    PluginConfigureWindow()
    Gtk.main()

