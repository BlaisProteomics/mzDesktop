import wx
import multiplierz.mzSearch.comet_search as comet_search
from multiplierz.mass_biochem import unimod
from collections import defaultdict
#import multiplierz.mzAPI
import wx.lib.delayedresult as delayedresult
import cPickle
import time    
import process_comet_xml
import subprocess
#import thread
import wx.lib.delayedresult as delayedresult
#import mgf2ms2
#mgf2ms2.convert(r'C:\SBF\test\2012-07-24-mTraq-1_RECAL.mgf', None)
#print "imported"
import os, sys, shutil, re, subprocess, glob
#sys.stderr = open('error.log', 'w')
#sys.stdout = open('output.log', 'w')
#file_r = open(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), 'settings.txt'), 'r')
#global COMET_DIR
#COMET_DIR = file_r.readlines()[0]




commonMods = ['Oxidation(M)',
              'Phosphorylation(STY)',
              'Carbamidomethyl(C)',
              'Methylthio(C)']

itraqMods = ['iTRAQ8plex',
             'iTRAQ4plex']

additionalMods = commonMods + [''] + [''] + itraqMods


from multiplierz import myData
from multiplierz.settings import settings

COMET_DIR = os.path.dirname(settings.get_comet())
workflow_record = os.path.join(myData, 'comet_workflows.txt')
#ENZYME_DICT = {'No_enzyme':'0', 'Trypsin':'1', r'Trypsin/P':'2', 'Lys_C':'3', 'Lys_N':'4', 'Arg_C':'5', 'Asp_N':'6', r'CNBr':'7', 'Glu_C':'8', 'PepsinA':'9', 'Chymotrypsin':'10'}
ENZYME_DICT = {"No_enzyme":'0', 'Trypsin':'1', r'Lys_C':'2', 'Lys_N':'3','Arg_C':'4','Asp_N':'5','CNBr':'6','Glu_C':'7','PepsinA':'8','Chymotrypsin':'9',r'Trypsin/Glu_C':'10',r"Trypsin/P":'11'}

#DATABASE_DIRECTORY = os.path.dirname(os.path.realpath(__file__).replace('\\library.zip','')) + '\\FastaDatabases'
#DATABASE_DIRECTORY = os.path.dirname(os.path.abspath(sys.argv[0])).replace('\\library.zip','') + '\\FastaDatabases'
#DATABASE_DIRECTORY = os.path.join(myData, 'pyCometDatabases')
#DATABASES = glob.glob(DATABASE_DIRECTORY + '\\*.fasta')

from multiplierz import fastaFiles
DATABASES = []
with open(fastaFiles, 'r') as fastas:
    for line in fastas:
        if not line.strip()[0] == '#':
            DATABASES.append(line.strip())

#assert DATABASES, "No database paths found in %s; please update file." % fastaFiles

def get_multiple_files(caption):
    dlg = wx.FileDialog(None, caption, defaultFile=os.getcwd(), pos = (2,2), style = wx.FD_MULTIPLE, wildcard = "*.xls")
    if dlg.ShowModal() == wx.ID_OK:
        filenames=dlg.GetFilenames()
        dir = dlg.GetDirectory()
        os.chdir(dir)
    dlg.Destroy()
    return filenames, dir

class Page(wx.Panel):
    def __init__(self, parent):
        panel = wx.Panel.__init__(self, parent)

class InsertFrame(wx.Frame):
    def __init__(self, parent, id):
        self.jobID = 0
        self.workflow_list = self.read_workflow_list()
        self.workflow = self.read_workflow()        
        wx.Frame.__init__(self,parent,id, 'PyComet 64 bit 0.0.7', size =(580,660), pos = (50,50))
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        panel = wx.Panel(self)
        nb = wx.Notebook(panel, size=(600,600), pos= (10,10))
        self.page1 = Page(nb)
        self.page2 = Page(nb)
        #self.page3 = Page(nb)
        
        nb.AddPage(self.page1, "Main")
        nb.AddPage(self.page2, "Settings")
        #nb.AddPage(self.page3, "Queue")
        
        self.createButtons(self.page1)
        self.createCheckBoxes(self.page1)
        self.createLabels(self.page1)
        #self.createListBoxes(self.page3)
        self.createTextBoxes(self.page1)
        
        self.createComboBoxes(self.page1)
        self.createCheckListBoxes(self.page1)   
        self.createRadioBoxes()
        self.dir = ''
        self.filenames = []        
        
        self.statusbar = self.CreateStatusBar()
        self.statusbar.SetStatusText("Ready")
        self.set_workflow("Nothing")
        self.FindWindowByName("FDR_Rate").Show(False) 
        self.FindWindowByName("enzyme").SetValue("Trypsin")
        self.FindWindowByName("workFlow").SetValue("Nothing")
        self.CreateMenuBar()
        self.vmb = True
        self.fmb = True

    def OnClose(self, event):
        self.Destroy()

    def OnOpenProjectFolder(self, panel):
        subprocess.Popen('explorer "' + self.defaultDir + '"')

    def OnAutoCalBrowse(self, panel):
        pass
        
    #def read_workflow(self):
        #print COMET_DIR
        #file_r = open(COMET_DIR + '\\workflows.txt', 'r')
        
        #data = file_r.readlines()
        #file_r.close()
        #workflow_dict = {}
        #for member in data:
            #j = member.split("|")
            #key = j[0].strip()
            #fixed = j[1].split(":")[1].strip()
            #fixed_list = [x.strip() for x in fixed.split(",") if x != '']
            #var = j[2].split(":")[1].strip()
            #var_list = [x.strip() for x in var.split(",")]    
            #workflow_dict[key]=[fixed_list, var_list]
        #return workflow_dict  
    
    #def read_workflow_list(self):
        
        #file_r = open(COMET_DIR + '\\workflow_list.txt', 'r')
    
        #data = file_r.readlines()
        #workflow_list = []
        #for member in data:
            #workflow_list.append(member.strip())
        #file_r.close()
        #return workflow_list
    
    #def write_workflow_list(elf, workflowData):
        #workflows = open(COMET_DIR + '\\workflow_list.txt', 'w')
        #workflow_details = open(COMET_DIR + '\\workflows.txt', 'w')
        
        #for workflow, modifications in workflowData:
            #fixedMods, varMods = modifications
            #workflows.write(workflow + '\n')
            
            #fixedMods = "fm: " + ', '.join(fixedMods)
            #varMods = "vm: " + ', '.join(varMods)
            #workflow_details.write('|'.join([workflow, fixedMods, varMods]) + '\n')
        
        #workflows.close()
        #workflow_details.close()
        
    def read_workflow(self):
        try:
            workflowFile = open(workflow_record, 'r')
        except IOError as err:
            if err[0] == 2: # 'No such file or directory'
                print "No workflow file %s found."% workflow_record
                return {'Nothing':([], [])}
        
        workflows = {}
        for line in workflowFile:
            workflow, varmods, fixmods = line.strip().split('|')
            
            varmods = [x for x in varmods.split(';') if x]
            fixmods = [x for x in fixmods.split(';') if x]
            
            workflows[workflow] = fixmods, varmods
        
        return workflows
    
    def read_workflow_list(self):
        try:
            workflowFile = open(workflow_record, 'r')
        except IOError as err:
            if err[0] == 2: # 'No such file or directory'
                print "No workflow file %s found." % workflow_record
                return {'Nothing':([], [])}

        workflows = []
        for line in workflowFile:
            workflow, _, _ = line.split('|')
            workflows.append(workflow)
        
        return workflows
            

    def set_workflow(self, workflow):
        #workflow_dict = self.return_mods()
        workflow_dict = self.read_workflow()

        if workflow not in workflow_dict:
            return

        vm = workflow_dict[workflow][1]
        fm = workflow_dict[workflow][0]
        self.FindWindowByName("modsListBox").Clear()
        i=-1
        j=-1
        for i, member in enumerate(vm):
            self.FindWindowByName("modsListBox").Append(member)
            self.FindWindowByName("modsListBox").Check(i, True)
        self.FindWindowByName("fmodsListBox").Clear()
        for j, member in enumerate(fm):
            self.FindWindowByName("fmodsListBox").Append(member)
            self.FindWindowByName("fmodsListBox").Check(j, True)
        cysAlk = str(self.FindWindowByName("cysAlk").GetValue()).strip()
        cysMod = str(self.FindWindowByName("cysMod").GetValue()).strip()
        cysDict = {'Iodoacetamide':'Carbamidomethyl(C)', 'MMTS':'Methylthio(C)'}
        if cysMod == 'Fixed':
            self.FindWindowByName("fmodsListBox").Append(cysDict[cysAlk])
            self.FindWindowByName("fmodsListBox").Check(j+1, True)            
        else:
            self.FindWindowByName("modsListBox").Append(cysDict[cysAlk])
            self.FindWindowByName("modsListBox").Check(i+1, True)            

    def databases(self, server):
        return ['Marto_FR_Yeast','Marto_FR_EColi', 'Marto_FR_Human', 'Marto_FR_Mouse']

    
    def menuData(self):
        return  ()
    # None of these are currently usable, or really important.
            #("&File",
                    #("&Open", "Open Template", self.OnLoad),
                    #("&Save", "Save Template", self.OnSave)),
                 #("&Tools",
                  #("mgf2ms2", "Convert mgf to ms2", self.Onmgf2ms2)),
                #("&Help",
                    #("&Help", "Help", self.OnHelp)))
    
    def CreateMenuBar(self):
        menuBar = wx.MenuBar()
        for eachMenuData in self.menuData():
            menuLabel = eachMenuData[0]
            print menuLabel
            menuItems = eachMenuData[1:]
            print menuItems
            menuBar.Append(self.createMenu(menuItems), menuLabel)
        self.SetMenuBar(menuBar)
    
    def createMenu(self, menuData):
        menu=wx.Menu()
        print menuData
        for eachLabel, eachStatus, eachHandler in menuData:
            if not eachLabel:
                menu.AppendSeparator(self)
                continue
            menuItem = menu.Append(-1, eachLabel, eachStatus)
            self.Bind(wx.EVT_MENU, eachHandler, menuItem)
        return menu
    
    def ComboBoxData(self):
        return (('dbaseName', (300,120), (200,20), [os.path.basename(x) for x in DATABASES] or ["None found!"], 0, False, None, self.page1),
                ('workFlow', (300,280), (100,20), self.workflow_list, 0, True, self.OnWorkFlow, self.page1),
                ('cysAlk', (300,340), (120,20), ['Iodoacetamide', 'MMTS'], 0, True, self.OnCysAlk, self.page1),
                ('cysMod', (420,340), (80,20), ['Fixed', 'Variable'], 0, True, self.OnCysAlk, self.page1),
                ('enzyme', (300,70), (200,20), [x for x in ENZYME_DICT.keys()], 0, False, None, self.page1),
                #('xTract', (300,100), (200,20), ['Orbi2mgf_RTCWDC','yTRAQ', 'yTRAQ(8-plex)', r'CAD/HCD', r'TriplePlay', 'ABSciex MS Data Converter', 'TMTtraq', 'LDA yTRAQ', 'LDA CAD/HCD', 'ETD LT/FT', 'IT/FT'], 0, False, None, self.page1),
                #('quant', (300,400), (200,20), ['None', r'SILAC K+6 R+6 [MD]', r'SILAC K+6 R+10 [MD]', r'Bala3plex', r'Bala2of3plex','HiRes2G', 'HiRes4G','mTRAQ','HGBala6plex'], 0, False, None, self.page1),
                ('fdr', (300,220), (60,20), ['Yes', 'No'], 0, True, self.OnCgFRF, self.page1),
                ('precTolUnit', (70,65), (60,20), ['ppm', 'amu'], 0, False, None, self.page2),
                #('prodTolUnit', (70,115), (60,20), ['Da', 'mmu'], 0, False, None, self.page2),
                #('HCDprodTolUnit', (70,165), (60,20), ['mmu', 'Da'], 0, False, None, self.page2),
    
                )

    def OnCysAlk(self, event):
        workflow = self.FindWindowByName("workFlow").GetValue().strip()
        self.set_workflow(workflow)

    def createComboBoxes(self, panel):
        for eachName, eachPos, eachSize, eachList, eachInit, eachEvent, eachHandler, eachPanel in self.ComboBoxData():
                ComboBox = self.BuildOneComboBox(panel, eachName, eachPos, eachSize, eachList, eachInit, eachEvent, eachHandler, eachPanel)


    def BuildOneComboBox(self, panel, eachName, eachPos, eachSize, eachList, eachInit, eachEvent, eachHandler, eachPanel):
        if isinstance(eachList, dict):
            eachList = eachList.keys()
            
        try:
            ComboBox = wx.ComboBox(eachPanel, -1, size=eachSize, pos=eachPos, name=eachName, value=eachList[eachInit], choices=eachList)
        except IndexError:
            ComboBox = wx.ComboBox(eachPanel, -1, size=eachSize, pos=eachPos, name=eachName, choices=eachList)
            
        if eachEvent:
            self.Bind(wx.EVT_COMBOBOX, eachHandler, ComboBox)
        return ComboBox
        
    def ButtonData(self): #("Execute", self.OnEXE, (10, 400), (120,25), self.page1),
        return (("Execute", self.OnHandle, (10, 400), (120,25), self.page1),
                ("Select Files", self.OnBrowse, (10, 10), (120,25), self.page1),
                #('L', self.OnLoad, (350, 10), (20,20), self.page1),
                #('S', self.OnSave, (370, 10), (20,20), self.page1),
                ('Workflow Editor', self.onWorkflowEdit, (370, 400), (120, 25), self.page1)
                ) #self.handle_exe self.OnEXE

    def CheckData(self):
##        return (("Phosphopeptide Only", (10, 50), (150,25), "phosCheck", False),
##                ("Remove cRAP", (10, 70), (150,25), "crapCheck", True)
##                )
        return (("Perform Search", (10, 450), (150, 25), "PerformSearchCheck", True, self.page1),
                ("Save Parameter File", (200, 450), (150, 25), "SaveParameterCheck", False, self.page1)
                )
    
    def LabelData(self):
        return (("Database", (300, 100), (150,20), self.page1),
                ("Files to Process", (10, 50), (80,20), self.page1),
                ("Search Parameters", (10, 240), (120,20), self.page1),
                ("Variable Modifications", (10, 260), (120,20), self.page1),
                ("Select Workflow", (300,260), (150,20), self.page1),
                ("Cysteines", (300,320), (150,20), self.page1),
                #("Quantitation", (300,380), (150,20), self.page1),
                ("False Discovery Rate", (300,200), (150,20), self.page1),
                ("Precursor Tolerance", (10,45), (120,20), self.page2),
                ("Fragment bin tolerance", (10,95), (120,20), self.page2),
                ("Fragment bin offset", (10,145), (120,20), self.page2),
                ("Number of threads", (10,195), (120,20), self.page2),
                ("Spectral batch size", (10, 245), (120,20), self.page2),
                ("Reverse Db Identifier", (10, 295), (120,20), self.page2),
                ("Enzyme", (300, 50), (80,20), self.page1),
                ("Missed Cleavages", (300, 150), (180,15), self.page1),
                ("Fixed Modifications", (160, 260), (120,20), self.page1),
                #('Template', (300, 10), (50,20), self.page1),
                
        
                )
    
    def TextBoxData(self):
##        return (("Deamidated (NQ),Oxidation (M),Phospho (ST),Phospho (Y)", (10, 280), (280,20), "itMods"),
##                )
        return (("10.00", (10,65), (50,20), "precTol", self.page2),
                ("1.0005", (10, 115), (50,20), "prodBinTol", self.page2),
                ("0.4", (10,165), (50,20), "prodBinOffset", self.page2),
                ("0", (10,215), (50,20), "NumThreads", self.page2),
                ("10000", (10,265), (50,20), "NumSpectra", self.page2),
                ("REV_", (10,315), (50,20), "RevDbId", self.page2),
                ("2", (300, 170), (50,20), "missedCleavages", self.page1),
                ("0.01", (300,490), (50,20), "FDR_Rate", self.page1),            
                )

    def RadioBoxData(self):
            return (("Dimension", ['1D', 'mD'], 'dimensionRadioBox', (150, 10), wx.DefaultSize, self.page1),
                    ("FDR", ['expect', 'xcorr'], 'fdrSort', (10, 410), wx.DefaultSize, self.page2)
                )

## ([], 'searchListBox', (10, 260), (280,150))
    #("Deamidated (NQ),Oxidation (M),Phospho (ST),Phospho (Y)", (10, 280), (280,20), "itMods")
    def CheckListBoxData(self):
        #database = unimod.UnimodDatabase(os.path.join(myData, 'unimod.xml'))
        #unimodNames = database.get_all_mod_names()
        unimodNames = unimod.get_all_mod_names()
        
        return (([], 'filesListBox', (10, 70), (280,150)),
                #(['Deamidated (NQ)', 'Oxidation (M)', 'Phospho (ST)', 'Phospho (Y)'], 'modsListBox', (10,280), (140,100)),
                #(['Carbamidomethyl (C)', 'iTRAQ (N-term)', 'iTRAQ (K)'], 'fmodsListBox', (155,280), (140,100))
                (unimodNames, 'modsListBox', (10,280), (140,100)),
                (unimodNames, 'fmodsListBox', (155,280), (140,100))
                )

    def BuildOneCheckListBox(self, panel, eachList, eachName, eachPos, eachSize):
        CheckListBox = wx.CheckListBox(panel, -1, size=eachSize, pos=eachPos, name=eachName, choices = eachList, style=wx.LB_HSCROLL)
        return CheckListBox
    
    def createCheckListBoxes(self, panel):
        for eachList, eachName, eachPos, eachSize in self.CheckListBoxData():
            CheckListBox = self.BuildOneCheckListBox(panel, eachList, eachName, eachPos, eachSize)

    def ListBoxData(self):
        return (([], 'MessageBox', (10, 50), (480,450)),
                )                

    def createListBoxes(self, panel):
        for eachList, eachName, eachPos, eachSize in self.ListBoxData():
            ListBox = self.BuildOneListBox(panel, eachList, eachName, eachPos, eachSize)

    def createRadioBoxes(self):
        for eachLabel, eachList, eachName, eachPos, eachSize, eachPanel in self.RadioBoxData():
            radiobox = self.BuildOneRadioBox(eachPanel, eachLabel, eachList, eachName, eachSize, eachPos)

    def createTextBoxes(self, panel):
        for eachLabel, boxPos, boxSize, eachName, eachPanel in self.TextBoxData():
            TextBox = self.MakeOneTextBox(eachPanel, eachLabel, boxSize, boxPos, eachName)

    def createLabels(self, panel):
        print self.LabelData()
        for eachLabel, labelPos, labelSize, eachPanel in self.LabelData():
            label = self.MakeOneLabel(panel, eachLabel, labelPos, labelSize, eachPanel)
    
    def createButtons(self, panel):
        for eachLabel, eachHandler, pos, size, eachPanel in self.ButtonData():
            button = self.BuildOneButton(eachPanel, eachLabel, eachHandler, pos, size)
            
    def createCheckBoxes(self, panel):
        for eachLabel, pos, size, eachName, eachValue, eachPanel in self.CheckData():
            check = self.CreateOneCheck(eachPanel, eachLabel, pos,size, eachName, eachValue)

    def BuildOneListBox(self, panel, eachLabel, eachName, eachPos, eachSize):
        ListBox = wx.ListBox(panel, -1, size=eachSize, pos=eachPos, name=eachName, style=wx.LB_HSCROLL)
        return ListBox

    def BuildOneRadioBox(self, panel, eachLabel, eachList, eachName, eachSize, eachPos):
        radiobox = wx.RadioBox(panel, -1, label=eachLabel, pos=eachPos, size=eachSize, choices=eachList, majorDimension=2, style=wx.RA_SPECIFY_COLS | wx.NO_BORDER, name=eachName) #
        return radiobox

    def MakeOneTextBox(self, eachPanel, eachLabel, boxSize, boxPos, eachName):
        textBox = wx.TextCtrl(eachPanel, -1, eachLabel, pos = boxPos, size=boxSize, name = eachName)
        return textBox

    def MakeOneLabel(self, panel, label, labelPos, labelSize, eachPanel):        
        label = wx.StaticText(eachPanel, -1, label, pos=labelPos, size=labelSize, name = label)
        return label

    def BuildOneButton(self, eachPanel, label, handler, pos, size):
        button = wx.Button(eachPanel, -1, label, pos, size, name=label)
        self.Bind(wx.EVT_BUTTON, handler, button)
        return button

    def CreateOneCheck(self, eachPanel, label, pos, size, boxname, eachValue):
        checkbox = wx.CheckBox(eachPanel, -1, label, pos, size, name = boxname)
        if eachValue:
            checkbox.SetValue(eachValue)
        return checkbox

    def OnBrowse(self, event):
        dlg = wx.FileDialog(None, "Select Files..", pos = (2,2), style = wx.FD_MULTIPLE, wildcard = "Peak Lists (*.ms2,*.mgf)|*.ms2;*.mgf")
        if dlg.ShowModal() == wx.ID_OK:
            filenames=dlg.GetFilenames()
            dir = dlg.GetDirectory()
            os.chdir(dir)
            self.dir = dir
            self.defaultDir = dir
            self.filenames = filenames
            self.FindWindowByName("filesListBox").Clear()
            for filename in filenames:
                self.FindWindowByName("filesListBox").Append(filename)  
                
        dlg.Destroy()


            #self.FindWindowByName("searchListBox").Append(filename)
        

    def OnTemplate(self, event):
        print "TEMPLATE SELECTED!"
        template = self.FindWindowByName("template").GetValue().strip()
        print template
        if template == "Danial":
            self.set_workflow('Phospho iTRAQ')
            self.FindWindowByName("xTract").SetValue('yTRAQ')
            self.FindWindowByName("fdr").SetValue('FRF5ppm')
            self.FindWindowByName("workFlow").SetValue('Phospho iTRAQ')
            self.FindWindowByName("modsListBox").Check(0, False)
            self.FindWindowByName("dimensionRadioBox").SetStringSelection('mD')
            self.FindWindowByName("mfdCheck").SetValue(True)
        
        
    def Onmgf2ms2(self, event):
        #import mgf2ms2
        import mzGUI_standalone as mzGUI
        #mgfFilename, cdir = mgf2ms2.get_single_file()
        mgfFilename = mzGUI.file_chooser(wildcard='MGF|*.mgf|All|*')
        try:
            #mgf2ms2.convert(mgfFilename)
            comet_search.mgf_to_ms2(mgfFilename)
        except TypeError:
            pass

    def setOrganism(self, dbase):
        organism = ''
        if dbase.find('Human') > -1:
            organism = 'HUMAN'
        elif dbase.find('Mouse') > -1:
            organism = 'MOUSE'
        else:
            organism = 'NA'
        return organism

    def OnWorkFlow(self, event):
        print "EVENT"
        wrkflow = self.FindWindowByName("workFlow").GetValue().strip()
        self.set_workflow(wrkflow)

    def OnCgFRF(self, event):
        print "EVENT"
        FRFF = self.FindWindowByName("fdr").GetValue().strip()
        print FRFF
        if FRFF == "Tunable FRFF":
            self.FindWindowByName("FDR_Rate").Show(True)
        else:
            self.FindWindowByName("FDR_Rate").Show(False)
    #M4
    def update_id_base(self, id, file, dir):
        if os.path.exists(dir + '\\mascot_id_base.txt'):
            file_w = open(dir + '\\mascot_id_base.txt', 'a')
        else:
            file_w = open(dir + '\\mascot_id_base.txt', 'w')
        file_w.write(id.split(':')[0].strip()[1:] + '\t' + file + '\n')
        file_w.close()
    def retrieve_id_base(self, dir):
        f2id = {}
        if os.path.exists(dir + '\\mascot_id_base.txt'):
            file_r = open(dir + '\\mascot_id_base.txt', 'r')
            lines = file_r.readlines()
            for line in lines:
                id = line.split('\t')[0].strip()
                file = line.split('\t')[1].strip()
                f2id[file]=id
            self.f2id = f2id
        return self.f2id
            

    def GetSettings(self):
        set = {}
        set['fragmentation'] = self.FindWindowByName("fragmentation").GetValue()
        set["mouseToHuman"] = self.FindWindowByName("mouseToHuman").GetValue()
        set["massAccuracyAnalysis"] = self.FindWindowByName("massAccuracyAnalysis").GetValue()
        set["makeGenePage"] = self.FindWindowByName("makeGenePage").GetValue()
        set["GeneToMake"] = self.FindWindowByName("genePage").GetValue()
        set["proteinFormatter"] = self.FindWindowByName("proteinFormatter").GetValue()
        set["kinaseAnalysis"] = self.FindWindowByName("kinaseAnalysis").GetValue()
        set["proteinFormatterPeptideStringency"] = int(self.FindWindowByName("proteinFormatterPeptideStringency").GetValue().strip())
        set["kinaseAnalysisPeptideStringency"] = int(self.FindWindowByName("kinaseAnalysisPeptideStringency").GetValue().strip())
        set["requirePhosphorylation"] = self.FindWindowByName("requirePhosphorylation").GetValue()
        set['xtractor'] = self.FindWindowByName("xTract").GetValue().strip()
        set['dim'] = self.FindWindowByName("dimensionRadioBox").GetStringSelection().strip()
        set['mfd'] = self.FindWindowByName("mfdCheck").GetValue()
        set['mzd'] = self.FindWindowByName("mzdCheck").GetValue()
        set['phosanalyze'] = self.FindWindowByName("phosanalyzerCheck").GetValue()
        set['flagKin'] = self.FindWindowByName("flagKin").GetValue()
        set['workflow'] = self.FindWindowByName("workFlow").GetValue().strip()
        set['dbase'] = self.FindWindowByName("dbaseName").GetValue().strip()
        set['organism'] = self.setOrganism(set['dbase'])
        set['quant'] = self.FindWindowByName("quant").GetValue().strip()
        set['dir'] = self.dir
        set['prMods'] = self.FindWindowByName("prMods").GetValue()
        set['fdr'] = self.FindWindowByName("fdr").GetValue().strip()
        set["MCO"] = float(self.FindWindowByName("MCO").GetValue().strip())
        set["HCD MCO"] = float(self.FindWindowByName("HCD MCO").GetValue().strip())
        set["MD_retrieve"] = self.FindWindowByName("retrieveMDscore").GetValue()

        self.set = set
        return set

    def _resultConsumer(self, delayedResult):
        jobID = delayedResult.getJobID()
        assert jobID == self.jobID
        try:
            result = delayedResult.get()
        except NotImplementedError, exc:
            a=1
            print "Result for job %s raised exception: %s" % (jobID, exc)
            return

    def OnHandle(self, event):
        self.abortEvent = delayedresult.AbortEvent()
        self.abortEvent.clear()        
        self.jobID += 1
        self.OnExeThread(1, self.abortEvent)
        #delayedresult.startWorker(self._resultConsumer, self.OnExeThread,
                                  #wargs=(self.jobID, self.abortEvent), jobID=self.jobID)
    
    def make_time(self, time_val):
        ret_time = str(time_val.tm_hour) + ":" + str(time_val.tm_min) + ':' + str(time_val.tm_sec)
        return ret_time            
    
    def post_message(self, message):
        self.FindWindowByName("MessageBox").Append(message)
    
    def OnExeThread(self, event, abortEvent):
        self.statusbar.SetStatusText("Executing...")
        start = time.localtime()
        #self.statusbar.SetStatusText(str(start))
        start_time = self.make_time(start)
        self.FindWindowByName("Execute").Disable()
        #self.statusbar.SetStatusText("Executing...")
        #self.FindWindowByName("dbaseName")
        dbase = self.FindWindowByName("dbaseName").GetValue().strip()
        rev = self.FindWindowByName("RevDbId").GetValue().strip()
        exp_dim = self.FindWindowByName("dimensionRadioBox").GetStringSelection().strip()
        fdr_sort = self.FindWindowByName("fdrSort").GetStringSelection().strip()
        self.FindWindowByName("MessageBox").Append("Starting Job (" + start_time + ')')
        
        saveParameters = self.FindWindowByName("SaveParameterCheck").GetValue()
        performSearch = self.FindWindowByName("PerformSearchCheck").GetValue()
        
        if not self.filenames and saveParameters:
            print "Target data file must be specified to create valid Comet parameters file!"
        
        for current_ms2file in self.filenames:
            if performSearch and os.path.splitext(current_ms2file)[1] == '.mgf':
                self.FindWindowByName("MessageBox").Append(self.dir + '\\' + current_ms2file)
                self.FindWindowByName("MessageBox").Append('MGF detected, converting...')
                #import mgf2ms2
                #mgf2ms2.convert(current_ms2file)
                converted_ms2file = current_ms2file[:-4] + '.ms2'
                comet_search.mgf_to_ms2(current_ms2file, outputfile = converted_ms2file)
                current_ms2file = converted_ms2file
                
                #self.FindWindowByName("MessageBox").Append(os.path.dirname(os.path.abspath(sys.argv[0])))
                #self.FindWindowByName("MessageBox").Append(str(os.path.exists('C:\\PyComet_v2014011_64bit\\library.zip\\mgf2ms2.pyc')))
                
                #if os.path.exists(os.path.dirname(os.path.abspath(sys.argv[0]) + '\\library.zip\\mgf2ms2.pyc')):
                #if os.path.exists('C:\\PyComet_v2014011_64bit\\library.zip\\mgf2ms2.pyc'):
                #p = subprocess.Popen('C:\\PyComet_v2014011_64bit\\library.zip\\mgf2ms2.py ' + self.dir + '\\' + current_ms2file)
                #p = subprocess.Popen('C:\\Python26\\Python.exe C:\\PyComet_v2014011_64bit\\mgf2ms2.py ' + self.dir + '\\' + current_ms2file)
                
                #p = subprocess.Popen(os.path.dirname(os.path.abspath(sys.argv[0])) + '\\library.zip\\mgf2ms2.py ' + self.dir + '\\' + current_ms2file)
                #p.wait()  
                #else:
                #    p = subprocess.Popen(os.path.dirname(os.path.abspath(sys.argv[0])) + '\\mgf2ms2.py ' + self.dir + '\\' + current_ms2file)
                #    p.wait() 
                #subprocess.Popen(args)
                #mgf2ms2.convert(self.dir + '\\' + current_ms2file, parent=self)
                
            varmods = []
            fxMods = []            
            self.FindWindowByName("MessageBox").Append(current_ms2file)
            for i in range(0, self.FindWindowByName("modsListBox").GetCount()):
                if self.FindWindowByName("modsListBox").IsChecked(i):
                    varmods.append(self.FindWindowByName("modsListBox").GetString(i))
            for i in range(0, self.FindWindowByName("fmodsListBox").GetCount()):
                if self.FindWindowByName("fmodsListBox").IsChecked(i):
                    fxMods.append(self.FindWindowByName("fmodsListBox").GetString(i))
            fm = ','.join(fxMods)
            vm = ','.join(varmods)
            mc = self.FindWindowByName("missedCleavages").GetValue().strip()
            enzyme = self.FindWindowByName("enzyme").GetValue().strip() 
            fdr = self.FindWindowByName("fdr").GetValue().strip() 
            precTol = self.FindWindowByName("precTol").GetValue().strip() 
            prodBinTol = self.FindWindowByName("prodBinTol").GetValue().strip()
            prodBinOffset = self.FindWindowByName("prodBinOffset").GetValue().strip()
            precTolUnit = self.FindWindowByName("precTolUnit").GetValue().strip()
            numthreads = self.FindWindowByName("NumThreads").GetValue().strip()
            numspectra = self.FindWindowByName("NumSpectra").GetValue().strip()            
            #ms2file, database, fixed_mods=None, var_mods=None, fdr="-PYes"
            
            fullDB = [x for x in DATABASES if dbase == os.path.basename(x.strip())][0]
            
            comet_search.perform_comet_search(self.dir + '\\' + current_ms2file, fullDB, '-FM=' + fm, '-VM=' + vm, "-P" + fdr, enzyme, mc, precTol,
                                              precTolUnit, prodBinTol, prodBinOffset, NumThreads=numthreads, NumSpectra=numspectra, ExpDim=exp_dim, RevDbId=rev, parent=self,
                                              fdrSort=fdr_sort, runType = (performSearch, saveParameters))        
        
        if exp_dim != '1D' and fdr == 'Yes':
            print 'fdr merged'
            self.post_message("Calc fdr for merged results... " + self.make_time(time.localtime()))
            process_comet_xml.merge_multiple_csv([COMET_DIR + '\\' + x[:-4]+'.pep.csv' for x in self.filenames], COMET_DIR + '\\Merged.csv')
            #raise ValueError("A")            
            process_comet_xml.calc_fdr(COMET_DIR + '\\Merged.csv', 0.01, fdr_sort, rev_txt=rev)
            #line = r'comet_search.py "' + COMET_DIR + '\\' + current_ms2file + '" "' + COMET_DIR + '\\' + dbase + '" -FM=' + fm + ' -VM=' + vm + ' -PNo'
            #print line
            #p = subprocess.Popen(line)
        self.statusbar.SetStatusText("Task Finished!!")
        end = time.localtime()
        end_time = self.make_time(end)        
        self.FindWindowByName("MessageBox").Append("Search finished: " + end_time)
        elapsed = time.mktime(end) - time.mktime(start)
        self.FindWindowByName("MessageBox").Append("Elapsed: " + str(elapsed) + ' seconds.')
        self.FindWindowByName("Execute").Enable()

    def OnEXE(self, event):#, abortEvent
        self.statusbar.SetStatusText("Executing...")
        #self.FindWindowByName("dbaseName")
        dbase = self.FindWindowByName("dbaseName").GetValue().strip()
        rev = self.FindWindowByName("RevDbId").GetValue().strip()
        exp_dim = self.FindWindowByName("dimensionRadioBox").GetStringSelection().strip()
        #C:\PyComet_v2014011_64bit> comet_search.exe C:\PyComet_v2014011_64bit\0621ms_0fl_010_MGFPeaklist.ms2 C:\PyComet_v2014011_64bit\uni_Mus+musculus_.decoy.fasta -FM=iTRAQ4plex,Methylthio(C) -VM=Oxidation(M) -PYes
        varmods = []
        fxMods = []
        for current_ms2file in self.filenames:
            for i in range(0, self.FindWindowByName("modsListBox").GetCount()):
                if self.FindWindowByName("modsListBox").IsChecked(i):
                    varmods.append(self.FindWindowByName("modsListBox").GetString(i))
            for i in range(0, self.FindWindowByName("fmodsListBox").GetCount()):
                if self.FindWindowByName("fmodsListBox").IsChecked(i):
                    fxMods.append(self.FindWindowByName("fmodsListBox").GetString(i))
            fm = ','.join(fxMods)
            vm = ','.join(varmods)
            mc = self.FindWindowByName("missedCleavages").GetValue().strip()
            enzyme = self.FindWindowByName("enzyme").GetValue().strip() 
            fdr = self.FindWindowByName("fdr").GetValue().strip() 
            precTol = self.FindWindowByName("precTol").GetValue().strip() 
            prodBinTol = self.FindWindowByName("prodBinTol").GetValue().strip()
            prodBinOffset = self.FindWindowByName("prodBinOffset").GetValue().strip()
            precTolUnit = self.FindWindowByName("precTolUnit").GetValue().strip()
            numthreads = self.FindWindowByName("NumThreads").GetValue().strip()
            #numspectra = self.FindWindowByName("NumSpectra").GetValue().strip()            
            #ms2file, database, fixed_mods=None, var_mods=None, fdr="-PYes"
            #comet_search.perform_comet_search(COMET_DIR + '\\' + current_ms2file, COMET_DIR + '\\' + dbase, '-FM=' + fm, '-VM=' + vm, "-P" + fdr, enzyme, mc, precTol, precTolUnit, prodBinTol, prodBinOffset, NumThreads=numthreads, NumSpectra=numspectra, ExpDim=exp_dim, RevDbId=rev)        
            comet_search.perform_comet_search(COMET_DIR + '\\' + current_ms2file, COMET_DIR + '\\' + dbase, '-FM=' + fm, '-VM=' + vm, "-P" + fdr, enzyme, mc, precTol, precTolUnit, prodBinTol, prodBinOffset, NumThreads=numthreads, ExpDim=exp_dim, RevDbId=rev)        
        
        if exp_dim != '1D' and fdr == 'Yes':
            print 'fdr merged'
            process_comet_xml.merge_multiple_csv([COMET_DIR + '\\' + x[:-4]+'.pep.csv' for x in self.filenames], COMET_DIR + '\\Merged.csv')
            #raise ValueError("A")            
            process_comet_xml.calc_fdr(COMET_DIR + '\\Merged.csv', 0.01, 'xcorr', rev_txt=rev)
            #line = r'comet_search.py "' + COMET_DIR + '\\' + current_ms2file + '" "' + COMET_DIR + '\\' + dbase + '" -FM=' + fm + ' -VM=' + vm + ' -PNo'
            #print line
            #p = subprocess.Popen(line)
        self.statusbar.SetStatusText("Task Finished!!")
        
    def onWorkflowEdit(self, event):
        workflowApp = WorkflowEditor(self)
        workflowApp.Show()
        print "Exited Show()."


class WorkflowEditor(wx.Frame):
    def __init__(self, parent):
        #import multiplierz.unimod as unimod
        #from comet_search import VAR_MODS, FIXED_MODS
        
        self.workflows = parent.read_workflow()
        #unimodDB = unimod.UnimodDatabase(os.path.join(myData, 'unimod.xml'))
        #self.unimods = sorted(unimodDB.get_all_mod_names())
        
        #modList = additionalMods + [''] + [x for x in self.unimods if x not in additionalMods]
        #self.varModList = additionalMods + [''] + sorted([x for x in VAR_MODS.keys() if x not in additionalMods])
        #self.fixModList = additionalMods + [''] + sorted([x for x in FIXED_MODS.keys() if x not in additionalMods])
        
        modNames = sorted([x for x in comet_search.modLookup.keys() if x not in additionalMods])
        self.varModList = additionalMods + [''] + modNames
        self.fixModList = additionalMods + [''] + modNames
        
        
        wx.Frame.__init__(self, parent, -1, "Workflow Editor", size = (500, 830))
        panel = wx.Panel(self, -1)
        
        gbs = wx.GridBagSizer(10, 5)
        
        workflowLabel = wx.StaticText(panel, -1, "Select Workflow: ")
        self.workflowSelect = wx.ComboBox(panel, -1,
                                          choices = self.workflows.keys() + ['<New workflow>'],
                                          name = 'Select Workflow')
        
        varModLabel = wx.StaticText(panel, -1, "Variable Modifications")
        fixModLabel = wx.StaticText(panel, -1, "Fixed Modifications")
        
        self.varModControl = wx.CheckListBox(panel, -1, choices = self.varModList,
                                             size = (220, 600), name = "Varmods")
        self.fixModControl = wx.CheckListBox(panel, -1, choices = self.fixModList,
                                             size = (220, 600), name = "Fixmods")
        
        self.saveButton = wx.Button(panel, -1, "Save Changes")
        self.closeButton = wx.Button(panel, -1, "Close")
        
        self.Bind(wx.EVT_COMBOBOX, self.loadWorkflow, self.workflowSelect)
        self.Bind(wx.EVT_BUTTON, self.saveWorkFlow, self.saveButton)
        self.Bind(wx.EVT_BUTTON, self.OnClose, self.closeButton)
        
        gbs.Add(workflowLabel, (0, 0), (1, 1))
        gbs.Add(self.workflowSelect, (0, 1), (1, 4), flag = wx.EXPAND)
        gbs.Add(varModLabel, (2, 0), (1, 1))
        gbs.Add(fixModLabel, (2, 3), (1, 1))
        gbs.Add(self.varModControl, (3, 0), (5, 2), flag = wx.EXPAND)
        gbs.Add(self.fixModControl, (3, 3), (5, 2), flag = wx.EXPAND)
        gbs.Add(self.saveButton, (8, 0), (1, 5), flag = wx.EXPAND)
        gbs.Add(self.closeButton, (9, 0), (1, 5), flag = wx.EXPAND)
        
        gbs.AddGrowableRow(5)
        
        box = wx.BoxSizer()
        box.Add(gbs, 0, wx.ALL, 10)
        panel.SetSizerAndFit(box)
        
    def loadWorkflow(self, event):
        print "loadWorkFlow!"
        workflowName = self.workflowSelect.GetValue()
        if workflowName == '<New workflow>': return
        
        fixMods, varMods = self.workflows[workflowName]

        
        self.fixModControl.SetCheckedStrings([x for x in fixMods if x and x in self.fixModList])
        self.varModControl.SetCheckedStrings([x for x in varMods if x and x in self.varModList])
        
        self.fixModControl.SetToolTip(wx.ToolTip('\n'.join(sorted(self.fixModControl.GetCheckedStrings()))))
        self.varModControl.SetToolTip(wx.ToolTip('\n'.join(sorted(self.varModControl.GetCheckedStrings()))))
        
    # NOTE- The "Save Changes" button looks like it should only change
    # the currently selected workflow?  Have it be that way?
    def saveWorkFlow(self, event):
        workflowName = self.workflowSelect.GetValue()
        
        if workflowName == '<New workflow>':
            nameRequest = wx.TextEntryDialog(self, "Name for new workflow:")
            nameRequest.ShowModal()
            workflowName = nameRequest.GetValue()
            if workflowName == '<New workflow>':
                raise Exception, "Can't name workflow %s" % workflowName
            
        varMods = [x for x in self.varModControl.GetCheckedStrings() if x]
        fixMods = [x for x in self.fixModControl.GetCheckedStrings() if x]
        
        self.workflows[workflowName] = fixMods, varMods
        
        #workflowFile = open(COMET_DIR + '\\workflows.txt', 'w')
        #workflowList = open(COMET_DIR + '\\workflow_list.txt', 'w')
        #for workflow, (fixmods, varmods) in self.workflows.items():
            #string = "%s | fm: %s | vm: %s\n" % (workflow,
                                                 #', '.join(fixmods),
                                                 #', '.join(varmods))
            #workflowFile.write(string)
            #workflowList.write(workflow + '\n')
            
        #workflowFile.close()
        #workflowList.close()
        
        workflowFile = open(workflow_record, 'w')
        for workflow, (fixmods, varmods) in self.workflows.items():
            fixStr = ';'.join(fixmods)
            varStr = ';'.join(varmods)
            string = '|'.join([workflow, varStr, fixStr]) + '\n'
            workflowFile.write(string)
        workflowFile.close()
        
        self.workflowSelect.Clear()
        self.workflowSelect.AppendItems(self.workflows.keys())
        
        
        self.GetParent().FindWindowByName('workFlow').Clear()
        self.GetParent().FindWindowByName('workFlow').AppendItems(self.workflows.keys())
        
        messdog = wx.MessageDialog(self, '%s saved.' % workflowName)
        messdog.ShowModal()
        
    def OnClose(self, evt):
        self.Close()
        

def startPyComet():
    app = wx.PySimpleApp()
    frame = InsertFrame(parent=None, id=-1)
    frame.Show()
    app.MainLoop()    

if __name__ == '__main__':
    app = wx.PySimpleApp()
    frame = InsertFrame(parent=None, id=-1)
    frame.Show()
    app.MainLoop()
        