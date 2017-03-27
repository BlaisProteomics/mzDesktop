import multiplierz.spectral_process as s_p
import multiplierz.mgf as mgf
from gui import BasicTab
import wx
from async import launch_process


reduceChargeTooltip = ("This algorithm attempts to determine the charge state "
                       "of fragment ions by matching fragment peaks with their "
                       "co-isotopic peaks; when this can be identified, the "
                       "original set of isotopic peaks is removed and replaced "
                       "with a charge-reduced (charge 1) peak.  This often "
                       "improves database search scores and allows the spectra "
                       "to be searched in a single-charge mode; however, it is"
                       "only effective on scans taken with <0.01Da mz accuracy.")
topNPeaksTooltip = ("This filter takes the most intense peaks in each spectrum "
                    "and discards the rest.")
excludeRadiusTooltip = ("Based on a filtration technique used by the OMSSA "
                        "database search tool; peaks are chosen in order of "
                        "greatest-to-least intensity, and in each case "
                        "surrounding peaks within a given range (the 'radius') "
                        "are discarded.")
signalNoiseTooltip = ("This filter removes the least intense peaks from a "
                      "given scan until the signal-to-noise ratio of all "
                      "peaks in the scan is at least as high as the specified "
                      "threshold.")
intThresholdTooltip = ("This filter removes all peaks in each scan below "
                      "the specified intensity threshold.")
rangeTooltip = ("This filters out all peaks in the spectrum beyond a certain"
                "MZ range (e.g., '500-2000'.)")

centroidTooltip = ("Ensures that spectra are written in centroided format,"
                   "where spectral peaks are taken as the arithmetic mean of all"
                   "points on the peak curve.  This greatly improves search"
                   "performance in most cases, as well as reducing file size.")
scanTypeTooltip = ("For Thermo .RAW files only, multiplierz can extract MS2 scans"
                   "of a specified scan type (Collision-Induced Dissociation (CID),"
                   "Higher-energy Collisional Dissociation (HCD), or Electron-"
                   "Transfer Dissociation (ETD)), ignoring all other MS2 scans"
                   "in the file.")

scanTypeList = ['All', 'CID', 'HCD', 'ETD']

class MGFPanel(BasicTab):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)

        self.processes = {}
        self.activeProcesses = set()

        self.gbs = wx.GridBagSizer(10, 10)

        # Converter Segment
        extractorLabel = wx.StaticText(self, -1, "Convert Data To MGF")

        convertInLabel = wx.StaticText(self, -1, "Input")
        self.convertInCtrl = wx.TextCtrl(self, -1, "")
        self.convertInBrowse = wx.Button(self, -1, "Browse")

        convertOutLabel = wx.StaticText(self, -1, "Output")
        self.convertOutCtrl = wx.TextCtrl(self, -1, "")
        self.convertOutBrowse = wx.Button(self, -1, "Browse")

        self.scanTypeLabel = wx.StaticText(self, -1, "Extract Scan Type")
        self.scanTypeLabel.SetToolTip(wx.ToolTip(scanTypeTooltip))
        self.scanType = wx.ComboBox(self, -1, choices = scanTypeList)
        self.scanType.SetToolTip(wx.ToolTip(scanTypeTooltip))
        self.scanType.SetValue('All')

        self.centroid = wx.CheckBox(self, -1, "Centroid Spectra (recommended)")
        self.centroid.SetToolTip(wx.ToolTip(centroidTooltip))
        self.centroid.SetValue(True)

        self.convertButton = wx.Button(self, -1, "Convert")


        # Processing Segment

        processorLabel = wx.StaticText(self, -1, "Process MGF Spectra")

        processInputLabel = wx.StaticText(self, -1, "Input")
        self.processInputCtrl = wx.TextCtrl(self, -1, "")
        self.processInputBrowse = wx.Button(self, -1, "Browse")

        processOutputLabel = wx.StaticText(self, -1, "Output")
        self.processOutputCtrl = wx.TextCtrl(self, -1, "")
        self.processOutputBrowse = wx.Button(self, -1, "Browse")

        self.processingControls = []
        self.processingControls.append(self.processCtrl(s_p.deisotope_reduce_scan,
                                                        "Reduce Charge",
                                                        '',
                                                        reduceChargeTooltip))
        self.processingControls.append(self.processCtrl(s_p.top_n_peaks,
                                                        "Take High-Intensity Peaks",
                                                        "# Peaks",
                                                        topNPeaksTooltip))
        self.processingControls.append(self.processCtrl(s_p.exclusion_radius,
                                                        "Exclude Radius",
                                                        "Radius",
                                                        excludeRadiusTooltip))
        self.processingControls.append(self.processCtrl(s_p.signal_noise,
                                                        "Signal-to-Noise Filter",
                                                        "S/N Threshold",
                                                        signalNoiseTooltip))
        self.processingControls.append(self.processCtrl(s_p.intensity_threshold,
                                                        "Intensity Threshold",
                                                        "Threshold",
                                                        intThresholdTooltip))
        self.processingControls.append(self.processCtrl(s_p.mz_range,
                                                        "MZ Range",
                                                        "Range",
                                                        rangeTooltip))
        

        self.processButton = wx.Button(self, -1, "Process")


        # Placement

        self.gbs.Add(extractorLabel, (0, 0), flag = wx.ALIGN_RIGHT)
        self.gbs.Add(convertInLabel, (1, 0), flag = wx.ALIGN_RIGHT)
        self.gbs.Add(self.convertInCtrl, (1, 1), span = (1, 6), flag = wx.EXPAND)
        self.gbs.Add(self.convertInBrowse, (1, 7), flag = wx.ALIGN_LEFT)
        self.gbs.Add(convertOutLabel, (2, 0), flag = wx.ALIGN_RIGHT)
        self.gbs.Add(self.convertOutCtrl, (2, 1), span = (1, 6), flag = wx.EXPAND)
        self.gbs.Add(self.convertOutBrowse, (2, 7), flag = wx.ALIGN_LEFT)
        self.gbs.Add(self.centroid, (3, 4), flag = wx.ALIGN_RIGHT)
        self.gbs.Add(self.scanTypeLabel, (3, 1), flag = wx.ALIGN_RIGHT)
        self.gbs.Add(self.scanType, (3, 2), flag = wx.ALIGN_LEFT)
        self.gbs.Add(self.convertButton, (4, 1), flag = wx.EXPAND)


        self.gbs.Add(wx.StaticLine(self, -1), (6, 0), span = (1, 7), flag = wx.EXPAND)


        self.gbs.Add(processorLabel, (7, 0), flag = wx.ALIGN_RIGHT)
        self.gbs.Add(processInputLabel, (8, 0), flag = wx.ALIGN_RIGHT)
        self.gbs.Add(self.processInputCtrl, (8, 1), span = (1, 6), flag = wx.EXPAND)
        self.gbs.Add(self.processInputBrowse, (8, 7), flag = wx.ALIGN_LEFT)
        self.gbs.Add(processOutputLabel, (9, 0), flag = wx.ALIGN_RIGHT)
        self.gbs.Add(self.processOutputCtrl, (9, 1), span = (1, 6), flag = wx.EXPAND)
        self.gbs.Add(self.processOutputBrowse, (9, 7), flag = wx.ALIGN_LEFT)

        #self.placeProcess(11, chaRedLabel, None, self.chaRedActive,
                          #None, self.chaRedOrder)
        #self.placeProcess(12, topNLabel, topNArgLabel, self.topNArgActive,
                          #self.topNArg, self.topNOrder)
        #self.placeProcess(13, excludeRadLabel, excludeRadArgLabel, self.excludeRagActive,
                          #self.excludeRadArg, self.excludeRadOrder)
        #self.placeProcess(14, sigNoiLabel, sigNoiArgLabel, self.sigNoiActive,
                          #self.sigNoiArg, self.sigNoiOrder)
        #self.placeProcess(15, intThresLabel, intThresArgLabel, self.intThresActive,
                          #self.intThresArg, self.intThresOrder)
                          
        self.gbs.Add(wx.StaticText(self, -1, "Algorithm"), (11, 1))
        self.gbs.Add(wx.StaticText(self, -1, "Use"), (11, 2))
        self.gbs.Add(wx.StaticText(self, -1, "Parameter"), (11, 3), span = (1, 2),
                     flag = wx.ALIGN_CENTER)
        self.gbs.Add(wx.StaticText(self, -1, "Step Number"), (11, 5))
        self.gbs.Add(wx.StaticLine(self, -1), (12, 1), span = (1, 5), flag = wx.EXPAND)
        for row, controlset in enumerate(self.processingControls, start = 13):
            self.placeProcess(row, *controlset)
            
        self.gbs.Add(self.processButton, (19, 1), flag = wx.EXPAND)

        self.gbs.Add(wx.StaticText(self, -1, ""), (20, 0)) # Just to make the bottom growable col work.
        self.gbs.Add(wx.StaticText(self, -1, ""), (0, 8)) # Likewise for the outer growable col.

                
        # Buttonery

        self.Bind(wx.EVT_BUTTON, self.getConvertInput, self.convertInBrowse)
        self.Bind(wx.EVT_BUTTON, self.getConvertOutput, self.convertOutBrowse)
        self.Bind(wx.EVT_BUTTON, self.getProcessInput, self.processInputBrowse)
        self.Bind(wx.EVT_BUTTON, self.getProcessOutput, self.processOutputBrowse)
        self.Bind(wx.EVT_BUTTON, self.convert, self.convertButton)
        self.Bind(wx.EVT_BUTTON, self.process, self.processButton)

        # Etc

        self.gbs.AddGrowableCol(6)
        self.gbs.AddGrowableCol(8)
        self.gbs.AddGrowableRow(5)
        self.gbs.AddGrowableRow(20)

        overBox = wx.BoxSizer()
        overBox.Add(self.gbs, 1, wx.ALL | wx.EXPAND, 20)
        self.SetSizerAndFit(overBox)


    def processCtrl(self, processFunc, processName, argName, tooltip):
        label = wx.StaticText(self, -1, processName)
        if argName:
            arglabel = wx.StaticText(self, -1, argName)
            argCtrl = wx.TextCtrl(self, -1, "")
        else:
            arglabel = None
            argCtrl = None
        activeCheck = wx.CheckBox(self, -1, "")
        activeCheck.SetValue(False)
        order = wx.ComboBox(self, -1, choices = [], size = (45, -1))

        def toggleUse(event):
            use = activeCheck.GetValue()
            if use:
                self.activeProcesses.add(order)
            else:
                try:
                    self.activeProcesses.remove(order)
                except KeyError:
                    #print order
                    pass

            for switch in self.activeProcesses:
                switch.Set([str(x) for x in range(1, len(self.activeProcesses)+1)])
            #order.Set([str(x) for x in range(1, self.activeProcesses+1)])
            
            #label.Enable(use)
            order.Enable(use)
            if argName:
                argCtrl.SetValue("")
                argCtrl.Enable(use)
                arglabel.Enable(use)            

        toggleUse(None)
        self.Bind(wx.EVT_CHECKBOX, toggleUse, activeCheck)
        
        label.SetToolTip(wx.ToolTip(tooltip))
        if arglabel:
            arglabel.SetToolTip(wx.ToolTip(tooltip))  
        activeCheck.SetToolTip(wx.ToolTip(tooltip))
        order.SetToolTip(wx.ToolTip(tooltip))

        return label, arglabel, activeCheck, argCtrl, order, processFunc

    def placeProcess(self, row, label, arglabel, activeCheck, argCtrl, order, _):
        self.gbs.Add(label, (row, 1), flag = wx.ALIGN_LEFT)
        self.gbs.Add(activeCheck, (row, 2), flag = wx.ALIGN_RIGHT)
        if arglabel and argCtrl:
            self.gbs.Add(arglabel, (row, 3), flag = wx.ALIGN_RIGHT)
            self.gbs.Add(argCtrl, (row, 4), flag = wx.ALIGN_LEFT)
        
        self.gbs.Add(order, (row, 5), flag = wx.ALIGN_LEFT)

    
    def getConvertInput(self, event):
        dialog = wx.FileDialog(self, "Choose input file...",
                               wildcard = "RAW|*.raw|WIFF|*.wiff|mzML|*.mz|All|*.*",
                               style = wx.FD_OPEN | wx.FD_MULTIPLE)
        
        if dialog.ShowModal() == wx.ID_OK:
            paths = dialog.GetPaths()
            self.convertInCtrl.SetValue(", ".join(paths))
            self.convertOutCtrl.SetValue(", ".join([x + '.mgf' for x in paths]))
    
    def getConvertOutput(self, event):
        dialog = wx.FileDialog(self, "Choose output file...",
                               wildcard = 'MGF|*.mgf|All|*',
                               style = wx.FD_SAVE)
        
        if dialog.ShowModal() == wx.ID_OK:
            self.convertOutCtrl.SetValue(", ".join(paths))
            
    def getProcessInput(self, event):
        dialog = wx.FileDialog(self, "Choose input file...",
                               wildcard = "MGF|*.mgf|All|*",
                               style = wx.FD_OPEN | wx.FD_MULTIPLE)
    
        if dialog.ShowModal() == wx.ID_OK:
            paths = dialog.GetPaths()
            self.processInputCtrl.SetValue(", ".join(paths))
            
            defOutPaths = ['.'.join(x.split('.')[:-1] + ['processed', 'mgf'])
                           for x in paths]
            self.processOutputCtrl.SetValue(", ".join(defOutPaths))
            
    def getProcessOutput(self, event):
        dialog = wx.FileDialog(self, "Choose output file...",
                               wildcard = 'MGF|*.mgf|All|*',
                               style = wx.FD_SAVE)
    
        if dialog.ShowModal() == wx.ID_OK:
            self.processOutputCtrl.SetValue(", ".join(paths))        
        

    def convert(self, event):
        inputfile = self.convertInCtrl.GetValue()
        outputfile = self.convertOutCtrl.GetValue()
        
        scantype = self.scanType.GetValue()
        centroid = self.centroid.GetValue()
        
        if scantype == 'All':
            scantype = None
        
        inputs = [x.strip() for x in inputfile.split(',') if x] # Right?
        #if len(inputs) > 1 and outputfile:
            #raise IOError, "Ambigous outputfile selection!"
        if outputfile:
            outputs = outputs = [x.strip() for x in outputfile.split(',') if x]
        else:
            outputs = [x + '.mgf' for x in inputs]
        
        if len(inputs) != len(outputs):
            messdog = wx.MessageDialog(self, "Input files do not match outputs!",
                                       style = wx.OK)
            messdog.ShowModal()
            messdog.Destroy()
            return
        
        for infile, outfile in zip(inputs, outputs):
            print "Extracting spectra from %s..." % infile
            #mgf.extract(infile, outputfile = outfile, centroid = centroid)
            try:
                self.convertButton.Enable(False)
                def callback(results):
                    print "\tExtracted spectra to %s" % results
                launch_process(mgf.extract, callback = callback,
                               datafile = infile, outputfile = outfile,
                               centroid = centroid)
            finally:
                self.convertButton.Enable(True)
        
        print "Done."
        

    def process(self, event):
        processes = []
        for _, _, activeCheck, argCtrl, order, function in self.processingControls:
            if activeCheck.GetValue():
                try:
                    orderNum = int(order.GetValue())
                except ValueError:
                    orderNum = 99
                
                if argCtrl:
                    processes.append((orderNum, argCtrl.GetValue(), function))
                else:
                    processes.append((orderNum, None, function))
                    
        
        if not processes:
            messdog = wx.MessageDialog(self, "No processing steps selected!",
                                       style = wx.OK)
            messdog.ShowModal()
            messdog.Destroy()
            return
        
        infiles = [x.strip() for x in self.processInputCtrl.GetValue().split(',')]
        outfiles = [x.strip() for x in self.processOutputCtrl.GetValue().split(',')]
        if len(infiles) != len(outfiles):
            messdog = wx.MessageDialog(self, "Input files do not match outputs!",
                                       style = wx.OK)
            messdog.ShowModal()
            messdog.Destroy()
            return
        
        processes.sort(key = lambda x: x[0])
        functions = [(x[1], x[2]) for x in processes]
        for infile, outfile in zip(infiles, outfiles):
            print "Processing %s..." % infile
            #mgf.apply_spectral_process(infile, functions, outputFile = outfile)
            try:
                self.processButton.Enable(False)
                def callback(outfile):
                    print "\tProcessed file written to %s" % outfile
                launch_process(mgf.apply_spectral_process, callback,
                               infile, functions, outputFile = outfile)
            finally:
                self.processButton.Enable(True)
                
        
        print "Done."
    
    