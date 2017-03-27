import wx
import wxmpl
from numpy import arange

from gui import BasicTab
import multiplierz.mzTools.isoDist as isoDist

toolTip = ("Enter peptide sequence as a string of letters (e.g., 'PEPTIDE') or "
           "molecular formula as atomic letters followed by numbers (e.g. 'C502H7'; "
           "currently only CHNOPS are supported.)")

class IsotopePanel(BasicTab):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)

        panelBox = wx.GridBagSizer()

        inLabel = wx.StaticText(self, -1, style = wx.ALIGN_RIGHT,
                                label = "Chemical Formula or Pepide Sequence: ")
        inLabel.SetToolTip(wx.ToolTip(toolTip))
        self.inField = wx.TextCtrl(self, -1, value = "",  size = (300, -1), style = wx.TE_PROCESS_ENTER)
        self.goButton = wx.Button(self, -1, 'Calculate')
        self.Bind(wx.EVT_BUTTON, self.on_click, id = self.goButton.GetId())
        self.Bind(wx.EVT_TEXT_ENTER, self.on_click, id = self.inField.GetId())
        
        panelBox.Add(inLabel, (0, 1), flag = wx.ALIGN_CENTER | wx.ALL, border = 3)
        panelBox.Add(self.inField, (0, 2), flag = wx.ALIGN_CENTER | wx.ALL, border = 3)
        panelBox.Add(self.goButton, (0, 3), flag = wx.ALIGN_CENTER | wx.ALL, border = 10)

        graphRim = wx.Panel(self, -1, style = wx.SUNKEN_BORDER)
        graphBox = wx.BoxSizer()
        self.graphPanel = wxmpl.PlotPanel(graphRim, -1)
        graphBox.Add(self.graphPanel, 1, wx.EXPAND, 0)
        graphRim.SetSizerAndFit(graphBox)

        self.outputListBox = wx.TextCtrl(self,
                                         style = wx.TE_READONLY | wx.TE_MULTILINE | wx.TE_DONTWRAP | wx.TE_RIGHT)
        self.outputListBox.SetSize((10, -1))
        
        panelBox.Add(self.outputListBox, (2, 0), flag = wx.EXPAND)
        panelBox.Add(graphRim, (2, 1), flag = wx.EXPAND, span = wx.GBSpan(1, 4))
        
        panelBox.AddGrowableRow(2)
        panelBox.AddGrowableCol(3)
        
        overBox = wx.BoxSizer()
        overBox.Add(panelBox, 1, wx.ALL|wx.EXPAND, 20)
        self.SetSizerAndFit(overBox)
        
        
        
        

    def on_click(self, event):
        inputSequence = self.inField.GetValue()
        if not all(x in isoDist.aminoForms for x in inputSequence):
            messdog = wx.MessageDialog(self, "Error- invalid amino acid string: %s ." % inputSequence,
                                       style = wx.OK)
            messdog.ShowModal()
            messdog.Destroy()
            return               
        inputRecipe = isoDist.renderFormula(inputSequence)
        isotopes = isoDist.isotopicDistribution(inputRecipe)

        #majorIsotopes = [x for x in isotopes if x >= 1]
        while isotopes[-1] < 0.1:
            isotopes = isotopes[:-1]

        distFig = self.graphPanel.get_figure()
        distFig.clf()
        distAx = distFig.add_subplot(111)
        distAx.bar(range(0, len(isotopes) + 1), [0] + isotopes,
                   width = 0.3, align = 'center')
        distAx.set_xticks(arange(len(isotopes) + 1))
        distAx.set_yticks(arange(0, 110, 10))
        distAx.set_ylim(0, 110)
        self.graphPanel.draw()

        isoString = ""
        for isotope in isotopes:
            isoString += ("%.8f\n" % isotope)
        self.outputListBox.Clear()
        self.outputListBox.AppendText(isoString)
        
        print "Distribution calculated."







