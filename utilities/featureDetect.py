from multiplierz.mzTools.featureDetector import detectorRun
from regex import RegexHelper
from multiplierz.mzReport import reader
import wx

import async





class DetectorSession(wx.Frame):
    def __init__(self, parent):
        super(DetectorSession, self).__init__(parent, title = "Feature Detection Utility", size = (700, 500))
        
        self.panel = wx.Panel(self)
        
        titleText = wx.StaticText(self.panel, -1, "Choose spectrometer data file and result file(s) to annotate:")
        dataLabel, self.dataCtrl, dataBrowse = self.ctrlSet("Data File")
        resultLabel, self.resultCtrl, resultBrowse = self.ctrlSet("Result Files")
        
        parserNote = wx.StaticText(self.panel, -1, ("MZ and scan number data will be recovered "
                                                    "from the Spectrum Description field in the\n"
                                                    "search result files.  Enter regular expressions "
                                                    "that transform a spectrum description\n"
                                                    "to each value."))
        self.customParserCheck = wx.CheckBox(self.panel, -1, "Use Default Parsers")
        self.customParserCheck.SetValue(True)
        self.Bind(wx.EVT_CHECKBOX, self.toggleParserCtrls, self.customParserCheck)
        toMzLabel = wx.StaticText(self.panel, -1, "MZ parser")
        self.toMzCtrl = wx.TextCtrl(self.panel, -1, "")
        self.toMzHelp = wx.Button(self.panel, -1, "Regex Utility")
        
        toScanLabel = wx.StaticText(self.panel, -1, "Scan Number Parser")
        self.toScanCtrl = wx.TextCtrl(self.panel, -1, "")
        self.toScanHelp = wx.Button(self.panel, -1, "Regex Utility")
        
        self.goButton = wx.Button(self.panel, -1, "Annotate")
        
        self.linkBrowser(self.dataCtrl, dataBrowse, "Select Data File",
                         wildcard = 'RAW|*.raw|Other|*.*')
        self.linkBrowser(self.resultCtrl, resultBrowse, "Select Result Files",
                         wildcard = 'Excel|*.xls;*.xlsx|Comma-Separated|*.csv|Other|*.*',
                         style = wx.FD_OPEN | wx.FD_MULTIPLE)
        
        self.Bind(wx.EVT_BUTTON, self.onMzHelp, self.toMzHelp)
        self.Bind(wx.EVT_BUTTON, self.onScanHelp, self.toScanHelp)
        self.Bind(wx.EVT_BUTTON, self.runDetector, self.goButton)
        
        self.gbs = wx.GridBagSizer(10, 10)
        
        self.gbs.Add(titleText, (0, 0), span = (1, 3))
        self.placeSet(2, dataLabel, self.dataCtrl, dataBrowse)
        self.placeSet(3, resultLabel, self.resultCtrl, resultBrowse)
        
        self.gbs.Add(parserNote, (5, 0), span = (1, 4))
        self.gbs.Add(self.customParserCheck, (6, 1), span = (1, 2))
        self.placeSet(7, toMzLabel, self.toMzCtrl, self.toMzHelp)
        self.placeSet(8, toScanLabel, self.toScanCtrl, self.toScanHelp)

        
        self.gbs.Add(self.goButton, (12, 1), span = (1, 2))
        
        self.gbs.AddGrowableCol(1)
        
        overBox = wx.BoxSizer()
        overBox.Add(self.gbs, 1, wx.ALL, 20)
        self.panel.SetSizerAndFit(overBox)
        
        self.toggleParserCtrls(None)
        
        self.Centre()
        self.Show()
    
    def ctrlSet(self, label, default = ""):
        labelText = wx.StaticText(self.panel, -1, label)
        control = wx.TextCtrl(self.panel, -1, default, style = wx.EXPAND)
        browser = wx.Button(self.panel, -1, "Browse")
        return labelText, control, browser
        
    def placeSet(self, row, label, control, button):
        self.gbs.Add(label, (row, 0), flag = wx.ALIGN_RIGHT)
        self.gbs.Add(control, (row, 1), span = (1, 3), flag = wx.ALIGN_LEFT | wx.EXPAND)
        if button: self.gbs.Add(button, (row, 4))
        
    def linkBrowser(self, control, button, message, wildcard, style = wx.FD_OPEN):
        def browseForFile(*etc):
            filedialog = wx.FileDialog(parent = self, message = message,
                                       wildcard = wildcard, style = style)
            filedialog.ShowModal()
            filepath = ';'.join(filedialog.GetPaths())
            control.SetValue(filepath)
            
        self.Bind(wx.EVT_BUTTON, browseForFile, button)   
        
    
    def onMzHelp(self, event):
        descExample = ''
        try:
            firstFile = (x.strip() for x in self.resultCtrl.GetValue().split(';')).next()
            if firstFile:
                print "Peeking into %s for a sample spectrum description..." % firstFile
                data = reader(firstFile)
                row = data.__iter__().next()
                descExample = row['Spectrum Description']
                data.close()
        except Exception as err:
            print err
        
        helper = RegexHelper(self, self.toMzCtrl.GetValue(), descExample)
        if helper.ShowModal() == wx.ID_OK:
            self.toMzCtrl.SetValue(helper.getRegex())
        
        helper.Destroy()
    
    def onScanHelp(self, event):
        descExample = ''
        try:
            firstFile = (x.strip() for x in self.resultCtrl.GetValue().split(';')).next()
            if firstFile:
                print "Peeking into %s for a sample spectrum description..." % firstFile
                data = reader(firstFile)
                row = data.__iter__().next()
                descExample = row['Spectrum Description']
                data.close()
        except Exception as err:
            print err
        
        helper = RegexHelper(self, self.toScanCtrl.GetValue(), descExample)
        if helper.ShowModal() == wx.ID_OK:
            self.toScanCtrl.SetValue(helper.getRegex())
        
        helper.Destroy()
        
    def toggleParserCtrls(self, event):
        useParsers = not self.customParserCheck.GetValue()
        self.toMzCtrl.SetValue('')
        self.toMzCtrl.Enable(useParsers)
        self.toMzHelp.Enable(useParsers)
        self.toScanCtrl.SetValue('')
        self.toScanCtrl.Enable(useParsers)
        self.toScanHelp.Enable(useParsers)
        
    def runDetector(self, event):
        datafile = self.dataCtrl.GetValue()
        resultfiles = [x.strip() for x in self.resultCtrl.GetValue().split(';') if x]
        
    
        mzRegex = self.toMzCtrl.GetValue()
        scanRegex = self.toScanCtrl.GetValue()
        
        wx.BeginBusyCursor()
        self.goButton.Enable(False)
        #detectorRun(datafile, resultfiles, mzRegex, scanRegex)
        async.launch_process(detectorRun, None, datafile, resultfiles, mzRegex, scanRegex)
        self.goButton.Enable(True)
        wx.EndBusyCursor()
    
        
        
        
        
        
        
if __name__ == '__main__':
    app = wx.App(0)
    detector = DetectorSession(None)
    app.MainLoop()