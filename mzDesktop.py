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
__version__ = '2.0'


import os
import re
import shutil
import sys
import time
import wx

import matplotlib
matplotlib.use('WXAgg') # Prevents an obscure error that sometimes crops up.

#import win32api
#_exe_name = win32api.GetModuleFileName(win32api.GetModuleHandle(None))
_exe_name = sys.executable

if os.path.exists(os.path.join(os.curdir, 'mzDesktop.py')):
    install_dir = os.path.abspath(os.curdir)
else:
    #install_dir = os.path.dirname(_exe_name)
    install_dir = os.path.dirname(sys.executable)

import multiplierz
from multiplierz import myData, SettingsFile, logger_message


#print install_dir
os.chdir(install_dir)


from multiplierz.settings import MultiplierzSettings

# make sure unimod.sqlite is in the user's directory
if not os.path.exists(os.path.join(myData, 'unimod.sqlite')):
    print "Deploying unimod.sqlite..."
    shutil.copy(os.path.join(install_dir, 'unimod.sqlite'), myData)

# make sure there is a settings.xml file present
if not os.path.exists(os.path.join(myData, SettingsFile)):
    print "Deploying settings file (%s)" % SettingsFile
    shutil.copy(os.path.join(install_dir, SettingsFile), myData)

settings = MultiplierzSettings(os.path.join(myData, SettingsFile), logger_message)    


error_log = os.path.join(myData, "debug.log")

def log_bug(errType, err, traceback):
    if not os.path.exists(error_log):
        log = open(error_log, 'w')
        log.write('MULTIPLIERZ ERROR LOG\n')
        log.write('Please include this file with bug reports\n')
    else:
        log = open(error_log, 'a')
    
    import platform as p
    log.write('-------')
    multiplierz_data = 'Multiplierz version: %s %s\n' % (multiplierz.__version__, __version__)
    python_data = 'Python version info: %s %s %s %s\n' % (p.python_build()[0], p.python_build()[1],
                                                          p.python_compiler(), p.python_implementation())
    system_data = 'System info: %s %s\n' % (p.platform(), platform.processor())
    
    log.write(multiplierz_data)
    log.write(python_data)
    log.write(system_data)
    log.write('\n')
    log.write('%s\n' % errType)
    log.write('%s\n' % err)
    log.write('%s\n' % traceback)
    
    log.close()
    
    print "Error recorded in mzDesktop log file %s\n" % error_log
    sys.__excepthook__(errType, err, traceback)
    

if __name__ == '__main__':
    #sys.excepthook = log_bug
    from multiprocessing import freeze_support
    freeze_support()
    
    #with open(os.path.join(install_dir, "License.txt")) as lfh:
        #license_file = lfh.read()

    if len(sys.argv) > 1:
        main_frame = None

        arg = sys.argv[1]
        
        if arg == '--run_register_interfaces':
            print "PERFORMING MZAPI SETUP"
            from multiplierz.mzAPI.management import registerInterfaces
            registerInterfaces()
            print "Setup complete; exiting."
        else:
            arg_ext = os.path.splitext(arg)[1]
    
            if arg_ext == '.mzd':
                app = wx.App(False)
                _icon = wx.Icon(_exe_name, wx.BITMAP_TYPE_ICO)
    
                logger_message(60, 'Loading mzResults...')
    
                from gui.report_viewer import ReportViewer
    
                report_viewer = ReportViewer(None, arg)
                report_viewer.SetIcon(_icon)
                report_viewer.Show()
    
                app.MainLoop()
    else:
        app = wx.App(False)

        _icon = wx.Icon(_exe_name, wx.BITMAP_TYPE_ICO)

        from gui import MultiplierzFrame

        main_frame = MultiplierzFrame(None, _icon, os.path.join(install_dir, 'Scripts'))

        logger_message(50, "\nInstall Directory: %s\nData Directory: %s\n" % (install_dir, myData))

        #logger_message(50, "\n%s" % license_file)
        logger_message(50, "multiplierz Version: %s" % multiplierz.__version__)

        wx.Yield()

        #Splash Screen
        # This causes a popup error message for some reason; suppressing that
        # by disabling logging temporarily.
        wx.Log_EnableLogging(False)
        try:
            wx.SplashScreen(wx.Image(os.path.join(install_dir,
                            'images', 'multiplierzlogo.png')).ConvertToBitmap(),
                            wx.SPLASH_CENTRE_ON_PARENT | wx.SPLASH_TIMEOUT,
                            500, main_frame, -1)
        except:
            pass
        wx.Log_EnableLogging(True)
        wx.Yield()        

        main_frame.Show()

        app.MainLoop()


# Still used in report_viewer.py.
def find_mz_file(local_dir='.', file_name=None, spec_desc=None):
    '''Takes its best crack at locating an mz_file, using these steps:

    - If 'file_name' is specified, first try to use that path.
    - If it cannot be found (or is not a full path), look in the local
      directory for the file of the same name.
        - If file_name is not an mz_file type, try appending or
          switching the extension.
        - If file_name is an mzURL, look for the file locally,
          then try the URL to make sure it works.
    - If none of that works, try to use the spectrum description.
    - If that doesn't work either, return None.
    '''

    mz_file = None

    import multiplierz.mzAPI.mzURL as mzURL
    url_reg = re.compile(r'((http://.+)/files/([^/]+))(?:/scans/.*)?', flags=re.I)
    check_url = None

    if file_name:
        url_m = url_reg.match(file_name)

        base = os.path.basename(file_name)

        #for e in ('.raw', '.wiff', '.mzml', '.mzml.gz'):
        for e in mzGUI.MZ_EXT_2:
            if file_name.endswith(e) and os.path.exists(file_name):
                mz_file = file_name
                break
            elif file_name.endswith(e) and os.path.exists(os.path.join(local_dir, base)):
                mz_file = os.path.join(local_dir, base)
                break
            elif os.path.exists(file_name + e):
                mz_file = file_name + e
                break
            elif os.path.exists(os.path.join(local_dir, base + e)):
                mz_file = os.path.join(local_dir, base + e)
                break
            else:
                try:
                    if os.path.exists(file_name[:(file_name.index(e) + len(e))]):
                        mz_file = file_name[:(file_name.index(e) + len(e))]
                        break
                    elif os.path.exists(os.path.join(local_dir, 
                                                     file_name[:(file_name.index(e) 
                                                                 + len(e))])):
                        mz_file = os.path.exists(os.path.join(local_dir,
                                                              file_name[:(file_name.index(e)
                                                                          + len(e))]))
                        break
                except ValueError:
                    continue
        else:
            if url_m:
                #for e in ('.raw','.wiff','.mzml','.mzml.gz'):
                for e in mzGUI.MZ_EXT_2:
                    if os.path.exists(os.path.join(local_dir, url_m.group(3) + e)):
                        mz_file = os.path.join(local_dir, url_m.group(3) + e)
                        break
                else:
                    if settings.mzServer == 'always':
                        check_url = True
                    elif settings.mzServer == 'ask':
                        with URLDialog(None) as dlg:
                            if dlg.ShowModal() == wx.ID_OK:
                                check_url = True
                                if dlg.default_ck.GetValue():
                                    settings.mzServer = 'always'
                                    settings.save()
                            else:
                                check_url = False
                                if dlg.default_ck.GetValue():
                                    settings.mzServer = 'never'
                                    settings.save()
                    else:
                        check_url = False

                    if check_url and mzURL.check_mzURL(url_m.group(2),
                                                       url_m.group(3)):
                        mz_file = url_m.group(1)


    if mz_file is None and spec_desc:
        raw_m = re.match(r'(.+?)\..+\.dta', spec_desc, flags=re.I)
        wiff_m = re.match(r'File\:\s(.+?)\,', spec_desc, flags=re.I)
        url_m = url_reg.match(spec_desc)

        if raw_m:
            mz_file = os.path.join(local_dir, raw_m.group(1) + '.raw')
            if not os.path.exists(mz_file):
                if os.path.exists(mz_file+'.lnk'):
                    mz_file += '.lnk'
                else:
                    mz_file = None
        elif wiff_m:
            mz_file = os.path.join(local_dir, wiff_m.group(1))
            if not os.path.exists(mz_file):
                if os.path.exists(mz_file+'.lnk'):
                    mz_file += '.lnk'
                else:
                    mz_file = None
        elif url_m:
            #for e in ('.raw','.wiff','.mzml','.mzml.gz'):
            for e in mzGUI.MZ_EXT_2:
                if os.path.exists(os.path.join(local_dir, url_m.group(3) + e)):
                    mz_file = os.path.join(local_dir, url_m.group(3) + e)
                    break
            else:
                if check_url is None:
                    if settings.mzServer == 'always':
                        check_url = True
                    elif settings.mzServer == 'ask':
                        with URLDialog(None) as dlg:
                            if dlg.ShowModal() == wx.ID_OK:
                                check_url = True
                                if dlg.default_ck.GetValue():
                                    settings.mzServer = 'always'
                                    settings.save()
                            else:
                                check_url = False
                                if dlg.default_ck.GetValue():
                                    settings.mzServer = 'never'
                                    settings.save()
                    else:
                        check_url = False

                if check_url and mzURL.check_mzURL(url_m.group(2),
                                                   url_m.group(3)):
                    mz_file = url_m.group(1)

    #if mz_file is not None and mz_file.lower().endswith('.lnk'):
        #mz_file = multiplierz.mzAPI.follow_link(mz_file)

    return mz_file




    
    