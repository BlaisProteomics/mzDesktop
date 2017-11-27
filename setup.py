from setuptools import setup, find_packages
try:
    import py2exe
except ImportError:
    pass
import matplotlib # Has its own datafiles thingy.

import sys, os
sys.setrecursionlimit(5000)
# py2exe recurses when gathering all modules rather than iterates.
# Written by some functional programming hotshot, I'd bet.
try:
    import numpy
    sys.path.append(os.path.join(numpy.__path__[0], 'core'))
except ImportError:
    print "numpy not found or not installed."
# To find numpy-atlas.dll, possibly other things.

if sys.argv[1] == 'py2exe':
    try:
        from openpyxl import modified_for_py2exe
    except ImportError:
        raise RuntimeError, ("The official openpyxl is not compatible "
                             "with py2exe; hardcoded versions of the "
                             "versioning constants must be added to "
                             "openpyxl/__init__.py (and the flag "
                             "modified_for_py2exe added, to satisfy "
                             "this failsafe.)")



def get_data_files():
    """
    py2exe doesn't seem to know about MANIFEST.in, so it has to be done manually.
    """
    start_dir = os.path.dirname(os.path.realpath(__file__))
    datafiles = []
    
    base_files = []
    for filename in ['COPYING', 'COPYING.LESSER', 'README',
                     'LICENSE.txt', 'setup.nsi', 'mascot.ini',
                     'unimod.sqlite', 'MSFileReader_x86_x64_v3.0SP3.exe']:
        #filepath = os.path.join(start_dir, filename)
        #assert os.path.exists(filepath), filepath
        #base_files.append(filepath)
        assert os.path.exists(os.path.join(start_dir, filename)), filename
        base_files.append(filename)
    datafiles.append(('', base_files))
    
    #images = []
    #for filename in ['BlaisLogo.jpg', 'multiplierzlogo.png']:
        #filepath = os.path.join(start_dir, 'images', filename)
        #assert os.path.exists(filepath), filepath
        #images.append(filepath)        
    #datafiles.append(('images', images))
    
    for recursive_dir in ['pyComet', 'xTandem', 'images',
                          'interface_modules']:
        for path, _, filenames in os.walk(recursive_dir):
            path_files = []
            for filename in filenames:    
                if not (filename.lower().endswith('py') or
                        filename.lower().endswith('pyc')):
                    filepath = os.path.join(path, filename)
                    assert os.path.exists(filepath), filepath
                    path_files.append(os.path.relpath(filepath, start_dir))
            datafiles.append((path, path_files))
    
    # matplotlib returns absolute-path files, but py2exe suddenly
    # demands *relative* paths.
    mplibfiles = matplotlib.get_py2exe_datafiles() 
    for site, files in mplibfiles:
        relfiles = [os.path.relpath(f, start_dir) for f in files]
        datafiles.append((site, relfiles))
    
    return datafiles
                

setup(name = 'mzDesktop',
      version = '2.0.3',
      description = 'The multiplierz mzDesktop GUI toolset',
      author = 'William Max Alexander (et al.)',
      author_email = 'williamM_alexander@dfci.harvard.edu',
      classifiers = ['Development Status :: 4 - Beta',
                     'Intended Audience :: Science/Research',
                     'Topic :: Scientific/Engineering :: Bio-Informatics',
                     'License :: OSI Approved :: GNU Lesser General Public License v2 or later (LGPLv2+)',
                     'Programming Language :: Python :: 2.7',
                     ],
      keywords = 'biology bioinformatics proteomics spectrometry',
      packages = find_packages(),
      include_package_data=True,
      install_requires = ['multiplierz', 'matplotlib', 'wx'],
      excludes = ['libzmq.pyd'],
      #console=['mzDesktop.py'],
      console = [{'script': 'mzDesktop.py',
                  'icon_resources': [(1, 'images\icons\multiplierz.ico')]}],      
      options = {'py2exe': {'packages': ['iminuit', 'wx'], # wx instead?
                                       ###'mzDesktop/gui', 'mzDesktop/utilities',
                                       ###'mzDesktop/xtandem', 'mzDesktop/pyComet'],
                          #'excludes': ['MySQLdb', '_gtkagg', '_tkagg', 'hotshot', 'PIL',
                                       #'compiler', 'bsddb', 'py2exe', 'isapi',
                                       #'setuptools', 'wxPython', 'Tkconstants', 'Tkinter', 'tcl',
                                       #'ipython', 'bokeh'],
                          'dll_excludes': ['libgdk-win32-2.0-0.dll',
                                           'libgobject-2.0-0.dll',
                                           'libgdk_pixbuf-2.0-0.dll',
                                           'tcl85.dll', 'tk85.dll',
                                           'uxtheme.dll', 'iertutil.dll',
                                           'wininet.dll', 'normaliz.dll',
                                           'libzmq.pyd']
                          }
               },
      data_files = get_data_files()
      #data_files = get_data_files()
      )






# NIST installer setup stage

print "mzDesktop built; packaging into NSIS installer."

import re
from subprocess import Popen
import shutil
import _winreg
aReg = _winreg.ConnectRegistry(None,_winreg.HKEY_LOCAL_MACHINE)
aKey = _winreg.OpenKey(aReg, r"SOFTWARE\Wow6432Node\NSIS")
n,v,t = _winreg.EnumValue(aKey,0)
nsis_path = re.sub('\\\\','/',v)
_winreg.CloseKey(aKey)
_winreg.CloseKey(aReg)
make_nsis_path = nsis_path+'/makensis.exe'
arg1 = 'dist/setup.nsi'
Popen([make_nsis_path,arg1]).wait()
shutil.copy('dist/mzDesktop_setup.exe', os.curdir)

print "Executable installer created."