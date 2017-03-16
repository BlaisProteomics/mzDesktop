'''
MS2 File Format

S 1800 1800 692.90729
Z 5 3460.53643
200.83763 17.89
205.15532 8.51
...

MGF File format
BEGIN IONS
TITLE=Locus:1.1.1.68.2 File:"0621ms_0fl_010.wiff"
CHARGE=2+
PEPMASS=358.21370
RTINSECONDS=60
114.1094 16.0000 1
END IONS
...
'''

#import multiplierz.mascot as mascot
#import mzGUI_standalone as mzGUI
#import mz_workbench.mz_masses as mz_masses

global proton
import glob, re, wx, time, sys
proton = 1.0072764201041

def get_single_file(caption='Select File...', wx_wildcard = "MGF file (*.mgf)|*.mgf"):
    app = wx.PySimpleApp()
    dlg = wx.FileDialog(None, caption, pos = (2,2), wildcard = wx_wildcard)
    filename, dir = None, None
    if dlg.ShowModal() == wx.ID_OK:
        filename=dlg.GetPath()
        dir = dlg.GetDirectory()
        print filename
        print dir
    dlg.Destroy()
    return filename, dir
    

def parse_mgf(file_name, iterator=False):
    """BORROWED FROM MASCOT.py
    Parses an MGF file and stores contents in a dictionary.

    Function takes MGF file and returns a dictionary with the following structure:
    {queryCount:,    #Contains total number of spectra submitted
    SEARCH:,
    REPTYPE:,
    Query1:{
            PEPMASS:,
            CHARGE:,
            TITLE:,
            IONSTRING:      #mz:intensity,mz:intensity...
            }
    Query2:{}
    Query3:{}
    ... upto queryCount
    }

    If 'iterator' is True, it instead returns a generator of queries.
    The header information is lost, but this can be useful for going
    through each query and modifying it in some way.

    Example:
        >>> file_name = r'C:\Documents and Settings\User\Desktop\Data\mgf file\5556.mgf'
        >>> mgfHash = mascot.parse_mgf(file_name)
        >>> print mgfHash['SEARCH']
        MIS
        >>> print mgfHash['REPTYPE']
        Peptide
        >>> print mgfHash['queryCount']
        3708
        >>> print mgfHash['Query20']['PEPMASS']
        351.00958155898
        >>> print mgfHash['Query20']['CHARGE']
        2+
        >>> print mgfHash['Query20']['TITLE']
        File: 20060901_K562_iTRAQ_ic50_2E6cells.wiff, Sample: 20060901_K562_iTRAQ_ic50_2E6cells (sample number 1), Elution: 0.968 min, Period: 1, Cycle(s): 5 (Experiment 6)
        >>> print mgfHash['Query20']['IONSTRING']
        110.0743:0.0551,110.9813:0.0633,112.0498:0.0318,113.0028:0.0798,116.0367:0.0404,116.991:0.8285,118.9125:0.0409,120.0302:0.0329,124.9908:0.2267,127.0249:0.1274,130.0515:0.1284,131.0063:0.2322,133.101:0.0433,133.9803:0.0348,134.9561:0.1919,136.9294:0.1494,139.0196:0.0443,140.9918:0.2678,143.0017:0.387,149.0195:0.2475,151.0051:0.1292,152.9582:0.1207,154.944:0.0654,156.0799:0.1313,157.0232:0.0847,158.9977:1.3751,163.0324:0.1534,165.0117:0.1737,167.0314:0.4367,168.0114:0.3998,170.9828:0.8054,173.0069:0.2471,175.0024:0.3577,177.0063:0.9991,178.9297:0.0603,181.9913:0.0811,184.9952:0.0613,186.0046:0.2258,188.9995:0.6712,191.0054:0.2387,193.0222:0.3027,194.9649:0.9647,196.9802:0.1687,199.0064:0.0636,200.9888:0.5762,205.0195:0.3227,207.0101:0.6704,210.9484:0.2072,212.9657:3.4193,214.9891:0.033,216.9973:0.0996,218.9938:0.2115,223.0057:0.157,224.9976:0.0563,230.9687:0.8336,234.969:0.0115,236.97:0.1271,240.9826:0.0932,242.9859:0.0468,245.0273:0.0235,246.0462:0.1297,248.9958:0.4977,251.9898:0.0835,261.959:0.0965,267.0478:0.0123,267.9055:0.1475,272.9789:0.0744,278.8947:0.0502,290.952:0.1025,296.933:0.1423

    """

    def iter_mgf(f):
        '''f should be an open file object, already in the first query.'''

        # parameters possibly present inside a query
        local_params = set(('CHARGE', 'COMP', 'ETAG', 'INSTRUMENT', 'IT_MODS',
                            'PEPMASS', 'RTINSECONDS', 'SCANS', 'SEQ', 'TAG',
                            'TITLE', 'TOL', 'TOLU'))

        in_query = True
        query = dict(IONSTRING=[])
        ion_re = re.compile('(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)')
        ion_charge_re = re.compile('(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)')
        try:
            for line in f:
                if not in_query:
                    if line.upper().startswith('BEGIN IONS'):
                        in_query = True
                        query = dict(IONSTRING=[])
                    continue
                elif line[0] in ('#', ';', '!', '/') or line.strip() == '':
                    continue # comment line or blank line
                elif line.upper().startswith('END IONS'):
                    in_query = False
                    query['IONSTRING'] = ','.join(query['IONSTRING'])
                    yield query
                else:
                    if '=' in line and line.upper().split('=', 1)[0] in local_params:
                        query[line.upper().split('=', 1)[0]] = line.split('=', 1)[1].strip()
                    else:
                        n = ion_charge_re.match(line)
                        if n:
                            query['IONSTRING'].append('%s:%s:%s' % (n.group(1),n.group(2),n.group(3)))
                        else:
                            m = ion_re.match(line)
                            if m:
                                query['IONSTRING'].append('%s:%s' % (m.group(1),m.group(2)))
        finally:
            f.close()

    global_params = set(('ACCESSION', 'CHARGE', 'CLE', 'COM', 'CUTOUT', 'DB', 'DECOY',
                         'ERRORTOLERANT', 'FORMAT', 'FRAMES', 'INSTRUMENT', 'IT_MODS',
                         'ITOL', 'ITOLU', 'MASS', 'MODS', 'PEP_ISOTOPE_ERROR', 'PFA',
                         'PRECURSOR', 'QUANTITATION', 'REPORT', 'REPTYPE', 'SEARCH',
                         'SEG', 'TAXONOMY', 'TOL', 'TOLU', 'USEREMAIL', 'USERNAME'))

    f = open(file_name, mode='rb')

    if iterator:
        line = ''
        while not line.startswith('BEGIN IONS'):
            line = f.readline()
        return iter_mgf(f)

    mgf_hash = dict()

    for line in f:
        if line[0] in ('#', ';', '!', '/') or line.strip() == '':
            continue # comment line or blank line
        elif '=' in line:
            k,v = line.upper().split('=', 1)
            if k in global_params:
                mgf_hash[k] = v.strip()
        elif line.upper().startswith('BEGIN IONS'):
            break # time to use the iterator

    mgf_hash.update(('Query%d' % (i+1), q) for i,q in enumerate(iter_mgf(f)))

    mgf_hash['queryCount'] = sum(1 for k in mgf_hash if k.startswith('Query'))

    return mgf_hash

def convert(mgfFilename, parent=None):
    ms2Filename=mgfFilename[:-4]+'.ms2'
    out = file(ms2Filename, 'w')
    if parent:
        parent.post_message("Reading MGF... " + parent.make_time(time.localtime()))    
    else:    
        print "Parsing MGF..."    
    mgf_data = parse_mgf(mgfFilename)
    if parent:
        parent.post_message(str(len(mgf_data)) + ' ' + parent.make_time(time.localtime())) 
        parent.post_message('Finished parsing MGF ' + parent.make_time(time.localtime())) 
    else:    
        print len(mgf_data)
        print "Finished parsing MGF"
    scans = []

    for i in range(1, int(mgf_data['queryCount'])+1):
        if i % 1000 == 0:
            if parent:
                parent.post_message(str(i)) 
            else:
                print i
        title = mgf_data['Query%d'%i]['TITLE']
        pep_mass = float(mgf_data['Query%d'%i]['PEPMASS'])
        try:
            charge = int(mgf_data['Query%d'%i]['CHARGE'][:-1])
        except:
            charge = 0
        if mgf_data['Query%d'%i]['IONSTRING']:
            cur_scan = [(float(mz), float(intensity)) for mz,intensity in [peak.split(":")[:2] for peak in mgf_data['Query%d'%i]['IONSTRING'].split(",")]]
    
            sid = int(title.split(".")[3])
            mz = pep_mass
            z = charge
            print >> out, "S %d %d %.5f" % (sid, sid, mz)
            print >> out, "Z %d %.5f" % (z, (mz*z)-((z-1)*proton))
            
            for (ms2_mz,ms2_s) in cur_scan:
                print >> out, "%.5f %.2f" % (ms2_mz,ms2_s) 
        
if __name__ == "__main__":
    if len(sys.argv) > 1:
        convert(*sys.argv[1:])  
    else:
        mgfFilename, cdir = get_single_file()
        convert(mgfFilename)