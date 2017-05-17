from multiplierz.mzReport import reader, writer
#import wxmpl
import wx
from collections import defaultdict
import wx.grid
import wx.lib.agw.xlsgrid as grid
import wx.lib.inspection
import wx.richtext as ri
from multiplierz.fasta import parse_to_dict
from math import floor, ceil
import re, os, os.path


try:
    from gui import BasicTab
    from utilities.regex import RegexHelper
except ImportError:
    from wx.lib.agw.flatnotebook import PageContainer
    BasicTab = PageContainer
    RegexHelper = lambda x: 1/0
    
    foo = wx.App(0)

from multiplierz import myData, fastaFiles
#fastaRecordFile = os.path.join(myData, "fastafiles.txt")

def readFastaRecords():
    if not os.path.exists(fastaFiles):
        print "Initializing fasta records."
        fastas = open(fastaFiles, 'w')
        fastas.close()
        return []
    
    with open(fastaFiles, 'r') as fastas:
        return [x.strip() for x in list(fastas) if os.path.exists(x.strip())]

def addToFastaRecords(paths):
    for path in paths:
        assert os.path.exists(path)
        
    existing = readFastaRecords()
    paths = [x for x in paths if not x in existing]
    for path in paths:    
        confirm = wx.MessageDialog(None, message = "Do you want to add %s to Multiplierz's FASTA list?" % path,
                                   style = wx.CENTER | wx.YES_NO)
        
        if confirm.ShowModal() == wx.ID_YES:
            with open(fastaFiles, 'a') as fastas:
                fastas.write(path + '\n')
            print "FASTA list updated."
        else:
            print "Not updating FASTA list."
    
    
timesNewPeptide = wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
detectedPeptide = wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)

chartAnnotateFont = wx.Font(7, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)

normalStyle = ('white', 'black')
foundStyle = (wx.Colour(255, 100, 100), 'black')
highlightStyle = (wx.Colour(0, 200, 0), 'black')
foundHighlightStyle = (wx.Colour(255, 100, 100), 'green')
foundModStyle = (wx.Colour(255, 100, 100), 'yellow')


selectedRow = wx.grid.GridCellAttr()
selectedRow.SetBackgroundColour('green')
nonSelectedRow = wx.grid.GridCellAttr()


class DataError(Exception):
    def __init__(self, value = None):
        self.value = value
    def __str__(self):
        return repr(self.value)



class FancyRenderer(wx.grid.PyGridCellRenderer):
    def __init__(self):
        wx.grid.PyGridCellRenderer.__init__(self)
        self.styles = defaultdict(lambda: [normalStyle] * 10)
        
    def SetStyles(self, row, col, styleInfo):
        self.styles[row, col] = styleInfo
        
    def Draw(self, grid, attr, dc, rect, row, col, isSelected):
        dc.SetBackgroundMode(wx.SOLID)
        dc.SetBrush(wx.Brush(wx.WHITE, wx.SOLID))
        dc.SetPen(wx.TRANSPARENT_PEN)
        dc.DrawRectangleRect(rect)

        #dc.SetBackgroundMode(wx.TRANSPARENT)
        dc.SetFont(attr.GetFont())

        text = grid.GetCellValue(row, col)
        x = rect.x + 1
        y = rect.y + 1

        for index, ch in enumerate(text):
            backColor, foreColor = self.styles[row, col][index]
            dc.SetTextForeground(foreColor)
            dc.SetTextBackground(backColor)
            
            dc.DrawText(ch, x, y)
            x = x + 9
            if x > rect.right - 5:
                break        
        

class HighlighterGrid(wx.grid.Grid):
    def __init__(self, parent):
        wx.grid.Grid.__init__(self, parent, -1)
        self.SetDefaultRenderer(FancyRenderer())
        
        #self.Bind(wx.EVT_MOTION, self.getTextPosition)
        
    
    def SetCellWithStyle(self, row, col, text, highlightThings):
        renderer = self.GetCellRenderer(row, col)
        renderer.SetStyles(row, col, highlightThings)
        self.SetCellValue(row, col, text)
        
    
    def RenderToDC(self, dc, offset):
        rows = self.GetNumberRows()
        cols = self.GetNumberCols()
        
        for row in range(0, rows):
            for col in range(0, cols):
                renderer = self.GetCellRenderer(row, col)
                rect = self.CellToRect(row, col)                
                #attr = self.GetDefaultAttributes()
                #attr = self.GetTable().GetAttr(row, col, wx.grid.GridCellAttr())
                attr = wx.grid.GridCellAttr()
                attr.SetFont(self.GetCellFont(row, col))
                
                rect.SetX(rect.GetX() + offset[0])
                rect.SetY(rect.GetY() + offset[1])
                
                renderer.Draw(self, attr, dc, rect, row, col, False)
                
                
        
    #def getTextPosition(self, event):
        #print event.GetPositionTuple()
        #event.Skip()
        

class ProteinGraphPanel(wx.Panel):
    def __init__(self, parent, size):
        super(ProteinGraphPanel, self).__init__(parent, size = size)
        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        self.SetBackgroundColour(wx.Colour(255,255,255))
        self.Bind(wx.EVT_SIZE, self.onSize)
        self.Bind(wx.EVT_PAINT, self.onPaint)
        
        self.protein = None
        self.dc = None
    
    def onSize(self, event):
        event.Skip()
        self.Refresh()
        
    
    def onPaint(self, event):
        dc = wx.AutoBufferedPaintDC(self)
        dc.Clear()
        
        dc.SetBackgroundMode(wx.TRANSPARENT)
        
        width, height = self.GetClientSize()
        horzOffset = 10
        vertOffset = 10
        
        horzExtent = width - (horzOffset*2)
        vertExtent = height - (vertOffset*2)
        
        dc.DrawRectangle(horzOffset, vertOffset, horzExtent, vertExtent)
        
        if not self.protein:    
            if event: event.Skip()
            return
        else:
            sequence, coverage = self.protein
            length = float(len(sequence))
            
            fractCover = []
            for begin, end in coverage.items():
                fractCover.append((begin/length, end/length, begin, begin + end))
        
            dc.SetBrush(wx.Brush(wx.Colour(255, 0, 0)))
            dc.SetFont(chartAnnotateFont)
        
            for begin, end, seqBegin, seqEnd in fractCover:
                dc.DrawRectangle(horzOffset + (horzExtent*begin), vertOffset,
                                 (horzExtent*end), vertExtent)
                # Add 1 to seqBegin (but not seqEnd!) to specify starting/ending AAs in 1-mode indexing.
                self.emplaceText(dc, str(seqBegin+1), horzOffset + (horzExtent*begin), vertOffset, 'bottom', 'right')
                self.emplaceText(dc, str(seqEnd), horzOffset + (horzExtent*(begin + end)), vertExtent + vertOffset, 'top', 'left')
            
            self.emplaceText(dc, "1", horzOffset + 2, vertOffset + vertExtent/2, 'mid', 'left')
            self.emplaceText(dc, str(len(sequence)), horzOffset + horzExtent - 2, vertOffset + vertExtent/2,
                             'mid', 'right')
            
            if event: event.Skip()
            
    def emplaceText(self, dc, text, x, y, vertAlign = 'mid', horzAlign = 'mid'):
        tW, tH = dc.GetTextExtent(text)
        
        if vertAlign == 'top':
            modY = y
        elif vertAlign == 'mid':
            modY = y - tH/2
        elif vertAlign == 'bottom':
            modY = y - tH
        else:
            raise Exception
            
        if horzAlign == 'left':
            modX = x
        elif horzAlign == 'mid':
            modX = x - tW/2
        elif horzAlign == 'right':
            modX = x - tW
        else:
            raise Exception
        
        dc.DrawText(text, modX, modY)



class CoveragePanel(BasicTab):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)

        fastaLabel = wx.StaticText(self, -1, "FASTA File")
        self.fastaChooser = wx.ComboBox(self, -1, "",
                                        choices = [''] + readFastaRecords(),
                                        style = wx.TE_PROCESS_ENTER)
        self.fastaButton = wx.Button(self, -1, "Browse")
        
        regexLabel = wx.StaticText(self, -1, "FASTA Label Parser")
        self.regexEntry = wx.TextCtrl(self, -1, "[\S]+(?=[\s])")
        self.regexHelp = wx.Button(self, -1, "Regular Expression Help")

        fileLabel = wx.StaticText(self, -1, "Results File")
        self.fileChooser = wx.TextCtrl(self, -1, "", style = wx.TE_PROCESS_ENTER)
        self.browseButton = wx.Button(self, -1, "Browse", size = (-1, -1))

        self.protList = wx.grid.Grid(self)
        
        self.protGraph = ProteinGraphPanel(self, size = (-1, 50))
        
        self.sequenceDisplay = HighlighterGrid(self) 
        self.sequenceDisplay.EnableEditing(False)
        self.sequenceDisplay.EnableGridLines(False)
        self.sequenceDisplay.CreateGrid(0, 0)
        self.sequenceDisplay.SetDefaultCellFont(timesNewPeptide)
        self.sequenceDisplay.SetRowLabelSize(0)
        self.sequenceDisplay.SetColLabelSize(0)
        self.sequenceDisplay.SetMinSize((10, 10))
        self.sequenceDisplay.DisableDragGridSize()

        self.sheetSelectLabel = wx.StaticText(self, -1, "Sheet Name")
        self.sheetSelect = wx.TextCtrl(self, -1, "Data", style = wx.TE_PROCESS_ENTER)

        self.searchLabel = wx.StaticText(self, -1, "Search")
        self.searchBar = wx.TextCtrl(self, -1, style = wx.TE_PROCESS_ENTER)

        scoreCutLabel = wx.StaticText(self, -1, "Score cutoff")
        self.scoreCutCtrl = wx.TextCtrl(self, -1, '0', size = (35, -1),
                                        style = wx.TE_CENTRE | wx.TE_PROCESS_ENTER)
        
        accessionCtrlLabel = wx.StaticText(self, -1, "Accession ")
        self.prevAccession = wx.Button(self, -1, "<", size = (20, -1))
        self.accessionCounter = wx.TextCtrl(self, -1, '0', size = (35, -1),
                                            style = wx.TE_READONLY | wx.TE_CENTRE)
        self.nextAccession = wx.Button(self, -1, ">", size = (20, -1))
        

        
        highlightResidueLabel = wx.StaticText(self, -1, "Highlight Residues  ")
        self.highlightCtrl = wx.TextCtrl(self, -1, '', size = (150, -1),
                                         style = wx.TE_PROCESS_ENTER)
        
        self.saveButton = wx.Button(self, -1, "Save Image")
        self.clipButton = wx.Button(self, -1, "Copy Image to Clipboard")
        
        self.coverageIndicator = wx.TextCtrl(self, -1, '', style = wx.TE_READONLY)
        
        gbs = wx.GridBagSizer(15, 7)

        gbs.Add(fastaLabel, (0,0), flag = wx.ALIGN_RIGHT)
        gbs.Add(self.fastaChooser, (0,1), (1, 3), flag = wx.EXPAND)
        gbs.Add(self.fastaButton, (0, 5), flag = wx.ALIGN_LEFT)
        
        gbs.Add(regexLabel, (0, 6), flag = wx.ALIGN_RIGHT)
        gbs.Add(self.regexEntry, (0, 7), (1, 2), flag = wx.EXPAND)
        gbs.Add(self.regexHelp, (1, 7), (1, 2), flag = wx.ALIGN_LEFT | wx.EXPAND)

        gbs.Add(fileLabel, (1,0), flag = wx.ALIGN_RIGHT)
        gbs.Add(self.fileChooser, (1, 1), (1, 3), flag = wx.EXPAND)
        gbs.Add(self.browseButton, (1, 5), flag = wx.ALIGN_LEFT)

        gbs.Add(self.protGraph, (2,3), (2,7), flag = wx.EXPAND)
        
        gbs.Add(self.sheetSelectLabel, (2, 0), flag = wx.ALIGN_RIGHT | wx.ALIGN_BOTTOM)
        gbs.Add(self.sheetSelect, (2, 1), flag = wx.ALIGN_LEFT | wx.ALIGN_BOTTOM)
        gbs.Add(self.searchLabel, (3, 0), flag = wx.ALIGN_RIGHT | wx.ALIGN_BOTTOM)
        gbs.Add(self.searchBar, (3, 1), (1, 2), flag = wx.EXPAND | wx.ALIGN_BOTTOM)
        gbs.Add(self.protList, (4,0), (5, 3), flag = wx.EXPAND)
        gbs.Add(self.sequenceDisplay, (4, 3), (5, 7), flag = wx.EXPAND)
        
        gbs.Add(scoreCutLabel, (9, 0), flag = wx.CENTER)
        gbs.Add(self.scoreCutCtrl, (9, 1), flag = wx.ALIGN_LEFT)
        
        accessionBox = wx.BoxSizer(wx.HORIZONTAL)
        accessionBox.Add(accessionCtrlLabel, flag = wx.CENTER)
        accessionBox.Add(self.prevAccession, flag = wx.ALIGN_RIGHT)
        accessionBox.Add(self.accessionCounter, flag = wx.CENTER)
        accessionBox.Add(self.nextAccession, flag = wx.ALIGN_LEFT)
        gbs.Add(accessionBox, (9, 2), flag = wx.ALIGN_RIGHT)
        
        residueBox = wx.BoxSizer(wx.HORIZONTAL)
        residueBox.Add(highlightResidueLabel, flag = wx.CENTER)
        residueBox.Add(self.highlightCtrl, flag = wx.ALIGN_CENTER)
        gbs.Add(residueBox, (9,3), flag = wx.ALIGN_RIGHT)
        
        gbs.Add(self.saveButton, (9,5))
        gbs.Add(self.clipButton, (9,6))
        
        gbs.Add(self.coverageIndicator, (9, 8))

        gbs.AddGrowableCol(2)
        gbs.AddGrowableCol(3)
        gbs.AddGrowableCol(8)
        #gbs.AddGrowableCol(4)
        gbs.AddGrowableRow(5)

        self.fastaFilename = None
        self.filenames = ['']
        self.sequence = None
        self.psms = None
        
        self.protList.CreateGrid(100, 2)
        self.protList.SetRowLabelSize(1)
        self.protList.SetColLabelValue(0, "Accession")
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
        self.Bind(wx.EVT_BUTTON, self.regularHelp, self.regexHelp)
        self.Bind(wx.EVT_SIZE, self.resizeHandler)
        self.Bind(wx.EVT_TEXT_ENTER, self.scoreFilter, self.scoreCutCtrl)
        self.Bind(wx.EVT_BUTTON, self.prevAccessionPressed, self.prevAccession)
        self.Bind(wx.EVT_BUTTON, self.nextAccessionPressed, self.nextAccession)
        self.Bind(wx.EVT_TEXT, self.highlightPepStr, self.highlightCtrl)
        self.Bind(wx.EVT_TEXT_ENTER, self.searchFilter, self.searchBar)
        self.Bind(wx.EVT_BUTTON, self.saveImage, self.saveButton)
        self.Bind(wx.EVT_BUTTON, self.clipboardImage, self.clipButton)
        self.Bind(wx.EVT_TEXT_ENTER, self.openFile, self.sheetSelect)
        self.sequenceDisplay.GetGridWindow().Bind(wx.EVT_MOTION, self.peptidePopup)
        
        #self.sequenceDisplay.SetFont(timesNewPeptide)
        
        deviceContext = wx.ScreenDC()
        deviceContext.SetFont(timesNewPeptide)
        self.textBlockWidth, _ = deviceContext.GetTextExtent("PEPTIDESTR   ")
        
        self.seqBlocksPerRow = None
        self.resizeHandler(None)
        
        self.subAccession = 0
        self.scoreCutoff = 0
        
        self.highlightSeqs = {}
        
        self.searchTerm = None
        self.oldRow = None
        
        #self.chartProtein()


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
        seqBlocksPerRow = floor((seqBoxWidth / float(self.textBlockWidth)))
        
        if self.seqBlocksPerRow != seqBlocksPerRow:
            if self.seqBlocksPerRow:
                self.sequenceDisplay.DeleteCols(numCols = self.seqBlocksPerRow)
            self.sequenceDisplay.InsertCols(numCols = seqBlocksPerRow)
            for i in range(0, int(seqBlocksPerRow)):
                self.sequenceDisplay.SetColSize(i, self.textBlockWidth)

                
            self.seqBlocksPerRow = seqBlocksPerRow
        
        
        if self.sequence:
            self.displayProtein(None)
        
        
    def browseForFasta(self, event):
        filedialog = wx.FileDialog(parent = self, message = "Choose Files",
                                   style = wx.FD_OPEN | wx.FD_MULTIPLE)
        filedialog.ShowModal()
        newfiles = filedialog.GetPaths()

        #self.fastaChooser.Clear()
        #self.fastaChooser.AppendText(newfile)
        self.fastaChooser.SetSelection(0)
        self.fastaChooser.SetString(0, '; '.join(newfiles))
        
        if newfiles:
            addToFastaRecords(newfiles)


    def browseForFile(self, event):
        filedialog = wx.FileDialog(parent = self, message = "Choose Files",
                                   style = wx.FD_OPEN | wx.FD_MULTIPLE)
        filedialog.ShowModal()
        newfiles = filedialog.GetPaths()

        self.fileChooser.Clear()
        self.fileChooser.AppendText('; '.join(newfiles))
        
        self.openFile(None)
        
        
        
        
    def regularHelp(self, event):
        regex = self.regexEntry.GetValue()
        fastaFile = self.fastaChooser.GetValue().split(';')[0].strip()
        fastaSample = ''
        if fastaFile and os.path.exists(fastaFile):
            fasta = open(fastaFile, 'r')
            i = 0
            for line in fasta:
                if line[0] == '>':
                    fastaSample = line[1:].strip() # '>' is removed as it is in the FASTA parser.
                    break
                i += 1
                if i > 100: break
        
        helper = RegexHelper(self, regex, fastaSample)
        if helper.ShowModal() == wx.ID_OK:
            self.regexEntry.SetValue(helper.getRegex())
        
        
        
            

    def openFile(self, event):
        filenames = self.fileChooser.GetValue()
        filenames = [x.strip() for x in filenames.split(';')]

        self.filenames = filenames
        self.sheetname = self.sheetSelect.GetValue()
        if not self.sheetname: self.sheetname = 'Data'

        reportData = []
        for resultFile in filenames:
            try:
                report = reader(resultFile, sheet_name = self.sheetname, autotypecast = False)
            except IOError:
                print "%s has no sheet %s" % (resultFile, self.sheetname)
                continue
            reportData += list(report)

        self.psmsByAccession = defaultdict(list)
        protList = set()
        for psm in reportData:
            if float(psm['Peptide Score']) < self.scoreCutoff: continue
            if (self.searchTerm and 
                self.searchTerm.lower() not in psm['Accession Number'].lower() and
                self.searchTerm.lower() not in psm['Protein Description'].lower()):
                continue
            
            protList.add((psm['Accession Number'], psm['Protein Description']))
            for accession in psm['Accession Number'].split(';'):
                self.psmsByAccession[accession].append(psm)

        self.updateProtList(list(protList))
        

    def fastaLookup(self, protein):
        if not (self.fastaFilename and self.fastaFilename == self.fastaChooser.GetValue()
                and self.labelRegexStr == self.regexEntry.GetValue()):
            fastaFilename = self.fastaChooser.GetValue()
            if not fastaFilename:
                raise DataError, "No FASTA file selected."
                        
            #labelConverter = lambda x: x.split(' ')[0][1:]
            self.labelRegexStr = self.regexEntry.GetValue()
            labelRegex = re.compile(self.labelRegexStr)
            def labelConverter(label):
                # This currently doesn't deal with databases that have combined
                # multi-accession headers.
                #sublabels = label.split('\x01') # Some databases, 
                result = re.search(labelRegex, label)
                if not result:
                    raise DataError, "Can't process FASTA file.  %s gives no match for: %s" % (self.labelRegexStr, label)
                else:
                    return result.group()
            
            #labelConverter = lambda x: re.match(labelRegex, x)
            self.fastaFilename = fastaFilename
            try:
                fastafiles = self.fastaFilename.split('; ')
                self.fasta = {}
                for fastafile in fastafiles:
                    self.fasta.update(parse_to_dict(fastafile, labelConverter))
            except DataError as err:
                wx.MessageBox(str(err), "Could not parse FASTA file.")
                self.fastaFilename = None
                self.labelRegexStr = None
                raise err
        try:
            return self.fasta[protein]
        except KeyError:
            print (self.labelRegexStr, protein)
            raise DataError, "Protein sequence not available in FASTA database."

    def scoreFilter(self, event):
        self.scoreCutoff = float(self.scoreCutCtrl.GetValue())
        self.openFile(event)
        self.displayAccession()
        
    def searchFilter(self, event):
        self.searchTerm = self.searchBar.GetValue().strip()
        self.openFile(event)
        
    def updateProtList(self, proteinData):
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
            
            protein = (self.protList.GetCellValue(event.GetRow(), 0),
                       self.protList.GetCellValue(event.GetRow(), 1))
            
            if not protein[0]:
                if event:
                    event.Skip()            
                return

            if event:
                self.selectRow = event.GetRow()
                wx.CallAfter(self.markReadRow)

            self.accessions = protein[0].split(';')
            accession = self.accessions[0]
            
            self.subAccession = 0
            self.accessionCounter.SetValue(str(0))
            self.accessionCount = len(self.accessions)            
            
            accession = protein[0]
            if ';' in accession:
                accession = accession.split(';')[0]            
                
                # accession is unused?
                
            self.displayAccession()
        #except Exception as err:
            #errBox = wx.MessageBox(str(err), "An Error Occurred.")
            #import traceback
            #print traceback.format_exc()       
        finally:
            self.Enable(True)      
        
        if event:
            event.Skip()
            
    def markReadRow(self):
        self.protList.SelectRow(self.selectRow)

            
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
            self.coverageToPeptide = defaultdict(list)
            self.modifications = defaultdict(list)
            for psm in self.psms:
                pepSeq = psm['Peptide Sequence']
                index = self.sequence.index(pepSeq)
                extent = len(pepSeq)
                
                if index not in self.peptideCoverage:
                    self.peptideCoverage[index] = extent
                else:
                    self.peptideCoverage[index] = max(self.peptideCoverage[index], extent)
                    
                self.coverageToPeptide[(index, index + extent)].append(psm)
                
                if psm['Variable Modifications']:
                    mods = psm['Variable Modifications'].split('; ')
                else:
                    mods = []
                for site, kind in [x.split(': ') for x in mods if x]:
                    try:
                        site = int(site[1:])
                    except ValueError:
                        # Currently only phospho mods are being represented in
                        # the coverage view, and those don't happen on terminals.
                        # So non-numerical sites can be ignored.
                        continue
                    kind = kind.strip()
                    self.modifications[kind].append(index + site - 1) 
                    
            self.highlightPepStr(None)
            self.displayProtein(None)                
        except DataError as err:
            errBox = wx.MessageBox(str(err), "An Error Occurred.")
            import traceback
            print traceback.format_exc()       
        finally:
            self.Enable(True)
            
    
    def highlightPepStr(self, event):
        pepStr = self.highlightCtrl.GetValue()
        if not (self.sequence and pepStr):
            if self.highlightSeqs:
                self.highlightSeqs = {}
                self.displayProtein(None)
            return
        
        pepStr = [x.strip().upper() for x in pepStr.split(',') if x.strip()]
        
        occurences = []
        for subStr in pepStr:
            occurences += [(x.start(), x.end()) for x in re.finditer(subStr, self.sequence)]
        
        if dict(occurences) != self.highlightSeqs:
            self.highlightSeqs = dict(occurences)
            self.displayProtein(None)
            

    def displayProtein(self, event):
        rows = self.sequenceDisplay.GetNumberRows()
        if rows:
            self.sequenceDisplay.DeleteRows(numRows = rows)
        self.sequenceDisplay.InsertRows(numRows = ceil(len(self.sequence) / ((self.seqBlocksPerRow - 1) * 10)) + 1)
            
        gotPeptides = []
        for begin, end in self.peptideCoverage.items():
            gotPeptides += range(begin, begin + end)
        
        gotPepStrs = []
        for begin, end in self.highlightSeqs.items():
            gotPepStrs += range(begin, end)
            
            
        for col in range(1, int(self.seqBlocksPerRow)):
            self.sequenceDisplay.SetCellWithStyle(0, col, "%s" % (((col-1)*10)+1), [('white', 'blue')] * 10)
            self.sequenceDisplay.SetCellAlignment(0, col, wx.ALIGN_RIGHT, wx.ALIGN_CENTRE)
            
        row = 1
        prev = 0
        i = 10
        while i <= len(self.sequence):
            self.sequenceDisplay.SetCellWithStyle(row, 0, "%s" % str(i-9), [('white', 'blue')] * 10)
            self.sequenceDisplay.SetCellAlignment(row, 0, wx.ALIGN_RIGHT, wx.ALIGN_CENTRE)
            
            for col in range(1, int(self.seqBlocksPerRow)):
                block = self.sequence[prev:i]
                styles = [normalStyle] * 10

                relevantFoundAAs = [x for x in gotPeptides if prev <= x < i]
                relevantHighlights = [x for x in gotPepStrs if prev <= x < i]

                for index in range(prev, i):
                    if index in relevantFoundAAs and index in relevantHighlights:
                        styles[index - prev] = foundHighlightStyle
                    elif index in relevantFoundAAs:
                        styles[index - prev] = foundStyle
                    elif index in relevantHighlights:
                        styles[index - prev] = highlightStyle
                    
                    if index in self.modifications['Phospho']:
                        styles[index - prev] = foundModStyle
                
                self.sequenceDisplay.SetCellWithStyle(row, col, block, styles)
                prev = i
                i += 10
            row += 1
            
        self.chartProtein()
        
        coverageFrac = float(len(set(gotPeptides))) / len(self.sequence)
        self.coverageIndicator.SetValue('%.2f%% Coverage' % (coverageFrac*100))
        
        
    def chartProtein(self):    
        self.protGraph.protein = self.sequence, self.peptideCoverage
        self.protGraph.Refresh()
    

    
    def saveImage(self, event, outputName = None):
        if not self.sequence: return
        
        if not outputName:
            filedialog = wx.FileDialog(parent = self, message = 'Save to Image',
                                       style = wx.FD_SAVE, wildcard = "*.png")
            filedialog.ShowModal()
            outputName = filedialog.GetPath()
            
            if not outputName:
                print "Invalid output file name %s" % outputName
                return
        
        currentAccession = self.accessions[self.subAccession]
        
        image = self.renderCombinedImage()
        image.SaveFile(outputName, wx.BITMAP_TYPE_PNG)
        
        print outputName + " saved!"
        del image
        
    def clipboardImage(self, event):
        if not self.sequence: return
        
        image = self.renderCombinedImage()
        
        dataObj = wx.BitmapDataObject(image)

        wx.TheClipboard.Open()
        wx.TheClipboard.SetData(dataObj)
        wx.TheClipboard.Close()
            
    
    def renderCombinedImage(self):
        graphRect = self.protGraph.GetRect()
        seqRect = self.sequenceDisplay.GetRect()
        seqSize = self.sequenceDisplay.GetSize()
        
        
        
        effectiveSeqHeight = (self.sequenceDisplay.CellToRect(0,0).height *
                              self.sequenceDisplay.GetNumberRows())
        effectiveSeqWidth = (self.sequenceDisplay.CellToRect(0,0).width *
                             self.sequenceDisplay.GetNumberCols())
        
        bitmap = wx.EmptyBitmap(graphRect.width, (graphRect.height) + effectiveSeqHeight)
        
        image = wx.MemoryDC()
        image.SelectObject(bitmap)
        
        graphDC = wx.WindowDC(self.protGraph)
        seqDC = wx.WindowDC(self.sequenceDisplay)
        
        xos, yos = self.ClientToScreen((0,0)) # X-offset, Y-offset.

        image.Blit(0, 0, graphRect.width, graphRect.height, graphDC, 0, 0)
        self.sequenceDisplay.RenderToDC(image, (0, graphRect.height))


        # Fill in that extra black bit on the right edge not covered by any cells.
        image.SetBrush(wx.Brush(wx.Colour(255,255,255)))
        image.DrawRectangle(effectiveSeqWidth, graphRect.height,
                            graphRect.width - effectiveSeqWidth, effectiveSeqHeight)
        
        return bitmap
    
    
    
    def peptidePopup(self, event):
        if not self.sequence:
            event.Skip()
            return
        
        point = event.GetPositionTuple()
        x, y = self.sequenceDisplay.CalcUnscrolledPosition(event.GetX(), event.GetY())
        row, col = self.sequenceDisplay.XYToCell(x, y)
        if row < 0 or col < 0:
            event.Skip()
            return        
        
        row, col = row - 1, col - 1 # Compensating for 'label' row/column.
        
        minLoc = (row * (self.seqBlocksPerRow - 1) * 10) + (col * 10)
        maxLoc = minLoc + 10
        
        psms = []

        for coverage, psmList in self.coverageToPeptide.items():
            if minLoc >= coverage[1] or maxLoc <= coverage[0]: continue
            psms += psmList
        
        #if psms:
        popupText = []
        for psm in psms:
            text = "%s\nScore: %s\nCharge: %s\nVariable Mods: %s\n" % (psm['Peptide Sequence'],
                                                                       psm['Peptide Score'],
                                                                       psm['Charge'],
                                                                       psm['Variable Modifications'])
            popupText.append(text)
        
        popupText = '\n'.join(popupText)
        event.GetEventObject().SetToolTipString(popupText)

        event.Skip()
        
        
        



def annotateFileWithCoverageImages(resultfile, fastafile):
    from multiplierz.mzReport.mzSpreadsheetClassic import XLSheetWriter as classic_writer    
    import tempfile, os, shutil
    
    foo = wx.App(0)
    
    coverpanel = CoveragePanel(wx.Frame(None))
    coverpanel.fastaChooser.SetSelection(0)
    coverpanel.fastaChooser.SetString(0, fastafile)
    coverpanel.resizeSequence()
    coverpanel.fileChooser.AppendText(resultfile)
    coverpanel.openFile(None)
    
    psms = reader(resultfile)
    output = classic_writer(resultfile + '.coverage_annotated.xls',
                            columns = psms.columns + ['Coverage'])

    tempdir = tempfile.mkdtemp()
    tempimgs = []
    i = 0
    for psm in psms:
        accessions = psm['Accession Number'].split('; ')
        for accession in accessions:
            coverpanel.accessions = [accession]
            coverpanel.subAccession = 0
            coverpanel.displayAccession()
            coverpanel.chartProtein()
            
            #tempimg = tempfile.
            #coverpanel.saveImage(None, )
            #image = coverpanel.renderCombinedImage()
            # Convert image somehow?
            img = os.path.join(tempdir, str(i) + '.png')
            i += 1
            #coverpanel.saveImage(None, outputName = img)
            #coverpanel.sequenceDisplay.SetSize((2000, 500))
            seqHeight = (coverpanel.sequenceDisplay.CellToRect(0,0).height *
                         coverpanel.sequenceDisplay.GetNumberRows())
            seqWidth = (coverpanel.sequenceDisplay.CellToRect(0,0).width *
                        coverpanel.sequenceDisplay.GetNumberCols())          
            bitmap = wx.EmptyBitmap(seqWidth, seqHeight)
            imageDC = wx.MemoryDC()
            imageDC.SelectObject(bitmap)
            coverpanel.sequenceDisplay.RenderToDC(imageDC, (0, 0))
            bitmap.SaveFile(img, wx.BITMAP_TYPE_BMP)
            
            #image = wx.ImageFromBitmap(bitmap)
            #image = image.Rescale(seqWidth * 10, seqHeight * 1, quality = wx.IMAGE_QUALITY_HIGH)
            #image.SaveFile(img, wx.BITMAP_TYPE_PNG)
            
            
            
            psm['Coverage'] = '#'
            output.write(psm, metadata = [('Coverage', ('image', seqHeight, seqWidth), img)])
            break
    
    output.close()
    shutil.rmtree(tempdir)
