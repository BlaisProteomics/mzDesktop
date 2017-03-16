import wx
import os
from multiplierz.mzTools.labelEvaluation import evaluateMascotFile
import async

summaryTemplates = [['Total Peptides','Total Lysines','Total Arginines',
                     'Fully Labelled','Lysine Labelled','Arginine Labelled'],
                    ['Total Peptides','Total Lysines','Fully Labelled',
                     'NTerm Labelled','Lysine Labelled']]

class ShowEvaluationSummary(wx.Dialog):
    def __init__(self, parent, summary):
        super(ShowEvaluationSummary, self).__init__(parent, title = "Evaluation Result Summary",
                                                    size = (200, 200))
        panel = wx.Panel(self, -1)
        
        template = [xs for xs in summaryTemplates if
                    all([x.lower() in summary.keys() for x in xs])][0]
        
        writeup = []
        for key in template:
            writeup.append("%s: %s" % (key, summary[key.lower()]))
        writeup = '\n'.join(writeup)
        
        textBox = wx.TextCtrl(self, -1, writeup, size = (200, 180),
                              style = wx.TE_READONLY | wx.BORDER_NONE | wx.TE_MULTILINE)
        okButton = wx.Button(self, -1, "OK")
        self.Bind(wx.EVT_BUTTON, self.ok, okButton)
        
        box = wx.BoxSizer(wx.VERTICAL)
        box.Add(textBox, flag = wx.EXPAND)
        box.Add(okButton)
        
        self.SetSizerAndFit(box)
        self.Centre()
        self.Show()
    
    def ok(self, event):
        self.EndModal(wx.ID_OK)
        
            
        
        


class LabelEvaluation(wx.Frame):
    def __init__(self, parent):
        super(LabelEvaluation, self).__init__(parent, title = 'Label Efficiency Evaluation',
                                              size = (700, 300))
        self.panel = wx.Panel(self, -1)
        
        dataLabel, self.dataCtrl, dataButton = self.ctrlSet('Data File')
        resultsLabel, self.resultsCtrl, resultsButton = self.ctrlSet('Results File')
        featureLabel, self.featureCtrl, featureButton = self.ctrlSet('Feature File (Optional)')
        self.goButton = wx.Button(self.panel, -1, "Evaluate")
        
        self.linkBrowser(self.dataCtrl, dataButton, "Choose Data File",
                         'RAW|*.raw|Other|*.*')
        self.linkBrowser(self.resultsCtrl, resultsButton, "Choose Search Results File",
                         'XLSX|*.xlsx|XLS|*.xls|Other|*.*')
        self.linkBrowser(self.featureCtrl, featureButton, "Choose Feature Data File",
                         '*.*')
        self.Bind(wx.EVT_BUTTON, self.evaluate, self.goButton)
        
        self.gbs = wx.GridBagSizer(20, 20)
        self.placeSet(0, dataLabel, self.dataCtrl, dataButton)
        self.placeSet(1, resultsLabel, self.resultsCtrl, resultsButton)
        self.placeSet(2, featureLabel, self.featureCtrl, featureButton)
        self.gbs.Add(self.goButton, (4, 0), span = (1, 3), flag = wx.EXPAND)
        
        self.gbs.AddGrowableCol(1)
        
        overBox = wx.BoxSizer()
        overBox.Add(self.gbs, 1, wx.ALL, 20)
        self.panel.SetSizerAndFit(overBox)
        self.Centre()
        self.Show()
        
        
    def ctrlSet(self, label, default = ""):
        labelText = wx.StaticText(self.panel, -1, label)
        control = wx.TextCtrl(self.panel, -1, default, style = wx.EXPAND)
        browser = wx.Button(self.panel, -1, "Browse")
        
        return labelText, control, browser
        
    def placeSet(self, row, label, control, button):
        self.gbs.Add(label, (row, 0), flag = wx.ALIGN_RIGHT)
        self.gbs.Add(control, (row, 1), flag = wx.ALIGN_LEFT | wx.EXPAND)
        if button: self.gbs.Add(button, (row, 2))
        
    def linkBrowser(self, control, button, message, wildcard):
        def browseForFile(*etc):
            filedialog = wx.FileDialog(parent = self, message = message,
                                       wildcard = wildcard)
            filedialog.ShowModal()
            filepath = filedialog.GetPath()
            control.SetValue(filepath)
            
        self.Bind(wx.EVT_BUTTON, browseForFile, button)
        
    
    def evaluate(self, event):
        dataFile = self.dataCtrl.GetValue()
        resultsFile = self.resultsCtrl.GetValue()
        featureFile = self.featureCtrl.GetValue()
        
        assert resultsFile and (dataFile or featureFile), "Input files missing!"
        assert (os.path.exists(resultsFile) and
                (os.path.exists(dataFile) or
                 os.path.exists(featureFile))), "Input files not available!"
        
        outputfile = '.'.join(resultsFile.split('.')[:-1]) + '_LABEL_EVALUATION.xlsx'
        #evaluation, outputfile = evaluateMascotFile(resultsFile, dataFile,
                                                    #featureFile, outputfile)
        self.goButton.Enable(False)
        wx.BeginBusyCursor()
        evaluation, outputfile = async.launch_process(evaluateMascotFile, None,
                                                      resultsFile, dataFile,
                                                      featureFile, outputfile)       
        self.goButton.Enable(True)
        wx.EndBusyCursor()
        
        summaryDisplay = ShowEvaluationSummary(self, evaluation)
        summaryDisplay.ShowModal()
        


if __name__ == '__main__':
    app = wx.App(0)
    searcher = LabelEvaluation(None)
    app.MainLoop()    