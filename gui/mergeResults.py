import wx
import tempfile
import os
import shutil
from multiplierz.mzReport import reader, writer
from multiplierz.mzGUI_standalone import report_chooser
from gui import BasicTab
from multiplierz.mzTools.multifile import filterJoin
from multiplierz import myData
from multiplierz.internalAlgorithms import collectByCriterion

optionList = ['Accession Number',
              'Peptide Sequence',
              'Variable Modifications',
              'Charge']

modeList = ['Concatenate All',
            'Cross-Report Key',
            'Unique-by-File Report',
            'Entries-in-Common Report']

class MergePanel(BasicTab):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)
        
        fileLabel = wx.StaticText(self, -1, "Input Files")
        self.fileList = wx.ListBox(self, -1, choices = [],
                                   style = wx.LB_MULTIPLE | wx.LB_HSCROLL)
        
        self.addButton = wx.Button(self, -1, "Add")
        self.removeButton = wx.Button(self, -1, "Remove")
        self.clearButton = wx.Button(self, -1, "Clear")
        
        fieldsLabel = wx.StaticText(self, -1, "Fields To Match")
        self.fieldsCtrl = wx.CheckListBox(self, -1, choices = optionList, size = (-1, 300))
        self.fieldsAdd = wx.Button(self, -1, "Additional Columns")
        
        self.modeCtrl = wx.RadioBox(self, -1, "Mode",
                                        choices = modeList,
                                        style = wx.RA_SPECIFY_ROWS)
        
        self.outputLabel = wx.StaticText(self, -1, "Output File")
        self.outputCtrl = wx.TextCtrl(self, -1, "")
        self.outputBrowse = wx.Button(self, -1, "Save As")
        # Only one of these two sets should be active, based on whether the
        # output file is going to be combined.
        
        self.runButton = wx.Button(self, -1, "Merge Files")
        
        self.gbs = wx.GridBagSizer(10, 10)
        
        self.gbs.Add(fileLabel, (0, 1))
        self.gbs.Add(self.fileList, (1,1), span = (12, 5), flag = wx.EXPAND)
        
        self.gbs.Add(self.addButton, (1, 0), flag = wx.ALIGN_RIGHT)
        self.gbs.Add(self.removeButton, (2, 0), flag = wx.ALIGN_RIGHT)
        self.gbs.Add(self.clearButton, (3, 0), flag = wx.ALIGN_RIGHT)
        
        self.gbs.Add(fieldsLabel, (5, 0), flag = wx.ALIGN_BOTTOM | wx.ALIGN_CENTER)
        self.gbs.Add(self.fieldsCtrl, (6, 0), span = (2, 1), flag = wx.EXPAND)
        self.gbs.Add(self.fieldsAdd, (8, 0), flag = wx.ALIGN_CENTER)
        
        self.gbs.Add(self.modeCtrl, (12, 0))
        
        self.gbs.Add(self.outputLabel, (14, 2), flag = wx.ALIGN_RIGHT)
        self.gbs.Add(self.outputCtrl, (14, 3), span = (1, 1), flag = wx.EXPAND)
        self.gbs.Add(self.outputBrowse, (14, 4), flag = wx.ALIGN_LEFT)
        
        self.gbs.Add(self.runButton, (17, 3), span = (1, 1), flag = wx.EXPAND)
        
        self.gbs.AddGrowableCol(3)
        self.gbs.AddGrowableRow(4)
        self.gbs.AddGrowableRow(12)
        
        overBox = wx.BoxSizer()
        overBox.Add(self.gbs, 1, wx.ALL|wx.EXPAND, 20)
        
        self.SetSizerAndFit(overBox)
        
        self.Bind(wx.EVT_BUTTON, self.addFile, self.addButton)
        self.Bind(wx.EVT_BUTTON, self.removeFile, self.removeButton)
        self.Bind(wx.EVT_BUTTON, self.clearFiles, self.clearButton)
        
        self.Bind(wx.EVT_BUTTON, self.addColumnsMenu, self.fieldsAdd)

        self.Bind(wx.EVT_BUTTON, self.saveBrowse, self.outputBrowse)
        
        self.Bind(wx.EVT_BUTTON, self.dispatchModes, self.runButton)

    def addFile(self, event):
        filenames = report_chooser(self, mode = 'm')
        if filenames:
            self.fileList.InsertItems(filenames, 0)
    
    def removeFile(self, event):
        filenames = [self.fileList.GetString(x) for x in range(0, self.fileList.GetCount())
                     if not self.fileList.IsSelected(x)]
        self.fileList.Set(filenames)
    
    def clearFiles(self, event):
        self.fileList.Clear()
        
    def addColumnsMenu(self, event):
        filenames = [self.fileList.GetString(x) for x in range(0, self.fileList.GetCount())]
        
        columns = set()
        for filename in filenames:
            read = reader(filename)
            columns.update(read.columns)
        
        columns = list(columns)
        
        if columns:
            columnDialog = wx.MultiChoiceDialog(None, "Choose Columns To Match:", "More Fields",
                                                choices = columns)
            if columnDialog.ShowModal() == wx.ID_OK:
                newCheckedColumnIndices = columnDialog.GetSelections()
                newCheckedColumns = [columns[i] for i in newCheckedColumnIndices]
                
                
                oldColumns = self.fieldsCtrl.GetStrings()
                checkedColumns = self.fieldsCtrl.GetCheckedStrings()
                
                self.fieldsCtrl.SetItems(oldColumns + [x for x in newCheckedColumns if x not in oldColumns])
                self.fieldsCtrl.SetCheckedStrings(list(checkedColumns) + [x for x in newCheckedColumns if x not in checkedColumns])
        else:
            columnAlert = wx.MessageDialog(None, "Could not get additional columns; no files selected.")
            columnAlert.ShowModal()
        
    def saveBrowse(self, event):
        filedialog = wx.FileDialog(self, "Choose Output File", 
                                   wildcard = 'XLS|*.xls|XLSX|*.xlsx|Other|*',
                                   style = wx.FD_SAVE)
        
        filedialog.ShowModal()
        self.outputCtrl.SetValue(filedialog.GetPath())
    
    
    def dispatchModes(self, event):
        self.runButton.Enable(False)
        
        mode = self.modeCtrl.GetString(self.modeCtrl.GetSelection())
        self.criteria = self.fieldsCtrl.GetCheckedStrings()
        self.inputfiles = [(x, reader(x)) for x in self.fileList.GetStrings()]

        
        outputfile = self.outputCtrl.GetValue()
        if not outputfile:
            outputfile = 'combined_output_file'
        if not outputfile.split('.')[-1].lower() in ('xls', 'xlsx', 'csv', 'mzd'):
            outputfile += '.xlsx'
        if not os.path.isabs(outputfile):
            outdir = os.path.dirname(self.inputfiles[0][0])
            outputfile = os.path.join(outdir, outputfile)
        
        
        if mode in ['Concatenate All', 'Unique-by-File Report', 'Entries-in-Common Report']:
            columnsets = [x[1].columns for x in self.inputfiles]
            columnIntersection = reduce(set.intersection, columnsets, set(columnsets[0]))
            self.outcolumns = ['Source'] + [x for x in columnsets[0] if x in columnIntersection]   
            
            if mode != 'Concatenate All':
                assert all([x in self.outcolumns for x in self.criteria])             
        elif mode in ['Cross-Report Key']:
            self.outcolumns = ['Key'] + [x[0] for x in self.inputfiles]
        else:
            raise Exception
        
       
        
        self.output = writer(outputfile,
                             columns = self.outcolumns)        
        
        if mode == 'Concatenate All':
            self.concatenate()
        elif mode == 'Cross-Report Key':
            self.cross_report_key()
        elif mode == 'Unique-by-File Report':
            self.unique_by_file()
        elif mode == 'Entries-in-Common Report':
            self.entries_in_common()
        else:
            raise Exception
        
        self.output.close()
        print "Wrote %s" % outputfile
        self.runButton.Enable(True)
    
    
    def concatenate(self):
        for filename, rdr in self.inputfiles:
            for psm in rdr:
                outpsm = dict([(k, v) for k, v in psm.items() if k in self.outcolumns])
                outpsm['Source'] = filename
                self.output.write(outpsm)
        
        print "Concatenated."
    
    def cross_report_key(self):
        criteriaByFile = {}
        def criterion(psm):
            return tuple([psm[x] for x in self.criteria])
        
        for filename, rdr in self.inputfiles:
            criteriaByFile[filename] = collectByCriterion(rdr, criterion)
        
        entities = set(sum([x.keys() for x in criteriaByFile.values()], []))
        for thing in entities:
            outrow = {'Key': '__'.join(map(str, thing))}
            for filename, byCriterion in criteriaByFile.items():
                outrow[filename] = thing in byCriterion
        
            self.output.write(outrow)
        
        print "Report key generated."
    
    def unique_by_file(self):
        criteriaByFile = {}
        def criterion(psm):
            return tuple([psm[x] for x in self.criteria])
        
        for filename, rdr in self.inputfiles:
            criteriaByFile[filename] = collectByCriterion(rdr, criterion)
        
        for filename, byCriterion in criteriaByFile.items():
            for thing, psms in byCriterion.items():
                if not any([thing in criteriaByFile[x] for x, _ in self.inputfiles
                            if x != filename]):
                    outpsm = dict([(k, v) for k, v in psms[0].items() if k in self.outcolumns])
                    outpsm['Source'] = filename                    
                    self.output.write(outpsm) # Currently writes only one instance of a unique entry.
    
        print "Unique entry report generated."
    
    def entries_in_common(self):
        criteriaByFile = {}
        def criterion(psm):
            return tuple([psm[x] for x in self.criteria])
        
        for filename, rdr in self.inputfiles:
            criteriaByFile[filename] = collectByCriterion(rdr, criterion)
        
        for filename, byCriterion in criteriaByFile.items():
            for thing, psms in byCriterion.items():
                if all([thing in criteriaByFile[x] for x, _ in self.inputfiles]):
                    for psm in psms:
                        outpsm = dict([(k, v) for k, v in psm.items() if k in self.outcolumns])
                        outpsm['Source'] = filename                        
                        self.output.write(outpsm) # Currently writes all instances.
    
        print "Common entry report generated."        
    
    
            
                        
    
        
    
        
       
        
            
        
        
        
        
    
            
                
                
    
    
        