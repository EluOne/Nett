#!/usr/bin/python
'Nova Echo Trade Tool'
# Copyright (C) 2014  Tim Cumming
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Author: Tim Cumming aka Elusive One
# Created: 01/04/14

import wx
import sqlite3 as lite

import config
from common.api import onError, reprocess, fetchMinerals, fetchItems

# System db id numbers
systemNames = {30002659: 'Dodixie', 30000142: 'Jita', 30002053: 'Hek', 30002187: 'Amarr'}  # 30002510: 'Rens'
# Mineral db id numbers
mineralIDs = {34: 'Tritanium', 35: 'Pyerite', 36: 'Mexallon', 37: 'Isogen', 38: 'Nocxium', 39: 'Zydrine', 40: 'Megacyte'}

# This will be the lists for the ui choices on the market.
itemList = []
marketGroups = {}
marketRelations = {}
numIDs = 0
# This will be the list shown in the Quickbar
typeNames = {}


class MainWindow(wx.Frame):
    def __init__(self, *args, **kwds):
        kwds["style"] = wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, *args, **kwds)

        # List and Dictionary initialisation.
        if itemList == []:  # Build a list of all blueprints and facilities from the static data dump.
            try:
                con = lite.connect('sqlite-latest.sqlite')
                con.text_factory = str

                with con:
                    cur = con.cursor()
                    statement = "SELECT typeID, typeName, marketGroupID FROM invtypes WHERE marketGroupID >= 0 ORDER BY typeName;"
                    cur.execute(statement)

                    rows = cur.fetchall()

                    for row in rows:
                        # typeID, typeName
                        itemList.append([int(row[0]), str(row[1]), int(row[2])])

                    groupStatement = "SELECT marketGroupID, marketGroupName FROM invMarketGroups WHERE marketGroupID >= 0 ORDER BY marketGroupID;"
                    cur.execute(groupStatement)

                    groupRows = cur.fetchall()

                    for row in groupRows:
                        # typeID, typeName
                        marketGroups.update({int(row[0]): str(row[1])})

                    relationStatement = "SELECT marketGroupID, parentGroupID FROM invMarketGroups ORDER BY parentGroupID;"
                    cur.execute(relationStatement)

                    relationRows = cur.fetchall()

                    for row in relationRows:
                        # typeID, typeName
                        if row[1]:
                            marketRelations.update({int(row[0]): int(row[1])})
                        else:
                            marketRelations.update({int(row[0]): 'Market'})

            except lite.Error as err:
                error = ('SQL Lite Error: ' + repr(err.args[0]) + repr(err.args[1:]))  # Error String
                onError(error)
            finally:
                if con:
                    con.close()

        # Append list to selection box choice.
        #choices = [""]
        #for i in range(len(bpoList)):
        #    choices.append(str(bpoList[i][1]))

        #self.itemSearch = wx.ComboBox(self, wx.ID_ANY, choices=choices, style=wx.CB_DROPDOWN)

        #self.marketTree = wx.TreeCtrl(self, -1, style=wx.TR_HAS_BUTTONS | wx.TR_DEFAULT_STYLE | wx.SUNKEN_BORDER)

        #self.itemSelector = wx.ComboBox(self, wx.ID_ANY, choices=[], style=wx.CB_DROPDOWN)
        #self.fetchButton = wx.Button(self, wx.ID_ANY, ("Fetch Data"))
        #self.addButton = wx.Button(self, wx.ID_ANY, ("Add"))

        self.leftNotebook = wx.Notebook(self, wx.ID_ANY, style=0)
        self.marketNotebookPane = wx.Panel(self.leftNotebook, wx.ID_ANY)
        self.searchTextCtrl = wx.TextCtrl(self.marketNotebookPane, wx.ID_ANY, "")
        self.searchButton = wx.Button(self.marketNotebookPane, wx.ID_ANY, ("Search"))
        self.marketTree = wx.TreeCtrl(self.marketNotebookPane, wx.ID_ANY, style=wx.TR_HAS_BUTTONS | wx.TR_DEFAULT_STYLE | wx.SUNKEN_BORDER)
        self.addButton = wx.Button(self.marketNotebookPane, wx.ID_ANY, ("Add to Quickbar"))
        self.fetchButton = wx.Button(self.marketNotebookPane, wx.ID_ANY, ("Fetch Data"))
        self.notebook_1_pane_2 = wx.Panel(self.leftNotebook, wx.ID_ANY)
        self.quickbarListCtrl = wx.ListCtrl(self.notebook_1_pane_2, wx.ID_ANY, style=wx.LC_REPORT | wx.SUNKEN_BORDER)

        self.rightPanel = wx.ScrolledWindow(self, wx.ID_ANY, style=wx.TAB_TRAVERSAL)

        self.statusbar = self.CreateStatusBar()  # A Statusbar in the bottom of the window

        # Menu Bar
        self.frame_menubar = wx.MenuBar()

        self.fileMenu = wx.Menu()
        self.menuAbout = wx.MenuItem(self.fileMenu, wx.ID_ABOUT, "&About", "", wx.ITEM_NORMAL)
        self.fileMenu.AppendItem(self.menuAbout)

        self.menuExit = wx.MenuItem(self.fileMenu, wx.ID_EXIT, "E&xit", "", wx.ITEM_NORMAL)
        self.fileMenu.AppendItem(self.menuExit)

        self.frame_menubar.Append(self.fileMenu, "File")
        self.SetMenuBar(self.frame_menubar)
        # Menu Bar end

        # Menu events.
        self.Bind(wx.EVT_MENU, self.OnExit, self.menuExit)
        self.Bind(wx.EVT_MENU, self.OnAbout, self.menuAbout)

        self.Bind(wx.EVT_BUTTON, self.onProcess, self.fetchButton)
        self.Bind(wx.EVT_BUTTON, self.onAdd, self.addButton)

        self.__set_properties()
        self.__do_layout()

    def __set_properties(self):
        self.SetTitle(("Nett"))
        self.SetSize((1024, 600))
        self.rightPanel.SetScrollRate(10, 10)
        self.SetBackgroundColour(wx.NullColour)  # Use system default colour

        self.statusbar.SetStatusText('Welcome to Nema')

    def __do_layout(self):
        mainSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.itemsSizer = wx.BoxSizer(wx.VERTICAL)
        quickbarSizer = wx.BoxSizer(wx.VERTICAL)
        mainMarketSizer = wx.BoxSizer(wx.VERTICAL)
        searchSizer = wx.BoxSizer(wx.HORIZONTAL)
        searchSizer.Add(self.searchTextCtrl, 1, wx.EXPAND, 0)
        searchSizer.Add(self.searchButton, 0, wx.ADJUST_MINSIZE, 0)
        buttonSizer = wx.BoxSizer(wx.HORIZONTAL)
        buttonSizer.Add(self.addButton, 0, wx.ADJUST_MINSIZE, 0)
        buttonSizer.Add(self.fetchButton, 0, wx.ADJUST_MINSIZE, 0)

        mainMarketSizer.Add(searchSizer, 0, wx.EXPAND, 0)
        mainMarketSizer.Add(self.marketTree, 2, wx.EXPAND, 0)
        mainMarketSizer.Add(buttonSizer, 0, wx.EXPAND, 0)

        self.marketNotebookPane.SetSizer(mainMarketSizer)
        quickbarSizer.Add(self.quickbarListCtrl, 1, wx.EXPAND, 0)
        self.notebook_1_pane_2.SetSizer(quickbarSizer)
        self.leftNotebook.AddPage(self.marketNotebookPane, ("Market"))
        self.leftNotebook.AddPage(self.notebook_1_pane_2, ("Quickbar"))
        mainSizer.Add(self.leftNotebook, 1, wx.EXPAND, 0)

        self.rightPanel.SetSizer(self.itemsSizer)
        mainSizer.Add(self.rightPanel, 2, wx.EXPAND, 0)
        self.SetSizer(mainSizer)
        self.Layout()

        # register the self.onExpand function to be called
        wx.EVT_TREE_ITEM_EXPANDING(self.marketTree, self.marketTree.GetId(), self.onExpand)
        # initialize the marketTree
        self.buildTree('Market')

    def onExpand(self, event):
        '''onExpand is called when the user expands a node on the tree
        object. It checks whether the node has been previously expanded. If
        not, the extendTree function is called to build out the node, which
        is then marked as expanded.'''

        # get the wxID of the entry to expand and check it's validity
        itemID = event.GetItem()
        if not itemID.IsOk():
            itemID = self.marketTree.GetSelection()

        # only build that marketTree if not previously expanded
        old_pydata = self.marketTree.GetPyData(itemID)
        if old_pydata[1] == False:
            # clean the subtree and rebuild it
            self.marketTree.DeleteChildren(itemID)
            self.extendTree(itemID)
            self.marketTree.SetPyData(itemID, (old_pydata[0], True, old_pydata[2]))

    def buildTree(self, rootID):
        '''Add a new root element and then its children'''
        self.rootID = self.marketTree.AddRoot(rootID)
        self.marketTree.SetPyData(self.rootID, (rootID, 1))
        self.extendTree(self.rootID)
        self.marketTree.Expand(self.rootID)

    def extendTree(self, parentID):
        '''extendTree is a semi-lazy Tree builder. It takes
        the ID of a tree entry and fills in the tree with its child
        sub market groups and their children - updating 2 layers of the
        tree. This function is called by buildTree and onExpand methods'''
        parentGroup = self.marketTree.GetPyData(parentID)[0]
        subGroups = []
        numIDs = list(range(len(itemList)))

        for key in marketRelations:
            if marketRelations[key] == parentGroup:
                subGroups.append(int(key))
        subGroups.sort()

        if subGroups == []:
            # We've reached the end of the branch and must add the leaves.
            newsubGroups = []

            for x in numIDs:  # Iterate over all of the id lists generated above.
                if itemList[x][2] == parentGroup:
                    newsubGroups.append(int(x))
            newsubGroups.sort()

            for child in newsubGroups:
                childGroup = child
                childID = self.marketTree.AppendItem(parentID, str(itemList[child][1]))
                self.marketTree.SetPyData(childID, (itemList[child][0], False, True))
        else:
            for child in subGroups:
                childGroup = child
                # add the child to the parent
                childID = self.marketTree.AppendItem(parentID, str(marketGroups[child]))
                # associate the child ID with its marketTree entry
                self.marketTree.SetPyData(childID, (childGroup, False, False))

                # Now the child entry will show up, but it current has no
                # known children of its own and will not have a '+' showing
                # that it can be expanded to step further down the marketTree.
                # Solution is to go ahead and register the child's children,
                # meaning the grandchildren of the original parent
                newParentID = childID
                newParentGroup = childGroup
                newsubGroups = []

                for key in marketRelations:
                    if marketRelations[key] == newParentGroup:
                        newsubGroups.append(int(key))
                newsubGroups.sort()

                if newsubGroups != []:
                    for grandchild in newsubGroups:
                        grandchildGroup = grandchild
                        if marketRelations[grandchildGroup]:
                            grandchildID = self.marketTree.AppendItem(newParentID, str(marketGroups[grandchild]))
                            self.marketTree.SetPyData(grandchildID, (grandchildGroup, False, False))
                else:
                    for x in numIDs:  # Iterate over all of the id lists generated above.
                        if itemList[x][2] == newParentGroup:
                            newsubGroups.append(int(x))
                    newsubGroups.sort()

                    for grandchild in newsubGroups:
                        grandchildGroup = grandchild
                        grandchildID = self.marketTree.AppendItem(newParentID, str(itemList[grandchild][1]))
                        self.marketTree.SetPyData(grandchildID, (grandchildGroup, False, False))

    def onAddWidget(self, moduleID, moduleName):
        '''onAddWidget will add widgets into the right scrolling
        panel as required to show the number of items prices'''
        # Lets try add to the right panel.
        self.moduleSizer_1_staticbox = wx.StaticBox(self.rightPanel, wx.ID_ANY, (str(moduleName)))
        self.moduleSizer_1_staticbox.Lower()
        moduleSizer_1 = wx.StaticBoxSizer(self.moduleSizer_1_staticbox, wx.VERTICAL)
        reproGrid_1 = wx.GridSizer(3, 5, 0, 0)
        itemGrid_1 = wx.GridSizer(3, 5, 0, 0)

        itemLabel_1 = wx.StaticText(self.rightPanel, wx.ID_ANY, ("Item Value"))
        itemMarketLabel_1 = wx.StaticText(self.rightPanel, wx.ID_ANY, ("Market"))
        itemAmarrLabel_1 = wx.StaticText(self.rightPanel, wx.ID_ANY, ("Amarr"))
        itemDodiLabel_1 = wx.StaticText(self.rightPanel, wx.ID_ANY, ("Dodixie"))
        itemHekLabel_1 = wx.StaticText(self.rightPanel, wx.ID_ANY, ("Hek"))
        itemJitaLabel_1 = wx.StaticText(self.rightPanel, wx.ID_ANY, ("Jita"))
        itemSellLabel_1 = wx.StaticText(self.rightPanel, wx.ID_ANY, ("Sell"))
        itemAmarrSell_1 = wx.TextCtrl(self.rightPanel, wx.ID_ANY, "", size=(130, 21), style=wx.TE_RIGHT, name="itemAmarrSell_%s" % moduleID)
        itemDodiSell_1 = wx.TextCtrl(self.rightPanel, wx.ID_ANY, "", size=(130, 21), style=wx.TE_RIGHT, name="itemDodiSell_%s" % moduleID)
        itemHekSell_1 = wx.TextCtrl(self.rightPanel, wx.ID_ANY, "", size=(130, 21), style=wx.TE_RIGHT, name="itemHekSell_%s" % moduleID)
        itemJitaSell_1 = wx.TextCtrl(self.rightPanel, wx.ID_ANY, "", size=(130, 21), style=wx.TE_RIGHT, name="itemJitaSell_%s" % moduleID)
        itemBuyLabel_1 = wx.StaticText(self.rightPanel, wx.ID_ANY, ("Buy"))
        itemAmarrBuy_1 = wx.TextCtrl(self.rightPanel, wx.ID_ANY, "", size=(130, 21), style=wx.TE_RIGHT, name="itemAmarrBuy_%s" % moduleID)
        itemDodiBuy_1 = wx.TextCtrl(self.rightPanel, wx.ID_ANY, "", size=(130, 21), style=wx.TE_RIGHT, name="itemDodiBuy_%s" % moduleID)
        itemHekBuy_1 = wx.TextCtrl(self.rightPanel, wx.ID_ANY, "", size=(130, 21), style=wx.TE_RIGHT, name="itemHekBuy_%s" % moduleID)
        itemJitaBuy_1 = wx.TextCtrl(self.rightPanel, wx.ID_ANY, "", size=(130, 21), style=wx.TE_RIGHT, name="itemJitaBuy_%s" % moduleID)

        static_line_1 = wx.StaticLine(self.rightPanel, wx.ID_ANY)

        reproLabel_1 = wx.StaticText(self.rightPanel, wx.ID_ANY, ("Reprocessed Value"))
        reproMarketLabel_1 = wx.StaticText(self.rightPanel, wx.ID_ANY, ("Market"))
        reproAmarrLabel_1 = wx.StaticText(self.rightPanel, wx.ID_ANY, ("Amarr"))
        reproDodiLabel_1 = wx.StaticText(self.rightPanel, wx.ID_ANY, ("Dodixie"))
        reproHekLabel_1 = wx.StaticText(self.rightPanel, wx.ID_ANY, ("Hek"))
        reproJitaLabel_1 = wx.StaticText(self.rightPanel, wx.ID_ANY, ("Jita"))
        reproSellLabel_1 = wx.StaticText(self.rightPanel, wx.ID_ANY, ("Sell"))
        reproAmarrSell_1 = wx.TextCtrl(self.rightPanel, wx.ID_ANY, "", size=(130, 21), style=wx.TE_RIGHT, name="reproAmarrSell_%s" % moduleID)
        reproDodiSell_1 = wx.TextCtrl(self.rightPanel, wx.ID_ANY, "", size=(130, 21), style=wx.TE_RIGHT, name="reproDodiSell_%s" % moduleID)
        reproHekSell_1 = wx.TextCtrl(self.rightPanel, wx.ID_ANY, "", size=(130, 21), style=wx.TE_RIGHT, name="reproHekSell_%s" % moduleID)
        reproJitaSell_1 = wx.TextCtrl(self.rightPanel, wx.ID_ANY, "", size=(130, 21), style=wx.TE_RIGHT, name="reproJitaSell_%s" % moduleID)
        reproBuyLabel_1 = wx.StaticText(self.rightPanel, wx.ID_ANY, ("Buy"))
        reproAmarrBuy_1 = wx.TextCtrl(self.rightPanel, wx.ID_ANY, "", size=(130, 21), style=wx.TE_RIGHT, name="reproAmarrBuy_%s" % moduleID)
        reproDodiBuy_1 = wx.TextCtrl(self.rightPanel, wx.ID_ANY, "", size=(130, 21), style=wx.TE_RIGHT, name="reproDodiBuy_%s" % moduleID)
        reproHekBuy_1 = wx.TextCtrl(self.rightPanel, wx.ID_ANY, "", size=(130, 21), style=wx.TE_RIGHT, name="reproHekBuy_%s" % moduleID)
        reproJitaBuy_1 = wx.TextCtrl(self.rightPanel, wx.ID_ANY, "", size=(130, 21), style=wx.TE_RIGHT, name="reproJitaBuy_%s" % moduleID)

        moduleSizer_1.Add(itemLabel_1, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ADJUST_MINSIZE, 0)
        itemGrid_1.Add(itemMarketLabel_1, 0, wx.ADJUST_MINSIZE, 0)
        itemGrid_1.Add(itemAmarrLabel_1, 0, wx.ADJUST_MINSIZE, 0)
        itemGrid_1.Add(itemDodiLabel_1, 0, wx.ADJUST_MINSIZE, 0)
        itemGrid_1.Add(itemHekLabel_1, 0, wx.ADJUST_MINSIZE, 0)
        itemGrid_1.Add(itemJitaLabel_1, 0, wx.ADJUST_MINSIZE, 0)
        itemGrid_1.Add(itemSellLabel_1, 0, wx.ADJUST_MINSIZE, 0)
        itemGrid_1.Add(itemAmarrSell_1, 0, wx.ADJUST_MINSIZE, 0)
        itemGrid_1.Add(itemDodiSell_1, 0, wx.ADJUST_MINSIZE, 0)
        itemGrid_1.Add(itemHekSell_1, 0, wx.ADJUST_MINSIZE, 0)
        itemGrid_1.Add(itemJitaSell_1, 0, wx.ADJUST_MINSIZE, 0)
        itemGrid_1.Add(itemBuyLabel_1, 0, wx.ADJUST_MINSIZE, 0)
        itemGrid_1.Add(itemAmarrBuy_1, 0, wx.ADJUST_MINSIZE, 0)
        itemGrid_1.Add(itemDodiBuy_1, 0, wx.ADJUST_MINSIZE, 0)
        itemGrid_1.Add(itemHekBuy_1, 0, wx.ADJUST_MINSIZE, 0)
        itemGrid_1.Add(itemJitaBuy_1, 0, wx.ADJUST_MINSIZE, 0)
        moduleSizer_1.Add(itemGrid_1, 1, wx.EXPAND, 0)

        moduleSizer_1.Add(static_line_1, 0, wx.EXPAND, 0)

        moduleSizer_1.Add(reproLabel_1, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ADJUST_MINSIZE, 0)
        reproGrid_1.Add(reproMarketLabel_1, 0, wx.ADJUST_MINSIZE, 0)
        reproGrid_1.Add(reproAmarrLabel_1, 0, wx.ADJUST_MINSIZE, 0)
        reproGrid_1.Add(reproDodiLabel_1, 0, wx.ADJUST_MINSIZE, 0)
        reproGrid_1.Add(reproHekLabel_1, 0, wx.ADJUST_MINSIZE, 0)
        reproGrid_1.Add(reproJitaLabel_1, 0, wx.ADJUST_MINSIZE, 0)
        reproGrid_1.Add(reproSellLabel_1, 0, wx.ADJUST_MINSIZE, 0)
        reproGrid_1.Add(reproAmarrSell_1, 0, wx.ADJUST_MINSIZE, 0)
        reproGrid_1.Add(reproDodiSell_1, 0, wx.ADJUST_MINSIZE, 0)
        reproGrid_1.Add(reproHekSell_1, 0, wx.ADJUST_MINSIZE, 0)
        reproGrid_1.Add(reproJitaSell_1, 0, wx.ADJUST_MINSIZE, 0)
        reproGrid_1.Add(reproBuyLabel_1, 0, wx.ADJUST_MINSIZE, 0)
        reproGrid_1.Add(reproAmarrBuy_1, 0, wx.ADJUST_MINSIZE, 0)
        reproGrid_1.Add(reproDodiBuy_1, 0, wx.ADJUST_MINSIZE, 0)
        reproGrid_1.Add(reproHekBuy_1, 0, wx.ADJUST_MINSIZE, 0)
        reproGrid_1.Add(reproJitaBuy_1, 0, wx.ADJUST_MINSIZE, 0)
        moduleSizer_1.Add(reproGrid_1, 1, wx.EXPAND, 0)
        self.itemsSizer.Add(moduleSizer_1, 1, wx.EXPAND | wx.SHAPED, 0)
        self.rightPanel.SetSizer(self.itemsSizer)
        self.Layout()

    def onAdd(self, event):
        # Get current selection data from tree ctrl
        currentSelection = self.marketTree.GetSelection()
        pydata = self.marketTree.GetPyData(currentSelection)

        # Check its an item not a group
        if pydata[2] == True:
            itemID = pydata[0]
            for item in itemList:
                if item[0] == itemID:
                    typeNames.update({int(item[0]): str(item[1])})
        print(typeNames)

    # Start of process() function
    def onProcess(self, event):
        if typeNames != {}:
            dodixieMineralBuy, dodixieMineralSell, jitaMineralBuy, jitaMineralSell, hekMineralBuy, hekMineralSell, amarrMineralBuy, amarrMineralSell = fetchMinerals()

            print("Mineral Prices by System\n")

            for mineral in mineralIDs:
                print('%s (%s): (Dodixie: Buy: %s / Sell: %s) (Jita: Buy: %s / Sell: %s) (Amarr: Buy: %s / Sell: %s) (Hek: Buy: %s / Sell: %s)' % (mineralIDs[mineral], int(mineral),
                                                                                             dodixieMineralBuy[mineral], dodixieMineralSell[mineral],
                                                                                             jitaMineralBuy[mineral], jitaMineralSell[mineral],
                                                                                             amarrMineralBuy[mineral], amarrMineralSell[mineral],
                                                                                             hekMineralBuy[mineral], hekMineralSell[mineral]))

            idList = []
            for item in typeNames:
                idList.append(item)

            #idList = [4473, 16437...]
            dodixieItemBuy, dodixieItemSell, jitaItemBuy, jitaItemSell, hekItemBuy, hekItemSell, amarrItemBuy, amarrItemSell = fetchItems(idList)

            for item in typeNames:
                #output = reprocess(16437)
                output = reprocess(int(item))
                #print(typeNames[item])
                #print('%s (%s)\nDodixie: Buy: %s / Sell: %s\nJita: Buy: %s / Sell: %s\nAmarr: Buy: %s / Sell: %s\nHek: Buy: %s / Sell: %s' %
                #      (typeNames[item], int(item), dodixieItemBuy[item], dodixieItemSell[item],
                #        jitaItemBuy[item], jitaItemSell[item], amarrItemBuy[item], amarrItemSell[item], hekItemBuy[item], hekItemSell[item]))

                dodixieBuyTotal = 0  # Fullfilling Buy orders
                dodixieSellTotal = 0  # Placing Sell orders
                jitaBuyTotal = 0  # Fullfilling Buy orders
                jitaSellTotal = 0  # Placing Sell orders
                amarrBuyTotal = 0  # Fullfilling Buy orders
                amarrSellTotal = 0  # Placing Sell orders
                hekBuyTotal = 0  # Fullfilling Buy orders
                hekSellTotal = 0  # Placing Sell orders

                for key in output:
                    if key in mineralIDs:
                        dodixieBuyTotal = dodixieBuyTotal + (int(output[key]) * dodixieMineralBuy[key])
                        dodixieSellTotal = dodixieSellTotal + (int(output[key]) * dodixieMineralSell[key])
                        jitaBuyTotal = jitaBuyTotal + (int(output[key]) * jitaMineralBuy[key])
                        jitaSellTotal = jitaSellTotal + (int(output[key]) * jitaMineralSell[key])
                        amarrBuyTotal = amarrBuyTotal + (int(output[key]) * amarrMineralBuy[key])
                        amarrSellTotal = amarrSellTotal + (int(output[key]) * amarrMineralSell[key])
                        hekBuyTotal = hekBuyTotal + (int(output[key]) * hekMineralBuy[key])
                        hekSellTotal = hekSellTotal + (int(output[key]) * hekMineralSell[key])
                #print('Reprocessed (Perfect):\nDodixie: Buy: %s / Sell: %s\nJita: Buy: %s / Sell: %s\nAmarr: Buy: %s / Sell: %s\nHek: Buy: %s / Sell: %s\n' %
                #      (dodixieBuyTotal, dodixieSellTotal, jitaBuyTotal, jitaSellTotal, amarrBuyTotal, amarrSellTotal, hekBuyTotal, hekSellTotal))

                self.onAddWidget(int(item), typeNames[item])

                # Item Values
                amarrBuy = wx.FindWindowByName("itemAmarrBuy_%s" % int(item))
                amarrBuy.SetValue(str(amarrItemBuy[item]))
                dodiBuy = wx.FindWindowByName("itemDodiBuy_%s" % int(item))
                dodiBuy.SetValue(str(dodixieItemBuy[item]))
                hekBuy = wx.FindWindowByName("itemHekBuy_%s" % int(item))
                hekBuy.SetValue(str(hekItemBuy[item]))
                jitBuy = wx.FindWindowByName("itemJitaBuy_%s" % int(item))
                jitBuy.SetValue(str(jitaItemBuy[item]))

                amarrSell = wx.FindWindowByName("itemAmarrSell_%s" % int(item))
                amarrSell.SetValue(str(amarrItemSell[item]))
                dodiSell = wx.FindWindowByName("itemDodiSell_%s" % int(item))
                dodiSell.SetValue(str(dodixieItemSell[item]))
                hekSell = wx.FindWindowByName("itemHekSell_%s" % int(item))
                hekSell.SetValue(str(hekItemSell[item]))
                jitSell = wx.FindWindowByName("itemJitaSell_%s" % int(item))
                jitSell.SetValue(str(jitaItemSell[item]))

                # Reprocess Values
                amarrBuy = wx.FindWindowByName("reproAmarrBuy_%s" % int(item))
                amarrBuy.SetValue(str(amarrBuyTotal))
                dodiBuy = wx.FindWindowByName("reproDodiBuy_%s" % int(item))
                dodiBuy.SetValue(str(dodixieBuyTotal))
                hekBuy = wx.FindWindowByName("reproHekBuy_%s" % int(item))
                hekBuy.SetValue(str(hekBuyTotal))
                jitBuy = wx.FindWindowByName("reproJitaBuy_%s" % int(item))
                jitBuy.SetValue(str(jitaBuyTotal))

                amarrSell = wx.FindWindowByName("reproAmarrSell_%s" % int(item))
                amarrSell.SetValue(str(amarrSellTotal))
                dodiSell = wx.FindWindowByName("reproDodiSell_%s" % int(item))
                dodiSell.SetValue(str(dodixieSellTotal))
                hekSell = wx.FindWindowByName("reproHekSell_%s" % int(item))
                hekSell.SetValue(str(hekSellTotal))
                jitSell = wx.FindWindowByName("reproJitaSell_%s" % int(item))
                jitSell.SetValue(str(jitaSellTotal))

    def OnAbout(self, e):
        description = """A tool designed for our corporate industrialists to
compare items at the main market hubs.

If you like my work please consider an ISK donation to Elusive One.

All EVE-Online related materials are property of CCP hf."""

        licence = """NETT is released under GNU GPLv3:

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>."""

        info = wx.AboutDialogInfo()

        #info.SetIcon(wx.Icon('', wx.BITMAP_TYPE_PNG))
        info.SetName('Nova Echo Trade Tool')
        info.SetVersion(config.version)
        info.SetDescription(description)
        #info.SetCopyright('(C) 2013 Tim Cumming')
        info.SetWebSite('https://github.com/EluOne/Nett')
        info.SetLicence(licence)
        info.AddDeveloper('Tim Cumming aka Elusive One')
        #info.AddDocWriter('')
        #info.AddArtist('')
        #info.AddTranslator('')

        wx.AboutBox(info)

    def OnExit(self, e):
        dlg = wx.MessageDialog(self, 'Are you sure to quit Nett?', 'Please Confirm', wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
        if dlg.ShowModal() == wx.ID_YES:
            self.Close(True)

# end of class MainWindow
if __name__ == "__main__":
    app = wx.PySimpleApp(0)
    wx.InitAllImageHandlers()
    frame = MainWindow(None, wx.ID_ANY, "")
    app.SetTopWindow(frame)
    frame.Show()
    app.MainLoop()
