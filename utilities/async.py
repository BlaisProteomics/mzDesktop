import wx
import multiprocessing
from time import sleep
import os
import traceback
from multiplierz import myData
from multiplierz import __version__ as __m_version__

error_log = os.path.join(myData, "debug.log")


# This module handles both async to avoid GUI lockup and 
# clean reporting/logging of errors.  Functions that call
# things through launch_process should rely on control flow
# returning normally regardless of whether the called
# function raised an exception (the exception object is
# returned in that case.)  They can therefore perform
# 'cleanup' (re-enabling controls, etc) but shouldn't
# report success; use a callback for that, if necessary.

def log_bug(err):
    if not os.path.exists(error_log):
        log = open(error_log, 'w')
        log.write('MULTIPLIERZ ERROR LOG\n')
        log.write('Please include this file with bug reports\n')
    else:
        log = open(error_log, 'a')
    
    import platform as p
    log.write('\n-------\n')
    multiplierz_data = 'Multiplierz version: %s\n' % __m_version__
    python_data = 'Python version info: %s %s %s %s %s \n' % (p.python_build()[0], p.python_build()[1],
                                                              p.python_compiler(), p.python_implementation(),
                                                              '.'.join(p.python_version_tuple()))
    system_data = 'System info: %s %s\n' % (p.platform(), p.processor())
    
    log.write(multiplierz_data)
    log.write(python_data)
    log.write(system_data)
    log.write('\n')
    log.write('%s\n' % err)
    traceback.print_exc(file = log)
    
    log.close()
    
    print "Error recorded in mzDesktop log file %s\n" % error_log


def sub_runner(function, channel, args, kwargs):
    try:
        results = function(*args, **kwargs)
    except Exception as err:
        log_bug(err)
        channel.put(err)
        raise err # Returning error from task thread.
        
    channel.put(results)
    

def launch_process(function, callback = None, *args, **kwargs):
    resultchannel = multiprocessing.Queue()
    stuff = (function, resultchannel, args, kwargs)
    subproc = multiprocessing.Process(target = sub_runner, args = stuff)
    try:
        subproc.start()
    
        while subproc.is_alive():
            wx.Yield()
            sleep(0.1)
            
        
        subproc.join()
        results = resultchannel.get(block = False)
        
        if isinstance(results, Exception):
            raise results
        if callable(callback):
            return callback(results)
        elif hasattr(callback, 'Enable'):
            callback.Enable(True)
            return
        elif not callback:
            return results
        else:
            raise Exception, "Invalid callback."        
    except Exception as err:
        messdog = wx.MessageDialog(None,
                                   ('An error occured:\n%s\n'
                                    'Please consider '
                                    'submitting a bug report '
                                    'to the multiplierz team.' % repr(err)),
                                   'Error', style = wx.OK)
        messdog.ShowModal()
        messdog.Destroy()
        #raise err
        return err
            
    
    
    
    
    


def foo(bar):
    print bar
    return 'baz'

def cb(x):
    print "Callback %s!" % x
    return 'qux'





if __name__ == '__main__':
    launch_thread_process(foo, cb, 'foo')
    
    print "Done."
    
    