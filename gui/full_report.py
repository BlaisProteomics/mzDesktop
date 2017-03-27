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

from multiplierz.mzSearch.mascot.report import MascotReport

#from multiplierz.mzAPI import find_mz_file
#from mzDesktop import find_mz_file
from multiplierz.mzGUI_standalone import report_chooser

import mzDesktop

class FullReportWindow(wx.Frame):
    def __init__(self, parent):
        """Instantiate the FullReportWindow class. This is a one-stop-shop for
        downloading Mascot searches from a server (public or private).

        The basic workflow of this editor is:
        1. Input Mascot ID(s)
        2. Customize settings via the GUI
        3. Select an optional script to run on the reports
        3. Hit Submit, and wait. It can take a while.
        """

        wx.Frame.__init__(self, parent, -1, "Full Mascot/Multiplierz Report",
                          style=wx.DEFAULT_FRAME_STYLE ^ (wx.RESIZE_BORDER | wx.MAXIMIZE_BOX))
        self.SetExtraStyle(wx.WS_EX_VALIDATE_RECURSIVELY)
        self.SetIcon(parent.GetIcon())

        self.pane = pane = wx.Panel(self, -1, style = wx.TAB_TRAVERSAL | wx.CLIP_CHILDREN)

        gbs = wx.GridBagSizer(10,7)

        labels = ('Login',
                  'Password',
                  'Mascot ID(s)')

        for i,lbl in enumerate(labels):
            gbs.Add( wx.StaticText(pane, -1, lbl, style=wx.ALIGN_RIGHT),
                     (i,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT )

        self.output_lbl = wx.TextCtrl(pane, -1, 'Output Folder', style=wx.ALIGN_RIGHT|wx.NO_BORDER|wx.TE_READONLY)
        self.output_lbl.SetBackgroundColour(pane.GetBackgroundColour())
        gbs.Add( self.output_lbl,
                 (4,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT )

        for i,lbl in enumerate(('Max. Number of Hits',
                                'Ion Score Cut-Off')):
            gbs.Add( wx.StaticText(pane, -1, lbl, style=wx.ALIGN_RIGHT),
                     (i+5,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT )

        self.login_text = wx.TextCtrl(pane,  -1,  "",  size=(100,-1))
        gbs.Add( self.login_text,
                 (0,1) )

        self.password_text = wx.TextCtrl(pane, -1, "", size=(100,-1), style=wx.TE_PASSWORD)
        gbs.Add( self.password_text,
                 (1,1) )

        if not mzDesktop.settings.mascot_security:
            self.login_text.Enable(False)
            self.password_text.Enable(False)

        self.mascot_id_text = wx.TextCtrl(pane, -1, "")
        gbs.Add( self.mascot_id_text,
                 (2,1), (1,4), flag=wx.EXPAND )

        # combine checkbox
        self.combine_ck = wx.CheckBox(pane, -1, "   Combine Into One File")
        gbs.Add( self.combine_ck,
                 (3,1), (1,4), flag=wx.ALIGN_LEFT )
        self.combine_ck.Bind(wx.EVT_CHECKBOX, self.on_combine_check)

        self.output_text = wx.TextCtrl(pane, -1, mzDesktop.myData, size=(320,-1))
        gbs.Add( self.output_text,
                 (4,1), (1,3), flag=wx.EXPAND )

        folder_btn = wx.Button(pane, -1, "Browse")
        gbs.Add( folder_btn,
                 (4,4) )
        folder_btn.Bind(wx.EVT_BUTTON, self.on_output_browse)

        self.max_hits_text = wx.TextCtrl(pane, -1, "1000", size=(100,-1))
        gbs.Add( self.max_hits_text,
                 (5,1) )

        self.ion_cutoff_text = wx.TextCtrl(pane, -1, "20", size=(100,-1))
        gbs.Add( self.ion_cutoff_text,
                 (6,1) )

        gbs.Add( wx.StaticText(pane, -1, 'Instrument', style=wx.ALIGN_RIGHT),
                 (7,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT )

        instrument_list = ['ESI-TRAP',
                           'ETD-TRAP',
                           'ESI-QUAD-TOF',
                           'MALDI-TOF-TOF']

        self.instrument = wx.ComboBox(pane, -1, value="ESI-TRAP",
                                      choices=instrument_list, style=wx.CB_DROPDOWN)
        self.instrument.SetSelection(0)
        gbs.Add( self.instrument,
                 (7,1), (1,3) )

        self.bold_red_ck = wx.CheckBox(pane, -1, "Require Bold Red  ",
                                       size=(139,13), style=wx.ALIGN_RIGHT)
        self.bold_red_ck.SetValue(True)

        self.show_query_ck = wx.CheckBox(pane, -1, "Show Input Query Data  ",
                                         size=(139,13), style=wx.ALIGN_RIGHT)
        self.show_query_ck.SetValue(True)

        self.quant_ck = wx.CheckBox(pane, -1, "Peptide Quantitation  ",
                                    size=(139,13), style=wx.ALIGN_RIGHT)
        if mzDesktop.settings.mascot_version < '2.2':
            self.quant_ck.Enable(False)

        #self.genbank_ck = wx.CheckBox(pane, -1, "Include GenBank Info  ",
                                      #size=(139,13), style=wx.ALIGN_RIGHT)

        for i,ck_box in enumerate((self.bold_red_ck,
                                   self.show_query_ck,
                                   self.quant_ck)):
            gbs.Add( ck_box,
                     (i+8,0), (1,2), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT )

        ncbi_image = wx.Image(os.path.join(mzDesktop.install_dir, 'images', 'ncbi_logo.GIF'))
        gbs.Add( wx.StaticBitmap(pane, -1, wx.BitmapFromImage(ncbi_image)),
                 (11,2) )

        self.same_sets_ck = wx.CheckBox(pane, -1, "Include Same-Set Protein Hits  ",
                                        size=(167,13), style=wx.ALIGN_RIGHT)

        self.sub_sets_ck = wx.CheckBox(pane, -1, "Include Sub-Set Protein Hits  ",
                                       size=(167,13), style=wx.ALIGN_RIGHT)

        self.rank_one_ck = wx.CheckBox(pane, -1, "First Rank Peptides Only  ",
                                       size=(167,13), style=wx.ALIGN_RIGHT)

        self.prot_report = wx.CheckBox(pane, -1, "Protein-Level Summary  ",
                                       size=(167,13), style=wx.ALIGN_RIGHT)

        for i,ck_box in enumerate((self.same_sets_ck,
                                   self.sub_sets_ck,
                                   self.rank_one_ck,
                                   self.prot_report)):
            gbs.Add( ck_box,
                     (i+8,3), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT )

        # web-extract pane
        mascot_web = wx.CollapsiblePane(pane, label='Web Extract')
        mascot_web.Bind(wx.EVT_COLLAPSIBLEPANE_CHANGED, self.on_pane_change)
        self.web_pane(mascot_web.GetPane())
        gbs.Add(mascot_web, (12,0), (1,5), flag=wx.EXPAND )

        # peaks pane
        extract_peaks = wx.CollapsiblePane(pane, label='Retrieve Peaks')
        extract_peaks.Bind(wx.EVT_COLLAPSIBLEPANE_CHANGED, self.on_pane_change)
        self.peaks_pane(extract_peaks.GetPane())
        gbs.Add(extract_peaks, (13,0), (1,5), flag=wx.EXPAND )

        # custom script option
        custom_script = wx.CollapsiblePane(pane, label='Custom Script')
        custom_script.Bind(wx.EVT_COLLAPSIBLEPANE_CHANGED, self.on_pane_change)
        self.script_pane(custom_script.GetPane())
        gbs.Add(custom_script, (14,0), (1,5), flag=wx.EXPAND )

        # Submit button
        submit = wx.Button(pane, -1, "Submit")
        gbs.Add( submit, (15,0), (1,5), flag=wx.EXPAND )
        submit.Bind(wx.EVT_BUTTON, self.on_submit)

        box = wx.BoxSizer()
        box.Add(gbs, 1, wx.EXPAND|wx.ALL, 20)

        pane.SetSizerAndFit(box)
        self.SetClientSize(pane.GetSize())

    # callback methods
    def on_pane_change(self, event):
        '''Refresh the layout when a collapsible pane is resized'''
        self.pane.Layout()
        self.pane.Fit()
        self.SetClientSize(self.pane.GetSize())
        self.Refresh()

    def on_combine_check(self, event):
        if self.combine_ck.IsChecked():
            self.output_lbl.SetLabel('Output File')
        else:
            self.output_lbl.SetLabel('Output Folder')

    def on_output_browse(self, event):
        if self.combine_ck.IsChecked():
            output_file = report_chooser(self, title='Save output file as:', mode='w')
            if output_file:
                self.output_text.SetValue(output_file)
        else:
            folder_chooser = wx.DirDialog(self, "Choose folder to save output:",
                                          style=wx.DD_DEFAULT_STYLE | wx.DD_NEW_DIR_BUTTON)
            if folder_chooser.ShowModal() == wx.ID_OK:
                self.output_text.SetValue(folder_chooser.GetPath())
            folder_chooser.Destroy()

    def on_data_browse(self, event):
        #folder_chooser = wx.DirDialog(self, "Choose folder containing the data files:",
                                      #style=wx.DD_DEFAULT_STYLE | wx.DD_NEW_DIR_BUTTON)
        folder_chooser = wx.FileDialog(self, "Choose data file:",
                                       style = wx.DD_DEFAULT_STYLE | wx.DD_NEW_DIR_BUTTON)
        if folder_chooser.ShowModal() == wx.ID_OK:
            self.pk_data_folder.SetValue(folder_chooser.GetPath())
            self.script_data_folder.SetValue(folder_chooser.GetPath())
        folder_chooser.Destroy()

    def on_script(self, event):
        script_chooser = wx.FileDialog(self, "Choose script to run:",
                                       wildcard='Multiplierz scripts (*.mz)|*.mz',
                                       style=wx.FD_OPEN)
        if script_chooser.ShowModal() == wx.ID_OK:
            self.script_text.SetValue(script_chooser.GetPath())
        script_chooser.Destroy()

    def on_web_check(self, event):
        enabled = self.include_web.GetValue()
        for ctrl in (self.web_img_ck,
                     self.web_cov_ck):
            ctrl.Enable(enabled)
        if mzDesktop.settings.mascot_version == '2.1':
            self.web_mod_ck.Enable(enabled)

    def on_peak_check(self, event):
        enabled = self.include_peaks.GetValue()
        for ctrl in (self.pk_data_folder,
                     self.pk_data_btn,
                     self.pk_time_window,
                     self.pk_mz_window,
                     self.pk_peak_area_ck,
                     self.pk_rep_ions_ck,
                     self.pk_graph_ck,
                     self.pk_precursor_ck,
                     self.pk_ms_ms_ck):
            ctrl.Enable(enabled)

    def on_script_check(self, event):
        enabled = self.use_script.GetValue()
        for ctrl in (self.script_text,
                     self.script_btn,
                     self.script_data_folder,
                     self.script_data_btn):
            ctrl.Enable(enabled)

    def web_pane(self, pane):
        '''Add the web extract options to the collapsible web panel.

        Only need instrument choice and image/mods/coverage checkboxes.'''

        webSizer = wx.GridBagSizer(10,7)

        self.include_web = wx.CheckBox(pane, -1, '   Web Extract')
        webSizer.Add( self.include_web,
                      (0,0), (1,2), flag=wx.ALIGN_CENTER )
        self.include_web.Bind(wx.EVT_CHECKBOX, self.on_web_check)

        self.web_img_ck = wx.CheckBox(pane, -1, "   MS-MS Image", size=(135, 13))
        self.web_img_ck.SetValue(1)

        self.web_mod_ck = wx.CheckBox(pane, -1, "   Modification Positions", size=(135, 13))
        if mzDesktop.settings.mascot_version == '2.1':
            self.web_mod_ck.SetValue(True)

        self.web_cov_ck = wx.CheckBox(pane, -1, "   Protein Coverage Info", size=(135, 13))

        for i,ckbx in enumerate((self.web_img_ck,
                                 self.web_mod_ck,
                                 self.web_cov_ck)):
            webSizer.Add( ckbx,
                          (i+1,0), (1,2), flag=wx.ALIGN_CENTER )

        webSizer.AddGrowableCol(0,2)
        webSizer.AddGrowableCol(1,3)

        for ctrl in (self.web_img_ck,
                     self.web_mod_ck,
                     self.web_cov_ck):
            ctrl.Enable(False)

        border = wx.BoxSizer()
        border.Add(webSizer, 1, wx.EXPAND, 10)
        pane.SetSizer(border)

    def peaks_pane(self, pane):
        '''Add the retrieve peaks options to the collapsible peaks panel.

        Need a directory of peak files, time window, m/z window, and checkboxes.'''

        peaksSizer = wx.GridBagSizer(10,7)

        self.include_peaks = wx.CheckBox(pane, -1, '   Retrieve Peaks')
        peaksSizer.Add( self.include_peaks,
                        (0,0), (1,3), flag=wx.ALIGN_CENTER )
        self.include_peaks.Bind(wx.EVT_CHECKBOX, self.on_peak_check)

        for i,lbl in enumerate(('Peak Data Folder',
                                'Time Window (min)',
                                'm/z Window (amu)')):
            peaksSizer.Add( wx.StaticText(pane, -1, lbl, style=wx.ALIGN_RIGHT),
                            (i+1,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT )

        self.pk_data_folder = wx.TextCtrl(pane, -1, '')
        peaksSizer.Add( self.pk_data_folder,
                        (1,1), flag=wx.EXPAND )

        self.pk_data_btn = wx.Button(pane, -1, 'Browse')
        peaksSizer.Add( self.pk_data_btn,
                        (1,2) )
        self.pk_data_btn.Bind(wx.EVT_BUTTON, self.on_data_browse)

        self.pk_time_window = wx.TextCtrl(pane, -1, "1.0", size=(50,-1))
        peaksSizer.Add( self.pk_time_window,
                        (2,1) )

        self.pk_mz_window = wx.TextCtrl(pane, -1, "0.2", size=(50,-1))
        peaksSizer.Add( self.pk_mz_window,
                        (3,1) )

        self.pk_peak_area_ck = wx.CheckBox(pane, -1, "   Peak Area", size=(130,13))
        self.pk_rep_ions_ck = wx.CheckBox(pane, -1, "   iTRAQ Ion Intensities", size=(130,13))
        self.pk_graph_ck = wx.CheckBox(pane, -1, "   XIC Graph", size=(130,13))
        self.pk_precursor_ck = wx.CheckBox(pane, -1, "   Precursor Mass Graph", size=(130,13))
        self.pk_ms_ms_ck = wx.CheckBox(pane, -1, "   MS-MS Graph", size=(130,13))

        for i,ckbx in enumerate((self.pk_peak_area_ck,
                                 self.pk_rep_ions_ck,
                                 self.pk_graph_ck,
                                 self.pk_precursor_ck,
                                 self.pk_ms_ms_ck)):
            peaksSizer.Add( ckbx,
                            (i+4,0), (1,3), flag=wx.ALIGN_CENTER )

        for ctrl in (self.pk_data_folder,
                     self.pk_data_btn,
                     self.pk_time_window,
                     self.pk_mz_window,
                     self.pk_peak_area_ck,
                     self.pk_rep_ions_ck,
                     self.pk_graph_ck,
                     self.pk_precursor_ck,
                     self.pk_ms_ms_ck):
            ctrl.Enable(False)

        peaksSizer.AddGrowableCol(1)

        border = wx.BoxSizer()
        border.Add(peaksSizer, 1, wx.EXPAND, 10)
        pane.SetSizer(border)

    def script_pane(self, pane):
        '''Add the options for custom script post-processing. For now,
        this is pretty simple: you can choose a script to run on each report
        and data file, using a mandatory 'run_script' function.
        '''

        scriptSizer = wx.GridBagSizer(10,7)

        self.use_script = wx.CheckBox(pane, -1, '   Run Custom Script')
        scriptSizer.Add( self.use_script,
                         (0,0), (1,3), flag=wx.ALIGN_CENTER )
        self.use_script.Bind(wx.EVT_CHECKBOX, self.on_script_check)

        scriptSizer.Add( wx.StaticText(pane, -1, 'Script',
                                       size=(75,13), style=wx.ALIGN_RIGHT),
                         (1,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT )

        self.script_text = wx.TextCtrl(pane, -1, '')
        scriptSizer.Add( self.script_text,
                         (1,1), flag=wx.EXPAND )

        self.script_btn = wx.Button(pane, -1, 'Browse')
        scriptSizer.Add( self.script_btn,
                         (1,2) )
        self.script_btn.Bind(wx.EVT_BUTTON, self.on_script)

        scriptSizer.Add( wx.StaticText(pane, -1, 'Peak Data Folder',
                                       size=(75,13), style=wx.ALIGN_RIGHT),
                         (2,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT )

        self.script_data_folder = wx.TextCtrl(pane, -1, '')
        scriptSizer.Add( self.script_data_folder,
                         (2,1), flag=wx.EXPAND )

        self.script_data_btn = wx.Button(pane, -1, 'Browse')
        scriptSizer.Add( self.script_data_btn,
                         (2,2) )
        self.script_data_btn.Bind(wx.EVT_BUTTON, self.on_data_browse)

        scriptSizer.AddGrowableCol(1)

        for ctrl in (self.script_text,
                     self.script_btn,
                     self.script_data_folder,
                     self.script_data_btn):
            ctrl.Enable(False)

        border = wx.BoxSizer()
        border.Add(scriptSizer, 1, wx.EXPAND, 10)
        pane.SetSizer(border)

    def on_submit(self, event):
        wx.BeginBusyCursor()

        (login, password, mascot_ID_input,
         output_path, rank_one, #genbank,
         protein_report, instrument) = (self.login_text.GetValue(),
                                        self.password_text.GetValue(),
                                        ''.join(self.mascot_id_text.GetValue().split()),
                                        self.output_text.GetValue(),
                                        self.rank_one_ck.GetValue(),
                                        #self.genbank_ck.GetValue(),
                                        self.prot_report.GetValue(),
                                        self.instrument.GetValue())

        if self.combine_ck.IsChecked():
            if os.path.exists(output_path) and os.path.isdir(output_path):
                wx.MessageBox("Please specify a file for output", "Error", style=wx.OK|wx.CENTRE|wx.ICON_ERROR)
                wx.EndBusyCursor()
                return

            output_path, combined_file = os.path.split(output_path)
        else:
            if not os.path.isdir(output_path):
                wx.MessageBox("Please specify a folder for output", "Error", style=wx.OK|wx.CENTRE|wx.ICON_ERROR)
                wx.EndBusyCursor()
                return

            combined_file = False

        mascot_options = dict(zip(('max_hits', 'ion_cutoff', 'bold_red',
                                   'show_query_data', 'show_same_set',
                                   'show_sub_set', 'quant'),
                                  (int(self.max_hits_text.GetValue()),
                                   float(self.ion_cutoff_text.GetValue()),
                                   self.bold_red_ck.GetValue(),
                                   self.show_query_ck.GetValue(),
                                   self.same_sets_ck.GetValue(),
                                   self.sub_sets_ck.GetValue(),
                                   self.quant_ck.GetValue())))

        spectra = self.include_web.GetValue()
        if spectra:
            mascot_web_options = dict(zip(('ms2_img',
                                           'mascot_ms2',
                                           'mascot_var_mods'), #, 'draw_pep'),
                                          (self.web_img_ck.GetValue(),
                                           mzDesktop.settings.mascot_ms2,
                                           self.web_mod_ck.GetValue()))) #, True)))

            mascot_prot_cov = self.web_cov_ck.GetValue()
        else:
            mascot_web_options = None
            mascot_prot_cov = False


        peaks = self.include_peaks.GetValue()
        if peaks:
            peaks_options = dict(zip(('peak_data_path', 'time_window',
                                      'mz_window', 'peak_area', 'reporter_ions',
                                      'plot_xic', 'plot_ms1', 'plot_ms2'),
                                     (self.pk_data_folder.GetValue(),
                                      self.pk_time_window.GetValue(),
                                      self.pk_mz_window.GetValue(),
                                      self.pk_peak_area_ck.GetValue(),
                                      self.pk_rep_ions_ck.GetValue(),
                                      self.pk_graph_ck.GetValue(),
                                      self.pk_precursor_ck.GetValue(),
                                      self.pk_ms_ms_ck.GetValue())))
        else:
            peaks_options = None

        script = self.use_script.GetValue()
        script_path = self.script_text.GetValue()

        if script:
            execfile(script_path, globals(), globals())
            if 'run_script' not in globals():
                raise ValueError('Custom script does not contain function:'
                                 ' run_script(report, data_file)')

        mascot_ID_list = mascot_ID_input.split(',')

        if peaks:
            if peaks_options['time_window'].find(":") > -1:
                vals = peaks_options['time_window'].split(":")
                peaks_options['time_window'] = (float(vals[0]),
                                                float(vals[1]))
            else:
                total_time_window = float(peaks_options['time_window'])
                peaks_options['time_window'] = (total_time_window/2.0,
                                                total_time_window/2.0)

            if peaks_options['mz_window'].find(":") > -1:
                vals = peaks_options['mz_window'].split(":")
                peaks_options['mz_window'] = (float(vals[0]),
                                              float(vals[1]))
            else:
                total_mz_window = float(peaks_options['mz_window'])
                peaks_options['mz_window'] = (total_mz_window/2.0,
                                              total_mz_window/2.0)

        #mascot_reporter = MascotReport(mzDesktop.settings.mascot_server,
                                       #mzDesktop.settings.mascot_security,
                                       #login=login, password=password)
        mascot_reporter = MascotReport(mzDesktop.settings.mascot_server,
                                       mzDesktop.settings.mascot_version,
                                       login = login, password = password)
        if not mzDesktop.settings.mascot_security:
            mascot_reporter.mascot.logged_in = True
        else:
            check_login = mascot_reporter.login_mascot()
            if check_login == 'error':
                wx.MessageBox('Please check your username and password and try again',
                              'Mascot Login Error',
                              style=wx.ICON_EXCLAMATION)
                #hide hourglass
                wx.EndBusyCursor()

                return

        new_id_list = []
        for mascot_ID in mascot_ID_list:
            if '-' in mascot_ID:
                (firstID, lastID) = mascot_ID.split('-')
                new_id_list.extend(str(ID) for ID in range(int(firstID), int(lastID)+1))
            else:
                new_id_list.append(mascot_ID)

        ret_val = mascot_reporter.get_reports(mascot_ids = new_id_list,
                                              chosen_folder = output_path,
                                              combined_file = combined_file,
                                              #genbank = genbank,
                                              protein_report = protein_report,
                                              rank_one = rank_one,
                                              instrument = instrument,
                                              mascot_options = mascot_options,
                                              peaks = peaks,
                                              peaks_options = peaks_options,
                                              mascot_web = spectra,
                                              mascot_web_options = mascot_web_options,
                                              mascot_prot_cov = mascot_prot_cov,
                                              #ext = mzDesktop.settings.default_format)
                                              ext = '.mzd')

        if script:
            # could just check 'peaks' but get_report might have decided not
            # to extract peaks, if it couldn't find the file
            if isinstance(ret_val,tuple):
                # ret_val is (report_file, data_file) tuple
                try:
                    run_script(*ret_val)
                except Exception, e:
                    mzDesktop.logger_message(50, ("%s threw exception, did not complete"
                                                  % os.path.basename(script_path)))
                    mzDesktop.logger_message(50, "Details:\t%s" % e)
            else:
                # ret_val is the report_file, which should be
                # named after the data file. Need to find it.
                data_path = self.script_data_folder.GetValue()
                #data_file = ''

                base = os.path.splitext(os.path.basename(ret_val))[0] # strip off report extension
                if base.endswith('.mgf'):
                    base = base[:-4]

                data_file = mzDesktop.find_mz_file(data_path, base)

                if data_file is None:
                    mzDesktop.logger_message(40, "Warning: Couldn't find data file, script not run")
                else:
                    try:
                        run_script(ret_val, data_file)
                    except Exception, e:
                        mzDesktop.logger_message(50, ("%s threw exception, did not complete"
                                                      % os.path.basename(script_path)))
                        mzDesktop.logger_message(50, "Details: %s" % e)

        wx.EndBusyCursor()
        wx.MessageBox("Reports Downloaded", "Finished!")
