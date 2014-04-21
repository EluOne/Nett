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

import time
import datetime
import wx
import sqlite3 as lite

import config
from common.api import onError, reprocess, fetchItems

from ObjectListView import ObjectListView, ColumnDefn, GroupListView

# This will be the lists for the ui choices on the market.
quickbarList = []
materialsList = []
itemList = []
marketGroups = {}
marketRelations = {}
numIDs = 0


# This is the class where we will store item data from the database and Eve-Central queries.
class Item(object):
    def __init__(self, itemID, itemName, marketGroupID,
                 amarrItemBuy, dodixieItemBuy, hekItemBuy, jitaItemBuy,
                 amarrItemSell, dodixieItemSell, hekItemSell, jitaItemSell,
                 lastQuery, widgetKey):
        self.itemID = itemID
        self.itemName = itemName
        self.marketGroupID = marketGroupID
        # Market Buy Order Prices
        self.amarrItemBuy = amarrItemBuy
        self.dodixieItemBuy = dodixieItemBuy
        self.hekItemBuy = hekItemBuy
        self.jitaItemBuy = jitaItemBuy
        # Market Sell Order Prices
        self.amarrItemSell = amarrItemSell
        self.dodixieItemSell = dodixieItemSell
        self.hekItemSell = hekItemSell
        self.jitaItemSell = jitaItemSell
        # Use a per item time stamp to handle query limiting to the API server.
        self.lastQuery = lastQuery
        # Due to limits on 32bit machines we can't use the item IDs as the basis for widget IDs
        self.widgetKey = widgetKey


# This is the class where we will store material data from the database and Eve-Central queries.
# I have decided to use the name Material instead of Minerals as the upcoming changes to reprocessing
# will affect the returned outcome to include recyclable parts.
# This will probably end up being removed as it uses nearly all the same fields as above.
class Material(object):
    def __init__(self, materialID, materialName,
                 amarrBuy, dodixieBuy, hekBuy, jitaBuy,
                 amarrSell, dodixieSell, hekSell, jitaSell,
                 lastQuery):
        self.materialID = materialID
        self.materialName = materialName
        # Market Buy Order Prices
        self.amarrBuy = amarrBuy
        self.dodixieBuy = dodixieBuy
        self.hekBuy = hekBuy
        self.jitaBuy = jitaBuy
        # Market Sell Order Prices
        self.amarrSell = amarrSell
        self.dodixieSell = dodixieSell
        self.hekSell = hekSell
        self.jitaSell = jitaSell
        # Use a per item time stamp to handle query limiting to the API server.
        self.lastQuery = lastQuery


# This class is just for the display of material prices in the materialsListCtrl.
class MaterialRow(object):
    def __init__(self, materialName, systemName, materialBuy, materialSell):
        self.materialName = materialName
        self.systemName = systemName
        self.materialBuy = '{:,.2f}'.format(materialBuy)
        self.materialSell = '{:,.2f}'.format(materialSell)


class MainWindow(wx.Frame):
    def __init__(self, *args, **kwds):
        kwds["style"] = wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, *args, **kwds)

        self.numWidgets = 0

        # List and Dictionary initialisation.
        if itemList == []:  # Build a list of all items from the static data dump.
            try:
                con = lite.connect('static.db')  # Currently the full dump that I haven't uploaded. (325mb)
                con.text_factory = str

                with con:
                    cur = con.cursor()
                    # With this query we are looking to populate the itemID's with their respective names and parent market groups.
                    # Eve items currently go up to ID 33612, then Dust items start from 350916
                    statement = "SELECT typeID, typeName, marketGroupID FROM invtypes WHERE marketGroupID >= 0 ORDER BY typeName;"
                    cur.execute(statement)

                    rows = cur.fetchall()

                    for row in rows:
                        itemList.append(Item(int(row[0]), str(row[1]), int(row[2]), 0, 0, 0, 0, 0, 0, 0, 0, 0, 0))

                    # This query will hold all of the market group ID to name relations in a dictionary for ease.
                    groupStatement = "SELECT marketGroupID, marketGroupName FROM invMarketGroups WHERE marketGroupID >= 0 ORDER BY marketGroupID;"
                    cur.execute(groupStatement)

                    groupRows = cur.fetchall()

                    for row in groupRows:
                        marketGroups.update({int(row[0]): str(row[1])})

                    # This statement is for the branches of the market treeCtrl using all the market groups and their relationship to each other.
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
        self.searchTextCtrl = wx.TextCtrl(self.marketNotebookPane, wx.ID_ANY, "Search Not Available")
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

        self.statusbar = self.CreateStatusBar()  # A Status bar in the bottom of the window

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

        # Button Events
        self.Bind(wx.EVT_BUTTON, self.onProcess, self.fetchButton)
        self.Bind(wx.EVT_BUTTON, self.onProcess, self.fetchButtonTwo)

        self.Bind(wx.EVT_BUTTON, self.onAdd, self.addButton)
        self.Bind(wx.EVT_BUTTON, self.onRemove, self.removeButton)

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
            ColumnDefn('Name', 'left', 320, 'itemName'),
        ])

        self.materialsListCtrl.SetColumns([
            ColumnDefn('Name', 'left', 100, 'materialName'),
            ColumnDefn('Buy', 'right', 90, 'materialBuy'),
            ColumnDefn('Sell', 'right', 90, 'materialSell'),
            ColumnDefn('System', 'right', -1, 'systemName'),
        ])

        self.materialsListCtrl.SetSortColumn(self.materialsListCtrl.columns[4])

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

    def onAddWidget(self, moduleID, moduleName, widgetKey):
        '''onAddWidget will add widgets into the right scrolling
        panel as required to show the number of items prices'''
        # Lets try add to the right panel.
        #self.moduleSizer_1_staticbox = wx.StaticBox(self.rightPanel, wx.ID_ANY, (str(moduleName)), name="module_%s" % moduleID)
        self.moduleSizer_1_staticbox = wx.StaticBox(self.rightPanel, int('100%s' % widgetKey), (str(moduleName)), name="module_%s" % moduleID)
        self.moduleSizer_1_staticbox.Lower()
        moduleSizer_1 = wx.StaticBoxSizer(self.moduleSizer_1_staticbox, wx.VERTICAL)
        reproGrid_1 = wx.GridSizer(3, 5, 0, 0)
        itemGrid_1 = wx.GridSizer(3, 5, 0, 0)

        itemLabel_1 = wx.StaticText(self.rightPanel, wx.ID_ANY, ("Item Value"), name="itemValue_%s" % moduleID)
        itemMarketLabel_1 = wx.StaticText(self.rightPanel, wx.ID_ANY, ("Market"), name="itemMarket_%s" % moduleID)
        itemAmarrLabel_1 = wx.StaticText(self.rightPanel, wx.ID_ANY, ("Amarr"), name="itemAmarr_%s" % moduleID)
        itemDodiLabel_1 = wx.StaticText(self.rightPanel, wx.ID_ANY, ("Dodixie"), name="itemDodixie_%s" % moduleID)
        itemHekLabel_1 = wx.StaticText(self.rightPanel, wx.ID_ANY, ("Hek"), name="itemHek_%s" % moduleID)
        itemJitaLabel_1 = wx.StaticText(self.rightPanel, wx.ID_ANY, ("Jita"), name="itemJita_%s" % moduleID)
        itemSellLabel_1 = wx.StaticText(self.rightPanel, wx.ID_ANY, ("Sell"), name="itemSell_%s" % moduleID)
        #itemAmarrSell_1 = wx.TextCtrl(self.rightPanel, wx.ID_ANY, "", size=(130, 21), style=wx.TE_RIGHT, name="amarrItemSell_%s" % moduleID)
        itemAmarrSell_1 = wx.TextCtrl(self.rightPanel, int('101%s' % widgetKey), "", size=(130, 21), style=wx.TE_RIGHT, name="amarrItemSell_%s" % moduleID)
        itemDodiSell_1 = wx.TextCtrl(self.rightPanel, int('102%s' % widgetKey), "", size=(130, 21), style=wx.TE_RIGHT, name="dodixieItemSell_%s" % moduleID)
        itemHekSell_1 = wx.TextCtrl(self.rightPanel, int('103%s' % widgetKey), "", size=(130, 21), style=wx.TE_RIGHT, name="hekItemSell_%s" % moduleID)
        itemJitaSell_1 = wx.TextCtrl(self.rightPanel, int('104%s' % widgetKey), "", size=(130, 21), style=wx.TE_RIGHT, name="jitaItemSell_%s" % moduleID)
        itemBuyLabel_1 = wx.StaticText(self.rightPanel, wx.ID_ANY, ("Buy"), name="itemBuy_%s" % moduleID)
        itemAmarrBuy_1 = wx.TextCtrl(self.rightPanel, int('105%s' % widgetKey), "", size=(130, 21), style=wx.TE_RIGHT, name="amarrItemBuy_%s" % moduleID)
        itemDodiBuy_1 = wx.TextCtrl(self.rightPanel, int('106%s' % widgetKey), "", size=(130, 21), style=wx.TE_RIGHT, name="dodixieItemBuy_%s" % moduleID)
        itemHekBuy_1 = wx.TextCtrl(self.rightPanel, int('107%s' % widgetKey), "", size=(130, 21), style=wx.TE_RIGHT, name="hekItemBuy_%s" % moduleID)
        itemJitaBuy_1 = wx.TextCtrl(self.rightPanel, int('108%s' % widgetKey), "", size=(130, 21), style=wx.TE_RIGHT, name="jitaItemBuy_%s" % moduleID)

        static_line_1 = wx.StaticLine(self.rightPanel, wx.ID_ANY, name="line_%s" % moduleID)

        reproLabel_1 = wx.StaticText(self.rightPanel, wx.ID_ANY, ("Reprocessed Value"), name="reproValue_%s" % moduleID)
        reproMarketLabel_1 = wx.StaticText(self.rightPanel, wx.ID_ANY, ("Market"), name="reproMarket_%s" % moduleID)
        reproAmarrLabel_1 = wx.StaticText(self.rightPanel, wx.ID_ANY, ("Amarr"), name="reproAmarr_%s" % moduleID)
        reproDodiLabel_1 = wx.StaticText(self.rightPanel, wx.ID_ANY, ("Dodixie"), name="reproDodixie_%s" % moduleID)
        reproHekLabel_1 = wx.StaticText(self.rightPanel, wx.ID_ANY, ("Hek"), name="reproHek_%s" % moduleID)
        reproJitaLabel_1 = wx.StaticText(self.rightPanel, wx.ID_ANY, ("Jita"), name="reproJita_%s" % moduleID)
        reproSellLabel_1 = wx.StaticText(self.rightPanel, wx.ID_ANY, ("Sell"), name="reproSell_%s" % moduleID)
        reproAmarrSell_1 = wx.TextCtrl(self.rightPanel, int('201%s' % widgetKey), "", size=(130, 21), style=wx.TE_RIGHT, name="reproAmarrSell_%s" % moduleID)
        reproDodiSell_1 = wx.TextCtrl(self.rightPanel, int('202%s' % widgetKey), "", size=(130, 21), style=wx.TE_RIGHT, name="reproDodixieSell_%s" % moduleID)
        reproHekSell_1 = wx.TextCtrl(self.rightPanel, int('203%s' % widgetKey), "", size=(130, 21), style=wx.TE_RIGHT, name="reproHekSell_%s" % moduleID)
        reproJitaSell_1 = wx.TextCtrl(self.rightPanel, int('204%s' % widgetKey), "", size=(130, 21), style=wx.TE_RIGHT, name="reproJitaSell_%s" % moduleID)
        reproBuyLabel_1 = wx.StaticText(self.rightPanel, wx.ID_ANY, ("Buy"), name="reproBuy_%s" % moduleID)
        reproAmarrBuy_1 = wx.TextCtrl(self.rightPanel, int('205%s' % widgetKey), "", size=(130, 21), style=wx.TE_RIGHT, name="reproAmarrBuy_%s" % moduleID)
        reproDodiBuy_1 = wx.TextCtrl(self.rightPanel, int('206%s' % widgetKey), "", size=(130, 21), style=wx.TE_RIGHT, name="reproDodixieBuy_%s" % moduleID)
        reproHekBuy_1 = wx.TextCtrl(self.rightPanel, int('207%s' % widgetKey), "", size=(130, 21), style=wx.TE_RIGHT, name="reproHekBuy_%s" % moduleID)
        reproJitaBuy_1 = wx.TextCtrl(self.rightPanel, int('208%s' % widgetKey), "", size=(130, 21), style=wx.TE_RIGHT, name="reproJitaBuy_%s" % moduleID)

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

    def onRemoveWidget(self, widgetKey):
        """Remove all children components for a given module and destroy them"""
        child = wx.FindWindowById(int('100%s' % widgetKey))
        if child:
            parent = child.GetContainingSizer()

            widgetIds = [
                 '101', '102', '103', '104', '105', '106', '107', '108',
                 '201', '202', '203', '204', '205', '206', '207', '208'
                 ]
            for wid in widgetIds:
                widget = wx.FindWindowById(int('%s%s' % (wid, widgetKey)))
                if widget:
                    widget.Destroy()

            if parent:
                self.itemsSizer.Hide(parent)
                self.itemsSizer.Remove(parent)
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

    def onRemove(self, event):
        numItemRows = list(range(len(quickbarList)))

        # Get current selection from quickbarList ctrl
        for x in self.quickbarListCtrl.GetSelectedObjects():
            for y in numItemRows:
                if (x.itemID == quickbarList[y].itemID):
                    quickbarList[y] = 'deleted'
                    self.onRemoveWidget(x.widgetKey)

            for z in quickbarList[:]:
                if z == 'deleted':
                    quickbarList.remove(z)

        self.quickbarListCtrl.SetObjects(quickbarList)

    def onProcess(self, event):
        # TODO: Add a query limit of some form, so we are nice to the Eve-Central servers.
        if quickbarList != []:
            timingMsg = 'Using Local Cache'

            # Build a list of item ids to send to Eve-Central.
            idList = []
            for item in quickbarList:
                idList.append(item.itemID)
            # We'll tag on the mineral query with the item ids to save traffic.
            for mineral in config.mineralIDs:
                idList.append(mineral)

            #print(idList)
            #idList = [4473, 16437...]

            # This is for time stamping our out bound queries so we don't request data we already have that is recent.
            queryTime = datetime.datetime.utcnow().replace(microsecond=0)

            # Start the clock for the fetch from Eve-Central.
            t = time.clock()

            self.statusbar.SetStatusText('Nett - Fetching Data from Eve-Central.com...')

            dodixieBuy, dodixieSell, jitaBuy, jitaSell, hekBuy, hekSell, amarrBuy, amarrSell = fetchItems(idList)

            fetchTime = ((time.clock() - t) * 1000)  # Timing messages for info and debug.

            self.statusbar.SetStatusText('Nett - Calculating Reprocessed Values...')

            # Restart the clock for processing data.
            t = time.clock()

            for mineral in config.mineralIDs:
                materialsList.append(Material(int(mineral), config.mineralIDs[mineral],
                                              amarrBuy[mineral], dodixieBuy[mineral], hekBuy[mineral], jitaBuy[mineral],
                                              amarrSell[mineral], dodixieSell[mineral], hekSell[mineral], jitaSell[mineral],
                                              queryTime))

            materialRows = []
            for mineral in materialsList:
                materialRows.append(MaterialRow(mineral.materialName, 'Amarr', mineral.amarrBuy, mineral.amarrSell))
                materialRows.append(MaterialRow(mineral.materialName, 'Dodixie', mineral.dodixieBuy, mineral.dodixieSell))
                materialRows.append(MaterialRow(mineral.materialName, 'Hek', mineral.hekBuy, mineral.hekSell))
                materialRows.append(MaterialRow(mineral.materialName, 'Jita', mineral.jitaBuy, mineral.jitaSell))

            self.materialsListCtrl.SetObjects(materialRows)

            for item in quickbarList:
                output = reprocess(item.itemID)
                #print(output)

                reproDodixieBuy = 0  # Fullfilling Buy orders
                reproDodixieSell = 0  # Placing Sell orders
                reproJitaBuy = 0  # Fullfilling Buy orders
                reproJitaSell = 0  # Placing Sell orders
                reproAmarrBuy = 0  # Fullfilling Buy orders
                reproAmarrSell = 0  # Placing Sell orders
                reproHekBuy = 0  # Fullfilling Buy orders
                reproHekSell = 0  # Placing Sell orders

                # Generate reprocessed values from raw material prices. (Currently not stored)
                for key in output:
                    if key in config.mineralIDs:
                        reproDodixieBuy = reproDodixieBuy + (int(output[key]) * dodixieBuy[key])
                        reproDodixieSell = reproDodixieSell + (int(output[key]) * dodixieSell[key])
                        reproJitaBuy = reproJitaBuy + (int(output[key]) * jitaBuy[key])
                        reproJitaSell = reproJitaSell + (int(output[key]) * jitaSell[key])
                        reproAmarrBuy = reproAmarrBuy + (int(output[key]) * amarrBuy[key])
                        reproAmarrSell = reproAmarrSell + (int(output[key]) * amarrSell[key])
                        reproHekBuy = reproHekBuy + (int(output[key]) * hekBuy[key])
                        reproHekSell = reproHekSell + (int(output[key]) * hekSell[key])

                if wx.FindWindowByName("module_%s" % int(item.itemID)):
                    continue
                else:
                    self.numWidgets += 1
                    item.widgetKey = self.numWidgets
                    self.onAddWidget(int(item.itemID), item.itemName, item.widgetKey)

                # Send Values to the GUI elements. as we have added to the wx widgets
                # on the fly the easiest way to identify the widgets is by their unique
                # names assigned on creation.

                item.amarrItemBuy = amarrBuy[item.itemID]
                item.dodixieItemBuy = dodixieBuy[item.itemID]
                item.hekItemBuy = hekBuy[item.itemID]
                item.jitaItemBuy = jitaBuy[item.itemID]

                item.amarrItemSell = amarrSell[item.itemID]
                item.dodixieItemSell = dodixieSell[item.itemID]
                item.hekItemSell = hekSell[item.itemID]
                item.jitaItemSell = jitaSell[item.itemID]

                item.lastQuery = queryTime

                # Iterate over all of the widgets and their respective variables to fill in values.
                # '{:,.2f}'.format(value) Uses the Format Specification Mini-Language to produce more human friendly output.

                # Item Values
                widgetNames = ['amarrItemBuy', 'dodixieItemBuy', 'hekItemBuy', 'jitaItemBuy',
                               'amarrItemSell', 'dodixieItemSell', 'hekItemSell', 'jitaItemSell']
                for name in widgetNames:
                    widget = wx.FindWindowByName("%s_%s" % (name, int(item.itemID)))
                    widget.SetValue('{:,.2f}'.format(vars(item)[name]))

                # Reprocess Values
                widgetNames = ['reproAmarrBuy', 'reproDodixieBuy', 'reproHekBuy', 'reproJitaBuy',
                               'reproAmarrSell', 'reproDodixieSell', 'reproHekSell', 'reproJitaSell']
                for name in widgetNames:
                    widget = wx.FindWindowByName("%s_%s" % (name, int(item.itemID)))
                    widget.SetValue('{:,.2f}'.format(vars()[name]))

            processTime = ((time.clock() - t) * 1000)

            timingMsg = 'Fetch: %0.2f ms / Process: %0.2f ms' % (fetchTime, processTime)

            self.statusbar.SetStatusText('Nett - Idle - %s' % timingMsg)

    def OnAbout(self, e):
        description = """A tool designed for our corporate industrialists to
compare items at the main market hubs.

If you like my work please consider an ISK donation to Elusive One.

This application uses data provided by Eve-Central.com
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


class MyApp(wx.App):
    def OnInit(self):
        frame = MainWindow(None, -1, '')
        self.SetTopWindow(frame)
        frame.Center()
        frame.Show()
        return 1

# end of class MyApp

if __name__ == '__main__':
    app = MyApp(0)
    app.MainLoop()
