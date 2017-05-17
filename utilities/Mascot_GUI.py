import wx
import os, sys
import tempfile

from multiplierz.mzGUI_standalone import file_chooser
from multiplierz import myData
from multiplierz.mzSearch import retrieveMascotReport
from multiplierz.mzSearch.mascot.interface import MascotSearcher
from multiplierz import settings
from multiplierz.post_process import combine_accessions, calculate_FDR

default_parfile = os.path.join(myData, '.Mascot_default.par')

parCtrls = [('USERNAME','Name'),
            ('USEREMAIL','Email'),
            ('DB','Database'),
            ('CHARGE','Default Charge'),
            ('CLE','Enzyme'),
            ('QUANTITATION','Quantitation'),
            ('INSTRUMENT','Instrument'),
            ('MASS','Use Averaged Mass'),
            ('TOL','Precursor Tol.'),
            ('ITOL','Fragment Tol.'),
            ('TOLU','Prec Unit'),
            ('ITOLU','Frag Unit'),
            ('MODS','Fixed Modifications'),
            ('IT_MODS','Variable Modifications'),
            ('PFA','Missed Cleavages'),
            ('ERRORTOLERANT', 'Error Tolerant Search'),
            ('bold_red', 'Require Bold Red'),
            ('show_query_data', 'Show Query Data'),
            ('show_same_set', 'Include Same-Set Protein Hits'),
            ('show_sub_set', 'Include Sub-Set Protein Hits'),
            ('rank_one', 'First-Rank Peptides Only'),
            ('combine_spectra', 'Combine Spectra'),
            ('run_fdr', 'FDR Filter (Requies Forward-Reverse Database)'),
            ('fdr_key', 'Reverse Accession Key'),
            ('ion_cutoff', 'Ion Score Cutoff')]
ctrlByPar = dict(parCtrls)

class MascotPanel(wx.Frame):
    def __init__(self, parent, login = None, password = None, writeback = (lambda x: None)):
        wx.Frame.__init__(self, None, -1, "Submit Mascot MS/MS Ions Search", 
                          style = wx.DEFAULT_FRAME_STYLE ^ (wx.RESIZE_BORDER | wx.MAXIMIZE_BOX))
        pane = wx.Panel(self, -1, style = wx.TAB_TRAVERSAL | wx.CLIP_CHILDREN)
        
        self.Bind(wx.EVT_CLOSE, self.onClose, self)
        
        self.login = login
        self.password = password
        
        self.ms = None
        self.DATABASES = []
        self.SHORTMODS = []
        self.LONGMODS = []
        self.ENZYMES = []
        self.CHARGES = []
        self.QUANTS = []
        self.INSTRUMENTS = []
        self.getMascotValues()
        
        menuBar = wx.MenuBar()
        fileMenu = wx.Menu()
        fileMenu_load = wx.MenuItem(fileMenu, -1, 'Load Parameter File')
        fileMenu_save = wx.MenuItem(fileMenu, -1, 'Save Parameter File')
        fileMenu_exit = wx.MenuItem(fileMenu, -1, "Exit")
        fileMenu.AppendItem(fileMenu_load)
        fileMenu.AppendItem(fileMenu_save)
        fileMenu.AppendSeparator()
        fileMenu.AppendItem(fileMenu_exit)
        self.Bind(wx.EVT_MENU, self.loadPar, fileMenu_load)
        self.Bind(wx.EVT_MENU, self.savePar, fileMenu_save)
        self.Bind(wx.EVT_MENU, self.onClose, fileMenu_exit)
        modMenu = wx.Menu()
        self.modMenu_allMods = wx.MenuItem(modMenu, -1, "Show Full Modification List",
                                      kind = wx.ITEM_CHECK)
        modMenu.AppendItem(self.modMenu_allMods)
        self.Bind(wx.EVT_MENU, self.swapModLists, self.modMenu_allMods)
        menuBar.Append(fileMenu, "File")
        menuBar.Append(modMenu, "Modifications")
        self.SetMenuBar(menuBar)
        
        
        
        
        def textCtrl(label):
            return (wx.StaticText(pane, -1, label),
                    wx.TextCtrl(pane, -1, name = label.replace('\n', ' ')))
        
        def checkCtrl(label, choices, size = None):
            return (wx.StaticText(pane, -1, label),
                    wx.CheckListBox(pane, -1, choices = choices,
                                    name = label.replace('\n', ' '),
                                    size = size))

        def choiceCtrl(label, choices):
            return (wx.StaticText(pane, -1, label),
                    wx.Choice(pane, -1, choices = choices,
                              name = label.replace('\n', ' ')))
        
        def checkBox(label):
            return wx.CheckBox(pane, -1, label, name = label)
        
        nameLabel, self.nameCtrl = textCtrl('Name')
        emailLabel, self.emailCtrl = textCtrl('Email')
        titleLabel, self.titleCtrl = textCtrl('Search Title')
        dataLabel, self.dataCtrl = textCtrl('Data File')
        precTolLabel, self.precTolCtrl = textCtrl('Precursor Tol.')
        fragTolLabel, self.fragTolCtrl = textCtrl('Fragment Tol.')
        
        dbaseLabel, self.dbaseCtrl = checkCtrl('Database', self.DATABASES)
        fixmodLabel, self.fixmodCtrl = checkCtrl('Fixed\nModifications', self.SHORTMODS, (50, 200))
        varmodLabel, self.varmodCtrl = checkCtrl('Variable\nModifications', self.SHORTMODS, (50, 200))
        self.Bind(wx.EVT_CHECKLISTBOX, self.updateTooltips, self.dbaseCtrl)
        self.Bind(wx.EVT_CHECKLISTBOX, self.updateTooltips, self.fixmodCtrl)
        self.Bind(wx.EVT_CHECKLISTBOX, self.updateTooltips, self.varmodCtrl)
        
        enzymeLabel, self.enzymeCtrl = choiceCtrl('Enzyme', self.ENZYMES)
        quantLabel, self.quantCtrl = choiceCtrl('Quantitation', self.QUANTS)
        chargeLabel, self.chargeCtrl = choiceCtrl('Default Charge', self.CHARGES)
        instrumentLabel, self.instrumentCtrl = choiceCtrl('Instrument', self.INSTRUMENTS)
        cleaveLabel, self.cleaveCtrl = choiceCtrl('Missed\nCleavages', map(str, range(10)))
        precUnitLabel, self.precUnitCtrl = choiceCtrl('Prec Unit', ['Da', 'mmu', '%%', 'ppm'])
        fragUnitLabel, self.fragUnitCtrl = choiceCtrl('Frag Unit', ['Da', 'mmu', '%%', 'ppm'])
        precUnitLabel.Destroy()
        fragUnitLabel.Destroy()
        
        
        self.errorTol = checkBox("Error Tolerant Search")
        
        #self.monoOrAverage = wx.CheckBox(pane, -1, "Use Averaged Mass", 
                                         #name = "Use Averaged Mass")
        self.monoOrAverage = checkBox("Use Averaged Mass")
        
        self.downloadSearch = checkBox("Download Results After Search Completes")
        self.Bind(wx.EVT_CHECKBOX, self.toggleSearchMode, self.downloadSearch)
        
        self.boldRed = checkBox("Require Bold Red")
        self.showData = checkBox("Show Query Data")
        self.sameSet = checkBox("Include Same-Set Protein Hits")
        self.subSet = checkBox("Include Sub-Set Protein Hits")
        self.firstRank = checkBox("First-Rank Peptides Only")
        self.combineSpectra = checkBox("Combine Spectra")
        self.fdr_filter = checkBox("FDR Filter (Requies Forward-Reverse Database)")
        self.fdrKeyLabel, self.fdrKeyCtrl = textCtrl('Reverse Accession Key')
        self.ionLabel, self.ionCtrl = textCtrl('Ion Score Cutoff')
        
        self.browseButton = wx.Button(pane, -1, "Browse")
        self.goButton = wx.Button(pane, -1, "Submit")
        self.Bind(wx.EVT_BUTTON, self.openData, self.browseButton)
        self.Bind(wx.EVT_BUTTON, self.submitSearch, self.goButton)
        
        self.gbs = wx.GridBagSizer(10, 10)
        
        # Really probably should divide things into sub-boxes.  Visual grouping,
        # also easier to modify.
        
        headerBox = wx.GridBagSizer(10, 10)
        headerLayout = [(nameLabel, (0, 0), wx.ALIGN_RIGHT), (self.nameCtrl, (0, 1), wx.ALIGN_LEFT),
                        (emailLabel, (0, 3), wx.ALIGN_RIGHT), (self.emailCtrl, (0, 4), wx.ALIGN_LEFT),
                        (titleLabel, (1, 0), wx.ALIGN_RIGHT), (self.titleCtrl, (1, 1), wx.EXPAND, (1, 4))]
        
        dbBox = wx.GridBagSizer(10, 10)
        dbLayout = [(dbaseLabel, (0, 0), wx.ALIGN_RIGHT), (self.dbaseCtrl, (0, 1), wx.EXPAND, (3, 2)),
                    (enzymeLabel, (0, 4), wx.ALIGN_RIGHT), (self.enzymeCtrl, (0, 5), wx.ALIGN_LEFT),
                    (cleaveLabel, (1, 4), wx.ALIGN_RIGHT), (self.cleaveCtrl, (1, 5), wx.ALIGN_LEFT),
                    (self.errorTol, (2, 4), wx.EXPAND, (1, 2))]
                    #(self.monoOrAverage, (2, 3), wx.EXPAND, (1, 2))]
        
        modBox = wx.GridBagSizer(10, 10)
        modLayout = [(fixmodLabel, (0, 0), wx.ALIGN_RIGHT), (self.fixmodCtrl, (0, 1), wx.EXPAND, (3, 2)),
                     (varmodLabel, (0, 3), wx.ALIGN_RIGHT), (self.varmodCtrl, (0, 4), wx.EXPAND, (3, 2))]
        
        ctrlBox = wx.GridBagSizer(10, 10)
        ctrlLayout = [(quantLabel, (0, 0), wx.ALIGN_RIGHT), (self.quantCtrl, (0, 1), wx.EXPAND, (1, 2)),
                      (self.monoOrAverage, (0, 3), wx.ALIGN_RIGHT, (1, 2)),
                      (precTolLabel, (1, 0), wx.ALIGN_RIGHT), (self.precTolCtrl, (1, 1), wx.EXPAND),
                      (self.precUnitCtrl, (1, 2), wx.ALIGN_LEFT),
                      (fragTolLabel, (1, 3), wx.ALIGN_RIGHT), (self.fragTolCtrl, (1, 4), wx.EXPAND),
                      (self.fragUnitCtrl, (1, 5), wx.ALIGN_LEFT),
                      (chargeLabel, (2, 0), wx.ALIGN_RIGHT), (self.chargeCtrl, (2, 1), wx.ALIGN_LEFT),
                      (instrumentLabel, (2, 3), wx.ALIGN_RIGHT), 
                      (self.instrumentCtrl, (2, 4), wx.ALIGN_LEFT, (1, 2))]
        
        resultBox = wx.GridBagSizer(10, 10)
        resultLayout = [(self.downloadSearch, (0, 0), wx.ALIGN_CENTER, (1, 5)),
                        (self.showData, (1, 1), wx.ALIGN_LEFT, (1, 2)), (self.sameSet, (1, 3), wx.ALIGN_LEFT, (1, 2)),
                        (self.firstRank, (2, 1), wx.ALIGN_LEFT, (1, 2)), (self.subSet, (2, 3), wx.ALIGN_LEFT, (1, 2)),
                        (self.combineSpectra, (3, 1), wx.ALIGN_LEFT, (1, 2)), (self.boldRed, (3, 3), wx.ALIGN_LEFT, (1, 2)),
                        (self.fdr_filter, (4, 1), wx.ALIGN_LEFT, (1, 2)),
                        (self.ionLabel, (4, 3), wx.ALIGN_RIGHT), (self.ionCtrl, (4, 4), wx.ALIGN_LEFT),
                        (self.fdrKeyLabel, (5, 1), wx.ALIGN_RIGHT), (self.fdrKeyCtrl, (5, 2), wx.ALIGN_LEFT)]
        
        
        
        
        for i, (box, layout) in enumerate([(headerBox, headerLayout), (dbBox, dbLayout), 
                                           (modBox, modLayout), (ctrlBox, ctrlLayout),
                                           (resultBox, resultLayout)]):
            for element in layout:
                if len(element) == 3:
                    widget, pos, flag = element
                    span = (1, 1)
                elif len(element) == 4:
                    widget, pos, flag, span = element
                box.Add(widget, pos = pos, span = span, flag = flag)
            
            self.gbs.Add(box, (i*2, 0), span = (1, 3), flag = wx.EXPAND)
            self.gbs.Add(wx.StaticLine(pane, -1, style = wx.LI_HORIZONTAL),
                         (i*2+1, 0), span = (1, 3), flag = wx.EXPAND)
            
        
        self.gbs.Add(dataLabel, (i*2+2, 0), flag = wx.ALIGN_RIGHT)
        self.gbs.Add(self.dataCtrl, (i*2+2, 2), flag = wx.EXPAND)
        self.gbs.Add(self.browseButton, (i*2+2, 1), flag = wx.ALIGN_LEFT)
        self.gbs.Add(self.goButton, (i*2+4, 0), span = (1, 3), flag = wx.EXPAND)
        
        self.gbs.AddGrowableCol(1)    
        
        modBox.AddGrowableCol(1)
        modBox.AddGrowableCol(4)
        modBox.AddGrowableRow(2)
        headerBox.AddGrowableCol(1)
        
        overBox = wx.BoxSizer()
        overBox.Add(self.gbs, 0, wx.ALL, 10)

        pane.SetSizerAndFit(overBox)
        self.SetClientSize(pane.GetSize())
        
        if os.path.exists(default_parfile):
            self.loadPar(None, default_parfile)
        
        self.toggleSearchMode(None)
        self.updateTooltips(None)
        self.Show()
        
    def getMascotValues(self):
        self.ms = MascotSearcher(settings.get_mascot_server(), settings.get_mascot_version())
        if settings.get_mascot_security():
            self.ms.login(self.login, self.password)
        fields = self.ms.get_fields(settings.get_mascot_version()) # Error presentation?
        
        self.DATABASES = fields['DB']
        self.SHORTMODS = sorted(list(set(fields['IT_MODS'] + fields['MODS'])))
        self.LONGMODS = sorted(fields['ALLMODS'])
        #self.FIXMODS = fields['MASTER_MODS']
        self.ENZYMES = fields['CLE']
        self.CHARGES = fields['CHARGE']
        self.QUANTS = fields['QUANTITATION']
        self.INSTRUMENTS = fields['INSTRUMENT'] 
        #print "FOO"
        
    def toggleSearchMode(self, event):
        mode = self.downloadSearch.GetValue()
        self.boldRed.Enable(mode)
        self.showData.Enable(mode)
        self.sameSet.Enable(mode)
        self.subSet.Enable(mode)
        self.firstRank.Enable(mode)
        self.combineSpectra.Enable(mode)
        self.fdr_filter.Enable(mode)    
        self.ionLabel.Enable(mode)
        self.ionCtrl.Enable(mode)
        self.fdrKeyLabel.Enable(mode)
        self.fdrKeyCtrl.Enable(mode)
        
    def loadPar(self, event, filename = None):
        if not filename:
            filename = file_chooser('Select a Mascot parameters file:',
                                    wildcard = 'PAR|*.par|All|*.*')
        if not filename:
            return
        
        with open(filename, 'r') as par:
            for line in par:
                line = line[:line.find('#')].strip() # # is the comment character.
                if '=' not in line:
                    continue
                key, value = line.split('=')
                try:
                    ctrl = self.FindWindowByName(ctrlByPar[key])
                    assert ctrl
                except (KeyError, AssertionError):
                    print "Unused key: %s" % key
                    continue
                if isinstance(ctrl, wx.CheckListBox):
                    values = [x.strip() for x in value.split(',') if x]
                    try:
                        ctrl.SetCheckedStrings(values)
                    except AssertionError as err:
                        print 'Exception- %s (in %s)' % (str(err), ctrl.Name)
                elif isinstance(ctrl, wx.CheckBox):
                    if key == 'MASS':
                        ctrl.SetValue(value == 'AVERAGE')
                    else:
                        if value:
                            ctrl.SetValue(float(value))
                        else:
                            ctrl.SetValue(False)
                elif isinstance(ctrl, wx.Choice):
                    num = ctrl.FindString(value)
                    if num >= 0:
                        ctrl.SetSelection(num)
                    else:
                        ctrl.Append(value)
                        ctrl.SetSelection(ctrl.Count-1)
                else:
                    ctrl.SetValue(value)

        self.updateTooltips(None)
        print "Loaded parfile."
        
    def collectParameters(self):
        parameters = []
        for key, ctrlname in parCtrls:
            ctrl = self.FindWindowByName(ctrlname)
            if isinstance(ctrl, wx.CheckListBox):
                value = ','.join(ctrl.GetCheckedStrings())
            elif isinstance(ctrl, wx.Choice):
                value = ctrl.GetString(ctrl.GetCurrentSelection())
            elif isinstance(ctrl, wx.CheckBox):
                #assert ctrl == self.monoOrAverage, "Rewrite for new checkbox!"
                if key == 'MASS':
                    value = 'AVERAGE' if ctrl.GetValue() else 'MONOISOTOPIC' 
                else:
                    value = int(ctrl.GetValue())
            else:
                value = ctrl.GetValue()      
            parameters.append((key, value))
        return parameters
        
    def savePar(self, event, filename = None):
        if not filename:
            filename = file_chooser('Save Mascot parameters file:', mode = 'w',
                                    wildcard = 'PAR|*.par|All|*.*')
        
        parameters = self.collectParameters()
        with open(filename, 'w') as par:
            for key, value in parameters:
                par.write('%s=%s\n' % (key, value))
        print "Saved parfile."
            
    def swapModLists(self, event):
        fixmods = self.fixmodCtrl.GetCheckedStrings()
        varmods = self.varmodCtrl.GetCheckedStrings()
        self.fixmodCtrl.Clear()
        self.varmodCtrl.Clear()
        if self.modMenu_allMods.IsChecked():
            mods = self.LONGMODS
        else:
            mods = self.SHORTMODS
        for mod in mods:
            self.fixmodCtrl.Append(mod)
            self.varmodCtrl.Append(mod) 
        
        abandonFixed = []
        for fixmod in fixmods:
            index = self.fixmodCtrl.FindString(fixmod)
            if index == -1:
                abandonFixed.append(fixmod)
            else:
                self.fixmodCtrl.Check(index)
        abandonVar = []
        for varmod in varmods:
            index = self.varmodCtrl.FindString(varmod)
            if index == -1:
                abandonVar.append(varmod)
            else:
                self.varmodCtrl.Check(index)
        
        if abandonFixed or abandonVar:
            if abandonFixed:
                fixstr = '\nFixed Mods;\n%s\n' % '\n'.join(abandonFixed)
            else:
                fixstr = ''
            if abandonVar:
                varstr = '\nVariable Mods;\n%s' % '\n'.join(abandonVar)
            else:
                varstr = ''
            wx.MessageBox('NOTE- some modifications have been dropped;\n%s %s' % (fixstr, varstr))
        
        self.updateTooltips(None)
    
    def updateTooltips(self, event):
        for ctrl in [self.fixmodCtrl, self.varmodCtrl, self.dbaseCtrl]:
            if event and ctrl != event.GetEventObject():
                continue
        
            tipstr = '\n'.join(sorted(ctrl.GetCheckedStrings()))
            ctrl.SetToolTip(wx.ToolTip(tipstr))
            
    def onClose(self, event):
        self.savePar(None, default_parfile)
        self.Destroy()
    
    def openData(self, event):
        datafile = file_chooser('Open MS data file:', mode = 'r',
                                wildcard = 'MGF|*.MGF|All|*.*')
        if not datafile:
            return
        self.dataCtrl.SetValue(datafile)
        
    def submitSearch(self, event):
        self.goButton.Enable(False)
        
        datafile = self.dataCtrl.GetValue()
        parameters = self.collectParameters()
        
        if not (self.ms != None and self.ms.logged_in):
            # This would be very odd.
            self.ms = MascotSearcher(MascotSearcher(settings.get_mascot_server(),
                                                    settings.get_mascot_version()))
            self.ms.login(self.login, self.password)
        
        dat_id = None
        try:
            wx.BeginBusyCursor()
            assert os.path.exists(datafile), '%s not found!' % datafile
            dat_id, err = self.ms.search(parameters, datafile)
            if err:
                raise RuntimeError, 'Mascot error: %s' % repr(err)
            if not dat_id:
                raise RuntimeError, ('.DAT id not returned; usually this '
                                     'is due to a connection error.')
        except AssertionError as err:
            wx.MessageBox('Search process encountered an error:\n\n%s' % repr(err),
                          "Could not run search.")    
            raise err
        finally:
            wx.EndBusyCursor()
            self.goButton.Enable(True)         
        
        if not (self.downloadSearch.GetValue() and dat_id):
            if dat_id:
                wx.MessageBox("Successfully submitted search; search log # %s" % dat_id)
                return
        
        try:
            wx.BeginBusyCursor()
            self.goButton.Enable(False)
            resultfile = retrieveMascotReport([dat_id],
                                              login_name = self.login,
                                              password = self.password,
                                              rank_one = self.firstRank.GetValue(),
                                              ion_cutoff = float(self.ionCtrl.GetValue()),
                                              bold_red = self.boldRed.GetValue(),
                                              max_hits = 999999,
                                              show_query_data = self.showData.GetValue(),
                                              show_same_set = self.sameSet.GetValue(),
                                              show_sub_set = self.subSet.GetValue())[0]
            if self.combineSpectra.GetValue():
                resultfile = combine_accessions(resultfile, resultfile)
            if self.fdr_filter.GetValue():
                fdrKey = self.fdrKeyCtrl.GetValue()
                if not fdrKey:
                    fdrKey = 'rev_'
                resultfile = calculate_FDR(resultfile, outputfile = resultfile,
                                           decoyString = fdrKey)
            wx.MessageBox('Wrote search session %s to %s' % (dat_id, resultfile),
                          'Mascot search completed.')
        except Exception as err:
            wx.MessageBox('Result download encountered an error:\n\n%s' % repr(err),
                          "Could not run search.")   
            raise err
        finally:
            wx.EndBusyCursor()
            self.goButton.Enable(True)









class LoginDialog(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, "Mascot Login")

        gbs = wx.GridBagSizer(10, 5)

        pos = iter([(0,0), (0,1), (1,0), (1,1), (2,0), (2,1)])

        gbs.Add( wx.StaticText(self, -1, "Login:", style=wx.ALIGN_RIGHT), pos.next(), flag=wx.EXPAND )
        gbs.Add( wx.TextCtrl(self, -1, "", size=(75,21),
                             name="Login"), pos.next() )

        gbs.Add( wx.StaticText(self, -1, "Password:", style=wx.ALIGN_RIGHT), pos.next(), flag=wx.EXPAND )
        gbs.Add( wx.TextCtrl(self, -1, "", style=wx.PASSWORD, size=(75,21),
                             name="Password"), pos.next() )

        btn = wx.Button(self, wx.ID_OK)
        btn.SetDefault()
        gbs.Add( btn, pos.next() )
        gbs.Add( wx.Button(self, wx.ID_CANCEL), pos.next() )

        box = wx.BoxSizer()
        box.Add(gbs, 0, wx.ALL, 10)

        self.SetSizerAndFit(box)


username = None
password = None
def runMascotSearch(parent, writeback = None):
    global username
    global password 
    
    if settings.mascot_security and username == None and password == None:
        dlg = LoginDialog(None)
        result = dlg.ShowModal()
        if result == wx.ID_OK:
            username, password = (dlg.FindWindowByName("Login").GetValue(),
                                  dlg.FindWindowByName("Password").GetValue())        
        dlg.Destroy()

    try:
        mascot_frame = MascotPanel(parent,
                                   login = username, 
                                   password = password)
    except RuntimeError as err:
        username = None
        password = None
        wx.MessageBox(str(err))
        raise err
    
    mascot_frame.Show()
    
        


if __name__ == '__main__':
    foo = wx.App(0)
    bar = MascotPanel(None, 'pipeline', 'pipeline')
    foo.MainLoop()
        
        
        
        
        
        
        