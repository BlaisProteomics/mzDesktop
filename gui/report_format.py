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

#import multiplierz.mascot.report as mzReport
import multiplierz.mzReport as mzReport
import multiplierz.mzSearch.mascot.interface as mascot

from multiplierz.mzReport.formats.protein_pilot import ProteinPilot
from multiplierz.mzReport.formats.omssa import OMSSA_CSV
#from multiplierz.mzReport.formats.mzIdentML import mzIdentML
from multiplierz.mzTools.mzIdentMLAPI import mzIdentML
from multiplierz.mzReport.formats.xtandem import format_XML
from multiplierz.mzReport import reader, writer

from mzDesktop import settings

from gui import BasicTab

class ReportFormatPanel(BasicTab):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)

        gbs = wx.GridBagSizer(12, 5)

        gbs.Add( wx.StaticText(self, -1, 'Files to Convert'),
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
                 (1,1), (3,5), flag=wx.EXPAND )

        gbs.Add( wx.StaticText(self, -1, 'Input Format', style=wx.ALIGN_RIGHT),
                 (4,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT )

        input_formats = ('Mascot CSV (*.csv)',
                         'Mascot DAT (*.dat)',
                         'Mascot mzIdentML (*.mzid)',
                         'ProteinPilot Peptide Summary (*.txt)',
                         'OMSSA (*.csv)',
                         'X!Tandem XML (*.xml)',
                         'Multiplierz Report (*.xls; *.xlsx; *.csv; *.mzd)')

        self.input_format = wx.Choice(self, -1, choices=input_formats)
        self.input_format.SetSelection(0)
        gbs.Add( self.input_format,
                 (4,1) )

        gbs.Add( wx.StaticText(self, -1, 'Output Format', style=wx.ALIGN_RIGHT),
                 (5,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT )

        output_formats = ('Excel Spreadsheet (.xls)',
                          'Excel 2007 Spreadsheet (.xlsx)',
                          'Comma-Separated Values (.csv)',
                          'mzResults Database (.mzd)')

        self.output_format = wx.Choice(self, -1, choices=output_formats)
        self.output_format.SetSelection({'.xls': 0,
                                         '.xlsx': 1,
                                         '.csv': 2,
                                         '.mzd': 3}[settings.default_format])
        gbs.Add( self.output_format,
                 (5,1) )


        
        self.combineCheck = wx.CheckBox(self, -1, "Merge All")
        combineLabel = wx.StaticText(self, -1, "Combined File")
        self.combineCtrl = wx.TextCtrl(self, -1, "")
        self.combineCheck.SetValue(False)
        self.combineCtrl.Enable(False)
        
        self.Bind(wx.EVT_CHECKBOX, self.toggleCombine, self.combineCheck)
        
        gbs.Add(self.combineCheck, (5, 2), flag = wx.ALIGN_RIGHT)
        gbs.Add(combineLabel, (5, 3), flag = wx.ALIGN_RIGHT)
        gbs.Add(self.combineCtrl, (5, 4), flag = wx.EXPAND)

        convert_btn = wx.Button(self, 20, "Convert", size=(160,-1))
        gbs.Add( convert_btn ,
                 (6,0), (1,3), flag=wx.ALIGN_CENTER )
        convert_btn.Bind(wx.EVT_BUTTON, self.on_convert)

        gbs.AddGrowableCol(1)
        gbs.AddGrowableCol(4)
        gbs.AddGrowableRow(3)

        box = wx.BoxSizer()
        box.Add(gbs, 1, wx.ALL|wx.EXPAND, 20)
        self.SetSizerAndFit(box)

    def toggleCombine(self, event):
        combine = self.combineCheck.GetValue()
        self.combineCtrl.Enable(combine)
            
            

    def on_click_add(self, event):
        wildcard = ('Mascot CSV (*.csv)|*.csv|'
                    'Mascot DAT (*.dat)|*.dat|'
                    'Mascot mzIdentML (*.mzid)|*.mzid|'
                    'ProteinPilot Peptide Reports (*.txt)|*.txt|'
                    'OMSSA CSV (*.csv)|*.csv|'
                    'X!Tandem XML (*.xml)|*.xml|'
                    'mzReport-Supported Formats (*.xls; *.xlsx; *.csv; *.mzd)|*.xls; *.xlsx; *.csv; *.mzd|'
                    'All Files|*')

        file_chooser = wx.FileDialog(None, "Choose Files to Convert",
                                     wildcard=wildcard,
                                     style=wx.FD_MULTIPLE)

        file_chooser.SetFilterIndex(self.input_format.GetSelection())

        if file_chooser.ShowModal() == wx.ID_OK:
            self.file_list.Set(sorted(set(self.file_list.GetStrings() + file_chooser.GetPaths())))
            self.input_format.SetSelection(file_chooser.GetFilterIndex())

        file_chooser.Destroy()

    def on_click_remove(self, event):
        remove = self.file_list.GetSelections()
        files = [f for i,f in enumerate(self.file_list.GetStrings()) if i not in remove]
        self.file_list.Set(files)

    def on_click_clear(self, event):
        self.file_list.Clear()

    def on_convert(self, event):
        if not self.file_list.GetStrings():
            wx.MessageBox('No files selected', 'Error')
            return

        #show hourglass
        wx.BeginBusyCursor(wx.HOURGLASS_CURSOR)

        files = self.file_list.GetStrings()
        input_format = self.input_format.GetSelection()
        output_format = self.output_format.GetSelection()
        output_ext = { 0:'.xls', 1:'.xlsx', 2:'.csv', 3:'.mzd' }[output_format]

        #update statusbar
        self.set_status("Converting...", 0)
        self.set_status("", 1)

        if self.combineCheck.GetValue():
            if input_format not in [0, 6]:
                wx.MessageBox("Only tabular/Excel files can currently be merged.")
                return
            combineFiles(self.file_list.GetStrings(),
                         self.combineCtrl.GetValue(),
                         output_ext)
            wx.EndBusyCursor()        
            self.set_status("Ready", 0)
            self.set_status("Done", 1)            
            return
            
            

        if input_format == 0: # Mascot CSV
            mascot_converter = mascot.mascot(version=settings.mascot_version)

            for file_name in files:
                self.set_status(file_name, 1)

                #Run MascotCSV program
                clean_csv_file = '_clean'.join(os.path.splitext(file_name))

                rep_file = os.path.splitext(clean_csv_file)[0] + output_ext
                if os.path.exists(rep_file):
                    os.remove(rep_file)

                mascot_converter.clean_csv(file_name, export_file=clean_csv_file, ion_list=False)

                repreader = mzReport.reader(clean_csv_file)
                repwriter = mzReport.writer(rep_file, columns=repreader.columns)

                for row in repreader:
                    repwriter.write(row)

                repreader.close()
                repwriter.close()

                #if os.path.splitext(rep_file)[1].lower() in ('.xls', '.xlsx', 'mzd'):
                    #mascot_reporter.mascot_header(rep_file, file_name)

                os.remove(clean_csv_file)

        elif input_format == 1: # Mascot DAT
            mascot_reporter = mzTools.MascotReport()

            _mascot_options = dict(max_hits=1000, ion_cutoff=20, bold_red=True,
                                   unassigned_queries=False, show_query_data=True,
                                   show_same_set=False, show_sub_set=False, quant=False)

            for file_name in files:
                self.set_status(file_name, 1)

                mascot_dat_file = mascot.MascotDatFile(file_name, **_mascot_options)
                mascot_header = mascot_dat_file.mascot_header()
                #mascot_header, prot_report, pep_report = mascot.parse_dat_file(file_name, **_mascot_options)

                ms_file_name = mascot_header[7][1] or (os.path.splitext(os.path.basename(file_name))[0])
                report_file = os.path.join(os.path.dirname(file_name),
                                           os.path.basename(ms_file_name) + output_ext)

                if os.path.exists(report_file):
                    os.remove(report_file)

                if output_ext in ('.xls', '.xlsx', '.mzd'):
                    mascot_reporter.mascot_header(report_file, mascot_header)
                    #mascot_reporter.mascot_header(report_file, mascot_header)

                if mascot_dat_file.res_file.getMascotVer() >= '2.3':
                    report = mzReport.writer(report_file,
                                             columns=(mzReport.default_columns[:1]
                                                      + ['Protein Database']
                                                      + mzReport.default_columns[1:]))
                else:
                    report = mzReport.writer(report_file, default_columns=True)

                #for row in pep_report:
                for row in mascot_dat_file.peptide_report():
                    report.write(row)

                mascot_dat_file.close()
                report.close()

        #elif input_format == 2: # Mascot mzIdentML
            #for file_name in files:
                #mzid = mzIdentML(file_name)
                #report_file = os.path.splitext(file_name)[0] + output_ext

                #if os.path.exists(report_file):
                    #os.remove(report_file)

                #report = mzReport.writer(report_file, default_columns=True)

                #for row in mzid:
                    #report.write(row)

                #report.close()

        elif input_format == 2: # Mascot mzIdentML
            for file_name in files:
                mzid = mzIdentML(file_name)
                data = mzid.peptideSummary()
                header = data[0].keys()
                
                report_file = os.path.splitext(file_name)[0] + output_ext
                
                if os.path.exists(report_file): os.remove(report_file)
                
                report = mzReport.writer(report_file, columns = header)
                
                for row in data:
                    writeRow = []
                    for column in header:
                        thing = row[column]
                        if type(thing) == type(['list']):
                            thing = "; ".join(thing)
                        writeRow.append(thing)
                    report.write(writeRow)

                report.close()
                
        elif input_format == 3: # Protein Pilot
            for file_name in files:
                self.set_status(file_name, 1)
                pilot = ProteinPilot(file_name)
                pilot.format(str(os.path.splitext(file_name)[0] + output_ext))

        elif input_format == 4: # OMMSA
            for file_name in files:
                self.set_status(file_name, 1)
                omssa = OMSSA_CSV(file_name)
                omssa.format(str(os.path.splitext(file_name)[0] + output_ext))

        elif input_format == 5: # X!Tandem XML
            for file_name in files:
                report_file = os.path.splitext(file_name)[0] + output_ext

                format_XML(file_name, report_file)

        elif input_format == 6: # other mzReport
            output_method = {'.xls': mzReport.toXLS,
                             '.xlsx': mzReport.toXLS,
                             '.csv': mzReport.toCSV,
                             '.mzd': mzReport.toMZD}[output_ext]

            for file_name in files:
                self.set_status(file_name, 1)
                
                rdr = reader(file_name)
                outputname = '.'.join(file_name.split('.')[:-1]) + output_ext
                wtr = writer(outputname, columns = rdr.columns)
                
                for row in rdr:
                    wtr.write(row)
                wtr.close()
                rdr.close()
                
                #if output_ext.startswith('.xls'):
                    #output_method(file_name, output_ext == '.xlsx')
                #else:
                    #output_method(file_name)

        #hide hourglass
        wx.EndBusyCursor()

        self.set_status("Ready", 0)
        self.set_status("Done", 1)


def combineFiles(files, outputFile, ext):
    if not os.path.isabs(outputFile):
        outputFile = os.path.join(os.path.dirname(files[0]),
                                  os.path.basename(outputFile))
        
    if not outputFile[-1*len(ext):] == ext:
        outputFile += ext
        
    print "Merging %s" % files
    columns = reader(files[0]).columns
    output = writer(outputFile, columns = ['Source'] + columns)
    
    for filename in files:
        for row in reader(filename):
            row['Source'] = os.path.basename(filename)
            output.write(row)
    
    output.close()
    print "Wrote %s !" % outputFile    