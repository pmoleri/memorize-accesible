#    Copyright (C) 2010 ceibalJAM! ceibaljam.org
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import gtk
from os.path import join, dirname

from gettext import gettext as _

from sugar import profile

import logging
from gobject import SIGNAL_RUN_FIRST, TYPE_PYOBJECT

_logger = logging.getLogger('memorize-activity')

class AccessibilityToolbar(gtk.Toolbar):
    __gtype_name__ = 'AccessibilityToolbar'
    
    __gsignals__ = {
        'accessibility_changed': (SIGNAL_RUN_FIRST, None, 2 * [TYPE_PYOBJECT]),
    }
    
    def __init__(self, activity):
        gtk.Toolbar.__init__(self)
        self.activity = activity
        self._lock = True
        self.jobject = None
        
        # Accessible mode checkbox
        self._accessible = gtk.CheckButton(_('Accessible'))
        self._accessible.connect('toggled', self._accessibility_changed)
        self._add_widget(self._accessible)
        
        # Scanning speed scale
        min = 1
        max = 5
        step = 1
        default = 2.5
        
        self._speed_adj = gtk.Adjustment(default, min, max, step)
        self._speed_bar = gtk.HScale(self._speed_adj)
        self._speed_bar.set_draw_value(True)
        self._speed_bar.set_update_policy(gtk.UPDATE_DISCONTINUOUS)
        self._speed_bar.set_size_request(240,15)
        self._speed_adj.connect("value_changed", self._accessibility_changed)

        # Add it to the toolbar
        self._add_widget(self._speed_bar)
    
    def _add_widget(self, widget, expand=False):
        tool_item = gtk.ToolItem()
        tool_item.set_expand(expand)
        tool_item.add(widget)
        widget.show()
        self.insert(tool_item, -1)
        tool_item.show()
        
    def _game_reset_cb(self, widget):
        self.emit('game_changed', None, None, 'reset', None, None)
        
    def _load_game(self, button):
        pass
    
    def _accessibility_changed(self, widget):
        self.emit("accessibility_changed", self._accessible.get_active(), self._speed_bar.get_value())
