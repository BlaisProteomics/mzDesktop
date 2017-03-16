from multiplierz.mzReport import reader, writer
import wxmpl
import wx
from collections import defaultdict
from gui import BasicTab
import wx.grid
import wx.lib.inspection
import wx.richtext as ri
from multiplierz import parseFasta
from math import floor

timesNewPeptide = wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
detectedPeptide = wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)

normalStyle = ri.RichTextAttr(wx.TextAttr(colText = 'black', colBack = 'white', font = timesNewPeptide))
foundStyle = ri.RichTextAttr(wx.TextAttr(colText = 'black', colBack = 'red', font = timesNewPeptide))

class DataError(Exception):
    def __init__(self, value = None):
        self.value = value
    def __str__(self):
        return repr(self.value)

class CoveragePanel(BasicTab):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)

        fastaLabel = wx.StaticText(self, -1, "FASTA File")
        self.fastaChooser = wx.TextCtrl(self, -1, "", style = wx.TE_PROCESS_ENTER)
        self.fastaButton = wx.Button(self, -1, "Browse")
        
        regexLabel = wx.StaticText(self, -1, "FASTA Label Parser")
        self.regexEntry = wx.TextCtrl(self, -1, "")

        fileLabel = wx.StaticText(self, -1, "Results File")
        self.fileChooser = wx.TextCtrl(self, -1, "", style = wx.TE_PROCESS_ENTER)
        self.browseButton = wx.Button(self, -1, "Browse")

        self.protList = wx.grid.Grid(self, -1)
        
        self.protGraph = wxmpl.PlotPanel(self, -1, size = (-1, 0.5))
        self.sequenceDisplay = wxmpl.PlotPanel(self, -1)

        scoreCutLabel = wx.StaticText(self, -1, "Score cutoff")
        self.scoreCutCtrl = wx.TextCtrl(self, -1, '0', size = (35, -1),
                                        style = wx.TE_CENTRE | wx.TE_PROCESS_ENTER)
        
        accessionCtrlLabel = wx.StaticText(self, -1, "Accession ")
        self.prevAccession = wx.Button(self, -1, "<", size = (20, -1))
        self.accessionCounter = wx.TextCtrl(self, -1, '0', size = (35, -1),
                                            style = wx.TE_READONLY | wx.TE_CENTRE)
        self.nextAccession = wx.Button(self, -1, ">", size = (20, -1))
        
        gbs = wx.GridBagSizer(15, 7)

        gbs.Add(fastaLabel, (0,0), flag = wx.ALIGN_RIGHT)
        gbs.Add(self.fastaChooser, (0,1), (1, 4), flag = wx.EXPAND)
        gbs.Add(self.fastaButton, (0, 5), flag = wx.ALIGN_LEFT)
        
        gbs.Add(regexLabel, (0, 6), flag = wx.ALIGN_RIGHT)
        gbs.Add(self.regexEntry, (0, 7), flag = wx.EXPAND)

        gbs.Add(fileLabel, (1,0), flag = wx.ALIGN_RIGHT)
        gbs.Add(self.fileChooser, (1, 1), (1, 6), flag = wx.EXPAND)
        gbs.Add(self.browseButton, (1, 7), flag = wx.ALIGN_LEFT)

        gbs.Add(self.protGraph, (2,3), (1,7), flag = wx.EXPAND)
        gbs.Add(self.protList, (2,0), (6, 3), flag = wx.EXPAND)
        gbs.Add(self.sequenceDisplay, (3, 3), (5, 7), flag = wx.EXPAND)
        
        gbs.Add(scoreCutLabel, (8, 0), flag = wx.CENTER)
        gbs.Add(self.scoreCutCtrl, (8, 1), flag = wx.ALIGN_LEFT)
        
        accessionBox = wx.BoxSizer(wx.HORIZONTAL)
        accessionBox.Add(accessionCtrlLabel, flag = wx.CENTER)
        accessionBox.Add(self.prevAccession, flag = wx.ALIGN_RIGHT)
        accessionBox.Add(self.accessionCounter, flag = wx.CENTER)
        accessionBox.Add(self.nextAccession, flag = wx.ALIGN_LEFT)
        gbs.Add(accessionBox, (8, 4))

        gbs.AddGrowableCol(2)
        gbs.AddGrowableCol(3)
        gbs.AddGrowableCol(4)
        gbs.AddGrowableRow(5)

        self.fastaFilename = None
        self.filenames = ['']
        self.sequence = None
        self.psms = None
        
        self.protList.CreateGrid(100, 2)
        self.protList.SetRowLabelSize(1)
        self.protList.SetColLabelValue(0, "GI")
        self.protList.SetColLabelValue(1, "Description")
        self.protList.SetMaxSize((-1, 500))
        self.protList.SetMinSize((10, 10)) # Here's the key to making wx.Grids behave appropriately.
        
        overBox = wx.BoxSizer()
        overBox.Add(gbs, 1, wx.ALL | wx.EXPAND, 20)
        self.SetSizerAndFit(overBox)
        
        self.Bind(wx.EVT_TEXT_ENTER, self.openFile, self.fileChooser)
        self.Bind(wx.EVT_BUTTON, self.browseForFasta, self.fastaButton)
        self.Bind(wx.EVT_BUTTON, self.browseForFile, self.browseButton)
        self.Bind(wx.grid.EVT_GRID_CELL_LEFT_CLICK, self.readProtein, self.protList)  
        self.Bind(wx.EVT_SIZE, self.resizeHandler)
        self.Bind(wx.EVT_TEXT_ENTER, self.scoreFilter, self.scoreCutCtrl)
        self.Bind(wx.EVT_BUTTON, self.prevAccessionPressed, self.prevAccession)
        self.Bind(wx.EVT_BUTTON, self.nextAccessionPressed, self.nextAccession)

        #self.sequenceDisplay.SetFont(timesNewPeptide)
        
        deviceContext = wx.ScreenDC()
        deviceContext.SetFont(timesNewPeptide)
        self.textBlockWidth, _ = deviceContext.GetTextExtent("PEPTIDESTR ")
        
        self.seqBlocksPerRow = None
        self.resizeHandler(None)
        
        self.subAccession = 0
        self.scoreCutoff = 0


    def resizeHandler(self, event): 
        wx.CallAfter(self.fixGridRows) # Its absurd that this has to be done.
        wx.CallAfter(self.resizeSequence)
        if event: event.Skip()

    def fixGridRows(self):
        gridWidth, _ = self.protList.GetSize()
        accessionWidth = min([(gridWidth-18)/2, 200])
        descWidth = gridWidth - (accessionWidth + 18)
        self.protList.SetColSize(0, accessionWidth)
        self.protList.SetColSize(1, descWidth)
        
    def resizeSequence(self):
        seqBoxWidth, _ = self.sequenceDisplay.GetSize()
        self.seqBlocksPerRow = floor((seqBoxWidth / float(self.textBlockWidth)) - 0.15)
        
        if self.sequence:
            self.displayProtein(None)
        
        
    def browseForFasta(self, event):
        filedialog = wx.FileDialog(parent = self, message = "Choose Files",
                                   style = wx.FD_OPEN)
        filedialog.ShowModal()
        newfile = filedialog.GetPath()

        self.fastaChooser.Clear()
        self.fastaChooser.AppendText(newfile)


    def browseForFile(self, event):
        filedialog = wx.FileDialog(parent = self, message = "Choose Files",
                                   style = wx.FD_OPEN | wx.FD_MULTIPLE)
        filedialog.ShowModal()
        newfiles = filedialog.GetPaths()

        self.fileChooser.Clear()
        self.fileChooser.AppendText('; '.join(newfiles))
        
        self.openFile(None)

    def openFile(self, event):
        print "openFile"
        filenames = self.fileChooser.GetValue()
        filenames = [x.strip() for x in filenames.split(';')]

        #if not filenames or filenames == self.filenames: return
        #else: self.filenames = filenames
        self.filenames = filenames

        reportData = []
        for resultFile in filenames:
            report = reader(resultFile)
            reportData += list(report)

        self.psmsByAccession = defaultdict(list)
        protList = []
        for psm in reportData:
            if float(psm['Peptide Score']) < self.scoreCutoff: continue
            
            protList.append((psm['Accession Number'], psm['Protein Description']))
            for accession in psm['Accession Number'].split(';'):
                #protein = psm['Accession Number'], psm['Protein Description']
                self.psmsByAccession[accession].append(psm)

        self.updateProtList(protList)

    def fastaLookup(self, protein):
        print "fastaLookup"
        if not (self.fastaFilename and self.fastaFilename == self.fastaChooser.GetValue()):
            self.fastaFilename = self.fastaChooser.GetValue()
            if not self.fastaFilename: return
            
            labelConverter = lambda x: x.split(' ')[0][1:]
            self.fasta = parseFasta(self.fastaFilename, labelConverter)
        
        try:
            return self.fasta[protein]
        except KeyError:
            raise DataError, "Protein sequence not available in FASTA database."

    def scoreFilter(self, event):
        self.scoreCutoff = float(self.scoreCutCtrl.GetValue())
        self.openFile(event)
        
    def updateProtList(self, proteinData):
        print "updateProtList"
        line = 0
        if self.protList.GetNumberRows():
            self.protList.DeleteRows(numRows = self.protList.GetNumberRows())
        self.protList.InsertRows(numRows = len(proteinData))
        for accession, description in proteinData:
            self.protList.SetCellValue(line, 0, accession)
            self.protList.SetCellValue(line, 1, description)
            line += 1

    def readProtein(self, event):
        try:
            self.Enable(False)
            
            print "readProtein"
            
            protein = (self.protList.GetCellValue(event.GetRow(), 0),
                       self.protList.GetCellValue(event.GetRow(), 1))
            
            if not protein[0]:
                if event:
                    event.Skip()            
                return

            self.accessions = protein[0].split(';')
            accession = self.accessions[0]
            
            self.subAccession = 0
            self.accessionCounter.SetValue(str(0))
            self.accessionCount = len(self.accessions)            
            
            accession = protein[0]
            if ';' in accession:
                accession = accession.split(';')[0]            

            self.sequence = self.fastaLookup(accession)
            self.psms = self.psmsByAccession[accession]
    
            self.peptideCoverage = {}
            for psm in self.psms:
                pepSeq = psm['Peptide Sequence']
                index = self.sequence.index(pepSeq)
                extent = len(pepSeq)
                self.peptideCoverage[index] = extent
    
            self.displayProtein(None)
        except DataError as err:
            errBox = wx.MessageBox(str(err), "An Error Occurred.")
            import traceback
            print traceback.format_exc()       
        finally:
            self.Enable(True)
        
        if event:
            event.Skip()
            
    def prevAccessionPressed(self, event):
        if self.subAccession > 0:
            self.subAccession -= 1
            self.accessionCounter.SetValue(str(self.subAccession))
            self.displayAccession()
    def nextAccessionPressed(self, event):
        if self.subAccession < self.accessionCount - 1:
            self.subAccession += 1
            self.accessionCounter.SetValue(str(self.subAccession))
            self.displayAccession()
    
    def displayAccession(self):
        try:
            self.Enable(False)
            
            accession = self.accessions[self.subAccession]
            
            self.sequence = self.fastaLookup(accession.strip())
            self.psms = self.psmsByAccession[accession]
            
            self.peptideCoverage = {}
            for psm in self.psms:
                pepSeq = psm['Peptide Sequence']
                index = self.sequence.index(pepSeq)
                extent = len(pepSeq)
                self.peptideCoverage[index] = extent 
            
            self.displayProtein(None)
        except DataError as err:
            errBox = wx.MessageBox(str(err), "An Error Occurred.")
            import traceback
            print traceback.format_exc()       
        finally:
            self.Enable(True)
        
    #def displayProtein(self, event):
        #print "displayProtein"

        #if self.seqBlocksPerRow == None:
            #self.resizeSequence()
        
        #self.sequenceDisplay.Clear()
        #self.sequenceDisplay.EndAllStyles()
        ##self.sequenceDisplay.BeginTextColour((0,0,0))
        #self.sequenceDisplay.BeginStyle(normalStyle)
        #covEnds = []
        #i = 0
        #blocks = 0
        #for char in self.sequence:
            #if i % 10 == 0 and i:
                #self.sequenceDisplay.WriteText(' ')
                #blocks += 1
            #if blocks % self.seqBlocksPerRow == 0 and blocks:
                #self.sequenceDisplay.Newline()
                #blocks = 0
            #while i in covEnds:
                ##self.sequenceDisplay.EndTextColour()
                #self.sequenceDisplay.EndStyle()
                #covEnds.remove(i)
            #if i in self.peptideCoverage.keys():
                ##self.sequenceDisplay.BeginTextColour((0,255,0))
                #self.sequenceDisplay.BeginStyle(foundStyle)
                #covEnds.append(self.peptideCoverage[i] + i)

            #self.sequenceDisplay.WriteText(char)
            #i += 1       
        #print "Done."
        
    def displayProtein(self, event):
        print "displayProtein"
        
        if self.seqBlocksPerRow == None:
            self.resizeSequence()
        
        figure = self.sequenceDisplay.get_figure()
        figure.clear()
        
        dpi = figure.get_dpi()
        width = figure.get_figwidth() * dpi

        leftMargin = width / 10.0
        rightMargin = width - (width / 10.0)
        topMargin = 20
        
        nextCharHorz = leftMargin
        nextCharVert = topMargin
        inCurBlock = 0

        charHeight = 10
        charWidth = 10

        for char in self.sequence:
            if inCurBlock == 10:
                inCurBlock = 1
                if nextCharHorz + (charWidth * 11) > rightMargin:
                    nextCharVert += charHeight
                    nextCharHorz = leftMargin
                else:
                    nextCharHorz += charWidth
            
            print (nextCharVert, nextCharHorz)
            figure.text(nextCharVert/dpi, nextCharHorz/dpi, char)
            nextCharHorz += charWidth
            inCurBlock += 1
                
        print "Done."
        











