#!/usr/bin/env python3

from gi.repository import GLib
import os
import config

class ScreensaverPluginConfig:
    def __init__(self, name):
        self.default_settings = GLib.KeyFile()
        self.name = name

        try:
            os.makedirs(os.path.join(GLib.get_user_config_dir(), "cinnamon-screensaver"))
        except:
            pass

        try:
            default_path = os.path.join(config.pkgdatadir, "screensaver-plugin-settings.defaults")
            self.default_settings.load_from_file(default_path,
                                                 GLib.KeyFileFlags.KEEP_COMMENTS)
        except GLib.Error:
            pass

        self.user_settings = GLib.KeyFile()
        self.user_path = os.path.join(GLib.get_user_config_dir(), "cinnamon-screensaver", "screensaver-plugin-settings.conf")

        if os.path.exists(self.user_path):
            try:
                self.user_settings.load_from_file(self.user_path,
                                                  GLib.KeyFileFlags.KEEP_COMMENTS)
            except GLib.Error:
                print("Error loading user settings")

    def get_default_command_line(self):
        if self.default_settings.has_group(self.name):
            try:
                return self.default_settings.get_string(self.name, "CommandLine")
            except:
                pass

        return ""

    def get_command_line(self):
        if self.user_settings.has_group(self.name):
            try:
                return self.user_settings.get_string(self.name, "CommandLine")
            except:
                pass
        else:
            return self.get_default_command_line()

    def set_command_line(self, command_line):
        self.user_settings.set_string(self.name, "CommandLine", command_line)

    def set_to_default(self):
        self.user_settings.set_string(self.name, "CommandLine", self.get_default_command_line())

    def save(self):
        try:
            if os.path.exists(self.user_path):
                os.remove(self.user_path)

            self.user_settings.save_to_file(self.user_path)
        except GLib.Error as e:
            print("Could not save configuration", e.message)
