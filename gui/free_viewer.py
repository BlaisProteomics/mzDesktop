#from multiplierz.mzAPI import mzFile
from multiplierz.mzAPI.raw import mzFile # Non-RAW support could be troublesome.
from multiplierz.mzReport import reader, writer
from multiplierz.mzTools.featureUtilities import save_feature_database, FeatureInterface
from multiplierz.internalAlgorithms import collectByCriterion
from multiplierz.mzTools.featureDetector import Feature

#from label_viewer import InterfacePlot


import matplotlib
from matplotlib.figure import Figure
from matplotlib.cm import get_cmap

matplotlib.use('WXAgg')
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas

import os
import wx
from gui import BasicTab
import cPickle as pickle
import re
from numpy import average, isnan, median
from collections import defaultdict

XICSegmentLength = 2
spectrumMZWidth = 5

tolerance = 0.05




def renderPeptideTag(peptide):
    return "%s - %s - %s" % peptide

def applyAlignmentCurve(curve, xic, inverse = False):
    if not curve:
        return xic
    
    assert len(curve) == 4 and all([isinstance(x, float) for x in curve]), "Incorrect curve format!"
    
    a,b,c,d = curve
    if not inverse:
        return [(rt + (((rt**3)*a) + b*(rt**2) + c*rt + d), intensity)
                for rt, intensity in xic]
    else:
        return [(rt - (((rt**3)*a) + b*(rt**2) + c*rt + d), intensity)
                for rt, intensity in xic]        

def applyAlignmentToPoint(curve, pt, inverse = False):
    if not curve:
        return pt
    
    assert len(curve) == 4 and all([isinstance(x, float) for x in curve]), "Incorrect curve format!"
    
    a,b,c,d = curve
    if not inverse:
        return pt + (((pt**3)*a) + b*(pt**2) + c*pt + d)
    else:
        return pt - (((pt**3)*a) + b*(pt**2) + c*pt + d)



# Mapping is implicitly a map between this file and a
# "main" benchmark data file.
class mzFileMapped(mzFile):
    def __init__(self, datafile, curve = None):
        if not datafile.lower().endswith('raw'):
            raise NotImplementedError, "Label-free Quant Viewer only supports .RAW format for now."
        mzFile.__init__(self, datafile)
        
        self.ms1s = [x[2] for x in self.scan_info(0, 99999) if x[3] == 'MS1']
        
        self.curve = curve
    
    def setCurve(self, curve):
        self.curve = curve
    
    def map_scan(self, target, **kwargs):
        if isinstance(target, float):
            rt = applyAlignmentToPoint(self.curve, target)
            scan = self.scanForTime(rt)
            #ms1 = max([x for x in self.ms1s if x <= scan])
            ms1s = reversed(self.ms1s)
            ms1 = ms1s.next()
            while ms1 > scan:
                ms1 = ms1s.next()
        elif isinstance(target, int):
            if target in self.ms1s:
                ms1 = target
            else:
                #ms1 = max([x for x in self.ms1s if x <= scan])
                ms1s = reversed(self.ms1s)
                ms1 = ms1s.next()
                while ms1 > scan:
                    ms1 = ms1s.next()
            # If we're getting by scan number we *shouldn't* compensate, right?
            
        scan = self.scan(ms1, centroid = True)
        
        # Also going to perform injection-time correction
        injTime = self.scanInjectionTime(ms1)
        scan = [(x[0], x[1] / injTime) for x in scan]
        return scan
        
    
    def map_xic(self, start_time, stop_time, start_mz, stop_mz, **kwargs):
        start_mapped = applyAlignmentToPoint(self.curve, float(start_time))
        stop_mapped = applyAlignmentToPoint(self.curve, float(stop_time))
        xic = self.xic(start_mapped, stop_mapped, start_mz, stop_mz, **kwargs)
        
        xic_mapped = applyAlignmentCurve(self.curve, xic, inverse = True)
        
        if not (xic_mapped[1][0] >= start_time and xic_mapped[-2][0] <= stop_time):
            print "WARNING: Suspicious xic endpoints: %s vs %s and %s vs %s ." % (xic_mapped[1][0], start_time, xic_mapped[-2][0], stop_time)
        # mzFile.xic isn't very precise; using inner elements is a halfway decent buffer.
        
        return xic_mapped
    
    def map_timeForScan(self, scan):
        rt = self.timeForScan(scan)
        return applyAlignmentToPoint(self.curve, rt, inverse = True)
 
 
def derivePatchworkMZs(psmLookup, dataLookup, segments):
    peptides = []
    pepsByFile = []
    for resultfile, psms in psmLookup.values():
        pepsByFile.append(dict([((x['Peptide Sequence'], x['Variable Modifications'], x['Charge']),
                                 x['Experimental mz']) for x in psms]))
    peptides = [set(x.keys()) for x in pepsByFile]
    commonPeptides = reduce(lambda x, y: x & y, peptides)
    commonMZs = [float(pepsByFile[0][x]) for x in commonPeptides]
    
    
    patches = []
    for segmentStart in segments:
        segmentStop = segmentStart + XICSegmentLength
        segmentMid = segmentStart + (XICSegmentLength/2.0)
        
        #mzInts = []
        #for mz in commonMZs:
            #ints = []
            #for datafile, data in dataLookup.items():
                #scan = data.map_scan(segmentMid) # Automatically MS1'd!
                #ints.append(sum([x[1] for x in scan if abs(x[0] - mz) < tolerance]))
            #mzInts.append((mz, average(ints)))
        
        mzInts = defaultdict(list)
        for datafile, data in dataLookup.items():
            scan = data.map_scan(segmentMid) # Automatically MS1'd!
            for mz in commonMZs:
                intensity = sum([x[1] for x in scan if abs(x[0] - mz) < tolerance])
                mzInts[mz].append(intensity)
            #mzInts.append((mz, average(ints)))
            
        
        segmentMZ, _ = max(mzInts.items(), key = lambda x: sum(x[1]))
        
        patches.append((segmentStart, segmentStop, segmentMZ))
    
    return patches
                



def drawSegmentXIC(data, mzBySegment, curve):
    totalXIC = []
    for segment, mz in mzBySegment:
        segmentBegin = applyAlignmentToPoint(curve, segment)
        segmentEnd = applyAlignmentToPoint(curve, segment + XICSegmentLength)
        
        segmentXIC = data.xic(segment, segment + XICSegmentLength, mz - 0.01, mz + 0.01)
        if curve:
            segmentXIC = applyAlignmentCurve(curve, segmentXIC)
        totalXIC.append((segmentXIC, segmentBegin, segmentEnd))
    
    return totalXIC
    
    


class AlignmentPlot(wx.Dialog):
    def __init__(self, parent, ident = -1, talkback = None):
        super(AlignmentPlot, self).__init__(parent,
                                            title = "Modify RT Alignment",
                                            style = wx.RESIZE_BORDER | wx.MAXIMIZE_BOX | wx.MINIMIZE_BOX | wx.DEFAULT_DIALOG_STYLE)
        
        #panel = wx.Panel(self, -1, style = wx.EXPAND)
        #self.ShowFullScreen(True)
        
        self.fig = Figure()
        
        self.canvas = FigureCanvas(self, -1, self.fig)
    
        wxbackground = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE)
        wxbackground = [x / 255.0 for x in wxbackground]
        self.fig.set_facecolor(wxbackground)
        
        self.saveButton = wx.Button(self, -1, "Use This Alignment")
        self.abortButton = wx.Button(self, -1, "Use Default Alignment")
        self.Bind(wx.EVT_BUTTON, self.saveExit, self.saveButton)
        self.Bind(wx.EVT_BUTTON, self.abortExit, self.abortButton)
        
        self.controlBox = wx.GridBagSizer(1, 1)
        self.controlBox.Add(self.saveButton, (0, 1), flag = wx.ALIGN_RIGHT)
        self.controlBox.Add(self.abortButton, (0, 2), flag = wx.ALIGN_LEFT)
        self.controlBox.AddGrowableCol(0)
        
        self.sizer = wx.GridBagSizer()
        self.sizer.Add(self.canvas, (0, 0), flag = wx.EXPAND)
        self.sizer.Add(self.controlBox, (1, 0))
        self.sizer.AddGrowableRow(0)
        self.sizer.AddGrowableCol(0)
        self.SetSizer(self.sizer)
        self.Fit() 
        
        self.newAlignPt = None
        self.alignPtPairs = []
        
        self.clickBack = self.canvas.mpl_connect('button_press_event', self.mouseClick)
        self.releaseBack = self.canvas.mpl_connect('button_release_event', self.mouseRelease)        
        
        self.clickpt = None
        self.clickpixel = None
        
        self.talkback = talkback
        
    
    def mouseClick(self, event):
        if event.button == 1:
            print "Leftclick!"
            self.clickpt = event.xdata, event.ydata
            self.clickpixel = event.x, event.y
            print self.clickpt, self.clickpixel
            
    def mouseRelease(self, event):
        ax = event.inaxes
        if not ax:
            return
        ax = self.fig.get_axes().index(ax)
        
        if event.button == 1:
            if self.newAlignPt and ax != self.newAlignPt[0]:
                newPt = ax, event.xdata, event.ydata
                self.alignPtPairs.append((self.newAlignPt, newPt))
                self.newAlignPt = None
            else:
                self.newAlignPt = ax, event.xdata, event.ydata
        
        
        elif event.button == 3:
            self.newAlignPt = None
            
        print self.newAlignPt, self.alignPtPairs
    

    
    def patchworkPlot(self, resultLookup, dataLookup, referenceFile):
        
        
        startPoint = min([x.time_range()[0] for x in dataLookup.values()])
        stopPoint = max([x.time_range()[1] for x in dataLookup.values()])
        
        segments = range(int(round(startPoint)), int(round(stopPoint)), XICSegmentLength)
        self.talkback("Deriving relevant MZs for plot...")
        mzs = derivePatchworkMZs(resultLookup, dataLookup, segments)
        
        patchworkXICs = []
        for datafile, data in dataLookup.items():
            self.talkback("Plotting alignment XIC for %s" % datafile)
            patches = []
            for start, stop, mz in mzs:
                xic = data.map_xic(start, stop, mz - tolerance, mz + tolerance)
                
                if data.curve:
                    nativeXic = data.xic(start, stop, mz - tolerance, mz + tolerance)
                    referenceXic = dataLookup[referenceFile].xic(start, stop, mz - tolerance, mz + tolerance)
                else:
                    nativeXic = None
                    referenceXic = None
                
                patches.append((start, stop, xic, nativeXic, referenceXic))
            
            patchworkXICs.append((datafile, patches))
        
        self.talkback("Drawing plot...")
        self.plots(patchworkXICs)
        self.talkback("Ready.")
                
        
    def plots(self, xics):    
        #colors = rainbow([1/float(x) for x in range(1, len(pts) + 1)])
        set1 = get_cmap('Set1')    
        
        for index, (datafile, xicPatches) in enumerate(xics, start = 1):
            ax = self.fig.add_subplot(len(xics), 1, index)
            ax.set_yscale('log')
            pts = []
            for patch, (start, stop, xic, nativeXic, referenceXic) in enumerate(xicPatches):
                pts += [start, stop]
                
                color = set1(float(patch)/ len(xicPatches))
                xic = [x for x in xic if x[1] > 1]
                if xic:
                    ax.plot(zip(*xic)[0], zip(*xic)[1], color = color)
                nativeXic = [x for x in nativeXic if x[1] > 1] if nativeXic else None
                if nativeXic:
                    ax.plot(zip(*nativeXic)[0], zip(*nativeXic)[1], 
                            color = 'b', alpha = 0.2)
                referenceXic = [x for x in referenceXic if x[1] > 1] if referenceXic else None
                if referenceXic:
                    ax.plot(zip(*referenceXic)[0], zip(*referenceXic)[1],
                            color = 'k', alpha = 0.2)
                
                
                
                bot, top = ax.get_ylim()
                ax.vlines(pts, [bot] * len(pts), [top] * len(pts), color = '0.75')
                #ax.set_ylim(bot, top)
            ax.set_xlim(min(pts), max(pts))
        
        # All xics should have the same set of starts and stops.
        
        
        self.fig.tight_layout(pad = 0, rect = [0.005, 0.1, 1, 0.95])
        self.canvas.draw()

            
    # TODO: wtf even?
    def saveExit(self, event):
        # Somethingsomething alignment settings saved here.
        self.Destroy()
        
    def abortExit(self, event):
        # Somethingsomethingsomething.
        self.Destroy()        
        
    def getAlignment(self):
        return None # Somethingsomething manually-set-alignment somehow.

        
        
        
        

class LabelFreePanel(BasicTab):
    def __init__(self, parent, id = -1):
        wx.Panel.__init__(self, parent, -1)
        
        self.set_status("Initializing...", 0)
        self.set_status("", 1)
        
        self.entrySelector = wx.TreeCtrl(self, -1, size = (350, -1),
                                         style = wx.TR_LINES_AT_ROOT | wx.TR_HIDE_ROOT | wx.TR_TWIST_BUTTONS | wx.TR_HAS_BUTTONS)
        self.Bind(wx.EVT_TREE_SEL_CHANGED, self.displayPeptide, self.entrySelector)
        self.xicPlot = InterfacePlot(self, -1)
        self.spectraPlot = InterfacePlot(self, -1)
        
        self.Bind(EVT_InterfaceClick, self.xicClick, self.xicPlot)
        
        self.fileDisplay = wx.ListCtrl(self, -1, size = (-1, 100), style = wx.LC_REPORT)
        #self.fileDisplay.AppendColumn("MS Data")
        #self.fileDisplay.AppendColumn("PSM File")
        self.fileDisplay.InsertColumn(0, "#")
        self.fileDisplay.InsertColumn(1, "MS Data")
        self.fileDisplay.InsertColumn(2, "PSM File")
        self.fileDisplay.InsertColumn(3, "Feature File")
        self.fileBrowse = wx.Button(self, -1, "Add Data/PSM/Feature Fileset")
        self.fileClear = wx.Button(self, -1, "Clear Selections")
        self.Bind(wx.EVT_BUTTON, self.addFiles, self.fileBrowse)
        self.Bind(wx.EVT_BUTTON, self.clearFiles, self.fileClear)
        
        self.alignButton = wx.Button(self, -1, "Manual Alignment Tool")
        self.Bind(wx.EVT_BUTTON, self.launchAlignment, self.alignButton)
        
        self.initializeButton = wx.Button(self, -1, "Load Without Alignment")
        self.Bind(wx.EVT_BUTTON, self.loadFromFiles, self.initializeButton)
        
        self.loadCurveButton = wx.Button(self, -1, "Load Curve From File")
        self.Bind(wx.EVT_BUTTON, self.loadCurves, self.loadCurveButton)
        
        self.alignmentDisplay = wx.TextCtrl(self, -1, style = wx.TE_READONLY)
        
        
        self.searchCtrl = wx.TextCtrl(self, -1)
        self.searchType = wx.ComboBox(self, -1, choices = ['Accession', 'Peptide'])
        self.searchButton = wx.Button(self, -1, "Filter", size = (50, -1)) 
        
        self.Bind(wx.EVT_BUTTON, self.displayProteinList, self.searchButton)
        
        #self.scanLArrow = wx.Button(self, -1, "<", size = (20, -1))
        #self.currentScan = wx.TextCtrl(self, -1, size = (50, -1), style = wx.TE_CENTRE | wx.TE_PROCESS_ENTER)
        #self.scanRArrow = wx.Button(self, -1, ">", size = (20, -1))
        #self.Bind(wx.EVT_BUTTON, self.scanLeft, self.scanLArrow)
        #self.Bind(wx.EVT_TEXT_ENTER, self.reselectScan, self.currentScan)
        #self.Bind(wx.EVT_BUTTON, self.scanRight, self.scanRArrow)  
        
        
        self.gb = wx.GridBagSizer(1, 1)
        self.controlBox = wx.GridBagSizer(10, 10)
        self.searchBox = wx.GridBagSizer(1, 1)
        
        self.controlBox.Add(self.fileDisplay, (0, 0), (2, 7), flag = wx.EXPAND)
        self.controlBox.Add(self.fileBrowse, (2, 0), flag = wx.ALIGN_RIGHT | wx.EXPAND)
        self.controlBox.Add(self.fileClear, (2, 1), flag = wx.ALIGN_LEFT | wx.EXPAND)
        self.controlBox.Add(self.alignButton, (2, 3), flag = wx.ALIGN_RIGHT)
        self.controlBox.Add(self.initializeButton, (2, 4), flag = wx.ALIGN_LEFT)
        self.controlBox.Add(self.loadCurveButton, (2, 5), flag = wx.ALIGN_LEFT)
        self.controlBox.Add(self.alignmentDisplay, (2, 6), flag = wx.EXPAND)
        self.controlBox.AddGrowableCol(2)
        self.controlBox.AddGrowableCol(6)
        self.gb.Add(self.controlBox, (0,0), (1, 10), flag = wx.EXPAND)
        
        self.searchBox.Add(self.searchCtrl, (0, 0), flag = wx.EXPAND)
        self.searchBox.Add(self.searchType, (0, 1))
        self.searchBox.Add(self.searchButton, (0, 2), flag = wx.ALIGN_LEFT)
        self.searchBox.AddGrowableCol(0)
        self.gb.Add(self.searchBox, (2, 0), (1, 3), flag = wx.EXPAND)        
        
        self.gb.Add(self.entrySelector, (3, 0), (10, 3), flag = wx.EXPAND)
        self.gb.Add(self.xicPlot, (2, 3), (5, 7), flag = wx.EXPAND)
        self.gb.Add(self.spectraPlot, (7, 3), (5, 7), flag = wx.EXPAND)
        
        self.gb.AddGrowableCol(5)
        self.gb.AddGrowableRow(3)
        self.gb.AddGrowableRow(8)        
        
        overBox = wx.BoxSizer()
        overBox.Add(self.gb, 1, wx.ALL|wx.EXPAND, 20)
        self.SetSizerAndFit(overBox)
        
        self.fileDisplay.SetColumnWidth(0, self.fileDisplay.Size[0]/2)
        self.fileDisplay.SetColumnWidth(1, self.fileDisplay.Size[0]/2)        
        
        self.set_status("...", 0)
        
        self.wxMode = False
        
        self.files = {}
        self.dataPtrs = {}
        self.psms = {}
        self.features = {}
        self.ms1s = None
        
        self.proteins = None
        
        self.curves = {}
        
        
        
    def addFiles(self, event):
        filedialog = wx.FileDialog(parent = self, message = "Choose MS Data File",
                                   style = wx.FD_OPEN,
                                   wildcard = 'RAW|*.raw|All|*')
        filedialog.ShowModal()
        datafile = filedialog.GetPath()  
        
        filedialog = wx.FileDialog(parent = self, message = "Choose Search Result File",
                                   style = wx.FD_OPEN,
                                   wildcard = 'XLSX|*.xlsx|XLS|*.xls|CSV|*.csv|All|*')
        filedialog.ShowModal()
        resultfile = filedialog.GetPath()  
        
        filedialog = wx.FileDialog(parent = self, message = "Choose Feature File",
                                   style = wx.FD_OPEN,
                                   wildcard = 'Features|*.features|All|*')
        filedialog.ShowModal()
        featurefile = filedialog.GetPath()          
        
        
        self.files[os.path.basename(datafile)] = datafile
        self.files[os.path.basename(resultfile)] = resultfile
        self.files[os.path.basename(featurefile)] = featurefile
        
        if datafile and resultfile:
            self.fileDisplay.Append([str(self.fileDisplay.GetItemCount()),
                                     os.path.basename(datafile),
                                     os.path.basename(resultfile),
                                     os.path.basename(featurefile)])
            self.fileDisplay.SetColumnWidth(0, 50)
            self.fileDisplay.SetColumnWidth(1, (self.fileDisplay.Size[0]/3) - 17)
            self.fileDisplay.SetColumnWidth(2, (self.fileDisplay.Size[0]/3) - 17)          
            self.fileDisplay.SetColumnWidth(3, (self.fileDisplay.Size[0]/3) - 17)
        else:
            print "Not all files specified."
        
        
    def clearFiles(self, event):
        selections = []
        sel = self.fileDisplay.GetFirstSelected()
        while sel >= 0:
            selections.append(sel)
            sel = self.fileDisplay.GetNextSelected(sel)
        
        for sel in sorted(selections, reverse = True):
            for col in [1, 2, 3]:
                del self.files[self.fileDisplay.GetItemText(sel, col)]
            self.fileDisplay.DeleteItem(sel)
          
          
    def loadCurves(self, event):
        curveDialog = wx.FileDialog(parent = self, message = "Choose Curve File",
                                    style = wx.FD_OPEN,
                                    wildcard = 'All|*')        
        curveDialog.ShowModal()
        curveFile = curveDialog.GetPath()
        
        if curveFile:
            curves = pickle.load(open(curveFile, 'r'))
            # As per the output of diffPointRetrieval.py, there should be
            # one particular file that is the 'origin' of all of these mappings.
            # All that's really required is that the origin has mappings to all
            # the others, but that's harder to assert so pithily.            
            assert len(set(zip(*curves)[0])) == 1
            
            for fromFile, toFile, curve in curves:
                self.curves[os.path.basename(toFile)] = curve
            self.referenceFile = os.path.basename(fromFile)
            self.curves[self.referenceFile] = None
        
            self.launchAlignment(None)
        else:
            print "No file chosen."
        
    
    def loadFromFiles(self, event):
        self.set_status("Opening data files...", 0)
        datafiles = [self.files[self.fileDisplay.GetItemText(x, 1)]
                     for x in range(0, self.fileDisplay.GetItemCount())]
        self.dataPtrs = {}
        for datafile in datafiles:
            basedata = os.path.basename(datafile)
            if self.curves:
                self.dataPtrs[basedata] = mzFileMapped(datafile,
                                                       self.curves[basedata])
            else:
                self.dataPtrs[basedata] = mzFileMapped(datafile)                
                
    
        self.set_status("Loading PSMs...", 0)
        resultfiles = [(self.files[self.fileDisplay.GetItemText(x, 1)], 
                        self.files[self.fileDisplay.GetItemText(x, 2)])
                       for x in range(0, self.fileDisplay.GetItemCount())]         
        self.psms = {}
        for datafile, resultfile in resultfiles:
            #if datafile not in self.psms or self.psms[datafile][0] != resultfile:
            psms = list(reader(resultfile))
            self.psms[os.path.basename(datafile)] = resultfile, psms 
                
        featurefiles = [(self.files[self.fileDisplay.GetItemText(x, 1)], 
                         self.files[self.fileDisplay.GetItemText(x, 3)])
                        for x in range(0, self.fileDisplay.GetItemCount())]
        self.features = {}
        for datafile, featurefile in featurefiles:
            #if datafile not in self.features or self.features[datafile[0]] != featurefile:
            featureDB = FeatureInterface(featurefile)
            self.features[os.path.basename(datafile)] = featureDB


        self.set_status("Loading MS1 info...", 0)
        self.ms1s = dict([(x, [s for s in data.scan_info(0, 9999999) if s[3] == 'MS1'])
                          for x, data in self.dataPtrs.items()])
        
        
        self.set_status("Collecting peptides...", 0)
        self.proteins = defaultdict(list)
        for datafile, (resultfile, psms) in self.psms.items():
            for psm in psms:
                psm['Datafile'] = datafile
            byProtein = collectByCriterion(psms, lambda x: x['Accession Number'])
            for acc, psms in byProtein.items():
                self.proteins[acc] += psms        
        
        for acc, psms in self.proteins.items():
            collected = collectByCriterion(psms,
                                           lambda x: renderPeptideTag((x['Peptide Sequence'],
                                                                       x['Variable Modifications'],
                                                                       x['Charge'])))        
            self.proteins[acc] = collected
        
    
        self.set_status("...", 0)
        if event:
            self.render(None)
            
            
    
    def launchAlignment(self, event):
        """
        Presently this initializes the whole display.
        """
    
        self.loadFromFiles(None)
    
        self.set_status("Launching alignment tool...", 0)

        #mzPts = derivePatchworkXICs(self.psms, self.dataPtrs)
        #patchedXICs = []
        #for datafile, data in self.dataPtrs.items():
            #patchedXICs.append((datafile, drawSegmentXIC(data, mzPts, self.curves)))
        
        self.set_status("Alignment Tool.", 0)
        
        talkback = lambda x: self.set_status(x, 1)
        
        aligner = AlignmentPlot(self, -1, talkback)
        #aligner.plots(patchedXICs, mzPts, self.curves)
        aligner.patchworkPlot(self.psms, self.dataPtrs, self.referenceFile)
        aligner.ShowModal()
        #self.alignment = aligner.getAlignment()
        
        self.set_status("...", 0)
        
        self.render(None)
        
        
    def scanLeft(self, event):
        pass
    def scanRight(self, event):
        pass
    def reselectScan(self, event):
        pass
    
    
    
    def render(self, event):
        self.displayProteinList(None)
        
    
    
    def displayProteinList(self, event):
        if not self.proteins:
            print "Protein data not loaded."
            return

        self.wxMode = True
        self.entrySelector.DeleteAllItems()
        self.root = self.entrySelector.AddRoot("Foo")
        self.wxMode = False
        
        self.set_status("Writing protein list...", 0)

        visibleProteins = []
        filterType = self.searchType.GetValue()
        filterStr = self.searchCtrl.GetValue()
        for protein, peptides in self.proteins.items():
            if filterType == 'Accession':
                if not filterStr in protein:
                    continue
            
            visiblePeptides = []
            if filterType == 'Peptide':
                for peptide, psms in peptides.items():
                    if filterStr in peptide:
                        visiblePeptides.append((peptide, psms))
            else:
                visiblePeptides = peptides.items()
            
            if visiblePeptides:
                visibleProteins.append((protein, sorted(visiblePeptides)))
                    
            

        for protein, peptides in sorted(visibleProteins):
            proteinTag = protein
            root = self.entrySelector.AppendItem(self.entrySelector.GetRootItem(),
                                                 proteinTag)
            
            
            for peptide, psms in peptides:
                subroot = self.entrySelector.AppendItem(root, peptide)
                
                for psm in psms:
                    psmTag = '%s---%s' % (psm['Spectrum Description'].split('.')[1],
                                        os.path.basename(psm['Datafile']))
                    self.entrySelector.AppendItem(subroot, psmTag)
                    
        self.entrySelector.CollapseAll()
        
        self.set_status("Ready.", 0)
        
        
    
    def displayPeptide(self, event):
        if self.wxMode:
            return
        self.set_status("Rendering peptide plots...", 0)
        
        root = self.entrySelector.GetRootItem()
        selection = self.entrySelector.GetSelection()
        descent = []
        while selection != root:
            descent.append(self.entrySelector.GetItemText(selection))
            selection = self.entrySelector.GetItemParent(selection)        
        
        if not descent:
            raise IOError
        
        #print descent
        accession = descent[-1]
        if len(descent) > 1:
            peptide = descent[-2]
        else:
            peptide = None
        if len(descent) > 2:
            scan = descent[-3]
        else:
            scan = None
            
        print accession, peptide, scan
        self.plot_accession = accession
        self.plot_peptide = peptide
        self.plot_scan = scan
        
    
        self.plotPeptideXIC()
        self.plotPeptideSpectrum()
        
        self.set_status("Ready.", 0)
    
    

    def plotPeptideXIC(self):
        assert self.proteins
        if not self.plot_peptide:
            #print "Should clear plot here."
            self.xicPlot.clear()
            return
        
        psms = self.proteins[self.plot_accession][self.plot_peptide]
        
        mz = average([float(x['Experimental mz']) for x in psms])
        
        psmsByFile = collectByCriterion(psms, lambda x: x['Datafile'])
        rts = []
        for datafile, dfpsms in psmsByFile.items():
            scans = [int(x['Spectrum Description'].split('.')[1]) for x in dfpsms]
            rts += [self.dataPtrs[datafile].map_timeForScan(x) for x in scans]
            
        frts = []
        rangesByFile = {}
        for datafile, dfpsms in psmsByFile.items():
            featureIndices = [int(x['Feature']) for x in dfpsms if x['Feature'] != '-']
            features = [self.features[datafile][x] for x in featureIndices]
            scanranges = [x.scanrange for x in features]
            rtranges = [[self.dataPtrs[datafile].timeForScan(x) for x in xs] for xs in scanranges]
            rtranges = [[applyAlignmentToPoint(self.curves[datafile], x, inverse = True) for x in xs]
                        for xs in rtranges]
            rangesByFile[datafile] = rtranges
            frts += list(sum(rangesByFile[datafile], []))
        
        
            
        bothRTs = rts + frts
        span = min(bothRTs), max(bothRTs)

        if self.plot_scan:
            scan, scandatafile = [x.strip() for x in self.plot_scan.split('---')]
            scanrt = self.dataPtrs[scandatafile].map_timeForScan(int(scan))
        else:
            scanrt = None        
        
        self.xicPlot.plotXICs(self.dataPtrs, span, mz, scanrt, rangesByFile)
        
 
    
    
    def plotPeptideSpectrum(self):
        if not self.plot_scan:
            return
        
        
        psms = self.proteins[self.plot_accession][self.plot_peptide]
        mz = average([float(x['Experimental mz']) for x in psms])        
        
        scan, originDatafile = [x.strip() for x in self.plot_scan.split('---')]
        rt = self.dataPtrs[originDatafile].map_timeForScan(int(scan))
        assert isinstance(rt, float)
        
            
        self.spectraPlot.plotSpectrum(self.dataPtrs.items(), rt, mz)
            
        
    
    def displayScan(self, rt):
        # Should be in terms of the "main" datafile.
        # Redraws both plots!
        
        self.xicPlot.drawXIC(rt)

        if self.plot_accession and self.plot_peptide:
            psms = self.proteins[self.plot_accession][self.plot_peptide]
            mz = average([float(x['Experimental mz']) for x in psms]) 
            self.spectraPlot.plotSpectrum(self.dataPtrs.items(), rt, mz)
        else:
            self.spectraPlot.clear()
        
        
        
    
    def xicClick(self, event):
        print "xicClick!"
        rt = event.matEvt.xdata

        self.displayScan(rt)
        
        
        
                
                
            

        

matplotlib.use('WXAgg')
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas

import wx.lib.newevent




InterfaceClickEvent, EVT_InterfaceClick = wx.lib.newevent.NewCommandEvent()

class InterfacePlot(wx.Panel):
    def __init__(self, parent, ident = -1):
        wx.Panel.__init__(self, parent, ident, size = (100, 100))
        # Why does "size = (100, 100)" make the size adapt correctly?
        # It is a mystery!

        self.fig = Figure()
        self.ax = self.fig.add_subplot(111)
        #self.ax.yaxis.set_visible(False)
        #self.ax.xaxis.set_visible(False)
        #self.ax.yaxis.get_major_formatter().set_powerlimits((-1, 3))
        #self.fig.tight_layout(h_pad = 1)
        self.fig.tight_layout(pad = 0, rect = [0.005, 0.1, 1, 0.95])


        self.canvas = FigureCanvas(self, -1, self.fig)

        wxbackground = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE)
        wxbackground = [x / 255.0 for x in wxbackground]
        self.fig.set_facecolor(wxbackground)
        #self.fig.set_facecolor((0.5, 0.5, 0.5))

        self.sizer = wx.BoxSizer()
        self.sizer.Add(self.canvas, -1, wx.EXPAND)
        self.SetSizer(self.sizer)
        self.Fit()

        self.clickBack = self.canvas.mpl_connect('button_press_event', self.mouseClick)
        self.releaseBack = self.canvas.mpl_connect('button_release_event', self.mouseRelease)

        self.canvas.draw()

        self.span = None
        self.top = None
        self.clickpt = (None, None)
        self.clickpixel = (None, None)
        
        self.basespan = None
        self.balance = None
        

    def mouseClick(self, event):
        if event.button == 1:
            print "Leftclick!"
            self.clickpt = event.xdata, event.ydata
            self.clickpixel = event.x, event.y
            print self.clickpt, self.clickpixel

        elif event.button == 3:
            print "Rightclick!"
            if self.span:
                self.ax.set_xlim(*self.span)
                self.ax.set_ylim(0, self.top)
                self.canvas.draw()

    def mouseRelease(self, event):
        if event.button == 1:
            print "Leftrelease!"
            if not (all(self.clickpt) and all(self.clickpixel)):
                print "No click data."
                return 

            newpixel = event.x, event.y
            if not all([x and x >= 0 for x in newpixel]):
                print "Released outside of bounds."
                return

            travel = (abs(newpixel[0] - self.clickpixel[0])**2 +
                      abs(newpixel[1] - self.clickpixel[1])**2)
            print "Travel: %s" % travel
            if travel > 200:
                print "Resize!"
                newpt = event.xdata, event.ydata
                top = max(newpt[1], self.clickpt[1])
                bot = min(newpt[1], self.clickpt[1])
                left = min(newpt[0], self.clickpt[0])
                right = max(newpt[0], self.clickpt[0])

                if not self.balance:
                    self.ax.set_ylim(0, top)
                else:
                    lim = max(top, -1*bot)
                    self.ax.set_ylim(lim*-1, lim)
                    
                self.ax.set_xlim(left, right)
                self.canvas.draw()
            else:
                clickEvent = InterfaceClickEvent(self.GetId(), matEvt = event)
                wx.PostEvent(self, clickEvent)         
        
        elif event.button == 3:
            print "Rightrelease!"
            
            if self.basespan:
                (bot, top), (left, right) = self.basespan
                self.ax.set_xlim(left, right)
                self.ax.set_ylim(bot, top)
                self.canvas.draw()



    def clear(self):
        #self.ax.clf()
        self.fig.clf(keep_observers=True)
        #self.fig = Figure()
        self.ax = self.fig.add_subplot(111)
        self.ax.yaxis.get_major_formatter().set_powerlimits((-1, 3))
        self.ax.xaxis.get_major_formatter().set_powerlimits((-5, 10))
        #self.fig.tight_layout(pad = 0.1, w_pad = 1)
        #self.ax = self.fig.add_axes([0.])
        
        self.basespan = None
        
    

    def plotXICs(self, dataLookup, span, mz, rt, features):
        self.xicParams = {'data':dataLookup,
                          'span':span,
                          'mz':mz,
                          'features':features}
        
        self.drawXIC(rt)

        
    def drawXIC(self, rt):
        self.clear()
        
        dataLookup, span, mz, features = (self.xicParams['data'],
                                          self.xicParams['span'],
                                          self.xicParams['mz'],
                                          self.xicParams['features'])
        
        span = list(span)
        if rt and rt - 1 < span[0]:
            span[0] = rt - 1
        elif rt and rt + 1 > span[1]:
            span[1] = rt + 1
        
        for datafile, data in dataLookup.items():            
            xic = data.map_xic(span[0] - 1,
                               span[1] + 1,
                               mz - tolerance,
                               mz + tolerance)
            
            self.ax.plot(zip(*xic)[0], zip(*xic)[1], label = datafile)
        bot, top = self.ax.get_ylim()
        left, right = self.ax.get_xlim()            
        
        if features:
            set1 = get_cmap('Set1')
            index = 1.0
            length = float(len(sum(features.values(), [])))
            for datafile, ranges in features.items():
                for start, stop in ranges:
                    color = set1(float(index)/length)
                    index += 1
                    self.ax.axvspan(start, stop, color = color, alpha = 0.9)
                    
        
        if rt:
            self.ax.vlines([rt], [0], [top], color = 'r', linestyle = '--')
        self.ax.set_ylim(0, top)
        self.ax.set_xlim(left, right)
            
        self.ax.set_label("%s - %s" % (span[0], span[1]))
            
        self.ax.legend()
            
        self.canvas.draw()
        # Prelimiary version of this function, so far.
        
        self.basespan = (bot, top), (left, right)
        self.balance = False        
        
    def plotSpectrum(self, dataSpectra, rt, mz):
        # Mirror plot of two spectra currently.  The case of > 2 input files will
        # be handled later, differently, somehow.
        
        self.clear()
        
        #for datafile, spectrum in dataSpectra:
            #self.vlines(zip(*spectrum)[0], [0] * len(spectrum), zip(*spectrum)[1])
        #self.canvas.draw()
        
        if len(dataSpectra) > 2:
            print "MS plot with >2 files not currently supported!"
            
        topFile, topData = dataSpectra[0]
        topScan = topData.map_scan(rt, centroid = True)
        topScan = [x for x in topScan if abs(x[0] - mz) < spectrumMZWidth]
        if topScan:
            self.ax.vlines(zip(*topScan)[0], [0] * len(topScan), zip(*topScan)[1])
        
        botFile, botData = dataSpectra[1]
        botScan = botData.map_scan(rt, centroid = True)
        botScan = [x for x in botScan if abs(x[0] - mz) < spectrumMZWidth]
        if botScan:
            self.ax.vlines(zip(*botScan)[0], [0] * len(botScan), 
                           [x * -1 for x in zip(*botScan)[1]])
        
        left, right = self.ax.get_xlim()
        bot, top = self.ax.get_ylim()
        lim = max([bot*-1, top])

        self.ax.text(right, lim, topFile, horizontalalignment = 'right', verticalalignment = 'top')
        self.ax.text(right, lim*-1, botFile,
                  horizontalalignment = 'right', verticalalignment = 'bottom')
        
        self.ax.vlines([mz], [lim*-1], [lim], linestyle = '--', color = 'r')
        self.ax.set_ylim(lim*-1, lim)
        
        left, right = self.ax.get_xlim()
        self.ax.plot([left, right], [0, 0], color = 'k')
        self.ax.set_xlim(left, right)
        
        self.ax.set_label('%s' % rt)
        
        self.canvas.draw()
        
        self.basespan = (lim*-1, lim), (left, right)
        self.balance = True
        
        
        
            