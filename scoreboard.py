#    Copyright (C) 2006, 2007, 2008 One Laptop Per Child
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
#

import gtk
import logging
from playerscoreboard import PlayerScoreboard

_logger = logging.getLogger('memorize-activity')

class Scoreboard(gtk.EventBox):
    def __init__(self):
        gtk.EventBox.__init__(self)

        self.players = {}
        self.current_buddy = None

        self.vbox = gtk.VBox(False)        
        
        fill_box = gtk.EventBox()
        fill_box.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse('#4c4d4f'))
        fill_box.show()
        self.vbox.pack_end(fill_box, True, True)
                   
        scroll = gtk.ScrolledWindow()
        scroll.props.shadow_type = gtk.SHADOW_NONE           
        scroll.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        scroll.add_with_viewport(self.vbox)
        scroll.set_border_width(0)
        scroll.get_child().set_property('shadow-type', gtk.SHADOW_NONE)
        self.add(scroll)
        self.show_all()

    def change_game(self, widget, data, grid):
        for buddy in self.players.keys():
            self.players[buddy].change_game(len(grid))
        
    def add_buddy(self, widget, buddy, score):
        ### FIXME: this breaks when the body is empty
        nick = buddy.props.nick
        stroke_color, fill_color = buddy.props.color.split(',')
        player = PlayerScoreboard(nick, fill_color, stroke_color, score)
        player.show()
        self.players[buddy] = player        
        self.vbox.pack_start(player, False, False)
        if score == -1:
            player.set_wait_mode(True)
        self.show_all()
            
    def rem_buddy(self, widget, buddy):
        self.vbox.remove(self.players[buddy])        
        del self.players[buddy] ### fix for self.players[id]
    
    def set_selected(self, widget, buddy):
        if self.current_buddy is not None:
            old = self.players[self.current_buddy]
            old.set_selected(False)
        self.current_buddy = buddy 
        player = self.players[buddy]
        player.set_selected(True)
    
    def set_buddy_message(self, widget, buddy, msg):
        self.players[buddy].set_message(msg)
        
    def increase_score(self, widget, buddy):
        self.players[buddy].increase_score()

    def reset(self, widget):
        for buddy in self.players.keys():
            self.players[buddy].reset()
            
    def set_wait_mode(self, widget, buddy, status):
        self.players[buddy].set_wait_mode(status)
        
