import multiplierz.fasta as fasta
from gui import BasicTab
import wx
from multiplierz.mass_biochem import enzymeSpecification





partialDatabaseTooltip = ("Creates a new FASTA database by copying each entry from"
                          "the original where the entry header contains the selector"
                          "string.")
reverseDatabaseTooltip = ("Creates a new FASTA database in which the peptide sequence"
                          "in every entry is reversed, for use in forward-reverse"
                          "decoy analysis.  'rev_' is appended to be beginning"
                          "of each header.")
forwardReverseTooltip = ("Creates a new FASTA database containing both all the entries"
                         "of the original database and duplicates of all entries with"
                         "reversed sequences (and with 'rev_' appended to the header.)"
                         "Useful for searches with early versions of Mascot, which"
                         "only search one database at a time.")
pseudoReverseTooltip = ("Creates a new FASTA database in which all peptide sub-sequences,"
                        "split according to the specified enzyme, are reversed; this may"
                        "offer slightly better search characteristics, as described in "
                        "(Elias and Gygi 2007, 'Target-decoy search strategy for increased"
                        "confidence in large-scale protein identifications by mass spectrometry.')")
pseudoForwardReverseTooltip = ("As above, but with both the original and pseudo-reversed entries.")
combinedTooltip = ("Combine multiple FASTA databases together.")


class FastaPanel(BasicTab):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)
        
        self.gbs = wx.GridBagSizer(10, 10)
        
        chooserLabel = wx.StaticText(self, -1, "FASTA\nfile(s)")
        self.chooserCtrl = wx.TextCtrl(self, -1, "", size = (-1, 75))
        self.chooserButton = wx.Button(self, -1, "Browse")
        
        selectorLabel = wx.StaticText(self, -1, "Selector String")
        self.selectorCtrl = wx.TextCtrl(self, -1, "")
        self.selectorButton = wx.Button(self, -1, "Create Partial Database")
        
        self.reverseButton = wx.Button(self, -1, "Create Reverse Database")
        self.forwardReverseButton = wx.Button(self, -1, "Create Forward/Reverse Database")
        
        self.pseudoReverseButton = wx.Button(self, -1, "Create Pseudo-Reverse Database")
        self.pseudoRevEnzyme = wx.ComboBox(self, -1, value = "Trypsin", choices = enzymeSpecification.keys())
        
        self.pseudoForwardReverseButton = wx.Button(self, -1, "Create Forward/Pseudo-Reverse Database")
        self.pseudoForwardRevEnzyme = wx.ComboBox(self, -1, value = "Trypsin", choices = enzymeSpecification.keys())
        
        self.combineButton = wx.Button(self, -1, "Combine Databases")
        
        self.gbs.Add(chooserLabel, (0, 0), flag = wx.ALIGN_RIGHT)
        self.gbs.Add(self.chooserCtrl, (0, 1), span = (2, 5), flag = wx.EXPAND)
        self.gbs.Add(self.chooserButton, (0, 7), flag = wx.ALIGN_LEFT)
        
        self.gbs.Add(selectorLabel, (2, 0), flag = wx.ALIGN_RIGHT)
        self.gbs.Add(self.selectorCtrl, (2, 1), span = (1, 3), flag = wx.EXPAND)
        self.gbs.Add(self.selectorButton, (2, 5), flag = wx.ALIGN_LEFT)
        
        self.gbs.Add(self.reverseButton, (4, 1), flag = wx.EXPAND)
        self.gbs.Add(self.forwardReverseButton, (5, 1), flag = wx.EXPAND)
        self.gbs.Add(self.pseudoReverseButton, (6, 1), flag = wx.EXPAND)
        self.gbs.Add(self.pseudoRevEnzyme, (6, 2))
        self.gbs.Add(self.pseudoForwardReverseButton, (7, 1), flag = wx.EXPAND)
        self.gbs.Add(self.pseudoForwardRevEnzyme, (7, 2))
        self.gbs.Add(self.combineButton, (8, 1), flag = wx.EXPAND)
        
        self.selectorButton.SetToolTip(wx.ToolTip(partialDatabaseTooltip))
        self.reverseButton.SetToolTip(wx.ToolTip(reverseDatabaseTooltip))
        self.forwardReverseButton.SetToolTip(wx.ToolTip(forwardReverseTooltip))
        self.pseudoReverseButton.SetToolTip(wx.ToolTip(pseudoReverseTooltip))
        self.pseudoForwardReverseButton.SetToolTip(wx.ToolTip(pseudoForwardReverseTooltip))
        self.combineButton.SetToolTip(wx.ToolTip(combinedTooltip))
        
        
        self.gbs.AddGrowableCol(7)
        #self.gbs.AddGrowableRow(3)
        #self.gbs.AddGrowableRow(7)
        
        overBox = wx.BoxSizer()
        overBox.Add(self.gbs, 1, wx.ALL|wx.EXPAND, 20)
        
        self.SetSizerAndFit(overBox)
        
        self.Bind(wx.EVT_BUTTON, self.onChoose, self.chooserButton)
        self.Bind(wx.EVT_BUTTON, self.onSelector, self.selectorButton)
        self.Bind(wx.EVT_BUTTON, self.onReverse, self.reverseButton)
        self.Bind(wx.EVT_BUTTON, self.onForwardReverse, self.forwardReverseButton)
        self.Bind(wx.EVT_BUTTON, self.onCombine, self.combineButton)
        self.Bind(wx.EVT_BUTTON, self.onPseudoReverse, self.pseudoReverseButton)
        self.Bind(wx.EVT_BUTTON, self.onPseudoForwardReverse, self.pseudoForwardReverseButton)
        
        
    def onChoose(self, event):
        filedialog = wx.FileDialog(parent = self, message = "Choose FASTA",
                                   wildcard = 'FASTA|*.fasta|Other|*',
                                   style = wx.FD_OPEN | wx.FD_MULTIPLE)
        if filedialog.ShowModal() == wx.ID_OK:
            newfiles = filedialog.GetPaths()
        else:
            print "Not ID_OK"
            return

        self.chooserCtrl.Clear()
        self.chooserCtrl.AppendText('; '.join(newfiles))
        
    def onSelector(self, event):
        fastas = self.chooserCtrl.GetValue().split(';')
        outputs = []
        
        selector = self.selectorCtrl.GetValue().strip()
        
        for fastafile in fastas:
            filedialog = wx.FileDialog(parent = self, message = "Choose Output For Selector on %s" % fastafile,
                                       wildcard = 'FASTA|*.fasta|Other|*',
                                       style = wx.FD_SAVE)
            if filedialog.ShowModal() == wx.ID_OK:
                outputs.append(filedialog.GetPath())
            else:
                print "Not ID_OK"
                return
        
        self.set_status("Working...", 0)
        self.set_status("", 1)          
        for fastafile, output in zip(fastas, outputs):
            fasta.partial_database(fastafile, output, selector)
        self.set_status("Ready", 0)
        self.set_status("Done", 1)            
            
            
    def invokeReverser(self, includeForward):
        fastas = self.chooserCtrl.GetValue().split(';')
        outputs = []

        for fastafile in fastas:
            filedialog = wx.FileDialog(parent = self, message = "Choose Output For %s" % fastafile,
                                       wildcard = 'FASTA|*.fasta|Other|*',
                                       style = wx.FD_SAVE)
            if filedialog.ShowModal() == wx.ID_OK:
                outputs.append(filedialog.GetPath())
            else:
                print "Not ID_OK"
                return
        
        self.set_status("Working...", 0)
        self.set_status("", 1)        
        for fastafile, output in zip(fastas, outputs):
            fasta.reverse_database(fastafile, output, include_forward = includeForward)    
        self.set_status("Ready", 0)
        self.set_status("Done", 1)          
            
    def onReverse(self, event):
        self.invokeReverser(False)
            
    def onForwardReverse(self, event):
        self.invokeReverser(True)
        
    def onPseudoReverse(self, event):
        fastas = self.chooserCtrl.GetValue().split(';')
        enzyme = self.pseudoRevEnzyme.GetValue()
        outputs = []

        for fastafile in fastas:
            filedialog = wx.FileDialog(parent = self, message = "Choose Output For %s" % fastafile,
                                       wildcard = 'FASTA|*.fasta|Other|*',
                                       style = wx.FD_SAVE)
            if filedialog.ShowModal() == wx.ID_OK:
                outputs.append(filedialog.GetPath())
            else:
                print "Not ID_OK"
                return
        
        self.set_status("Working...", 0)
        self.set_status("", 1)        
        for fastafile, output in zip(fastas, outputs):
            fasta.pseudo_reverse(fastafile, output, enzyme = enzyme)    
        self.set_status("Ready", 0)
        self.set_status("Done", 1) 
        
    def onPseudoForwardReverse(self, event):
        fastas = self.chooserCtrl.GetValue().split(';')
        enzyme = self.pseudoForwardRevEnzyme.GetValue()
        outputs = []

        for fastafile in fastas:
            filedialog = wx.FileDialog(parent = self, message = "Choose Output For %s" % fastafile,
                                       wildcard = 'FASTA|*.fasta|Other|*',
                                       style = wx.FD_SAVE)
            if filedialog.ShowModal() == wx.ID_OK:
                outputs.append(filedialog.GetPath())
            else:
                print "Not ID_OK"
                return
        
        self.set_status("Working...", 0)
        self.set_status("", 1)        
        for fastafile, output in zip(fastas, outputs):
            fasta.pseudo_reverse(fastafile, output, enzyme = enzyme, include_forward = True)    
        self.set_status("Ready", 0)
        self.set_status("Done", 1)        
        
    def onCombine(self, event):
        fastas = [x.strip() for x in self.chooserCtrl.GetValue().split(';')]
        
        filedialog = wx.FileDialog(parent = self, message = "Choose Output For Combined File",
                                   wildcard = 'FASTA|*.fasta|Other|*',
                                   style = wx.FD_SAVE)
        if filedialog.ShowModal() == wx.ID_OK:
            output = filedialog.GetPath()
        else:
            print "Not ID_OK"
            return        
        
        self.set_status("Working...", 0)
        self.set_status("", 1)
        fasta.combine(fastas, output)
        self.set_status("Ready", 0)
        self.set_status("Done", 1)            