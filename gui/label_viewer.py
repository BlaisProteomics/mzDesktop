from multiplierz.mzAPI import mzFile
from multiplierz.mzAPI.mzMemo import async_mzFile
from multiplierz.mzReport import reader, writer
from multiplierz.mzTools.featureUtilities import save_feature_database, FeatureInterface
from multiplierz.internalAlgorithms import collectByCriterion, multisplit
from multiplierz.mzTools.featureDetector import Feature
from multiplierz.mgf import standard_title_parse
from numpy import average, sqrt
from string import letters
import os

import wx
from gui import BasicTab

import re
from numpy import average, isnan, median, arange
from collections import defaultdict

import matplotlib
from matplotlib.figure import Figure
from matplotlib.ticker import FormatStrFormatter

matplotlib.use('WXAgg')
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas

import wx.lib.newevent

from time import clock
before = clock()

tolerance = 0.03

largenum = 3000

silacIndicator = 'Label'

gene_column = 'gene_symbols'
silac_ratio_key_heavy = 'Overlap Ratio (H/L)'
silac_ratio_key_medium = 'Overlap Ratio (M/L)'

isobaricTypes = {4:'iTRAQ', 6:'TMT', 8:'iTRAQ', 10:'TMT'}

parentheticalGetter = re.compile(r'(?<=\()[0-9](?=\))')

def safediv(a, b):
    return a/float(b) if b else None

defaultSortModes = ['Score', 'PSM Count']
isobaricSortModes = []
silacSortModes = []


reportersByPlexity = {4 : [114.11, 115.11, 116.11, 117.12],
                      6 : [126.127, 127.131, 128.134, 129.138, 130.141, 131.138],
                      8 : [113.11, 114.11, 115.11, 116.11,
                           117.12, 118.12, 119.12, 121.12],
                      10 : ['126', '127N', '127C', '128N', '128C',
                            '129N', '129C', '130N', '130C', '131']}

actual10PlexIons = [126.127726, 127.124761, 127.131081, 128.128116, 128.134436,
                    129.131471, 129.137790, 130.134825, 130.141145, 131.138180]

def parsePeptide(psm):
    if psm['Variable Modifications']:
        mods = [x for x in psm['Variable Modifications'].split('; ') if silacIndicator not in x]
    else:
        mods = ''
    return psm['Peptide Sequence'], '; '.join(mods), str(psm['Charge'])


reporterColumns = None
def readIsobaricReporters(psm, plexity):
    labels = [str(round(x)) if isinstance(x, float) else str(x) for x in reportersByPlexity[plexity]]
    
    global reporterColumns
    if not (reporterColumns and all([x in psm for _, x in reporterColumns])):
        if all([any([l.lower() in x.lower() for x in psm.keys()]) for l in labels]):
            reporterColumns = []
            for label in labels:
                cols = [x for x in psm.keys() if label in x]
                # In case there's more than one, the reporter ion intensity is likely
                # to be higher than the experimental mz or whatever.
                reporterColumns.append((label, max(cols, key = lambda x: psm[x])))
            print "Found reporter ion columns %s" % '; '.join(['-'.join(x) for x in reporterColumns])
        else:
            reporterColumns = None
            
    if reporterColumns:
        return [psm[x] for _, x in reporterColumns]
    else:
        if 'MultiplierzMGF' in psm['Spectrum Description']:
            attrib = standard_title_parse(psm['Spectrum Description'])
            if plexity == 10:
                labelnames = reportersByPlexity[10]
            else:
                labelnames = [str(int(x)) for x in reportersByPlexity[plexity]]
            
            reporters = [float(attrib[x]) for x in labelnames]
        else:
            words = psm['Spectrum Description'].split('-')[-1].split('|')
            reporters = [float(x) for x in words if x.strip(' _' + letters)][:plexity]
        
        return reporters
    
def scanFromDesc(desc):
    # Also placeholder!  Real version should deal with new spectrum descriptions,
    # and check for overriding parse rule.
    words = desc.split('|')
    if words[1] == 'MultiplierzMGF':
        scanword = [x for x in words if 'scan' in x.lower()][0]
        return int(scanword.split(':')[1])
    else:
        # Classic mode description parser.
        return int(desc.split('.')[1])


def calculateShift(peptide,
                   hevKMass, hevRMass,
                   medKMass = None, medRMass = None):
    rcount = peptide.count('R')
    kcount = peptide.count('K')
    
    lightHeavyShift = hevKMass*kcount + hevRMass * rcount
    
    if medKMass and medRMass:
        lightMediumShift = medKMass*kcount + medRMass * rcount
        mediumHeavyShift = lightHeavyShift - lightMediumShift
        return [lightHeavyShift, lightMediumShift, mediumHeavyShift]
    else:
        return lightHeavyShift
    
 
def ratioSetForPSMs(psms, settings):
    ratios = defaultdict(list)
    for psm in psms:
        if settings['type'] == 'SILAC':
            #heavyRats = average([psm[silac_ratio_key_heavy] for psm in psms])
            ratios['heavy'].append(psm[silac_ratio_key_heavy])
            if settings['plex'] > 2:
                ratios['medium'].append(psm[silac_ratio_key_medium])
        elif settings['type'] == 'isobaric':
            ratioChannels = settings['ratios']
            reporters = readIsobaricReporters(psm, settings['plex'])
            corrections = settings['ionCorrections']
            for nom, den in ratioChannels:
                nomCor = corrections[nom]
                denCor = corrections[den]
                ratios[nom, den].append(safediv(reporters[nom]*nomCor,
                                                reporters[den]*denCor))
        else:
            assert settings['type'] == 'none'
            ratios = {}
    
        
                
    return ratios
            
    

def deriveAllMZs(peptide, chg, 
                 lightmz, mediummz, heavymz,
                 hRMass, hKMass, mRMass = None, mKMass = None):
    if not (mRMass or mKMass):
        mediummz = False
        lightheavyshift = calculateShift(peptide, hKMass, hRMass)
    else:
        (lightheavyshift, lightmediumshift,
         mediumheavyshift) = calculateShift(peptide, hKMass, hRMass, mKMass, mRMass)
    
    if not lightmz or isnan(lightmz):
        if mediummz:
            lightmz = massToMZ(mzToMass(mediummz, chg) - lightmediumshift, chg)
        if heavymz:
            lightmz = massToMZ(mzToMass(heavymz, chg) - lightheavyshift, chg)
    if mediummz != False and (not mediummz or isnan(mediummz)):
        if lightmz:
            mediummz = massToMZ(mzToMass(lightmz, chg) + lightmediumshift, chg)
        elif heavymz:
            mediummz = massToMZ(mzToMass(heavymz, chg) - mediumheavyshift, chg)
    if not heavymz or isnan(heavymz):
        if lightmz:
            heavymz = massToMZ(mzToMass(lightmz, chg) + lightheavyshift, chg)
        if mediummz:
            heavymz = massToMZ(mzToMass(mediummz, chg) + mediumheavyshift, chg)    
            
    assert not any([isnan(x) for x in [lightmz, mediummz, heavymz]])
    
    return lightmz, mediummz, heavymz

proton = 1.00727647
     
def mzToMass(mz, chg):
    return (mz * chg) - (chg * proton)

def massToMZ(mass, chg):
    return (mass + (chg * proton)) / chg
    


        
def calculateProteinRatios(psms, settings):
    # Returns string with appropriate ratio data.
    if settings['type'] == 'SILAC':
        heavyRatios = [float(x[silac_ratio_key_heavy]) for x in psms 
                       if x[silac_ratio_key_heavy] != '-']
        heavyRatAvg, heavyRatMed = (round(average(heavyRatios), 2),
                                    round(median(heavyRatios), 2))
        if settings['plex'] > 2:
            mediumRatios = [float(x[silac_ratio_key_medium]) for x in psms 
                       if x[silac_ratio_key_medium] != '-']
            mediumRatAvg, mediumRatMed = (round(average(mediumRatios), 2),
                                          round(average(mediumRatios), 2))
            
            ratioString = ("(M/L: Avg. %s, Med. %s) (H\L: Avg. %s Med. %s)"
                           % (mediumRatAvg, mediumRatMed, heavyRatAvg, heavyRatMed))
            ratioDict = dict(medium = mediumRatAvg, heavy = heavyRatAvg)
        else:
            ratioString = ("(H\L: Avg. %s Med. %s)" % (heavyRatAvg, heavyRatMed))
            ratioDict = dict(heavy = heavyRatAvg)
    
    elif settings['type'] == 'isobaric':
        reporterIntList = [readIsobaricReporters(x, settings['plex']) for x in psms]
        corrections = settings['ionCorrections']
        reporterInts = [sum(x) * c for x, c in zip(zip(*reporterIntList), corrections)]
        targetRats = settings['ratios']
        
        # Currently takes the ratio of summed reporters;
        # could instead take the average of individual scan ratios?
        
        ratios = [(x, y, reporterInts[x]/reporterInts[y] if reporterInts[y] else None)
                  for x, y in targetRats]
        
        ratioString = ' '.join(['(%s/%s: %0.2f)' % (z, y, r) for (z, y, r) in ratios if r])
        ratioDict = dict([((x, y), r) for (x, y, r) in ratios])
    
    else:
        ratioString = ''
        ratioDict = {}
    
    return ratioString, ratioDict
        
        

def collectAndAnnotatePSMs(allProteinPsms, settings):
    if settings['type'] == 'SILAC':        
        if settings['plex'] == 2:
            def pepRatioStr(psms):
                heavyRatios = [float(x[silac_ratio_key_heavy]) for x in psms 
                               if x[silac_ratio_key_heavy] != '-']
                heavyRatio = average(heavyRatios) if heavyRatios else '-'   
                barePepStr = '|'.join([str(x) for x in parsePeptide(psms[0])])
                if isinstance(heavyRatio, float):
                    return "%s (H/L: %.2f)" % (barePepStr, heavyRatio)
                else:
                    return "%s (H/L: %s)" % (barePepStr, heavyRatio)
                
            def psmRatioStr(psm): 
                if isinstance(psm[silac_ratio_key_heavy], float):
                    return "%s (Score: %s)" % (scanFromDesc(psm['Spectrum Description']),
                                                          psm['Peptide Score'])	
                else:
                    return "%s (Score: %s)" % (scanFromDesc(psm['Spectrum Description']),
                                                          psm['Peptide Score'])	                    
        else:
            def pepRatioStr(psms):
                heavyRatios = [float(x[silac_ratio_key_heavy]) for x in psms 
                               if x[silac_ratio_key_heavy] != '-']
                heavyRatio = ('%.2f' % average(heavyRatios)) if heavyRatios else '-'                
                mediumRatios = [float(x[silac_ratio_key_medium]) for x in psms 
                                if x[silac_ratio_key_medium] != '-']            
                mediumRatio = ('%.2f' % average(mediumRatios)) if mediumRatios else float('NaN')
                barePepStr = '|'.join([str(x) for x in parsePeptide(psms[0])])
                return "%s (H/L: %s) (M/L %s)" % (barePepStr, heavyRatio, mediumRatio)
            def psmRatioStr(psm):
                return "%s (Score: %s)" % (str(scanFromDesc(psm['Spectrum Description'])),
                                            psm['Peptide Score'])
        
    elif settings['type'] == 'isobaric':
        def pepRatioStr(psms):
            reporterIntList = [readIsobaricReporters(x, settings['plex']) for x in psms]
            corrections = settings['ionCorrections']
            reporterInts = [sum(x) * c for x, c in zip(zip(*reporterIntList), corrections)]
            targetRats = settings['ratios']
            # Currently takes the ratio of summed reporters;
            # could instead take the average of individual scan ratios?
            ratios = [(x, y, safediv(reporterInts[x], reporterInts[y])) for x, y in targetRats]            
            barePepStr = '|'.join([str(x) for x in parsePeptide(psms[0])])
            return barePepStr + ' ' + ' '.join(['(%s/%s: %0.2f)' % (z+1, y+1, r) for (z, y, r) in ratios if r])
        
        def psmRatioStr(psm):
            reporterInts = readIsobaricReporters(psm, settings['plex'])
            corrections = settings['ionCorrections']
            reporterInts = [x * c for x, c in zip(reporterInts, corrections)]
            ratios = [(x, y, safediv(reporterInts[x], reporterInts[y])) for x, y in settings['ratios']]
            
            return (str(scanFromDesc(psm['Spectrum Description'])) +
                    ' Score: %s ' % psm['Peptide Score'] +
                    ' '.join(['(%s/%s: %0.2f)' % (z+1, y+1, r) for (z, y, r) in ratios if r]))
    
    else:
        assert settings['type'] == 'none'
        def pepRatioStr(psms):
            return '|'.join([str(x) for x in parsePeptide(psms[0])])
        def psmRatioStr(psm):
            return (str(scanFromDesc(psm['Spectrum Description'])) +
                    ' Score: %s' % psm['Peptide Score'])
    
    
    if 'source' in allProteinPsms[0]:
        def sourcePrefix(psm):
            return psm['Spectrum Description'].split('.')[0] + ' '
    else:
        def sourcePrefix(psm):
            return ''
    
    psmsByPeptide = collectByCriterion(allProteinPsms, lambda x: parsePeptide(x))
    
    for pep, psms in psmsByPeptide.items():
        pepstr = pepRatioStr(psms)
        for psm in psms:
            psm['peptide string'] = pepstr
            psm['psm string'] = sourcePrefix(psm) + psmRatioStr(psm)
            assert psm['peptide string']
            assert psm['psm string']
    
    return psmsByPeptide
    
            
defaultSettings = {'type':'none',
                   'plex':2, # 2 or 3 for SILAC, 4 through 10 for TMT.
                   'ionCorrections':None, # Ion-ratio dict.
                   'ratios':None,
                   'heavyR':None,
                   'heavyK':None,
                   'mediumR':None,
                   'mediumK':None}  

#defaultSettings = {'type':'SILAC',
                   #'plex':2, # 2 or 3 for SILAC, 4 through 10 for TMT.
                   #'ionCorrections':None, # Ion-ratio dict.
                   #'ratios':None,
                   #'heavyR':'Label:13C(6)15N(4)',
                   #'heavyK':'Label:13C(6)15N(2)',
                   #'mediumR':None,
                   #'mediumK':None}    
    
class LabelSettingsDialog(wx.Dialog):
    def __init__(self, parent = None, settings = None):
        super(LabelSettingsDialog, self).__init__(parent, title = 'Label Viewer Settings')
        if not settings:
            self.settings = defaultSettings
        else:
            self.settings = settings
        
        self.selectMode = wx.RadioBox(self, -1, "Label Mode", choices = ['None',
                                                                         "SILAC 2-Plex",
                                                                         "SILAC 3-Plex",
                                                                         "iTRAQ 4-plex",
                                                                         "TMT 6-plex",
                                                                         "iTRAQ 8-plex",
                                                                         "TMT 10-plex"],
                                                              majorDimension = 7,
                                                              style = wx.RA_SPECIFY_ROWS)
        self.Bind(wx.EVT_RADIOBOX, self.enableRelevantControls, self.selectMode)
        
        silacLabel = wx.StaticText(self, -1, "SILAC")
        self.silacMKLabel = wx.StaticText(self, -1, "Medium K Label")
        self.silacHKLabel = wx.StaticText(self, -1, "Heavy K Label")
        self.silacMRLabel = wx.StaticText(self, -1, "Medium R Label")
        self.silacHRLabel = wx.StaticText(self, -1, "Heavy R Label")        
        self.silacMKCtrl = wx.TextCtrl(self, -1, value = 'Label:2H(4)')
        self.silacHKCtrl = wx.TextCtrl(self, -1, value = 'Label:13C(6)15N(2)')
        self.silacMRCtrl = wx.TextCtrl(self, -1, value = 'Label:13C(6)')
        self.silacHRCtrl = wx.TextCtrl(self, -1, value = 'Label:13C(6)15N(4)') 
        self.silacControls = [silacLabel, self.silacHKCtrl, self.silacHRCtrl,
                              self.silacMKCtrl, self.silacMRCtrl,
                              self.silacMKLabel, self.silacHKLabel,
                              self.silacMRLabel, self.silacHRLabel]
        
        isobaricLabel = wx.StaticText(self, -1, "Isobaric Label")
        correctionLabel = wx.StaticText(self, -1, "Channel Correction Factors")
        self.corrControls = []
        for i in range(10):
            corLabel = wx.TextCtrl(self, -1, '', size = (50, -1),
                                   style = wx.TE_READONLY | wx.BORDER_NONE | wx.TE_CENTRE)
            corControl = wx.TextCtrl(self, -1, '', size = (50, -1))
            self.corrControls.append((i, corLabel, corControl))
        ratioSpecLabel = wx.StaticText(self, -1, "Ratios of Interest")
        self.ratioSpecControl = wx.TextCtrl(self, -1, '', style = wx.TE_MULTILINE)
        self.isobaricControls = ([isobaricLabel, correctionLabel, ratioSpecLabel, self.ratioSpecControl]
                                 + list(zip(*self.corrControls)[1]) + list(zip(*self.corrControls)[2]))
        
        self.okButton = wx.Button(self, -1, 'OK')
        self.Bind(wx.EVT_BUTTON, self.onOK, self.okButton)
        
        self.overBox = wx.BoxSizer(wx.VERTICAL)
        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.silacS = wx.GridBagSizer(5, 5)
        self.isoS = wx.GridBagSizer(5, 5)
        
        self.silacS.Add(silacLabel, (0, 1), flag = wx.ALIGN_CENTRE)
        self.silacS.Add(self.silacMKLabel, (2, 0), flag = wx.ALIGN_RIGHT)
        self.silacS.Add(self.silacMRLabel, (3, 0), flag = wx.ALIGN_RIGHT)
        self.silacS.Add(self.silacHKLabel, (4, 0), flag = wx.ALIGN_RIGHT)
        self.silacS.Add(self.silacHRLabel, (5, 0), flag = wx.ALIGN_RIGHT)
        self.silacS.Add(self.silacMKCtrl, (2, 1), span = (1, 2), flag = wx.ALIGN_LEFT)
        self.silacS.Add(self.silacMRCtrl, (3, 1), span = (1, 2), flag = wx.ALIGN_LEFT)
        self.silacS.Add(self.silacHKCtrl, (4, 1), span = (1, 2), flag = wx.ALIGN_LEFT)
        self.silacS.Add(self.silacHRCtrl, (5, 1), span = (1, 2), flag = wx.ALIGN_LEFT)
        
        
        corBox = wx.GridBagSizer(5, 5)
        for i, corLabel, corControl in self.corrControls:
            corBox.Add(corLabel, (0, i), flag = wx.EXPAND)
            corBox.Add(corControl, (1, i), flag = wx.EXPAND)
        self.isoS.Add(isobaricLabel, (0, 1), flag = wx.ALIGN_CENTRE)
        self.isoS.Add(correctionLabel, (2, 0), flag = wx.ALIGN_LEFT)
        self.isoS.Add(corBox, (3, 0), span = (1, 3), flag = wx.EXPAND)
        self.isoS.Add(ratioSpecLabel, (5, 0), flag = wx.ALIGN_LEFT)
        self.isoS.Add(self.ratioSpecControl, (6, 0), span = (3, 3), flag = wx.EXPAND)
        
        line1 = wx.StaticLine(self, -1, style = wx.LI_VERTICAL)
        line2 = wx.StaticLine(self, -1, style = wx.LI_VERTICAL)
        #print line1.IsVertical()
        #print line2.IsVertical()
        self.sizer.Add(self.selectMode, 0, wx.ALL | wx.EXPAND, 20)
        self.sizer.Add(line1, 0.1, wx.ALL | wx.EXPAND, 5)
        self.sizer.Add(self.silacS, 1, wx.ALL | wx.EXPAND, 20)
        self.sizer.Add(line2, 0.1, wx.ALL | wx.EXPAND, 5)
        self.sizer.Add(self.isoS, 2, wx.ALL | wx.EXPAND, 20)
        
        self.overBox.Add(self.sizer, 1, wx.ALL|wx.EXPAND)
        self.overBox.Add(self.okButton, 0, wx.ALL | wx.ALIGN_RIGHT, 20)
        
        self.SetSizerAndFit(self.overBox)
        
        
        if self.settings['type'] == 'SILAC':
            selection = 'SILAC 2-Plex' if self.settings['plex'] == 2 else 'SILAC 3-Plex'
        elif self.settings['type'] == 'isobaric':
            plex = self.settings['plex']
            if plex == 4: selection = "iTRAQ 4-plex"
            elif plex == 6: selection = "TMT 6-plex"
            elif plex == 8: selection = "iTRAQ 8-plex"
            elif plex == 10: selection = "TMT 10-plex"
        elif self.settings['type'] == 'none':
            selection = 'None'
            
        self.selectMode.SetSelection(self.selectMode.FindString(selection))
        self.enableRelevantControls(None)
        if selection in ['SILAC 3-Plex', 'SILAC 2-Plex']:
            self.silacHRCtrl.SetValue(self.settings['heavyR'])
            self.silacHKCtrl.SetValue(self.settings['heavyK'])
            if self.settings['type'] == 'SILAC 2-Plex':
                self.silacMKCtrl.SetValue(self.settings['mediumK'])
                self.silacMRCtrl.SetValue(self.settings['mediumR'])
        elif selection in ["iTRAQ 4-plex", "TMT 6-plex", "iTRAQ 8-plex", "TMT 10-plex"]:
            for value, (index, _, ctrl) in zip(self.settings['ionCorrections'], self.corrControls):
                ctrl.SetValue(str(value))
            self.ratioSpecControl.SetValue('; '.join(['/'.join([str(x+1) for x in xs]) for xs in self.settings['ratios']]))
            # Adding one because channels should be represented as 1-indexed.
            
        

        
        
    def enableRelevantControls(self, event):
        mode = self.selectMode.GetString(self.selectMode.GetSelection())
           
        if mode in ['SILAC 3-Plex', 'SILAC 2-Plex']:
            for thing in self.isobaricControls:
                thing.Enable(False)
            for thing in self.silacControls:
                thing.Enable(True)
            if mode == 'SILAC 2-Plex':
                self.silacMKCtrl.Enable(False)
                self.silacMRCtrl.Enable(False)            
            for _, label, ctrl in self.corrControls:
                label.SetValue('-')
                ctrl.SetValue('')                   
        elif mode in ["iTRAQ 4-plex", "TMT 6-plex", "iTRAQ 8-plex", "TMT 10-plex"]:
            for thing in self.isobaricControls:
                thing.Enable(True)
            for thing in self.silacControls:
                thing.Enable(False)
                
            plexity = int(mode.split('-')[0].split(' ')[-1])
            ions = reportersByPlexity[plexity]
                
            for label, (_, labelWidget, ctrlWidget) in zip(ions, self.corrControls):
                labelWidget.SetValue(str(label))
                ctrlWidget.SetValue('1.0')
                labelWidget.Enable(True)
                ctrlWidget.Enable(True)
            for _, label, ctrl in self.corrControls[len(ions):]:
                label.SetValue('-')
                ctrl.SetValue('')
                ctrl.Enable(False)
        else:
            for thing in self.isobaricControls:
                thing.Enable(False)
            for thing in self.silacControls:
                thing.Enable(False)            
        
        
    def onOK(self, event):
        self.EndModal(wx.ID_OK)
    def onClose(self, event):
        self.EndModal(wx.ID_CANCEL)
        
    def retrieveSettings(self):
        settings = {}
        error = None
        mode = self.selectMode.GetString(self.selectMode.GetSelection())
        if mode in ['SILAC 3-Plex', 'SILAC 2-Plex']:
            settings['type'] = 'SILAC'
            MKTag = self.silacMKCtrl.GetValue()
            MRTag = self.silacMRCtrl.GetValue()
            HKTag = self.silacHKCtrl.GetValue()
            HRTag = self.silacHRCtrl.GetValue()

            settings['heavyR'] = HRTag
            settings['heavyK'] = HKTag            
            if mode == 'SILAC 3-Plex':
                settings['plex'] = 3
                settings['mediumR'] = MRTag
                settings['mediumK'] = MKTag
            else:
                settings['plex'] = 2
            
        elif mode in ["iTRAQ 4-plex", "TMT 6-plex", "iTRAQ 8-plex", "TMT 10-plex"]:
            settings['type'] = 'isobaric'
            corrections = []
            for index, ionLabel, ionCtrl in self.corrControls:
                if ionCtrl.Enabled:
                    #corrections.append((index, str(ionLabel.GetValue()), 
                                        #float(ionCtrl.GetValue())))
                    corrections.append(float(ionCtrl.GetValue()))
            settings['ionCorrections'] = corrections
            settings['plex'] = len(corrections)
            assert len(corrections) in [4,6,8,10]
            
            ratioStr = self.ratioSpecControl.GetValue()
            roundstr = lambda (x, y): (int(round(float(x)-1)), int(round(float(y)-1)))
            # Subtracting one to make channels 1-indexed.
            try:
                settings['ratios'] = [roundstr(xs.split('/')) for xs in multisplit(ratioStr, ' \n;,') if xs]
            except ValueError:
                error = 'Invalid ratio settings given: %s' % ratioStr
        else:
            settings = defaultSettings
        
        if not error:
            return settings
        else:
            return error
            
            
            



if __name__ == '__main__':
    app = wx.App(0)
    foo = LabelSettingsDialog(None, None)
    foo.ShowModal()


    
    
    
class plotState(object):
    def __init__(self, ax, data):
        self.ax = ax
        self.data = data
        
        self._mode = None # 'xic' or 'scan'
                
        self._rtspan = None
        self._mzwidths = None
      
        self._scan = None
        self._mzspan = None # 'scan' extent
        self.centroid = True
        
        self.annotations = []
        self.zoomstack = []
      
        
        # This data is generated by the object from the mzFile instance; unsettable.
        # These are kept as a cache to avoid unnecessary mzFile accessses.
        self._xicdata = {}
        self._scandata = None
        
    
    @property
    def mode(self):
        return self._mode
    @mode.setter
    def mode(self, mode):
        if mode != self._mode:
            if mode == 'xic':
                self.scan = None
                self.mzspan = None
                self.centroid = True
                self._scandata = []
            elif mode == 'scan':
                self.mzwidths = None
                self.rtspan = None
                self._xicdata = {}
            else:
                raise NotImplementedError, "Invalid mode: %s" % mode
            self.zoomstack = []
            self._mode = mode
    
    @property
    def mzwidths(self):
        return self._mzwidths
    @mzwidths.setter
    def mzwidths(self, widths):
        if widths != self._mzwidths:
            self._mzwidths = widths
            self._xicdata = {}
        
    @property
    def scan(self):
        return self._scan
    @scan.setter
    def scan(self, scanNum):
        if scanNum:
            print "Generating scan."
            self._scandata = self.data.scan(scanNum, centroid = self.centroid)
            self.zoomstack = [(0, self._scandata[-1][0])] # This may be redundant?
            # But whatever else does it doesn't seem to work for isobaric focus.
        else:
            self._scandata = []
        self._scan = scanNum
        
        
    @property        
    def xic_data(self):
        xics = []
        # Don't cache attributes, just in case the same width somehow
        # comes up in a different context.
        for start, stop, attrib in self.mzwidths:
            if ((start, stop) in self._xicdata and 
                self._xicdata[start, stop][0][0] <= self.rtspan[0] and
                self._xicdata[start, stop][-1][0] >= self.rtspan[1]):
                xics.append((self._xicdata[start, stop], attrib))
            else:
                print "Generating XIC."
                xicstart = clock()
                left, right = self.rtspan[0] - 0.1, self.rtspan[1] + 0.1
                xic = self.data.xic(left, right, start, stop)
                self._xicdata[start, stop] = xic
                print clock() - xicstart
                xics.append((xic, attrib))
        
        return xics
                
        #xics = []
        #for index, xicdata in enumerate(self._xicdata):
            #if xicdata[0][0] <= self.rtspan[0] and xicdata[-1][0] >= self.rtspan[1]:
                #xics.append([x for x in xicdata if self.rtspan[0] <= x[0] <= self.rtspan[1]])
            #else:
                #print "Generating XIC."
                #xic = self.data.xic(*self.rtspan + self._mzwidths[index])
                ##self._rtspan = xic[0][0], xic[-1][0]
                #self._xicdata[index] = xic
                #xics.append(xic)
        
        #assert xics
        #return xics
                
            
            
        #if (self._xicdata and
            #self._xicdata[0][0] <= self.rtspan[0] and self._xicdata[-1][0] >= self.rtspan[1]):
            #return [x for x in self._xicdata if self.rtspan[0] <= x[0] <= self.rtspan[1]]
        #else:
            #print "Generating XIC."
            #xic = self.data.xic(*self.rtspan + self._mzwidth)
            #self._rtspan = xic[0][0], xic[-1][0]
            #self._xicdata = xic
            #return xic
    
    @property
    def scan_data(self):
        # Presuming scanNum was set, there should be valid scan data.
        return [x for x in self._scandata if self.mzspan[0] <= x[0] <= self.mzspan[1]]
    
    
    @property
    def mzspan(self):
        return self._mzspan
    @mzspan.setter
    def mzspan(self, span):
        self.zoomstack.append(span)
        self._mzspan = span
        
    @property
    def rtspan(self):
        return self._rtspan
    @rtspan.setter
    def rtspan(self, span):
        self.zoomstack.append(span)
        self._rtspan = span




class PlotControl(object):
    """
    Abstract box of methods that translate settings and events from the GUI
    into plot state modifications.
    """
    
    def __init__(self, gui):
        self.gui = gui
        self.topst = None
        self.botst = None
        
    def set_states(self, topstate, botstate):
        self.topst = topstate
        self.botst = botstate
        #self.topst.mode = 'xic'
        #self.botst.mode = 'scan'
            
    
    def general_xic(self):
        self.xic([], None)
        self.gui.scanPlot.updatePlots()
        
    def scan_plot(self, scan, psm = None):
        #if peptide:
            #psms = [x for x in self.gui.proteins[protein] if parsePeptide(x) == peptide]
        #elif protein:
            #psms = [x for x in self.gui.proteins[protein]]
        #else:
            #psms = []        
        
        self.xic([psm] if psm else [], scan)
        self.spectrum(scan, psm)
        
        self.gui.scanPlot.updatePlots()
        
        
        
    def targeted_plot(self, protein, peptide, scan = None):
        psms = [x for x in self.gui.proteins[protein] if parsePeptide(x) == peptide]

        if scan:
            psm = [x for x in psms if scanFromDesc(x['Spectrum Description']) == scan][0]
            
            if 'source' in psm:
                self.gui.openData(psm['Spectrum Description'].split('.')[0] + '.raw')

            if self.gui.mode == 'SILAC':
                scan = self.gui.ms1Lookup[scan]
                lightmz, _, heavymz = self.get_silac_mzs(psms)
                range = lightmz - 5, heavymz + 5
            else:
                range = None
            self.spectrum(scan, psm, range)
            
            if self.gui.mode == 'SILAC':
                self.silac_spectrum_annotation(psms,
                                               scanFromDesc(psm['Spectrum Description']))
            elif self.gui.mode == 'isobaric':
                self.isobaric_spectrum_annotation(psm)
                
        self.xic(psms, scan)
            
        self.gui.scanPlot.updatePlots()
        
    
    def xic(self, psms, scan):
        self.topst.mode = 'xic'
        self.topst.annotations = []
        
        if psms and self.gui.mode == 'SILAC':
            lightmz, mediummz, heavymz = self.get_silac_mzs(psms)
            if self.gui.plexity == 3:
                mzs = [(lightmz, {'color':'r'}),
                       (mediummz, {'color':'g'}),
                       (heavymz, {'color':'b'})]
            else: 
                mzs = [(lightmz, {'color':'r'}), (heavymz, {'color':'b'})]
                
            self.topst.mzwidths = [(x-tolerance, x+tolerance, attrib) for x, attrib in mzs if x]            
        elif psms:
            mz = average([x['Experimental mz'] for x in psms])
            self.topst.mzwidths = [(mz-tolerance, mz+tolerance, {})]
        else:
            try:
                mz = self.gui.scanPlot.mzlookup[scan]
                if not mz: raise KeyError
                
                self.topst.mzwidths = [(mz - tolerance, mz + tolerance, {})]
            except KeyError:
                self.topst.mzwidths = [(0, 3000, {})]
        
        self.topst.rtspan = self.gui.data.time_range()
        if psms:
            rts = [self.gui.data.time_for_scan(scanFromDesc(x['Spectrum Description']))
                   for x in psms]
            self.topst.rtspan = min(rts) - 0.5, max(rts) + 0.5
            for psmrt in rts:
                self.topst.annotations.append(('PSM', 'pin', psmrt, 
                                               {'color':'b', 'alpha':0.2}))            
        else:
            if scan in self.gui.scanPlot.mzlookup:
                rt = self.gui.data.time_for_scan(scan)
                self.topst.rtspan = rt - 2, rt + 2
            # Else the time_range() span is sufficient.
        
        if scan:
            rt = self.gui.data.time_for_scan(scan)
            self.topst.annotations.append(('currentscan', 'pin', rt, {'color':'r', 'linestyle':'--'}))


        if psms and self.gui.features and 'feature' in psms[0].keys():
            features = [self.gui.features[x] for x in
                         set([psm['Feature'] for psm in psms]) if x != '-']
            for feature in features:
                featurerange = [self.gui.data.time_for_scan(x) for x in feature.scanrange]
                self.topst.annotations.append(('feature', 'range', featurerange, {'color':'k', 'alpha':0.2}))

        if psms and self.gui.mode == 'SILAC' and any(['Feature' in x for x in psms[0].keys()]):
            lightfeatures = [self.gui.features[x] for x in set([psm['Light Features'] for psm in psms])]
            heavyfeatures = [self.gui.features[x] for x in set([psm['Heavy Features'] for psm in psms])]
            try:
                mediumfeatures = [self.gui.features[x] for x in set([psm['Medium Features'] for psm in psms])]
            except KeyError:
                mediumfeatures = []

            for features, color in zip([lightfeatures, mediumfeatures, heavyfeatures], ('r', 'g', 'b')):
                for feature in features:
                    featurerange = [self.gui.data.time_for_scan(x) for x in feature.scanrange]
                    self.topst.annotations.append(('silacFeature', 'range', featurerange, {'color':color, 'alpha':0.2}))



    def spectrum(self, scan, psm = None, range = None):     
        self.botst.mode = 'scan'
        self.botst.scan = scan
        self.botst.annotations = []
        
        if not range:
            self.botst.mzspan = 0, 2000
        else:
            self.botst.mzspan = range
        self.botst.centroid = True
        
        if psm:
            self.annotations = [('precursor', 'pin', float(psm['Experimental mz']),
                                 {'color':'r', 'linestyle':'--'})]
    
    def isobaric_spectrum_annotation(self, psm):
        reporters = reportersByPlexity[self.gui.plexity] if self.gui.plexity < 10 else actual10PlexIons
        repRange = ((min(reporters)-2, max(reporters)+2)
                    if not len(reporters) == 10 else (126, 132))
        
        #ratios = zip(reporters, ratioSetForPSMs([psm], self.gui.settings))
        reporterInts = readIsobaricReporters(psm, self.gui.plexity)
        reporterInts = [x * c for x, c in zip(reporterInts, self.gui.corrections)]
        ratios = zip(reporters, reporterInts)        
        
        self.botst.mzspan = repRange
        for ion, intensity in ratios:
            self.botst.annotations.append(('ReporterIon', intensity, ion,
                                              {'color':'b', 'linewidth':5, 'alpha':0.2}))
            
        
        
    def get_silac_mzs(self, psms):
        heavytags = [self.gui.heavyK, self.gui.heavyR]
        mediumtags = [self.gui.mediumK, self.gui.mediumR]
    

        heavyPsms = [x for x in psms if
                     any([tag in x['Variable Modifications'] for tag in heavytags])]
        mediumPsms = [x for x in psms if
                      x not in heavyPsms and
                      any([str(tag) in x['Variable Modifications'] for tag in mediumtags])]        
        lightPsms = [x for x in psms if x not in heavyPsms + mediumPsms]        
    
        if lightPsms:
            lightmz = average([float(psm['Experimental mz']) for psm in lightPsms])
        else: lightmz = None
        if mediumPsms:
            mediummz = average([float(psm['Experimental mz']) for psm in mediumPsms])
        else: mediummz = None
        if heavyPsms:
            heavymz = average([float(psm['Experimental mz']) for psm in heavyPsms])        
        else: heavymz = None
    
        return deriveAllMZs(psm['Peptide Sequence'], psm['Charge'],
                            lightmz, mediummz, heavymz,
                            self.gui.heavyRMass, self.gui.heavyKMass,
                            self.gui.mediumRMass, self.gui.mediumKMass)        

        
    
    def silac_spectrum_annotation(self, psms, scan):
        heavytags = [self.gui.heavyK, self.gui.heavyR]
        mediumtags = [self.gui.mediumK, self.gui.mediumR]        
        
        mediumPsms = [x for x in psms if
                      any([str(tag) in x['Variable Modifications'] for tag in mediumtags])]
        heavyPsms = [x for x in psms if
                     any([tag in x['Variable Modifications'] for tag in heavytags])]
        lightPsms = [x for x in psms if x not in heavyPsms + mediumPsms]         
        lightmz, mediummz, heavymz = self.get_silac_mzs(psms)
        
        self.botst.annotations += [('silacMZ', 'pin', lightmz, {'color':'r', 'linestyle':'--'}),
                                   ('silacMZ', 'pin', heavymz, {'color':'b', 'linestyle':'--'})]
        if self.gui.plexity == 3:
            self.botst.annotations.append(('silacMZ', 'pin', mediummz, {'color':'g', 'linestyle':'--'}))
        
        if self.gui.features:
            lightfeatures = self.gui.getFeatures(set(sum([[f.strip() for f in x['Light Features'].split(';') if f.strip()] for x in lightPsms], [])))
            heavyfeatures = self.gui.getFeatures(set(sum([[f.strip() for f in x['Heavy Features'].split(';') if f.strip()] for x in heavyPsms], [])))
            mediumfeatures = self.gui.getFeatures(set(sum([[f.strip() for f in x['Medium Features'].split(';') if f.strip()] for x in mediumPsms], [])))
            
            def featurePeaksInScan(feature):
                try:
                    return dict(feature.regions)[self.gui.ms1Lookup[scan]] # I think?
                except KeyError:
                    return []
            lightpeaks = sum([featurePeaksInScan(x) for x in lightfeatures], [])
            mediumpeaks = sum([featurePeaksInScan(x) for x in mediumfeatures], [])
            heavypeaks = sum([featurePeaksInScan(x) for x in heavyfeatures], [])
            
            for mz, intensity in lightpeaks:
                self.botst.annotations.append(('lightFeaturePeak', intensity, mz,
                                               {'color':'r', 'linewidth':5, 'alpha':0.2}))
            for mz, intensity in mediumpeaks:
                self.botst.annotations.append(('mediumFeaturePeak', intensity, mz,
                                               {'color':'g', 'linewidth':5, 'alpha':0.2}))
            for mz, intensity in heavypeaks:
                self.botst.annotations.append(('heavyFeaturePeak', intensity, mz,
                                               {'color':'b', 'linewidth':5, 'alpha':0.2}))
            
            
                
            
        
            
        
        
        
        
        
        
    
    



class InterfacePlot(wx.Panel):
    def __init__(self, parent, ident = -1):
        wx.Panel.__init__(self, parent, ident, size = (100, 100))
        # Why does "size = (100, 100)" make the size adapt correctly?
        # It is a mystery!
        
        self.fig = Figure()
        self.ax1 = self.fig.add_subplot(211)
        self.ax2 = self.fig.add_subplot(212)
        self.ax1.get_yaxis().set_tick_params(which='both', direction='in')
        self.fig.tight_layout(pad = 0, h_pad = 0, w_pad = 0)
        
        
        self.canvas = FigureCanvas(self, -1, self.fig)
        
        wxbackground = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE)
        wxbackground = [x / 255.0 for x in wxbackground]
        self.fig.set_facecolor(wxbackground)
        #self.fig.set_facecolor((0.5, 0.5, 0.5)) # For layout testing.
        
        self.sizer = wx.BoxSizer()
        self.sizer.Add(self.canvas, -1, wx.EXPAND)
        self.SetSizer(self.sizer)
        self.Fit()
        
        self.clickBack = self.canvas.mpl_connect('button_press_event', self.mouseClick)
        self.releaseBack = self.canvas.mpl_connect('button_release_event', self.mouseRelease)
        
        self.ax1.yaxis.get_major_formatter().set_powerlimits((-1, 3))
        self.ax1.xaxis.get_major_formatter().set_powerlimits((-5, 10))        
        self.ax2.yaxis.get_major_formatter().set_powerlimits((-1, 3))
        self.ax2.xaxis.get_major_formatter().set_powerlimits((-5, 10))        
        
        self.canvas.draw()
        
        self.states = None
        self.data = None

        self.clickax = None
        self.rightclick = self.leftclick = None
        self.rightclickpixel = self.leftclickpixel = None
        
        self.scaleType = 'data'
        
    
    def setData(self, data, mzlookup, scanCallback):
        self.states = {self.ax1 : plotState(self.ax1, data), 
                       self.ax2 : plotState(self.ax2, data)}
    
        self.data = data
        #self.commissionDefaultPlot()
        self.scanback = scanCallback

        self.ax1.cla()
        self.ax2.cla()
    
        self.mzlookup = mzlookup

        
    
    def zoom(self, ax, newxspan, newyspan):
        state = self.states[ax]
        if state.mode == 'xic':
            state.rtspan = newxspan
        elif state.mode == 'scan':
            state.mzspan = newxspan
        # y-span is unused; automatically adapts from new plot.  Good enough for Xcalibur.
        self.updatePlots()
            
    
    def unzoom(self, ax):
        state = self.states[ax]
        oldspan = state.zoomstack.pop()
        try:
            newxspan = state.zoomstack.pop()
            if state.mode == 'xic':
                state.rtspan = newxspan
            elif state.mode == 'scan':
                state.mzspan = newxspan
            self.updatePlots()
        except IndexError:
            state.zoomstack.append(oldspan)
            
      
    def selectScan(self, xicax, scanax, rt, centroid = True):
        xicstate = self.states[xicax]
        scanstate = self.states[scanax]
        assert xicstate.mode == 'xic', "What?"
        scanstate.mode = 'scan'
        
        xicstate.annotations = [('currentscan', 'pin', rt, {'color':'r', 'linestyle':'--'})]
        
        scanNum = self.data.scan_for_time(rt)
        scanstate.scan = scanNum
        scanstate.mzspan = 0, largenum
        scanstate.centroid = centroid
        scanstate.annotations = []
        
        self.scanback(scanNum)
        self.updatePlots()
        
        
         
            
    def updatePlots(self):
        if not self.states:
            return 
        
        for state in self.states.values():
            if state.mode == 'xic':
                self.displayXIC(state)
            elif state.mode == 'scan':
                self.displaySpectrum(state)
            
    
    def displayXIC(self, state):
        assert state.mode == 'xic'
        
        ax = state.ax
        ax.cla()
        ax.yaxis.get_major_formatter().set_powerlimits((-1, 3))
        
        xics = state.xic_data
        dataleft, dataright = state.rtspan
        for xic, attrib in xics:
            xic = [x for x in xic if dataleft - 1 < x[0] < dataright + 1]
            if xic:
                ax.plot(zip(*xic)[0], zip(*xic)[1], **attrib)
        
        bot, top = ax.get_ylim()
        left, right = ax.get_xlim()
        for _, thing, position, appearance in state.annotations:
            if thing == 'pin':
                ax.vlines([position], [0], [top], **appearance)
            elif thing == 'range':
                ax.axvspan(*position, **appearance)
            else:
                print "Unrecognized thing: %s" % thing
                
        ax.set_ylim(0, top)
        ax.set_xlim(*state.rtspan)
        
        left, right = state.rtspan
        labelcoord = right - ((right-left)/100), top*0.99
        labeltext = ''
        for start, stop, _ in state.mzwidths:
            datafile = os.path.basename(state.data.data_file)
            labeltext += "%s XIC RT[%.2f - %.2f] MZ[%.2f - %.2f]\n" % (datafile, left, right, start, stop)
        ax.text(labelcoord[0], labelcoord[1], labeltext,
                horizontalalignment = 'right', verticalalignment = 'top', color = 'b')
        
        self.canvas.draw()
        
    
    def displaySpectrum(self, state):
        ax = state.ax
        ax.cla()
        ax.yaxis.get_major_formatter().set_powerlimits((-1, 3))
        
        assert state.mode == 'scan'
        
        scan = state.scan_data
        if scan:
            ax.vlines(zip(*scan)[0], [0] * len(scan), zip(*scan)[1])
        #else:
            #print "Empty scan."
            #return
        
        bot, top = ax.get_ylim()
        left, right = ax.get_xlim()
        #assert len(set([x[2] for x in state.annotations])) == len(state.annotations)
        highAnnotation = 0
        for _, thing, position, color in state.annotations:
            if thing == 'pin':
                ax.vlines([position], [bot], [top], **color)
            elif thing == 'range':
                ax.axvspan(*position + color)
            elif isinstance(thing, float):
                if thing > highAnnotation: highAnnotation = thing
                ax.vlines([position], [bot], [thing], **color)                
            else:
                print "Unrecognized thing: %s" % thing
                
        if highAnnotation and not self.scaleType == 'data':
            top = highAnnotation * 1.2
        ax.set_ylim(0, top)
            
        if state.mzspan[1] != largenum:
            #ax.set_xlim(state.mzspan)
            left, right = state.mzspan
        else:
            left = state.mzspan[0]
            rightmost = scan[-1][0]
            right = rightmost + ((rightmost - left) / 10)
        
        labelcoord = right - ((right-left)/100), top*0.99
        scantype = 'MS2' if state.scan in self.mzlookup else 'MS1'
        if scantype == 'MS2':
            prec = self.mzlookup[state.scan]
            ax.text(labelcoord[0], labelcoord[1],
                    "%s Scan %d at MZ %.2f (%.2f - %.2f)" % (scantype, state.scan, prec, left, right),
                    horizontalalignment = 'right', verticalalignment = 'top', color = 'b')
            ax.vlines([prec], [bot], [top], linestyle = '--', color = 'r')
        else:
            ax.text(labelcoord[0], labelcoord[1],
                    "%s Scan %d (%.2f - %.2f)" % (scantype, state.scan, left, right),
                    horizontalalignment = 'right', verticalalignment = 'top', color = 'b')            
        
        ax.set_xlim(left, right)
        
        self.canvas.draw()    
        
    
    def mouseClick(self, event):
        button = event.button
        ax = event.inaxes
        if not ax:
            #print "Out of bounds."
            return
        
        #print button, ax
        if button == 1:
            self.leftclick = event.xdata, event.ydata
            self.leftclickpixel = event.x, event.y
            self.clickax = ax
        elif button == 3:
            self.rightclick = event.xdata, event.ydata
            self.rightclickpixel = event.x, event.y
            self.clickax = ax
            
    
    def mouseRelease(self, event):
        if not self.clickax:
            return
        if not event:
            raise NotImplementedError, "What?"
        button = event.button
        ax = event.inaxes       
        if not ax == self.clickax:
            self.clickax = None
            self.rightclick = self.leftclick = None
            self.rightclickpixel = self.leftclickpixel = None     
            return
        

        def euclidean(first, second):
            return sqrt((first[0] - second[0])**2 + (first[1] - second[1])**2)
        
        if button == 1:
            pixel = event.x, event.y
            distance = euclidean(pixel, self.leftclickpixel)
            if distance > 5:
                # Zoom on current graph.
                
                top = max(event.ydata, self.leftclick[1])
                bot = 0
                left = min(event.xdata, self.leftclick[0])
                right = max(event.xdata, self.leftclick[0])
                
                #print 'Zoom'
                self.zoom(ax, (left, right), None)
            
            elif self.states[ax].mode == 'xic':
                # Display scan at selected RT.
                otherAx = [x for x in self.states.keys() if x != ax][0]
                #print 'Select'
                self.selectScan(ax, otherAx, event.xdata)
        
        elif button == 3:
            #print 'Unzoom'
            self.unzoom(ax)
                
                    
    def resetXICRT(self, *etc):
        for state in self.states.values():
            if state.mode == 'xic':
                state.rtspan = state.data.time_range()
                self.displayXIC(state)
    
    def resetXICMZ(self, *etc):
        for state in self.states.values():
            if state.mode == 'xic':
                state.mzwidths = [(0, largenum)]
                self.displayXIC(state)














class LabelPanel(BasicTab):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)
        
        self.set_status("Initializing...", 0)
        self.set_status("", 1)
        
        self.entrySelector = wx.TreeCtrl(self, -1, size = (350, -1),
                                         style = wx.TR_LINES_AT_ROOT | wx.TR_HIDE_ROOT | wx.TR_TWIST_BUTTONS | wx.TR_HAS_BUTTONS)
        self.ratioPlot = BoxPlotter(self, -1)
        #self.xicPlot = InterfacePlot(self, -1)
        #self.peakPlot = InterfacePlot(self, -1)
        self.scanPlot = InterfacePlot(self, -1)
        self.plotControl = PlotControl(self)
        
        #self.Bind(EVT_InterfaceClick, self.xicClick, self.scanPlot)
        
        #self.Bind(wx.EVT_TREE_SEL_CHANGED, self.render, self.entrySelector)
        self.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.render, self.entrySelector)
        
        self.resultLabel = wx.StaticText(self, -1, 'Search Result File')
        self.resultSelector = wx.TextCtrl(self, -1)
        self.resultBrowse = wx.Button(self, -1, "Browse")
        self.featureLabel = wx.StaticText(self, -1, 'Feature File')
        self.featureSelector = wx.TextCtrl(self, -1)
        self.featureBrowse = wx.Button(self, -1, "Browse")
        self.dataLabel = wx.StaticText(self, -1, 'Data File')
        self.dataSelector = wx.TextCtrl(self, -1)
        self.dataBrowse = wx.Button(self, -1, "Browse")
        
        self.Bind(wx.EVT_BUTTON, self.getResult, self.resultBrowse)
        self.Bind(wx.EVT_BUTTON, self.getFeatureDB, self.featureBrowse)
        self.Bind(wx.EVT_BUTTON, self.getData, self.dataBrowse)
        
        #self.parseLabel = wx.StaticText(self, -1, "Spectrum Description Parser")
        #self.parseCtrl = wx.TextCtrl(self, -1, value = "Default")
        #self.parseUtility = wx.Button(self, -1, 'Regex Utility')
        
        self.searchCtrl = wx.TextCtrl(self, -1)
        self.searchType = wx.ComboBox(self, -1, choices = ['Accession', 'Peptide'])
        self.searchButton = wx.Button(self, -1, "Filter", size = (50, -1))

        self.sortCtrl = wx.ComboBox(self, -1, choices = defaultSortModes)
        self.sortButton = wx.Button(self, -1, "Sort", size = (50, -1))
        
        self.Bind(wx.EVT_BUTTON, self.updateData, self.searchButton)
        self.Bind(wx.EVT_BUTTON, self.updateData, self.sortButton)

         
        self.launchSettingsDialog = wx.Button(self, -1, "Label Settings")
        self.Bind(wx.EVT_BUTTON, self.updateSettings, self.launchSettingsDialog)
        self.modeIndicator = wx.TextCtrl(self, -1, "No mode selected.", 
                                         style = wx.TE_READONLY)
        
        
        self.scanLArrow = wx.Button(self, -1, "<", size = (20, -1))
        self.currentScan = wx.TextCtrl(self, -1, size = (50, -1), style = wx.TE_CENTRE | wx.TE_PROCESS_ENTER)
        self.scanRArrow = wx.Button(self, -1, ">", size = (20, -1))
        
        self.ms1LArrow = wx.Button(self, -1, "<MS1", size = (40, -1))
        self.ms1RArrow = wx.Button(self, -1, "MS1>", size = (40, -1))
        
        self.Bind(wx.EVT_BUTTON, self.ms1Left, self.ms1LArrow)
        self.Bind(wx.EVT_BUTTON, self.scanLeft, self.scanLArrow)
        self.Bind(wx.EVT_TEXT_ENTER, self.reselectScan, self.currentScan)
        self.Bind(wx.EVT_BUTTON, self.scanRight, self.scanRArrow)
        self.Bind(wx.EVT_BUTTON, self.ms1Right, self.ms1RArrow)
        
        
        self.scaleControl = wx.ComboBox(self, -1, choices = ['Scale to Data', 'Scale to Label'],
                                        value = 'Scale to Data')
        self.Bind(wx.EVT_COMBOBOX, self.setScaleType, self.scaleControl)
        
        self.gb = wx.GridBagSizer(10, 10)
        self.controlBox = wx.GridBagSizer(10, 10)
        self.searchBox = wx.GridBagSizer(1, 1)
        self.settingsBox = wx.GridBagSizer(10, 10)
        
        self.controlBox.Add(self.dataLabel, (0, 0), flag = wx.ALIGN_RIGHT)
        self.controlBox.Add(self.dataSelector, (0, 1), (1, 4), flag = wx.ALIGN_LEFT | wx.EXPAND)
        self.controlBox.Add(self.dataBrowse, (0, 5), flag = wx.EXPAND)
        self.controlBox.Add(self.resultLabel, (1, 0), flag = wx.ALIGN_RIGHT)
        self.controlBox.Add(self.resultSelector, (1, 1), (1, 4), flag = wx.ALIGN_LEFT | wx.EXPAND)
        self.controlBox.Add(self.resultBrowse, (1, 5), flag = wx.EXPAND)
        self.controlBox.Add(self.featureLabel, (0, 6), flag = wx.ALIGN_RIGHT)
        self.controlBox.Add(self.featureSelector, (0, 7), (1, 4), flag = wx.ALIGN_LEFT | wx.EXPAND)
        self.controlBox.Add(self.featureBrowse, (0, 11), flag = wx.EXPAND)
        self.controlBox.Add(self.modeIndicator, (1, 6), (1, 5), flag = wx.EXPAND)
        self.controlBox.Add(self.launchSettingsDialog, (1, 11), flag = wx.EXPAND)
        self.controlBox.AddGrowableCol(2)
        self.controlBox.AddGrowableCol(8)        
        self.gb.Add(self.controlBox, (0, 0), (2, 10), flag = wx.EXPAND)
        
        self.searchBox.Add(self.searchCtrl, (0, 0), flag = wx.EXPAND)
        self.searchBox.Add(self.searchType, (0, 1))
        self.searchBox.Add(self.searchButton, (0, 2), flag = wx.ALIGN_LEFT)
        self.searchBox.Add(self.sortCtrl, (1, 0), span = (1, 2), flag = wx.EXPAND)
        self.searchBox.Add(self.sortButton, (1, 2), flag = wx.ALIGN_LEFT)
        self.searchBox.AddGrowableCol(0)
        self.gb.Add(self.searchBox, (2, 0), (1, 3), flag = wx.EXPAND)
        

        scrollerBox = wx.BoxSizer(wx.HORIZONTAL)
        scrollerBox.Add(self.ms1LArrow, 0, wx.ALL | wx.ALIGN_RIGHT, 10)
        scrollerBox.Add(self.scanLArrow, 0, wx.ALL | wx.ALIGN_RIGHT, 10)
        scrollerBox.Add(self.currentScan, 1, wx.TOP | wx.ALIGN_CENTER_HORIZONTAL, 10)
        scrollerBox.Add(self.scanRArrow, 0, wx.ALL | wx.ALIGN_LEFT, 10)
        scrollerBox.Add(self.ms1RArrow, 0, wx.ALL | wx.ALIGN_RIGHT, 10)

        self.gb.Add(self.entrySelector, (3, 0), (11, 3), flag = wx.EXPAND)
        self.gb.Add(self.ratioPlot, (2, 3), (12, 1), flag = wx.EXPAND)
        #self.gb.Add(self.xicPlot, (2, 4), (5, 6), flag = wx.EXPAND)
        #self.gb.Add(self.peakPlot, (7, 4), (6, 6), flag = wx.EXPAND)
        self.gb.Add(self.scanPlot, (2, 4), (11, 6), flag = wx.EXPAND)
    
        self.gb.Add(self.settingsBox, (13, 0), (1, 4), flag = wx.EXPAND)
        self.gb.Add(self.scaleControl, (13, 4), flag = wx.ALIGN_LEFT)
        self.gb.Add(scrollerBox, (13, 5), (1, 4), flag = wx.ALIGN_CENTRE)
    
        self.gb.AddGrowableCol(5)
        self.gb.AddGrowableRow(3)
        self.gb.AddGrowableRow(8)
    
        overBox = wx.BoxSizer()
        overBox.Add(self.gb, 1, wx.ALL|wx.EXPAND, 20)
        self.SetSizerAndFit(overBox)
        
        self.wxMode = False # 'Is this thing being called by some madness in WX itself?'
        
        self.root = self.entrySelector.AddRoot('Foo')
        
        self.data = None
        self.psms = None
        self.features = None
        self.parser = None
        self.settings = defaultSettings
        
        self.dataCache = {}
        
        self.proteins = None
        self.proteinByTag = {}
        self.peptideByTag = {}
        
        self.featureCache = {}
        
        self.currentDataFile = None
        self.currentResultFile = None
        self.currentFeatureFile = None
        self.currentParserString = None
        self.currentFilter = None, None
        self.currentSorter = None
        self.currentMinFeatures = None
        
        self.plot_accession = None
        self.plot_peptide = None
        self.plot_scan = None
        
        self.mode = 'none'
        self.plexity = None
        
        self.ms1Lookup = None
        self.psmLookup = None
        
        self.combinedResultsMode = False # Whether a combined PSM file is being used.
        
        self.set_status("Ready.", 0)
        



    def getResult(self, event):
        filedialog = wx.FileDialog(parent = self, message = "Choose Search Result File",
                                   style = wx.FD_OPEN,
                                   wildcard = 'XLSX|*.xlsx|XLS|*.xls|CSV|*.csv|All|*')
        filedialog.ShowModal()
        newfile = filedialog.GetPath()
    
        self.resultSelector.Clear()
        self.resultSelector.SetValue(newfile)
        
        self.updateData(event)
        
    def getFeatureDB(self, event):
        filedialog = wx.FileDialog(parent = self, message = "Choose Feature Database File",
                           style = wx.FD_OPEN,
                           wildcard = 'All|*')
        filedialog.ShowModal()
        newfile = filedialog.GetPath()
    
        self.featureSelector.Clear()
        self.featureSelector.SetValue(newfile)
        
        self.updateData(event)
        
    def getData(self, event):
        filedialog = wx.FileDialog(parent = self, message = "Choose MS Data File",
                   style = wx.FD_OPEN,
                   wildcard = 'RAW|*.raw|WIFF|*.wiff|All|*.*')
        filedialog.ShowModal()
        newfile = filedialog.GetPath()
    
        self.dataSelector.Clear()
        self.dataSelector.SetValue(newfile)
        
        self.updateData(event)
        

    
    def openData(self, newData):    
        if not os.path.isabs(newData):
            if not self.currentResultFile and os.path.isabs(currentResultFile):
                raise RuntimeError, "Absolute path must be specified!"
            newData = os.path.join(os.path.dirname(self.currentResultFile),
                                   os.path.basename(newData))
        
        if self.currentDataFile != newData:
            self.currentDataFile = newData
            self.dataSelector.SetValue(newData)
            
            if newData in self.dataCache:
                (self.data,
                 self.ms1Lookup,
                 self.mzLookup) = self.dataCache[newData]
            else:
                self.data = async_mzFile(newData)
                self.set_status("Indexing MS Data...", 0)
                self.getMS1Lookup()
                self.dataCache[newData] = self.data, self.ms1Lookup, self.mzLookup
                self.set_status("...", 0)
            
            self.scanPlot.setData(self.data, self.mzLookup, 
                                  lambda x: self.currentScan.SetValue(str(x)))
            self.plotControl.set_states(self.scanPlot.states[self.scanPlot.ax1],
                                        self.scanPlot.states[self.scanPlot.ax2])
            
            featurefile = self.featureSelector.GetValue()
            expectedfeatures = '.'.join(newData.split('.') + ['features'])
            if (self.combinedResultsMode and
                featurefile != expectedfeatures and
                os.path.exists(expectedfeatures)):
                self.featureSelector.SetValue(expectedfeatures)
                self.set_status("Updating feature data...", 0)
                self.features = FeatureInterface(expectedfeatures)
                self.currentFeatureFile = expectedfeatures
                self.set_status("...", 0)                
                    
                
        
    
    def setScaleType(self, event):
        if self.scaleControl.GetStringSelection() == 'Scale to Data':
            self.scanPlot.scaleType = 'data'
        else:
            self.scanPlot.scaleType = 'annotation'
            
        self.scanPlot.updatePlots()
        
    
    def updateSettings(self, event):
        settingsDialog = LabelSettingsDialog(self, self.settings)
        
        if settingsDialog.ShowModal() == wx.ID_OK:
            settings = settingsDialog.retrieveSettings()
            if isinstance(settings, basestring):
                wx.MessageBox('An error occurred:\n%s' % settings).ShowModal()
                return
            else:
                self.settings = settings
        
            self.mode = self.settings['type']
            self.plexity = self.settings['plex']
            if self.mode == 'SILAC':
                self.corrections = None
                self.ratios = None
                self.heavyR = self.settings['heavyR']
                self.heavyK = self.settings['heavyK']
                self.heavyRMass = sum([int(x) for x in parentheticalGetter.findall(self.heavyR)])
                self.heavyKMass = sum([int(x) for x in parentheticalGetter.findall(self.heavyK)])
                if self.plexity == 3:
                    self.mediumR = self.settings['mediumR']
                    self.mediumK = self.settings['mediumK']
                    self.mediumRMass = sum([int(x) for x in parentheticalGetter.findall(self.mediumR)])
                    self.mediumKMass = sum([int(x) for x in parentheticalGetter.findall(self.mediumK)])
                else:
                    self.mediumR = self.mediumK = None
                    self.mediumRMass = self.mediumKMass = None
                    
                self.modeIndicator.SetValue('SILAC %s-plex' % self.plexity)

                self.sortCtrl.Clear()
                for thing in defaultSortModes + silacSortModes:
                    self.sortCtrl.Append(thing)

            elif self.mode == 'isobaric':
                self.mediumRMass = self.mediumKMass = None
                self.heavyRMass = self.heavyKMass = None
                self.corrections = self.settings['ionCorrections']
                self.ratios = self.settings['ratios']
                
                ratioStr = '; '.join('%s/%s' % (x+1, y+1) for x, y in self.ratios)
                
                self.modeIndicator.SetValue('Isobaric (%s) %s-plex, reading channel ratios [ %s ]'
                                            % (isobaricTypes[self.plexity], self.plexity, ratioStr))

                isobaricSortModes = ['%s/%s' % (x+1, y+1) for x, y in self.ratios]

                self.sortCtrl.Clear()
                for thing in defaultSortModes + isobaricSortModes:
                    self.sortCtrl.Append(thing)
        
        self.updateData(None, force = True)
        
        
        
        
    
    
    def scanLeft(self, event):
        curScan = int(self.currentScan.GetValue())
        if not curScan:
            return
        toScan = curScan - 1
        self.plot_scan = toScan
        self.currentScan.SetValue(str(toScan))
        
        if self.psmLookup and toScan in self.psmLookup:
            self.plotControl.scan_plot(toScan, self.psmLookup[toScan])
        else:
            self.plotControl.scan_plot(toScan)

        self.set_status("Ready.", 0)
    def scanRight(self, event):
        curScan = int(self.currentScan.GetValue())
        if not curScan:
            return
        toScan = curScan + 1
        self.plot_scan = toScan
        self.currentScan.SetValue(str(toScan))
        
        if self.psmLookup and toScan in self.psmLookup:
            self.plotControl.scan_plot(toScan, self.psmLookup[toScan])      
        else:
            self.plotControl.scan_plot(toScan)            

        self.set_status("Ready.", 0)
        
    
    def ms1Left(self, event):
        curScan = int(self.currentScan.GetValue())
        if not curScan:
            return
        toScan = max([x for x in self.ms1Lookup.values() if x < curScan])
        
        nextScanOver = max([x for x in self.ms1Lookup.values() if x < toScan])
        self.data.preorder('scan', nextScanOver, centroid = True)
        
        self.plot_scan = toScan
        self.currentScan.SetValue(str(toScan))
        if self.psmLookup and toScan in self.psmLookup:
            self.plotControl.scan_plot(toScan, self.psmLookup[toScan])      
        else:
            self.plotControl.scan_plot(toScan)            

        self.set_status("Ready.", 0)        
    def ms1Right(self, event):
        curScan = int(self.currentScan.GetValue())
        if not curScan:
            return
        toScan = min([x for x in self.ms1Lookup.values() if x > curScan])
        
        nextScanOver = min([x for x in self.ms1Lookup.values() if x > toScan])
        self.data.preorder('scan', nextScanOver, centroid = True)        
        
        self.plot_scan = toScan
        self.currentScan.SetValue(str(toScan))
        if self.psmLookup and toScan in self.psmLookup:
            self.plotControl.scan_plot(toScan, self.psmLookup[toScan])      
        else:
            self.plotControl.scan_plot(toScan)            

        self.set_status("Ready.", 0) 
        
        
    def reselectScan(self, event):
        scanNum = int(self.currentScan.GetValue())
        self.plot_scan = scanNum
        
        if self.psmLookup and scanNum in self.psmLookup:
            self.plotControl.scan_plot(scanNum, self.psmLookup[scanNum])      
        else:
            self.plotControl.scan_plot(scanNum)         
        
        self.set_status("Ready.", 0)        
    
    def updateData(self, event, force = False):
        self.set_status("Updating...", 0)
        
        newData = self.dataSelector.GetValue()
        newResults = self.resultSelector.GetValue()
        newFeatures = self.featureSelector.GetValue()
        #newParser = self.parseCtrl.GetValue()
        newFilter = self.searchCtrl.GetValue(), self.searchType.GetValue()
        newSorter = self.sortCtrl.GetValue()
        #newMinFeatures = int(self.minFeaturesCtrl.GetValue().strip())
        newMinFeatures = None
        
        global before
        #print "A %s" % (clock() - before)
        before = clock()
        
        wx.Yield()        
        
        update = False
        if newData and newData != self.currentDataFile:
            self.set_status("Opening MS Data file...", 0)
            self.openData(newData)
            self.plotControl.general_xic()
            update = True
        if newResults and newResults != self.currentResultFile:
            self.currentResultFile = newResults
            start = clock()
            self.set_status("Loading protein list...", 0)
            psmReader = reader(newResults, autotypecast = False)
            psms = list(psmReader)
            
            self.combinedResultsMode = 'Source' in psms[0]
            
            self.psmLookup = dict([(scanFromDesc(x['Spectrum Description']), x) for x in psms])
            if gene_column in psmReader.columns:
                self.proteins = collectByCriterion(psms, lambda x: x[gene_column], splitby = ';')
            else:
                self.proteins = collectByCriterion(psms, lambda x: x['Accession Number'], splitby = '; ')
            #print clock() - start
            self.set_status("...", 0)
            update = True
        if newFeatures and newFeatures != self.currentFeatureFile:
            self.currentFeatureFile = newFeatures
            self.set_status("Updating feature data...", 0)
            self.features = FeatureInterface(newFeatures)
            self.set_status("...", 0)
            update = True

            
        #if newParser.strip() and newParser.strip() != 'Default' and newParser != self.currentParserString:
            #self.currentParserString = newParser
            #self.parser = re.compile(newParser)
            #update = True
        if newFilter != self.currentFilter:
            self.currentFilter = newFilter
            update = True
        if newSorter != self.currentSorter:
            self.currentSorter = newSorter
            update = True
        if newMinFeatures != self.currentMinFeatures:
            self.currentMinFeatues = newMinFeatures
            update = True
        

        before = clock()
        
        if not ((update or force) and self.proteins and self.settings):
            self.set_status("Ready.", 0)
            return
        #wx.Yield()

        self.set_status("Updating protein display...", 0)
        
        self.updateProteinList()
            
                
        before = clock()        
        
        self.set_status("Ready.", 0)
        
        
        
    def updateProteinList(self):
        self.wxMode = True
        self.entrySelector.DeleteAllItems()
        self.wxMode = False
        self.root = self.entrySelector.AddRoot('Foo')   
        #self.root = self.entrySelector.GetRootItem()
        
        searchArg = self.currentFilter[0]
        if searchArg:
            searchMode = self.currentFilter[1]
        else:
            searchMode = None        
        
        
        def viewableProteins():
            # To separate the filtration code from the GUI bits, and make
            # a sorted list.
            proteins = []
            for protein, psms in self.proteins.items():
                protRatString, protRatDict = calculateProteinRatios(psms, self.settings)
                
                if searchMode == 'Accession' and searchArg not in protein:
                    continue
                elif searchMode == 'Peptide':
                    psms = [psm for psm in psms if any([searchArg in x for x in parsePeptide(psm)])]
                elif searchMode == 'Scan':
                    psms = [psm for psm in psms if searchArg in scanFromDesc(psm['Spectrum Description'])]                                       
                
                if not psms:
                    continue
                
                psmsByPeptide = collectAndAnnotatePSMs(psms, self.settings)
                psmsByPeptide = [(k, sorted(psms, key = lambda x: x['Peptide Score'], reverse = True))
                                 for k, psms in psmsByPeptide.items()]
                psmsByPeptide.sort(key = lambda x: x[0][1]) # By charge.
                
                
                proteins.append((protein, psmsByPeptide, protRatString, protRatDict))
            

            proteins.sort(key = self.deriveSorter(), reverse = True)
            return proteins
            
        
            
        for protein, psmsByPeptide, protRatString, protRatDict in viewableProteins():
            proteinTag = protein + " " + protRatString
            self.proteinByTag[proteinTag] = protein
            root = self.entrySelector.AppendItem(self.entrySelector.GetRootItem(), proteinTag)
            
            for peptide, psms in psmsByPeptide:
                peptideTag = psms[0]['peptide string']
                self.peptideByTag[peptideTag] = peptide
                subroot = self.entrySelector.AppendItem(root, peptideTag)
    
                for psm in psms:
                    psmTag = psm['psm string']
                    self.entrySelector.AppendItem(subroot, psmTag)      
        
        self.entrySelector.CollapseAll()    
        self.entrySelector.UnselectAll()
        
        self.set_status("Ready.", 0)


    def deriveSorter(self):
        sorter = self.sortCtrl.GetValue()

        if not sorter:
            def sort(x):
                return x
        elif sorter == 'Score': # Implicitly, peptide score.
            def sort((a, psmsByPep, b, c)):
                psms = sum(zip(*psmsByPep)[1], [])
                return max([x['Peptide Score'] for x in psms])
        elif sorter == 'PSM Count':
            def sort((a, psmsByPep, b, c)):
                psms = sum(zip(*psmsByPep)[1], [])
                return len(psms)
        elif '/' in sorter and len(sorter) < 5:
            first, second = [int(x)-1 for x in sorter.split('/')]
            plexity = self.plexity

            def sort((a, psmsByPep, b, c)):
                psms = sum(zip(*psmsByPep)[1], [])
                reporterInts = zip(*[readIsobaricReporters(x, plexity) for x in psms])
                firstInt = average(reporterInts[first])
                secondInt = average(reporterInts[second])
                return firstInt / secondInt
            


        else:
            raise NotImplementedError

        return sort


    def getMS1Lookup(self):
        self.ms1Lookup = {}
        self.mzLookup = {}
        prev = None
        scaninfo = self.data.scan_info()
        for _, mz, scanNum, level, _ in scaninfo:
            if level == 'MS1':
                prev = scanNum
                self.ms1Lookup[scanNum] = scanNum
            else:
                self.ms1Lookup[scanNum] = prev
                self.mzLookup[scanNum] = mz
        
            
    def getFeatures(self, indices):
        for index in indices:
            print "Retrieving %s" % index
            start = clock()
            index = str(index)
            if not self.features:
                return
            elif index in self.featureCache:
                #print "---"
                yield self.featureCache[index]
            else:
                feature = self.features[index]
                self.featureCache[index] = feature
                #print "- %s" % (clock() - start)
                yield feature
            
        
            
    
    def render(self, event):
        self.set_status("Rendering plots...", 0)
        global before
        #print "D %s" %  (clock() - before)
        before = clock()        
        if self.wxMode == True:
            return
        
        root = self.entrySelector.GetRootItem()
        selection = self.entrySelector.GetSelection()
        descent = []
        while selection != root:
            descent.append(self.entrySelector.GetItemText(selection))
            selection = self.entrySelector.GetItemParent(selection)

        if not descent:
            print "Render failed."
            return

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
            
        #print accession, peptide, scan
        #print '-'
        
        if accession:
            accession = self.proteinByTag[accession]
        if peptide:
            peptide = self.peptideByTag[peptide]
        if scan:
            try:
                scan = int(scan.split()[0].strip())
            except ValueError:
                scan = int(scan.split()[1].strip())
            # Perhaps should repace with a regex, but note that scan numbers can be small.
        
        #print accession, peptide, scan
        
        update_boxplot = False
        update_xic = False
        update_scan = False        
        if self.plot_accession != accession:
            self.plot_accession = accession
            self.plot_peptide = None
            self.plot_scan = None
            self.featureCache = {}
            update_boxplot = True
            update_xic = True
            update_scan = True
            
        if self.plot_peptide != peptide:
            self.plot_peptide = peptide
            self.plot_scan = None
            update_boxplot = True
            update_xic = True
            update_scan = True
        if self.plot_scan != scan:
            self.plot_scan = scan
            #if scan:
                #ms1 = max([x for x in self.ms1Lookup.values() if x < scan])
                #self.currentScan.SetValue(str(ms1))
            update_xic = True
            update_scan = True
        
        if update_boxplot:
            self.render_boxplot()
            wx.Yield()
            
        self.plotControl.targeted_plot(self.plot_accession,
                                       self.plot_peptide,
                                       self.plot_scan)
        if scan:
            self.currentScan.SetValue(str(self.plot_scan))
        
        
        #print "E %s" % (clock() - before)
        #before = clock()        
        
        self.set_status("Ready.", 0)
        
    
    def render_boxplot(self):
        if self.mode == 'none' or not self.mode:
            return
        
        self.set_status("Rendering box plot...", 0)
        
        psms = self.proteins[self.plot_accession]
        ratioDict = ratioSetForPSMs(psms, self.settings)
        
        assert self.plot_accession in psms[0]['Accession Number'].split('; ')
        
        if self.mode == 'SILAC' and self.plexity == 2:
            ratioSets = [ratioDict['heavy']]
        elif self.mode == 'SILAC' and self.plexity == 3:
            ratioSets = [ratioDict['medium'], ratioDict['heavy']]
        elif self.mode == 'isobaric':
            ratioSets = [x[1] for x in sorted(ratioDict.items())]
        else:
            assert self.mode == 'none'
            ratioSets = []
        
        self.ratioPlot.plot(ratioSets, None)
            




        
class BoxPlotter(wx.Panel):
    def __init__(self, parent, ident = -1):
        wx.Panel.__init__(self, parent, ident, size = (100, 100))
        # Why does "size = (100, 100)" make the size adapt correctly?
        # It is a mystery!
        
        self.fig = Figure()
        self.ax = self.fig.add_subplot(111)
        self.ax.xaxis.set_visible(False)
        self.ax.yaxis.get_major_formatter().set_powerlimits((-5, 5))
        self.ax.yaxis.set_major_formatter(FormatStrFormatter('%.1f'))
        self.ax.tick_params(direction='in', pad = -25)
        
        self.ax.set_ylim(0, 2)
        
        bot, top = self.ax.get_ylim()
        inc = (top - bot)/8
        self.ax.set_yticks([x for x in arange(bot+inc, top, inc)])              
        
        
        self.fig.tight_layout(pad = 0, rect = [0.2, 0.02, 0.95, 1])
        
        
        self.canvas = FigureCanvas(self, -1, self.fig)
        
        wxbackground = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE)
        wxbackground = [x / 255.0 for x in wxbackground]
        self.fig.set_facecolor(wxbackground)
        #self.fig.set_facecolor((0.5, 0.5, 0.5))

        self.sizer = wx.BoxSizer()
        self.sizer.Add(self.canvas, -1, wx.EXPAND)
        self.SetSizer(self.sizer)
        self.Fit()
        
        #self.clickBack = self.canvas.mpl_connect('button_press_event', self.raiseClick)
        
        self.canvas.draw()
        
    def plot(self, ratioSets, markpt = None):
        
        self.fig.clf(keep_observers=True)
        self.ax = self.fig.add_subplot(111)
        self.ax.yaxis.get_major_formatter().set_powerlimits((-1, 7))
        self.ax.tick_params(axis = 'x', labelbottom = 'off')
        
        self.ax.tick_params(direction='in', pad = -30)
        #self.ax.locator_params(axis = 'y', nbins = 20)
        #self.ax.yaxis.get_major_ticks()[0].label1.set_visible(False)
        #self.ax.yaxis.get_major_ticks()[-1].label1.set_visible(False)         

        self.ax.yaxis.set_major_formatter(FormatStrFormatter('%.1f'))
        ratioSets = [[x for x in xs if x not in [None, '-']] for xs in ratioSets]
        #self.ax.set_xlim(0, 1.1)
        if any(ratioSets):
            #posInc = 0.6/len(ratioSets)
            #positions = [0.7 + x for x in arange(posInc, 0.6+posInc, posInc)]
            self.ax.boxplot(ratioSets)
        #if markpt:
            #self.ax.plot([0.75, 1.25], [markpt, markpt], color = 'r', linestyle = '--')
            
        self.ax.set_xlim(0, 1.5)
        bot, top = self.ax.get_ylim()
        if top - bot < 1:
            bot -= 0.5
            top += 0.5
        edge = (top - bot)/10
        ticks = [x for x in arange(0, 10, 0.1) if bot+edge <= x <= top-edge]
        self.ax.set_yticks(ticks)
        self.canvas.draw()
        