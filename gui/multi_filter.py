# Copyright 2008 Dana-Farber Cancer Institute
# multiplierz is distributed under the terms of the GNU Lesser General Public License
#
# This file is part of multiplierz.
#
# multiplierz is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# multiplierz is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with multiplierz.  If not, see <http://www.gnu.org/licenses/>.

import wx
import os
import re

import multiplierz.mzTools

from mzDesktop import myData
from mzGUI import report_chooser

from gui import BasicTab

class MultiFilterPanel(BasicTab):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)

        self.default_dir = myData

        gbs = wx.GridBagSizer(12, 5)

        gbs.Add( wx.StaticText(self, -1, 'Files to Filter'),
                 (0,1), flag=wx.ALIGN_CENTER_VERTICAL)

        add_files_btn = wx.Button(self, -1, 'Add')
        gbs.Add( add_files_btn,
                 (1,0) )
        add_files_btn.Bind(wx.EVT_BUTTON, self.on_click_add)

        remove_files_btn = wx.Button(self, -1, 'Remove')
        gbs.Add( remove_files_btn,
                 (2,0) )
        remove_files_btn.Bind(wx.EVT_BUTTON, self.on_click_remove)

        clear_files_btn = wx.Button(self, -1, 'Clear')
        gbs.Add( clear_files_btn,
                 (3,0) )
        clear_files_btn.Bind(wx.EVT_BUTTON, self.on_click_clear)

        self.file_list = wx.ListBox(self, -1, choices=[], style=wx.LB_SORT|wx.LB_MULTIPLE|wx.LB_HSCROLL)
        gbs.Add( self.file_list,
                 (1,1), (3,2), flag=wx.EXPAND )

        gbs.Add( wx.StaticText(self, -1, 'Reference File\nOf Keys to Match', style=wx.ALIGN_RIGHT),
                 (4,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT )

        self.source_file_text = wx.TextCtrl(self, -1, '')
        gbs.Add( self.source_file_text,
                 (4,1), flag=wx.EXPAND)

        write_file_btn = wx.Button(self, -1, 'Browse')
        gbs.Add( write_file_btn,
                 (4,2) )
        write_file_btn.Bind(wx.EVT_BUTTON, self.on_click_source)

        gbs.Add( wx.StaticText(self, -1, "Include or Exclude Filter Keys", style=wx.ALIGN_CENTER),
                 (5,0), (1,3), flag=wx.ALIGN_CENTER )

        self.category_radio = wx.RadioBox(self, -1, "", choices=['Include', 'Exclude'], style=wx.RA_SPECIFY_COLS)
        self.category_radio.SetSelection(0)
        gbs.Add( self.category_radio,
                 (6,0), (1,3), flag=wx.ALIGN_CENTER )

        self.append_ck = wx.CheckBox(self, -1, "Combine Into One File  ", style=wx.ALIGN_RIGHT)
        gbs.Add( self.append_ck,
                 (7,0), (1,3), flag=wx.ALIGN_CENTER )

        #Submit Button
        filter_btn = wx.Button(self, -1, 'Filter', size=(160,-1))
        gbs.Add( filter_btn,
                 (8,0), (1,3), flag=wx.ALIGN_CENTER )
        filter_btn.Bind(wx.EVT_BUTTON, self.on_click_filter)

        gbs.AddGrowableCol(1)
        gbs.AddGrowableRow(3)

        box = wx.BoxSizer()
        box.Add(gbs, 1, wx.ALL|wx.EXPAND, 20)
        self.SetSizerAndFit(box)

    def on_click_add(self, event):
        file_names = report_chooser(self, mode='m')
        if file_names:
            self.default_dir = os.path.dirname(file_names[0])
            self.file_list.Set(sorted(set(self.file_list.GetStrings() + file_names)))

    def on_click_remove(self, event):
        remove = self.file_list.GetSelections()
        files = [f for i,f in enumerate(self.file_list.GetStrings()) if i not in remove]
        self.file_list.Set(files)

    def on_click_clear(self, event):
        self.file_list.Clear()

    def on_click_source(self, event):
        file_name = report_chooser(self, 'Choose Source File:', defaultDir=self.default_dir)
        if file_name:
            self.source_file_text.SetValue(file_name)

    def on_click_filter(self, event):
        if not self.file_list.GetStrings():
            wx.MessageBox('No files selected', 'Error')
            return

        #show hourglass
        wx.BeginBusyCursor(wx.HOURGLASS_CURSOR)

        files = self.file_list.GetStrings()
        key_source_file = self.source_file_text.GetValue()
        selection = self.category_radio.GetSelection()
        append = self.append_ck.GetValue()

        #update statusbar
        self.set_status("Filtering ...",0)
        self.set_status("",1)

        from mzDesktop import settings

        multiplierz.mzTools.multifile.filter_join(files,
                                                  key_source_file,
                                                  selection,
                                                  append,
                                                  ext = settings.get_default_format())

        #hide hourglass
        wx.EndBusyCursor()

        self.set_status("Ready",0)
        self.set_status("Done",1)
