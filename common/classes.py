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
# Created: 05/05/14


# This is the class where we will store item data from the database and Eve-Central queries.
class Item(object):
    def __init__(self, itemID, itemName, marketGroupID,
                 amarrItemBuy, dodixieItemBuy, hekItemBuy, jitaItemBuy,
                 amarrItemSell, dodixieItemSell, hekItemSell, jitaItemSell,
                 reproAmarrBuy, reproDodixieBuy, reproHekBuy, reproJitaBuy,
                 reproAmarrSell, reproDodixieSell, reproHekSell, reproJitaSell,
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
        # Reprocessed Market Buy Order Prices
        self.reproAmarrBuy = reproAmarrBuy
        self.reproDodixieBuy = reproDodixieBuy
        self.reproHekBuy = reproHekBuy
        self.reproJitaBuy = reproJitaBuy
        # Reprocessed Market Sell Order Prices
        self.reproAmarrSell = reproAmarrSell
        self.reproDodixieSell = reproDodixieSell
        self.reproHekSell = reproHekSell
        self.reproJitaSell = reproJitaSell
        # Use a per item time stamp to handle query limiting to the API server.
        self.lastQuery = lastQuery
        # Due to limits on 32bit machines we can't use the item IDs as the basis for widget IDs
        self.widgetKey = widgetKey


# This is the class where we will store material data from the database and Eve-Central queries.
# I have decided to use the name Material instead of Minerals as the upcoming changes to reprocessing
# will affect the returned outcome to include recyclable parts.
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
