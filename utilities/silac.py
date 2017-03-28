from multiplierz.mzTools.silacAnalysis import SILAC2Plex, SILAC3Plex
from multiplierz.mzReport import reader
from regex import RegexHelper
import wx
import os

import async



unimod = None



class SILACSession(wx.Frame):
    def __init__(self, parent, title):
        super(SILACSession, self).__init__(parent, title=title, size = (700, 700))
        
        panel = wx.Panel(self)
        #featureBox = wx.StaticBox(panel, -1)
        

        self.fileBox = wx.TextCtrl(panel, size = (450, 200),
                                   style = wx.TE_READONLY | wx.TE_MULTILINE |
                                   wx.TE_DONTWRAP)
        
        
        dataLabel = wx.StaticText(panel, -1, "Data File")
        self.dataCtrl = wx.TextCtrl(panel, -1, "")
        self.dataBrowse = wx.Button(panel, -1, "Browse")
        
        resultLabel = wx.StaticText(panel, -1, "Peptide File(s)")
        self.resultCtrl = wx.TextCtrl(panel, -1, "")
        self.resultBrowse = wx.Button(panel, -1, "Browse")
        
        #regexExplaination = wx.StaticText(panel, -1, "")
        
        self.customParserCheck = wx.CheckBox(panel, -1, "Use Default Parsers")
        self.customParserCheck.SetValue(True)
        self.Bind(wx.EVT_CHECKBOX, self.toggleParsers, self.customParserCheck)
        
        toMZLabel = wx.StaticText(panel, -1, "M/Z parser")
        self.toMZCtrl = wx.TextCtrl(panel, -1, "")
        self.toMZUtility = wx.Button(panel, -1, "Regex Utility")
        toScanLabel = wx.StaticText(panel, -1, "Scan Number\nParser")
        self.toScanCtrl = wx.TextCtrl(panel, -1, "")
        self.toScanUtility = wx.Button(panel, -1, "Regex Utility")
        

        self.mediumKTag = wx.TextCtrl(panel, size = (120, 25),
                                     value = "Label:2H(4)")
        self.mediumKLabel = wx.StaticText(panel, label = "Medium K")
        self.mediumRTag = wx.TextCtrl(panel, size = (120, 25),
                                      value = "Label:13C(6)")
        self.mediumRLabel = wx.StaticText(panel, label = "Medium R")
        self.heavyKTag = wx.TextCtrl(panel, size = (120, 25),
                                     value = "Label:13C(6)15N(2)")
        self.heavyKLabel = wx.StaticText(panel, label = "Heavy K ")
        self.heavyRTag = wx.TextCtrl(panel, size = (120, 25),
                                     value = "Label:13C(6)15N(4)")
        self.heavyRLabel = wx.StaticText(panel, label = "Heavy R ")
        
        
        toleranceLabel = wx.StaticText(panel, -1, "M/Z Tolerance (PPM)")
        self.toleranceCtrl = wx.TextCtrl(panel, -1, "10")
        #snLabel = wx.StaticText(panel, -1, "Signal/Noise\nThreshold")
        #self.snCtrl = wx.TextCtrl(panel, -1, "25")
        

        #self.combinedResultsCheck = wx.CheckBox(panel, -1, "Combined Results File")

        self.goButton = wx.Button(panel, wx.ID_ANY, 'Analyze')        
        
        self.Bind(wx.EVT_BUTTON, self.browseForData, self.dataBrowse)
        self.Bind(wx.EVT_BUTTON, self.browseForResults, self.resultBrowse)
        self.Bind(wx.EVT_BUTTON, self.beginAnalysis, id = self.goButton.GetId())
        self.Bind(wx.EVT_BUTTON, self.launchMZUtility, self.toMZUtility)
        self.Bind(wx.EVT_BUTTON, self.launchScanUtility, self.toScanUtility)
        
        
        
        gbs = wx.GridBagSizer(10, 10)
        
        vBox = wx.BoxSizer(wx.VERTICAL)                
        vBox.Add(self.fileBox, flag = wx.EXPAND)
        
        gbs.Add(dataLabel, (0, 0), flag = wx.ALIGN_RIGHT)
        gbs.Add(self.dataCtrl, (0, 1), (1, 4), flag = wx.EXPAND)
        gbs.Add(self.dataBrowse, (0, 5), flag = wx.ALIGN_LEFT)
        
        gbs.Add(resultLabel, (1, 0), flag = wx.ALIGN_RIGHT)
        gbs.Add(self.resultCtrl, (1, 1), (1, 4), flag = wx.EXPAND)
        gbs.Add(self.resultBrowse, (1, 5), flag = wx.ALIGN_LEFT)
        
        #gbs.Add(self.combinedResultsCheck, (2, 1))        
        
        
        gbs.Add(self.customParserCheck, (4, 1), flag = wx.ALIGN_LEFT)
        
        gbs.Add(toMZLabel, (5, 0), flag = wx.ALIGN_RIGHT)
        gbs.Add(self.toMZCtrl, (5, 1), (1, 4), flag = wx.EXPAND)
        gbs.Add(self.toMZUtility, (5, 5), flag = wx.ALIGN_LEFT)        
        
        gbs.Add(toScanLabel, (6, 0), flag = wx.ALIGN_RIGHT)
        gbs.Add(self.toScanCtrl, (6, 1), (1, 4), flag = wx.EXPAND)
        gbs.Add(self.toScanUtility, (6, 5), flag = wx.ALIGN_LEFT)
        
        gbs.Add(self.mediumKLabel, (8, 1), flag = wx.ALIGN_RIGHT)
        gbs.Add(self.mediumKTag, (8, 2), flag = wx.ALIGN_LEFT)
        gbs.Add(self.mediumRLabel, (9, 1), flag = wx.ALIGN_RIGHT)
        gbs.Add(self.mediumRTag, (9, 2), flag = wx.ALIGN_LEFT)
        
        gbs.Add(self.heavyKLabel, (8, 3), flag = wx.ALIGN_RIGHT)
        gbs.Add(self.heavyKTag, (8, 4), flag = wx.ALIGN_LEFT)
        gbs.Add(self.heavyRLabel, (9, 3), flag = wx.ALIGN_RIGHT)
        gbs.Add(self.heavyRTag, (9, 4), flag = wx.ALIGN_LEFT)
        
        gbs.Add(toleranceLabel, (11, 1), flag = wx.ALIGN_RIGHT)
        gbs.Add(self.toleranceCtrl, (11, 2), flag = wx.ALIGN_LEFT)
        #gbs.Add(toleranceLabel, (9, 1), flag = wx.ALIGN_RIGHT)
        #gbs.Add(self.toleranceCtrl, (9, 2), flag = wx.ALIGN_LEFT)
        #gbs.Add(snLabel, (9, 3), flag = wx.ALIGN_RIGHT)
        #gbs.Add(self.snCtrl, (9, 4), flag = wx.ALIGN_LEFT)
        
        gbs.Add(self.goButton, (13, 1), (1, 4), flag = wx.EXPAND)
        
        gbs.AddGrowableCol(2)


        vBox.Add(gbs, flag = wx.EXPAND | wx.ALL | wx.ALIGN_CENTER , border = 10)

        panel.SetSizer(vBox)
        
        self.fileBox.ChangeValue("""
        === SILAC Analysis Tool ===
        
        Select a spectrometry data file and a set of search result files; annotated files will be placed in the same directory.
        
        Scan number and precursor M/Z values of each PSM are recovered through the Spectrum Description string; regular 
        expressions which match to each value in the description string are required.  See the Regex Utility for help
        composing these.
        
        Specify the tag formulae as they appear the search result file; leave the medium tag field blank for 2-Plex SILAC
        analysis.
        
        """)
        
        
        self.descriptionSample = ''
        
        self.toggleParsers(None)
        
        self.Centre()
        self.Show()
        
        
    def fileBrowse(self, event):
        fileDialog = wx.FileDialog(parent = self, message = "Choose Mascot File",
                                   style = wx.FD_OPEN)
        fileDialog.ShowModal()
        self.fileBox.Clear()
        
        self.fileBox.AppendText(fileDialog.GetPath() + "\n")
        fileDialog.Destroy()
    
    def browseForData(self, event):
        fileDialog = wx.FileDialog(self, message = "Choose Data File(s)",
                                   style = wx.FD_OPEN | wx.FD_MULTIPLE)
        #fileDialog.ShowModal()
        #self.dataCtrl.SetValue(fileDialog.GetPath())
        #fileDialog.Destroy()
        if fileDialog.ShowModal() == wx.ID_OK:
            self.dataCtrl.SetValue('; '.join(fileDialog.GetPaths()))
        fileDialog.Destroy()        
        
    def browseForResults(self, parent):

        
        fileDialog = wx.FileDialog(self, message = "Choose Target File(s)",
                                   style = wx.FD_OPEN | wx.FD_MULTIPLE)
        if fileDialog.ShowModal() == wx.ID_OK:
            self.resultCtrl.SetValue('; '.join(fileDialog.GetPaths()))
            self.descriptionSample = ''
        fileDialog.Destroy()
        
    def toggleParsers(self, event):
        useParsers = not self.customParserCheck.GetValue()
        
        self.toMZCtrl.Enable(useParsers)
        self.toMZUtility.Enable(useParsers)
        self.toScanCtrl.Enable(useParsers)
        self.toScanUtility.Enable(useParsers)
        
    def sampleTarget(self):
        try:
            firstFile = (x.strip() for x in self.resultCtrl.GetValue().split(';')).next()
            if firstFile:
                print "Peeking into %s for a sample spectrum description..." % firstFile
                data = reader(firstFile)
                row = data.__iter__().next()
                self.descriptionSample = row['Spectrum Description']
                data.close()
        except Exception as err:
            print err        
         
    def launchMZUtility(self, event):
        if not self.descriptionSample:
            self.sampleTarget()
        
        helper = RegexHelper(self, self.toMZCtrl.GetValue(), self.descriptionSample)
        if helper.ShowModal() == wx.ID_OK:
            self.toMZCtrl.SetValue(helper.getRegex())
        helper.Destroy()
        
    def launchScanUtility(self, event):
        if not self.descriptionSample:
            self.sampleTarget()
            
        helper = RegexHelper(self, self.toScanCtrl.GetValue(), self.descriptionSample)
        if helper.ShowModal() == wx.ID_OK:
            self.toScanCtrl.SetValue(helper.getRegex())
        helper.Destroy()
        
        
         
    def beginAnalysis(self, event):
        fileNames = [x.strip() for x in self.resultCtrl.GetValue().split(';')]
        dataFiles = [x.strip() for x in self.dataCtrl.GetValue().split(';')]
        
        global mediumK
        global mediumR
        global heavyK
        global heavyR
        global allTags
        global PLEXITY
        
        global mediumShifts
        global heavyShifts
        
        
        mediumK = self.mediumKTag.GetValue().strip()
        mediumR = self.mediumRTag.GetValue().strip()
        heavyK = self.heavyKTag.GetValue().strip()
        heavyR = self.heavyRTag.GetValue().strip()
        
        if self.customParserCheck.GetValue():
            toMZRegex = self.toMZCtrl.GetValue()
            toScanRegex = self.toScanCtrl.GetValue()
        else:
            toMZRegex = toScanRegex = None
        
        errors = []
        
        #combined = self.combinedResultsCheck.GetValue()
        #if combined and len(dataFiles) == 1:
            #errors.append("Only one MS data file should be selected for non-combined analysis; multiplierz found %d" % len(dataFiles))
        
        try:
            featureTolerance = float(self.toleranceCtrl.GetValue())    
        except ValueError as err:
            errors.append('PPM tolerance must be a specified as a floating-point number.  (10 is often a good value.)')
            featureTolerance = None
            
        
            


            
        #snThreshold = int(self.snCtrl.GetValue())
        
        constantsDict = {'mzRegex' : toMZRegex,
                         'scanRegex' : toScanRegex,
                         'tolerance' : featureTolerance}
                         #'signalNoiseThreshold' : snThreshold}
        if not toMZRegex:
            del constantsDict['mzRegex']
        if not toScanRegex:
            del constantsDict['scanRegex']
        
        if (not mediumK) and (not mediumR):
            PLEXITY = 2
            allTags = [heavyK, heavyR]
        else:
            PLEXITY = 3
            allTags = [mediumK, mediumR, heavyK, heavyR]
            
        
        if not ((mediumK and mediumR) or
                ((not mediumK) and (not mediumR))):
            errors.append("Both (for 3-plex SILAC) or neither (for "
                          "2-plex SILAC) medium tags must be specified.")
        
        if not all([os.path.exists(x) for x in fileNames]):
            errors.append("Could not find input files: "
                          "%s" % ' '.join([x for x in fileNames if not os.path.exists(x)]))
        
        if not all([os.path.exists(x) for x in dataFiles]):
            errors.append("Could not find MS data files: "
                          "%s" % ' '.join([x for x in dataFiles if not os.path.exists(x)]))            
            
        
        if errors:
            errDlg = wx.MessageDialog(self, 'Found %d errors:\n\n' % len(errors) + '\n\n'.join(errors),
                                      'Multiplierz encountered an error', style = wx.OK)
            errDlg.ShowModal()
            raise RuntimeError
            
            
        wx.BeginBusyCursor()
        try:
            if mediumK:
                PLEXITY = 3
                allTags = [mediumK, mediumR, heavyK, heavyR]
            else:
                PLEXITY = 2
                allTags = [heavyK, heavyR]
                
            print "Running SILAC analysis with plexity %s." % PLEXITY
            print "SILAC tag literals are: %s" % str(allTags)
            
            self.goButton.Enable(False)
            
            if PLEXITY == 3:
                async.launch_process(SILAC3Plex, None, 
                                     dataFiles, fileNames, mediumTags = [mediumK, mediumR],
                                     heavyTags = [heavyK, heavyR], **constantsDict)
            else:
                async.launch_process(SILAC2Plex, None,
                                     dataFiles, fileNames, heavyTags = [heavyK, heavyR],
                                     **constantsDict)            
                
            self.goButton.Enable(True)             
        finally:
            wx.EndBusyCursor()
                
        
                
                
if __name__ == '__main__':
    app = wx.App(0)
    SILACSession(None, "SILAC Analysis Tool")
    app.MainLoop()