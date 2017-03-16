from multiplierz.mzAPI import mzFile
from multiplierz.mzReport import writer
from multiplierz.mgf import parse_mgf

from multiplierz.mass_biochem import findIonsInData

from gui import BasicTab
import wx



# This could be consolidated with DeNovoDisplay and a few others.
class FoundIonsDisplay(wx.Frame):
    def __init__(self, parent, id, columns, data):
        wx.Frame.__init__(self, parent, id, title = "Spectra with Found Ions")
        
        #parent.SetIcon(parent.get_icon())
        pane = wx.Panel(self, -1, style = wx.TAB_TRAVERSAL | wx.CLIP_CHILDREN)
        
        grid = wx.grid.Grid(pane, -1)
        grid.CreateGrid(len(data), len(columns))
        for i, col in enumerate(columns):
            grid.SetColLabelValue(i, col)
        
        for row, values in enumerate(data):
            for col, key in enumerate(columns):
                grid.SetCellValue(row, col, str(values[key]))
        
        overBox = wx.BoxSizer()
        overBox.Add(grid, 1, wx.EXPAND|wx.ALL, 5)
        pane.SetSizerAndFit(overBox)
        


class SpectrumPanel(BasicTab):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)
        
        ionPanelLabel = wx.StaticText(self, -1, 'Detect Ions')
        ionPanelLabel.SetFont(wx.Font(15, wx.DEFAULT, wx.NORMAL, wx.NORMAL))
        
        ionFileLabel = wx.StaticText(self, -1, "Data File")
        self.ionFileCtrl = wx.TextCtrl(self, -1)
        ionFileBrowse = wx.Button(self, -1, "Browse")
        
        ionSelectLabel = wx.StaticText(self, -1, "Target Ions")
        self.ionSelectCtrl = wx.TextCtrl(self, -1, style = wx.TE_MULTILINE)
        
        thresholdLabel = wx.StaticText(self, -1, "Threshold Intensity")
        self.thresholdCtrl = wx.TextCtrl(self, -1)
        
        toleranceLabel = wx.StaticText(self, -1, "M/Z Tolerance")
        self.toleranceCtrl = wx.TextCtrl(self, -1)
        
        self.saveAsCheck = wx.CheckBox(self, -1, "Save Output To File")
        self.saveAsCtrl = wx.TextCtrl(self, -1)
        saveAsBrowse = wx.Button(self, -1, 'Browse')
        
        goButton = wx.Button(self, -1, "Find Ions")
        
        gbs = wx.GridBagSizer(5, 5)
        gbs.Add(ionPanelLabel, (0, 0), span = (1, 3), flag = wx.ALL | wx.ALIGN_CENTER_HORIZONTAL,
                border = 10)
        
        gbs.Add(ionFileLabel, (1, 0), flag = wx.ALIGN_RIGHT)
        gbs.Add(self.ionFileCtrl, (1, 1), flag = wx.EXPAND)
        gbs.Add(ionFileBrowse, (1, 2), flag = wx.ALIGN_LEFT)
        
        gbs.Add(ionSelectLabel, (2, 0), flag = wx.ALIGN_RIGHT)
        gbs.Add(self.ionSelectCtrl, (2, 1), span = (1, 2), flag = wx.EXPAND)
        
        gbs.Add(thresholdLabel, (3, 0), flag = wx.ALIGN_RIGHT)
        gbs.Add(self.thresholdCtrl, (3, 1), flag = wx.ALIGN_LEFT)
        gbs.Add(toleranceLabel, (4, 0), flag = wx.ALIGN_RIGHT)
        gbs.Add(self.toleranceCtrl, (4, 1), flag = wx.ALIGN_LEFT)
        
        gbs.Add(self.saveAsCheck, (6, 0), flag = wx.ALIGN_RIGHT)
        gbs.Add(self.saveAsCtrl, (6, 1), flag = wx.EXPAND)
        gbs.Add(saveAsBrowse, (6, 2), flag = wx.ALIGN_LEFT)
        
        gbs.Add(goButton, (8, 1), flag = wx.EXPAND, border = 15)
        
        gbs.AddGrowableRow(2)
        
        overBox = wx.BoxSizer()
        overBox.Add(gbs, 1, wx.ALL | wx.EXPAND, 10)
        self.SetSizerAndFit(overBox)
        
        self.Bind(wx.EVT_BUTTON, self.onBrowse, ionFileBrowse)
        self.Bind(wx.EVT_BUTTON, self.onSaveBrowse, saveAsBrowse)
        self.Bind(wx.EVT_BUTTON, self.calculate, goButton)
        
        self.Show()
        
    def onBrowse(self, event):
        filedialog = wx.FileDialog(parent = self, message = "Choose MS Data File",
                                   style = wx.FD_OPEN,
                                   wildcard = 'RAW|*.raw|WIFF|*.wiff|All|*.*')
    
        result = filedialog.ShowModal()
        if result == wx.ID_OK:
            newfile = filedialog.GetPath()
            self.ionFileCtrl.SetValue(newfile)
        else:
            print "Cancelled selection."      
            
    def onSaveBrowse(self, event):
        filedialog = wx.FileDialog(parent = self, message = "Save Results To:",
                                   style = wx.FD_SAVE,
                                   wildcard = 'XLSX|*.xlsx|XLS|*.xls|CSV|*.csv|Any|*')
    
        result = filedialog.ShowModal()
        if result == wx.ID_OK:
            newfile = filedialog.GetPath()
            self.saveAsCtrl.SetValue(newfile)
        else:
            print "Cancelled selection."    
    
    def calculate(self, event):
        datafile = self.ionFileCtrl.GetValue()
        ionStr = self.ionSelectCtrl.GetValue()
        ions = [float(x) for x in ionStr.split()]
        
        tolerance = float(self.toleranceCtrl.GetValue())
        threshold = float(self.thresholdCtrl.GetValue())
        
        saveOutput = self.saveAsCheck.GetValue()
        if saveOutput:
            outputFile = self.saveAsCtrl.GetValue()
            if not outputFile:
                raise IOError, "Output file not selected."
        
        results, resultColumns = findIonsInData(datafile, ions, tolerance,
                                                threshold, includeColumns = True)
        
        if saveOutput:
            output = writer(outputFile, columns = resultColumns)
            for row in results:
                output.write(row)
            output.close()
        else:
            resultDisplay = FoundIonsDisplay(self, -1, resultColumns, results)
            resultDisplay.Show()