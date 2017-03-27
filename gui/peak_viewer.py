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

import os
import re

import wx
import wx.grid
import wx.lib.splitter as splitter

from matplotlib.ticker import ScalarFormatter

import wxmpl

from numpy import array, hypot

import multiplierz.mzReport

from multiplierz.mzAPI import mzFile
from multiplierz.mass_biochem import fragment, mz_pep_format
from multiplierz.mzTools.mz_image import ion_color_dict
import multiplierz.mzTools.mz_image as mz_image

from mzDesktop import settings #, MZ_WILDCARD

from multiplierz.mzGUI_standalone import report_chooser, file_chooser, MZ_WILDCARD

from gui.fragment import FragTable as FT

_ITRAQ_IONS = (114.11, 115.11, 116.12, 117.12)




# Originally from multiplierz.mzTools.precursor_peaks.py .
def add_centroid_scan_points(scan):
    scan_data = []
    for sc in scan:
        # add data point with zeros before and after
        scan_data.extend(((sc[0],0), sc, (sc[0],0)))

    return scan_data



class mzPlot(wx.Frame):
    def __init__(self, parent=None, title="mzPlot", size=(600,450)):
        wx.Frame.__init__(self, parent, -1, title, size=size)

        self.xy_data = None
        self.last_anno = None
        self.tooltip_str = '%%3.1f, %%3d' # default tooltip string

        #Icon
        self.SetIcon(wx.Icon(os.path.join(install_dir, 'images', 'icons', 'multiplierz.ico'),
                             wx.BITMAP_TYPE_ICO))

        #add menu bar
        menu_bar = wx.MenuBar()

        #Edit Menu
        edit_menu = wx.Menu()

        change_title = edit_menu.Append(-1, 'Change &Title\tCtrl+T', 'Change Plot Title')
        self.Bind(wx.EVT_MENU, self.on_title, change_title)

        x_label = edit_menu.Append(-1, 'Change &X Axis Label\tCtrl+X', 'Change X Axis Label')
        self.Bind(wx.EVT_MENU, self.on_xlabel, x_label)

        y_label = edit_menu.Append(-1, 'Change &Y Axis Label\tCtrl+Y', 'Change Y Axis Label')
        self.Bind(wx.EVT_MENU, self.on_ylabel, y_label)

        menu_bar.Append(edit_menu, "&Edit")

        save_menu = wx.Menu()

        save_image = save_menu.Append(-1, '&Save Image\tCtrl+S', 'Save Plot as Image')
        self.Bind(wx.EVT_MENU, self.on_save, save_image)

        menu_bar.Append(save_menu, "&Save")

        resize_menu = wx.Menu()

        resize_800 = resize_menu.Append(-1, "800x600\tAlt+1", "Resize Plot to 800x600")
        self.Bind(wx.EVT_MENU, lambda e: self.on_resize((800,600)), resize_800)

        resize_1200 = resize_menu.Append(-1, "1200x900\tAlt+2", "Resize Plot to 1200x900")
        self.Bind(wx.EVT_MENU, lambda e: self.on_resize((1200,900)), resize_1200)

        resize_1400 = resize_menu.Append(-1, "1400x1050\tAlt+3", "Resize Plot to 1400x1050")
        self.Bind(wx.EVT_MENU, lambda e: self.on_resize((1400,1050)), resize_1400)

        menu_bar.Append(resize_menu, "&Resize")

        self.SetMenuBar(menu_bar)

        self.plot_panel = wxmpl.PlotPanel(self, -1, (1.6, 1.2))
        self.plot_panel.mpl_connect('button_release_event', self.on_click)

        self.figure = self.plot_panel.get_figure()
        a = self.figure.add_axes([0.125, 0.1, 0.775, 0.8])
        a.set_title(title)

        self.plot_panel.draw()

        box = wx.BoxSizer()
        box.Add(self.plot_panel, 1, wx.EXPAND, 0)
        self.SetSizerAndFit(box)
        self.SetSize(size)

    def on_resize(self, size):
        self.SetSize(size)
        self.SendSizeEvent()

    def on_title(self, event):
        with wx.TextEntryDialog(self, 'Title this graph',
                                'Enter Graph Title',
                                self.GetTitle()) as title_dlg:
            if title_dlg.ShowModal() == wx.ID_OK:
                title = title_dlg.GetValue()
                self.SetTitle(title)
                self.figure.get_axes()[0].set_title(title)
                self.plot_panel.draw()

    def on_xlabel(self, event):
        with wx.TextEntryDialog(self, 'Change X-Axis Label',
                                'Enter X-Axis Label',
                                self.figure.get_axes()[0].get_xlabel()) as xlabel_dlg:
            if xlabel_dlg.ShowModal() == wx.ID_OK:
                title = xlabel_dlg.GetValue()
                self.figure.get_axes()[0].set_xlabel(title)
                self.plot_panel.draw()

    def on_ylabel(self, event):
        with wx.TextEntryDialog(self, 'Change Y-Axis Label',
                                'Enter Y-Axis Label',
                                self.figure.get_axes()[0].get_ylabel()) as ylabel_dlg:
            if ylabel_dlg.ShowModal() == wx.ID_OK:
                title = ylabel_dlg.GetValue()
                self.figure.get_axes()[0].set_ylabel(title)
                self.plot_panel.draw()

    def on_save(self, event):
        wildcard = ("PNG (*.png)|*.png|"
                    "PDF (*.pdf)|*.pdf|"
                    "PS (*.ps)|*.ps|"
                    "EPS (*.eps)|*.eps|"
                    "SVG (*.svg)|*.svg")
        formats = ('PNG', 'PDF', 'PS', 'EPS', 'SVG')

        with wx.FileDialog(self, "Save figure as...",
                           wildcard=wildcard, style=wx.FD_SAVE) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                self.plot_panel.print_figure(dlg.GetPath(),
                                             format=formats[dlg.GetFilterIndex()])

    def closest_point(self, event):
        if self.xy_data is None:
            return None

        axes = event.canvas.figure.get_axes()[0]

        xlim = axes.get_xlim()
        ylim = axes.get_ylim()

        xy_data = [(x,y) for x,y in self.xy_data
                   if xlim[0] <= x <= xlim[1] and ylim[0] <= y <= ylim[1]]

        if not xy_data:
            return None

        e_xy = array([event.x, event.y])

        xy = min((axes.transData.transform([x,y]) for x,y in xy_data),
                 key = lambda xy: hypot(*(e_xy - xy)))

        # 10 pixel threshold for labeling
        if all(abs(xy - e_xy) < 10.0):
            return (tuple(abs(axes.transData.inverted().transform(xy))),
                    tuple(axes.transData.inverted().transform(xy+5)))
        else:
            return None

    def on_click(self, event):
        '''Annotate the point closest to the cursor if it is within range'''

        if event.inaxes:
            xy_o = self.closest_point(event)
            if xy_o:
                xy,o = xy_o

                if self.last_anno is not None:
                    self.last_anno.remove()

                tip = self.tooltip_str % xy

                axes = self.figure.get_axes()[0]

                t = axes.text(o[0], o[1], tip)
                self.last_anno = t
                event.canvas.draw()

                return

        if self.last_anno is not None:
            self.last_anno.remove()
            self.last_anno = None

        event.canvas.draw()

    def plot(self, *args, **kwargs):
        '''A simple wrapper for matplotlib's axes.plot() function. If you
        want to do something more complicated, you can access the figure
        directly using mzPlot.figure'''

        self.figure.clear()
        axes = self.figure.add_axes([0.125, 0.1, 0.775, 0.8])
        self.xy_data = axes.plot(*args, **kwargs)[0].get_xydata()

        self.plot_panel.draw()

    def plot_xic(self, title="XIC", data=None, scan_dot=None, other_MS2s=None):
        if data is None:
            raise TypeError("Required argument 'data' cannot be None")

        self.tooltip_str = '(%%3.%df, %%3.%df)' % (settings.xic_time_figs,
                                                   settings.xic_int_figs)

        mz_image._make_xic(self.figure, None,
                           [x for x,y in data],
                           [y for x,y in data],
                           scan_dot,
                           [x for x,y in other_MS2s] if other_MS2s else [],
                           [y for x,y in other_MS2s] if other_MS2s else [],
                           title)

        self.plot_panel.draw()

    def plot_full_ms(self, title="Full MS", scan=None, scan_mz=None):
        if scan is None:
            raise TypeError("Required argument 'scan' cannot be None")

        self.tooltip_str = '(%%3.%df, %%3.%df)' % (settings.ms1_mz_figs,
                                                   settings.ms1_int_figs)

        mz_image._make_ms1(self.figure,
                           None,
                           scan,
                           scan.mode,
                           [scan_mz] if scan_mz else None,
                           title,
                           settings.MS1_view_mz_window / 2)

        self.plot_panel.draw()

    def plot_ms_ms(self, title="MS-MS", scan=None):
        if scan is None:
            raise TypeError("Required argument 'scan' cannot be None")

        self.tooltip_str = '(%%3.%df, %%3.%df)' % (settings.ms2_mz_figs,
                                                   settings.ms2_int_figs)

        mz_image._make_ms2(self.figure,
                           scan,
                           scan.mode,
                           None,
                           title=title)

        self.plot_panel.draw()

    def plot_venn(self, A, B, AB, A_label, B_label, title='Venn Diagram', eps=0.001):
        '''Plot a proportional 2-set Venn diagram. A and B are the sizes of the two sets,
        AB is the size of the intersection, and eps is an error margin for the proportional
        placement. E.g. if eps is 0.01 then the areas of the plot will be accurate to ~1%.

        A lower eps will give a more accurate plot at the expense of longer running time.
        The method uses a bisecting search algorithm to find the right proportions.'''

        mz_image.make_venn(self.figure, A, B, AB, A_label, B_label, title, eps)

        self.plot_panel.draw()









class PeakViewer(wx.Frame):
    def __init__(self, parent, icon=None, mz_file=None):
        wx.Frame.__init__(self, parent, -1, "Multiplierz - Peak Viewer", size=(1200,900))
        self.SetMinSize((800,600))

        self.SetIcon(parent.GetIcon() if parent else icon)

        self.Bind(wx.EVT_CLOSE, self.on_exit)

        # menu bar
        menu_bar = wx.MenuBar()

        view_menu = wx.Menu()

        all_panels = view_menu.Append(-1, "&All Panels\tCtrl+1",
                                      "Show All Panels")
        self.Bind(wx.EVT_MENU, self.on_all_panels, all_panels)

        all_plots = view_menu.Append(-1, "A&ll Plots\tCtrl+2",
                                     "Show All Plots")
        self.Bind(wx.EVT_MENU, self.on_all_plots, all_plots)

        view_menu.AppendSeparator()

        self.show_ctrl_panel = view_menu.AppendCheckItem(-1, "&Control Panel\tCtrl+Space",
                                                         "Show Control Panel")
        self.show_ctrl_panel.Check(True)
        self.Bind(wx.EVT_MENU, self.on_show_ctrl, self.show_ctrl_panel)

        self.show_XIC = view_menu.AppendCheckItem(-1, "&XIC Plot\tCtrl+3",
                                                  "Show XIC Plot Panel")
        self.show_XIC.Check(True)
        self.Bind(wx.EVT_MENU,
                  lambda e: self.show_plot(self.show_XIC, 0, self.XIC_pane),
                  self.show_XIC)

        self.show_MS1 = view_menu.AppendCheckItem(-1, "&Precursor Mass Plot\tCtrl+4",
                                                  "Show Precursor Mass Plot Panel")
        self.show_MS1.Check(True)
        self.Bind(wx.EVT_MENU,
                  lambda e: self.show_plot(self.show_MS1,
                                           1 if self.show_XIC.IsChecked() else 0,
                                           self.MS1_pane),
                  self.show_MS1)

        self.show_MS2 = view_menu.AppendCheckItem(-1, "&MS/MS Scan Plot\tCtrl+5",
                                                  "Show MS/MS Scan Plot Panel")
        self.show_MS2.Check(True)
        self.Bind(wx.EVT_MENU,
                  lambda e: self.show_plot(self.show_MS2, 2, self.MS2_pane),
                  self.show_MS2)

        view_menu.AppendSeparator()

        show_frag = view_menu.Append(-1, "Show Fragment Ions\tCtrl+F",
                                          "Show theoretical fragment ions")
        self.Bind(wx.EVT_MENU, self.on_frag, show_frag)

        self.view_iTRAQ = view_menu.AppendCheckItem(-1, "Show iTRAQ\tCtrl+I",
                                                    "Zoom in on iTRAQ ion range")
        self.view_iTRAQ.Check(False)
        self.Bind(wx.EVT_MENU, self.on_view_iTRAQ, self.view_iTRAQ)

        view_menu.AppendSeparator()

        exit_item = view_menu.AppendCheckItem(-1, "&Quit\tCtrl+Q",
                                              "Quit")
        self.Bind(wx.EVT_MENU, self.on_exit, exit_item)

        menu_bar.Append(view_menu, "&View")


        # save menu
        save_menu = wx.Menu()
        save_XIC = save_menu.Append(-1, "Save &XIC Plot",
                                    "Save XIC Plot")
        self.Bind(wx.EVT_MENU, lambda e: self.on_save(self.XIC_plot_panel), save_XIC)

        save_MS1 = save_menu.Append(-1, "Save &Precursor Mass Plot",
                                   "Save Precursor Mass Plot")
        self.Bind(wx.EVT_MENU, lambda e: self.on_save(self.MS1_plot_panel), save_MS1)

        save_MS2 = save_menu.Append(-1, "Save &MS/MS Scan Plot",
                                    "Save MS/MS Scan Plot")
        self.Bind(wx.EVT_MENU, lambda e: self.on_save(self.MS2_plot_panel), save_MS2)

        menu_bar.Append(save_menu, "&Save")


        # tool menu
        tools_menu = wx.Menu()

        report_view = tools_menu.Append(-1, "&Connect to Report", "Connect to a Multiplierz Report")
        self.Bind(wx.EVT_MENU, self.on_rep_file, report_view)

        scans_table = tools_menu.Append(-1, "Display Scan &Table", "Display Table of All Scans")
        self.Bind(wx.EVT_MENU, self.on_scans_table, scans_table)

        menu_bar.Append(tools_menu, "&Tools")


        # scrapbook menu
        scrapbook_menu = wx.Menu()
        scrapbook_XIC = scrapbook_menu.Append(-1, "Add &XIC Plot",
                                              "Add XIC Plot to Scrap Book")
        self.Bind(wx.EVT_MENU, lambda e: self.on_scrapbook('XIC'), scrapbook_XIC)

        scrapbook_MS1 = scrapbook_menu.Append(-1, "Add &Precursor Mass Plot",
                                              "Add Precursor Mass Plot to Scrap Book")
        self.Bind(wx.EVT_MENU, lambda e: self.on_scrapbook('MS1'), scrapbook_MS1)

        scrapbook_MS2 = scrapbook_menu.Append(-1, "Add &MS/MS Scan Plot",
                                              "Add &MS/MS Scan Plot to Scrap Book")
        self.Bind(wx.EVT_MENU, lambda e: self.on_scrapbook('MS2'), scrapbook_MS2)

        menu_bar.Append(scrapbook_menu, "Scrap &Book")

        self.SetMenuBar(menu_bar)


        # main panel
        main_panel = wx.Panel(self, -1)
        #main_panel.SetBackgroundColour(wx.Colour(255,255,255))

        # control options
        ctrl_pane = self.control_panel = wx.Panel(main_panel, -1, style=wx.BORDER_SUNKEN|wx.TAB_TRAVERSAL)
        #ctrl_pane.SetBackgroundColour(wx.Colour(255,255,255))

        gbs = wx.GridBagSizer(10, 5)

        title_text = wx.StaticText(ctrl_pane, -1, 'Peak Viewer', style=wx.ALIGN_CENTER)
        title_text.SetFont(wx.Font(15, wx.DEFAULT, wx.NORMAL, wx.BOLD))

        gbs.Add( title_text,
                 (0,0), (1,6), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_CENTER )

        gbs.Add( wx.StaticText(ctrl_pane, -1, 'Peak Data File', style=wx.ALIGN_RIGHT),
                 (1,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT )

        self.mz_file_text = wx.TextCtrl(ctrl_pane, -1, '', style = wx.TE_PROCESS_ENTER)
        self.mz_file_text.Bind(wx.EVT_TEXT_ENTER, self.on_ms_enter)
        gbs.Add( self.mz_file_text,
                 (1,1), (1,4), flag=wx.EXPAND )

        ms_file_btn = wx.Button(ctrl_pane, -1, 'Browse')
        ms_file_btn.Bind(wx.EVT_BUTTON, self.on_ms_file)
        gbs.Add( ms_file_btn,
                 (1,5) )

        #gbs.Add( wx.StaticText(ctrl_pane, -1, 'Multiplierz File', style=wx.ALIGN_RIGHT),
                 #(2,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT )

        #self.rep_file_text = wx.TextCtrl(ctrl_pane, -1, '')
        #gbs.Add( self.rep_file_text,
                 #(2,1), (1,4), flag=wx.EXPAND )

        #rep_file_btn = wx.Button(ctrl_pane, -1, 'Browse')
        #rep_file_btn.Bind(wx.EVT_BUTTON, self.on_rep_file)
        #gbs.Add( rep_file_btn,
                 #(2,5) )

        gbs.Add( wx.StaticText(ctrl_pane, -1, 'm/z Range', style=wx.ALIGN_RIGHT),
                 (3,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT )

        self.mz_start = wx.TextCtrl(ctrl_pane, -1, '', size=(50,-1))
        gbs.Add( self.mz_start,
                 (3,1) )

        gbs.Add( wx.StaticText(ctrl_pane, -1, '-', style=wx.ALIGN_CENTER),
                 (3,2), flag=wx.ALIGN_CENTER )

        self.mz_end = wx.TextCtrl(ctrl_pane, -1, '', size=(50,-1))
        gbs.Add( self.mz_end,
                 (3,3) )

        gbs.Add( wx.StaticText(ctrl_pane, -1, 'Time Range', style=wx.ALIGN_RIGHT),
                 (4,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT )

        self.time_start = wx.TextCtrl(ctrl_pane, -1, '', size=(50,-1))
        gbs.Add( self.time_start,
                 (4,1) )

        gbs.Add( wx.StaticText(ctrl_pane, -1, '-', style=wx.ALIGN_CENTER),
                 (4,2), flag=wx.ALIGN_CENTER )

        self.time_end = wx.TextCtrl(ctrl_pane, -1, '', size=(50,-1))
        gbs.Add( self.time_end,
                 (4,3) )

        plot_btn = wx.Button(ctrl_pane, -1, 'Plot')
        plot_btn.Bind(wx.EVT_BUTTON, lambda e: self.on_plot_XIC(0.0, 0.0))
        gbs.Add( plot_btn,
                 (3,4), (2,1), flag=wx.ALIGN_CENTER )


        gbs.Add( wx.StaticText(ctrl_pane, -1, 'Peptide', style=wx.ALIGN_RIGHT),
                 (6,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT )

        self.peptide_text = wx.TextCtrl(ctrl_pane, -1, '')
        gbs.Add( self.peptide_text,
                 (6,1), (1,4), flag=wx.EXPAND )

        gbs.Add( wx.StaticText(ctrl_pane, -1, 'iTRAQ', style=wx.ALIGN_RIGHT),
                 (7,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT )

        self.itraq_radio = wx.RadioBox(ctrl_pane, -1, choices=['Yes','No'])
        self.itraq_radio.SetSelection(1)
        gbs.Add( self.itraq_radio,
                 (7,1), (1,3) )
        self.itraq_radio.Bind(wx.EVT_RADIOBOX, self.format_peptide)

        gbs.Add( wx.StaticText(ctrl_pane, -1, 'Carbamidomethyl', style=wx.ALIGN_RIGHT),
                 (8,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT )

        self.carb_radio = wx.RadioBox(ctrl_pane, -1, choices=['Yes','No'])
        self.carb_radio.SetSelection(1)
        gbs.Add( self.carb_radio,
                 (8,1), (1,3) )
        self.carb_radio.Bind(wx.EVT_RADIOBOX, self.format_peptide)

        gbs.Add( wx.StaticText(ctrl_pane, -1, 'Ions:', style=wx.ALIGN_RIGHT),
                 (9,0), (4,1), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT )

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
        ion_coord = [(x,y) for x in range(9,12) for y in range(1,6)]

        for i,c,(x,y) in zip(ion_list,ion_code,ion_coord):
            self.ions[i] = wx.CheckBox(ctrl_pane, -1, i, name=c)
            gbs.Add( self.ions[i],
                     (x,y) )

        self.one_plus = wx.CheckBox(ctrl_pane, -1, '1+ ions')
        gbs.Add( self.one_plus,
                 (13,1) )

        self.two_plus = wx.CheckBox(ctrl_pane, -1, '2+ ions')
        gbs.Add( self.two_plus,
                 (13,2) )

        self.ions['b'].SetValue(True)
        self.ions['y'].SetValue(True)
        self.one_plus.SetValue(True)

        self.show_table = wx.CheckBox(ctrl_pane, -1, 'Show Table')
        gbs.Add( self.show_table,
                 (13,4), (1,2) )

        frag_btn = wx.Button(ctrl_pane, -1, 'Fragment')
        gbs.Add( frag_btn,
                 (14,1), (1,3), flag=wx.ALIGN_CENTER_HORIZONTAL|wx.ALIGN_TOP )
        frag_btn.Bind(wx.EVT_BUTTON, self.on_frag)

        self.frag_clear = wx.Button(ctrl_pane, -1, 'Clear')
        gbs.Add( self.frag_clear,
                 (14,4), flag=wx.ALIGN_TOP )
        self.frag_clear.Bind(wx.EVT_BUTTON, self.on_frag_clear)

        #gbs.AddGrowableCol(6,1)
        #gbs.AddGrowableRow(5,1)
        #gbs.AddGrowableRow(14,1)

        box = wx.BoxSizer()
        box.Add(gbs, 1, wx.ALL|wx.EXPAND, 5)
        ctrl_pane.SetSizerAndFit(box)


        # the plot panels
        splitter_pane = wx.Panel(main_panel, -1)
        #splitter_pane.SetBackgroundColour(wx.Colour(255,255,255))

        splitter_window = self.splitter_window = splitter.MultiSplitterWindow(splitter_pane, -1)
        splitter_window.SetOrientation(wx.VERTICAL)

        self.last_anno = {'XIC': None,
                          'MS1': None,
                          'MS2': None}

        self.last_frag_anno = None

        self.XIC_data = None  # xic data
        self.report_data = [] # mascot xls data

        self.MS1_data = None
        self.MS2_data = None

        # XIC panel
        XIC_pane = self.XIC_pane = wx.Panel(splitter_window, -1, size = (1, 1),
                                            style=wx.TAB_TRAVERSAL)
        #XIC_pane.SetBackgroundColour(wx.Colour(255,255,255))

        XIC_gbs = wx.GridBagSizer(5,5)

        XIC_rim = wx.Panel(XIC_pane, -1, style = wx.SUNKEN_BORDER)

        #self.XIC_plot_panel = wxmpl.PlotPanel(XIC_pane, -1, (1.6,1.2))
        self.XIC_plot_panel = wxmpl.PlotPanel(XIC_rim, -1)
        self.XIC_figure = self.XIC_plot_panel.get_figure()
        #a = self.XIC_figure.add_axes([0.1, 0.2, 0.85, 0.7])
        #a = self.XIC_figure.add_axes([0.125, 0.1, 0.775, 0.6])
        a = self.XIC_figure.add_axes([0.06, 0.1, 0.9, 0.825])

        #a.set_xlabel("Retention Time (seconds)")
        #a.set_ylabel("Intensity")
        #a.get_yaxis().get_major_formatter().set_powerlimits((3, 3))
        a.ticklabel_format(scilimits = (3, 4))

        self.XIC_plot_panel.mpl_connect('button_release_event',
                                        lambda e: self.on_click(e, 'XIC'))
        self.XIC_plot_panel.mpl_connect('pick_event', self.on_XIC_click)

        
        
        #XIC_gbs.Add(self.XIC_plot_panel, (0,0), (1,6), flag=wx.EXPAND)
        rimBox = wx.GridSizer()
        rimBox.Add(self.XIC_plot_panel, flag = wx.EXPAND)
        XIC_rim.SetSizerAndFit(rimBox)
        #XIC_gbs.Add(XIC_rim, (0,0), (1,6), flag=wx.EXPAND)

        self.XIC_plot_panel.draw()

        XICvtw = settings.XIC_view_time_window

        # buttons for incrementing time
        dec_start_time = wx.Button(XIC_pane, -1, '<', size=(20,20))
        dec_start_time.Bind(wx.EVT_BUTTON,
                            lambda e: self.on_plot_XIC(-XICvtw, 0.0))
        XIC_gbs.Add(dec_start_time, (0,0), flag=wx.ALIGN_RIGHT)

        inc_start_time = wx.Button(XIC_pane, -1, '>', size=(20,20))
        inc_start_time.Bind(wx.EVT_BUTTON,
                            lambda e: self.on_plot_XIC(XICvtw, 0.0))
        XIC_gbs.Add(inc_start_time, (0,1), flag=wx.ALIGN_LEFT)

        shrink_btn = wx.Button(XIC_pane, -1, "Shrink")
        shrink_btn.Bind(wx.EVT_BUTTON,
                        lambda e: self.on_plot_XIC(XICvtw, -XICvtw))
        XIC_gbs.Add(shrink_btn, (0,3), flag=wx.ALIGN_RIGHT)

        expand_btn = wx.Button(XIC_pane, -1, "Expand")
        expand_btn.Bind(wx.EVT_BUTTON,
                        lambda e: self.on_plot_XIC(-XICvtw, XICvtw))
        XIC_gbs.Add(expand_btn, (0,7), flag=wx.ALIGN_LEFT)

        dec_end_time = wx.Button(XIC_pane, -1, '<', size=(20,20))
        dec_end_time.Bind(wx.EVT_BUTTON,
                          lambda e: self.on_plot_XIC(0.0, -XICvtw))
        XIC_gbs.Add(dec_end_time, (0,9), flag=wx.ALIGN_RIGHT)

        inc_end_time = wx.Button(XIC_pane, -1, '>', size=(20,20))
        inc_end_time.Bind(wx.EVT_BUTTON,
                          lambda e: self.on_plot_XIC(0.0, XICvtw))
        XIC_gbs.Add(inc_end_time, (0,10), flag=wx.ALIGN_LEFT)

        xicLabel = wx.StaticText(XIC_pane,
                                 label = "Peak XIC         (Intensity x Retention Time)")
        XIC_gbs.Add(xicLabel, (0, 5), flag = wx.ALIGN_TOP)

        #XIC_gbs.AddGrowableCol(2, 1)
        #XIC_gbs.AddGrowableCol(3, 1)
        ##XIC_gbs.AddGrowableCol(2, 1)
        XIC_gbs.AddGrowableCol(2)
        XIC_gbs.AddGrowableCol(4)
        XIC_gbs.AddGrowableCol(6)
        XIC_gbs.AddGrowableCol(8)
        XIC_gbs.AddGrowableRow(0)

        box = wx.BoxSizer(wx.VERTICAL)
        #box.Add(XIC_gbs, 1, wx.EXPAND, 0)
        box.Add(XIC_rim, 1, wx.EXPAND, 0)
        box.Add(XIC_gbs, proportion = 0, flag = wx.EXPAND | wx.ALIGN_CENTER, border = 0)
        XIC_pane.SetSizerAndFit(box)

        #splitter_window.AppendWindow(XIC_rim)
        splitter_window.AppendWindow(XIC_pane)

        # MS1 panel
        MS1_pane = self.MS1_pane = wx.Panel(splitter_window, -1, style=wx.TAB_TRAVERSAL)
        #MS1_pane.SetBackgroundColour(wx.Colour(255,255,255))

        MS1_gbs = wx.GridBagSizer(1,1)

        MS1_rim = wx.Panel(MS1_pane, -1, style = wx.SUNKEN_BORDER)

        self.MS1_plot_panel = wxmpl.PlotPanel(MS1_rim, -1, (1.6,1.2))
        self.MS1_figure = self.MS1_plot_panel.get_figure()
        #a = self.MS1_figure.add_axes([0.125, 0.1, 0.775, 0.8])
        #a = self.MS1_figure.add_axes([0.1, 0.2, 0.85, 0.7])
        a = self.MS1_figure.add_axes([0.06, 0.1, 0.9, 0.825])
        
        a.get_yaxis().get_major_formatter().set_powerlimits((3, 3))
        
        
        #a.set_xlabel("M/Z")
        #a.set_ylabel("Intensity")

        self.MS1_plot_panel.mpl_connect('button_release_event',
                                        lambda e: self.on_click(e, 'MS1'))
        self.MS1_plot_panel.mpl_connect('pick_event', self.on_MS1_click)


        #MS1_gbs.Add(self.MS1_plot_panel, (0,0), (1,3), flag=wx.EXPAND)
        rimBox2 = wx.GridSizer()
        rimBox2.Add(self.MS1_plot_panel, flag = wx.EXPAND)
        MS1_rim.SetSizerAndFit(rimBox2)

        self.MS1_plot_panel.draw()

        prev_ms1_btn = wx.Button(MS1_pane, -1, '<', size=(40,-1))
        MS1_gbs.Add(prev_ms1_btn, (0,0), flag=wx.ALIGN_LEFT)
        prev_ms1_btn.Bind(wx.EVT_BUTTON, lambda e: self.on_change_scan('MS1'))

        next_ms1_btn = wx.Button(MS1_pane, -1, '>', size=(40,-1))
        MS1_gbs.Add(next_ms1_btn, (0,4), flag=wx.ALIGN_RIGHT)
        next_ms1_btn.Bind(wx.EVT_BUTTON, lambda e: self.on_change_scan('MS1', True))
        
        ms1Label = wx.StaticText(MS1_pane,
                                 label = "Precursor Spectrum         (Intensity x M/Z)")
        MS1_gbs.Add(ms1Label, (0, 2), flag = wx.ALIGN_TOP)

        MS1_gbs.AddGrowableCol(1)
        MS1_gbs.AddGrowableCol(3)
        MS1_gbs.AddGrowableRow(0)

        box2 = wx.BoxSizer(wx.VERTICAL)
        box2.Add(MS1_rim, 1, wx.EXPAND, 0)
        #box2.Add(MS1_gbs, 1, wx.EXPAND, 0)
        box2.Add(MS1_gbs, proportion = 0, flag = wx.EXPAND | wx.ALIGN_CENTER, border = 0)
        MS1_pane.SetSizerAndFit(box2)

        splitter_window.AppendWindow(MS1_pane)


        #Plot MS/MS

        #MS/MS Panel
        MS2_pane = self.MS2_pane = wx.Panel(splitter_window, -1)
        #MS2_pane.SetBackgroundColour(wx.Colour(255,255,255))

        MS2_gbs = wx.GridBagSizer(1,1)
        
        MS2_rim = wx.Panel(MS2_pane, -1, style = wx.SUNKEN_BORDER)

        self.MS2_plot_panel = wxmpl.PlotPanel(MS2_rim, -1, (1.6,1.2))
        self.MS2_figure = self.MS2_plot_panel.get_figure()
        #a = self.MS2_figure.add_axes([0.125, 0.1, 0.775, 0.8])
        #a = self.MS2_figure.add_axes([0.1, 0.2, 0.85, 0.7])
        a = self.MS2_figure.add_axes([0.06, 0.1, 0.9, 0.825])
        
        a.get_yaxis().get_major_formatter().set_powerlimits((3, 3))
        
        
        #a.set_xlabel("M/Z")
        #a.set_ylabel("Intensity")

        self.MS2_plot_panel.mpl_connect('button_release_event',
                                        lambda e: self.on_click(e, 'MS2'))
        self.MS2_plot_panel.mpl_connect('pick_event', self.on_MS2_click)

        #MS2_gbs.Add(self.MS2_plot_panel, (0,0), (1,3), flag=wx.EXPAND)
        rimBox3 = wx.GridSizer()
        rimBox3.Add(self.MS2_plot_panel, flag = wx.EXPAND)
        MS2_rim.SetSizerAndFit(rimBox3)

        prev_ms2_btn = wx.Button(MS2_pane, -1, '<', size=(40,-1))
        MS2_gbs.Add(prev_ms2_btn, (0,0), flag=wx.ALIGN_LEFT)
        prev_ms2_btn.Bind(wx.EVT_BUTTON, lambda e: self.on_change_scan('MS2'))

        next_ms2_btn = wx.Button(MS2_pane, -1, '>', size=(40,-1))
        MS2_gbs.Add(next_ms2_btn, (0,4), flag=wx.ALIGN_RIGHT)
        next_ms2_btn.Bind(wx.EVT_BUTTON, lambda e: self.on_change_scan('MS2', True))

        ms2Label = wx.StaticText(MS2_pane,
                                 label = "MS2 Spectrum         (Intensity x M/Z)")
        MS2_gbs.Add(ms2Label, (0, 2), flag = wx.ALIGN_TOP)

        self.MS2_plot_panel.draw()

        MS2_gbs.AddGrowableCol(1)
        MS2_gbs.AddGrowableCol(3)
        MS2_gbs.AddGrowableRow(0)

        box3 = wx.BoxSizer(wx.VERTICAL)
        box3.Add(MS2_rim, 1, wx.EXPAND, 0)
        #box3.Add(MS2_gbs, 1, wx.EXPAND, 0)
        box3.Add(MS2_gbs, proportion = 0, flag = wx.EXPAND | wx.ALIGN_CENTER, border = 0)
        MS2_pane.SetSizerAndFit(box3)

        splitter_window.AppendWindow(MS2_pane)

        spl_box = wx.BoxSizer()
        spl_box.Add(splitter_window, 1, wx.ALL|wx.EXPAND, 0)
        splitter_pane.SetSizerAndFit(spl_box)

        splitter_window.SizeWindows()

        box = wx.BoxSizer(wx.HORIZONTAL)
        box.Add(ctrl_pane, 0, wx.ALL|wx.EXPAND, 5)
        box.Add(splitter_pane, 1, wx.ALL|wx.EXPAND, 5)
        main_panel.SetSizerAndFit(box)

        self.report_viewer = None
        self.report_dir = ''

        self.openMz = False

        self.ms2mz = 0
        self.combined_file = False

        # dictionary of mz file objects
        self.mz_files = {}

        # dictionary of IDed/other MS2 scans, per file
        #self.IDed_MS2_scans = {}
        #self.other_MS2_scans = {}

        # the current mz file
        self.mz_file_name = ''

        self.frag_data = None
        self.itraq_lines = None

        self.MS1_XIC_scans = []

        self.scrap_book = None

        self.gen_scan_table = False

        self.on_all_panels(None)

    def on_exit(self, event):
        for k in self.mz_files:
            self.mz_files[k].close()

        if self.report_viewer is not None:
            self.report_viewer.peak_viewer = None

        self.SendSizeEvent()
        self.Refresh()
        self.Destroy()

    def on_save(self, plot_panel):
        wildcard = ("PNG (*.png)|*.png|"
                    "PDF (*.pdf)|*.pdf|"
                    "PS (*.ps)|*.ps|"
                    "EPS (*.eps)|*.eps|"
                    "SVG (*.svg)|*.svg")
        formats = ('PNG', 'PDF', 'PS', 'EPS', 'SVG')
        dlg = wx.FileDialog(self, "Save figure as...",
                            wildcard=wildcard, style=wx.FD_SAVE)
        if dlg.ShowModal() == wx.ID_OK:
            plot_panel.print_figure(dlg.GetPath(), format=formats[dlg.GetFilterIndex()])
        dlg.Destroy()

    def on_scrapbook(self, plot_tag):
        data = {'XIC': self.XIC_data,
                'MS1': self.MS1_data,
                'MS2': self.MS2_data}[plot_tag]

        if not data:
            return

        if plot_tag == 'XIC':
            start_mz = self.mz_start.GetValue()
            end_mz = self.mz_end.GetValue()

            title = 'XIC: [%s - %s]' % (start_mz, end_mz)
        elif plot_tag == 'MS1':
            title = 'Precursor Mass mz: %s, time: %s' % (data[1], data[2])
        elif plot_tag == 'MS2':
            title = 'MS/MS Scan mz: %s, time: %s' % (self.ms2mz, data[1])

        title_dlg = wx.TextEntryDialog(self, 'Enter a title for this graph', 'Graph Title', title)

        if title_dlg.ShowModal() == wx.ID_OK:
            title = title_dlg.GetValue()
            if self.scrap_book == None:
                self.scrap_book = ScrapBook(self, -1)
                self.scrap_book.Show()

            self.scrap_book.add_plot(title='%d: %s' % (self.scrap_book.child_counter + 1, title),
                                     data=data,
                                     plot_tag=plot_tag)

        title_dlg.Destroy()

    def on_view_iTRAQ(self, event):
        if self.MS2_data:
            axes = self.MS2_figure.get_axes()[0]

            if self.view_iTRAQ.IsChecked():
                axes.set_xlim([113, 118])
                itraq_data = [i for i in self.MS2_data[0] if 113 <= i[0] <= 118]
                if itraq_data:
                    axes.set_ylim((0.0, max(i[1] for i in itraq_data) * 1.1))
                self.itraq_lines = [axes.axvline(x=i, ymin=0, ymax=1, ls='--', c='r')
                                    for i in _ITRAQ_IONS]
            else:
                if self.itraq_lines:
                    for i in self.itraq_lines:
                        i.remove()
                    self.itraq_lines = None
                axes.autoscale_view()

            self.MS2_plot_panel.draw()

    def on_all_panels(self, event):
        self.control_panel.Show(True)
        self.show_ctrl_panel.Check(True)
        self.show_XIC.Check(True)
        self.show_MS1.Check(True)
        self.show_MS2.Check(True)

        self.control_panel.Show(True)
        self.show_plot(self.show_XIC, 0, self.XIC_pane)
        self.show_plot(self.show_MS1, 1, self.MS1_pane)
        self.show_plot(self.show_MS2, 2, self.MS2_pane)

        self.size_plots()
        self.control_panel.GetParent().Layout()

    def on_all_plots(self, event):
        self.show_ctrl_panel.Check(False)
        self.show_XIC.Check(True)
        self.show_MS1.Check(True)
        self.show_MS2.Check(True)

        self.control_panel.Show(False)
        self.show_plot(self.show_XIC, 0, self.XIC_pane)
        self.show_plot(self.show_MS1, 1, self.MS1_pane)
        self.show_plot(self.show_MS2, 2, self.MS2_pane)

        self.size_plots()
        self.control_panel.GetParent().Layout()

    def on_show_ctrl(self, event):
        self.control_panel.Show(self.show_ctrl_panel.IsChecked())
        self.control_panel.GetParent().Layout()

    def size_plots(self, event=None):
        sashes = len(self.splitter_window._windows)
        height = self.splitter_window.GetSize()[1] / sashes

        for i in range(sashes):
            self.splitter_window.SetSashPosition(i, height)

        self.splitter_window.Refresh()

    def show_plot(self, show, index, plot_pane):
        if show.IsChecked():
            if not plot_pane.IsShown():
                plot_pane.Show(True)
                self.splitter_window.InsertWindow(index, plot_pane)
        else:
            if len(self.splitter_window._windows) == 1:
                show.Check(True)
                wx.MessageBox("Cannot hide all plots.", "View Control")
                return

            self.splitter_window.DetachWindow(plot_pane)
            plot_pane.Show(False)

        self.size_plots()

    def closest_point(self, event, plot_tag):
        thisline = event.artist
        data = thisline.get_xydata()

        ind = event.ind[0]
        ind0,ind1 = max(ind - 2, 0), min(ind + 2, len(data))

        axes = {'XIC': self.XIC_figure,
                'MS1': self.MS1_figure,
                'MS2': self.MS2_figure}[plot_tag].get_axes()[0]

        x0,x1 = axes.get_xlim()
        y0,y1 = axes.get_ylim()

        data = [(x,y) for x,y in data if x0 <= x <= x1 and y0 <= y <= y1]
        # ind is strangely unreliable, so we'll search the points around it if possible
        data = data[ind0:ind1] or data

        if not data:
            return None

        e_xy = array([event.mouseevent.x, event.mouseevent.y])

        xy = min(((x,y) for x,y in data),
                 key=lambda xy: hypot(*(e_xy - axes.transData.transform(xy))))

        if hypot(*(e_xy - axes.transData.transform(xy))) > 20:
            return None

        if plot_tag == 'XIC':
            tip = '%%3.%df, %%3.%df' % (settings.xic_time_figs,
                                        settings.xic_int_figs)
        elif plot_tag == 'MS1':
            tip = '%%3.%df, %%3.%df' % (settings.ms1_mz_figs,
                                        settings.ms1_int_figs)
        elif plot_tag == 'MS2':
            tip = '%%3.%df, %%3.%df' % (settings.ms2_mz_figs,
                                        settings.ms2_int_figs)

        tip = tip % xy

        if self.last_anno[plot_tag] is not None:
            self.last_anno[plot_tag].remove()
            self.last_anno[plot_tag] = None

        o = axes.transData.inverted().transform(axes.transData.transform(xy)+5)
        t = axes.text(o[0], o[1], tip)

        self.last_anno[plot_tag] = t

        return xy

    def on_click(self, event, plot_tag):
        '''Annotate the point closest to the cursor if it is within range'''

        if self.last_anno[plot_tag] is not None:
            self.last_anno[plot_tag].remove()
            self.last_anno[plot_tag] = None

            if plot_tag == 'MS2' and self.last_frag_anno is not None:
                self.last_frag_anno.remove()
                self.last_frag_anno = None

            event.canvas.draw()

        if event.inaxes:
            event.inaxes.pick(event)

    def on_MS1_click(self, event):
        if not (self.MS1_data and self.openMz):
            return

        self.closest_point(event, 'MS1')

        self.MS1_plot_panel.draw()

    def on_MS2_click(self, event):
        # this method displays the closest point and the closest fragment ion
        if not (self.MS2_data and self.openMz):
            return

        xy = self.closest_point(event, 'MS2')

        if not xy:
            if self.last_frag_anno is not None:
                self.last_frag_anno.remove()
                self.last_frag_anno = None
            return

        axes = self.MS2_figure.get_axes()[0]

        if self.frag_data:
            x,ion,axv = min(self.frag_data, key=lambda xi: abs(xy[0] - xi[0]))

            if self.last_frag_anno is not None:
                self.last_frag_anno.remove()

            y = axes.get_ylim()[1] * 0.9

            self.last_frag_anno = axes.text(x, y, '%3.1f: %s' % (x,ion))
        elif self.itraq_lines:
            ion = min(_ITRAQ_IONS, key=lambda i: abs(xy[0] - i))

            if self.last_frag_anno is not None:
                self.last_frag_anno.remove()

            y = axes.get_ylim()[1] * 0.9

            self.last_frag_anno = axes.text(ion, y, '%3.1f' % ion)

        self.MS2_plot_panel.draw()

    def on_XIC_click(self, event):
        if not (self.XIC_data and self.openMz):
            return

        xy = self.closest_point(event, 'XIC')

        self.XIC_plot_panel.draw()

        if not xy:
            return

        wx.BeginBusyCursor(wx.HOURGLASS_CURSOR)

        scan_time = xy[0]

        start_mz = float(self.mz_start.GetValue())
        end_mz = float(self.mz_end.GetValue())

        data = self.mz_files[self.mz_file_name].scan(scan_time)
        data.sort()

        scan_info = self.mz_files[self.mz_file_name].scan_info(scan_time-0.001,
                                                               scan_time+0.001)
        scan_info = min(scan_info, key = lambda si: abs(scan_time - si[0]))

        if scan_info[3] == 'MS1':
            # update MS1 plot
            scan_mz = float(self.ms2mz)

            self.MS1_data = (data, scan_mz, scan_time)

            self.draw_MS1_plot()
        elif scan_info[3] == 'MS2':
            # update MS2 plot
            self.MS2_data = (data, scan_time)

            self.draw_MS2_plot()

        wx.EndBusyCursor()

    def get_plot_ranges(self):
        start_time = self.time_start.GetValue()
        end_time = self.time_end.GetValue()
        start_mz = self.mz_start.GetValue()
        end_mz = self.mz_end.GetValue()

        if not all((start_time, end_time, start_mz, end_mz)):
            wx.MessageBox("Please enter time and mz ranges.", "Missing Values")
            return None
        else:
            try:
                start_time = float(start_time)
                end_time = float(end_time)
                start_mz = float(start_mz)
                end_mz = float(end_mz)
            except ValueError:
                wx.MessageBox("Ranges must be valid numbers.", "Invalid Input")
                return None

        return (start_time, end_time, start_mz, end_mz)

    def draw_XIC_plot(self, start_time, end_time, start_mz, end_mz, scan_time=None):
        if start_time >= end_time:
            wx.MessageBox("End time must be greater than start time.", "Time Window Error")
            return

        XIC_data = self.mz_files[self.mz_file_name].xic(start_time, end_time, start_mz, end_mz)

        if not XIC_data:
            wx.MessageBox("Peak integration failed.\nPlease check time and mz windows and try again.", "No XIC Data")
            return
        else:
            self.time_start.SetValue('%0.2f' % start_time)
            self.time_end.SetValue('%0.2f' % end_time)
            self.mz_start.SetValue('%0.2f' % start_mz)
            self.mz_end.SetValue('%0.2f' % end_mz)

        if self.XIC_data and self.XIC_data[1] and not scan_time:
            scan_time = self.XIC_data[1][0][0]

        
        #self.MS1_XIC_scans = []
        #extraWindow = 0
        #fullRange = self.mz_files[self.mz_file_name].time_range()
        #while not self.MS1_XIC_scans:
        scan_info = self.mz_files[self.mz_file_name].scan_info(XIC_data[0][0],
                                                               XIC_data[-1][0])
                                                               #start_mz, end_mz)

        self.MS1_XIC_scans = [s_time for (s_time,mz,n,s_type,m) in scan_info
                              if s_type == 'MS1' or s_type == 'ms']
            
            #extraWindow += 1
            #if extraWindow > (fullRange[1] - fullRange[0]):
                #raise AssertionError, "No corresponding MS1 scan exists in file!"

        ms2_scans = [(s_time,mz) for (s_time,mz,n,s_type,m) in scan_info
                     if s_type == 'MS2' or s_type == 'ms2']

        other_MS2s = []

        scan_dot = None

        for (t,mz) in ms2_scans:
            if t >= self.MS1_XIC_scans[0]:
                point1Time, point1Int = max((XICt,XICi) for XICt,XICi in XIC_data if XICt < t)
                point2Time, point2Int = min((XICt,XICi) for XICt,XICi in XIC_data if XICt >= t)
                slope = float(point2Int - point1Int) / float(point2Time - point1Time)

                intercept = point2Int - slope * point2Time

                scan_int = slope * t + intercept

                if (self.report_viewer is not None or self.gen_scan_table) and scan_time:
                    if abs(t - scan_time) <= 0.0005: # "6 ms should be enough for anybody"
                        scan_dot = (t, scan_int)
                    else:
                        # previous versions of the peak viewer would make a distinction here
                        # between IDed and non-IDed scans. That's been dropped for now, but
                        # it might come back in the future

                        other_MS2s.append((t, scan_int))
                else:
                    other_MS2s.append((t, scan_int))

        xic_time = [x for x,y in XIC_data]
        xic_int = [y for x,y in XIC_data]

        bin_times = [x for x,y in other_MS2s]
        bin_ints = [y for x,y in other_MS2s]

        self.XIC_data = (XIC_data,
                         ((scan_dot,) if scan_dot else ()),
                         tuple(other_MS2s))

        self.last_anno['XIC'] = None

        axes = self.XIC_figure.get_axes()[0]
        axes.clear()

        axes.plot(xic_time, xic_int, '--rs', linewidth=2, markeredgecolor='k',
                  markerfacecolor='g', markersize=5, picker=2.5)

        axes.ticklabel_format(axis = 'y', scilimits = (3, 4))

        if len(bin_times) > 0:
            axes.plot(bin_times, bin_ints, 'yo', markersize=7, picker=2.5)

        # plot the scan dot last, so it stays on top of other markers
        if scan_dot is not None:
            axes.plot([scan_dot[0]], [scan_dot[1]], 'b^', markersize=10, picker=2.5)

        axes.set_ylim(ymin=0.0)

        axes.xaxis.set_major_formatter(ScalarFormatter(useOffset=False, useMathText=True))

        self.XIC_plot_panel.draw()

        # reset frame size
        self.SendSizeEvent()

    def on_plot_XIC(self, dt_start, dt_end):
        '''Plots (or resizes) a XIC. dt_start and dt_end are the deltas for
        the start and end times, respectively.'''

        if not self.openMz:
            wx.MessageBox("Please select an MS data file.", "No MS Data File")
            return

        plot_ranges = self.get_plot_ranges()
        if plot_ranges is None:
            return # appropriate error message provided by that method
        else:
            (start_time, end_time, start_mz, end_mz) = plot_ranges

        wx.BeginBusyCursor(wx.HOURGLASS_CURSOR)

        first_time, last_time = self.mz_files[self.mz_file_name].time_range()

        start_time = max(start_time + dt_start, first_time + 0.00001)
        end_time = min(end_time + dt_end, last_time - 0.00001)

        self.draw_XIC_plot(start_time, end_time, start_mz, end_mz)

        wx.EndBusyCursor()

    def draw_MS1_plot(self):
        mode = self.MS1_data[0].mode

        ms1_data = self.MS1_data[0][:]

        if mode == 'c':
            ms1_data = add_centroid_scan_points(ms1_data)

        self.last_anno['MS1'] = None

        axes = self.MS1_figure.get_axes()[0]
        axes.clear()
        axes.plot([i[0] for i in ms1_data],
                  [i[1] for i in ms1_data],
                  c='k', picker=5)
        
        axes.ticklabel_format(axis = 'y', scilimits = (3, 4))

        if self.MS1_data[1]:
            half_window = settings.MS1_view_mz_window / 2
            axes.set_xlim((self.MS1_data[1] - half_window,
                           self.MS1_data[1] + half_window))
            try:
                axes.set_ylim((0.0, max(i[1] for i in ms1_data
                                        if abs(i[0] - self.MS1_data[1]) < 2.1) * 1.1))
            except ValueError:
                axes.set_ylim((0.0, max(i[1] for i in ms1_data) * 1.1))                                    
            axes.axvline(x=self.MS1_data[1], ymin=0, ymax=1, ls='--', c='b')

        axes.xaxis.set_major_formatter(ScalarFormatter(useOffset=False, useMathText=True))
        self.MS1_plot_panel.draw()

    def on_frag(self, event):
        self.view_iTRAQ.Check(False)
        if self.itraq_lines:
            for i in self.itraq_lines:
                i.remove()
            self.itraq_lines = None

        if self.last_anno['MS2'] is not None:
            self.last_anno['MS2'].remove()
            self.last_anno['MS2'] = None

        if self.last_frag_anno is not None:
            self.last_frag_anno.remove()
            self.last_frag_anno = None

        wx.BeginBusyCursor(wx.HOURGLASS_CURSOR)
        self.frag_clear.Enable(True)

        peptide = self.peptide_text.GetValue()
        if not peptide:
            wx.MessageBox('No peptide to fragment.', 'Error')
            wx.EndBusyCursor()
            return

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

        if self.show_table.IsChecked():
            try:
                frag_data = fragment_legacy(peptide, ion_array)
            except ValueError:
                wx.MessageBox('Invalid mass value.', 'Error')
                wx.EndBusyCursor()
                return
            except LookupError:
                wx.MessageBox('Invalid modification name or position.', 'Error')
                wx.EndBusyCursor()
                return

            pep_cleaner = re.compile(r'-?(\[.+?\]|[a-z])-?')

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

            #Frag Table
            tableFrame = FragTable(self, -1, "Fragment Table", row_headers, ion_array, data)
            tableFrame.Fit()
            tableFrame.SetMinSize(tableFrame.GetSize())
            tableFrame.Show(True)

        included = set(('b', 'y', 'c', 'z+1'))

        # complicated regex matches ion, location, and optional charge
        ion_re = re.compile(r'(.+)\((\d+)\).*?([\+\-]{2})?$')

        calc_masses, label_dict = fragment_legacy(peptide, ion_array, labels=True)

        axes = self.MS2_figure.get_axes()[0]
        axes.autoscale_view()

        xlim = axes.get_xlim()

        calc_masses = [c for c in calc_masses if xlim[0] < c < xlim[1]]

        if self.frag_data:
            for c,lbl,a in self.frag_data:
                a.remove()

        self.frag_data = [] # [(c,label_dict[c]) for c in calc_masses]

        for cmass in calc_masses:
            m = ion_re.match(label_dict[cmass])
            if m:
                for i in included:
                    if m.group(1).startswith(i):
                        n = m.group(1) + (m.group(3) or '')
                        if n in ion_color_dict:
                            color = ion_color_dict[n]
                        else:
                            color = 'black'

                        self.frag_data.append((cmass, label_dict[cmass],
                                               axes.axvline(x=cmass, ymin=0, ymax=1,
                                                            linewidth=0.5, ls=':', c=color)))

        self.MS2_plot_panel.draw()

        wx.EndBusyCursor()

    def on_frag_clear(self, event):
        wx.BeginBusyCursor(wx.HOURGLASS_CURSOR)

        self.draw_MS2_plot()

        wx.EndBusyCursor()

    def draw_MS2_plot(self):
        mode = self.MS2_data[0].mode

        ms2_data = self.MS2_data[0][:]

        if mode == 'c':
            ms2_data = add_centroid_scan_points(ms2_data)

        self.frag_clear.Enable(False)
        self.frag_data = None
        self.last_frag_anno = None

        self.last_anno['MS2'] = None

        axes = self.MS2_figure.get_axes()[0]
        axes.clear()
        axes.plot([i[0] for i in ms2_data],
                  [i[1] for i in ms2_data],
                  linestyle='-',
                  linewidth=0.5,
                  color='k',
                  picker=5)

        axes.ticklabel_format(axis = 'y', scilimits = (3, 4))

        if self.view_iTRAQ.IsChecked():
            axes.set_xlim([113,118])
            itraq_data = [i for i in self.MS2_data[0] if 113 <= i[0] <= 118]
            if itraq_data:
                axes.set_ylim((0.0, max(i[1] for i in itraq_data) * 1.1))
            for i in _ITRAQ_IONS:
                axes.axvline(x=i, ymin=0, ymax=1, ls='--', c='r')

        axes.xaxis.set_major_formatter(ScalarFormatter(useOffset=False, useMathText=True))
        self.MS2_plot_panel.draw()

    def on_change_scan(self, plot_tag, next_scan=False):
        scan_time = None

        if plot_tag == 'MS1':
            if self.MS1_data is not None:
                scan_time = self.MS1_data[2]
        elif plot_tag == 'MS2':
            if self.MS2_data is not None:
                scan_time = self.MS2_data[1]

        if scan_time is None:
            return

        start_time,stop_time = self.mz_files[self.mz_file_name].time_range()

        if next_scan:
            scan_times = [t for t,mz,n,st,m in self.mz_files[self.mz_file_name].scan_info(scan_time, stop_time)
                          if st == plot_tag and t > scan_time]
            if not scan_times:
                return

            new_time = min(scan_times)
        else:
            scan_times = [t for t,mz,n,st,m in self.mz_files[self.mz_file_name].scan_info(start_time, scan_time)
                          if st == plot_tag and t < scan_time]
            if not scan_times:
                return

            new_time = max(scan_times)

        new_scan = self.mz_files[self.mz_file_name].scan(new_time)

        if plot_tag == 'MS1':
            self.MS1_data = (new_scan, self.MS1_data[1], new_time)

            self.draw_MS1_plot()
        elif plot_tag == 'MS2':
            self.MS2_data = (new_scan, new_time)

            self.draw_MS2_plot()

    def format_peptide(self, event):
        peptide = self.peptide_text.GetValue()
        self.peptide_text.SetValue(mz_pep_format(peptide,
                                                 iTRAQ=(1 - self.itraq_radio.GetSelection()),
                                                 carb=(1 - self.carb_radio.GetSelection())))

        if self.frag_data:
            self.on_frag(None)

    def clear_plots(self):
        for fig,plot_panel in ((self.XIC_figure, self.XIC_plot_panel),
                               (self.MS1_figure, self.MS1_plot_panel),
                               (self.MS2_figure, self.MS2_plot_panel)):
            fig.get_axes()[0].clear()
            plot_panel.draw()

        self.last_anno = {'XIC': None,
                          'MS1': None,
                          'MS2': None}

        self.frag_clear.Enable(False)
        self.frag_data = None
        self.last_frag_anno = None

        self.XIC_data = None
        self.MS1_data = None
        self.MS2_data = None

        self.MS1_XIC_scans = []
        self.Refresh()

    def on_ms_file(self, event):
        file_chooser = wx.FileDialog(self, "Choose Input File:", wildcard=MZ_WILDCARD, style=wx.FD_OPEN)
        if file_chooser.ShowModal() == wx.ID_OK:
            for k in self.mz_files:
                self.mz_files[k].close()
            self.mz_files.clear()

            self.clear_plots()

            self.mz_file_text.SetValue(file_chooser.GetPath())

            self.mz_file_name = self.mz_file_text.GetValue()
            self.mz_files[self.mz_file_name] = mzFile(self.mz_file_name)

            self.openMz = True

        file_chooser.Destroy()
        self.Raise()
    
    def on_ms_enter(self, event):
        try:
            self.mz_file_name = self.mz_file_text.GetValue()
            assert (os.path.exists(self.mz_file_name) or self.mz_file_name[:5] == "http:")
            self.mz_files[self.mz_file_name] = mzFile(self.mz_file_name)
            self.openMz = True
            wx.MessageBox("%s has been opened successfully." % self.mz_file_name,
                          "File opened.")
        except AssertionError:
            wx.MessageBox("Incorrect path or filename.", "File not opened.")
        except NotImplementedError:
            wx.MessageBox("Indicated file is not a valid data file.", "File not opened.")
            pass
        

    def on_scans_table(self, event):
        wx.BeginBusyCursor(wx.HOURGLASS_CURSOR)

        if not self.openMz:
            wx.MessageBox("Please select a raw MS file", "No MS Data File")
            wx.EndBusyCursor()
            return

        self.combined_file = False

        scan_list = self.mz_files[self.mz_file_name].scan_list()

        self.report_data = [list(scan) for scan in scan_list if scan[1]]

        self.gen_scan_table = True

        self.report_viewer = ScansFrame(self, self.report_data, mz_file_name=self.mz_file_name)

        self.report_viewer.Show(True)
        wx.EndBusyCursor()

    def on_rep_file(self, event):
        from gui.report_viewer import ReportViewer

        file_name = report_chooser(self)

        if file_name:
            wx.BeginBusyCursor(wx.HOURGLASS_CURSOR)

            if self.combined_file:
                for k in self.mz_files:
                    self.mz_files[k].close()

            self.clear_plots()

            self.report_dir = os.path.dirname(file_name)

            report = multiplierz.mzReport.reader(file_name)

            if 'File' in report.columns:
                self.combined_file = True
            else:
                self.combined_file = False

            report.close()

            self.report_viewer = ReportViewer(self.GetParent(), file_name)
            self.report_viewer.SetIcon(self.GetIcon())
            self.report_viewer.peak_viewer = self

            self.report_viewer.Show(True)
            wx.EndBusyCursor()

    def get_icon(self):
        '''Returns the icon of the main frame, for creating new windows.
        '''
        return self.GetIcon()

    #def test_mousewheel(self, event):
        #if event.GetWheelRotation() > 0:
            #print 'mouse wheel up'
        #elif event.GetWheelRotation() < 0:
            #print 'mouse wheel down'


class ScansTable(wx.grid.PyGridTableBase):
    def __init__(self, columns, data):
        wx.grid.PyGridTableBase.__init__(self)

        self.columns = ['\n'.join(c.split()) for c in columns]
        self.data = data

        self._cols = self.GetNumberCols()
        self._rows = self.GetNumberRows()

    def GetNumberRows(self):
        return len(self.data)

    def GetNumberCols(self):
        return len(self.columns)

    def GetColLabelValue(self, col):
        return self.columns[col]

    def GetAttr(self, row, col, kind):
        pass

    def GetValue(self, row, col):
        return self.data[row][col]

    def SetValue(self, row, col, value):
        pass

    def reset_view(self, grid, data):
        self.data = data

        grid.BeginBatch()

        for current, new, delmsg, addmsg in [
            (self._rows, self.GetNumberRows(), wx.grid.GRIDTABLE_NOTIFY_ROWS_DELETED, wx.grid.GRIDTABLE_NOTIFY_ROWS_APPENDED),
            (self._cols, self.GetNumberCols(), wx.grid.GRIDTABLE_NOTIFY_COLS_DELETED, wx.grid.GRIDTABLE_NOTIFY_COLS_APPENDED)
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

        # update the scrollbars and the displayed part of the grid
        grid.AdjustScrollbars()

        grid.ForceRefresh()

    def sort_column(self, col, reverse=False):
        """
        col -> sort the data based on the column indexed by col
        """
        self.data.sort(key=lambda r: r[col], reverse=reverse)


class ScansFrame(wx.Frame):
    '''A frame for showing the scan list of a file. This class no longer deals with reports.
    Because of that, it is tied to a single file, which makes things simpler.'''

    def __init__(self, parent, data, mz_file_name):
        wx.BeginBusyCursor(wx.HOURGLASS_CURSOR)

        wx.Frame.__init__(self, parent, -1,
                          title="Peak List Table for %s" % mz_file_name,
                          size=(800,600))

        self.mz_file_name = mz_file_name
        self.SetIcon(parent.GetIcon())

        #self.column_dict = dict((c,i) for i,c in enumerate(columns))
        self.data = data

        self.sort_flag = False

        #right click menu
        self.right_click = wx.Menu()
        for i in ['Filter', 'Show All']:
            item = self.right_click.Append(-1, i)
            self.Bind(wx.EVT_MENU, self.on_filter_menu, item)
        self.right_click.FindItemByPosition(1).Enable(False)

        #mass table
        self.grid = wx.grid.Grid(self)
        #self.grid._table = ScansTable(['MS2 Time', 'mz'], data)
        self.grid._table = ScansTable(['MS2 Time', 'Experimental mz'], data)
        self.grid.SetTable(self.grid._table, True)

        self.Bind(wx.grid.EVT_GRID_CMD_CELL_LEFT_DCLICK, self.on_cell_dclick, self.grid)
        self.Bind(wx.grid.EVT_GRID_CMD_LABEL_LEFT_CLICK, self.on_label_click, self.grid)
        self.Bind(wx.grid.EVT_GRID_CMD_LABEL_RIGHT_CLICK, self.on_label_rclick, self.grid)

        self.Bind(wx.EVT_CLOSE, self.on_exit)

        wx.EndBusyCursor()

    def on_exit(self, event):
        self.GetParent().gen_scan_table = False

        if self.GetParent().XIC_data:
            self.GetParent().XIC_data = (self.GetParent().XIC_data[0],
                                         (),
                                         self.GetParent().XIC_data[2])
        self.Destroy()

    def on_cell_dclick(self, event):
        wx.BeginBusyCursor(wx.HOURGLASS_CURSOR)

        mz_file = self.mz_file_name

        row_num = self.grid.GetGridCursorRow()

        time = float(self.grid.GetCellValue(row_num, 0))
        mz = float(self.grid.GetCellValue(row_num, 1))

        self.GetParent().ms2mz = mz

        if mz_file not in self.GetParent().mz_files:
            self.GetParent().mz_files[mz_file] = mzFile(mz_file)

        first_time, last_time = self.GetParent().mz_files[mz_file].time_range()

        start_time = max(time - settings.XIC_gen_time_window / 2, first_time + 0.00001)
        end_time = min(time + settings.XIC_gen_time_window / 2, last_time)

        start_mz = mz - settings.XIC_gen_mz_window / 2
        end_mz = mz + settings.XIC_gen_mz_window / 2

        self.GetParent().draw_XIC_plot(start_time, end_time, start_mz, end_mz, time)

        # Precursor Masses Graph
        precursorScanTime = max([t for t in self.GetParent().MS1_XIC_scans if t <= time] or [time])

        data = self.GetParent().mz_files[mz_file].scan(precursorScanTime)
        data.sort()

        scan_mz = mz

        self.GetParent().MS1_data = (data, scan_mz, precursorScanTime)

        self.GetParent().draw_MS1_plot()

        # MS MS Graph
        self.GetParent().frag_clear.Enable(False)

        ms2_data = self.GetParent().mz_files[mz_file].scan(time)
        ms2_data.sort()

        self.GetParent().MS2_data = (ms2_data, time)

        self.GetParent().draw_MS2_plot()

        #reset frame size
        self.GetParent().SendSizeEvent()
        self.GetParent().Raise()

        wx.EndBusyCursor()

    def on_label_click(self, event):
        col = event.GetCol()

        if col > -1:
            self.grid._table.sort_column(col, self.sort_flag)
            self.sort_flag = not self.sort_flag

        self.grid.ForceRefresh()

    def on_label_rclick(self, event):
        self.RcColNum = event.GetCol()
        pos = event.GetPosition()
        self.PopupMenu(self.right_click, pos)

    def on_filter_menu(self, event):
        item = self.right_click.FindItemById(event.GetId())
        text = item.GetText()
        colNum = self.RcColNum

        if text == 'Filter':
            wx.BeginBusyCursor(wx.HOURGLASS_CURSOR)

            #filter dialog
            filter_dlg = wx.Dialog(self, -1, 'Filter Options', style=wx.DEFAULT_DIALOG_STYLE)
            fd_pane = wx.Panel(filter_dlg, -1)

            gbs = wx.GridBagSizer(5,5)

            gbs.Add( wx.StaticText(fd_pane, -1, self.grid.GetColLabelValue(colNum), style=wx.ALIGN_RIGHT),
                     (0,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT )

            filter_list = ['=', 'contains', '>', '<']
            options = wx.Choice(fd_pane, -1, choices=filter_list)
            gbs.Add( options,
                     (0,1) )
            options.SetSelection(0)

            filter_text = wx.TextCtrl(fd_pane, -1, "", style=wx.EXPAND)
            gbs.Add( filter_text,
                     (0,2), flag=wx.EXPAND )

            filter_btn = wx.Button(fd_pane, wx.ID_OK, "Filter")
            gbs.Add( filter_btn,
                     (1,0), (1,3), flag=wx.ALIGN_CENTER )

            gbs.AddGrowableCol(1)
            gbs.AddGrowableRow(0)

            box = wx.BoxSizer()
            box.Add(gbs, 1, wx.ALL|wx.EXPAND, 5)
            fd_pane.SetSizerAndFit(box)

            filter_dlg.Fit()

            if filter_dlg.ShowModal() == wx.ID_OK:
                self.right_click.FindItemByPosition(1).Enable(True)
                filter_opt = options.GetValue()
                filter_val = filter_text.GetValue()
            else:
                filter_dlg.Destroy()
                wx.EndBusyCursor()
                return

            filter_dlg.Destroy()

            self.sort_flag = False

            if filter_opt == '<':
                try:
                    filter_val = float(filter_val)
                except:
                    wx.MessageBox("Please enter a number.", "Data Type Error")
                    self.right_click.FindItemByPosition(1).Enable(False)

                self.grid._table.reset_view(self.grid, [row for row in self.data if row[colNum] < filter_val])
            elif filter_opt == '>':
                try:
                    filter_val = float(filter_val)
                except:
                    wx.MessageBox("Please enter a number.", "Data Type Error")
                    self.right_click.FindItemByPosition(1).Enable(False)

                self.grid._table.reset_view(self.grid, [row for row in self.data if row[colNum] > filter_val])
            elif filter_opt == '=':
                try:
                    filter_val = float(filter_val)
                except:
                    wx.MessageBox("Please enter a number.","Data Type Error")
                    self.right_click.FindItemByPosition(1).Enable(False)

                self.grid._table.reset_view(self.grid, [row for row in self.data if row[colNum] == filter_val])
            elif filter_opt == 'contains':
                self.grid._table.reset_view(self.grid, [row for row in self.data
                                                        if str(row[colNum]).find(filter_val) > -1])

            wx.EndBusyCursor()
        elif text == 'Show All':    #Show All
            wx.BeginBusyCursor(wx.HOURGLASS_CURSOR)

            self.right_click.FindItemByPosition(1).Enable(False)
            self.sort_flag = False
            self.grid._table.reset_view(self.grid, self.data)

            wx.EndBusyCursor()


class FragTable(FT):
    def __init__(self, parent, ID, TableTitle, row_headers, columns, data):
        FT.__init__(self, parent, ID, TableTitle, row_headers, columns, data)

        self.Bind(wx.grid.EVT_GRID_CMD_CELL_LEFT_DCLICK,
                  self.on_grid_dclick,
                  self.grid)

    def on_grid_dclick(self, event):
        wx.BeginBusyCursor(wx.HOURGLASS_CURSOR)

        row = self.grid.GetGridCursorRow()
        col = self.grid.GetGridCursorCol()
        mz = float(self.grid.GetCellValue(row, col))

        min_x = mz - 10
        max_x = mz + 10

        axes = self.GetParent().MS2_figure.get_axes()[0]

        axes.set_xlim((min_x, max_x))

        axes.set_ylim((0.0, max(i[1] for i in self.GetParent().MS2_data[0]
                                if min_x <= i[0] <= max_x) * 1.1))

        wx.EndBusyCursor()


class ScrapBook(wx.MDIParentFrame):
    def __init__(self, parent, ID):
        wx.BeginBusyCursor(wx.HOURGLASS_CURSOR)

        wx.MDIParentFrame.__init__(self, parent, ID, title='Scrap Book', size=(800,600))

        self.SetIcon(parent.GetIcon())

        self.Bind(wx.EVT_CLOSE, self.on_close)

        #add menu bar
        menu_bar = wx.MenuBar()

        #Scrapbook Menu
        actions_menu = wx.Menu()
        mirror = actions_menu.Append(-1, "&Mirror\tCtrl+M",
                                     "Compare two plots by mirroring one over the other")
        self.Bind(wx.EVT_MENU, self.on_mirror, mirror)

        overlay = actions_menu.Append(-1, "&Overlay\tCtrl+O",
                                      "Compare two plots by overlaying one over the other")
        self.Bind(wx.EVT_MENU, self.on_overlay, overlay)

        menu_bar.Append(actions_menu, "&Actions")

        #Edit Menu
        edit_menu = wx.Menu()
        title_menu = edit_menu.Append(-1, "Change &Title\tCtrl+T",
                                      "Change Plot Title")
        self.Bind(wx.EVT_MENU, self.on_title, title_menu)

        xlabel_menu = edit_menu.Append(-1, "Change &X Axis Label\tCtrl+X",
                                       "Change X Axis Label")
        self.Bind(wx.EVT_MENU, self.on_xlabel, xlabel_menu)

        ylabel_menu = edit_menu.Append(-1, "Change &Y Axis Label\tCtrl+Y",
                                       "Change Y Axis Label")
        self.Bind(wx.EVT_MENU, self.on_ylabel, ylabel_menu)

        menu_bar.Append(edit_menu, "&Edit")

        save_menu = wx.Menu()
        save_image = save_menu.Append(-1, "&Save Image\tCtrl+S",
                                              "Save Plot as Image")
        self.Bind(wx.EVT_MENU, self.on_save, save_image)

        menu_bar.Append(save_menu, "&Save")

        resize_menu = wx.Menu()

        resize_800 = resize_menu.Append(-1, "800x600\tAlt+1",
                                        "Resize Plot to 800x600")
        self.Bind(wx.EVT_MENU, lambda e: self.on_resize((800,600)), resize_800)

        resize_1200= resize_menu.Append(-1, "1200x900\tAlt+2",
                                        "Resize Plot to 1200x900")
        self.Bind(wx.EVT_MENU, lambda e: self.on_resize((1200,900)), resize_1200)

        resize_1400 = resize_menu.Append(-1, "1400x1050\tAlt+3",
                                         "Resize Plot to 1400x1050")
        self.Bind(wx.EVT_MENU, lambda e: self.on_resize((1400,1050)), resize_1400)

        menu_bar.Append(resize_menu, "&Resize")

        self.SetMenuBar(menu_bar)

        self.child_counter = 0

        wx.EndBusyCursor()

    def on_close(self, event):
        self.GetParent().scrap_book = None
        self.Destroy()

    def add_plot(self, title, data, plot_tag):
        sbc = ScrapBookChild(self, title, data, plot_tag)
        sbc.Show(True)
        self.GetParent().SendSizeEvent()

    def on_resize(self, size):
        self.GetActiveChild().on_resize(size)
        self.SendSizeEvent()

    def on_title(self, event):
        self.GetActiveChild().on_title(event)

    def on_xlabel(self, event):
        self.GetActiveChild().on_xlabel(event)

    def on_ylabel(self, event):
        self.GetActiveChild().on_ylabel(event)

    def on_save(self, event):
        self.GetActiveChild().on_save(event)

    def on_mirror(self, event):
        children = self.GetChildren()
        if len(children) < 2:
            wx.MessageBox("Must have at least two plots in Scrap Book.", "Not Enough Plots")
            return

        mirror_dlg = wx.Dialog(self, -1, 'Choose Windows to Compare')

        gbs = wx.GridBagSizer(5,5)

        child_labels = [child.GetLabel() for child in children]

        choices = (wx.Choice(mirror_dlg, -1, choices=child_labels, size=(250,-1)),
                   wx.Choice(mirror_dlg, -1, choices=child_labels, size=(250,-1)))

        for i,c in enumerate(choices):
            c.SetSelection(i)
            gbs.Add( c, (i,0), flag=wx.EXPAND )

        ok_btn = wx.Button(mirror_dlg, wx.ID_OK)

        gbs.Add( wx.Button(mirror_dlg, wx.ID_OK),
                 (2,0), flag=wx.ALIGN_CENTER )

        box = wx.BoxSizer()
        box.Add(gbs, 1, wx.ALL, 5)
        mirror_dlg.SetSizerAndFit(box)

        if mirror_dlg.ShowModal() == wx.ID_OK:
            (child_A,child_B) = [children[c.GetSelection()] for c in choices]
            title = 'Compare %s vs %s' % (child_A.GetLabel(), child_B.GetLabel())

            if (child_A.mirrored or child_B.mirrored or child_A.overlay or child_B.overlay):
                wx.MessageBox("Cannot mirror a combined plot", "Error")
                return
            elif child_A.plot_tag != child_B.plot_tag:
                wx.MessageBox("Cannot mirror plots of two different types", "Error")
                return
            elif child_A.plot_tag in ('MS1', 'MS2'):
                if child_A.data[0].mode != child_B.data[0].mode:
                    wx.MessageBox("Cannot mirror a profile scan against a centroid scan", "Error")
                    return

            data_sets = (child_A.data, child_B.data)

            mirror_frame = ScrapBookChild(self, title, data_sets, child_A.plot_tag, mirrored=True)
            mirror_frame.Show()

        mirror_dlg.Destroy()

    def on_overlay(self, event):
        children = self.GetChildren()
        if len(children) < 2:
            wx.MessageBox("Must have at least two plots in Scrap Book.", "Not Enough Plots")
            return

        overlay_dlg = wx.Dialog(self, -1, 'Choose Windows to Compare')

        gbs = wx.GridBagSizer(5,5)

        child_labels = [child.GetLabel() for child in children]

        choices = (wx.Choice(overlay_dlg, -1, choices=child_labels, size=(250,-1)),
                   wx.Choice(overlay_dlg, -1, choices=child_labels, size=(250,-1)))

        for i,c in enumerate(choices):
            c.SetSelection(i)
            gbs.Add( c, (i,0), flag=wx.EXPAND )

        ok_btn = wx.Button(overlay_dlg, wx.ID_OK)

        gbs.Add( wx.Button(overlay_dlg, wx.ID_OK),
                 (2,0), flag=wx.ALIGN_CENTER )

        box = wx.BoxSizer()
        box.Add(gbs, 1, wx.ALL, 5)
        overlay_dlg.SetSizerAndFit(box)

        if overlay_dlg.ShowModal() == wx.ID_OK:
            (child_A,child_B) = [children[c.GetSelection()] for c in choices]
            title = 'Compare %s vs %s' % (child_A.GetLabel(), child_B.GetLabel())

            if (child_A.mirrored or child_B.mirrored or child_A.overlay or child_B.overlay):
                wx.MessageBox("Cannot overlay a combined plot", "Error")
                return
            elif child_A.plot_tag != child_B.plot_tag:
                wx.MessageBox("Cannot overlay plots of two different types", "Error")
                return
            elif child_A.plot_tag in ('MS1', 'MS2'):
                if child_A.data[0].mode != child_B.data[0].mode:
                    wx.MessageBox("Cannot overlay a profile scan and a centroid scan", "Error")
                    return

            data_sets = (child_A.data, child_B.data)

            overlay_frame = ScrapBookChild(self, title, data_sets, child_A.plot_tag, overlay=True)
            overlay_frame.Show()

        overlay_dlg.Destroy()


class ScrapBookChild(wx.MDIChildFrame, mzPlot):
    def __init__(self, parent, title, data, plot_tag, mirrored=False, overlay=False):
        wx.BeginBusyCursor(wx.HOURGLASS_CURSOR)

        wx.MDIChildFrame.__init__(self, parent, -1, title, style=wx.DEFAULT_FRAME_STYLE)

        self.SetIcon(parent.GetIcon())

        self.Bind(wx.EVT_CLOSE, self.on_close)

        self.data = data
        self.plot_tag = plot_tag
        self.mirrored = mirrored
        self.overlay = overlay

        if self.mirrored:
            if self.plot_tag == 'XIC':
                self.xy_data = array(sum(self.data[0], ())
                                     + tuple((x,-y) for x,y in sum(self.data[1], ())))
            else:
                self.xy_data = array(self.data[0][0] + [(x,-y) for x,y in self.data[1][0]])
        elif self.overlay:
            if self.plot_tag == 'XIC':
                self.xy_data = array(sum(sum(d, ()) for d in self.data))
            else:
                self.xy_data = array(self.data[0][0] + self.data[1][0])
        else:
            if self.plot_tag == 'XIC':
                self.xy_data = array(sum(self.data, ()))
            else:
                self.xy_data = array(self.data[0])

        if mirrored and overlay:
            raise ValueError("Can't both mirror and overlay")

        self.last_anno = None

        # panel
        pane = wx.Panel(self, -1, style=wx.TAB_TRAVERSAL)
        #pane.SetBackgroundColour(wx.Colour(255,255,255))

        self.plot_panel = wxmpl.PlotPanel(pane, -1, (1.6,1.2), mirrored=mirrored)
        self.plot_panel.mpl_connect('button_release_event', self.on_click)

        self.figure = self.plot_panel.get_figure()

        if plot_tag == 'XIC':
            if mirrored or overlay:
                self.tooltip_str = '(%%3.%df, %%3.%df)' % (settings.xic_time_figs,
                                                           settings.xic_int_figs)

                axes = self.figure.add_axes([0.125, 0.1, 0.775, 0.8])
                axes.plot([x for x,y in data[0][0]],
                          [y for x,y in data[0][0]],
                          '--rs', linewidth=2, markeredgecolor='k',
                          markerfacecolor='g', markersize=5)

                if data[0][1]:
                    axes.plot([data[0][1][0][0]],
                              [data[0][1][0][1]],
                              'b^', markersize=10)
                if len(data[0][2]) > 0:
                    axes.plot([bt for bt,bi in data[0][2]],
                              [bi for bt,bi in data[0][2]],
                              'yo', markersize=10)

                axes.plot([x for x,y in data[1][0]],
                          [-y for x,y in data[1][0]] if mirrored else [y for x,y in data[1][0]],
                          '-.rs', linewidth=2, markeredgecolor='k',
                          markerfacecolor='g', markersize=5)

                if data[1][1]:
                    axes.plot([data[1][1][0][0]],
                              [-data[1][1][0][1]] if mirrored else [data[1][1][0][1]],
                              'b^', markersize=10)
                if len(data[1][2]) > 0:
                    axes.plot([bt for bt,bi in data[1][2]],
                              [-bi for bt,bi in data[1][2]] if mirrored else [bi for bt,bi in data[1][2]],
                              'yo', markersize=10)

                axes.xaxis.set_major_formatter(ScalarFormatter(useOffset=False, useMathText=True))

                axes.set_title(title)
            else:
                self.plot_xic(title, *data)
        elif plot_tag == 'MS1':
            if mirrored or overlay:
                self.tooltip_str = '(%%3.%df, %%3.%df)' % (settings.ms1_mz_figs,
                                                           settings.ms1_int_figs)

                axes = self.figure.add_axes([0.125, 0.1, 0.775, 0.8])

                xy_data_A = data[0][0]
                xy_data_B = data[1][0]

                if data[0][0].mode == 'c':
                    xy_data_A = add_centroid_scan_points(xy_data_A)
                    xy_data_B = add_centroid_scan_points(xy_data_B)

                axes.plot([i[0] for i in xy_data_A],
                          [i[1] for i in xy_data_A],
                          c='k')

                axes.plot([i[0] for i in xy_data_B],
                          [-i[1] for i in xy_data_B] if mirrored else [i[1] for i in xy_data_B],
                          linestyle='--', c='k')

                axes.xaxis.set_major_formatter(ScalarFormatter(useOffset=False, useMathText=True))

                axes.set_title(title)
            else:
                self.plot_full_ms(title, *data[:2])
        elif plot_tag == 'MS2':
            if mirrored or overlay:
                self.tooltip_str = '(%%3.%df, %%3.%df)' % (settings.ms2_mz_figs,
                                                           settings.ms2_int_figs)

                axes = self.figure.add_axes([0.125, 0.1, 0.775, 0.8])

                xy_data_A = data[0][0]
                xy_data_B = data[1][0]

                if data[0][0].mode == 'c':
                    xy_data_A = add_centroid_scan_points(xy_data_A)
                    xy_data_B = add_centroid_scan_points(xy_data_B)

                axes.plot([i[0] for i in xy_data_A],
                          [i[1] for i in xy_data_A],
                          linestyle='-',
                          linewidth=0.5,
                          color='k')

                axes.plot([i[0] for i in xy_data_B],
                          [-i[1] for i in xy_data_B] if mirrored else [i[1] for i in xy_data_B],
                          linestyle='--',
                          linewidth=0.5,
                          color='k')

                axes.xaxis.set_major_formatter(ScalarFormatter(useOffset=False, useMathText=True))

                axes.set_title(title)
            else:
                self.plot_ms_ms(title, *data[:1])

        self.plot_panel.draw()

        box = wx.BoxSizer()
        box.Add(self.plot_panel, 1, wx.EXPAND, 0)
        pane.SetSizerAndFit(box)

        self.GetParent().child_counter += 1

        wx.EndBusyCursor()

    def on_close(self, event):
        self.Destroy()
        self.GetParent().child_counter -= 1
