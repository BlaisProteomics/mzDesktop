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

import multiplierz.mzAPI

#from mzDesktop import MZ_WILDCARD

from multiplierz.mzGUI_standalone import MZ_WILDCARD

from gui import BasicTab

class InfoFilePanel(BasicTab):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)

        gbs = wx.GridBagSizer(12, 5)

        gbs.Add( wx.StaticText(self, -1, "Peak File", style=wx.ALIGN_RIGHT),
                 (0,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT )

        self.peak_file_text = wx.TextCtrl(self, -1, "", size=(250,-1))
        gbs.Add( self.peak_file_text,
                 (0,1), flag=wx.EXPAND )

        peak_file_btn = wx.Button(self, -1, "Browse")
        peak_file_btn.Bind(wx.EVT_BUTTON, self.OnClickPeakFile)
        gbs.Add( peak_file_btn,
                 (0,2) )

        # Make Info button
        make_info_btn = wx.Button(self, -1, "Make Info File", size=(160,-1))
        gbs.Add( make_info_btn,
                 (3,0), (1,3), flag=wx.ALIGN_CENTER)
        make_info_btn.Bind(wx.EVT_BUTTON, self.OnClickMakeInfo)

        gbs.AddGrowableCol(1)

        box = wx.BoxSizer()
        box.Add(gbs, 1, wx.ALL|wx.EXPAND, 20)
        self.SetSizerAndFit(box)

    def OnClickPeakFile(self,event):
        file_chooser = wx.FileDialog(None, "Choose Peak File:",
                                     wildcard=MZ_WILDCARD,
                                     style=wx.FD_OPEN)
        if file_chooser.ShowModal() == wx.ID_OK:
            self.peak_file_text.SetValue(file_chooser.GetPath())
        file_chooser.Destroy()

    def OnClickMakeInfo(self,event):
        #show hourglass
        wx.BeginBusyCursor(wx.HOURGLASS_CURSOR)

        #update statusbar
        self.set_status("Making Info File...", 0)
        self.set_status("", 1)

        peak_file = self.peak_file_text.GetValue().lower()

        multiplierz.mzAPI.make_info_file(peak_file)

        #hide hourglass
        wx.EndBusyCursor()

        self.set_status("Ready", 0)
        self.set_status("Done", 1)

