import wx
import wx.grid
import os

from gui import BasicTab
from multiplierz.mass_biochem import peptideForMass

from fragment import FragmentPanel
from digest import DigestPanel


class DeNovoDisplay(wx.Frame):
    def __init__(self, parent, id, columns, data):
        wx.Frame.__init__(self, parent, id, title = "Peptide Sequences For Mass")
        
        #parent.SetIcon(parent.get_icon())
        pane = wx.Panel(self, -1, style = wx.TAB_TRAVERSAL | wx.CLIP_CHILDREN)
        
        grid = wx.grid.Grid(pane, -1)
        grid.CreateGrid(len(data), len(columns))
        for i, col in enumerate(columns):
            grid.SetColLabelValue(i, col)
        
        for row, values in enumerate(data):
            for col in range(len(columns)):
                grid.SetCellValue(row, col, str(values[col]))
        
        overBox = wx.BoxSizer()
        overBox.Add(grid, 1, wx.EXPAND|wx.ALL, 5)
        pane.SetSizerAndFit(overBox)
        
        

class DeNovoPanel(BasicTab):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)

        #self.denovoTitle = wx.StaticText(self, -1, "Peptide-For-Mass Prediction")

        self.massLabel = wx.StaticText(self, -1, "Observed Mass")
        self.massCtrl = wx.TextCtrl(self, -1)
        self.lengthLabel = wx.StaticText(self, -1, "Peptide Length")
        self.lengthCtrl = wx.TextCtrl(self, -1)
        self.toleranceLabel = wx.StaticText(self, -1, "Mass Tolerance")
        self.toleranceCtrl = wx.TextCtrl(self, -1)
        
        self.waterCheck = wx.CheckBox(self, -1, "Include terminal H2O")
        self.permutCheck = wx.CheckBox(self, -1, "Show All Permutations")
        
        self.calcButton = wx.Button(self, -1, "Calculate Peptides")
        self.Bind(wx.EVT_BUTTON, self.calculate, self.calcButton)
        
        gbs = wx.GridBagSizer(10, 10)
        #gbs.Add(self.denovoTitle, (0, 0))
        gbs.Add(self.massLabel, (2, 0), flag = wx.ALIGN_RIGHT)
        gbs.Add(self.massCtrl, (2, 1), flag = wx.ALIGN_LEFT)
        gbs.Add(self.lengthLabel, (3, 0), flag = wx.ALIGN_RIGHT)
        gbs.Add(self.lengthCtrl, (3, 1), flag = wx.ALIGN_LEFT)
        gbs.Add(self.toleranceLabel, (4, 0), flag = wx.ALIGN_RIGHT)
        gbs.Add(self.toleranceCtrl, (4, 1), flag = wx.ALIGN_LEFT)
        gbs.Add(self.waterCheck, (2, 3), flag = wx.ALIGN_LEFT)
        gbs.Add(self.permutCheck, (3, 3), flag = wx.ALIGN_LEFT)
        gbs.Add(self.calcButton, (5, 0), span = (1, 2), flag = wx.EXPAND)
        
        
        overBox = wx.BoxSizer()
        overBox.Add(gbs, 1, wx.ALL|wx.EXPAND, 20)
        self.SetSizerAndFit(overBox)
    
    def calculate(self, event):
        mass = self.massCtrl.GetValue()
        length = self.lengthCtrl.GetValue()
        tolerance = self.toleranceCtrl.GetValue()
        
        water = self.waterCheck.GetValue()
        permute = self.permutCheck.GetValue()
        
        try:
            mass = float(mass)
            length = int(length)
            tolerance = float(tolerance)
            
            peptides = peptideForMass(mass, length, tolerance,
                                      add_H2O = water, unique_sets = not permute)
            
            if not peptides:
                raise Exception, "No peptides found for the given parameters."
            
            outputFrame = DeNovoDisplay(self, -1, ['Sequence', 'Mass'], peptides)
            outputFrame.Show()
            
        except Exception as err:
            wx.MessageBox(message = str(err))
        
            
            
            


class PeptidePanel(BasicTab):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)
        
        fragmenter = FragmentPanel(self)
        digester = DigestPanel(self)
        denovo = DeNovoPanel(self)
        
        fragTitle = wx.StaticText(self, -1, "Fragmentation")
        digeTitle = wx.StaticText(self, -1, "Digestion")
        denoTitle = wx.StaticText(self, -1, "Sequence")
        fragTitle.SetFont(wx.Font(15, wx.DEFAULT, wx.NORMAL, wx.NORMAL))
        digeTitle.SetFont(wx.Font(15, wx.DEFAULT, wx.NORMAL, wx.NORMAL))
        denoTitle.SetFont(wx.Font(15, wx.DEFAULT, wx.NORMAL, wx.NORMAL))
        
        #self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        #self.sizer.Add(fragmenter, flag = wx.EXPAND)
        #self.sizer.Add(wx.StaticLine(self, style = wx.LI_VERTICAL), flag = wx.EXPAND)
        #self.sizer.Add(digester, flag = wx.EXPAND)
        #self.sizer.Add(wx.StaticLine(self, style = wx.LI_VERTICAL), flag = wx.EXPAND)
        #self.sizer.Add(denovo, flag = wx.EXPAND)
        gbs = wx.GridBagSizer()
        gbs.Add(fragTitle, (0, 0), flag = wx.ALIGN_CENTER)
        gbs.Add(fragmenter, (1, 0), flag = wx.EXPAND)
        gbs.Add(wx.StaticLine(self, style = wx.LI_VERTICAL), (0, 1),
                span = (2, 1), flag = wx.EXPAND)
        gbs.Add(digeTitle, (0, 2), flag = wx.ALIGN_CENTER)
        gbs.Add(digester, (1, 2), flag = wx.EXPAND)
        gbs.Add(wx.StaticLine(self, style = wx.LI_VERTICAL), (0, 3),
                span = (2, 1), flag = wx.EXPAND)
        gbs.Add(denoTitle, (0, 4), flag = wx.ALIGN_CENTER)
        gbs.Add(denovo, (1, 4), flag = wx.EXPAND)
        
        gbs.AddGrowableCol(0)
        gbs.AddGrowableCol(2)
        gbs.AddGrowableCol(4)
        gbs.AddGrowableRow(1)
        
        self.SetSizerAndFit(gbs)