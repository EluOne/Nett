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
from common.api import onError, reprocess, fetchItems

from ObjectListView import ObjectListView, ColumnDefn, GroupListView

# System db id numbers
systemNames = {30002659: 'Dodixie', 30000142: 'Jita', 30002053: 'Hek', 30002187: 'Amarr'}  # 30002510: 'Rens'
# Mineral db id numbers
mineralIDs = {34: 'Tritanium', 35: 'Pyerite', 36: 'Mexallon', 37: 'Isogen',
              38: 'Nocxium', 39: 'Zydrine', 40: 'Megacyte', 11399: 'Morphite'}

# This will be the lists for the ui choices on the market.
quickbarList = []
materialsList = []
itemList = []
marketGroups = {}
marketRelations = {}
numIDs = 0


# This is the class where we will store item data from the database and Eve-Central queries.
class Item(object):
    def __init__(self, itemID, itemName, marketGroupID):
        self.itemID = itemID
        self.itemName = itemName
        self.marketGroupID = marketGroupID


# This is the class where we will store material data from the database and Eve-Central queries.
# I have decided to use the name Material instead of Minerals as the upcoming changes to reprocessing
# will affect the returned outcome to include recyclable parts.
class Material(object):
    def __init__(self, materialID, materialName):
        self.materialID = materialID
        self.materialName = materialName


class MainWindow(wx.Frame):
    def __init__(self, *args, **kwds):
        kwds["style"] = wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, *args, **kwds)

        # List and Dictionary initialisation.
        if itemList == []:  # Build a list of all items from the static data dump.
            try:
                con = lite.connect('sqlite-latest.sqlite')
                con.text_factory = str

                with con:
                    cur = con.cursor()
                    statement = "SELECT typeID, typeName, marketGroupID FROM invtypes WHERE marketGroupID >= 0 ORDER BY typeName;"
                    cur.execute(statement)

                    rows = cur.fetchall()

                    for row in rows:
                        itemList.append(Item(int(row[0]), str(row[1]), int(row[2])))

                    groupStatement = "SELECT marketGroupID, marketGroupName FROM invMarketGroups WHERE marketGroupID >= 0 ORDER BY marketGroupID;"
                    cur.execute(groupStatement)

                    groupRows = cur.fetchall()

                    for row in groupRows:
                        marketGroups.update({int(row[0]): str(row[1])})

                    relationStatement = "SELECT marketGroupID, parentGroupID FROM invMarketGroups ORDER BY parentGroupID;"
                    cur.execute(relationStatement)

                    relationRows = cur.fetchall()

                    for row in relationRows:
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

        self.leftNotebook = wx.Notebook(self, wx.ID_ANY, style=0)
        self.marketNotebookPane = wx.Panel(self.leftNotebook, wx.ID_ANY)
        self.searchTextCtrl = wx.TextCtrl(self.marketNotebookPane, wx.ID_ANY, "")
        self.searchButton = wx.Button(self.marketNotebookPane, wx.ID_FIND, (""))
        self.marketTree = wx.TreeCtrl(self.marketNotebookPane, wx.ID_ANY, style=wx.TR_HAS_BUTTONS | wx.TR_DEFAULT_STYLE | wx.SUNKEN_BORDER)
        self.addButton = wx.Button(self.marketNotebookPane, wx.ID_ANY, ("Add to Quickbar"))
        self.fetchButton = wx.Button(self.marketNotebookPane, wx.ID_ANY, ("Fetch Data"))

        self.quickbarNotebookPane = wx.Panel(self.leftNotebook, wx.ID_ANY)
        self.quickbarListCtrl = ObjectListView(self.quickbarNotebookPane, wx.ID_ANY, style=wx.LC_REPORT | wx.SUNKEN_BORDER)
        self.removeButton = wx.Button(self.quickbarNotebookPane, wx.ID_ANY, ("Remove From Quickbar"))
        self.fetchButtonTwo = wx.Button(self.quickbarNotebookPane, wx.ID_ANY, ("Fetch Data"))

        self.materiallsNotebookPane = wx.Panel(self.leftNotebook, wx.ID_ANY)
        self.materialsListCtrl = GroupListView(self.materiallsNotebookPane, wx.ID_ANY, style=wx.LC_REPORT | wx.SUNKEN_BORDER)

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

        # register the self.onExpand function to be called
        wx.EVT_TREE_ITEM_EXPANDING(self.marketTree, self.marketTree.GetId(), self.onExpand)

        self.__set_properties()
        self.__do_layout()

    def __set_properties(self):
        self.SetTitle(("Nett"))
        self.SetSize((1024, 600))
        self.rightPanel.SetScrollRate(10, 10)
        self.SetBackgroundColour(wx.NullColour)  # Use system default colour

        self.statusbar.SetStatusText('Welcome to Nett')

        self.quickbarListCtrl.SetEmptyListMsg('Add some items\nto start')

        self.quickbarListCtrl.SetColumns([
            ColumnDefn('Name', 'left', -1, 'itemName'),
        ])

        self.materialsListCtrl.SetColumns([
            ColumnDefn('Name', 'left', -1, 'materialName'),
            ColumnDefn('Buy', 'right', -1, 'materialBuy'),
            ColumnDefn('Sell', 'right', -1, 'materialSell'),
        ])

    def __do_layout(self):
        mainSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.itemsSizer = wx.BoxSizer(wx.VERTICAL)
        materialSizer = wx.BoxSizer(wx.VERTICAL)
        quickbarSizer = wx.BoxSizer(wx.VERTICAL)
        mainMarketSizer = wx.BoxSizer(wx.VERTICAL)

        searchSizer = wx.BoxSizer(wx.HORIZONTAL)
        searchSizer.Add(self.searchTextCtrl, 1, wx.EXPAND, 0)
        searchSizer.Add(self.searchButton, 0, wx.ADJUST_MINSIZE, 0)
        marketButtonSizer = wx.BoxSizer(wx.HORIZONTAL)
        marketButtonSizer.Add(self.addButton, 1, wx.ADJUST_MINSIZE, 0)
        marketButtonSizer.Add(self.fetchButton, 1, wx.ADJUST_MINSIZE, 0)
        mainMarketSizer.Add(searchSizer, 0, wx.EXPAND, 0)
        mainMarketSizer.Add(self.marketTree, 2, wx.EXPAND, 0)
        mainMarketSizer.Add(marketButtonSizer, 0, wx.EXPAND, 0)
        self.marketNotebookPane.SetSizer(mainMarketSizer)

        quickbarButtonSizer = wx.BoxSizer(wx.HORIZONTAL)
        quickbarButtonSizer.Add(self.removeButton, 1, wx.ADJUST_MINSIZE, 0)
        quickbarButtonSizer.Add(self.fetchButtonTwo, 1, wx.ADJUST_MINSIZE, 0)
        quickbarSizer.Add(self.quickbarListCtrl, 1, wx.EXPAND, 0)
        quickbarSizer.Add(quickbarButtonSizer, 0, wx.EXPAND, 0)
        self.quickbarNotebookPane.SetSizer(quickbarSizer)

        materialSizer.Add(self.materialsListCtrl, 1, wx.EXPAND, 0)
        self.materiallsNotebookPane.SetSizer(materialSizer)

        self.leftNotebook.AddPage(self.marketNotebookPane, ("Market"))
        self.leftNotebook.AddPage(self.quickbarNotebookPane, ("Quickbar"))
        self.leftNotebook.AddPage(self.materiallsNotebookPane, ("Minerals"))
        mainSizer.Add(self.leftNotebook, 1, wx.EXPAND, 0)

        self.rightPanel.SetSizer(self.itemsSizer)
        mainSizer.Add(self.rightPanel, 2, wx.EXPAND, 0)
        self.SetSizer(mainSizer)
        self.Layout()

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
                if itemList[x].marketGroupID == parentGroup:
                    newsubGroups.append(int(x))
            newsubGroups.sort()

            for child in newsubGroups:
                childGroup = child
                childID = self.marketTree.AppendItem(parentID, str(itemList[child].itemName))
                self.marketTree.SetPyData(childID, (itemList[child].itemID, False, True))
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
                        if itemList[x].marketGroupID == newParentGroup:
                            newsubGroups.append(int(x))
                    newsubGroups.sort()

                    for grandchild in newsubGroups:
                        grandchildGroup = grandchild
                        grandchildID = self.marketTree.AppendItem(newParentID, str(itemList[grandchild].itemName))
                        self.marketTree.SetPyData(grandchildID, (grandchildGroup, False, False))

    def onAddWidget(self, moduleID, moduleName):
        '''onAddWidget will add widgets into the right scrolling
        panel as required to show the number of items prices'''
        # Lets try add to the right panel.
        self.moduleSizer_1_staticbox = wx.StaticBox(self.rightPanel, wx.ID_ANY, (str(moduleName)), name="module_%s" % moduleID)
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
        itemGrid_1.Add(itemMarketLabel_1, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ADJUST_MINSIZE, 0)
        itemGrid_1.Add(itemAmarrLabel_1, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ADJUST_MINSIZE, 0)
        itemGrid_1.Add(itemDodiLabel_1, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ADJUST_MINSIZE, 0)
        itemGrid_1.Add(itemHekLabel_1, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ADJUST_MINSIZE, 0)
        itemGrid_1.Add(itemJitaLabel_1, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ADJUST_MINSIZE, 0)
        itemGrid_1.Add(itemSellLabel_1, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ADJUST_MINSIZE, 0)
        itemGrid_1.Add(itemAmarrSell_1, 0, wx.ADJUST_MINSIZE, 0)
        itemGrid_1.Add(itemDodiSell_1, 0, wx.ADJUST_MINSIZE, 0)
        itemGrid_1.Add(itemHekSell_1, 0, wx.ADJUST_MINSIZE, 0)
        itemGrid_1.Add(itemJitaSell_1, 0, wx.ADJUST_MINSIZE, 0)
        itemGrid_1.Add(itemBuyLabel_1, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ADJUST_MINSIZE, 0)
        itemGrid_1.Add(itemAmarrBuy_1, 0, wx.ADJUST_MINSIZE, 0)
        itemGrid_1.Add(itemDodiBuy_1, 0, wx.ADJUST_MINSIZE, 0)
        itemGrid_1.Add(itemHekBuy_1, 0, wx.ADJUST_MINSIZE, 0)
        itemGrid_1.Add(itemJitaBuy_1, 0, wx.ADJUST_MINSIZE, 0)
        moduleSizer_1.Add(itemGrid_1, 1, wx.EXPAND, 0)

        moduleSizer_1.Add(static_line_1, 0, wx.EXPAND, 0)

        moduleSizer_1.Add(reproLabel_1, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ADJUST_MINSIZE, 0)
        reproGrid_1.Add(reproMarketLabel_1, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ADJUST_MINSIZE, 0)
        reproGrid_1.Add(reproAmarrLabel_1, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ADJUST_MINSIZE, 0)
        reproGrid_1.Add(reproDodiLabel_1, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ADJUST_MINSIZE, 0)
        reproGrid_1.Add(reproHekLabel_1, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ADJUST_MINSIZE, 0)
        reproGrid_1.Add(reproJitaLabel_1, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ADJUST_MINSIZE, 0)
        reproGrid_1.Add(reproSellLabel_1, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ADJUST_MINSIZE, 0)
        reproGrid_1.Add(reproAmarrSell_1, 0, wx.ADJUST_MINSIZE, 0)
        reproGrid_1.Add(reproDodiSell_1, 0, wx.ADJUST_MINSIZE, 0)
        reproGrid_1.Add(reproHekSell_1, 0, wx.ADJUST_MINSIZE, 0)
        reproGrid_1.Add(reproJitaSell_1, 0, wx.ADJUST_MINSIZE, 0)
        reproGrid_1.Add(reproBuyLabel_1, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ADJUST_MINSIZE, 0)
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

        # Check its an item not a market group
        if pydata[2] == True:
            selectedID = pydata[0]
            for item in itemList:
                # Find the selected ID in the complete item list
                if item.itemID == selectedID:
                    # Check for duplicates in the quickbar list
                    if item not in quickbarList:
                        quickbarList.append(item)

        self.quickbarListCtrl.SetObjects(quickbarList)

    # Start of process() function
    def onProcess(self, event):
        # TODO: Add a query limit of some form, so we are nice to the Eve-Central servers.
        if quickbarList != []:
            # Build a list of item ids to send to Eve-Central.
            idList = []
            for item in quickbarList:
                idList.append(item.itemID)
            # We'll tag on the mineral query with the item ids to save traffic.
            for mineral in mineralIDs:
                idList.append(mineral)

            print(idList)
            #idList = [4473, 16437...]
            self.statusbar.SetStatusText('Welcome to Nett - ' + 'Fetching Data from Eve-Central.com...')

            dodixieMineralBuy, dodixieMineralSell, jitaMineralBuy, jitaMineralSell, hekMineralBuy, hekMineralSell, amarrMineralBuy, amarrMineralSell, dodixieItemBuy, dodixieItemSell, jitaItemBuy, jitaItemSell, hekItemBuy, hekItemSell, amarrItemBuy, amarrItemSell = fetchItems(idList)

            print("Mineral Prices by System\n")

            for mineral in mineralIDs:
                print('%s (%s): (Dodixie: Buy: %s / Sell: %s) (Jita: Buy: %s / Sell: %s) (Amarr: Buy: %s / Sell: %s) (Hek: Buy: %s / Sell: %s)' % (mineralIDs[mineral], int(mineral),
                                                                                             dodixieMineralBuy[mineral], dodixieMineralSell[mineral],
                                                                                             jitaMineralBuy[mineral], jitaMineralSell[mineral],
                                                                                             amarrMineralBuy[mineral], amarrMineralSell[mineral],
                                                                                             hekMineralBuy[mineral], hekMineralSell[mineral]))

            for item in quickbarList:
                output = reprocess(item.itemID)
                print(output)

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

                if wx.FindWindowByName("module_%s" % int(item.itemID)):
                    continue
                else:
                    self.onAddWidget(int(item.itemID), item.itemName)

                # Send Values to the GUI elements. as we have added to the wx widgets
                # on the fly the easiest way to identify the widgets is by their unique
                # names assigned on creation.
                # '{:,.2f}'.format(value) Uses the Format Specification Mini-Language to produce more human friendly output.

                # Item Values
                amarrBuy = wx.FindWindowByName("itemAmarrBuy_%s" % int(item.itemID))
                amarrBuy.SetValue('{:,.2f}'.format(amarrItemBuy[item.itemID]))
                dodiBuy = wx.FindWindowByName("itemDodiBuy_%s" % int(item.itemID))
                dodiBuy.SetValue('{:,.2f}'.format(dodixieItemBuy[item.itemID]))
                hekBuy = wx.FindWindowByName("itemHekBuy_%s" % int(item.itemID))
                hekBuy.SetValue('{:,.2f}'.format(hekItemBuy[item.itemID]))
                jitBuy = wx.FindWindowByName("itemJitaBuy_%s" % int(item.itemID))
                jitBuy.SetValue('{:,.2f}'.format(jitaItemBuy[item.itemID]))

                amarrSell = wx.FindWindowByName("itemAmarrSell_%s" % int(item.itemID))
                amarrSell.SetValue('{:,.2f}'.format(amarrItemSell[item.itemID]))
                dodiSell = wx.FindWindowByName("itemDodiSell_%s" % int(item.itemID))
                dodiSell.SetValue('{:,.2f}'.format(dodixieItemSell[item.itemID]))
                hekSell = wx.FindWindowByName("itemHekSell_%s" % int(item.itemID))
                hekSell.SetValue('{:,.2f}'.format(hekItemSell[item.itemID]))
                jitSell = wx.FindWindowByName("itemJitaSell_%s" % int(item.itemID))
                jitSell.SetValue('{:,.2f}'.format(jitaItemSell[item.itemID]))

                # Reprocess Values
                amarrBuy = wx.FindWindowByName("reproAmarrBuy_%s" % int(item.itemID))
                amarrBuy.SetValue('{:,.2f}'.format(amarrBuyTotal))
                dodiBuy = wx.FindWindowByName("reproDodiBuy_%s" % int(item.itemID))
                dodiBuy.SetValue('{:,.2f}'.format(dodixieBuyTotal))
                hekBuy = wx.FindWindowByName("reproHekBuy_%s" % int(item.itemID))
                hekBuy.SetValue('{:,.2f}'.format(hekBuyTotal))
                jitBuy = wx.FindWindowByName("reproJitaBuy_%s" % int(item.itemID))
                jitBuy.SetValue('{:,.2f}'.format(jitaBuyTotal))

                amarrSell = wx.FindWindowByName("reproAmarrSell_%s" % int(item.itemID))
                amarrSell.SetValue('{:,.2f}'.format(amarrSellTotal))
                dodiSell = wx.FindWindowByName("reproDodiSell_%s" % int(item.itemID))
                dodiSell.SetValue('{:,.2f}'.format(dodixieSellTotal))
                hekSell = wx.FindWindowByName("reproHekSell_%s" % int(item.itemID))
                hekSell.SetValue('{:,.2f}'.format(hekSellTotal))
                jitSell = wx.FindWindowByName("reproJitaSell_%s" % int(item.itemID))
                jitSell.SetValue('{:,.2f}'.format(jitaSellTotal))

            self.statusbar.SetStatusText('Welcome to Nett - ' + 'Idle')

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
