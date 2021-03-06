#    Copyright (C) 2006, 2007, 2008 One Laptop Per Child
#    Copyright (C) 2009 Simon Schampijer, Aleksey Lim
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

# activate threads for gst needs
import gobject
gobject.threads_init()

import locale
locale.setlocale(locale.LC_NUMERIC, 'C')

import logging
_logger = logging.getLogger('memorize-activity')

from gettext import gettext as _
from os.path import join, dirname

import gtk
import telepathy
import telepathy.client

from sugar.activity.activity import Activity, ActivityToolbox
from sugar.presence import presenceservice
from sugar.presence.tubeconn import TubeConnection

from sugar import profile
import cardtable
import scoreboard
import game
import messenger
import memorizetoolbar
import createtoolbar
import accessibilitytoolbar
import cardlist
import createcardpanel
import face

SERVICE = 'org.laptop.Memorize'
IFACE = SERVICE
PATH = '/org/laptop/Memorize'

_TOOLBAR_PLAY = 1
_TOOLBAR_CREATE = 3

class MemorizeActivity(Activity):
    
    def __init__(self, handle):
        Activity.__init__(self, handle)

        self.create_load = False
        self.play_mode = None
        
        toolbox = ActivityToolbox(self)
        activity_toolbar = toolbox.get_activity_toolbar()

        self._memorizeToolbar = memorizetoolbar.MemorizeToolbar(self)
        toolbox.add_toolbar(_('Play'), self._memorizeToolbar)
        self._memorizeToolbar.show()
        
        self._accessibility_toolbar = accessibilitytoolbar.AccessibilityToolbar(self)
        toolbox.add_toolbar(_('Accessibility'), self._accessibility_toolbar)
        self._accessibility_toolbar.show()
        
        self._createToolbar = createtoolbar.CreateToolbar(self)
        toolbox.add_toolbar(_('Create'), self._createToolbar)
        self._createToolbar.show()
        
        self.set_toolbox(toolbox)
        toolbox.show()
        
        # Play game mode
        self.table = cardtable.CardTable()
        self.scoreboard = scoreboard.Scoreboard()
        self.game = game.MemorizeGame()

        self.table.connect('key-press-event', self.table.key_press_event)
        self.table.connect('card-flipped', self.game.card_flipped)
        self.table.connect('card-overflipped', self.game.card_overflipped)
        self.table.connect('card-highlighted', self.game.card_highlighted)

        self.game.connect('set-border', self.table.set_border)
        self.game.connect('flop-card', self.table.flop_card)
        self.game.connect('flip-card', self.table.flip_card)
        self.game.connect('cement-card', self.table.cement_card)
        self.game.connect('highlight-card', self.table.highlight_card)
        self.game.connect('load_mode', self.table.load_msg)

        self.game.connect('msg_buddy', self.scoreboard.set_buddy_message)
        self.game.connect('add_buddy', self.scoreboard.add_buddy)
        self.game.connect('rem_buddy', self.scoreboard.rem_buddy)
        self.game.connect('increase-score', self.scoreboard.increase_score)
        self.game.connect('wait_mode_buddy', self.scoreboard.set_wait_mode)
        self.game.connect('change-turn', self.scoreboard.set_selected)
        self.game.connect('change_game', self.scoreboard.change_game)

        self.game.connect('reset_scoreboard', self.scoreboard.reset)
        self.game.connect('reset_table', self.table.reset)

        self.game.connect('load_game', self.table.load_game)
        self.game.connect('change_game', self.table.change_game)
        self.game.connect('load_game', self._memorizeToolbar.update_toolbar)
        self.game.connect('change_game', self._memorizeToolbar.update_toolbar)
        
        self._memorizeToolbar.connect('game_changed', self.game.change_game)
        self._accessibility_toolbar.connect('accessibility_changed', self.table.accessibility_changed)
        
        self.hbox = gtk.HBox(False)
        self.set_canvas(self.hbox)

        # connect to the in/out events of the memorize activity
        self.connect('focus_in_event', self._focus_in)
        self.connect('focus_out_event', self._focus_out)
        self.connect('destroy', self._cleanup_cb)

        self.add_events(gtk.gdk.POINTER_MOTION_MASK)
        self.connect('motion_notify_event',
                lambda widget, event: face.look_at())

        # start on the game toolbar, might change this
        # to the create toolbar later
        self.toolbox.connect('current-toolbar-changed', self.change_mode)
        self.toolbox.set_current_toolbar(_TOOLBAR_PLAY)

        # Get the Presence Service
        self.pservice = presenceservice.get_instance()
        self.initiating = None
            
        # Buddy object for you
        owner = self.pservice.get_owner()
        self.owner = owner
        self.current = 0
        
        self.game.set_myself(self.owner)  
        self.connect('shared', self._shared_cb)
        
        # Owner.props.key
        if self._shared_activity:
            # We are joining the activity
            self.connect('joined', self._joined_cb)
            if self.get_shared():
                # We've already joined
                self._joined_cb()
        else:
            _logger.debug('buddy joined - __init__: %s', self.owner.props.nick)
            game_file = join(dirname(__file__), 'demos', 'addition.zip')
            self.game.load_game(game_file, 4, 'demo')
            _logger.debug('loading conventional')       
            self.game.add_buddy(self.owner)
        self.show_all()
        
    def read_file(self, file_path):
        if self.metadata['mime_type'] == 'application/x-memorize-project':
            self.toolbox.set_current_toolbar(_TOOLBAR_PLAY)
            if self.metadata.has_key('icon-color'):
                color = self.metadata['icon-color']
            else:
                color = profile.get_color().to_string()
            self.game.change_game(None, file_path, 4, 'file',
                                  self.metadata['title'], color)

    def change_mode(self, notebook, index):
        if index == _TOOLBAR_CREATE:
            if not self.create_load:
                # Create game mode
                self.cardlist = cardlist.CardList()
                self.createcardpanel = createcardpanel.CreateCardPanel()
                self.createcardpanel.connect('add-pair', self.cardlist.add_pair)
                self.createcardpanel.connect('update-pair',
                                             self.cardlist.update_selected)
                self.cardlist.connect('pair-selected',
                                      self.createcardpanel.pair_selected)
                self.cardlist.connect('update-create-toolbar',
                                      self._createToolbar.update_create_toolbar)
                self.cardlist.connect('update-create-buttons',
                                      self._createToolbar.update_buttons_status)
                self._createToolbar.connect('create_new_game',
                                            self.cardlist.clean_list)
                self._createToolbar.connect('create_new_game',
                                            self.createcardpanel.clean)
                self._createToolbar.connect('create_load_game',
                                            self.cardlist.load_game)
                self._createToolbar.connect('create_save_game',
                                            self.cardlist.save_game)
                self._createToolbar.connect('create_equal_pairs', \
                        self.createcardpanel.change_equal_pairs)
                self.create_load = True
 
            self.hbox.remove(self.scoreboard)
            self.hbox.remove(self.table)
            self.hbox.pack_start(self.createcardpanel, False)
            self.hbox.pack_start(self.cardlist)
            self.play_mode = False

        else:
            if self.play_mode == False:
                self.hbox.remove(self.createcardpanel)
                self.hbox.remove(self.cardlist)
            if self.play_mode in (False, None):
                self.hbox.pack_start(self.scoreboard)
                self.hbox.pack_start(self.table, False)
            self.play_mode = True
                
    def restart(self, widget):
        self.game.reset()

    def change_game(self, game_name, size, title=None, color=None):
        self.game.change_game(game_name, size, title, color)
        
    def _shared_cb(self, activity):
        _logger.debug('My activity was shared')
        self.initiating = True
        self._sharing_setup()

        _logger.debug('This is my activity: making a tube...')
        id_ = self.tubes_chan[telepathy.CHANNEL_TYPE_TUBES].OfferDBusTube(
            SERVICE, {})

    def _sharing_setup(self):
        if self._shared_activity is None:
            _logger.error('Failed to share or join activity')
            return
        self.conn = self._shared_activity.telepathy_conn
        self.tubes_chan = self._shared_activity.telepathy_tubes_chan
        self.text_chan = self._shared_activity.telepathy_text_chan
        
        self.tubes_chan[telepathy.CHANNEL_TYPE_TUBES].connect_to_signal( \
                'NewTube', self._new_tube_cb)
        
        self._shared_activity.connect('buddy-joined', self._buddy_joined_cb)
        self._shared_activity.connect('buddy-left', self._buddy_left_cb)

    def _list_tubes_reply_cb(self, tubes):
        for tube_info in tubes:
            self._new_tube_cb(*tube_info)

    def _list_tubes_error_cb(self, e):
        _logger.error('ListTubes() failed: %s', e)

    def _joined_cb(self, activity):
        if not self._shared_activity:
            return

        _logger.debug('Joined an existing shared activity')

        for buddy in self._shared_activity.get_joined_buddies():
            if buddy != self.owner:
                _logger.debug("buddy joined - _joined_cb: %s  "
                              "(get buddies and add them to my list)",
                              buddy.props.nick)
                self.game.add_buddy(buddy)

        self.game.add_buddy(self.owner)
        self.initiating = False
        self._sharing_setup()

        _logger.debug('This is not my activity: waiting for a tube...')
        self.tubes_chan[telepathy.CHANNEL_TYPE_TUBES].ListTubes(
            reply_handler=self._list_tubes_reply_cb, 
            error_handler=self._list_tubes_error_cb)

    def _new_tube_cb(self, identifier, initiator, tube_type, service,
                     params, state):
        _logger.debug('New tube: ID=%d initator=%d type=%d service=%s '
                     'params=%r state=%d', identifier, initiator, tube_type,
                      service, params, state)

        if (tube_type == telepathy.TUBE_TYPE_DBUS and
            service == SERVICE):
            if state == telepathy.TUBE_STATE_LOCAL_PENDING:
                self.tubes_chan[telepathy.CHANNEL_TYPE_TUBES].AcceptDBusTube( \
                        identifier)

            self.tube_conn = TubeConnection(self.conn, 
                self.tubes_chan[telepathy.CHANNEL_TYPE_TUBES], identifier,
                group_iface=self.text_chan[telepathy.CHANNEL_INTERFACE_GROUP])

            self.messenger = messenger.Messenger(self.tube_conn,
                                                 self.initiating,
                                                 self._get_buddy, self.game)
            self.game.connect('flip-card-signal', self.messenger.flip_sender)
            self.game.connect('change_game_signal', self.messenger.change_game)

    def _get_buddy(self, cs_handle):
        """Get a Buddy from a channel specific handle."""
        group = self.text_chan[telepathy.CHANNEL_INTERFACE_GROUP]
        my_csh = group.GetSelfHandle()
        if my_csh == cs_handle:
            handle = self.conn.GetSelfHandle()
        else:
            handle = group.GetHandleOwners([cs_handle])[0]
            assert handle != 0
        return self.pservice.get_buddy_by_telepathy_handle( \
                self.tp_conn_name, self.tp_conn_path, handle)
             
    def _buddy_joined_cb (self, activity, buddy):
        if buddy != self.owner:
            if buddy.props.nick == '':
                _logger.debug("buddy joined: empty nick=%s. Will not add.",
                              buddy.props.nick)
            else:
                _logger.debug("buddy joined: %s", buddy.props.nick)
                self.game.add_buddy(buddy)

    def _buddy_left_cb (self, activity, buddy):
        if buddy.props.nick == '':
            _logger.debug("buddy joined: empty nick=%s. Will not remove",
                          buddy.props.nick)
        else:
            _logger.debug("buddy left: %s", buddy.props.nick)
            self.game.rem_buddy(buddy)

    def _focus_in(self, event, data=None):
        self.game.audio.play()
        
    def _focus_out(self, event, data=None):
        self.game.audio.pause()
        
    def _cleanup_cb(self, data=None):        
        self.game.audio.stop()        
