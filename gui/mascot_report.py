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


#from multiplierz.mzSearch.mascot.report import retrieveMascotReport
from multiplierz.mzSearch.mascot_search import retrieveMascotReport
from multiplierz.post_process import calculate_FDR, combine_accessions

from mzDesktop import myData, settings, install_dir

from gui import BasicTab
from wx.lib.agw.flatnotebook import EVT_FLATNOTEBOOK_PAGE_CLOSING as EVT_FLATNOTEBOOK_PAGE_CLOSING

class MascotReportPanel(BasicTab):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)

        gbs = wx.GridBagSizer(12, 5)

        labels = ('Login',
                  'Password',
                  'Mascot ID(s)',
                  'Folder To Save Report File',
                  'Max. Number of Hits',
                  'Ion Score Cut-Off')

        for i,lbl in enumerate(labels):
            gbs.Add( wx.StaticText(self, -1, lbl, style=wx.ALIGN_RIGHT),
                     (i,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT )

        self.useLocalCheck = wx.CheckBox(self, -1, "Use Local\nDAT Files")
        #localDatLabel = wx.StaticText(self, -1, "Local .DAT Files")
        self.browseForDat = wx.Button(self, -1, "Select .DAT Files")
        self.datFiles = wx.TextCtrl(self, -1)
        self.browseForDat.Enable(False)
        self.datFiles.Enable(False)
        
        
        gbs.Add(self.useLocalCheck, (0, 2), flag = wx.ALIGN_RIGHT)
        #gbs.Add(localDatLabel, (1, 2))
        gbs.Add(self.browseForDat, (1, 2), flag = wx.ALIGN_RIGHT)
        gbs.Add(self.datFiles, (1, 3), span = (1, 4), flag=wx.EXPAND)
                
        
        self.useLocalCheck.Bind(wx.EVT_CHECKBOX, self.on_check_local)
        self.browseForDat.Bind(wx.EVT_BUTTON, self.browseForDatFiles)
        
        
        self.login_text = wx.TextCtrl(self,  -1,  "",  size=(100,-1))
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
                 (2,1), (1,6), flag=wx.EXPAND )

        self.folder_text = wx.TextCtrl(self, -1, myData)
        gbs.Add( self.folder_text,
                 (3,1), (1,5), flag=wx.EXPAND )

        folder_btn = wx.Button(self, -1, "Browse")
        gbs.Add( folder_btn,
                 (3,6) )
        folder_btn.Bind(wx.EVT_BUTTON, self.on_folder)

        self.max_hits_text = wx.TextCtrl(self, -1, "1000", size=(100,-1))
        gbs.Add( self.max_hits_text,
                 (4,1) )

        self.ion_cutoff_text = wx.TextCtrl(self, -1, "20", size=(100,-1))
        gbs.Add( self.ion_cutoff_text,
                 (5,1) )

        self.mzid_ck = wx.CheckBox(self, -1, "mzIdentML Format", style=wx.ALIGN_LEFT)
        gbs.Add(self.mzid_ck, (6,1))
        self.Bind(wx.EVT_CHECKBOX, self.on_mzid_check, self.mzid_ck)
        
        self.p2gCheck = wx.CheckBox(self, -1, "Gene Annotation", style = wx.ALIGN_LEFT)
        self.p2gCheck.SetValue(False)
        self.p2gCheck.Bind(wx.EVT_CHECKBOX, self.on_p2g_check)
        
        self.p2gLabel = wx.StaticText(self, -1, "Pep2Gene Database", style = wx.ALIGN_RIGHT)
        self.p2gField = wx.TextCtrl(self, -1, "", size = (-1, -1))
        self.p2gField.Enable(False)
        self.p2gButton = wx.Button(self, -1, "Browse")
        self.p2gButton.Bind(wx.EVT_BUTTON, self.on_p2g_folder)
        self.p2gButton.Enable(False)
        
        gbs.Add(self.p2gCheck, (7, 1))
        gbs.Add(self.p2gLabel, (8, 0), flag = wx.ALIGN_RIGHT)
        gbs.Add(self.p2gField, (8, 1), (1, 5), flag = wx.EXPAND)
        gbs.Add(self.p2gButton, (8, 6))

        self.bold_red_ck = wx.CheckBox(self, -1, "Require Bold Red ", style=wx.ALIGN_RIGHT)
        self.bold_red_ck.SetValue(True)

        self.show_query_ck = wx.CheckBox(self, -1, "Show Input Query Data ", style=wx.ALIGN_RIGHT)
        self.show_query_ck.SetValue(True)

        #self.quant_ck = wx.CheckBox(self, -1, "Peptide Quantitation ", style=wx.ALIGN_RIGHT)
        #if settings.mascot_version < '2.2':
            #self.quant_ck.Enable(False)

        #self.genbank_ck = wx.CheckBox(self, -1, "Include GenBank Info ", style=wx.ALIGN_RIGHT)
        
        self.combine_accessions = wx.CheckBox(self, -1, "Combine Redundant Spectra", style = wx.ALIGN_RIGHT)
        
        self.perform_FDR = wx.CheckBox(self, -1, "Forward-Reverse FDR Filter", style =wx.ALIGN_RIGHT)
        
        

        for i,ck_box in enumerate((self.bold_red_ck,
                                   self.show_query_ck,
                                   #self.quant_ck,
                                   #self.genbank_ck,
                                   self.combine_accessions,
                                   self.perform_FDR)):
            gbs.Add( ck_box,
                     (i+9,2), flag=wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL )

        try:
            #ncbi_image = wx.Image(os.path.join(install_dir, 'Images', 'ncbi_logo.GIF'))
            #gbs.Add( wx.StaticBitmap(self, -1, wx.BitmapFromImage(ncbi_image)), (12,3) )
            pass
        except:
            print "Could not display NCBI logo."
            pass

        self.same_sets_ck = wx.CheckBox(self, -1, "Include Same-Set Protein Hits ", style=wx.ALIGN_RIGHT)

        self.sub_sets_ck = wx.CheckBox(self, -1, "Include Sub-Set Protein Hits ", style=wx.ALIGN_RIGHT)

        self.rank_one_ck = wx.CheckBox(self, -1, "First Rank Peptides Only ", style=wx.ALIGN_RIGHT)

        #self.prot_report = wx.CheckBox(self, -1, "Protein-Level Summary ", style=wx.ALIGN_RIGHT)
        
        self.keep_dat = wx.CheckBox(self, -1, "Retain Local .DAT File", style=wx.ALIGN_RIGHT)
        
        
        for i,ck_box in enumerate((self.same_sets_ck,
                                   self.sub_sets_ck,
                                   self.rank_one_ck,
                                   #self.prot_report,
                                   self.keep_dat)):
            gbs.Add( ck_box,
                     (i+9,4), flag=wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL )

        make_report_btn = wx.Button(self, -1, "Make Report", size=(260,-1))
        gbs.Add( make_report_btn,
                 (16,0), (1,7), flag=wx.ALIGN_CENTER )
        make_report_btn.Bind(wx.EVT_BUTTON, self.on_get_report)

        gbs.AddGrowableCol(1,1)
        gbs.AddGrowableCol(5,1)
        #gbs.AddGrowableRow(9,1)
        #gbs.AddGrowableRow(14,1)

        box = wx.BoxSizer(wx.HORIZONTAL)
        box.AddSpacer(100)
        box.Add(gbs, 1, wx.ALL|wx.EXPAND, 20)
        box.AddSpacer(200)

        self.load_control_settings()
        self.GetParent().GetParent().Bind(wx.EVT_CLOSE,
                                          self.save_control_settings)

        self.SetSizerAndFit(box)
        
    def load_control_settings(self):
        controlValues = settings.retrieve_mascot_report_controls()
        
        self.max_hits_text.SetValue(controlValues['max hits'])
        self.ion_cutoff_text.SetValue(controlValues['ion cutoff'])
        self.mzid_ck.SetValue(controlValues['mzid'])
        self.p2gCheck.SetValue(controlValues['p2g'])
        self.bold_red_ck.SetValue(controlValues['bold red'])
        self.show_query_ck.SetValue(controlValues['show input query'])
        #self.quant_ck.SetValue(controlValues['pep quant'])
        #self.genbank_ck.SetValue(controlValues['genbank'])
        self.same_sets_ck.SetValue(controlValues['same-set hits'])
        self.sub_sets_ck.SetValue(controlValues['sub-set hits'])
        self.rank_one_ck.SetValue(controlValues['rank one only'])
        #self.prot_report.SetValue(controlValues['protein summary'])
        self.keep_dat.SetValue(controlValues['retain DAT'])
        
    
    def save_control_settings(self, event):
        controlValues = {}
        
        controlValues['max hits'] = self.max_hits_text.GetValue()
        controlValues['ion cutoff'] = self.ion_cutoff_text.GetValue()
        controlValues['mzid'] = self.mzid_ck.GetValue()
        controlValues['p2g'] = self.p2gCheck.GetValue()
        controlValues['bold red'] = self.bold_red_ck.GetValue()
        controlValues['show input query'] = self.show_query_ck.GetValue()
        #controlValues['pep quant'] = self.quant_ck.GetValue()
        #controlValues['genbank'] = self.genbank_ck.GetValue()
        controlValues['same-set hits'] = self.same_sets_ck.GetValue()
        controlValues['sub-set hits'] = self.sub_sets_ck.GetValue()
        controlValues['rank one only'] = self.rank_one_ck.GetValue()
        controlValues['protein summary'] = self.prot_report.GetValue()
        controlValues['retain DAT'] = self.keep_dat.GetValue()        
        
        settings.save_mascot_report_controls(controlValues)
        event.Skip()
        
        
        

    def on_folder(self,event):
        folder_chooser = wx.DirDialog(None, "Choose folder to Save Report:")
        if folder_chooser.ShowModal() == wx.ID_OK:
            self.folder_text.SetValue(folder_chooser.GetPath())
        folder_chooser.Destroy()
        
    def on_p2g_folder(self, event):
        folder_chooser = wx.FileDialog(None, "Choose Pep2Gene Database:")
        if folder_chooser.ShowModal() == wx.ID_OK:
            self.p2gField.SetValue(folder_chooser.GetPath())
        folder_chooser.Destroy()
        
    def on_p2g_check(self, event):
        if self.p2gCheck.GetValue():
            self.p2gField.Enable(True)
            self.p2gButton.Enable(True)
        else:
            self.p2gField.Enable(False)
            self.p2gButton.Enable(False)
            
    def on_mzid_check(self, event):
        mzidVal = not self.mzid_ck.GetValue()
        
        subControls = [self.p2gCheck,
                       self.p2gField,
                       self.bold_red_ck,
                       self.show_query_ck,
                       self.quant_ck,
                       #self.genbank_ck,
                       self.same_sets_ck,
                       self.sub_sets_ck,
                       self.rank_one_ck,
                       self.prot_report,
                       self.keep_dat]
        
        for control in subControls:
            control.Enable(mzidVal)
    
    def on_check_local(self, event):
        localMode = self.useLocalCheck.GetValue()

        self.browseForDat.Enable(localMode)
        self.datFiles.Enable(localMode)
        
        self.login_text.Enable(not localMode)
        self.password_text.Enable(not localMode)
        self.mascot_id_text.Enable(not localMode)
        
        if localMode:
            self.mzid_ck.SetValue(False)
            self.on_mzid_check(None)
        self.mzid_ck.Enable(not localMode)
        
    def browseForDatFiles(self, event):
        fileFinder = wx.FileDialog(None, "Choose .DAT File(s)", 
                                   wildcard = 'Mascot .DAT Files | *.dat',
                                   style = wx.FD_OPEN | wx.FD_MULTIPLE)
        if fileFinder.ShowModal() == wx.ID_OK:
            self.datFiles.SetValue(', '.join(fileFinder.GetPaths()))
        fileFinder.Destroy()
            

    def on_get_report(self,event):
        #show hourglass
        wx.BeginBusyCursor(wx.HOURGLASS_CURSOR)
        
        #try:
        #update statusbar
        self.set_status("Working...", 0)
        self.set_status("", 1)

        mascot_ID_input = ''.join(self.mascot_id_text.GetValue().split())
        mascot_ID_list = mascot_ID_input.split(',')
        
        new_id_list = []
        dat_file_list = []
        if self.useLocalCheck.GetValue():
            dat_file_list = [x.strip() for x in self.datFiles.GetValue().split(',')]
        else:
            for mascot_ID in mascot_ID_list:
                if '-' in mascot_ID:
                    (firstID, lastID) = mascot_ID.split('-')
                    new_id_list.extend(str(ID) for ID in range(int(firstID), int(lastID)+1))
                else:
                    new_id_list.append(mascot_ID)
                
        if self.mzid_ck.IsChecked():
            extension = '.mzid'
        else:
            extension = settings.default_format                    
    
        try:
            results = retrieveMascotReport(mascot_ids = new_id_list,
                                           dat_file_list = dat_file_list,
                                           chosen_folder = self.folder_text.GetValue(),
                                           mascot_server = settings.mascot_server,
                                           mascot_version = settings.mascot_version,
                                           combined_file = False,
                                           rank_one = self.rank_one_ck.GetValue(),
                                           max_hits = int(self.max_hits_text.GetValue()),
                                           ion_cutoff = float(self.ion_cutoff_text.GetValue()),
                                           bold_red = self.bold_red_ck.IsChecked(),
                                           show_query_data = self.show_query_ck.IsChecked(),
                                           show_same_set = self.same_sets_ck.IsChecked(),
                                           show_sub_set = self.sub_sets_ck.IsChecked(),
                                           #genbank = self.genbank_ck.GetValue(),
                                           protein_report = self.prot_report.GetValue(),
                                           quant = self.quant_ck.IsChecked(),
                                           ext = extension,
                                           login_name = self.login_text.GetValue(),
                                           password = self.password_text.GetValue(),
                                           keep_dat = self.keep_dat.IsChecked(),
                                           pep2gene = self.p2gField.GetValue() if self.p2gCheck.GetValue() else None
                                           )
        
        
            if self.combine_accessions.GetValue():
                print "Combining redundant peptide reports..."
                for result in results:
                    combine_accessions(result)
                print "Combining completed."
            
            if self.perform_FDR.GetValue():
                print "Performing FDR calculation..."
                for result in results:
                    calculate_FDR(result) # Will probably want to include a way to change defaults eventually.
                print "FDR completed."
                self.set_status("Done", 1)
        except Exception as err:
            errBox = wx.MessageBox(str(err), "An Error Occurred.")
            import traceback
            print traceback.format_exc()
        finally:
            # hide hourglass
            wx.EndBusyCursor()
        
        # update statusbar
        print "Done."
        self.set_status("Ready", 0)
                
                
            
        
            






