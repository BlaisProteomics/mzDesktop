# Copyright 2008 Dana-Farber Cancer Institute
# multiplierz is distributed under the terms of the GNU Lesser General Public License
#
# This file is part of multiplierz/mzDesktop.
#
# multiplierz/mzDesktop is free software: you can redistribute it and/or modify
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
import wx.py as py
import re
import os
import operator
import re

from gui import BasicTab

class ConsolePanel(BasicTab):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)

        gbs = wx.GridBagSizer()

        consolewin = py.crust.Crust(self)
        consolewin.shell.clear()
        consolewin.shell.prompt()

        gbs.Add(consolewin, (0,0), flag=wx.EXPAND)

        gbs.AddGrowableRow(0)
        gbs.AddGrowableCol(0)

        box = wx.BoxSizer()
        box.Add(gbs, 1, wx.ALL|wx.EXPAND, 10)
        self.SetSizerAndFit(box)
