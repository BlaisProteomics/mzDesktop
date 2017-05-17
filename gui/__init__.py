# Copyright 2008 Dana-Farber Cancer Institute
# multiplierz is distributed under the terms of the GNU Lesser General Public License
#
# This file is part of multiplierz.
#
# multiplierz is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# multiplierz is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with multiplierz.  If not, see <http://www.gnu.org/licenses/>.

__author__ = 'Jignesh Parikh, James Webber, William Max Alexander'

__all__ = [ 'console', 'digest', 'fragment', 'full_report',
            'info_file', 'mascot_report',
            'mascot_web', 'multi_detect', 'multi_filter', 'peaks',
            'peak_viewer', 'preferences', 'report_format',
            'report_viewer' ]

import __builtin__

import os
import sys
import time
import webbrowser
import wx
import wx.html

from wx.lib.agw import flatnotebook
from wx.lib.agw.flatnotebook import PageContainer

from multiplierz import myData, myTemp, logger_message, __version__, mzGUI_standalone





class Redirection():
    def __init__(self, statusbar, stdchannel):
        self.statusbar = statusbar
        self.channel = stdchannel
    def write(self, string):
        if string.strip():
            self.statusbar.SetStatusText(string.strip(), 1)
        self.channel.write(string)


#class BasicTab(wx.Panel):
class BasicTab(PageContainer):
    '''Base class for Multiplierz tabs. A tab is just a wx.Panel with some
    extra methods that access its grandparent (the main frame of Multiplierz).
    '''
    def set_status(self, text, index):
        '''Sets the status bar of the main window. The interface is
        the same as the wx.StatusBar.SetStatusText method.
        '''
        mainwindow = self.GetGrandParent()
        while mainwindow and not isinstance(mainwindow, MultiplierzFrame):
            mainwindow = mainwindow.GetParent()
        if mainwindow:
            mainwindow.statusbar.SetStatusText(text, index)

    def get_icon(self):
        '''Returns the icon of the main frame, for creating new windows.
        '''
        mainwindow = self.GetGrandParent()
        while mainwindow and not isinstance(mainwindow, MultiplierzFrame):
            mainwindow = mainwindow.GetParent()
        if mainwindow:        
            return mainwindow.GetIcon()
        else:
            raise NotImplementedError, "What are you even doing to the GUI?"




# This expects add-ons to be in a standard format:
# - they are Python scripts (.py files) (although this could change with mz-import)
# - they have a 'run%name' function, where %name is the name of the script
#
# In other words, this code looks in scripts_dir, adds those folders to sys.path,
# imports the python it finds, and adds a menu item for each one
class ScriptMenuItem:
    """
    This is a wrapper class for any add-on modules the user has.

    The constructor imports the module given (note: it takes only the name,
    no extension or path) and returns a callable instance that can be given
    to wx as a callback function.

    The only requirement is that it expects a special 'run%name' function in
    the script--and that the path should have already been added to sys.path.
    If it can't find the module it'll raise an exception--if it can't find the
    'run%name' function it will alert the user.

    Future consideration: implement a new importer that can handle .mz files
    """
    def __init__(self, name):
        """
        Creates an instance. Stores the name of the module (for lookup) and a
        reference to the module itself (for reloading)
        """
        self.name = name[3:] # strip off the 'RC_' prefix
        __builtin__.__import__(name) # import the module
        self.mod = sys.modules[name] # keep reference to this module

    def __call__(self, event):
        """
        This allows the instance to act as a callback for the GUI. It simply
        reloads the module and then calls the modules 'run%name' function,
        which is assumed to take no arguments.
        """
        reload(self.mod) # reload the module, this allows dynamic modification of script
        if ('run%s' % self.name) in self.mod.__dict__:
            self.mod.__dict__['run%s' % self.name]() # run the 'run%name' function
        else:
            mzGUI.alerts('Function "run%s" not found' % self.name, 'Error') # else, alert user


bugMessage = """
Multiplierz mzDesktop is a complex bioinformatics suite that is applicable
to many scientific workflows and capable of handling data from many
different kinds of equipment; as a result, no single lab has the resources to
rigorously test the multitude of use cases mzDesktop users may encounter.  We
greatly appreciate users taking the time to report any problems they
encounter using multiplierz.

Please describe the problem below; it is also typically helpful to include
the Python stack trace that accompanied the error (if any) either in the text
box or in an attached text file. If the problem encountered is specific to a
(reasonably small) data file, this may also be attached. Press 'Send' to
email the bug report and attachment(s).

"""

class BugFrame(wx.Frame):
    def __init__(self, parent):
        wx.Frame.__init__(self, parent, -1, 'Report Bug', size=(500,600),
                          style=wx.DEFAULT_FRAME_STYLE ^ (wx.RESIZE_BORDER | wx.MAXIMIZE_BOX))
        
        panel = wx.Panel(self, -1)
        
        #bugtext = wx.TextCtrl(panel, -1, value = bugMessage, style = wx.TE_MULTILINE)
        bugtext = wx.StaticText(panel, -1, bugMessage)
        
        nameLabel = wx.StaticText(panel, -1, "Name:")
        emailLabel = wx.StaticText(panel, -1, "Contact Email:")
        descLabel = wx.StaticText(panel, -1, "Bug Description:")
        
        self.nameBox = wx.TextCtrl(panel, -1)
        self.emailBox = wx.TextCtrl(panel, -1)
        self.descBox = wx.TextCtrl(panel, -1, style = wx.TE_MULTILINE)
        
        attachLabel = wx.StaticText(panel, -1, "Attachments:")
        self.attachCtrl = wx.TextCtrl(panel, -1)
        attachButton = wx.Button(panel, -1, "Browse")
        
        sendButton = wx.Button(panel, -1, "Send")
        
        gbs = wx.GridBagSizer(2, 2)
        gbs.Add(bugtext, (0, 0), span = (1, 3), flag = wx.EXPAND)
        gbs.Add(wx.StaticLine(panel, -1, style = wx.HORIZONTAL), (1, 0), 
                span = (1, 3), flag = wx.EXPAND)
        gbs.Add(nameLabel, (2, 0), flag = wx.ALIGN_RIGHT)
        gbs.Add(self.nameBox, (2, 1), flag = wx.EXPAND)
        gbs.Add(emailLabel, (3, 0), flag = wx.ALIGN_RIGHT)
        gbs.Add(self.emailBox, (3, 1), flag = wx.EXPAND)
        gbs.Add(descLabel, (4, 0), flag = wx.ALIGN_RIGHT)
        gbs.Add(self.descBox, (5, 0), span = (3, 3), flag = wx.EXPAND)
        gbs.Add(attachLabel, (9, 0), flag = wx.ALIGN_RIGHT)
        gbs.Add(self.attachCtrl, (9, 1), flag = wx.EXPAND)
        gbs.Add(attachButton, (9, 2), flag = wx.ALIGN_LEFT)
        gbs.Add(wx.StaticLine(panel, -1, style = wx.HORIZONTAL), (10, 0), 
                span = (1, 3), flag = wx.EXPAND)
        gbs.Add(sendButton, (11, 1))
        
        gbs.AddGrowableCol(1)
        gbs.AddGrowableRow(6)
        
        self.Bind(wx.EVT_BUTTON, self.onBrowse, attachButton)
        self.Bind(wx.EVT_BUTTON, self.onSend, sendButton)
        
        overBox = wx.BoxSizer()
        overBox.Add(gbs, 1, wx.ALL | wx.EXPAND, 10)
        panel.SetSizerAndFit(overBox)
        self.Show()
        
    def onBrowse(self, event):
        files = mzGUI_standalone.file_chooser(title = 'Choose files to send:',
                                              mode = 'm', wildcard = '*.*')
        self.attachCtrl.SetValue('; '.join(files))
    
    def onSend(self, event):
        #dialog = wx.MessageDialog(self, "The bug report feature is disabled until this is actually published.  (Sorry, Guillaume!)")
        contactEmail = 'williamM_alexander@dfci.harvard.edu'

        errorSenderEmail
        
        
        dialog.ShowModal()
        
        
class AboutFrame(wx.Frame):
    def __init__(self, parent):
        wx.Frame.__init__(self, parent, -1, 'About Multiplierz', size=(500,600),
                          style=wx.DEFAULT_FRAME_STYLE ^ (wx.RESIZE_BORDER | wx.MAXIMIZE_BOX))

        # multiplierz logo
        multiplierz_logo_file = os.path.join(install_dir, 'images', 'multiplierzlogo.png')
        # Blais logo
        blais_logo_file = os.path.join(install_dir, 'images', 'BlaisLogo.JPG')

        pane = wx.Panel(self, -1)
        pane.SetBackgroundColour(wx.Colour(255,255,255))

        self.SetIcon(parent.GetIcon())

        gbs = wx.GridBagSizer(10,10)

        #Add image
        try:
            logo = wx.Image(multiplierz_logo_file, wx.BITMAP_TYPE_ANY)
            gbs.Add( wx.StaticBitmap(pane, -1, wx.BitmapFromImage(logo)),
                     (0,0), flag=wx.ALIGN_CENTER )
        except Exception:
            print "Failure to load frame icon."

        font = wx.Font(10, 74, 90, 92, 0, 'Verdana')

        version_text = wx.StaticText(pane, -1, "Geryon Edition %s" % __version__,
                                     style=wx.ALIGN_CENTER)
        version_text.SetFont(font)
        gbs.Add( version_text,
                 (1,0), flag=wx.ALIGN_CENTER )

        help_link = wx.HyperlinkCtrl(pane, -1, 'Multiplierz Wiki',
                                     r'https://github.com/MaxAlex/multiplierz/wiki')
        help_link.SetFont(font)
        gbs.Add( help_link,
                 (2,0), flag=wx.ALIGN_CENTER )

        about_text = wx.StaticText(pane, -1, 'Authors:\nJignesh Parikh, James Webber, Max Alexander\n\nMarto Lab\nCancer Biology',
                                   style=wx.ALIGN_CENTER)
        about_text.SetFont(font)

        gbs.Add( about_text,
                 (3,0), flag=wx.ALIGN_CENTER )

        contact_link = wx.HyperlinkCtrl(pane, -1, 'Contact: Max Alexander',
                                        'mailto:williamM_alexander@dfci.harvard.edu')
        contact_link.SetFont(font)
        gbs.Add( contact_link,
                 (4,0), flag=wx.ALIGN_CENTER )

        try:
            blais_logo =  wx.BitmapButton(pane, -1,
                                          wx.BitmapFromImage(wx.Image(blais_logo_file,
                                                                      wx.BITMAP_TYPE_ANY)))
            gbs.Add( blais_logo,
                     (5,0), flag=wx.ALIGN_CENTER )            
        except Exception:
            print "Failure to load logo icon."
            
            


        blais_logo.SetCursor(wx.StockCursor(wx.CURSOR_HAND))
        blais_logo.Bind(wx.EVT_BUTTON, self.on_click_blais_logo)

        dfci_text = wx.StaticText(pane, -1, 'Dana-Farber Cancer Institute, 2009-2017',
                                  style=wx.ALIGN_CENTER)
        dfci_text.SetFont(font)
        gbs.Add( dfci_text,
                 (6,0), flag=wx.ALIGN_CENTER )

        ok_btn = wx.Button(pane, wx.ID_OK)
        gbs.Add( ok_btn,
                 (7,0), flag=wx.ALIGN_CENTER )
        ok_btn.Bind(wx.EVT_BUTTON, lambda e: self.Close())
        ok_btn.SetDefault()

        gbs.AddGrowableCol(0)
        gbs.AddGrowableRow(0)

        box = wx.BoxSizer()
        box.Add(gbs, 1, wx.ALL, 5)

        pane.SetSizerAndFit(box)

    def on_click_blais_logo(self, event):
        webbrowser.open_new_tab('http://blais.dfci.harvard.edu')




class MultiplierzFrame(wx.Frame):
    def __init__(self, parent, icon, scripts_dir):
        wx.Frame.__init__(self, parent, -1, "mzDesktop", size=(800,620))

        self.SetMinSize((800,600))

        # add icon
        self.SetIcon(icon)

        # add menu bar
        menu_bar = wx.MenuBar()

        file_menu = wx.Menu()
        
        # Removed due mostly to matplotlib 'recapturing mouse' errors and
        # a few bugs from changed legacy code.
        #peak_viewer = file_menu.Append(-1, "&Open MS Data File\tCtrl+O",
                                       #"Interactive Peak Viewer")
        #self.Bind(wx.EVT_MENU, self.on_peak_viewer, peak_viewer)

        report_viewer = file_menu.Append(-1, "Open &Multiplierz Report\tCtrl+M",
                                         "Report Viewer")
        self.Bind(wx.EVT_MENU, self.on_report_viewer, report_viewer)

        file_menu.AppendSeparator()

        file_menu_preferences = file_menu.Append(-1, "&Preferences\tF2", "Multiplierz Preferences")
        self.Bind(wx.EVT_MENU, self.on_preferences, file_menu_preferences)

        file_menu.AppendSeparator()

        file_menu_exit = file_menu.Append(wx.ID_EXIT, "&Quit\tCtrl+Q", "Terminate the program")
        self.Bind(wx.EVT_MENU, self.on_exit, file_menu_exit)
        self.Bind(wx.EVT_CLOSE, self.on_exit)

        menu_bar.Append(file_menu, "&File")

        #logger_message(50, 'Inititalizing Tools Menu...') 

        tools_menu = wx.Menu()

        #full_report_menu = tools_menu.Append(-1, "Mascot Report\tCtrl+W",
                                             #"Full Report Wizard for Single Mascot File")
        
        #self.Bind(wx.EVT_MENU, self.on_full_report, full_report_menu)
        
        p2g_menu = tools_menu.Append(-1, "Pep2Gene Utility",
                                     "Prepare and Use Pep2Gene Databases for Gene Annotation")
                
        self.Bind(wx.EVT_MENU, self.on_pep2gene, p2g_menu)
        
        mzTransform_menu = tools_menu.Append(-1, "mzTransform",
                                             "Batch processing of intact protein data.")
        self.Bind(wx.EVT_MENU, self.on_mzTransform, mzTransform_menu)
        
        silac_menu = tools_menu.Append(-1, "SILAC Analysis",
                                       "Annotate Search Results with SILAC Ratio Data")
        
        self.Bind(wx.EVT_MENU, self.on_silac, silac_menu)
        
        feature_menu = tools_menu.Append(-1, "Feature Detection",
                                         "Annotate Search Results with Spectrometric Source Feature Data")
        
        self.Bind(wx.EVT_MENU, self.on_featureDet, feature_menu)
        
        labelEv_menu = tools_menu.Append(-1, "Label Coverage Evaluation",
                                         "Evaluates the labelling efficiency of SILAC/TMT/iTRAQ.")
        self.Bind(wx.EVT_MENU, self.on_labelEv, labelEv_menu)        

        tools_menu.AppendSeparator()
        
        pycomet_menu = tools_menu.Append(-1, "Comet Search",
                                         "GUI interface to the Comet database search engine.")
        self.Bind(wx.EVT_MENU, self.on_pycomet, pycomet_menu)        
        
        xtandem_menu = tools_menu.Append(-1, "XTandem Search",
                                         "GUI interface to the XTandem database search engine.")
        self.Bind(wx.EVT_MENU, self.on_xtandem, xtandem_menu)
        
        mascot_menu = tools_menu.Append(-1, "Mascot Search",
                                        "GUI interface to submit searches to a Mascot server.")
        self.Bind(wx.EVT_MENU, self.on_mascot, mascot_menu)
        
        tools_menu.AppendSeparator()
        
        

        hotkeys = set()
        scripts_dir = os.path.join(install_dir, 'scripts')
        if os.path.exists(scripts_dir):
            print "Scripts directory found.  (This feature is deprecated!)"
            for d in os.listdir(scripts_dir):
                new_dir = os.path.join(scripts_dir, d)
                if os.path.isdir(new_dir): # for each directory we find in scripts_dir
                    for e in os.listdir(new_dir):
                        # maybe in future change this to 'mz', once we have mz-import
                        # only add files that start with 'RC_' prefix--allows user to have a 'main' file for
                        if e.startswith('RC_') and e.endswith('.py'):
                            # add this directory to the path (note: we don't add scripts_dir itself)
                            # also: I'm not adding a directory if it doesn't contain an RC script
                            if new_dir not in sys.path:
                                sys.path.append(new_dir)
                            # strip off prefix and extension for the menu item, assign a hotkey if possible
                            for i,c in enumerate(e[3:-3]):
                                if c not in hotkeys:
                                    hotkeys.add(c)
                                    item = tools_menu.Append(-1, e[3:(i+3)] + '&' + e[(i+3):-3])
                                    break
                            else:
                                item = tools_menu.Append(-1, e[3:-3]) # no hotkey to use
                            self.Bind(wx.EVT_MENU, ScriptMenuItem(e[:-3]), item) # bind the menu item to the wrapper class
        #else:
            #print 'Scripts directory %s not present.' % scripts_dir
        # The scripts feature is deprecated, so its not worth mentioning if 
        # there's no scripts directory.

        menu_bar.Append(tools_menu, "&Tools")

        #logger_message(50, 'Inititalizing Help Menu...')

        help_menu = wx.Menu()

        help_menu_contents = help_menu.Append(-1, "&Help\tF1", "Multiplierz Wiki")
        self.Bind(wx.EVT_MENU, self.on_help, help_menu_contents)

        help_menu.AppendSeparator()

        help_menu_about = help_menu.Append(wx.ID_ABOUT, "&About", "About this program")
        self.Bind(wx.EVT_MENU, self.on_about, help_menu_about)

        menu_bar.Append(help_menu, "&Help")
        

        bug_report = help_menu.Append(-1, "Report a Bug", "Report a Bug in Multiplierz mzDesktop.")
        self.Bind(wx.EVT_MENU, self.on_bugrep, bug_report)

        self.SetMenuBar(menu_bar)

        # add status bar
        self.statusbar = self.CreateStatusBar()
        self.statusbar.SetFieldsCount(2)
        self.statusbar.SetStatusWidths([-1,-3])
        self.statusbar.SetStatusText("Ready", 0)
        
        # A good idea, but will want to review all print statements to make
        # sure they make sense in this context (instead of, e.g., 'Generating Scan.'
        # just hanging out there while using the MS-MS View.)
        #redirector = Redirection(self.statusbar, sys.stdout)
        #sys.stdout = redirector
        #redirector2 = Redirection(self.statusbar, sys.stderr)
        #sys.stderr = redirector2

        self.nb = wx.Treebook(self, -1, size = (-1, -1), style = wx.NB_FIXEDWIDTH)
        self.nb.AssignImageList(wx.ImageList(1, 1)) # Makes sidebar at least so many pixels wide?

        #from console import ConsolePanel
        from digest import DigestPanel
        from fragment import FragmentPanel
        from info_file import InfoFilePanel
        from mascot_report import MascotReportPanel
        from mascot_web import MascotWebPanel
        from report_format import ReportFormatPanel
        from isoSim import IsotopePanel
        from transform_viewer import TransformPanel
        from proteinCoverage import CoveragePanel
        from fasta_tools import FastaPanel
        from mergeResults import MergePanel
        from mgf_tools import MGFPanel
        from general_viewer import ViewPanel
        from label_viewer import LabelPanel
        from free_viewer import LabelFreePanel
        from peptide_tools import PeptidePanel
        from spectrum_tools import SpectrumPanel
        
        ## Add Panels
        #panels = zip((MascotReportPanel, CoveragePanel, MergePanel,
                      #TransformPanel,
                      #MascotWebPanel, ReportFormatPanel, IsotopePanel, FastaPanel, MGFPanel,
                      #LabelPanel, LabelFreePanel, PeptidePanel,
                      #SpectrumPanel),
                     #('Download Mascot', 'Protein Coverage', 'Merge/Filter Results',
                      #'Charge Transform',
                      #'Mascot Web Extract', 'Reformat Reports', 'Isotope Distribution', 'FASTA Tools', 'MGF Tools',
                      #'MS-MS View', 'Cross-MS Quant View', 'Peptide Prediction',
                      #'Spectrum Tools'))
        
        panels = [(MascotReportPanel, 'Download Mascot'),
                  (MascotWebPanel, 'Mascot Web Extract'), # Mostly nonfunctional due to lack of XLSX metadata and outdated Mascot webscraping.
                  (MergePanel, 'Merge/Filter Results'),
                  (ReportFormatPanel, 'Reformat Reports'),
                  (CoveragePanel, 'Protein Coverage'),                  
                  (TransformPanel, 'Charge Transform'),
                  (IsotopePanel, 'Isotope Distribution'),
                  (LabelPanel, 'MS-MS View'),
                  #(LabelFreePanel, 'Cross-MS Quant View'),
                  (FastaPanel, 'FASTA Tools'),
                  (MGFPanel, 'MGF Tools'),
                  (PeptidePanel, 'Peptide Prediction'),
                  #(SpectrumPanel, 'Spectrum Tools')
                  ]

        # for each panel: call constructor, passing in notebook as the parent
        for (p,t) in panels:
            page = p(self.nb)
            # This will make tooltips that appear from the entire window;
            # not entirely desired behavior.            
            self.nb.AddPage(page, t)

        self.nb.GetTreeCtrl().SetMinSize((150, -1))
        self.nb.GetTreeCtrl().SetSize((150, -1))
        self.nb.SetDoubleBuffered(1)
        
        self.Show()
        
        self.Maximize()
        #self.nb.Tile()
        self.nb.Refresh()
        
        self.nb.Selection = 0

    def on_exit(self, event):
        logger_message(level=20, message='Cleaning up image folder')
        p = os.path.join(myTemp)
        for i in os.listdir(p):
            logger_message(level=10, message='removing %s ...' % os.path.join(p,i))
            os.remove(os.path.join(p,i))
        self.Destroy()
        sys.exit()

    def on_preferences(self, event):
        wx.BeginBusyCursor(wx.HOURGLASS_CURSOR)
        preferences_frame = PreferencesFrame(self)
        preferences_frame.Show()
        wx.EndBusyCursor()

    def on_peak_viewer(self, event):
        wx.BeginBusyCursor(wx.HOURGLASS_CURSOR)
        peak_viewer_frame = PeakViewer(self)
        peak_viewer_frame.Show()
        peak_viewer_frame.on_all_panels(None)
        wx.EndBusyCursor()

    def on_report_viewer(self, event):
        file_name = mzGUI.report_chooser()

        if file_name:
            wx.BeginBusyCursor(wx.HOURGLASS_CURSOR)
            report_viewer = ReportViewer(self, file_name)
            report_viewer.SetIcon(self.GetIcon())
            report_viewer.Show()
            wx.EndBusyCursor()

    def on_full_report(self, event):
        wx.BeginBusyCursor(wx.HOURGLASS_CURSOR)
        full_rep = FullReportWindow(self)
        full_rep.Show()
        wx.EndBusyCursor()

    def on_pep2gene(self, event):
        wx.BeginBusyCursor(wx.HOURGLASS_CURSOR)
        #import multiplierz.mzTools.pep2gene as pep2gene
        import utilities.pep2gene as pep2gene

        p2g = pep2gene.p2gSession(self)
        p2g.Show()    
                       
        wx.EndBusyCursor()
        
    def on_mzTransform(self, event):
        wx.BeginBusyCursor(wx.HOURGLASS_CURSOR)
        #import multiplierz.mzTools.mzTransform as mzt
        import utilities.mzTransform as mzt
        transform = mzt.deconvolutionSession(self, "mzTransform")
        transform.Show()
        wx.EndBusyCursor()
    
    def on_silac(self, event):
        wx.BeginBusyCursor(wx.HOURGLASS_CURSOR)
        #import multiplierz.mzTools.silacAnalysis as silac
        import utilities.silac as silac
        silapp = silac.SILACSession(None, "SILAC Analyzer")
        silapp.Show()
        wx.EndBusyCursor()
        
    def on_featureDet(self, event):
        import utilities.featureDetect as featureDetect
        detector = featureDetect.DetectorSession(None)
        detector.Show()
            
    def on_labelEv(self, event):
        import utilities.labelEvaluator as labelEv
        labelEv.LabelEvaluation(None)
        
    def on_help(self, event):
        webbrowser.open_new_tab(r'https://github.com/MaxAlex/multiplierz/wiki')

    def on_about(self, event):
        wx.Log_EnableLogging(False)
        about_frame = AboutFrame(self)
        about_frame.Show()
        wx.Log_EnableLogging(True)

    def on_bugrep(self, event):
        webbrowser.open_new_tab(r'https://github.com/MaxAlex/multiplierz/issues')
        #bug_frame = BugFrame(self)
        #BugFrame.Show()

    def on_pycomet(self, event):
        try:
            import utilities.Comet_GUI as comet
            comet.run_GUI(self)
        except Exception as err:
            messdog = wx.MessageDialog(self, str(err), style = wx.OK)
            messdog.ShowModal()
            raise err

    def on_xtandem(self, event):
        try:
            import utilities.Tandem_GUI as xtandem
            xtandem.runXTandemSearch(self)
        except Exception as err:
            messdog = wx.MessageDialog(self, str(err), style = wx.OK)        
            messdog.ShowModal()
            raise err
        
    def on_mascot(self, event):
        try:
            import utilities.Mascot_GUI as mascot
            writeBack = lambda x: self.statusbar.SetStatusText(x, 1)
            mascot.runMascotSearch(self, writeBack)
        except Exception as err:
            messdog = wx.MessageDialog(self, str(err), style = wx.OK)        
            messdog.ShowModal()
            raise err        





import multiplierz.mzGUI_standalone as mzGUI
from mzDesktop import install_dir



from full_report import FullReportWindow
from peak_viewer import PeakViewer
from report_viewer import ReportViewer

from preferences import PreferencesFrame