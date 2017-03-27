# Copyright 2008 Dana-Farber Cancer Institute
# multiplierz is distributed under the terms of the GNU Lesser General Public License
#
# This file is part of multiplierz/mzDesktop.
#
# multiplierz/mzDesktop is free software: you can redistribute it and/or modify
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
import wx.grid
import os

import multiplierz.mzReport

from multiplierz import myData
from multiplierz.mass_biochem import digest, mz

from multiplierz.mzGUI_standalone import report_chooser
from gui import BasicTab

class DigestPanel(BasicTab):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)

        gbs = wx.GridBagSizer(15, 7)

        gbs.Add( wx.StaticText(self, -1, 'Protein(s) in\nFasta Format', style=wx.ALIGN_RIGHT),
                 (0,0), flag=wx.ALIGN_RIGHT )

        self.proteinInput = wx.TextCtrl(self, -1, "", style=wx.TE_MULTILINE)
        gbs.Add( self.proteinInput,
                 (0,1), flag=wx.EXPAND )

        gbs.Add( wx.StaticText(self, -1, 'Enzyme', style=wx.ALIGN_RIGHT),
                 (1,0), flag=wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL)

        enzymeList =['Arg-C: [R][A-Z]',
                     'Asp-N: [A-Z][D]',
                     'Bromelain: [KAY][A-Z]',
                     'CNBr_HSer: [M][A-Z]',
                     'CNBr_HSerLac: [M][A-Z]',
                     'Cathepsin B: [R][A-Z]',
                     'Cathepsin D: [LF][^VAG]',
                     'Cathepsin G: [YWF][A-Z]',
                     'Chymotrypsin: [YWFL][A-Z]',
                     'Clostripain: [R][P]',
                     'Elastase: [AVLIGS][A-Z]',
                     'Glu-C_Bic: [E][A-Z]',
                     'Glu-C_Phos: [ED][A-Z]',
                     'Hydroxylamine: [N][G]',
                     'Lys-C: [K][A-Z]',
                     'Lys-N: [A-Z][K]',
                     'Papain: [RK][A-Z]',
                     'Pepsin: [LF][^VAG]',
                     'Proteinase K: [YWF][A-Z]',
                     'Subtilisin: [^RHK][A-Z]',
                     'Thermolysin: [LFIVMA][^P]',
                     'Trypsin: [KR][^P]']

        self.enzymeCB = wx.ComboBox(self, -1, choices=enzymeList, style=wx.CB_DROPDOWN)
        self.enzymeCB.SetSelection(0)
        gbs.Add( self.enzymeCB,
                 (1,1) )

        gbs.Add( wx.StaticText(self, -1, 'Missed Cleavages', style=wx.ALIGN_RIGHT),
                 (2,0), flag=wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL)

        self.missed_cleavagesCB = wx.ComboBox(self, -1, choices=['0', '1', '2', '3'], style=wx.CB_DROPDOWN)
        self.missed_cleavagesCB.SetSelection(0)
        gbs.Add( self.missed_cleavagesCB,
                 (2,1) )

        self.writeToggleCk = wx.CheckBox(self, -1, "Write Output to Report  ", style=wx.ALIGN_RIGHT)
        gbs.Add( self.writeToggleCk,
                 (3,0), (1,2), flag=wx.ALIGN_CENTER )

        #Submit Button
        digest_btn = wx.Button(self, -1, "Digest", size=(160,-1))
        gbs.Add( digest_btn,
                 (4,0), (1,2), flag=wx.ALIGN_CENTER )
        digest_btn.Bind(wx.EVT_BUTTON, self.OnClick)

        gbs.AddGrowableCol(1)
        gbs.AddGrowableRow(0)

        box = wx.BoxSizer()
        box.Add(gbs, 1, wx.ALL|wx.EXPAND, 20)
        self.SetSizerAndFit(box)

    def OnClick(self,event):
        #update statusbar
        self.set_status("Digesting...", 0)
        self.set_status("", 1)

        fasta_split = self.proteinInput.GetValue().split('\n')
        headers = []
        proteins = []

        for line in fasta_split:
            if not line:
                continue
            if line[0] == '>':
                headers.append(line[1:])
                proteins.append('')
                continue
            proteins[-1] += line.upper()


        enzyme = self.enzymeCB.GetValue()
        missed_cleavages = int(self.missed_cleavagesCB.GetValue())
        if enzyme[0] != "[":
            (enzyme,spec) = enzyme.split(':')

        data = []
        for (i, protein) in enumerate(proteins):
            digests = digest(protein, enzyme, missed_cleavages)
            header = headers[i]
            for (j, dig) in enumerate(digests):
                pep = digests[j][0]
                range = digests[j][1]
                m_c = digests[j][2]
                oneMass = "%0.3f" % mz(pep,[],1)
                twoMass = "%0.3f" % mz(pep,[],2)
                threeMass = "%0.3f" % mz(pep,[],3)
                data.append((header, pep, range, m_c, oneMass, twoMass, threeMass))


        if self.writeToggleCk.GetValue():
            writeFile = report_chooser(self, mode='w') or os.path.join(myData,'protDigest.csv')

            if os.path.exists(writeFile):
                os.remove(writeFile)

            cols = ['Header','Sequence','Range','Missed Cleavage',
                    '1+ Mass','2+ Mass','3+ Mass']
            report = multiplierz.mzReport.writer(writeFile, columns=cols)

            for peptide in data:
                pepRange = str(peptide[2][0])+'...'+str(peptide[2][1])
                report.write(peptide[:2] + (pepRange,) + peptide[3:])

            report.close()
        else:
            tableFrame = Table1(self, -1, "Digest Table", data)
            tableFrame.Show()

        #update statusbar
        self.set_status("Ready", 0)
        self.set_status("Done", 1)


class Table1(wx.Frame):
    def __init__(self,parent,id,TableTitle,digests):
        wx.Frame.__init__(self, parent, id, title = TableTitle, size=(640,480))

        #add icon
        self.SetIcon(parent.get_icon())

        colHeaders = ['Protein Header','Sequence','Range','Missed Cleavage','1+ Mass','2+ Mass','3+ Mass']
        rowCount = len(digests)

        pane = wx.Panel(self, -1, style = wx.TAB_TRAVERSAL | wx.CLIP_CHILDREN)

        #mass table
        grid = wx.grid.Grid(pane, -1)
        grid.CreateGrid(rowCount, len(colHeaders))

        #Set Column Headers
        for i,col in enumerate(colHeaders):
            grid.SetColLabelValue(i, col)

        #Print Data
        for i,peptide in enumerate(digests):
            for j,v in enumerate(peptide):
                if j != 2:
                    grid.SetCellValue(i,j,str(v))
                else:
                    grid.SetCellValue(i,j,'%d...%d' % v)

        grid.AutoSizeColumns(False)

        box = wx.BoxSizer()
        box.Add(grid, 1, wx.EXPAND|wx.ALL, 5)
        pane.SetSizerAndFit(box)

        w,h = self.GetSize()
        self.SetSize((grid.GetSize()[0]+36,h))
        self.SetMinSize((w/2,h/2))
