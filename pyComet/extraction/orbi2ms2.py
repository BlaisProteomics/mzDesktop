from multiplierz.mzAPI.raw import mzFile
import os
#import mz_workbench.mz_core as mz_core

import mzGUI_standalone as mzGUI

global proton
#proton = mz_core.mass_dict['H+']
proton = 1

tolerance = 0.02
s2n_threshold = 1.0

def get_cal_mass(DataFile):
    print "Performing precalibration..."
    B=DataFile.scan_info(12,12.5,start_mz=0, stop_mz=99999)
    tolerance=0.05
    a=445.120025
    low = a-tolerance
    hi = a+tolerance
    cal = []
    for scan in B:
        if scan[3]=='MS1':
            C=DataFile.cscan(scan[2])
            for mass in C:
                if mass[0] > low and mass[0] < hi and mass[3] == 1.0:
                    cal.append(mass)
                if mass[0] > hi:
                    break
    print cal
    mass_int = 0
    int_sum = 0
    for mass in cal:
        mass_int += mass[0]*mass[1]
        int_sum += mass[1]
    try:
        cal_mass = float(mass_int)/float(int_sum)
    except:
        print "Could not find cal mass..."
        cal_mass = 445.120025
    print cal_mass

    delta = abs(a-cal_mass)
    if delta > 0.05:
        print "WARNING... CAL MASS NOT THERE OR OUTSIDE WINDOW!"
        cal_mass = a
        raise ValueError

    return cal_mass

def getPrecursor(pMZ,ms):
    thePeak = filter(lambda (mz,s,s2n,z) : abs(mz-pMZ) <= tolerance, ms)
    if not thePeak:
        return (pMZ,0,0.0,0.0)
    temp = [(s,mz,s2n,z) for (mz,s,s2n,z) in thePeak]
    temp.sort(reverse=True)
    (s,mz,s2n,z) = temp[0]
    return (mz,s,s2n,z)

def grab_cal_mass(C, lastcal, main_cal):
    tolerance=0.003
    a=main_cal
    low = a-tolerance
    hi = a+tolerance
    cal = 0
    calibration = "INTERNAL"
    for mass in C:
        if mass[0] > low and mass[0] < hi and mass[3] == 1.0:
            cal = mass[0]
        if mass[0] > hi:
            break
    if not cal:
        cal = lastcal
        calibration = "EXTERNAL"

    return cal, calibration

def extract_mgf(rawFiles, mgfName=None, multiple_files=False):
    namelist = []
    if not multiple_files:
        if not mgfName:
            mgfName = rawFiles[0][:-4]+"_RECAL.ms2"
            namelist.append(mgfName)
        out = file(mgfName,'w')
        #print >> out, "MASS=Monoisotopic"
        #print >> out, "SEARCH=MIS"
    for rawFile in rawFiles:
        print
        print '**************************'
        print '*                        *'
        print '*  CREATING              *'
        print '*  MGF                   *'
        print '*  RTCWDC                *'
        print '**************************'
        print
        print 
        print rawFile
        print
        if multiple_files:
            out = file(rawFile[:-4]+"_RECAL.ms2",'w')
            namelist.append(rawFile[:-4]+"_RECAL.ms2")
            #print >> out, "MASS=Monoisotopic"
            #print >> out, "SEARCH=MIS"
        print "Creating rawfile Object"
        dmz = mzFile(rawFile)
        print "created"
        titles = dict(map(lambda (x,y): (x+1,y), list(enumerate(dmz.filters()))))
        (start,stop) = dmz.scan_range()
        main_cal = get_cal_mass(dmz)
        lastMS1 = None
        lastcal = main_cal
        calmass = lastcal
        
        for sid in range(start,stop):
            (time,title) = titles[sid]
            if title.find("Full ms ") > -1:
                lastMS1 = dmz.lscan(sid)
                C = dmz.cscan(sid)
                lastcal = calmass
                calmass, calibration = grab_cal_mass(C, lastcal, main_cal)
                frac = float(445.120025)/float(calmass)
            else:
                a = title.find("Full ms2 ")
                b = title.find("@cid")
                if a > -1 and b > -1:
                    putativeMZ = float(title[(a+9):b])
                    putativeZ = 0
                    (accmz,acccharge) = dmz.scanPrecursor(sid)
                    if accmz > 0.0 :
                        z  = acccharge
                        mz = accmz
                        (dummymz,s,s2n,dummyz) = getPrecursor(mz,lastMS1)
                    else:
                        (mz,s,s2n,z) = getPrecursor(putativeMZ,lastMS1)
                        if z > 0 :
                            (c13mz,c13s,c13s2n,c13z) = getPrecursor(mz - 1.0/float(z) , lastMS1)
                            if c13z == z and c13s > .7 * s :
                                mz = c13mz
                                s = c13s
                                z = c13z
                                s2n = c13s2n
                    if len(dmz.scan(sid)) :
                        #S  4627	  4627	   780.7
                        #Z  2	  1560.4
                        #Z  3	  2340.1
                        #257.8 6073
                        print >> out, "S %d %d %.5f" % (sid, sid, mz * frac)
                        print >> out, "Z %d %.5f" % (z, ((mz * frac)*z)-((z-1)*proton))
                        #if z:
                        #    print >> out, "CHARGE=%d+" % z
                        for (ms2_mz,ms2_s) in dmz.scan(sid):
                            print >> out, "%.5f %.2f" % (ms2_mz,ms2_s)
                        #print >> out, "END IONS\n"

        dmz.close()
        if multiple_files:
            out.close()
    if not multiple_files:
        out.close()
    return namelist

if __name__ == "__main__":
    rawFiles = mzGUI.file_chooser('Choose RAW File', 'm')
    extract_mgf(rawFiles, None, True)
