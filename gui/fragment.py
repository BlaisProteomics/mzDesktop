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
import wx.grid
import os
import re

import multiplierz.mzReport

from multiplierz import myData
from multiplierz.mass_biochem import fragment_legacy

from mzGUI import report_chooser
from gui import BasicTab


class FragmentPanel(BasicTab):
    def __init__(self, parent):
        wx.Panel.__init__(self,parent,-1)

        gbs = wx.GridBagSizer(15, 7)

        gbs.Add( wx.StaticText(self, -1, "Peptide", style=wx.ALIGN_RIGHT),
                 (0,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT )

        gbs.Add( wx.StaticText(self, -1, ("Peptide format: AA in CAPS and mods in \n" + 
                                          "lower case (e.g. 'PEPpTIDE').  Modifications \n" +
                                          "can be numerical in brackets PEP[79.966]TIDE")),
                 (1,1), (1,5), flag=wx.ALIGN_CENTER_VERTICAL )

        gbs.Add( wx.StaticText(self, -1, "Ions:", style=wx.ALIGN_RIGHT),
                 (2,0), (4,1), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT )

        self.peptideString = wx.TextCtrl(self, -1, "")
        gbs.Add( self.peptideString,
                 (0,1), (1,4), flag=wx.EXPAND )

        self.ions = {}

        # no good way to deal with internal ions right now...the list
        # is way longer than the other lists
        ion_list = ['a', 'b', 'y', 'z', 'c',
                    'a-H2O', 'b-H2O', 'y-H2O', 'z+1', 'x',
                    'a-NH3', 'b-NH3', 'y-NH3', 'z+2', 'Immonium']
                    #'Immonium', 'Internal yb', 'Internal ya']
        ion_code = ['a', 'b', 'y', 'z', 'c',
                    'a0', 'b0', 'y0', 'z+1', 'x',
                    'a*', 'b*', 'y*', 'z+2', 'imm']
                    #'imm', 'intyb', 'intya']
        ion_coord = [(x,y) for x in range(2,5) for y in range(1,6)]

        for i,c,(x,y) in zip(ion_list,ion_code,ion_coord):
            self.ions[i] = wx.CheckBox(self, -1, i, name=c)
            gbs.Add( self.ions[i],
                     (x,y) )

        self.one_plus = wx.CheckBox(self, -1, '1+ ions')
        gbs.Add( self.one_plus,
                 (6,2) )

        self.two_plus = wx.CheckBox(self, -1, '2+ ions')
        gbs.Add( self.two_plus,
                 (6,3) )

        self.ions['b'].SetValue(True)
        self.ions['y'].SetValue(True)
        self.one_plus.SetValue(True)
        self.one_plus.Enable(False) 
        # Current (5/2/14) fragmentation algorithm fails when trying to
        # only calculate +2 ions.        

        self.writeToggleCk = wx.CheckBox(self, -1, "Write Output to Report  ", style=wx.ALIGN_RIGHT)
        gbs.Add( self.writeToggleCk,
                 (7,0), (1,5), flag=wx.ALIGN_LEFT )

        #Submit Button
        fragment_btn = wx.Button(self, -1, "Fragment", size=(160,-1))
        gbs.Add( fragment_btn,
                 (8,0), (1,5), flag=wx.ALIGN_LEFT )
        fragment_btn.Bind(wx.EVT_BUTTON, self.on_click)

        #gbs.AddGrowableCol(5)
 
 
        
        # Col 7 and row 9 both cause problems when run in 2.6; why?
        
        #self.dataDisplay = FragPanel(self)
        #gbs.Add(self.dataDisplay, (0, 7), (13, 1), flag = wx.EXPAND | wx.FIXED_MINSIZE)
        
        #gbs.AddGrowableCol(7)
        
        #gbs.Add(wx.BoxSizer(), (9, 0)) # 2.6 Python-WX fails to extrapolate row/col count from growables.
        #gbs.AddGrowableRow(9)        
        
        box = wx.BoxSizer()
        box.Add(gbs, 1, wx.ALL|wx.EXPAND, 20)
        self.SetSizerAndFit(box)

    def on_click(self, event):
        #update statusbar
        self.set_status("Fragmenting...",0)
        self.set_status("",1)

        peptide = self.peptideString.GetValue()
        peptide = re.sub(r'\[\]', '', peptide)
        self.peptideString.SetValue(peptide)

        ion_array = []

        if self.one_plus.IsChecked():
            for k,v in self.ions.items():
                if v.IsChecked():
                    ion_array.append(v.GetName())
            if self.two_plus.IsChecked():
                ion_array.extend([(ion+'++') for ion in ion_array
                                  if not ion.startswith('inty')]) # NB: generator causes infinite loop!
        elif self.two_plus.IsChecked():
            for k,v in self.ions.items():
                if v.IsChecked() and not k.startswith('Internal'):
                    ion_array.append(v.GetName() + '++')

        ion_array.sort()

        if not peptide:
            wx.MessageBox('No peptide sequence was entered.')
            return
        
        try:
            frag_data = fragment_legacy(peptide, ion_array, labels = False)
        except ValueError:
            wx.MessageBox('Invalid mass value.', 'Error')

            # update statusbar
            self.set_status("Ready", 0)
            self.set_status("Done", 1)
            return
        except LookupError as err:
            wx.MessageBox('Invalid modification name or position.', 'Error')
            import sys
            print sys.exc_info()
            
            # update statusbar
            self.set_status("Ready", 0)
            self.set_status("Done", 1)
            return

        pep_cleaner = re.compile(r'-?(\[.+?\]|[a-z0-9])-?')

        # peptide without any modifications
        sequence = pep_cleaner.sub('', peptide)

        row_headers = list(sequence)

        for m in re.finditer(r'(-?(\[.+?\]|[a-z])-?)', peptide):
            mod = m.group(1)
            if m.end() < len(peptide):
                i = len(pep_cleaner.sub('', peptide[:m.end() + 1])) - 1
                row_headers[i] = '%s%s' % (mod, row_headers[i])
            else:
                row_headers[-1] = '%s%s' % (row_headers[-1], mod)

        data = [[0.0 for ion in ion_array] for aa in sequence]
        # convert data to list of lists per AA
        for i,ion in enumerate(ion_array):
            ion_series = frag_data[i] + [None]
            if ion[0] in ('x', 'y', 'z'):
                ion_series.reverse()
            for j,aa in enumerate(sequence):
                data[j][i] = ion_series[j]

        if self.writeToggleCk.GetValue():
            writeFile = report_chooser(self, mode='w') or os.path.join(myData, 'pepFrag.csv')

            if os.path.exists(writeFile):
                os.remove(writeFile)

            myreport = multiplierz.mzReport.writer(writeFile, columns=[''] + ion_array)

            for i in range(len(row_headers)):
                myreport.write([row_headers[i]] + data[i])

            myreport.close()
        else:
            tableFrame = FragTable(self, -1, "Fragment Table", row_headers, ion_array, data)
            tableFrame.Show()
            
        #self.dataDisplay.displayData(row_headers, ion_array, data)

        # update statusbar
        self.set_status("Ready", 0)
        self.set_status("Done", 1)

class FragTable(wx.Frame):
    def __init__(self, parent, id, TableTitle, row_headers, col_headers, data):
        wx.Frame.__init__(self, parent, id, title = TableTitle, size=(640,480))

        # add icon
        self.SetIcon(parent.get_icon())

        pane = wx.Panel(self, -1, style = wx.TAB_TRAVERSAL | wx.CLIP_CHILDREN)

        # mass table. Keep a reference for when the Peak Viewer uses this class
        grid = self.grid = wx.grid.Grid(pane, -1)
        grid.CreateGrid(len(row_headers), len(col_headers))

        # Set row/column Headers
        for i,row in enumerate(row_headers):
            grid.SetRowLabelValue(i, row)

        dc = wx.MemoryDC()
        dc.SelectObject(wx.NullBitmap)

        grid.SetRowLabelSize(dc.GetTextExtent(max(row_headers, key=lambda r: len(r)))[0])

        dc.Destroy()

        for i,col in enumerate(col_headers):
            grid.SetColLabelValue(i, col)

        # Print Data
        for row in range(len(row_headers)):
            for col in range(len(col_headers)):
                if data[row][col] is not None:
                    grid.SetCellValue(row, col, "%0.2f" % data[row][col])

        box = wx.BoxSizer()
        box.Add(grid, 1, wx.EXPAND|wx.ALL, 5)
        pane.SetSizerAndFit(box)

        w,h = self.GetSize()
        self.SetMinSize((w/2,h/2))


class FragPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1, 
                          style = wx.TAB_TRAVERSAL | wx.SUNKEN_BORDER | wx.FIXED_MINSIZE)
        
        self.SetBackgroundColour((255, 255, 255))
        
        self.box = wx.BoxSizer()
        self.grid = wx.grid.Grid(self, -1)
        self.grid.CreateGrid(0, 0)
        self.box.Add(self.grid, 1, wx.EXPAND, 5)
        
        self.SetSizer(self.box)
        # add icon
        #self.SetIcon(parent.get_icon())

        #pane = wx.Panel(self, -1, style = wx.TAB_TRAVERSAL | wx.CLIP_CHILDREN)

    def displayData(self, row_headers, col_headers, data):
        #self.box.Clear()
        #self.SetSizer(self.box)
        
        #try:
            #self.grid.ClearGrid()
        #except AttributeError:
            #pass
        
        #self.grid.CreateGrid(len(row_headers), len(col_headers))
        if self.grid.GetNumberCols():
            self.grid.DeleteCols(numCols = self.grid.GetNumberCols())
        if self.grid.GetNumberRows():
            self.grid.DeleteRows(numRows = self.grid.GetNumberRows())
        self.grid.InsertCols(numCols = len(col_headers))
        self.grid.InsertRows(numRows = len(row_headers))

        # Set row/column Headers
        for i,row in enumerate(row_headers):
            self.grid.SetRowLabelValue(i, row)

        dc = wx.MemoryDC()
        dc.SelectObject(wx.NullBitmap)

        self.grid.SetRowLabelSize(dc.GetTextExtent(max(row_headers, key=lambda r: len(r)))[0])

        dc.Destroy()
        

        for i,col in enumerate(col_headers):
            self.grid.SetColLabelValue(i, col)

        # Print Data
        for row in range(len(row_headers)):
            for col in range(len(col_headers)):
                if data[row][col] is not None:
                    self.grid.SetCellValue(row, col, "%0.2f" % data[row][col])

        #box = wx.BoxSizer()
        #self.box.Add(self.grid, 1, wx.EXPAND, 5)
        self.grid.ForceRefresh()
        self.box.Layout()
        
        #self.SetSizer(box)
        

        #w,h = self.GetSize()
        #self.SetMinSize((w/2,h/2))