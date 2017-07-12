import wx
import re
import os


from multiplierz import myData
try:
    raise Exception
    regularExpressionFile = open(os.path.join(myData, 'RegularExpressions.txt'), 'r')
    someNiceRegularExpressions = []
    for line in regularExpressionFile:
        someNiceRegularExpressions.append(line.strip())
except:
    someNiceRegularExpressions = [r'.+(?# Returns whole input)',
                                  r'[0-9]+(?# Returns first number- i.e., sequence of digits)',
                                  r'[0-9]+[/.][0-9]*(?# Returns first floating-point number- i.e., digits with single optional . character)',
                                  r'(?<=[-])[0-9]+[/.][0-9]*(?=[-])(?# Returns a floating-point number between two - characters)',
                                  r'(?<=[\s])[\S]+(?=[\s])(?# Returns first text surrounded by whitespace.)',
                                  r"(?<=[\s,>])[\S]+(?=[\s])(?# Returns first text surrounded by whitespace or the > character, such as in FASTA.)",
                                  r"([0-9]{2,})(?=\.\1)(?# Returns the first number that repeats after a following '.', e.g. '393.393'.)",
                                  "(?<=\|)[A-Z0-9\-]{1,10}(?=\|)(?# SwissProt/UniProt)",
                                  "(?<=ref\|)[A-Z0-9\-\_\.]{1,20}(?=\|)(?# NCBI)"]
    regularExpressionFile = open(os.path.join(myData, 'RegularExpressions.txt'), 'w')
    regularExpressionFile.writelines(someNiceRegularExpressions)
    regularExpressionFile.close()

class RegexHelper(wx.Dialog):
    def __init__(self, parent = None, startRegex = '', startSample = ''):
        super(RegexHelper, self).__init__(parent,
                                         title = "Regular Expression Utility",
                                         size = (1000, 300))
        
        panel = wx.Panel(self, -1, style = wx.EXPAND)
        
        helpfulText = wx.StaticText(panel, -1, ("See the Python re module documentation for help writing regular expressions."))
        
        self.regexLabel = wx.StaticText(panel, -1, "Regular Expression (Regex)")
        self.regexField = wx.ComboBox(panel, -1, value = startRegex, size = (-1, -1),
                                      choices = [startRegex] + someNiceRegularExpressions)
        self.sampleLabel = wx.StaticText(panel, -1, "Sample String")
        self.sampleField = wx.TextCtrl(panel, -1, startSample, size = (-1, -1))
        self.goButton = wx.Button(panel, -1, "Apply Regular Expression")
        self.goButton.Bind(wx.EVT_BUTTON, self.applyRegex)
        self.resultField = wx.TextCtrl(panel, -1, "", size = (-1, -1), style = wx.TE_READONLY)
        
        self.doneButton = wx.Button(panel, -1, "OK")
        self.doneButton.Bind(wx.EVT_BUTTON, self.OK)
        
        gridBag = wx.GridBagSizer(12, 5)
        gridBag.Add(helpfulText, (0, 0), span = (1, 3))
        gridBag.Add(self.regexLabel, (1, 0), flag = wx.ALIGN_RIGHT)
        gridBag.Add(self.regexField, (1, 1), span = (1, 2), flag = wx.EXPAND)
        gridBag.Add(self.sampleLabel, (2, 0), flag = wx.ALIGN_RIGHT)
        gridBag.Add(self.sampleField, (2, 1), span = (1, 2), flag = wx.EXPAND)
        gridBag.Add(self.goButton, (3, 0), span = (1, 3), flag = wx.EXPAND)
        gridBag.Add(self.resultField, (4, 0), span = (1, 3), flag = wx.EXPAND)
        gridBag.Add(self.doneButton, (6, 1), span = (1, 1), flag = wx.EXPAND)
        
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        
        gridBag.AddGrowableRow(0)
        gridBag.AddGrowableCol(2)
        gridBag.AddGrowableRow(3)
        
        box = wx.BoxSizer()
        box.Add(gridBag, 1, wx.ALL | wx.EXPAND, 20)
        panel.SetSizerAndFit(box)
        #self.Show()
        
    def applyRegex(self, event):
        regex = self.regexField.GetValue()
        sample = self.sampleField.GetValue()
        match = re.search(regex, sample)
        
        if match:
            self.resultField.SetValue(match.group(0))
        else:
            self.resultField.SetValue("--- No match ---")
            
    def getRegex(self):
        return self.regexField.GetValue()
        
        
    def OnClose(self, event):
        self.EndModal(wx.ID_CANCEL)
    def OK(self, event):
        self.EndModal(wx.ID_OK)
        
        
        
def runRegexHelper():
    app = wx.App(0)
    session = RegexHelper(None, '')

    if session.ShowModal() == wx.ID_OK:
        print session.getRegex()
    else:
        print "Nah."
    app.MainLoop()


if __name__ == '__main__':
    print runRegexHelper()