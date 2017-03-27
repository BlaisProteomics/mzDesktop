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

from tempfile import mkstemp

import multiplierz.mzReport

from multiplierz.mzSearch.mascot.report import MascotReport

from mzDesktop import settings

from multiplierz.mzGUI_standalone import report_chooser
from gui import BasicTab

class MascotWebPanel(BasicTab):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)

        gbs = wx.GridBagSizer(12, 5)

        labels = ('Login',
                  'Password',
                  'Mascot ID',
                  'Multiplierz File',
                  'Instrument')

        for i,lbl in enumerate(labels):
            gbs.Add( wx.StaticText(self, -1, lbl, style=wx.ALIGN_RIGHT),
                     (i,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT )

        self.login_text = wx.TextCtrl(self, -1, "", size=(100,-1))
        gbs.Add( self.login_text,
                 (0,1) )

        self.password_text = wx.TextCtrl(self, -1, "", size=(100,-1), style=wx.TE_PASSWORD)
        gbs.Add( self.password_text,
                 (1,1) )

        if not settings.mascot_security:
            self.login_text.Enable(False)
            self.password_text.Enable(False)

        self.mascot_id_text = wx.TextCtrl(self, -1, "")
        gbs.Add( self.mascot_id_text,
                 (2,1), (1,2), flag=wx.EXPAND )

        #clean mascot file
        self.file_text = wx.TextCtrl(self, -1, "")
        gbs.Add( self.file_text,
                 (3,1), flag=wx.EXPAND )

        file_btn = wx.Button(self, -1, "Browse")
        gbs.Add( file_btn,
                 (3,2) )
        file_btn.Bind(wx.EVT_BUTTON, self.OnClickMascotFile)

        #Enter Mascot Instrument
        instrument_list = ['ESI-TRAP',
                          'ETD-TRAP',
                          'ESI-QUAD-TOF',
                          'MALDI-TOF-TOF']

        self.instrument = wx.ComboBox(self, -1, value="ESI-TRAP",
                                      choices=instrument_list, style=wx.CB_DROPDOWN)
        self.instrument.SetSelection(0)
        gbs.Add( self.instrument,
                 (4,1) )

        self.img_ck = wx.CheckBox(self, -1, "   MS-MS Image", size=(135, 13))
        self.img_ck.SetValue(1)

        self.mod_ck = wx.CheckBox(self, -1, "   Modification Positions", size=(135, 13))
        if settings.mascot_version == '2.1':
            self.mod_ck.SetValue(True)
        else:
            self.mod_ck.Enable(False) # don't allow mod position download, should already be present

        self.cov_ck = wx.CheckBox(self, -1, "   Protein Coverage Info", size=(135, 13))

        for i,ckbx in enumerate((self.img_ck,
                                 self.mod_ck,
                                 self.cov_ck)):
            gbs.Add( ckbx,
                     (i+5,0), (1,3), flag=wx.ALIGN_CENTER )

        # Make XLS button
        make_report_btn = wx.Button(self, -1, "Submit", size=(160,-1))
        gbs.Add( make_report_btn,
                 (8,0), (1,3), wx.ALIGN_CENTER )
        make_report_btn.Bind(wx.EVT_BUTTON, self.OnClickGetGIF)

        gbs.AddGrowableCol(1)

        box = wx.BoxSizer()
        box.Add(gbs, 1, wx.ALL|wx.EXPAND, 20)

        self.SetSizerAndFit(box)

    def OnClickGetGIF(self, event):
        #show hourglass
        wx.BeginBusyCursor(wx.HOURGLASS_CURSOR)

        #update statusbar
        self.set_status("Getting Images...", 0)
        self.set_status("", 1)

        try:
    
            mascotWebExtract(mascot_id = self.mascot_id_text.GetValue(),
                             login = self.login_text.GetValue(),
                             password = self.password_text.GetValue(),
                             report_file = self.file_text.GetValue(),
                             ms2_img = self.img_ck.GetValue(),
                             mascot_var_mods = self.mod_ck.GetValue(),
                             mascot_prot_cov = self.cov_ck.GetValue(),
                             #draw_pep = True
                             instrument = self.instrument.GetValue())
        except Exception as err:
            wx.MessageBox("An error occurred:\n" + repr(err), "Error")
            wx.EndBusyCursor()
            raise   

        #update statusbar
        self.set_status("Ready", 0)
        self.set_status("Done", 1)

        #hide hourglass
        wx.EndBusyCursor()

    def OnClickMascotFile(self, event):
        file_name = report_chooser(self)
        if file_name:
            self.file_text.SetValue(file_name)






def mascotWebExtract(mascot_id,
                     login,
                     password,
                     report_file,
                     ms2_img = True,
                     mascot_var_mods = True,
                     mascot_prot_cov = False,
                     instrument = "ESI-TRAP"):
    
    """
    Extracts data from the multiplierz default Mascot server and inserts it
    into a search results file.
    
    mascot_id -> Mascot ID of the target search.
    
    login, password -> Login credentials for the Mascot server.  Not required
    if Mascot security is not enabled on the server.
    
    report_file -> Search results file to be annotated.
    
    ms2_img -> Whether to annotate data with an image depicting the detected MS2
    ions.
    
    mascot_var_mods ->
    
    mascot_prot_cov ->
    
    instrument -> The type of instrument which recorded the original data;
    must be one of "ESI-TRAP", "ETD-TRAP", "ESI-QUAD-TOF" or "MALDI-TOF-TOF".
    
    """
    
    if report_file.lower().endswith(".mzid"):
        raise NotImplementedError, ("This function does not support mzIdentML "
                                    "report files.  If you have access to the "
                                    "original data, you may use the Peak Extractor "
                                    "function to obtain MS-MS ion annotations.")
    
    mascot_reporter = MascotReport(settings.mascot_server,
                                   settings.mascot_version,
                                   login, password)
        
    if not settings.mascot_security:
        GIFText = 'success'
        mascot_reporter.mascot.logged_in = True
    else:
        GIFText = mascot_reporter.login_mascot()

    if GIFText == 'error':
        raise RuntimeError, "Mascot Login Error: Please check your username and password and try again."
        #wx.MessageBox("Please check your username and password and try again", 'Mascot Login Error', style=wx.ICON_EXCLAMATION)
        #update statusbar
        #self.set_status("Ready",0)
        #self.set_status("Done",1)

        ##hide hourglass
        #wx.EndBusyCursor()
        #return

    if ':' in mascot_id:
        (mascot_id, date) = mascot_id.split(':',1)
    else:
        date = None

    if ms2_img and settings.mascot_ms2:
        dat_file = mascot_reporter.mascot.download_dat(os.path.dirname(report_file),
                                                       mascot_id, date)
    else:
        dat_file = None

    report = multiplierz.mzReport.reader(report_file)

    rep_ext = os.path.splitext(report_file)[1].lower()

    # if this is an XLS file, we can just write over it. Otherwise, we need
    # to make a copy and rename it.
    if rep_ext == '.xls' or rep_ext == '.xlsx':
        tempname = report_file
    else:
        (h, tempname) = mkstemp(suffix=rep_ext,
                                dir=os.path.dirname(report_file))
        os.close(h)
        os.remove(tempname)

    isMZD = rep_ext == '.mzd'

    if ms2_img or mascot_var_mods:
        web_generator = mascot_reporter.mascot_web(mascot_id, ms2_img, mascot_var_mods, # draw_pep,
                                                   instrument, date=date,
                                                   isMZD=isMZD, dat_file=dat_file)
        web_generator.next()

    if mascot_prot_cov:
        prot_cov_generator = mascot_reporter.mascot_prot_coverage(mascot_id, None, date=date)
        prot_cov_generator.next()

    newcols = report.columns
    if mascot_prot_cov and 'Protein Coverage' not in newcols:
        newcols.append('Protein Coverage')

    newrep = multiplierz.mzReport.writer(tempname, columns=newcols)

    if isMZD:
        if ms2_img:
            cursor = report.conn.execute('SELECT * from ImageData where Col!="Peptide Sequence"')
        else:
            cursor = report.conn.execute('SELECT * from ImageData')
        newrep.conn.executemany('INSERT into ImageData values (?,?,?,?)',
                                ((lastID,col,tag,plotdata) for (lastID,col,tag,plotdata) in cursor))

    for row in report:
        md = []
        if ms2_img or mascot_var_mods:
            (vartext, img_tup) = web_generator.send(row)
            if ms2_img:
                md.append(img_tup)
            if mascot_var_mods:
                row['Variable Modifications'] = vartext

        if mascot_prot_cov:
            (prot_cov, md_tup) = prot_cov_generator.send(row)
            row['Protein Coverage'] = prot_cov
            md.append(md_tup)

        newrep.write(row, md)

    if ms2_img or mascot_var_mods:
        web_generator.close()

    if mascot_prot_cov:
        prot_cov_generator.close()

    report.close()
    newrep.close()

    if tempname != report_file:
        os.remove(report_file)
        os.rename(tempname, report_file)

    if dat_file:
        os.remove(dat_file)    