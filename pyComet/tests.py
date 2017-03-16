#import comet_search
#import glob
import process_comet_xml
#comet_search.combine_outputs(r"C:\PyComet_v2013010_64bit\output.csv", [r"C:\PyComet_v2013010_64bit\test1.csv", r"C:\PyComet_v2013010_64bit\test2.csv"])

#ms2files = glob.glob(r"C:\PyComet_v2013010_64bit\a\0621ms_0fl_010_MGFPeaklist*.ms2")

#for current_ms2file in ms2files:
#    print current_ms2file
#    print "Processing xml..."
#    process_comet_xml.process_file(current_ms2file[:-3] + 'pep.xml')
    
    
#comet_search.combine_outputs(r"C:\PyComet_v2013010_64bit\a\0621ms_0fl_010_MGFPeaklist.pep.csv", [x[:-3] + 'pep.csv' for x in ms2files])

#process_comet_xml.calc_fdr(r"C:\PyComet_v2013010_64bit\a\0621ms_0fl_010_MGFPeaklist.pep.csv", 0.01, 'xcorr', rev_txt='REV_')

#process_comet_xml.process_file(r'C:\PyComet_v2013010_64bit\2013-07-30-Cisinski-DMRT7-Ctrl-1_RECAL1.pep.xml')

def test(**kwargs):
    print kwargs
    
test(opt1=123)
