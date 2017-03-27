import wx
import os, re
from multiplierz.mzTools.pep2gene import add_gene_ids, create_fasta_index
from regex import RegexHelper
from multiplierz import myData, fastaList
import async

fastaFiles = fastaList()


# Pep2Gene Utility Tooltips

dbTypeTip = ("The source and format type of the input gene and protein data.")

fastaTip = ("A list of proteins that the search results will be compared against.")
Gene2RefSeqTip = ("A table provided by NCBI which matches protein IDs "
                  "to the corresponding gene IDs.  This file is available at "
                  "ftp://ftp.ncbi.nih.gov/gene/DATA/gene2refseq.gz")
regexGeneIdTip = ("A regular expression which will be used to extract the gene ID "
                  "from the label line of the FASTA file provided.")
taxonTip = ("The taxonomic category which the resulting database will apply to"
            "(e.g., 'human', 'mouse', etc.)")


uniprotMapTip = ("A table provided by UniProt which gives the gene id associated "
                 "with each UniProt accession number.  This file is available at "
                 "ftp://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/idmapping/idmapping_selected.tab")
fastaUniprotTip = ("A regular expression which will be used to extract the UniProt "
                   "accession number from the labels in the FASTA file.")

databaseTip = ("A database file, produced by interface above.")
targetTip = ("The search results file to be annotated.")




class p2gSession(wx.Frame):
    def __init__(self, parent):
        super(p2gSession, self).__init__(parent, title = "Pep2Gene Utility", size = (700, 500))

        overPanel = wx.Panel(self, -1, style = wx.EXPAND)

        dbmpTitle = wx.StaticText(overPanel, -1, "Compile Pep2Gene Database")

        dbmpFastaLabel = wx.StaticText(overPanel, -1, "FASTA File")
        self.dbmpFastaField = wx.ComboBox(overPanel, -1, "",
                                          choices = [os.path.basename(x) for x in fastaFiles])
        self.dbmpFastaButton = wx.Button(overPanel, -1, "Browse")
        self.dbmpFastaButton.Bind(wx.EVT_BUTTON, self.choose_fasta)
        dbmpFastaLabel.SetToolTip(wx.ToolTip(fastaTip))
        self.dbmpFastaField.SetToolTip(wx.ToolTip(fastaTip))


        self.regexLabel = wx.TextCtrl(overPanel, -1, "FASTA ID-to-Gene ID Regex",
                                      style = wx.TE_READONLY | wx.BORDER_NONE | wx.TE_RIGHT)
        self.regexField = wx.TextCtrl(overPanel, -1, "(?<=ref\|)[A-Z0-9\-\_\.]{1,20}(?=\|)(?# NCBI)", size = (-1, -1))
        self.regexButton = wx.Button(overPanel, -1, "Regex Help")
        self.regexButton.Bind(wx.EVT_BUTTON, self.runRegexUtility)
        self.regexLabel.SetToolTip(wx.ToolTip(regexGeneIdTip))
        self.regexField.SetToolTip(wx.ToolTip(regexGeneIdTip))

        self.dbmpCall = wx.Button(overPanel, -1, "Compile")
        self.dbmpCall.Bind(wx.EVT_BUTTON, self.makeFastaDB)

        gridBag = wx.GridBagSizer(12, 5)

        gridBag.Add(dbmpTitle, (0, 0), flag = wx.ALIGN_CENTER_VERTICAL)
        
        gridBag.Add(dbmpFastaLabel, (1, 0), flag = wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        gridBag.Add(self.dbmpFastaField, (1, 1), span = (1, 4), flag = wx.EXPAND)
        gridBag.Add(self.dbmpFastaButton, (1, 5), flag = wx.ALIGN_RIGHT)

        gridBag.Add(self.regexLabel, (2, 0), flag = wx.ALIGN_RIGHT | wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
        gridBag.Add(self.regexField, (2, 1), span = (1, 4), flag = wx.EXPAND)
        gridBag.Add(self.regexButton, (2, 5), flag = wx.ALIGN_RIGHT)

        gridBag.Add(self.dbmpCall, (3, 1))


        gridBag.Add(wx.StaticLine(overPanel, -1), (7, 0), span = (1, 6), flag = wx.EXPAND)

        lookupLabel = wx.StaticText(overPanel, -1, "Annotate Search Results")

        self.lookupDBField = wx.TextCtrl(overPanel, -1, "", size = (-1, -1))
        self.lookupDBLabel = wx.StaticText(overPanel, -1, "Pep2Gene Database")
        self.lookupDBButton = wx.Button(overPanel, -1, "Browse")
        self.lookupDBButton.Bind(wx.EVT_BUTTON, self.choose_DB)
        self.lookupDBLabel.SetToolTip(wx.ToolTip(databaseTip))
        self.lookupDBField.SetToolTip(wx.ToolTip(databaseTip))

        self.lookupSRField = wx.TextCtrl(overPanel, -1, "", size = (-1, -1))
        self.lookupSRLabel = wx.StaticText(overPanel, -1, "Target File")
        self.lookupSRButton = wx.Button(overPanel, -1, "Browse")
        self.lookupSRButton.Bind(wx.EVT_BUTTON, self.choose_SR)
        self.lookupSRLabel.SetToolTip(wx.ToolTip(targetTip))
        self.lookupSRField.SetToolTip(wx.ToolTip(targetTip))

        self.lookupCall = wx.Button(overPanel, -1, "Calculate")
        self.lookupCall.Bind(wx.EVT_BUTTON, self.run_p2g)

        gridBag.Add(lookupLabel, (8, 0), flag = wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        gridBag.Add(self.lookupDBLabel, (9, 0), flag = wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        gridBag.Add(self.lookupDBField, (9, 1), span = (1, 4), flag = wx.EXPAND)
        gridBag.Add(self.lookupDBButton, (9, 5), flag  = wx.ALIGN_RIGHT)
        gridBag.Add(self.lookupSRLabel, (10, 0), flag = wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        gridBag.Add(self.lookupSRField, (10, 1), span = (1, 4), flag = wx.EXPAND)
        gridBag.Add(self.lookupSRButton, (10, 5), flag = wx.ALIGN_RIGHT)
        gridBag.Add(self.lookupCall, (11, 1))


        self.programBar = wx.TextCtrl(overPanel, -1, "=== Pep2Gene Utility ===",
                                      style = wx.TE_READONLY | wx.TE_CENTRE)
        gridBag.Add(self.programBar, (12, 0), span = (1, 6),flag = wx.EXPAND)


        gridBag.AddGrowableCol(2)

        overBox = wx.BoxSizer()
        overBox.Add(gridBag, 1, wx.ALL | wx.EXPAND, 20)
        overPanel.SetSizerAndFit(overBox)
        self.Show()

    def choose_fasta(self, event):
        folder_chooser = wx.FileDialog(self, "Choose FASTA File:", wildcard = "SwissProt|*.fasta|NCBI|*.faa")
        if folder_chooser.ShowModal() == wx.ID_OK:
            self.dbmpFastaField.SetValue(folder_chooser.GetPath())
        folder_chooser.Destroy()        

    def choose_geneRef(self, event):
        folder_chooser = wx.FileDialog(self, "Choose Gene Reference File:")
        if folder_chooser.ShowModal() == wx.ID_OK:
            self.dbmpGRefField.SetValue(folder_chooser.GetPath())
        folder_chooser.Destroy()

    def choose_DB(self, event):
        folder_chooser = wx.FileDialog(self, "Choose Pep2Gene Database:",
                                       wildcard = "Pep2Gene Database |*.pep2gene| All Files |*.*")
        if folder_chooser.ShowModal() == wx.ID_OK:
            self.lookupDBField.SetValue(folder_chooser.GetPath())
        folder_chooser.Destroy()

    def choose_SR(self, event):
        folder_chooser = wx.FileDialog(self, "Choose Search Results File:",
                                       style = wx.FD_MULTIPLE)
        if folder_chooser.ShowModal() == wx.ID_OK:
            folderList = '; '.join(folder_chooser.GetPaths())
            self.lookupSRField.SetValue(folderList)
        folder_chooser.Destroy()        

    def makeFastaDB(self, event):
        print "Compiling Pep2Gene database..."

        fastaFile = self.dbmpFastaField.GetValue()
        if not os.path.isabs(fastaFile):
            fastaFile = [x for x in fastaFiles if os.path.basename(x) == fastaFile][0]
        #geneRef = self.dbmpGRefField.GetValue()
        regex = self.regexField.GetValue()
        #dbType = self.databaseTypeCtrl.GetValue()
        #taxon = self.taxonField.GetValue()
        outputFileName = (os.path.basename(fastaFile) + ".pep2gene")
        outputFile = os.path.join(myData, outputFileName)

        #labelParser = lambda x: re.search(regex, x).group(0)
        #parser = re.compile(regex)
        #def labelParser(label):
            #parsed = parser.search(label)
            #if not parsed:
                #raise IOError, "Could not parse FASTA label: %s" % label
            #return parsed.group(0)
        #dbType = 'NCBI' if dbType == 'NCBI' else 'UniProt'

        self.programBar.Clear()
        self.programBar.AppendText("Creating .pep2gene file...")
        self.dbmpCall.Enable(False)
        try:
            def completionCallback(outputFile):
                self.programBar.Clear()
                self.programBar.AppendText("Wrote %s" % outputFile)   
            #create_fasta_index(fastaFile, outputFile, regex)
            async.launch_process(create_fasta_index, completionCallback,
                                 fastaFile, outputFile, regex)
        except Exception as err:
            self.programBar.Clear()
        finally:
            self.dbmpCall.Enable(True)


        print "Wrote %s ." % outputFile
        print "Done."

    def run_p2g(self, event):
        print "Running Pep2Gene..."

        database = self.lookupDBField.GetValue()
        targets = self.lookupSRField.GetValue()

        self.programBar.AppendText("Annotating results files...")        	
        for target in [x.strip() for x in targets.split(';')]:
            self.programBar.Clear()
            self.programBar.AppendText("Annotating %s..." % target)
            self.lookupCall.Enable(False)
            try:
                def completionCallback(outputfile):
                    self.programBar.Clear()
                    self.programBar.AppendText("Wrote %s" % outputfile)
                #add_gene_ids(target, database, inPlace = False, distinguish_leucine=True)
                async.launch_process(add_gene_ids, completionCallback,
                                     target, database, inPlace = False, leucineAmbiguity=True)
            except Exception as err:
                self.programBar.Clear()
            finally:
                self.lookupCall.Enable(False)
            

        print "Done."

    def runRegexUtility(self, event):
        fastaFile = self.dbmpFastaField.GetValue()
        exampleLabel = ''
        if fastaFile and os.path.exists(fastaFile):
            fasta = open(fastaFile, 'r')
            for line in fasta:
                if line[0] == '>':
                    exampleLabel = line.strip()
                    break
            fasta.close()

        regHelp = RegexHelper(self, startRegex = self.regexField.GetValue(),
                              startSample = exampleLabel)
        if regHelp.ShowModal() == wx.ID_OK:
            regex = regHelp.getRegex()
            self.regexField.SetValue(regex)

    def dbSwitch(self, event):
        dbType = self.databaseTypeCtrl.GetValue()
        #assert dbType in databaseTypes

        if not dbType == 'NCBI':
            self.dbmpGRefLabel.SetValue("UniProt ID Mapping File")
            self.regexLabel.SetValue("FASTA-to-UniProt ID Regex")
            self.dbmpGRefLabel.SetToolTip(wx.ToolTip(uniprotMapTip))
            self.regexLabel.SetToolTip(wx.ToolTip(fastaUniprotTip))
            self.regexField.SetValue("(?<=\|)[A-Z0-9\-]{1,10}(?=\|)(?# SwissProt/UniProt)")
        else:
            self.dbmpGRefLabel.SetValue("Gene2RefSeq File")
            self.regexLabel.SetValue("FASTA-to-Gene ID Regex")
            self.dbmpGRefLabel.SetToolTip(wx.ToolTip(Gene2RefSeqTip))
            self.regexLabel.SetToolTip(wx.ToolTip(regexGeneIdTip))
            self.regexField.SetValue("(?<=ref\|)[A-Z0-9\-\_\.]{1,20}(?=\|)(?# NCBI)")

def runPep2Gene():
    app = wx.App(0)
    session = p2gSession(None)
    app.MainLoop()

if __name__ == '__main__':
    runPep2Gene()