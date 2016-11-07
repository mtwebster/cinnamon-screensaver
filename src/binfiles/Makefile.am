## We require new-style dependency handling.
AUTOMAKE_OPTIONS = 1.7

SUBDIRS=

NULL =

%:%.in Makefile
	$(AM_V_GEN)sed                  \
        -e s!\@datadir\@!$(datadir)!        \
        < $< > $@

all-local: cinnamon-screensaver cinnamon-screensaver-command cinnamon-screensaver-plugin-configure

bin_SCRIPTS = cinnamon-screensaver cinnamon-screensaver-command cinnamon-screensaver-plugin-configure

EXTRA_DIST =                \
    cinnamon-screensaver.in \
    cinnamon-screensaver-command.in \
    cinnamon-screensaver-plugin-configure.in \
    $(NULL)

MAINTAINERCLEANFILES =          \
    *~              \
    Makefile.in

-include $(top_srcdir)/git.mk
