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
import traceback
import requests

import sqlite3 as lite
import xml.etree.ElementTree as etree

import config


def onError(error):
    dlg = wx.MessageDialog(None, 'An error has occurred:\n' + error, '', wx.OK | wx.ICON_ERROR)
    dlg.ShowModal()  # Show it
    dlg.Destroy()  # finally destroy it when finished.
    #print('An error has occurred:\n' + error, '\n')


def reprocess(itemID):  # Takes a list of IDs to query the local db or api server.
    minerals = {}
    # We'll use the local static DB for items as they don't change.
    if itemID != '':  # We have some ids we don't know.
        try:
            con = lite.connect('static.db')

            with con:
                cur = con.cursor()
                statement = "SELECT materialTypeID, quantity FROM invTypeMaterials WHERE typeID = " + str(itemID)
                cur.execute(statement)

                rows = cur.fetchall()

                # We are using ids as keys as this can be matched against the mineralID dictionary.
                for row in rows:
                    minerals.update({int(row[0]): int(row[1])})

        except lite.Error as err:
            error = ('SQL Lite Error: ' + str(err.args[0]) + str(err.args[1:]))  # Error String
            onError(error)
        finally:
            if con:
                con.close()
    return minerals


def fetchItems(typeIDs):
    # Set the market prices from Eve Central will look like:
    # dodixieItemBuy = {3616: 26966195.29, 4473: 11158.6}
    dodixieBuy = {}
    dodixieSell = {}
    jitaBuy = {}
    jitaSell = {}
    hekBuy = {}
    hekSell = {}
    amarrBuy = {}
    amarrSell = {}

    if typeIDs != []:
        # Calculate the number of ids we have. We'll use a maximum of 100 IDs per query.
        # So we'll need to split this into multiple queries.
        numIDs = len(typeIDs)
        idList = []

        if numIDs > 100:
            startID = 0
            endID = 100
            while startID < numIDs:
                idList.append("&typeid=".join(map(str, typeIDs[startID:endID])))
                startID = startID + 100
                if ((numIDs - endID)) > 100:
                    endID = endID + 100
                else:
                    endID = numIDs

        else:
            idList.append("&typeid=".join(map(str, typeIDs[0:numIDs])))

        numIdLists = list(range(len(idList)))
        for x in numIdLists:  # Iterate over all of the id lists generated above.
            for system in config.systemNames:
                # Item prices by system url:
                baseUrl = 'http://api.eve-central.com/api/marketstat?typeid=%s&usesystem=%s'
                apiURL = baseUrl % (idList[x], system)
                #print(apiURL)

                try:  # Try to connect to the API server
                    downloadedData = requests.get(apiURL, headers=config.headers)

                    tree = etree.fromstring(downloadedData.text)
                    types = tree.findall('.//type')

                    for child in types:
                        ids = child.attrib
                        buy = child.find('buy')
                        sell = child.find('sell')
                        if system == 30002659:  # Dodi
                            dodixieBuy[int(ids['id'])] = float(buy.find('max').text)
                            dodixieSell[int(ids['id'])] = float(sell.find('min').text)
                        elif system == 30000142:  # Jita
                            jitaBuy[int(ids['id'])] = float(buy.find('max').text)
                            jitaSell[int(ids['id'])] = float(sell.find('min').text)
                        elif system == 30002053:  # Hek
                            hekBuy[int(ids['id'])] = float(buy.find('max').text)
                            hekSell[int(ids['id'])] = float(sell.find('min').text)
                        elif system == 30002187:  # Amarr
                            amarrBuy[int(ids['id'])] = float(buy.find('max').text)
                            amarrSell[int(ids['id'])] = float(sell.find('min').text)

                except requests.exceptions.HTTPError as err:  # An HTTP error occurred.
                    error = ('HTTP Error: %s %s\n' % (str(err.code), str(err.reason)))  # Error String
                    onError(error)
                except requests.exceptions.ConnectionError as err:  # A Connection error occurred.
                    error = ('Error Connecting to Eve-Central: ' + str(err.reason))  # Error String
                    onError(error)
                except requests.exceptions.RequestException as err:  # There was an ambiguous exception that occurred while handling your request.
                    error = ('HTTP Exception')  # Error String
                    onError(error)
                except Exception:
                    error = ('Generic Exception: ' + traceback.format_exc())  # Error String
                    onError(error)

    return dodixieBuy, dodixieSell, jitaBuy, jitaSell, hekBuy, hekSell, amarrBuy, amarrSell
