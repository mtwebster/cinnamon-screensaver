NULL =
SUBDIRS = icons

desktopdir = $(datadir)/applications
desktop_DATA = cinnamon-screensaver.desktop

cinnamon-screensaver.desktop: cinnamon-screensaver.desktop.in
	$(AM_V_GEN)$(MSGFMT) --desktop --template $< -d $(localedir) -o $@

dbussessionservicedir = $(DBUS_SESSION_SERVICE_DIR)
dbussessionservice_DATA = org.cinnamon.ScreenSaver.service

EXTRA_DIST = 				\
    cinnamon-screensaver.desktop.in \
	org.cinnamon.ScreenSaver.service.in \
	$(NULL)

CLEANFILES =                \
    cinnamon-screensaver.desktop

MAINTAINERCLEANFILES =			\
	*~				\
	Makefile.in

-include $(top_srcdir)/git.mk
