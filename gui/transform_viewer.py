import wx
import os
import wxmpl

import multiprocessing
import time

from multiplierz.mzTools.chargeTransform import findESIPeaks, getAllMW, plotSpectrum, EmptySpectrum, SpectralMiss, EmptyMass, mannAlgorithm, slideWritingNonsense
from multiplierz.mzTools.chargeTransform import obtainPeaksForMass
from utilities.mzTransform import deconvolutionSession
#from multiplierz.internalAlgorithms import iterativeFitBreak

from gui import BasicTab
from mzGUI import file_chooser
from numpy import average


maxChargeTip = ("The maximum potential charge of the target molecule that will be considered.")
mzTolTip = ("The width of an m/z region that will be read to find the peak at a given m/z "
            "point; the expected 'width' of a peak.")
snThresholdTip = ("The signal-to-noise multiple that will be required of a peak to warrant "
                  "a search for it in the spectrum; based on the intensity of the peak region "
                  "versus by the baseline intensity of the surrounding region.")
mzRangeTip = ("The m/z range that will be searched.")
maxSpecCountTip = ("Maximum chemical species that will be detected, per scan given.")





def findMassSequenceInMann(massSpectrum, mzSpectrum, cluePt):
    index, _ = min(enumerate(massSpectrum),
                           key = lambda (i, x): abs(cluePt[0] - x[0])**2 + abs(cluePt[1] - x[1])**2 )
    while True:
        if massSpectrum[index-1][1] > massSpectrum[index][1]:
            index -= 1
        elif massSpectrum[index+1][1] > massSpectrum[index][1]:
            index += 1
        else:
            break
    nearPoint = massSpectrum[index]
    chargePeaks = zip(*obtainPeaksForMass(mzSpectrum, nearPoint[0], 0.1))
    
    threshold = average([x[1] for x in mzSpectrum])*2
    
    return nearPoint, [x for x in chargePeaks if x[0][1] > threshold]
    



class TransformPanel(BasicTab):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)
        
        gbs = wx.GridBagSizer(15, 7)
        
        fileLabel = wx.StaticText(self, -1, "Data File", style = wx.TE_READONLY)
        self.fileChooser = wx.TextCtrl(self, -1, "")
        self.browseButton = wx.Button(self, -1, "Browse")
        gbs.Add(fileLabel, (0, 0), flag = wx.ALIGN_RIGHT)
        gbs.Add(self.fileChooser, (0, 1), (1, 5), flag = wx.EXPAND)
        gbs.Add(self.browseButton, (0, 6), flag = wx.ALIGN_RIGHT)
        self.Bind(wx.EVT_BUTTON, self.selectFile, id = self.browseButton.GetId())
        
        self.mannModeC = wx.CheckBox(self, -1, "Mann\nAlgorithm")
        self.mannModeC.SetValue(False)
        
        mzRangeL = wx.StaticText(self, -1, "M/Z\nRange", style = wx.ALIGN_RIGHT)
        self.mzRangeC = wx.TextCtrl(self, -1, "300-2000", style = wx.ALIGN_RIGHT)
        mzRangeL.SetToolTip(wx.ToolTip(mzRangeTip))
        
        massRangeL = wx.StaticText(self, -1, "Mass Range")
        self.massRangeC = wx.TextCtrl(self, -1, "10000-100000", style = wx.ALIGN_RIGHT)
        
        maxSpecL = wx.StaticText(self, -1, "Maximum\nSpecies", style = wx.ALIGN_RIGHT)
        self.maxSpecC = wx.TextCtrl(self, -1, "5", style = wx.ALIGN_RIGHT)
        maxSpecL.SetToolTip(wx.ToolTip(maxSpecCountTip))
        
        removalAreaL = wx.StaticText(self, -1, "Peak Removal\nWidth", style = wx.ALIGN_RIGHT)
        self.removalAreaC = wx.TextCtrl(self, -1, "2", style = wx.ALIGN_RIGHT)
        
        minimumPeaksL = wx.StaticText(self, -1, "Peaks Required", style = wx.ALIGN_RIGHT)
        self.minimumPeaksC = wx.TextCtrl(self, -1, "8", style = wx.ALIGN_RIGHT)
        
        peakIterL = wx.StaticText(self, -1, "Peak-Finding\nIterations", style = wx.ALIGN_RIGHT)
        self.peakIterC = wx.TextCtrl(self, -1, "2", style = wx.ALIGN_RIGHT)
        
        timeWindowL = wx.StaticText(self, -1, "RT Window", style = wx.ALIGN_RIGHT)
        self.timeWindowC = wx.TextCtrl(self, -1, "Auto", style = wx.ALIGN_RIGHT)
        self.Bind(wx.EVT_TEXT, self.changeTimeWindow, id = self.timeWindowC.GetId())
        
        recalSlopeL = wx.StaticText(self, -1, "Recalibration\nSlope", style = wx.ALIGN_RIGHT)
        self.recalSlopeC = wx.TextCtrl(self, -1, "0", style = wx.ALIGN_RIGHT)
        
        recalIntercL = wx.StaticText(self, -1, "Recalibration\nIntercept", style = wx.ALIGN_RIGHT)
        self.recalIntercC = wx.TextCtrl(self, -1, "0", style = wx.ALIGN_RIGHT)
        
        smoothWindowL = wx.StaticText(self, -1, "Smoothing Width", style = wx.ALIGN_RIGHT)
        self.smoothWindowC = wx.TextCtrl(self, -1, "0", style = wx.ALIGN_RIGHT)
        
        
        i = 0
        #for label in [maxChargeL, mzTolL, snThreshL, mzRangeL, maxSpecL]:
        for label in [mzRangeL, massRangeL, maxSpecL, removalAreaL, minimumPeaksL,
                      peakIterL, timeWindowL, recalSlopeL, recalIntercL, smoothWindowL]:
            gbs.Add(label, (i+1, 0), flag = wx.ALIGN_RIGHT)
            i += 1
        i = 0
        #for control in [self.maxChargeC, self.mzTolC, self.snThreshC,
                        #self.mzRangeC, self.maxSpecC]:
        for control in [self.mzRangeC, self.massRangeC, self.maxSpecC, self.removalAreaC, 
                        self.minimumPeaksC, self.peakIterC, self.timeWindowC,
                        self.recalSlopeC, self.recalIntercC, self.smoothWindowC]:
            gbs.Add(control, (i+1, 1))
            i += 1

        gbs.Add(self.mannModeC, (11, 0), (1, 1), flag = wx.ALIGN_RIGHT)
            
        self.goButton = wx.Button(self, -1, "Run")
        self.saveButton = wx.Button(self, -1, "Save Image")
        self.outButton = wx.Button(self, -1, "Export Settings \nto mzTransform")

        self.Bind(wx.EVT_BUTTON, self.deconvolute, id = self.goButton.GetId())
        self.Bind(wx.EVT_BUTTON, self.saveImage, id = self.saveButton.GetId())
        self.Bind(wx.EVT_BUTTON, self.toMZTransform, id = self.outButton.GetId())
        
        gbs.Add(self.goButton, (11, 1), (1, 1), flag = wx.ALIGN_CENTER)
        gbs.Add(self.saveButton, (12, 0), (1, 1), flag = wx.ALIGN_CENTER)
        gbs.Add(self.outButton, (12, 1), (1, 1), flag = wx.ALIGN_CENTER)
        
        self.graph = wxmpl.PlotPanel(self, -1)
        gbs.Add(self.graph, (1,2), (12, 5), flag = wx.EXPAND)
        
        gbs.AddGrowableCol(3)
        gbs.AddGrowableRow(10)
        
        overBox = wx.BoxSizer()
        overBox.Add(gbs, 1, wx.ALL|wx.EXPAND, 20)
        self.SetSizerAndFit(overBox)
        
        #self.graph.Bind(wxmpl.EVT_POINT, self.onMannClick, id = self.graph.GetId())      
        #wxmpl.EVT_POINT(self, self.graph.GetId(), self.onMannClick)
        
        self.knownSpectrum = None

        self.filename = None
        self.displayingType = None
        self.texts = []
        self.window = None
        
        self.usedLabelLetters = []

        self.canvasCallback = None
        
    def selectFile(self, event):
        #fileDialog = wx.FileDialog(self, "Choose Data File", message = "Choose Data File",
                                   #style = wx.FD_OPEN)
        #fileDialog.ShowModal()
        #filename = fileDialog.GetPath()
        #fileDialog.Destroy()
        filename = file_chooser()
        
        self.fileChooser.Clear()
        try:
            self.fileChooser.AppendText(filename)
        except TypeError:
            pass
        
        if filename != self.filename:
            self.knownSpectrum = None
        
        self.filename = filename
    
    #def deconvolute(self, event):
        #import cProfile
        #cProfile.runctx('self.deconvolute2(event)', globals(), locals(), 'deconStats')
    
    def changeTimeWindow(self, event):
        windowText = self.timeWindowC.GetValue()
        oldWindow = self.window
        
        if windowText and windowText != "Auto":
            try:
                startTime, endTime = [float(x) for x in windowText.split('-')]
            except ValueError:
                return
            self.window = startTime, endTime
        else:
            self.window = None
        
        if oldWindow != self.window:
            self.knownSpectrum = None
    
    def saveImage(self, event):
        if not self.filename:
            wx.MessageBox("No file selected.")
            return
        
        fig = self.graph.get_figure()
        fileDialog = wx.FileDialog(self, message = "Save Image As:",
                                   defaultFile = self.filename + ".svg",
                                   wildcard = 'SVG | *.svg | PowerPoint | *.ppt',
                                   style = wx.FD_SAVE)
        fileDialog.ShowModal()
        filepath = fileDialog.GetPath()
        
        if filepath.lower().endswith('ppt'):
            fig.savefig(filepath + "TEMP.png")
            slideWritingNonsense(filepath, filepath + "TEMP.png", self.filename)
            os.remove(filepath + "TEMP.png")
        else:
            fig.savefig(filepath)
        
    
    def deconvolute(self, event):
        wx.BeginBusyCursor(wx.HOURGLASS_CURSOR)
        
        self.filename = self.fileChooser.GetValue()

        print self.window
        try:
            assert self.fileChooser.GetValue(), "No file selected!"
            
            self.set_status("Working...", 0)
            self.set_status("", 1)
            
            if self.knownSpectrum:
                print "Known spectrum %s" % time.clock()
                spectrum = self.knownSpectrum[:]
            else:
                #spectrum = self.esiJob.get()
                print "Unknown spectrum %s" % time.clock()
                if self.filename.lower().endswith('.txt'):
                    spectrum = readPeakList(self.filename)
                else:
                    spectrum = findESIPeaks(self.filename, self.window)
                self.knownSpectrum = spectrum[:]
                print "Obtained spectrum %s" % time.clock()
            
            
            figure = self.graph.get_figure()
            figure.clear()
            
            try: slope = float(self.recalSlopeC.GetValue())
            except ValueError: slope = 0
            try: intercept = float(self.recalIntercC.GetValue())
            except ValueError: intercept = 0
            try: smoothWindow = int(self.smoothWindowC.GetValue())
            except ValueError: smoothWindow = 0
            
            if slope or intercept:
                recalSpectrum = []
                for mz, intensity in spectrum:
                    recalSpectrum.append((mz + (slope * mz) + intercept, intensity))
            else:
                recalSpectrum = spectrum
                    
            try:        
                mzRange = [float(mz) for mz in self.mzRangeC.GetValue().split("-")]
                assert len(mzRange) == 2
            except ValueError, AssertionError:
                raise Exception, "Invalid charge range; field must be in format '<low mass>-<high mass>."
            try:
                massRange = [float(mass) for mass in self.massRangeC.GetValue().split("-")]
                assert len(massRange) == 2
            except ValueError, AssertionError:
                raise Exception, "Invalid mass range; field must be in format '<low mass>-<high mass>'."
            

            
            if self.mannModeC.GetValue():
                print "Begin Mann mode. %s" % time.clock()
                self.midSpectrum = writeMannDeconvolution(recalSpectrum, figure, massRange)
                self.displayingType = "Mann"
                self.canvasCallback = figure.canvas.mpl_connect('button_press_event', self.onMannClick)
                self.usedLabelLetters = []
                
                self.set_status("Left-double-click to place mass labels, right-double-click to remove.  Drag to zoom, right-click to unzoom.", 1)
            else:
                print "Begin standard mode. %s" % time.clock()
                self.midSpectrum = chargeDeconvolution(recalSpectrum,
                                                       mzRange,
                                                       massRange,
                                                       int(self.maxSpecC.GetValue()),
                                                       float(self.removalAreaC.GetValue()),
                                                       int(self.minimumPeaksC.GetValue()),
                                                       int(self.peakIterC.GetValue()),
                                                       10,
                                                       smoothWindow,
                                                       figure
                                                       )
                self.displayingType = "Standard"
                self.set_status("Drag to zoom.", 1)
                
                if self.canvasCallback:
                    figure.canvas.mpl_disconnect(self.canvasCallback)
                    self.canvasCallback = None
                    
            print "Drawing %s" % time.clock()
            self.graph.draw()
        except EmptySpectrum as err:
            errBox = wx.MessageBox(str(err), "Charge Transformation Failed.")
            import traceback
            print traceback.format_exc() 
            
            figure = self.graph.get_figure()
            figure.clear()
            
            self.set_status("", 1)
        finally:
            wx.EndBusyCursor()
            self.set_status("Ready.", 0)
            
        print "Done %s" % time.clock()
    
    

        
    def onMannClick(self, event):
        if not event.dblclick:
            print "Skipping single click."
            #event.Skip()
            return
        
        pressed = event.button
        if pressed == 1: # Left-click.
            clickPoint = event.xdata, event.ydata
            if not (clickPoint[0] and clickPoint[1]): return
            
            #nearPoint = min(self.midSpectrum, key = lambda x: abs(clickPoint[0] - x[0])**2 + abs(clickPoint[1] - x[1])**2 )
            #print clickPoint
            #print nearPoint
            
            #foo = obtainPeaksForMass(self.knownSpectrum, nearPoint[0], 0.1)
            
            nearPoint, chargePts = findMassSequenceInMann(self.midSpectrum, self.knownSpectrum, clickPoint)
            labelLetter = 'A'
            while labelLetter in self.usedLabelLetters:
                labelLetter = chr(ord(labelLetter)+1)
            self.usedLabelLetters.append(labelLetter)
            
            nearPointLabelText = '%s\n%s' % (nearPoint[0], labelLetter)
            
            figure = self.graph.get_figure()
            lowAxis, midAxis = figure.get_axes()
            nearPointLabel = midAxis.text(nearPoint[0], nearPoint[1], 
                                          nearPointLabelText, color = 'r', fontsize = 15,
                                          horizontalalignment = 'center',
                                          verticalalignment = 'bottom')
            chargeTexts = []
            for chargePt, charge in chargePts:
                chargeLabel = lowAxis.text(chargePt[0], chargePt[1],
                                           labelLetter, color = 'r', fontsize = 15,
                                           horizontalalignment = 'center',
                                           verticalalignment = 'bottom')
                chargeTexts.append(chargeLabel)
            self.texts.append((nearPointLabel, chargeTexts, labelLetter))
            
            #newLabel = midAxis.text(nearPoint[0], nearPoint[1], nearPoint[0], color = 'r', fontsize = 15)
            #self.texts.append(newLabel)
            self.graph.draw()
            
        elif pressed == 3: # Right-click.
            clickPoint = event.xdata, event.ydata
            nearText = min(self.texts, key = lambda (x, y): abs(clickPoint[0] - x._x)**2 + abs(clickPoint[1] - x._y)**2)
            self.texts.remove(nearText)
            
            nearText[0].remove()
            for chargeText in nearText[1]:
                chargeText.remove()
                
            self.usedLabelLetters.remove(nearText[2])
            
            self.graph.draw()
            
        self.graph.ReleaseMouse()
        #event.Skip()
    
    def toMZTransform(self, event):
        transform = deconvolutionSession(self, "mzTransform")
        
        transform.removalAreaSetting.SetValue(self.removalAreaC.GetValue())
        transform.requiredLengthSetting.SetValue(self.minimumPeaksC.GetValue())
        transform.peakIterationsSetting.SetValue(self.minimumPeaksC.GetValue())
        transform.rangeSetting.SetValue(self.mzRangeC.GetValue())
        
        if self.filename:
            transform.fileBox.Clear()
            transform.fileBox.AppendText(self.filename)
            transform.files = [self.filename]
        
        transform.Show()
        


        
# NOT THE SAME ONE AS IN CHARGETRANSFORM.PY!  This one does the two-part plots
# rather than the three-plot.
        
def chargeDeconvolution(mzSpectrum, mzRange, massRange,
                        speciesCount, removalArea, minimumPeaks, peakIterations,
                        zcLabelCount, smoothWindow, targetFigure):
    
    # Filter by mzRange.
    mzSpectrum = [x for x in mzSpectrum if mzRange[0] < x[0] < mzRange[1]]
    # (Calibration done in the Transform Viewer object for some reason.)
    # Rescale intensity values.
    highIntensity = max([x[1] for x in mzSpectrum]) / 100
    mzSpectrum = [(mz, intensity/highIntensity) for (mz, intensity) in mzSpectrum]   
    
    #try:
    mwLabels, labelledMZPeaks, zcSpectrum = getAllMW(mzSpectrum, speciesCount,
                                                     removalArea, minimumPeaks, 
                                                     peakIterations, smoothWindow,
                                                     massRange)
    #except EmptySpectrum:
        #print "No peaks."
        #return

    targetFigure = plotSpectrum(mzSpectrum, sum(labelledMZPeaks, []), targetFigure, 2, 2,
                                printIntensity = False, xUnits = "m/z", 
                                labelColor = 'red', smallTicks = True,
                                labelParams = (1, 100),
                                caption = 'Mass Spectrum')
    
    targetFigure = plotSpectrum(zcSpectrum, mwLabels, targetFigure, 1, 2,
                                xRange = massRange, recoverPeaks = True,
                                carefulLabelling = True,
                                labelParams = (1, 100),
                                caption = 'Zero-Charge Spectrum')
    
    targetFigure.subplots_adjust(hspace = 0.5)
    
    return zcSpectrum

def writeMannDeconvolution(spectrum, targetFigure, massRange = (10000, 100000)):
    chargeRange = (2, 300)
    massSpectrum = mannAlgorithm(spectrum, massRange, chargeRange)
    
    targetFigure = plotSpectrum(spectrum, [], targetFigure, 2, 2,
                                printIntensity = False, xUnits = "M/Z", 
                                labelColor = 'red', smallTicks = True,
                                labelParams = (1, 100))
    
    targetFigure = plotSpectrum(massSpectrum, [], targetFigure, 1, 2,
                                xRange = massRange, recoverPeaks = True,
                                carefulLabelling = True,
                                labelParams = (1, 100))    
    
    targetFigure.subplots_adjust(hspace = 0.5)
    
    return massSpectrum  