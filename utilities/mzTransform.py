from multiplierz.mzTools.chargeTransform import chargeDeconvolution, compilePeakLists, findESIPeaks, chargeDecWholeRunMode, powerPointCleanup, consolidateMode
import async
import wx
import time
import os

initialPeakRemoval = str(3)
initialRequiredPeaks = str(8)
initialPeakIterations = str(2)
initialMZRange = "300-2000"


fileTypes = ['.txt', '.ppt', '.pptx', '.pgf', '.svgz', '.tiff', '.jpg', '.raw',
             '.jpeg', '.png', '.ps', '.svg', '.eps', '.rgba', '.pdf', '.tif']


# Helpful tooltip tests.

maxChargeTip = ("The maximum potential charge of the target molecule that will be considered.")
mzTolTip = ("The width of an m/z region that will be read to find the peak at a given m/z "
            "point; the expected 'width' of a peak.")
snThresholdTip = ("The signal-to-noise multiple that will be required of a peak to warrant "
                  "a search for it in the spectrum; based on the intensity of the peak region "
                  "versus by the baseline intensity of the surrounding region.")
mzRangeTip = ("The m/z range that will be searched.")
outputTypeTip = ("Format of the output file.")
maxSpecCountTip = ("Maximum chemical species that will be detected, per scan given.")
maxZoomTip = ("Maximum allowed labels on the topmost graph of the output (primarily "
              "intended to prevent graphical overcrowding.)")
maxZCTip = ("Maximum allowed labels on the middle graph of the output (primarily "
            "inteded to prevent graphical overcrowding.)")
segModeTip = ("In this mode, an analysis will be peformed on each time segment of "
              "the scan, and a set of graphs will be given for each.")
segSizeTip = ("Length of a time segment, in minutes.")
startTimeTip = ("The start time of the first time segment, in minutes.")
consolidateTip = ("If output format .ppt is chosen, consolidate all output graphs "
                  "into a single slideshow.")



requiredPeaksTip = ("The number of peaks corresponding to a given mass that must "
                    "be found for that mass to be considered detected.")
peakIterationsTip = ("The depth to which the initial peak-finding algorithm is " 
                     "recursively performed.  Higher values may be able to distinguish "
                     "partially overlapping peaks better.  2 is typically a good value.")
peakRemovalTip = ("Distance from a given peak that is cleared from the m/z spectrum "
                  "when that peak is identified as the product of a detected particle.")


class deconvolutionSession(wx.Frame):
    def __init__(self, parent, title):
        super(deconvolutionSession, self).__init__(parent, title=title, size = (760, 425))

        
        self.files = []
        self.SN = "5"
        self.outputType = ".svg"
        self.peakWidth = "2"
        self.maxCharge = "50"
        self.mzRange = "300-2000"
        self.segmentMode = False
        self.segmentSize = "5"
        self.startSegment = "0"
        
        panel = wx.Panel(self)
                                    
        vBox = wx.BoxSizer(wx.VERTICAL)
        topBox = wx.BoxSizer(wx.HORIZONTAL)
        self.fileBox = wx.TextCtrl(panel, size = (750, 150), 
                                   style = wx.TE_READONLY | wx.TE_MULTILINE | wx.TE_DONTWRAP)
        topBox.Add(self.fileBox, flag = wx.EXPAND|wx.LEFT|wx.RIGHT)
        vBox.Add(topBox, flag = wx.EXPAND|wx.ALIGN_TOP, border = 5)
        

        self.browseButton = wx.Button(panel, wx.ID_ANY, 'Browse...')
        self.Bind(wx.EVT_BUTTON, self.fileBrowse, id = self.browseButton.GetId())
        
        self.goButton = wx.Button(panel, wx.ID_ANY, 'Deconvolute!')
        self.Bind(wx.EVT_BUTTON, self.deconvolute, id = self.goButton.GetId())        
        
        self.removalAreaSetting = wx.TextCtrl(panel, size = (30, 25),
                                            name = "removalArea", value = initialPeakRemoval)
        self.removalAreaLabel = wx.StaticText(panel, style = wx.ALIGN_RIGHT,
                                              label = "Peak Removal\nArea:")
        self.removalAreaLabel.SetToolTip(wx.ToolTip(peakRemovalTip))
        
        self.requiredLengthSetting = wx.TextCtrl(panel, size = (30, 25),
                                            name = "requiredLength", value = initialRequiredPeaks)
        self.requiredLengthLabel = wx.StaticText(panel, style = wx.ALIGN_RIGHT,
                                                 label = "Required Peaks:")
        self.requiredLengthLabel.SetToolTip(wx.ToolTip(requiredPeaksTip))
        
        self.peakIterationsSetting = wx.TextCtrl(panel, size = (30, 25),
                                            name = "peakIterations", value = initialPeakIterations)
        self.peakIterationsLabel = wx.StaticText(panel, style = wx.ALIGN_RIGHT, 
                                                 label = "Peak\nIterations:")   
        self.peakIterationsLabel.SetToolTip(wx.ToolTip(peakIterationsTip))
        
        self.outputSetting = wx.TextCtrl(panel, size = (50, 25),
                                         name = "Output Type", value = self.outputType)
        self.outputLabel = wx.StaticText(panel, style = wx.ALIGN_RIGHT,
                                         label = "Output File\n Type:")        
        self.outputLabel.SetToolTip(wx.ToolTip(outputTypeTip))
        
        self.rangeSetting = wx.TextCtrl(panel, size = (70, 25),
                                        value = initialMZRange, name = "M/Z range")
        self.rangeLabel = wx.StaticText(panel, style = wx.ALIGN_RIGHT,
                                        label = "M/Z Range")
        self.rangeLabel.SetToolTip(wx.ToolTip(mzRangeTip))
        
        self.modeSetting = wx.CheckBox(panel, label = "Segment Mode")
        self.modeSetting.SetToolTip(wx.ToolTip(segModeTip))
        
        self.segmentSetting = wx.TextCtrl(panel, size = (50, 25),
                                          value = self.segmentSize, name = "Segment Size")
        self.segmentLabel = wx.StaticText(panel, style = wx.ALIGN_RIGHT,
                                          label = "Segment Size")
        self.segmentLabel.SetToolTip(wx.ToolTip(segSizeTip))
        
        self.segmentStart = wx.TextCtrl(panel, size = (50, 25),
                                        value = self.startSegment, name = "Start Segment")
        self.segStartLabel = wx.StaticText(panel, 
                                           label = "Start Time")
        self.segStartLabel.SetToolTip(wx.ToolTip(startTimeTip))
        
        self.mostSpecies = wx.TextCtrl(panel, size = (50, 25),
                                        value = "5", name = "Maximum Species")
        self.speciesLabel = wx.StaticText(panel, style = wx.ALIGN_RIGHT,
                                          label = "Maximum Species\n Count")
        self.speciesLabel.SetToolTip(wx.ToolTip(maxSpecCountTip))
        
        self.consolidateSetting = wx.CheckBox(panel, label = "Consolidate Slides")
        self.consolidateSetting.SetToolTip(wx.ToolTip(consolidateTip))
        
        self.zeroChargeLabels = wx.TextCtrl(panel, size = (50, 25),
                                            value = "", name = "Zero Charge Spectra Labels")
        self.zcLabelsLabel = wx.StaticText(panel, style = wx.ALIGN_RIGHT,
                                           label = "Maximum ZC\n Spectrum Labels")
        self.zcLabelsLabel.SetToolTip(wx.ToolTip(maxZCTip))
        
        self.zoomLabels = wx.TextCtrl(panel, size = (50, 25),
                                      value = "", name = "Zoomed Spectrum Labels")
        self.zoomLabelsLabel = wx.StaticText(panel, style = wx.ALIGN_RIGHT,
                                             label = "Maximum Zoomed\n Spectrum Labels")
        self.zoomLabelsLabel.SetToolTip(wx.ToolTip(maxZoomTip))
        
        self.recalCheck = wx.CheckBox(panel, label = "Recalibrate")
        
        self.recalSlopeLabel = wx.StaticText(panel, style = wx.ALIGN_RIGHT, 
                                             label = "Slope")
        self.recalSlope = wx.TextCtrl(panel, size = (50, 25), value = '0')
        
        self.recalInterLabel = wx.StaticText(panel, style = wx.ALIGN_RIGHT,
                                             label = "Intercept")
        self.recalInter = wx.TextCtrl(panel, size = (50, 25), value = '0')
        
        self.smoothWindowLabel = wx.StaticText(panel, style = wx.ALIGN_RIGHT,
                                               label = "Smoothing\nWindow Width")
        self.smoothWindow = wx.TextCtrl(panel, size = (50, 25), value = '')
        
        self.massRangeLabel = wx.StaticText(panel, style = wx.ALIGN_RIGHT,
                                            label = "Mass Range")
        self.massRange = wx.TextCtrl(panel, size = (50, 25), value = '10000-100000')
        
        self.mannMode = wx.CheckBox(panel, label = "Mann Algorithm")

        cpBox = wx.GridBagSizer(12, 5)
        
        labels = [self.removalAreaLabel, self.requiredLengthLabel, self.peakIterationsLabel,
                  self.rangeLabel, self.outputLabel, self.speciesLabel, 
                  self.zoomLabelsLabel, self.segmentStart, self.segmentSetting,
                  self.segmentLabel]
        general = [(self.removalAreaLabel, self.removalAreaSetting),
                   (self.requiredLengthLabel, self.requiredLengthSetting),
                   (self.peakIterationsLabel, self.peakIterationsSetting),
                   (self.rangeLabel, self.rangeSetting),
                   (self.outputLabel, self.outputSetting), 
                   (self.speciesLabel, self.mostSpecies), 
                   (self.zoomLabelsLabel, self.zoomLabels),
                   (self.zcLabelsLabel, self.zeroChargeLabels)]
        
        self.segmentMode = [(self.segmentLabel, self.segmentSetting),
                            (self.segStartLabel, self.segmentStart)]

        self.recalibrateMode = [(self.recalSlopeLabel, self.recalSlope),
                                (self.recalInterLabel, self.recalInter)]

        i = 0
        lastSpace = None
        for y in [0, 2]:
            for x in [0, 1, 2, 3]:
                try:
                    cpBox.Add(general[i][0], (x, y), flag = wx.ALIGN_RIGHT)
                    cpBox.Add(general[i][1], (x, y+1), flag = wx.ALIGN_LEFT)
                    i += 1
                except IndexError:
                    lastSpace = (x, y)
                    break
        
        cpBox.Add(self.modeSetting, (0, 5), span = (1, 2), flag = wx.ALIGN_CENTER)
        self.modeSetting.Bind(wx.EVT_CHECKBOX, self.on_segment_check)

        for x in range(0, len(self.segmentMode)):
            cpBox.Add(self.segmentMode[x][0], (x+1, 5), flag = wx.ALIGN_RIGHT)
            cpBox.Add(self.segmentMode[x][1], (x+1, 6), flag = wx.ALIGN_LEFT)
            self.segmentMode[x][0].Enable(False)
            self.segmentMode[x][1].Enable(False)
            
        cpBox.Add(self.recalCheck, (0,7), span = (1, 2), flag = wx.ALIGN_CENTER)
        self.recalCheck.Bind(wx.EVT_CHECKBOX, self.on_recal_check)
        for x in range(0, len(self.recalibrateMode)):
            cpBox.Add(self.recalibrateMode[x][0], (x+1, 7), flag = wx.ALIGN_RIGHT)
            cpBox.Add(self.recalibrateMode[x][1], (x+1, 8), flag = wx.ALIGN_LEFT)
            self.recalibrateMode[x][0].Enable(False)
            self.recalibrateMode[x][1].Enable(False)
            
        cpBox.Add(self.smoothWindowLabel, (3, 5), flag = wx.ALIGN_RIGHT)
        cpBox.Add(self.smoothWindow, (3, 6), flag = wx.ALIGN_LEFT)
        
        cpBox.Add(self.massRangeLabel, (4, 1), flag = wx.ALIGN_RIGHT)
        cpBox.Add(self.massRange, (4, 2), span = (1, 2), flag = wx.ALIGN_LEFT | wx.EXPAND)
        
        cpBox.Add(self.mannMode, (4, 7), span = (1, 2), flag = wx.ALIGN_RIGHT)
            
        cpBox.Add(self.browseButton, (0, 10), span = (1, 2), flag = wx.ALIGN_RIGHT | wx.EXPAND)
        cpBox.Add(self.consolidateSetting, (1, 10), span = (1, 2), flag = wx.ALIGN_CENTER)
        cpBox.Add(self.goButton, (2, 10), span = (1, 2), flag = wx.ALIGN_RIGHT | wx.EXPAND)
                    
        #cpBox.AddGrowableCol(7)
        cpBox.AddGrowableCol(9)                
        
        vBox.Add(cpBox, 1, wx.ALL | wx.EXPAND | wx.ALIGN_CENTER, 20)
        panel.SetSizerAndFit(vBox)
        
        self.fileBox.ChangeValue("""
        ====== mzTransform v0.015 ======
        
        Select one or more data files (.RAW, .WIFF, etc) which will be processed
        separately.  Alternately, select one or more spectrum lists (.txt files
        of mz-intensity pairs) which will be processed as a single 
        summed spectrum.
        
        Select output extension ".ppt" or ".pptx" to produce a PowerPoint slide,
        select extension ".txt" to produce the raw peak list data,
        otherwise select ".svg" (or any other extension supported by PyPlot) to
        produce an image file.
        
        
        """)
        
        
        
        
        self.Centre()
        self.Show()
        
    def on_segment_check(self, event):
        for label, field in self.segmentMode:
            state = self.modeSetting.GetValue()
            label.Enable(state)
            field.Enable(state)
            
    def on_recal_check(self, event):
        state = self.recalCheck.GetValue()
        for label, field in self.recalibrateMode:
            label.Enable(state)
            field.Enable(state)
        
    def fileBrowse(self, event):
        filedialog = wx.FileDialog(parent = self, message = "Choose Files", 
                                   style = wx.FD_OPEN | wx.FD_MULTIPLE)
        filedialog.ShowModal()
        newfiles = filedialog.GetPaths()
    
        self.files = newfiles
        self.fileBox.Clear()
        if newfiles:
            for filename in newfiles:
                self.fileBox.AppendText(filename + "\n")
        
        filedialog.Destroy()

    
    def deconvolute(self, event):
        time.clock()
        
        peakIterations = float(self.peakIterationsSetting.GetValue())
        outputType = self.outputSetting.GetValue()
        requiredLength = float(self.requiredLengthSetting.GetValue())
        removalArea = int(self.removalAreaSetting.GetValue())
        mzRange = self.rangeSetting.GetValue()
        segmentMode = self.modeSetting.GetValue()
        segmentTime = float(self.segmentSetting.GetValue())
        startSegment = float(self.segmentStart.GetValue())
        consolidateSet = self.consolidateSetting.GetValue()
        smoothWindow = self.smoothWindow.GetValue()
        massRange = self.massRange.GetValue()

        zcLabelCount = self.zeroChargeLabels.GetValue()
        zoomLabelCount = self.zoomLabels.GetValue()
        speciesCount = self.mostSpecies.GetValue()
        
        zcLabelCount = int(zcLabelCount) if zcLabelCount else None
        zoomLabelCount = int(zoomLabelCount) if zoomLabelCount else None
        speciesCount = int(speciesCount) if speciesCount else None
        smoothWindow = int(smoothWindow) if smoothWindow else 0
        
        mannMode = self.mannMode.GetValue()
        
        if self.recalCheck:
            recalSlope = float(self.recalSlope.GetValue())
            recalInter = float(self.recalInter.GetValue())
        else:
            recalSlope = recalInter = 0
        recalibrant = recalSlope, recalInter
        #try:
            #speciesCount = int(self.mostSpecies.GetValue())
        #except ValueError:
            #speciesCount = None
        
        mzRange = [int(mz) for mz in mzRange.split("-")]
        assert len(mzRange) == 2 and mzRange[0] < mzRange[1]
        
        massRange = [int(m) for m in massRange.split("-")]
        assert len(massRange) == 2 and massRange[0] < massRange[1]
        
        try:
            assert outputType in fileTypes
            assert len(self.files) > 0
        except AssertionError:
            self.fileBox.AppendText("Invalid output type or no files chosen.")
            return
        
        
        if consolidateSet:
            global consolidateMode
            consolidateMode = True        
        
        self.goButton.Enable(False)
        self.browseButton.Enable(False)
        wx.BeginBusyCursor()
        
        self.fileBox.AppendText("\n")
        if all([x.split(".")[-1] == "txt" for x in self.files]) and consolidateMode:
            try:
                filename = self.files[0] + ".output"
                self.fileBox.AppendText("Processing spectrum...\n")
                spectrum = compilePeakLists(self.files)
                
                warning = "Consolidate mode on multiple text files: merging \ninto combined m/z spectrum."
                self.fileBox.AppendText(warning)
                
                #chargeDeconvolution(spectrum, filename + outputType, mzRange, massRange,
                                    #speciesCount, removalArea, requiredLength, peakIterations,
                                    #zcLabelCount, zoomLabelCount, recalibrant, smoothWindow,
                                    #consolidateSet)
                                    
                def completionCallback(etc):
                    assert os.path.exists(filename + outputType)
                    self.fileBox.AppendText("Wrote " + filename + outputType + "\n")                    
                async.launch_process(chargeDeconvolution, completionCallback,
                                     spectrum, filename + outputType, mzRange, massRange,
                                     speciesCount, removalArea, requiredLength, peakIterations,
                                     zcLabelCount, zoomLabelCount, recalibrant, smoothWindow,
                                     consolidateSet)                                     
                
                

            except AssertionError as err:
                print err
                self.fileBox.AppendText("Failed to process files.\n")
        else:
            for filename in self.files:
                try:
                    assert os.path.exists(filename)
                except AssertionError:
                    self.fileBox.AppendText(filename + "not found!")
                    continue
                    
                
                try:
                    self.fileBox.AppendText("Processing " + filename + " ...\n")
                    
                    if not segmentMode:
                        spectrum = findESIPeaks(filename)
                        #spectrum = async.launch_process(findESIPeaks, None, filename)
                        #chargeDeconvolution(spectrum, filename + outputType, mzRange, massRange,
                                            #speciesCount, removalArea, requiredLength, peakIterations,
                                            #zcLabelCount, zoomLabelCount, recalibrant, smoothWindow,
                                            #consolidateSet)
                        async.launch_process(chargeDeconvolution, None,
                                             spectrum, filename + outputType, mzRange, massRange,
                                             speciesCount, removalArea, requiredLength, peakIterations,
                                             zcLabelCount, zoomLabelCount, recalibrant, smoothWindow,
                                             consolidateSet)
                        if not consolidateSet:
                            assert os.path.exists(filename + outputType)
                        self.fileBox.AppendText("Wrote " + filename + outputType + "\n")
                    elif segmentMode:
                        #chargeDecWholeRunMode(filename, filename + outputType, mzRange, massRange,
                                              #speciesCount, removalArea, requiredLength, peakIterations,
                                              #segmentTime, startSegment, consolidateSet,
                                              #zcLabelCount, zoomLabelCount, recalibrant,
                                              #smoothWindow)                  
                        async.launch_process(chargeDecWholeRunMode, None,
                                             filename, filename + outputType, mzRange, massRange,
                                             speciesCount, removalArea, requiredLength, peakIterations,
                                             segmentTime, startSegment, consolidateSet,
                                             zcLabelCount, zoomLabelCount, recalibrant,
                                             smoothWindow)
                        
                        self.fileBox.AppendText("Completed " + filename + '\n')
                except AssertionError as err:
                    print err
                    self.fileBox.AppendText("Failed to process " + filename + "\n")
                    
        if consolidateSet:
            powerPointCleanup()        
        
        self.goButton.Enable(True)
        self.browseButton.Enable(True)            
        wx.EndBusyCursor()

        print time.clock()
        self.fileBox.AppendText("\n\nDone!")
        self.files = []
        
        
if __name__ == '__main__':
    foo = wx.App(0)
    deconvolution = deconvolutionSession(None, "Independent mzTransform Session")
    foo.MainLoop()