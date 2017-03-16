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

import multiplierz.mzReport

from multiplierz import myData
from multiplierz.mzTools.multifile import detect_matches

from mzGUI import NumValidator, report_chooser
from gui import BasicTab

class MultiDetectPanel(BasicTab):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)

        # intersection of spreadsheet columns, cached for speed
        self.cats = None

        self.default_dir = myData

        gbs = wx.GridBagSizer(12,5)

        gbs.Add( wx.StaticText(self, -1, 'Files to Compare'),
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

        gbs.Add( wx.StaticText(self, -1, 'Save Detections\nReport As', size=(83,-1), style=wx.ALIGN_RIGHT),
                 (4,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT )

        self.write_file_text = wx.TextCtrl(self, -1, os.path.join(myData, 'PepByFile.xls'))
        gbs.Add( self.write_file_text,
                 (4,1), flag=wx.EXPAND)

        write_file_btn = wx.Button(self, -1, 'Browse')
        gbs.Add( write_file_btn,
                 (4,2) )
        write_file_btn.Bind(wx.EVT_BUTTON, self.on_click_write)

        gbs.Add( wx.StaticText(self, -1, 'Fields to Match', style=wx.ALIGN_CENTER),
                 (5,0), (1,3), flag=wx.ALIGN_CENTER )

        self.option_list_data = ['Accession Number',
                                 'Peptide Sequence',
                                 'Variable Modifications',
                                 'Charge']
        option_list = ['Protein', 'Peptide', 'Modifications', 'Charge']

        self.category_list = wx.CheckListBox(self, -1, choices=option_list, size=(104,70))
        gbs.Add( self.category_list,
                 (6,0), (1,3), flag=wx.ALIGN_CENTER )
        self.category_list.SetChecked((1,2))
        self.category_list.Bind(wx.EVT_CHECKLISTBOX, self.on_check_list)

        more_cat_btn = wx.Button(self, -1, "More...")
        gbs.Add( more_cat_btn,
                 (7,0), (1,3), flag=wx.ALIGN_CENTER )
        more_cat_btn.Bind(wx.EVT_BUTTON, self.on_click_more)

        self.tolerance_ck = wx.CheckBox(self, -1, "mz Tolerance  ", style=wx.ALIGN_RIGHT)
        gbs.Add( self.tolerance_ck,
                 (8,0), (1,3), flag=wx.ALIGN_CENTER )
        self.tolerance_ck.Bind(wx.EVT_CHECKBOX, self.on_check_tolerance)

        self.tolerance_text = wx.TextCtrl(self, -1, "0.0", size=(100,-1),
                                         name="mz Tolerance", validator=NumValidator(flag=True))
        gbs.Add( self.tolerance_text,
                 (9,0), (1,3), flag=wx.ALIGN_CENTER )
        self.tolerance_text.Enable(False)

        #Submit Button
        detect_btn = wx.Button(self, -1, 'Detect', size=(160,-1))
        gbs.Add( detect_btn,
                 (10,0), (1,3), flag=wx.ALIGN_CENTER )
        detect_btn.Bind(wx.EVT_BUTTON, self.on_click_detect)

        gbs.AddGrowableCol(1)
        gbs.AddGrowableRow(3)

        box = wx.BoxSizer()
        box.Add(gbs, 1, wx.ALL|wx.EXPAND, 20)
        self.SetSizerAndFit(box)

    def on_check_tolerance(self, event):
        if self.tolerance_ck.GetValue():
            self.tolerance_text.Enable(True)
        else:
            self.tolerance_text.Enable(False)

    def on_check_list(self, event):
        if self.category_list.GetChecked():
            self.tolerance_ck.Enable(True)
        else:
            self.tolerance_ck.SetValue(False)
            self.tolerance_ck.Enable(False)
            self.tolerance_text.Enable(False)

    def on_click_add(self, event):
        file_names = report_chooser(self, mode='m')

        if file_names:
            self.default_dir = os.path.dirname(file_names[0])
            self.file_list.Set(sorted(set(self.file_list.GetStrings() + file_names)))
            self.write_file_text.SetValue(os.path.join(self.default_dir,
                                                       os.path.basename(self.write_file_text.GetValue())))

            if self.cats:
                cols = []
                for f in file_names:
                    rdr = multiplierz.mzReport.reader(f)
                    cols.append(rdr.columns[:])
                    rdr.close()
                self.cats = sorted(set(self.cats).intersection(reduce(set.intersection,
                                                                      [set(c) for c in cols])))

    def on_click_remove(self, event):
        remove = self.file_list.GetSelections()
        files = [f for i,f in enumerate(self.file_list.GetStrings()) if i not in remove]
        self.file_list.Set(files)

        if not files:
            self.cats = None
            self.category_list.SetItems(self.category_list.GetStrings()[:4])
            self.category_list.SetChecked((1,2))
        elif self.cats:
            cols = []
            for f in files:
                rdr = multiplierz.mzReport.reader(f)
                cols.append(rdr.columns[:])
                rdr.close()
            cats = reduce(set.intersection, [set(c) for c in cols])

            self.cats = sorted(cats.difference(set(self.option_list_data + ['Experimental mz'])))

    def on_click_clear(self, event):
        self.file_list.Clear()
        self.cats = None
        self.category_list.SetItems(self.category_list.GetStrings()[:4])
        self.category_list.SetChecked((1,2))
        self.write_file_text.SetValue(os.path.join(myData, os.path.basename(self.write_file_text.GetValue())))

    def on_click_write(self, event):
        file_name = report_chooser(self, mode='w', defaultDir=self.default_dir)
        if file_name:
            self.write_file_text.SetValue(file_name)

    def on_click_more(self, event):
        if not self.cats:
            files = self.file_list.GetStrings()
            if not files:
                return
            cols = []
            for f in files:
                rdr = multiplierz.mzReport.reader(f)
                cols.append(rdr.columns[:])
                rdr.close()
            cats = reduce(set.intersection, [set(c) for c in cols])

            self.cats = sorted(c for c in cats.difference(set(self.option_list_data + ['Experimental mz'])) if c)

        more_cats = wx.MultiChoiceDialog(None, "Choose Columns To Match:", "More Fields",
                                         choices=self.cats)
        if more_cats.ShowModal() == wx.ID_OK:
            defaults = self.category_list.GetStrings()[:4]
            checked_defs = [d for i,d in enumerate(defaults)
                            if self.category_list.IsChecked(i)]

            checked_cats = [self.cats[i] for i in more_cats.GetSelections()]

            self.category_list.SetItems(defaults + checked_cats)
            self.category_list.SetCheckedStrings(checked_defs + checked_cats)

        more_cats.Destroy()

    def on_click_detect(self, event):
        if not self.file_list.GetStrings():
            wx.MessageBox('No files selected', 'Error')
            return
        elif self.tolerance_ck.GetValue() and not self.Validate():
            return

        # show hourglass
        wx.BeginBusyCursor(wx.HOURGLASS_CURSOR)
    
        #try:
        save_file = self.write_file_text.GetValue()

        columns = self.option_list_data + self.category_list.GetStrings()[4:]

        selections = [op for i,op in enumerate(columns)
                      if self.category_list.IsChecked(i)]

        tolerance = 0.0
        if self.tolerance_ck.GetValue():
            tol_field = 'Experimental mz'
            if self.tolerance_text.GetValue():
                tolerance = float(self.tolerance_text.GetValue())
            else:
                tolerance = 0.0
        else:
            tol_field = None
            tolerance = 0.0

        # update statusbar
        self.set_status("Running MultiFile Detect...", 0)
        self.set_status("", 1)

        files = self.file_list.GetStrings()
        detect_matches(files, selections, tol_field, tolerance, save_file)
        #except Exception as err:
            #wx.MessageBox("An error occurred:\n" + repr(err), "Error")
            #wx.EndBusyCursor()
            #raise

        # hide hourglass
        wx.EndBusyCursor()

        self.set_status("Ready", 0)
        self.set_status("Done", 1)
