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

import cStringIO
import os
import re

from collections import defaultdict
from numpy import array, hypot

import wx
import wx.grid

from wx.lib.agw import flatnotebook
from wx.lib.expando import ExpandoTextCtrl, EVT_ETC_LAYOUT_NEEDED

import multiplierz.mzReport
import multiplierz.mzTools.mz_image as mz_image

from multiplierz.mzAPI import mzFile
from multiplierz.mass_biochem import mz_pep_format

import wxmpl

from mzGUI import MZ_WILDCARD

from mzDesktop import find_mz_file, settings, logger_message

from autocomplete import AutocompleteTextCtrl, list_completer



def getTimeFromSpectrumDescription(description, mzfile):
    if description[:5] == 'Locus':
        # Then this is a full .wiff file description.
        numbers = description.replace(":", ".").replace(' ', ".").split(".")[1:6]
        scanNum = numbers[3]
        experiment = numbers[4]
        #return mzfile.timeForScan(int(scanNum) - 1, experiment)
        return mzfile.timeForScan(int(scanNum), experiment)
    elif len(description) < 19 and 4 < len(description.split(".")) < 7:
        # Then this is ???probably??? a shortened .wiff file description.
        numbers = description.split(".")
        scanNum = numbers[3]
        experiment = numbers[4]
        return mzfile.timeForScan(int(scanNum) - 1, experiment)
    elif description.split('=')[0] == 'scanId':
        # Then this is a .d file description.
        scanNum = description.split('=')[1]
        return mzfile.scan_time_from_scan_name(int(scanNum))
    elif description.split('.')[1] == description.split('.')[2]:
        # Then this is a .raw file description.
        scanNum = description.split('.')[1]
        return mzfile.timeForScan(int(scanNum))
    else:
        raise NotImplementedError
    



class ImageFrame(wx.Frame):
    def __init__(self, parent, col, title, image):
        wx.Frame.__init__(self, parent, -1, title=title,
                          style=(wx.DEFAULT_FRAME_STYLE ^ (wx.RESIZE_BORDER | wx.MAXIMIZE_BOX)))

        #add status bar
        status_bar = self.CreateStatusBar()
        status_bar.SetFieldsCount(1)
        status_bar.SetStatusStyles([wx.SB_FLAT])
        status_bar.SetStatusText("Ctrl+S to save", 0)

        box = wx.BoxSizer()

        self.col = col
        self.figure = None

        self.image = wx.StaticBitmap(self, -1, wx.BitmapFromImage(image))
        box.Add(self.image, 1, wx.EXPAND, 0)

        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.Bind(wx.EVT_KEY_UP, self.on_save_image)

        self.SetSizerAndFit(box)
        self.SetIcon(parent.GetParent().GetIcon())

    def update(self, title, image):
        self.SetTitle(title)
        self.image.SetBitmap(wx.BitmapFromImage(image))
        self.Refresh()

    def on_save_image(self, event):
        if event.GetKeyCode() == 83 and event.GetModifiers() == wx.MOD_CONTROL:
            wildcard = ("PNG (*.png)|*.png|"
                        "JPEG (*.jpg)|*.jpg|"
                        "TIFF (*.tiff)|*.tiff|"
                        "Bitmap (*.bmp)|*.bmp")
            formats = (wx.BITMAP_TYPE_PNG,
                       wx.BITMAP_TYPE_JPEG,
                       wx.BITMAP_TYPE_TIF,
                       wx.BITMAP_TYPE_BMP)
            dlg = wx.FileDialog(self, "Save figure as...",
                                wildcard=wildcard, style=wx.FD_SAVE)
            if dlg.ShowModal() == wx.ID_OK:
                self.image.GetBitmap().SaveFile(dlg.GetPath(), type=formats[dlg.GetFilterIndex()])
            dlg.Destroy()

    def on_close(self, event):
        i = self.GetParent().GetParent().nb.GetSelection()
        self.GetParent().GetParent().grid_ctrls[i].image_frames[self.col].remove(self)
        self.Destroy()


class DataFrame(wx.Frame):
    def __init__(self, parent, col):
        wx.Frame.__init__(self, parent, -1) #,
                          #style=(wx.DEFAULT_FRAME_STYLE ^ (wx.RESIZE_BORDER | wx.MAXIMIZE_BOX)))

        self.col = col

        dpi = int(sum(settings.image_size) / 14.0 * 100.0)

        self.canvas = wxmpl.PlotPanel(self, -1, (8.0, 6.0), dpi=dpi,
                                      location=False, autoscaleUnzoom=False)
        self.figure = self.canvas.get_figure()

        box = wx.BoxSizer()
        box.Add(self.canvas, 1, wx.EXPAND, 0)

        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.canvas.Bind(wx.EVT_KEY_UP, self.on_save_image)

        self.SetSizerAndFit(box)
        try:
            self.SetIcon(parent.GetParent().GetParent().GetParent().GetIcon())
        except AttributeError:
            self.SetIcon(parent.GetParent().GetParent().GetIcon())

    def setup(self, title, tag, *args):
        '''Specialized update method for initialization--because the PlotPanel creates its own
        figure, we need to first create the frame and then update the figure.'''


        self.SetTitle(title)


        self.tooltip = wx.ToolTip(tip='tip with a long %s line and a newline\n' % (' '*100))
        self.tooltip.Enable(False)
        self.tooltip.SetDelay(0)
        self.canvas.SetToolTip(self.tooltip)

        #self.Bind(wx.EVT_HELP, lambda e: self.on_help(tag))

        # allowing some backwards compatability for the ric->xic change
        if tag == 'xic' or tag == 'ric' or tag == 'ms1':
            self.xy = args[0]

            #add status bar
            status_bar = self.CreateStatusBar(style = wx.DEFAULT_STATUSBAR_STYLE ^ wx.ST_SIZEGRIP)
            status_bar.SetFieldsCount(3)
            status_bar.SetStatusStyles([wx.SB_FLAT]*3)
            status_bar.SetStatusText("Click and drag to zoom", 0)
            status_bar.SetStatusText("Right-click to zoom out", 1)
            status_bar.SetStatusText("Ctrl+S to save", 2)

            if tag == 'xic' or tag == 'ric': # backwards compatible
                tooltip = '(%%3.%df, %%3.%df)' % (settings.xic_time_figs,
                                                  settings.xic_int_figs)
            else:
                tooltip = '(%%3.%df, %%3.%df)' % (settings.ms1_mz_figs,
                                                  settings.ms1_int_figs)

            self.canvas.mpl_connect('motion_notify_event', lambda e: self.on_motion(e, tooltip))
        elif tag == 'ms2':
            self.labels = args[0]
            self.annotations = args[1]

            #add status bar
            status_bar = self.CreateStatusBar(style = wx.DEFAULT_STATUSBAR_STYLE ^ wx.ST_SIZEGRIP)
            status_bar.SetFieldsCount(4)
            status_bar.SetStatusStyles([wx.SB_FLAT]*4)
            status_bar.SetStatusWidths([-3, -3, -2, -6])
            status_bar.SetStatusText("Click+drag to zoom", 0)
            status_bar.SetStatusText("Right-click to zoom out", 1)
            status_bar.SetStatusText("Ctrl+S to save", 2)
            status_bar.SetStatusText("Hover/click on a residue to highlight fragment ions", 3)

            tooltip = '%%s\n(%%4.%df, %%3.%df)' % (settings.ms2_mz_figs,
                                                   settings.ms2_int_figs)

            # tooltip displays mz, intensity, label
            self.canvas.mpl_connect('motion_notify_event', lambda e: self.on_ms2_motion(e, tooltip))

            self.text_box = ((min(a[0] for a in self.annotations) - 0.05, 0.85),
                             (max(a[0] for a in self.annotations) + 0.05, 0.95))

            # [0] is the last annotation (or None). [1] is True if it is from a click event
            self.last_anno = (None, False)

            # highlight the relevant annotations when an amino acid is clicked
            self.canvas.mpl_connect('button_release_event', self.on_left_click)

    def update(self, title, tag, *args):
        self.SetTitle(title)

        # 'ric' allowed for (a little) backwards compatibility
        if tag == 'xic' or tag == 'ric' or tag == 'ms1':
            self.xy = args[0]
        elif tag == 'ms2':
            self.labels = args[0]
            self.annotations = args[1]

            self.text_box = ((min(a[0] for a in self.annotations) - 0.05, 0.85),
                             (max(a[0] for a in self.annotations) + 0.05, 0.95))

            # [0] is the last annotation (or None). [1] is True if it is from a click event
            self.last_anno = (None, False)

        self.canvas.draw()

    def on_motion(self, event, tooltip):
        if event.inaxes:
            a = event.inaxes
            e_xy = array([event.x, event.y])

            xy = min((a.transData.transform([x,y]) for x,y in self.xy),
                     key = lambda xy: hypot(*(e_xy - xy)))

            if all(abs(xy - e_xy) < 10.0):
                tip = tooltip % tuple(a.transData.inverted().transform(xy))
                self.tooltip.SetTip(tip) # update the tooltip
                self.tooltip.Enable(True) # make sure it's enabled
            else:
                self.tooltip.Enable(False)
        else:
            self.tooltip.Enable(False)

    def on_ms2_motion(self, event, tooltip):
        '''Called during mouse motion over figure'''
        if not self.labels:
            self.tooltip.Enable(False)
        elif event.inaxes:
            a = event.inaxes
            e_xy = array([event.x, event.y])

            mzi,lbl = min(((a.transData.transform([mz,i]),lbl)
                           for mz,i,lbl in self.labels),
                          key=lambda t: hypot(*(e_xy - t[0])))

            if all(abs(mzi - e_xy) < 10.0):
                mz,i = a.transData.inverted().transform(mzi)
                tip = tooltip % (', '.join(lbl), mz, i)
                self.tooltip.SetTip(tip) # update the tooltip
                self.tooltip.Enable(True) # make sure it's enabled
            else:
                self.tooltip.Enable(False)
        else: # mouse is outside the axes
            self.tooltip.Enable(False) # disable the tooltip

            # if the current annotation is from a click event, then don't change anything
            if not self.last_anno[1]:
                rel_x, rel_y = self.figure.transFigure.inverted().transform([event.x, event.y])

                # otherwise, find the appropriate annotation to display
                if self.text_box[0][1] < rel_y < self.text_box[1][1]:
                    if self.text_box[0][0] < rel_x < self.text_box[1][0]:
                        x,anno = min(self.annotations,
                                     key = lambda x_a: abs(x_a[0] - rel_x))
                        if anno is not None:
                            if self.last_anno[0] is not None:
                                self.last_anno[0].set_visible(False)
                            anno.set_visible(True)
                            self.canvas.draw()
                            self.last_anno = (anno, False)
                            return

        if (self.last_anno[0] is not None
            and not self.last_anno[1]):
            self.last_anno[0].set_visible(False)
            self.last_anno = (None, False)
            self.canvas.draw()

    def on_left_click(self, event):
        rel_x, rel_y = self.figure.transFigure.inverted().transform([event.x, event.y])

        # if mouse is in the peptide area, draw the appropriate annotation
        if self.text_box[0][1] < rel_y < self.text_box[1][1]:
            if self.text_box[0][0] < rel_x < self.text_box[1][0]:
                x,anno = min(self.annotations,
                             key = lambda x_a: abs(x_a[0] - rel_x))
                if anno is not None:
                    if self.last_anno[0] is not None:
                        self.last_anno[0].set_visible(False)
                    if (self.last_anno[0] is anno and self.last_anno[1]):
                        self.last_anno = (anno, False)
                        return
                    else:
                        anno.set_visible(True)
                        self.canvas.draw()
                        self.last_anno = (anno, True)
                        return

        # otherwise, clear any existing annotation
        if self.last_anno[0] is not None:
            self.last_anno[0].set_visible(False)
            self.last_anno = (None, False)
            self.canvas.draw()

    def on_save_image(self, event):
        if event.GetKeyCode() == 83 and event.GetModifiers() == wx.MOD_CONTROL:
            wildcard = ("PNG (*.png)|*.png|"
                        "PDF (*.pdf)|*.pdf|"
                        "PS (*.ps)|*.ps|"
                        "EPS (*.eps)|*.eps|"
                        "SVG (*.svg)|*.svg")
            formats = ('PNG', 'PDF', 'PS', 'EPS', 'SVG')
            dlg = wx.FileDialog(self, "Save figure as...",
                                wildcard=wildcard, style=wx.FD_SAVE)
            if dlg.ShowModal() == wx.ID_OK:
                self.figure.savefig(dlg.GetPath(), format=formats[dlg.GetFilterIndex()])
            dlg.Destroy()

    def on_close(self, event):
        #i = self.GetParent().GetParent().nb.GetSelection()
        #self.GetParent().GetParent().grid_ctrls[i].image_frames[self.col].remove(self)
        try:
            ancestor = self.GetParent().GetParent().GetParent().GetParent()
            ancestor.nb
        except AttributeError:
            ancestor = self.GetParent().GetParent().GetParent()
        i = ancestor.nb.GetSelection()
        #self.GetParent().GetParent().GetParent().GetParent().grid_ctrls[i].image_frames[self.col].remove(self)        
        # Perhaps this is supposed to do something important?  There's hardly any way to tell!
        try:
            self.Destroy()
        except wx._core.PyDeadObjectError:
            # Then the object is already destroy()'d?
            print "Dead-Object-Error suppressed."
        


class ReportModel(object):
    def __init__(self, file_name):
        if file_name.lower().endswith('.mzd'):
            self.is_MZD = True
            self.is_MZID = False
            self.report = multiplierz.mzReport.mzDB.SQLiteReader(file_name)
            # no need to expose the ImageData table, normally
            self.tables = tuple(t for t in self.report.tables if t != 'ImageData')

            # this is a piece of backwards compatibility--creates a fast index
            # for image data. It won't do anything on new files
            self.report.conn.execute('create unique index if not exists ImageDataIdx on ImageData(rowid,col)')

            self.page = 1
            self.rows_per_page = 1000
        elif file_name.lower().endswith('.mzid'):
            self.is_MZD = False
            self.is_MZID = True
            self.report = multiplierz.mzReport.reader(file_name)
        else:
            self.is_MZD = False
            self.is_MZID = False
            self.report = multiplierz.mzReport.reader(file_name)

        self.refresh() # gets data+columns

        if self.is_MZD:
            cursor = self.report.conn.execute("select distinct Col from ImageData where tag!='image'")
            self.md_cols = frozenset(c[0] for c in cursor)

            cursor = self.report.conn.execute("select distinct Col from ImageData where tag='image'")
            self.im_cols = frozenset(c[0] for c in cursor)
        elif self.is_MZID:
            if self.report.datafile.isAnnotated():
                self.md_cols = frozenset(['Peptide Sequence'])
                self.im_cols = frozenset()
            else:
                self.md_cols = self.im_cols = frozenset()    
        else:
            self.md_cols = self.im_cols = frozenset()

        self.ms_cols = frozenset(('file', 'spectrum description', 'Spectrum Description'))

    def refresh(self, table_name=None, query=None, page=None, rows_per_page=None):
        if not self.is_MZD:
            self.default = False

            self.columns = tuple(self.report.columns)
            self.col_dict = dict((c,i) for i,c in enumerate(self.columns))

            try:
                self.data = [(i+1,tuple(row[:])) for i,row in enumerate(self.report)]
            except TypeError:
                self.data = [(i, [row[k] for k in self.columns]) for i, row
                             in enumerate(self.report, start = 1)]
            self.row_count = len(self.data)

            return

        table_name = table_name or 'PeptideData' # PeptideData must be present

        if rows_per_page is not None:
            self.rows_per_page = rows_per_page

        if page is not None:
            self.page = page

        if query:
            try:
                cursor = self.report.conn.execute(query)
                self.default = False
            except multiplierz.mzReport.mzDB.sqlite3.Error, e:
                logger_message(20, "Invalid SQLite query, selecting everything instead")
                logger_message(10, "Error message: %s" % e)
                cursor = self.report.conn.execute('select * from %s limit (?) offset (?)' % table_name,
                                                  (self.rows_per_page,
                                                   (self.page - 1) * self.rows_per_page))
                self.default = True
        else:
            cursor = self.report.conn.execute('select * from %s limit (?) offset (?)' % table_name,
                                              (self.rows_per_page,
                                               (self.page - 1) * self.rows_per_page))
            self.default = True

        self.columns = [d[0] for d in cursor.description]
        self.columns = tuple((c[1:-1] if c[0] == c[-1] == '"' else c) for c in self.columns if c)
        self.col_dict = dict((c,i) for i,c in enumerate(self.columns))

        if 'rowid' in [c.lower() for c in self.columns]:
            self.default = True

            ri = [c.lower() for c in self.columns].index('rowid')

            self.data = [(row[ri], row) for row in cursor]
        else:
            # indices may or may not conform to correct rowid
            self.data = [(i+1,row) for i,row in enumerate(cursor)]

        self.row_count = len(self.data)

    def get_item_text(self, index, column):
        return self.data[index][1][column]

    def get_selection(self, rows, columns):
        if rows and columns:
            return [[self.data[i][1][j] for j in columns] for i in rows]
        elif rows:
            return [self.data[i][1][:] for i in rows]
        elif columns:
            return [[row[1][j] for j in columns] for row in self.data]

    def get_metadata(self, row, col):
        if self.is_MZD:
            return self.report.conn.execute(("SELECT tag,PlotData as 'PlotData [pickled]' FROM ImageData "
                                             "WHERE RowID=? AND Col=? AND Tag!='image'"),
                                            (self.data[row][0] + (self.page - 1) * self.rows_per_page, col)).fetchone()
        elif self.is_MZID:
            scan = self.report.datafile.getAnnotation(self.data[row][1][10])
            peptide = self.data[row][1][9]
            mods = self.data[row][1][1]
            modPeptide = mz_pep_format(peptide, mods)
            return 'ms2', (scan, 'c', modPeptide)

    def get_image_data(self, row, col):
        return self.report.conn.execute(("SELECT PlotData FROM ImageData "
                                         "WHERE RowID=? AND Col=? AND Tag='image'"),
                                        (self.data[row][0] + (self.page - 1) * self.rows_per_page, col)).fetchone()

    def close(self):
        self.report.close()


class ReportTable(wx.grid.PyGridTableBase):
    def __init__(self, model):
        wx.grid.PyGridTableBase.__init__(self)

        self.model = model

        self.mdcell = wx.grid.GridCellAttr()
        self.mdcell.SetBackgroundColour("light blue")
        self.imcell = wx.grid.GridCellAttr()
        self.imcell.SetBackgroundColour("spring green")

        self.mscell = wx.grid.GridCellAttr()
        self.mscell.SetBackgroundColour(wx.NamedColour('#FFA881'))

        self._rows = self.GetNumberRows()
        self._cols = self.GetNumberCols()
        self._colsort = [False] * self._cols

    def GetNumberRows(self):
        return self.model.row_count

    def GetNumberCols(self):
        return len(self.model.columns)

    def GetRowLabelValue(self, row):
        if self.model.default:
            return str(row + ((self.model.page - 1) * self.model.rows_per_page) + 1)
        else:
            return row + 1

    def GetColLabelValue(self, col):
        return '\n'.join(self.model.columns[col].split(None,1))

    def GetAttr(self, row, col, kind):
        if not self.model.default:
            return None

        col_name = self.model.columns[col]

        if col_name in self.model.md_cols:
            self.mdcell.IncRef()
            return self.mdcell
        elif col_name in self.model.im_cols:
            self.imcell.IncRef()
            return self.imcell
        elif col_name.lower() in self.model.ms_cols:
            self.mscell.IncRef()
            return self.mscell
        else:
            return None

    def GetValue(self, row, col):
        v = self.model.get_item_text(row, col)
        if v is None:
            return ''
        else:
            return v

    def SetValue(self, row, col, value):
        pass

    def reset_view(self, grid, table_name, query, page, rows_per_page):
        self.model.refresh(table_name, query, page, rows_per_page)

        grid.BeginBatch()

        for current, new, delmsg, addmsg in [
            (self._rows, self.GetNumberRows(), wx.grid.GRIDTABLE_NOTIFY_ROWS_DELETED, wx.grid.GRIDTABLE_NOTIFY_ROWS_APPENDED),
            (self._cols, self.GetNumberCols(), wx.grid.GRIDTABLE_NOTIFY_COLS_DELETED, wx.grid.GRIDTABLE_NOTIFY_COLS_APPENDED),
        ]:
            if new < current:
                msg = wx.grid.GridTableMessage(self,delmsg,new,current-new)
                grid.ProcessTableMessage(msg)
            elif new > current:
                msg = wx.grid.GridTableMessage(self,addmsg,new-current)
                grid.ProcessTableMessage(msg)
                msg = wx.grid.GridTableMessage(self, wx.grid.GRIDTABLE_REQUEST_VIEW_GET_VALUES)
                grid.ProcessTableMessage(msg)

        grid.EndBatch()

        self._rows = self.GetNumberRows()
        self._cols = self.GetNumberCols()
        self._colsort = [False] * self._cols

        # update the scrollbars and the displayed part of the grid
        grid.AdjustScrollbars()

        grid.ForceRefresh()

    def sort_column(self, col):
        """
        col -> sort the data based on the column indexed by col
        """
        self.model.data.sort(key=lambda r: r[1][col], reverse=self._colsort[col])
        self._colsort[col] = not self._colsort[col]


class ReportGrid(wx.grid.Grid):
    def __init__(self, parent, ID, model):
        wx.grid.Grid.__init__(self, parent, ID)

        self._table = ReportTable(model)
        self.SetTable(self._table, True)

        self.SetMinSize((700,500))
        self.reset()

        self.Bind(wx.grid.EVT_GRID_CELL_LEFT_DCLICK, self.on_cell_dclick)
        self.Bind(wx.grid.EVT_GRID_LABEL_LEFT_DCLICK, self.on_label_dclick)
        self.Bind(wx.grid.EVT_GRID_SELECT_CELL, self.on_cell_select)
        self.Bind(wx.EVT_KEY_DOWN, self.on_copy)

        self.image_methods = { 'ms1': mz_image._make_ms1,
                               'xic': mz_image._make_xic,
                               'ric': mz_image._make_xic, # backwards compatible
                               'ms2': mz_image._make_ms2 }

        self.image_frames = defaultdict(list)

    def on_copy(self, event):
        if event.ControlDown() and event.GetKeyCode() == 67:
            cols = self.GetSelectedCols()
            rows = self.GetSelectedRows()
            uleft = self.GetSelectionBlockTopLeft()
            bright = self.GetSelectionBlockBottomRight()

            # priority if it comes up: block > col > rows.
            # only the first block is considered (it's
            # possible to select multiple blocks, weirdly)
            if uleft and bright:
                rows = range(uleft[0][0], bright[0][0]+1)
                cols = range(uleft[0][1], bright[0][1]+1)
                selection = self.get_selection(rows, cols)
            elif cols:
                selection = self.get_selection(None, sorted(cols))
            elif rows:
                selection = self.get_selection(sorted(rows), None)
            else:
                event.Skip()
                return

            if wx.TheClipboard.Open():
                wx.TheClipboard.SetData(wx.TextDataObject(selection))

        event.Skip()

    def on_label_dclick(self, event):
        col = event.GetCol()

        if col > -1:
            self._table.sort_column(col)

        self.ForceRefresh()

    def on_cell_select(self, event):
        if self._table.model.default:
            row, col = event.GetRow(), event.GetCol()
            col = self._table.model.columns[col]
            if col in self.image_frames and self.image_frames[col]:
                title_im = self.get_image(row, col, self.image_frames[col][-1].figure)
                if title_im is not None:
                    self.image_frames[col][-1].update(*title_im)

        event.Skip()

    def on_cell_dclick(self, event):
        row, col = event.GetRow(), event.GetCol()
        col = self._table.model.columns[col]

        try:
            peak_viewer = self.GetParent().GetParent().GetParent().GetParent().peak_viewer
        except AttributeError:
            peak_viewer = self.GetParent().GetParent().peak_viewer

        if col in self._table.model.im_cols:
            wx.BeginBusyCursor(wx.HOURGLASS_CURSOR)

            self.image_frames[col].append(ImageFrame(self.GetParent(), col, *self.get_image(row, col)))
            self.image_frames[col][-1].Show()

            wx.EndBusyCursor()
        elif col in self._table.model.md_cols:
            wx.BeginBusyCursor(wx.HOURGLASS_CURSOR)

            self.image_frames[col].append(DataFrame(self.GetParent(), col))
            # two-part initialization
            self.image_frames[col][-1].setup(*self.get_image(row, col, self.image_frames[col][-1].figure))
            self.image_frames[col][-1].Show()

            wx.EndBusyCursor()
        elif (col.lower() in self._table.model.ms_cols
              or peak_viewer is not None):
            self.on_peak_viewer(event)
        else:
            event.Skip()

    def on_peak_viewer(self, event):
        wx.BeginBusyCursor(wx.HOURGLASS_CURSOR)
        
        try:
            # From mzResults.
            peak_viewer = self.GetParent().GetParent().GetParent().GetParent().peak_viewer
            ancestor = self.GetParent().GetParent().GetParent().GetParent()
        except AttributeError:
            # From mzDesktop "connect to results."
            peak_viewer = self.GetParent().GetParent().peak_viewer
            ancestor = self.GetParent().GetParent()
        
        if peak_viewer is None:
            if 'File' in self._table.model.col_dict:
                file_name = self.GetCellValue(event.GetRow(),
                                              self._table.model.col_dict['File'])
            else:
                file_name = None

            if 'Spectrum Description' in self._table.model.col_dict:
                spec_desc = self.GetCellValue(event.GetRow(),
                                              self._table.model.col_dict['Spectrum Description'])
            else:
                spec_desc = None


            mz_file = find_mz_file(os.path.dirname(ancestor.file_name),
                                   file_name,
                                   spec_desc)
            
            if mz_file:
                ancestor.connect(mz_file)
                peak_viewer = ancestor.peak_viewer
            else:
                wx.EndBusyCursor()
                ancestor.on_mz_file(None)
                return
        else:
            #peak_viewer = self.GetParent().GetParent().peak_viewer
            mz_file = None

        #column_dict = dict((k, self._table.model.col_dict[k])
                           #for k in ('File', 'MS2 Time', 'Experimental mz', 'Charge', #'mz', 'Charge',
                                     #'Peptide Sequence', 'Variable Modifications',
                                     #'Spectrum Description')
                           #if k in self._table.model.col_dict)
        column_dict = self._table.model.col_dict

        row = event.GetRow()

        if mz_file is None:
            file_name = (self.GetCellValue(row, column_dict['File'])
                         if 'File' in column_dict else None)
            spec_desc = (self.GetCellValue(row, column_dict['Spectrum Description'])
                         if 'Spectrum Description' in column_dict else None)
            mz_file = find_mz_file(peak_viewer.report_dir, file_name, spec_desc)

        # still no file? try the peak_viewer
        if mz_file is None or not (mz_file.startswith('http://') or os.path.exists(mz_file)):
            mz_file = peak_viewer.mz_file_name

            if not peak_viewer.openMz:
                wx.MessageBox("Please open an MS data file.", "No MS Data File")
                wx.EndBusyCursor()
                return

        peak_viewer.mz_file_name = mz_file
        if mz_file not in peak_viewer.mz_files:
            peak_viewer.mz_files[mz_file] = mzFile(mz_file)

        peak_viewer.openMz = True

        peak_viewer.mz_file_text.SetValue(mz_file)
        
       

        try:
            time = getTimeFromSpectrumDescription(self.GetCellValue(row, column_dict['Spectrum Description']),
                                                  peak_viewer.mz_files[mz_file])
        except NotImplementedError:
            try:
                time = float(self.GetCellValue(row, column_dict['MS2 Time']))                
            except KeyError:
                print "Insufficient data to retrieve peak!"
                return

        try:
            mz = float(self.GetCellValue(row, column_dict['Experimental mz']))
        except KeyError:
            mz = float(self.GetCellValue(row, column_dict['Experimental m/z']))

        peak_viewer.ms2mz = mz
        peak_viewer.time = time

        first_time, last_time = peak_viewer.mz_files[mz_file].time_range()

        start_time = max(time - settings.XIC_gen_time_window / 2, first_time + 0.00001)
        end_time = min(time + settings.XIC_gen_time_window / 2, last_time)

        start_mz = mz - settings.XIC_gen_mz_window / 2
        end_mz = mz + settings.XIC_gen_mz_window / 2

        peak_viewer.draw_XIC_plot(start_time, end_time, start_mz, end_mz, time)

        # Precursor Masses Graph
        precursorScanTime = max([t for t in peak_viewer.MS1_XIC_scans if t <= time] or [time])

        data = peak_viewer.mz_files[mz_file].scan(precursorScanTime)

        scan_mz = float(peak_viewer.ms2mz)

        peak_viewer.MS1_data = (data, scan_mz, precursorScanTime)

        peak_viewer.draw_MS1_plot()

        # MS MS Graph
        try:
            ms2_data = peak_viewer.mz_files[mz_file].scan(time)
        except KeyError:
            raise Exception, "Time {0} does not match any MS2 scan in {1}".format(time, mz_file)
        

        peak_viewer.MS2_data = (ms2_data, time)

        peak_viewer.draw_MS2_plot()

        #Fragmenter
        if ('Peptide Sequence' in column_dict
            and 'Variable Modifications' in column_dict):
            peptide = self.GetCellValue(row, column_dict['Peptide Sequence'])

            #Get Variable Mods from sheet
            var_mods = self.GetCellValue(row, column_dict['Variable Modifications'])

            itraq = (peak_viewer.itraq_radio.GetStringSelection() == "Yes")
            carb = (peak_viewer.carb_radio.GetStringSelection() == "Yes")
            peptide = mz_pep_format(peptide, modifications=var_mods, iTRAQ=itraq, carb=carb)

            peak_viewer.peptide_text.SetValue(peptide)

        wx.EndBusyCursor()

        #reset frame size
        peak_viewer.SendSizeEvent()
        peak_viewer.Raise()

    def get_selection(self, rows, cols):
        data = self._table.model.get_selection(rows, cols)
        return '\n'.join('\t'.join(str(r) if r is not None else '' for r in row) for row in data)

    def get_image(self, row, col, fig=None):
        datacol = col in self._table.model.md_cols
        imcol = col in self._table.model.im_cols

        if 'Accession Number' in self._table.model.col_dict:
            prot_acc = self._table.model.get_item_text(row, self._table.model.col_dict['Accession Number'])
        else:
            prot_acc = ''

        if 'Protein Description' in self._table.model.col_dict:
            prot_desc = self._table.model.get_item_text(row, self._table.model.col_dict['Protein Description'])
        else:
            prot_desc = ''

        if prot_acc and prot_desc:
            title = "%s - %s" % (prot_acc, prot_desc)
        else:
            title = (prot_acc or prot_desc or col)

        if datacol:
            tag,tup = self._table.model.get_metadata(row, col)

            return ((title, tag) + (self.image_methods[tag](fig, *tup) or (None,) ))
        elif imcol:
            im = cStringIO.StringIO(self._table.model.get_image_data(row, col))
            mywximage = wx.ImageFromStream(im)

            return (title, mywximage)

    def reset(self, table_name=None, query=None, page=None, rows_per_page=None):
        self._table.reset_view(self, table_name, query, page, rows_per_page)


class ReportViewer(wx.Frame):
    def __init__(self, parent, file_name):
        wx.Frame.__init__(self, parent, -1, "Viewing: %s" % os.path.basename(file_name))

        pane = wx.Panel(self, -1, style = wx.TAB_TRAVERSAL | wx.CLIP_CHILDREN)

        self.file_name = file_name

        self.peak_viewer = None

        isMZD = file_name.lower().endswith('.mzd')

        menu_bar = wx.MenuBar()

        file_menu = wx.Menu()

        file_item = file_menu.Append(-1, "Connect to &File\tCtrl+F")
        self.Bind(wx.EVT_MENU, self.on_mz_file, file_item)

        url_item = file_menu.Append(-1, "Connect to &URL\tCtrl+U")
        self.Bind(wx.EVT_MENU, self.on_mz_url, url_item)

        if isMZD:
            file_menu.AppendSeparator()

            show_sqlite = file_menu.AppendCheckItem(-1, "Show &SQLite Control\tCtrl+S")
            show_sqlite.Check(True)
            self.Bind(wx.EVT_MENU, self.on_sqlite_check, show_sqlite)

        file_menu.AppendSeparator()

        quit_item = file_menu.Append(-1, "&Quit\tCtrl+Q")
        self.Bind(wx.EVT_MENU, self.on_close, quit_item)

        menu_bar.Append(file_menu, "&Options")

        self.SetMenuBar(menu_bar)

        self.gbs = gbs = wx.GridBagSizer(5, 5)

        if isMZD:
            self.query_stxt = wx.StaticText(pane, -1, 'Query:')
            gbs.Add( self.query_stxt, (0,0), (1,1),
                     flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT )

            #self.query_text = ExpandoTextCtrl(pane, -1, '', size=(550,-1))
            self.query_text = AutocompleteTextCtrl(pane)
            #self.query_text.Bind(EVT_ETC_LAYOUT_NEEDED, lambda e: self.Fit())
            gbs.Add( self.query_text, (0,1), (1,4), flag=wx.EXPAND )

            self.query_btn = wx.Button(pane, -1, 'Execute')
            gbs.Add( self.query_btn, (0,5), (1,1), flag = wx.EXPAND)

            self.query_text.Bind(wx.EVT_TEXT_ENTER, self.on_query)
            self.query_btn.Bind(wx.EVT_BUTTON, self.on_query)

        self.model = ReportModel(file_name)

        if isMZD:
            self.nb = flatnotebook.FlatNotebook(pane, -1)
            self.grid_ctrls = []

            conn = self.model.report.conn
            cur = conn.execute('pragma table_info(PeptideData)')
            columns = ['"%s"' % x[1] for x in cur.fetchall()]
            
            autoTerms = columns + ['SELECT', 'FROM', 'PeptideData', 'WHERE', 'DISTINCT']
            completer = list_completer(autoTerms)
            #self.query_text.AutoComplete(autoTerms)
            self.query_text.SetCompleter(completer)
            

            for i,table_name in enumerate(self.model.tables):
                p = wx.Panel(self.nb, -1)
                self.nb.AddPage(p, table_name)

                box = wx.BoxSizer()
                self.grid_ctrls.append(ReportGrid(p, -1, self.model))
                box.Add(self.grid_ctrls[i], 1, wx.ALL|wx.EXPAND, 0)
                p.SetSizerAndFit(box)

            self.nb.Bind(flatnotebook.EVT_FLATNOTEBOOK_PAGE_CHANGED, self.on_nb)

            gbs.Add(self.nb, (1,0), (1,6), flag=wx.EXPAND)

            self.on_nb(None)

            style = self.nb.GetAGWWindowStyleFlag()
            style |= (flatnotebook.FNB_NO_NAV_BUTTONS
                      | flatnotebook.FNB_NODRAG
                      | flatnotebook.FNB_NO_X_BUTTON
                      | flatnotebook.FNB_HIDE_ON_SINGLE_TAB)
            self.nb.SetAGWWindowStyleFlag(style)

            self.nb.SetDoubleBuffered(1)
            self.nb.Refresh()
        else:
            self.grid_ctrl = ReportGrid(pane, -1, self.model)

            gbs.Add(self.grid_ctrl, (1,0), (1,6), flag=wx.EXPAND)

        if isMZD:
            self.rows_text = wx.TextCtrl(pane, -1, '1000', size=(60,-1), style=wx.TE_CENTER|wx.TE_PROCESS_ENTER)
            gbs.Add(self.rows_text, (2,0), (1,2), flag=wx.ALIGN_RIGHT)
            self.rows_text.Bind(wx.EVT_TEXT_ENTER, lambda e: self.change_page(0))

            gbs.Add( wx.StaticText(pane, -1, 'rows per page', style=wx.ALIGN_LEFT),
                     (2,2), (1,1), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT)

            prev_page_btn = wx.Button(pane, -1, '<', size=(40,-1))
            gbs.Add(prev_page_btn, (2,3), (1,1), flag=wx.ALIGN_RIGHT)
            prev_page_btn.Bind(wx.EVT_BUTTON, lambda e: self.change_page(-1))

            self.page_txt = wx.TextCtrl(pane, -1, '1', size=(40,-1), style=wx.TE_CENTER|wx.TE_PROCESS_ENTER)
            gbs.Add(self.page_txt, (2,4), (1,1), flag=wx.EXPAND)
            self.page_txt.Bind(wx.EVT_TEXT_ENTER, lambda e: self.change_page(0))

            next_page_btn = wx.Button(pane, -1, '>', size=(40,-1))
            gbs.Add(next_page_btn, (2,5), (1,1), flag=wx.ALIGN_LEFT)
            next_page_btn.Bind(wx.EVT_BUTTON, lambda e: self.change_page(1))


        gbs.SetEmptyCellSize((0,0))
        gbs.AddGrowableCol(2)
        gbs.AddGrowableRow(1)

        self.Bind(wx.EVT_CLOSE, self.on_close)

        box = wx.BoxSizer()
        box.Add(gbs, 1, wx.EXPAND|wx.ALL, 5)

        pane.SetSizerAndFit(box)
        self.SetMinSize((800,600))
        self.SetClientSize(pane.GetSize())

    def connect(self, mz_file):
        from gui.peak_viewer import PeakViewer

        if self.peak_viewer is None:
            self.peak_viewer = PeakViewer(self.GetParent(), self.GetIcon())
            self.peak_viewer.report_viewer = self
        else:
            for k in self.peak_viewer.mz_files:
                self.peak_viewer.mz_files[k].close()
            self.peak_viewer.mz_files.clear()

            self.peak_viewer.clear_plots()
            self.peak_viewer.Refresh()

        self.peak_viewer.mz_file_text.SetValue(mz_file)
        self.peak_viewer.mz_file_name = mz_file
        self.peak_viewer.mz_files[mz_file] = mzFile(mz_file)

        self.peak_viewer.report_dir = os.path.dirname(os.path.abspath(self.file_name))

        self.peak_viewer.openMz = True

        self.peak_viewer.Show()
        self.peak_viewer.on_all_panels(None)

    def on_mz_file(self, event):
        file_chooser = wx.FileDialog(self, "Choose Input File:", wildcard=MZ_WILDCARD, style=wx.FD_OPEN)
        if file_chooser.ShowModal() == wx.ID_OK:
            self.connect(file_chooser.GetPath())

        file_chooser.Destroy()
        self.Raise()

    def on_mz_url(self, event):
        url_chooser = wx.TextEntryDialog(self, "Enter an mzServer URL",
                                         'Connect to URL', '')
        if url_chooser.ShowModal() == wx.ID_OK:
            url_val = url_chooser.GetValue()

            report_dir = os.path.dirname(os.path.abspath(self.file_name))
            mz_file = find_mz_file(report_dir, url_val)

            if mz_file is not None:
                self.connect(mz_file)
            else:
                wx.MessageBox('No file found at this URL',
                              'Invalid URL')

        url_chooser.Destroy()
        self.Raise()

    def on_sqlite_check(self, event):
        self.gbs.Show(self.query_stxt, event.Checked())
        self.gbs.Show(self.query_text, event.Checked())
        self.gbs.Show(self.query_btn, event.Checked())

        self.gbs.Layout()

    def on_query(self, event):
        query = self.query_text.GetValue()
        self.query_text.CommitLine()
        query = ''.join(query.split('\n'))
        self.query_text.SetValue(query) # strip out the newlines
        self.Refresh()

        table_name = self.model.tables[self.nb.GetSelection()]
        self.grid_ctrls[self.nb.GetSelection()].reset(table_name=table_name, query=query)

        self.Fit()
        self.Refresh()

    def change_page(self, offset):
        try:
            rows_per_page = int(self.rows_text.GetValue())
        except ValueError:
            rows_per_page = 1000

        try:
            page = int(self.page_txt.GetValue()) + offset
        except ValueError:
            page = 1

        if rows_per_page < 1 or page < 1:
            rows_per_page = 1000
            page = 1

        self.rows_text.SetValue(str(rows_per_page))
        self.page_txt.SetValue(str(page))

        table_name = self.model.tables[self.nb.GetSelection()]

        self.grid_ctrls[self.nb.GetSelection()].reset(table_name, None, page, rows_per_page)

        self.query_text.Clear()
        self.Refresh()

    def on_nb(self, event):
        self.grid_ctrls[self.nb.GetSelection()].reset(table_name=self.model.tables[self.nb.GetSelection()])
        self.Refresh()

    def on_close(self, event):
        if self.peak_viewer is not None:
            self.peak_viewer.mzd_browser = None

        self.model.close()
        self.Destroy()
        if __name__ == '__main__': # or self.standalone:
            wx.GetApp().Exit()
            import sys
            sys.exit()

