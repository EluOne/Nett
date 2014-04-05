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
import urllib2
import httplib
import traceback

import sqlite3 as lite
import xml.etree.ElementTree as etree

# System db id numbers
systemNames = {30002659: 'Dodixie', 30000142: 'Jita', 30002053: 'Hek', 30002187: 'Amarr'}  # 30002510: 'Rens'
# Mineral db id numbers
mineralIDs = {34: 'Tritanium', 35: 'Pyerite', 36: 'Mexallon', 37: 'Isogen',
              38: 'Nocxium', 39: 'Zydrine', 40: 'Megacyte', 11399: 'Morphite'}


class Salvage(object):
    def __init__(self, itemID, itemName, itemBuyValue, itemSellValue, reprocessBuyValue, reprocessSellValue, action):
        self.itemID = itemID
        self.itemName = itemName
        # '{:,.2f}'.format(value) Uses the Format Specification Mini-Language to produce more human friendly output.
        self.itemBuyValue = '{:,.2f}'.format(itemBuyValue)
        self.itemSellValue = '{:,.2f}'.format(itemSellValue)
        self.reprocessBuyValue = '{:,.2f}'.format(reprocessBuyValue)
        self.reprocessSellValue = '{:,.2f}'.format(reprocessSellValue)
        self.action = action


def onError(error):
    dlg = wx.MessageDialog(None, 'An error has occurred:\n' + error, '', wx.OK | wx.ICON_ERROR)
    dlg.ShowModal()  # Show it
    dlg.Destroy()  # finally destroy it when finished.
    print('An error has occurred:\n' + error, '\n')


def reprocess(itemID):  # Takes a list of IDs to query the local db or api server.
    minerals = {}
    # We'll use the local static DB for items as they don't change.
    if itemID != '':  # We have some ids we don't know.
        try:
            con = lite.connect('static.db')

            with con:
                cur = con.cursor()
                # TODO: Change this to use ids through out until data is presented to user.
                statement = "SELECT materialTypeID, quantity FROM invTypeMaterials WHERE typeID = " + str(itemID)
                cur.execute(statement)

                rows = cur.fetchall()

                # Use the item strings returned to populate the typeNames dictionary.
                for row in rows:
                    minerals.update({int(row[0]): int(row[1])})

        except lite.Error as err:
            error = ('SQL Lite Error: ' + str(err.args[0]) + str(err.args[1:]))  # Error String
            onError(error)
        finally:
            if con:
                con.close()
    return minerals


def fetchMinerals():
    # Set the market prices from Eve Central will look like:
    # dodixieMineralBuy = {34: 4.65, 35: 11.14, 36: 43.82, 37: 120.03, 38: 706.93, 39: 727.19, 40: 1592.10}
    dodixieMineralBuy = {}
    dodixieMineralSell = {}
    jitaMineralBuy = {}
    jitaMineralSell = {}
    hekMineralBuy = {}
    hekMineralSell = {}
    amarrMineralBuy = {}
    amarrMineralSell = {}

    for system in systemNames:
        # All base minerals from each system url:
        # http://api.eve-central.com/api/marketstat?typeid=34&typeid=35&typeid=36&typeid=37&typeid=38&typeid=39&typeid=40&usesystem=30002659
        apiURL = 'http://api.eve-central.com/api/marketstat?typeid=34&typeid=35&typeid=36&typeid=37&typeid=38&typeid=39&typeid=40&usesystem=%s' % (system)

        try:  # Try to connect to the API server
            target = urllib2.urlopen(apiURL)  # download the file
            downloadedData = target.read()  # convert to string
            target.close()  # close file because we don't need it anymore

            tree = etree.fromstring(downloadedData)

            types = tree.findall('.//type')

            for child in types:
                ids = child.attrib
                buy = child.find('buy')
                sell = child.find('sell')
                if int(ids['id']) in mineralIDs:
                    #print('%s (%s): Buy: %s / Sell: %s' % (mineralIDs[int(ids['id'])], int(ids['id']), buy.find('max').text, sell.find('min').text))
                    if system == 30002659:  # Dodi
                        dodixieMineralBuy[int(ids['id'])] = float(buy.find('max').text)
                        dodixieMineralSell[int(ids['id'])] = float(sell.find('min').text)
                    elif system == 30000142:  # Jita
                        jitaMineralBuy[int(ids['id'])] = float(buy.find('max').text)
                        jitaMineralSell[int(ids['id'])] = float(sell.find('min').text)
                    elif system == 30002053:  # Hek
                        hekMineralBuy[int(ids['id'])] = float(buy.find('max').text)
                        hekMineralSell[int(ids['id'])] = float(sell.find('min').text)
                    elif system == 30002187:  # Amarr
                        amarrMineralBuy[int(ids['id'])] = float(buy.find('max').text)
                        amarrMineralSell[int(ids['id'])] = float(sell.find('min').text)
        except urllib2.HTTPError as err:
            error = ('HTTP Error: %s %s\n' % (str(err.code), str(err.reason)))  # Error String
            onError(error)
        except urllib2.URLError as err:
            error = ('Error Connecting to Tranquility: ' + str(err.reason))  # Error String
            onError(error)
        except httplib.HTTPException as err:
            error = ('HTTP Exception')  # Error String
            onError(error)
        except Exception:
            error = ('Generic Exception: ' + traceback.format_exc())  # Error String
            onError(error)

    return dodixieMineralBuy, dodixieMineralSell, jitaMineralBuy, jitaMineralSell, hekMineralBuy, hekMineralSell, amarrMineralBuy, amarrMineralSell


def fetchItems(idList):
    # Set the market prices from Eve Central will look like:
    # dodixieItemBuy = {3616: 26966195.29, 4473: 11158.6}
    dodixieItemBuy = {}
    dodixieItemSell = {}
    jitaItemBuy = {}
    jitaItemSell = {}
    hekItemBuy = {}
    hekItemSell = {}
    amarrItemBuy = {}
    amarrItemSell = {}

    if idList != []:
        idString = ("&typeid=".join(map(str, idList[:])))
        for system in systemNames:
            # Item prices by system url:
            # http://api.eve-central.com/api/marketstat?typeid=16437&typeid=4473&usesystem=30002659
            apiURL = 'http://api.eve-central.com/api/marketstat?typeid=16437&typeid=%s&usesystem=%s' % (idString, system)
            print(apiURL)

            try:  # Try to connect to the API server
                target = urllib2.urlopen(apiURL)  # download the file
                downloadedData = target.read()  # convert to string
                target.close()  # close file because we don't need it anymore

                tree = etree.fromstring(downloadedData)

                #print("Item Prices from %s" % systemNames[system])

                types = tree.findall('.//type')

                for child in types:
                    ids = child.attrib
                    buy = child.find('buy')
                    sell = child.find('sell')
                    if int(ids['id']) in idList:
                        #print('%s (%s): Buy: %s / Sell: %s' % (typeNames[int(ids['id'])], int(ids['id']), buy.find('max').text, sell.find('min').text))
                        if system == 30002659:  # Dodi
                            dodixieItemBuy[int(ids['id'])] = float(buy.find('max').text)
                            dodixieItemSell[int(ids['id'])] = float(sell.find('min').text)
                        elif system == 30000142:  # Jita
                            jitaItemBuy[int(ids['id'])] = float(buy.find('max').text)
                            jitaItemSell[int(ids['id'])] = float(sell.find('min').text)
                        elif system == 30002053:  # Hek
                            hekItemBuy[int(ids['id'])] = float(buy.find('max').text)
                            hekItemSell[int(ids['id'])] = float(sell.find('min').text)
                        elif system == 30002187:  # Amarr
                            amarrItemBuy[int(ids['id'])] = float(buy.find('max').text)
                            amarrItemSell[int(ids['id'])] = float(sell.find('min').text)
            except urllib2.HTTPError as err:
                error = ('HTTP Error: %s %s' % (str(err.code), str(err.reason)))  # Error String
                onError(error)
            except urllib2.URLError as err:
                error = ('Error Connecting to Tranquility: ' + str(err.reason))  # Error String
                onError(error)
            except httplib.HTTPException as err:
                error = ('HTTP Exception')  # Error String
                onError(error)
            except Exception:
                error = ('Generic Exception: ' + traceback.format_exc())  # Error String
                onError(error)

    return dodixieItemBuy, dodixieItemSell, jitaItemBuy, jitaItemSell, hekItemBuy, hekItemSell, amarrItemBuy, amarrItemSell
