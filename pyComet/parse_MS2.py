# Split MS2

def parse_MS2(filename):
    # [ [line 1, line 2, [(mz1, int1), (mz2, int2)]]
    out = []
    
    print "Opening file..."
    rdr = open(filename, 'r')
    print "Reading data into memory..."
    data = rdr.readlines()
    lines = len(data)
    print "Data in memory."
    
    counter = 0
    spectrum_count = 0
    more_input = True
    
    while more_input:
        if spectrum_count % 5000 == 0:
            print spectrum_count
        current_entry = []
        current_entry.append(data[counter])
        current_entry.append(data[counter+1])
        counter += 2
        
        new_query = False
        
        while not new_query:
            currentLine = data[counter]
            if not currentLine.startswith("S"):
                new_query = False
                current_entry.append(currentLine)
                counter += 1
                if counter == lines:
                    new_query = True
                    more_input = False
            else:
                new_query = True
        out.append(current_entry)
        spectrum_count += 1
    print "Done."
    print spectrum_count
    
    print "dividing..."
    
    current_start = 0
    current_position = 0
    
    current = 0
    wtr = None
    current_file = 0
    #append_text = str(current_file)
    #wtr = open(filename[:-4] + append_text + '.ms2', 'w')
    file_list = []
    
    #print "New file"
    #if wtr:
        #wtr.close()
    #current_file += 1
    print current_file
    append_text = str(current_file)
    wtr = open(filename[:-4] + append_text + '.ms2', 'w')
    file_list.append(filename[:-4] + append_text + '.ms2')    
    
    for i, member in enumerate(out):
        for entry in member:
            wtr.write(entry)
    wtr.close()
    return file_list
    
if __name__ == '__main__':
    #filename = r'C:\PyComet_2012013_64bit\0621ms_0fl_010_MGFPeaklist3.ms2'
    filename = r'C:\SBF\ACTIVE_COMET\0621ms_0fl_010_MGFPeaklist.ms2'
    
    parse_MS2(filename)
    