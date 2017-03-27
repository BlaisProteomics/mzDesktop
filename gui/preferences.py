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

import wx
import re

import mzGUI_standalone as mzGUI

import mzDesktop

class PreferencesFrame(wx.Frame):
    def __init__(self, parent):
        wx.Frame.__init__(self, parent, -1, "Preferences", size=(700,320),
                          style=wx.DEFAULT_FRAME_STYLE ^ (wx.RESIZE_BORDER | wx.MAXIMIZE_BOX))

        self.SetIcon(parent.GetIcon())

        panel = wx.Panel(self)

        box = wx.BoxSizer(wx.VERTICAL)

        listbook = wx.Listbook(self, -1)
        listbook.AssignImageList(wx.ImageList(60, 1))

        self.loggerVerbosity = LoggerVerbosityPage(listbook)
        self.cometTandemPaths = CometAndTandemPage(listbook, parent)
        self.mascotServer = MascotServerPage(listbook, parent)
        self.reportSettingsPage = ReportSettingsPage(listbook)
        self.peakViewer = PeakViewerPage(listbook)
        self.mzResultsSettings = mzResultsSettingsPage(listbook)
        self.mzServerSettings = mzServerSettingsPage(listbook)
        
        listbook.AddPage(self.loggerVerbosity, "Logger Verbosity")
        listbook.AddPage(self.cometTandemPaths, "Comet & Tandem Paths")
        listbook.AddPage(self.mascotServer, "Mascot Server")
        listbook.AddPage(self.reportSettingsPage, "Report Settings")
        listbook.AddPage(self.peakViewer, "Peak Viewer")
        listbook.AddPage(self.mzResultsSettings, "mzResults Settings")
        listbook.AddPage(self.mzServerSettings, "mzServer Settings")
        
        box.Add(listbook)
        
        okButton = wx.Button(self, -1, "OK")
        self.Bind(wx.EVT_BUTTON, self.setAndClose, okButton)
        
        applyButton = wx.Button(self, -1, "Apply")
        self.Bind(wx.EVT_BUTTON, self.justSet, applyButton)
        
        cancelButton = wx.Button(self, -1, "Cancel")
        self.Bind(wx.EVT_BUTTON, self.justClose, cancelButton)

        buttonBox = wx.BoxSizer(wx.HORIZONTAL)
        buttonBox.Add(okButton);buttonBox.Add(applyButton);buttonBox.Add(cancelButton)
        #gbs.Add(buttonBox, (7, 2), (1, 2), flag = wx.ALIGN_RIGHT)           
        box.Add(buttonBox, flag = wx.ALIGN_RIGHT)
        
        
        self.SetSizerAndFit(box)

        self.Bind(wx.EVT_CLOSE, self.on_exit)

    def on_exit(self, event):
        # might as well just write every time
        mzDesktop.settings.save()

        self.Destroy()

    def setAndClose(self, event):
        self.justSet(event)
        self.justClose(event)
        
    def justSet(self, event):
        self.loggerVerbosity.on_set_level(event)
        self.mascotServer.on_set_server(event)
        self.cometTandemPaths.on_set_paths(event)
        self.reportSettingsPage.on_set_size(event)
        self.peakViewer.on_set_params(event)
        self.mzResultsSettings.on_set_params(event)
        self.mzServerSettings.on_mzserver(event)
        
        mzDesktop.settings.save()
    
    def justClose(self, event):
        self.Destroy()

class LoggerVerbosityPage(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)

        gbs = wx.GridBagSizer(10, 10)

        self.logger_setting = wx.RadioBox(self, -1, 'Verbosity Level',
                                          style=wx.RA_HORIZONTAL,
                                          choices=['Highest',
                                                   'High',
                                                   'Medium',
                                                   'Low',
                                                   'Lowest'])

        gbs.Add( self.logger_setting,
                 (0,0), span = (1, 5), flag=wx.ALIGN_CENTER )
        self.logger_setting.SetSelection(max(0, int(mzDesktop.settings.logger_level / 10 - 1)))

        #btn = wx.Button(self, -1, 'Set Level')
        #gbs.Add( btn, (1,0), flag=wx.ALIGN_CENTER )
        #self.Bind(wx.EVT_BUTTON, self.on_set_level, btn)
        
        #okBtn = wx.Button(self, -1, "OK")
        #gbs.Add(okBtn, (1, 0), flag = wx.ALIGN_RIGHT)
        #self.Bind(wx.EVT_BUTTON, self.setAndClose, okBtn)
        
        #applyBtn = wx.Button(self, -1, "Apply")
        #gbs.Add(applyBtn, (1, 1), flag = wx.ALIGN_CENTER_HORIZONTAL)
        #self.Bind(wx.EVT_BUTTON, self.on_set_level, applyBtn)
        
        #cancelBtn = wx.Button(self, -1, "Cancel")
        #gbs.Add(cancelBtn, (1, 2), flag = wx.ALIGN_LEFT)
        #self.Bind(wx.EVT_BUTTON, self.justClose, cancelBtn)

        gbs.AddGrowableCol(0,1)

        #gbs.AddGrowableRow(1,1)
        gbs.AddGrowableRow(0,2)

        box = wx.BoxSizer()
        box.Add(gbs, 1, wx.ALL|wx.EXPAND, 15)

        self.SetSizerAndFit(box)

    def on_set_level(self, event):
        level = (int(self.logger_setting.GetSelection()) + 1) * 10

        mzDesktop.settings.logger_level = level

        #mzDesktop.logger_message(30, 'Verbosity Level Changed to %s' % level)
        #mzGUI.alerts('Verbosity Level Changed to %s' % self.logger_setting.GetStringSelection(),
                     #'Verbosity Level')
        
        #self.GetParent().GetParent().on_exit(None)

    def setAndClose(self, event):
        self.on_set_level(event)
        self.GetParent().GetParent().on_exit(None)
        
    def justClose(self, event):
        self.GetParent().GetParent().Destroy()

class MascotServerPage(wx.Panel):
    def __init__(self, parent, mainFrame):
        wx.Panel.__init__(self,parent,-1)

        self.mainFrame = mainFrame

        gbs = wx.GridBagSizer(10, 10)

        gbs.Add( wx.StaticText(self, -1,
                               "Mascot Server URL\n(e.g. http://mascot_server.edu/mascot)",
                               style=wx.ALIGN_RIGHT),
                 (0,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT )

        self.server = wx.TextCtrl(self, -1, mzDesktop.settings.mascot_server)
        gbs.Add( self.server,
                 (0,1), flag=wx.EXPAND )

        gbs.Add( wx.StaticText(self, -1, "Version", style=wx.ALIGN_RIGHT),
                 (1,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT )

        self.version = wx.Choice(self, -1, choices=['2.1','2.2','2.3','2.4','2.5'])
        self.version.SetStringSelection(mzDesktop.settings.mascot_version)
        gbs.Add( self.version,
                 (1,1) )

        gbs.Add( wx.StaticText(self, -1, "Security Enabled", style=wx.ALIGN_RIGHT),
                 (2,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT )

        self.security = wx.RadioBox(self, -1, choices=['No','Yes'], style=wx.ALIGN_RIGHT)
        gbs.Add( self.security,
                 (2,1) )

        self.security.SetSelection(mzDesktop.settings.mascot_security)

        gbs.Add( wx.StaticText(self, -1, "Get Modification Positions\n(version 2.2+ only)",
                               style=wx.ALIGN_RIGHT),
                 (3,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT )

        self.var_mods = wx.RadioBox(self, -1, choices=['No','Yes'], style=wx.ALIGN_RIGHT)
        gbs.Add( self.var_mods,
                 (3,1) )

        self.var_mods.SetSelection(mzDesktop.settings.mascot_var_mods)

        gbs.Add( wx.StaticText(self, -1, "Create MS2 images from DAT file",
                               style=wx.ALIGN_RIGHT),
                 (4,0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT )

        self.mascot_ms2 = wx.RadioBox(self, -1, choices=['No','Yes'], style=wx.ALIGN_RIGHT)
        gbs.Add( self.mascot_ms2,
                 (4,1) )

        self.mascot_ms2.SetSelection(mzDesktop.settings.mascot_ms2)

        #setMascotServerButton = wx.Button(self, -1, "Save Settings")
        #gbs.Add( setMascotServerButton,
                 #(5,0), (1,2), wx.ALIGN_CENTER )
        #setMascotServerButton.Bind(wx.EVT_BUTTON, self.on_set_server)
        
        #okButton = wx.Button(self, -1, "OK")
        ##gbs.Add(okButton, (5, 0), flag = wx.ALIGN_RIGHT)
        #self.Bind(wx.EVT_BUTTON, self.setAndClose, okButton)
        
        #applyButton = wx.Button(self, -1, "Apply")
        ##gbs.Add(applyButton, (5, 1), flag = wx.ALIGN_CENTER_HORIZONTAL)
        #self.Bind(wx.EVT_BUTTON, self.on_set_server, applyButton)
        
        #cancelButton = wx.Button(self, -1, "Cancel")
        ##gbs.Add(cancelButton, (5, 2), flag = wx.ALIGN_LEFT)
        #self.Bind(wx.EVT_BUTTON, self.justClose, cancelButton)

        #buttonBox = wx.BoxSizer(wx.HORIZONTAL)
        #buttonBox.Add(okButton);buttonBox.Add(applyButton);buttonBox.Add(cancelButton)
        #gbs.Add(buttonBox, (5, 0), (1, 2), flag = wx.ALIGN_RIGHT)

        for i in range(2):
            gbs.AddGrowableCol(i,1)

        for i in range(5):
            gbs.AddGrowableRow(i,1)

        box = wx.BoxSizer()
        box.Add(gbs, 1, wx.ALL, 15)

        self.SetSizerAndFit(box)

    def on_set_server(self, event):
        mascotServerLoc = self.server.GetValue()
        mascotServerVer = self.version.GetStringSelection()
        mascotServerSec = self.security.GetSelection()
        mascotVarMods = self.var_mods.GetSelection()
        mascotMS2 = self.mascot_ms2.GetSelection()

        mascotServerLoc = re.sub('\n+','',mascotServerLoc)
        mascotServerVer = re.sub('\n+','',mascotServerVer)

        mascot_report_page = None
        mascot_web_page = None
        for i in range(len(self.mainFrame.nb.GetChildren())-1):
            if self.mainFrame.nb.GetPageText(i) == "Download Mascot":
                mascot_report_page = self.mainFrame.nb.GetPage(i)
            elif self.mainFrame.nb.GetPageText(i) == "Mascot Web Extract":
                mascot_web_page = self.mainFrame.nb.GetPage(i)

        if mascotServerVer < '2.2':
            mascot_report_page.quant_ck.Enable(False)
            mascot_web_page.mod_ck.Enable(True)
            mascot_web_page.mod_ck.SetValue(True)
        else:
            mascot_report_page.quant_ck.Enable(True)
            mascot_web_page.mod_ck.Enable(not mascotVarMods)
            mascot_web_page.mod_ck.SetValue(not mascotVarMods)

        mzDesktop.settings.mascot_server = mascotServerLoc
        mzDesktop.settings.mascot_version = mascotServerVer
        mzDesktop.settings.mascot_security = mascotServerSec
        mzDesktop.settings.mascot_var_mods = mascotVarMods
        mzDesktop.settings.mascot_ms2 = mascotMS2

        logins = (mascot_report_page.login_text,
                  mascot_report_page.password_text,
                  mascot_web_page.login_text,
                  mascot_web_page.password_text)

        if mascotServerSec:
            mascotSecurity = "Enabled"
            for login in logins:
                login.Enable(True)
        else:
            mascotSecurity = "Disabled"
            for login in logins:
                login.Enable(False)

        mascotVarMods = 'positions parsed' if mascotVarMods else 'counts only'
        mascotMS2 = 'from DAT file' if mascotMS2 else 'from server'

        #mzDesktop.logger_message(30, ('Mascot server changed to %s. Version %s. Security %s. Variable mod %s. MS2 images %s'
                                      #% (mascotServerLoc, mascotServerVer, mascotSecurity, mascotVarMods, mascotMS2)))
        #mzGUI.alerts(('Mascot server changed to %s.\nVersion %s.\nSecurity %s.\nVariable mod %s\nMS2 images %s'
                      #% (mascotServerLoc, mascotServerVer, mascotSecurity, mascotVarMods, mascotMS2)),
                     #'Mascot Server')

        #self.GetParent().GetParent().on_exit(None)
        
    def setAndClose(self, event):
        self.on_set_server(event)
        self.GetParent().GetParent().on_exit(None)
        
    def justClose(self, event):
        self.GetParent().GetParent().Destroy()
        
        
class CometAndTandemPage(wx.Panel):
    def __init__(self, parent, mainFrame):
        wx.Panel.__init__(self, parent, -1)
        self.mainFrame = mainFrame
        gbs = wx.GridBagSizer(10, 10)
        
        cometLabel = wx.StaticText(self, -1, "Path To Comet Executable")
        self.cometCtrl = wx.TextCtrl(self, -1, mzDesktop.settings.get_comet())
        self.cometBrowse = wx.Button(self, -1, "Browse")
        
        xtandemLabel = wx.StaticText(self, -1, "Path To XTandem Executable")
        self.xtandemCtrl = wx.TextCtrl(self, -1, mzDesktop.settings.get_xtandem())
        self.xtandemBrowse = wx.Button(self, -1, "Browse")
        
        self.Bind(wx.EVT_BUTTON, self.onCBrowse, self.cometBrowse)
        self.Bind(wx.EVT_BUTTON, self.onXTBrowse, self.xtandemBrowse)
        
        gbs.Add(cometLabel, (0, 0))
        gbs.Add(self.cometCtrl, (1, 0), span = (1, 2), flag = wx.EXPAND)
        gbs.Add(self.cometBrowse, (1, 2))
        gbs.Add(xtandemLabel, (3, 0))
        gbs.Add(self.xtandemCtrl, (4, 0), span = (1, 2), flag = wx.EXPAND)
        gbs.Add(self.xtandemBrowse, (4, 2))
        
        gbs.AddGrowableCol(1)
        
        overbox = wx.BoxSizer()
        overbox.Add(gbs, 1, wx.ALL, 15)
        self.SetSizerAndFit(overbox)
        
        
    def onCBrowse(self, evt):
        comet = mzGUI.file_chooser('Select Comet Executable', mode = 'r',
                                   wildcard = '*.exe')
        self.cometCtrl.SetValue(comet)
        
    def onXTBrowse(self, evt):
        tandem = mzGUI.file_chooser('Select X! Tandem Executable', mode = 'r',
                                    wildcard = '*.exe')
        self.xtandemCtrl.SetValue(tandem)
        
    def on_set_paths(self, evt):
        mzDesktop.settings.set_comet(self.cometCtrl.GetValue())
        mzDesktop.settings.set_xtandem(self.xtandemCtrl.GetValue())
        
        
        
class ReportSettingsPage(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)

        gbs = wx.GridBagSizer(10, 10)

        self.fmt = wx.RadioBox(self, -1, 'Default Format',
                               style=wx.RA_VERTICAL,
                               choices=['Excel Spreadsheet (.xls)',
                                        'Excel 2007 Spreadsheet (.xlsx)',
                                        'Comma-Separated Values (.csv)',
                                        'mzResults Database (.mzd)'])
        gbs.Add( self.fmt, (0,0), (1,2), flag=wx.ALIGN_CENTER )
        self.fmt.SetSelection({'.xls': 0,
                               '.xlsx': 1,
                               '.csv': 2,
                               '.mzd': 3}[mzDesktop.settings.default_format])

        gbs.Add( wx.StaticText(self, -1, "Image Size", style=wx.ALIGN_CENTER),
                 (1,0), (1,2), flag=wx.ALIGN_CENTER )

        gbs.Add( wx.StaticText(self, -1, "Width"),
                 (2,0), (1,1), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT )

        self.imageSize_width = wx.TextCtrl(self, -1, str(mzDesktop.settings.image_size[0]),
                                           size=(50,-1), name='Width', validator=mzGUI.NumValidator())
        gbs.Add( self.imageSize_width, (2,1), (1,1), flag=wx.ALIGN_CENTER_VERTICAL )

        gbs.Add( wx.StaticText(self, -1, "Height"),
                 (3,0), (1,1), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT )

        self.imageSize_height = wx.TextCtrl(self, -1, str(mzDesktop.settings.image_size[1]),
                                            size=(50,-1), name='Height', validator=mzGUI.NumValidator())
        gbs.Add( self.imageSize_height, (3,1), (1,1), flag=wx.ALIGN_CENTER_VERTICAL )

        gbs.Add( wx.StaticText(self, -1, "Example: 6.0 x 4.5"),
                 (4,0), (1,2), flag=wx.ALIGN_CENTER )

        #btn = wx.Button(self, -1, "Save Settings")
        #gbs.Add( btn, (5,0), (1,2), flag=wx.ALIGN_CENTER )
        #self.Bind(wx.EVT_BUTTON, self.on_set_size, btn)
        
        #okButton = wx.Button(self, -1, "OK")
        #self.Bind(wx.EVT_BUTTON, self.setAndClose, okButton)
        
        #applyButton = wx.Button(self, -1, "Apply")
        #self.Bind(wx.EVT_BUTTON, self.on_set_size, applyButton)
        
        #cancelButton = wx.Button(self, -1, "Cancel")
        #self.Bind(wx.EVT_BUTTON, self.justClose, cancelButton)

        #buttonBox = wx.BoxSizer(wx.HORIZONTAL)
        #buttonBox.Add(okButton);buttonBox.Add(applyButton);buttonBox.Add(cancelButton)
        #gbs.Add(buttonBox, (5, 0), (1, 2), flag = wx.ALIGN_RIGHT)        

        for i in range(2):
            gbs.AddGrowableCol(i,1)

        #for i in range(6):
            #gbs.AddGrowableRow(i,1)

        box = wx.BoxSizer()
        box.Add(gbs, 1, wx.ALL, 15)

        self.SetSizerAndFit(box)

    def on_set_size(self, event):
        if not self.Validate():
            return

        fmt = ('.xls', '.xlsx', '.csv', '.mzd')[self.fmt.GetSelection()]
        width = float(self.imageSize_width.GetValue())
        height = float(self.imageSize_height.GetValue())

        mzDesktop.settings.default_format = fmt
        mzDesktop.settings.image_size = (width, height)

        #format_str = fmt[1:].upper()
        #sizeStr = "%s x %s " % (width, height)
        #mzDesktop.logger_message(30, 'Default format set to %s, image size set to %s' % (format_str, sizeStr))
        #mzGUI.alerts('Default format set to %s, image size set to %s' % (format_str, sizeStr),
                     #'Report Settings')
        
        #self.GetParent().GetParent().on_exit(None)
        
    def setAndClose(self, event):
        self.on_set_size(event)
        self.GetParent().GetParent().on_exit(None)
        
    def justClose(self, event):
        self.GetParent().GetParent().Destroy()    


class PeakViewerPage(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)

        gbs = wx.GridBagSizer(10, 10)

        for i,lbl in enumerate(('XIC Viewer Time Window',
                                'XIC Generation Time Window',
                                'XIC Generation m/z Window',
                                'MS1 Viewer m/z Window')):
            gbs.Add( wx.StaticText(self, -1, lbl, style=wx.ALIGN_RIGHT),
                     (i,0), flag=wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL )

        self.xic_viewer_time = wx.TextCtrl(self, -1, str(mzDesktop.settings.XIC_view_time_window),
                                           size=(45,-1), validator=mzGUI.NumValidator())
        self.xic_gen_time = wx.TextCtrl(self, -1, str(mzDesktop.settings.XIC_gen_time_window),
                                        size=(45,-1), validator=mzGUI.NumValidator())
        self.xic_gen_mz = wx.TextCtrl(self, -1, str(mzDesktop.settings.XIC_gen_mz_window),
                                      size=(45,-1), validator=mzGUI.NumValidator())
        self.ms1_viewer_mz = wx.TextCtrl(self, -1, str(mzDesktop.settings.MS1_view_mz_window),
                                         size=(45,-1), validator=mzGUI.NumValidator())

        for i,c in enumerate((self.xic_viewer_time,
                              self.xic_gen_time,
                              self.xic_gen_mz,
                              self.ms1_viewer_mz)):
            gbs.Add( c, (i,1) )

        #btn = wx.Button(self, -1, 'Save Settings')
        #gbs.Add( btn, (4,0), (1,2), flag=wx.ALIGN_CENTER )
        #self.Bind(wx.EVT_BUTTON, self.on_set_params, btn)
        
        #okButton = wx.Button(self, -1, "OK")
        #self.Bind(wx.EVT_BUTTON, self.setAndClose, okButton)
        
        #applyButton = wx.Button(self, -1, "Apply")
        #self.Bind(wx.EVT_BUTTON, self.on_set_params, applyButton)
        
        #cancelButton = wx.Button(self, -1, "Cancel")
        #self.Bind(wx.EVT_BUTTON, self.justClose, cancelButton)

        #buttonBox = wx.BoxSizer(wx.HORIZONTAL)
        #buttonBox.Add(okButton);buttonBox.Add(applyButton);buttonBox.Add(cancelButton)
        #gbs.Add(buttonBox, (5, 0), (1, 2), flag = wx.ALIGN_RIGHT)           

        gbs.AddGrowableCol(0,1)
        gbs.AddGrowableCol(1,1)

        #gbs.AddGrowableRow(4,1)

        box = wx.BoxSizer()
        box.Add(gbs, 1, wx.ALL|wx.EXPAND, 15)
        self.SetSizerAndFit(box)

    def on_set_params(self, event):
        if not self.Validate():
            return

        mzDesktop.settings.XIC_view_time_window = float(self.xic_viewer_time.GetValue())
        mzDesktop.settings.XIC_gen_time_window = float(self.xic_gen_time.GetValue())
        mzDesktop.settings.XIC_gen_mz_window = float(self.xic_gen_mz.GetValue())
        mzDesktop.settings.MS1_view_mz_window = float(self.ms1_viewer_mz.GetValue())

        #mzDesktop.logger_message(30,'Peak Viewer Parameters Changed')
        #mzGUI.alerts('Peak Viewer Parameters Changed')
        
        #self.GetParent().GetParent().on_exit(None)
        
    def setAndClose(self, event):
        self.on_set_params(event)
        self.GetParent().GetParent().on_exit(None)
        
    def justClose(self, event):
        self.GetParent().GetParent().Destroy()        


class mzResultsSettingsPage(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)

        gbs = wx.GridBagSizer(5, 10)

        gbs.Add( wx.StaticText(self, -1, 'Significant Figures', style=wx.ALIGN_CENTER),
                 (0,0), (1,5), flag=wx.ALIGN_CENTER )

        for i,lbls in enumerate((('Precursor MS:', 'm/z', 'intensity'),
                                 ('MS/MS:', 'm/z', 'intensity'),
                                 ('XIC:', 'time', 'intensity'))):
            gbs.Add( wx.StaticText(self, -1, lbls[0], style=wx.ALIGN_RIGHT),
                     (i+1,0), flag=wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL )
            gbs.Add( wx.StaticText(self, -1, lbls[1], style=wx.ALIGN_RIGHT),
                     (i+1,1), flag=wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL )
            gbs.Add( wx.StaticText(self, -1, lbls[2], style=wx.ALIGN_RIGHT),
                     (i+1,3), flag=wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL )

        self.ms1_mz_figs = wx.TextCtrl(self, -1, str(mzDesktop.settings.ms1_mz_figs), size=(30,-1),
                                       validator=mzGUI.NumValidator(func=int, flag=True))
        self.ms1_int_figs = wx.TextCtrl(self, -1, str(mzDesktop.settings.ms1_int_figs), size=(30,-1),
                                        validator=mzGUI.NumValidator(func=int, flag=True))
        self.ms2_mz_figs = wx.TextCtrl(self, -1, str(mzDesktop.settings.ms2_mz_figs), size=(30,-1),
                                       validator=mzGUI.NumValidator(func=int, flag=True))
        self.ms2_int_figs = wx.TextCtrl(self, -1, str(mzDesktop.settings.ms2_int_figs), size=(30,-1),
                                        validator=mzGUI.NumValidator(func=int, flag=True))
        self.xic_time_figs = wx.TextCtrl(self, -1, str(mzDesktop.settings.xic_time_figs), size=(30,-1),
                                         validator=mzGUI.NumValidator(func=int, flag=True))
        self.xic_int_figs = wx.TextCtrl(self, -1, str(mzDesktop.settings.xic_int_figs), size=(30,-1),
                                        validator=mzGUI.NumValidator(func=int, flag=True))

        for i,(cA,cB) in enumerate(((self.ms1_mz_figs, self.ms1_int_figs),
                                    (self.ms2_mz_figs, self.ms2_int_figs),
                                    (self.xic_time_figs, self.xic_int_figs))):
            gbs.Add( cA, (i+1,2) )
            gbs.Add( cB, (i+1,4) )

        self.theor_mz = wx.CheckBox(self, -1, ' Include Theoretical m/z')
        gbs.Add( self.theor_mz,
                 (4,1), (1,5), flag=wx.ALIGN_LEFT|wx.ALIGN_BOTTOM )
        self.theor_mz.SetValue(mzDesktop.settings.show_theor_mz)

        self.mass_error = wx.CheckBox(self, -1, ' Include Mass Error')
        gbs.Add( self.mass_error,
                 (5,1), (1,5), flag=wx.ALIGN_LEFT )
        self.mass_error.SetValue(mzDesktop.settings.show_mass_error)

        gbs.Add( wx.StaticText(self, -1, 'Significant Figures:', style=wx.ALIGN_RIGHT),
                 (6,0), (1,2), flag=wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL )

        self.mass_error_figs = wx.TextCtrl(self, -1, str(mzDesktop.settings.mass_error_figs), size=(30,-1),
                                           validator=mzGUI.NumValidator(func=int, flag=True))
        gbs.Add( self.mass_error_figs,
                 (6,2), flag=wx.ALIGN_CENTER_VERTICAL)

        self.mass_error_units = wx.RadioBox(self, -1, 'Mass Error Units',
                                            choices=['ppm', 'Da'], style=wx.ALIGN_RIGHT)
        self.mass_error_units.SetStringSelection(mzDesktop.settings.mass_error_units)
        gbs.Add( self.mass_error_units,
                 (6,3), (1,2) )

        #btn = wx.Button(self, -1, 'Save Settings')
        #gbs.Add( btn, (7,0), (1,5), flag=wx.ALIGN_CENTER )
        #self.Bind(wx.EVT_BUTTON, self.on_set_params, btn)

        #okButton = wx.Button(self, -1, "OK")
        #self.Bind(wx.EVT_BUTTON, self.setAndClose, okButton)
        
        #applyButton = wx.Button(self, -1, "Apply")
        #self.Bind(wx.EVT_BUTTON, self.on_set_params, applyButton)
        
        #cancelButton = wx.Button(self, -1, "Cancel")
        #self.Bind(wx.EVT_BUTTON, self.justClose, cancelButton)

        #buttonBox = wx.BoxSizer(wx.HORIZONTAL)
        #buttonBox.Add(okButton);buttonBox.Add(applyButton);buttonBox.Add(cancelButton)
        #gbs.Add(buttonBox, (7, 2), (1, 2), flag = wx.ALIGN_RIGHT)           

        gbs.AddGrowableCol(0,2)
        gbs.AddGrowableCol(4,2)

        gbs.AddGrowableRow(4,1)
        #gbs.AddGrowableRow(7,1)

        box = wx.BoxSizer()
        box.Add(gbs, 1, wx.ALL|wx.EXPAND, 15)
        self.SetSizerAndFit(box)

    def on_set_params(self, event):
        if not self.Validate():
            return

        mzDesktop.settings.ms1_mz_figs = int(self.ms1_mz_figs.GetValue())
        mzDesktop.settings.ms1_int_figs = int(self.ms1_int_figs.GetValue())
        mzDesktop.settings.ms2_mz_figs = int(self.ms2_mz_figs.GetValue())
        mzDesktop.settings.ms2_int_figs = int(self.ms2_int_figs.GetValue())
        mzDesktop.settings.xic_time_figs = int(self.xic_time_figs.GetValue())
        mzDesktop.settings.xic_int_figs = int(self.xic_int_figs.GetValue())

        mzDesktop.settings.show_theor_mz = self.theor_mz.GetValue()
        mzDesktop.settings.show_mass_error = self.mass_error.GetValue()
        mzDesktop.settings.mass_error_figs = int(self.mass_error_figs.GetValue())
        mzDesktop.settings.mass_error_units = self.mass_error_units.GetStringSelection()

        #mzDesktop.logger_message(30, 'mzResults Settings Changed')
        #mzGUI.alerts('mzResults Settings Changed')
        
        #self.GetParent().GetParent().on_exit(None)
    
    def setAndClose(self, event):
        self.on_set_params(event)
        self.GetParent().GetParent().on_exit(None)
        
    def justClose(self, event):
        self.GetParent().GetParent().Destroy()            


class mzServerSettingsPage(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)

        gbs = wx.GridBagSizer(10, 10)

        gbs.Add( wx.StaticText(self, -1, ("Experimental Feature:\n"
                                          "mzServers allow remote access to hosted data files.\n"),
                               style=wx.ALIGN_CENTER),
                 (0,0), flag=wx.EXPAND )

        self.mzserver = wx.RadioBox(self, -1, 'Connect to mzServer...',
                                    style=wx.RA_VERTICAL,
                                    choices=['Always',
                                             'Never',
                                             'Ask me each time'])
        gbs.Add( self.mzserver,
                 (1,0), flag=wx.ALIGN_CENTER )

        self.mzserver.SetSelection({'always': 0,
                                    'never': 1,
                                    'ask': 2}[mzDesktop.settings.mzServer])

        #btn = wx.Button(self, -1, "Save Settings")
        #gbs.Add( btn, (2,0), flag=wx.ALIGN_CENTER )
        #self.Bind(wx.EVT_BUTTON, self.on_mzserver, btn)
        
        
        #okButton = wx.Button(self, -1, "OK")
        #self.Bind(wx.EVT_BUTTON, self.setAndClose, okButton)
        
        #applyButton = wx.Button(self, -1, "Apply")
        #self.Bind(wx.EVT_BUTTON, self.on_mzserver, applyButton)
        
        #cancelButton = wx.Button(self, -1, "Cancel")
        #self.Bind(wx.EVT_BUTTON, self.justClose, cancelButton)

        #buttonBox = wx.BoxSizer(wx.HORIZONTAL)
        #buttonBox.Add(okButton);buttonBox.Add(applyButton);buttonBox.Add(cancelButton)
        #gbs.Add(buttonBox, (5, 0), (1, 2), flag = wx.ALIGN_RIGHT)       

        gbs.AddGrowableCol(0,1)

        #for i in range(1,3):
            #gbs.AddGrowableRow(i,1)

        box = wx.BoxSizer()
        box.Add(gbs, 1, wx.EXPAND|wx.ALL, 15)

        self.SetSizerAndFit(box)

    def on_mzserver(self, event):
        setting = ('always', 'never', 'ask')[self.mzserver.GetSelection()]

        mzDesktop.settings.mzServer = setting

        format_str = {'always': 'Always connect to',
                      'never': 'Never connect to',
                      'ask': 'Ask when connecting to'}[setting]

        #mzDesktop.logger_message(30, 'Default set: %s mzServers' % format_str)
        #mzGUI.alerts('Default set: %s mzServers' % format_str,
                     #'mzServer Settings')
        
        #self.GetParent().GetParent().on_exit(None)
    
    def setAndClose(self, event):
        self.on_mzserver(event)
        self.GetParent().GetParent().on_exit(None)
        
    def justClose(self, event):
        self.GetParent().GetParent().Destroy()            

