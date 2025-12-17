import requests, re, ctypes, os, json, random, time
import cloudscraper
from colorama import init, Fore, Style
from threading import Thread, Lock
from itertools import cycle, combinations
from datetime import datetime, timedelta
from collections import Counter
from time import sleep
from random import shuffle
lock = Lock()
init()
scraper = cloudscraper.create_scraper(browser={'browser': 'firefox','platform': 'windows','mobile': False})

config = json.load(open("config.json", "r"))
myValues = json.load(open("../myValues.json", "r"))
theirValues = json.load(open("../theirValues.json", "r"))
overallConfig = json.load(open("../overallConfig.json", "r"))
customValues = json.load(open("../customValues.json", "r"))
blacklists = json.load(open("../blacklistedUsers.json", "r"))
cookieList = open('../cookies.txt','r').read().splitlines()
theirValuesMain = {}
myValuesMain = {}

for item in myValues: myValuesMain[item] = int(myValues[item].split('|')[0])
for item in theirValues: theirValuesMain[item] = int(theirValues[item].split('|')[0])

proxyList = [{'https':'http://'+proxy} for proxy in open('../proxies.txt','r').read().splitlines()]
shuffle(proxyList)

playerBlacklist = blacklists['users']
customValuesMe = customValues['values']['me']
customValuesThem = customValues['values']['them']
customValuesExtra = customValues['values']['extra']
queueLimit = config['config']['queueLimit']

def splitKey(currentItems):
    number = currentItems.split(':')[1]
    return int(number)

Checked = []

class User:

    def __init__(self, **kwargs) -> None:
        [setattr(self, item, val) for item, val in kwargs.items()]
        if config['config']['theirCustomizations']['receiveOnlyValue']: self.noRap = True
        else: self.noRap = False
        self.tradesSent = 0
        self.tradesFailed = 0
        self.passingQueue = 0
        self.Owners = []
        self.myCombination = []
        self.tradesToSend = []
        self.myCurrentUaids = []
        self.usersToWork = []
        self.webhooksToSend = []
        self.overall()

    def title(self):
        while True: ctypes.windll.kernel32.SetConsoleTitleW(f'{config["userId"]} / Sent Trades: {self.tradesSent} / Failed Trades: {self.tradesFailed} / Queue: {len(self.tradesToSend)} / Available Users: {len(self.usersToWork)} / Owners: {len(self.Owners)}'); sleep(5)

    def debugger(self):
        global customValues, customValuesMe, customValuesThem, config
        self.debugAll = False
        while True:
            debugInput = input('')
            if debugInput == 'debug': self.debugAll = True
            if debugInput == 'undebug': self.debugAll = False
            if debugInput == 'stop': self.stopQueue = True
            if debugInput == 'unstop': self.stopQueue = False
            if debugInput == 'refresh':
                customValues = json.load(open("../customValues.json", "r"))
                customValuesMe = customValues['values']['me']
                customValuesThem = customValues['values']['them']
                config = json.load(open("config.json", "r"))

    def queueHandler(self):
        totalRemoved = 0
        if len(self.tradesToSend) > 0:
            with lock: print(f'{Fore.LIGHTBLACK_EX}({Fore.MAGENTA}queue{Fore.LIGHTBLACK_EX}) trade queue is being filtered')
            for currentTrade in self.tradesToSend:
                theirUserId, theirUaids, myUaids, myValue, theirValue = currentTrade[0], currentTrade[1], currentTrade[2], currentTrade[3], currentTrade[4]
                for uaid in myUaids:
                    if uaid not in self.myCurrentUaids:
                        self.tradesToSend.remove(currentTrade)
                        with lock: print(f'{Fore.LIGHTBLACK_EX}({Fore.MAGENTA}1{Fore.LIGHTBLACK_EX}) trade was removed from queue')
                        totalRemoved += 1
        with lock: print(f'{Fore.LIGHTBLACK_EX}({Fore.MAGENTA}{totalRemoved}{Fore.LIGHTBLACK_EX}) total trades were removed from queue')
        self.passingQueue = 0
        self.stopQueue = False

    def roliUpdater(self):
        global theirValues, myValues, Checked, myValuesMain, theirValuesMain
        currentAmount = 0
        while True:
            try:
                total = json.loads(
                    re.findall('item_details = (.*?);', requests.get('https://www.rolimons.com/deals', timeout=2).text)[0]
                )
                self.sellingUnder = [limited for limited in total if total[limited][5] == None if total[limited][1] < total[limited][2]]
                self.onlyValue = [f'{limited}' for limited in total if total[limited][5] != None]
                self.onlyRap = [f'{limited}' for limited in total if total[limited][5] == None]
                self.onlyRares = [f'limited' for limited in total if total[limited][8] == 1]
                myValues = json.load(open("../myValues.json", "r"))
                theirValues = json.load(open("../theirValues.json", "r"))
                for item in myValues: myValuesMain[item] = myValues[item].split('|')[0]
                for item in theirValues: theirValuesMain[item] = theirValues[item].split('|')[0]
                currentAmount += 1
                if currentAmount % 6 == 0: Checked.clear()
                sleep(600)
            except:
                sleep(10)
                continue

    def checkDontHoard(self, my_items):
        amount = Counter(my_items)
        for c in amount:
            if amount[c] >= 1 and c in overallConfig['do_not_hoard']:
                config['theirLists']['blacklistedLimiteds'].append(c)

    def getMyOverallValue(self, response):
        self.myOverallValue = 0
        currentItems = []
        for x in response:
            assetId = str(x['assetId'])
            if assetId in myValues:
                if assetId in customValuesMe:
                    self.myOverallValue += customValuesMe[assetId][0]
                self.myOverallValue += int(myValues[assetId].split('|')[0])
                currentItems.append(f'{assetId}:{int(myValues[assetId].split("|")[0])}')
        return currentItems

    def getHighestValueCombination(self, currentItems):
        self.highestValueCombination = 0
        currentItems.sort(key=splitKey, reverse=True)
        for i in range(config['config']['myCustomizations']['maximumItems']):
            try:
                if currentItems[i].split(':')[0] in customValuesMe:
                    self.highestValueCombination += customValuesMe[currentItems[i].split(':')[0]][0]
                self.highestValueCombination += int(currentItems[i].split(':')[1])
            except: pass

    def lowestIncludeValue(self):
        if config['myLists']['includeLimiteds'] != []:
            self.lowestIncludeMe = 0
            valuesList = []
            for item in config['myLists']['includeLimiteds']:
                itemValue = int(myValues[str(item)].split('|')[0])
                if str(item) in customValuesMe:
                    itemValue += int(customValuesMe[str(item)][0])
                valuesList.append(itemValue)
            valuesList.sort()
            self.lowestIncludeMe = valuesList[0]

    def getMyItems(self, response):
        foundAssets = [f'{info["assetId"]}:{info["userAssetId"]}' for info in response if not info['assetId'] in config['myLists']['keepLimiteds'] if f'{info["assetId"]}' in myValues]
        foundAssetsRap = [info for info in foundAssets if info.split(':')[0] in self.onlyRap]
        foundAssetsValue = [info for info in foundAssets if info.split(':')[0] in self.onlyValue]
        return foundAssetsRap, foundAssetsValue, foundAssets

    def grabCombinations(self, foundAssets, foundAssetsValue, foundAssetsRap):

        totalCombination = [p for i in range (4) for p in combinations(foundAssets, r=i+1) if len(p) <= config['config']['myCustomizations']['maximumItems'] and len(p) >= config['config']['myCustomizations']['minimumItems']]
        totalCombinationRap = [p for i in range (4) for p in combinations(foundAssetsRap, r=i+1) if len(p) <= config['config']['myCustomizations']['maximumItems'] and len(p) >= config['config']['myCustomizations']['minimumItems']]
        totalCombinationValue = [p for i in range (4) for p in combinations(foundAssetsValue, r=i+1) if len(p) <= config['config']['myCustomizations']['maximumItems'] and len(p) >= config['config']['myCustomizations']['minimumItems']]

        if config['myLists']['includeLimiteds'] != []: self.myCombination = [p for i in range(4) for p in combinations(foundAssets, r=i+1) if len(set(config['myLists']['includeLimiteds'])&{int(x.split(':')[0]) for x in p}) != 0 if len(p) <= config['config']['myCustomizations']['maximumItems'] and len(p) >= config['config']['myCustomizations']['minimumItems']]
        elif config['config']['myCustomizations']['giveOnlyValue']: self.myCombination = totalCombinationValue
        elif config['config']['myCustomizations']['giveOnlyRap']: self.myCombination = totalCombinationRap
        elif config['config']['myCustomizations']['tryValueFirst']: self.myCombination = totalCombinationValue + totalCombination
        else: self.myCombination = totalCombination

        realCombinations = []

        for mCombination in self.myCombination:
            myValue = myBiggestVal = myValueAdd = totalOpMe = opLimsMe = highestAddMe = myValueAddExtra = 0
            myTrade, myBiggestItem, allExtra, haveRareMe = 'Rap', '', True, False

            for assetId in mCombination:
                currentItem = assetId.split(':')[0]
                itemValue = int(myValuesMain[currentItem])
                myValue += itemValue
                if itemValue > myBiggestVal:
                    myBiggestVal, myBiggestItem = itemValue, currentItem
                if currentItem in self.onlyValue or int(currentItem) in overallConfig['value_instead']: myTrade = 'Value'
                if currentItem in customValuesMe:
                    allExtra = False
                    cValue = customValuesMe[currentItem][0]
                    myValueAdd += cValue
                    opLimsMe += 1
                    if cValue > highestAddMe: highestAddMe = cValue
                if currentItem in customValuesExtra:
                    cValue = customValuesExtra[currentItem][0]
                    myValueAddExtra += cValue
                    opLimsMe += 1
                    if cValue > highestAddMe: highestAddMe = cValue
                if currentItem in self.onlyRares: haveRareMe = True

            realCombinations.append([mCombination, myValue, myBiggestVal, myValueAdd, totalOpMe, opLimsMe, highestAddMe, myValueAddExtra, myTrade, myBiggestItem, allExtra, haveRareMe])

        self.myCombination = realCombinations


    def myItems(self):
        self.stopQueue = True
        while True:
            try:
                r = requests.get(f'https://inventory.roblox.com/v1/users/{config["userId"]}/assets/collectibles?sortOrder=Asc&limit=100&cursor=', cookies={'.ROBLOSECURITY': config['cookie']}, timeout=2, proxies=random.choice(proxyList)).json()
                if 'data' in r:
                    my_items = [x['assetId'] for x in r['data']]

                    self.checkDontHoard(my_items)
                    currentItems = self.getMyOverallValue(r['data'])
                    self.getHighestValueCombination(currentItems)
                    self.lowestIncludeValue()
                    foundAssetsRap, foundAssetsValue, foundAssets = self.getMyItems(r['data'])
                    self.myCurrentUaids = [x["userAssetId"] for x in r['data']]
                    self.grabCombinations(foundAssets, foundAssetsValue, foundAssetsRap)

                    with lock: print(f'{Fore.LIGHTBLACK_EX}({Fore.YELLOW}{len(self.myCombination)}{Fore.LIGHTBLACK_EX}) combinations were generated')
                    self.queueHandler()
                    if len(self.myCombination) == 0: continue
                    return None
                else:
                    sleep(2)
                    continue
            except Exception as err:
                print(err)
                continue

    def rolimons_scraping(self, sendingNow, keepTrack):
        global Checked
        try:
            r = requests.get('https://www.rolimons.com/tradeadsapi/getrecentads').json()
            for x in r['trade_ads']:
                if x[2] not in keepTrack and x[2] not in playerBlacklist:
                    if x[2] not in Checked: Checked.append(x[2]); keepTrack.append(x[2]); sendingNow.append(x[2])
        except: pass

    def rbxflip_scraping(self, sendingNow, keepTrack):
        global Checked
        try:
            r = scraper.get('https://legacy.rbxflip-apis.com/games/versus/CF').json()
            for x in r['data']['games']:
                if x['status'] == 'Completed':
                    host = int(x['host']['id'])
                    player = int(x['player']['id'])
                    if player not in keepTrack and player not in playerBlacklist:
                        if player not in Checked: Checked.append(player); keepTrack.append(player); sendingNow.append(player)
                    if host not in keepTrack and host not in playerBlacklist:
                        if host not in Checked: Checked.append(host); keepTrack.append(host); sendingNow.append(host)
        except: pass

    def bloxland_scraping(self, sendingNow, keepTrack):
        global Checked
        try:
            r = scraper.get('https://rest-bf.blox.land/games/crash').text
            userNames = re.findall('playerID":(.*?),"', r)
            userNames = [int(user) for user in userNames]
            for user in userNames:
                if user not in keepTrack and user not in playerBlacklist:
                    if user not in Checked: Checked.append(user); keepTrack.append(user); sendingNow.append(user)
        except: pass

    def otherScraping(self):
        keepTrack = []
        while True:
            sendingNow = []
            self.rolimons_scraping(sendingNow, keepTrack)
            self.rbxflip_scraping(sendingNow, keepTrack)
            self.bloxland_scraping(sendingNow, keepTrack)
            self.Owners = sendingNow + self.Owners
            sleep(60)

    def scrapeOwners(self, assetIds):
        global Checked
        for assetid in assetIds:
            nextCursor = ''
            while nextCursor != None:
                try:
                    r = requests.get(f'https://inventory.roblox.com/v2/assets/{assetid}/owners?sortOrder=Asc&limit=100&cursor={nextCursor}', cookies={'.ROBLOSECURITY': random.choice(cookieList)}, timeout=2).json()
                    if 'data' in r:
                        nextCursor = r['nextPageCursor']
                        for i in r['data']:
                            if i['owner'] != None and i['owner']['id'] not in playerBlacklist:
                                if '2022' in i['updated'] or '2021' in i['updated']:
                                    if i['owner']['id'] not in Checked:
                                        while True:
                                            if len(self.Owners) <= 1000 and len(self.usersToWork) <= 1000:
                                                Checked.append(i['owner']['id'])
                                                if i['owner']['id'] <= 3500000000: self.Owners.append(i['owner']['id'])
                                                else: self.Owners.insert(0, i['owner']['id'])
                                                break
                                            else:
                                                sleep(5)
                    else:
                        continue
                except Exception as err:
                    continue

    def checkOnline(self, number):
        global Checked
        while True:
            try:
                userId = self.Owners[number]
                self.Owners.remove(userId)
                while True:
                    try:
                        r = requests.get(f'https://api.roblox.com/users/{userId}/onlinestatus', timeout=2)
                        if r.status_code == 200:
                            onlineDate = str(datetime.now() - timedelta(hours=6)).split()[0]
                            if r.json()['IsOnline'] == True:
                                self.checkIfTrade(userId, False)
                            elif onlineDate in r.json()['LastOnline']:
                                self.checkIfTrade(userId, True)
                            break
                        else:
                            with lock: print('error')
                            break
                    except Exception as err:
                        print(err)
                        continue
            except:
                sleep(0.25)
                continue

    #def checkIfTrade(self, userId, option):
    #    global cantTrade, tradesSent, premium, sent, Checked
    #    while True:
    #        try:
    #            r = requests.get(f'https://www.roblox.com/users/{userId}/profile', cookies={'.ROBLOSECURITY': config['cookie']}, timeout=2).text
    #            if 'onClickTradeLink' in r and 'icon-premium' in r:
    #                if option == True: self.usersToWork.insert(0, userId)
    #                else: self.usersToWork.append(userId)
    #                break
    #            elif 'custom error module' in r:
    #                with lock: print(f'{Fore.LIGHTBLACK_EX}({Fore.RED}error{Fore.LIGHTBLACK_EX}) custom error module')
    #                sleep(1)
    #                continue
    #            else: break
    #        except Exception as err:
    #            continue

    def checkIfTrade(self, userId, option):
        global cantTrade, tradesSent, premium, sent, Checked
        while True:
            try:
                r = requests.get(f'https://www.roblox.com/users/{userId}/trade', cookies={'.ROBLOSECURITY': config['cookie']}, timeout=2)
                if r.status_code == 200:
                    if option == True: self.usersToWork.insert(0, userId)
                    else: self.usersToWork.append(userId)
                    break
                else: break
            except Exception as err:
                continue

    def theirBiggestValCombo(self, justAssets):
        valuesList = []
        for item in justAssets:
            itemValue = int(theirValues[str(item)].split('|')[0])
            if str(item) in customValuesThem:
                itemValue += int(customValuesThem[str(item)][0])
            valuesList.append(itemValue)
        valuesList.sort(reverse=True)
        biggestTotal = 0
        if len(valuesList) >= 4:
            for i in range(4):
                biggestTotal += valuesList[i]
        else:
            for i in valuesList:
                biggestTotal += i
        if biggestTotal < self.lowestIncludeMe: return True
        else: return False

    def grabRealAssets(self, justAssets, currentAssets):
        counts = Counter(justAssets)
        actualAssets = []
        for item in counts:
            if str(currentAssets).count(str(item)) > 4:
                amount = 0
                for info in currentAssets:
                    if item in info:
                        assetId, userAssetId = info.split(':',2)
                        actualAssets.append({'assetId': assetId, 'userAssetId': userAssetId})
                        amount += 1
                        if amount == 4: break
            else:
                for info in currentAssets:
                    if item in info:
                        assetId, userAssetId = info.split(':',2)
                        actualAssets.append({'assetId': assetId, 'userAssetId': userAssetId})
        return actualAssets

    def getTheirAssets(self, actualAssets):
        foundAssetsRap = [f'{x["assetId"]}:{x["userAssetId"]}' for x in actualAssets if str(x['assetId']) in theirValues if str(theirValues[str(x['assetId'])]).split('|')[3] != '1' if not int(x['assetId']) in config['theirLists']['blacklistedLimiteds'] if not str(x['assetId']) in self.sellingUnder if int(str(theirValues[str(x['assetId'])]).split('|')[0]) < self.myOverallValue*1.2 if str(x['assetId']) in self.onlyRap]
        foundAssetsValue = [f'{x["assetId"]}:{x["userAssetId"]}' for x in actualAssets if str(x['assetId']) in theirValues if str(theirValues[str(x['assetId'])]).split('|')[3] != '1' if not int(x['assetId']) in config['theirLists']['blacklistedLimiteds'] if not str(x['assetId']) in self.sellingUnder if int(str(theirValues[str(x['assetId'])]).split('|')[0]) < self.myOverallValue*1.2 if str(x['assetId']) in self.onlyValue]
        foundAssets = [f'{x["assetId"]}:{x["userAssetId"]}' for x in actualAssets if str(x['assetId']) in theirValues if str(theirValues[str(x['assetId'])]).split('|')[3] != '1' if not int(x['assetId']) in config['theirLists']['blacklistedLimiteds'] if not str(x['assetId']) in self.sellingUnder if int(str(theirValues[str(x['assetId'])]).split('|')[0]) < self.myOverallValue*1.2]
        return foundAssetsRap, foundAssetsValue, foundAssets

    def theirItems(self, userId):
        for i in range(5):
            try:
                r = requests.get(f'https://inventory.roblox.com/v1/users/{userId}/assets/collectibles?sortOrder=Asc&limit=100&cursor=', cookies={'.ROBLOSECURITY': config['cookie']}, timeout=2, proxies=random.choice(proxyList)).json()
                if 'data' in r:

                    currentAssets = [f'{x["assetId"]}:{x["userAssetId"]}' for x in r['data']]
                    justAssets = [f'{x["assetId"]}' for x in r['data']]
                    if config['myLists']['includeLimiteds']:
                        result = self.theirBiggestValCombo(justAssets)
                        if result == True: return None
                    actualAssets = self.grabRealAssets(justAssets, currentAssets)
                    foundAssetsRap, foundAssetsValue, foundAssets = self.getTheirAssets(actualAssets)

                    if config['theirLists']['includeLimiteds'] != []:
                        return [p for i in range (4) for p in combinations(foundAssets, r=i+1) if len(set(config['theirLists']['includeLimiteds'])&set([int(x.split(':')[0]) for x in p])) > 0 if len(p) <= config['config']['theirCustomizations']['maximumItems'] and len(p) >= config['config']['theirCustomizations']['minimumItems']]
                    else:
                        if config['config']['theirCustomizations']['receiveOnlyRap'] == True:
                            return [p for i in range (4) for p in combinations(foundAssetsRap, r=i+1) if len(p) <= config['config']['theirCustomizations']['maximumItems'] and len(p) >= config['config']['theirCustomizations']['minimumItems']]
                        elif config['config']['theirCustomizations']['receiveOnlyValue'] == True:
                            return [p for i in range (4) for p in combinations(foundAssetsValue, r=i+1) if len(p) <= config['config']['theirCustomizations']['maximumItems'] and len(p) >= config['config']['theirCustomizations']['minimumItems']]
                        else:
                            return [p for i in range (4) for p in combinations(foundAssets, r=i+1) if len(p) <= config['config']['theirCustomizations']['maximumItems'] and len(p) >= config['config']['theirCustomizations']['minimumItems']]
            except Exception as err:
                continue

    def findTrade(self):
        while True:
            for userId in self.usersToWork:
                try:
                    self.usersToWork.remove(userId)
                    start = time.time()
                    theirCombination = self.theirItems(userId)
                    #with lock: print(f'{Style.BRIGHT}{Fore.LIGHTBLACK_EX}({Fore.CYAN}{userId}{Fore.LIGHTBLACK_EX}) generated {Fore.CYAN}{len(theirCombination)}{Fore.LIGHTBLACK_EX} combinations')

                    if theirCombination != None and len(theirCombination) != 0:
                        shuffle(theirCombination)
                        finish = False
                        try:
                            for tCombination in theirCombination:
                                theirValue = theirBiggestVal = theirValueAddOriginal = opLims = highestAdd = theirValueAddExtra = 0
                                theirTrade, theirBiggestItem, haveRare, allExtraThem = 'Rap', '', False, True
                                itemList = [assetId.split(':')[0] for assetId in tCombination]
                                itemListValue = [assetId for assetId in itemList if assetId in self.onlyValue]

                                if self.noRap == True:
                                    if len(set(self.onlyRap)&set(itemList)) == len(tCombination):
                                        continue

                                counts = Counter(itemList)
                                dontWant = False
                                [dontWant := True for count in counts if counts[count] >= 2]
                                if dontWant == True: continue

                                for assetId in tCombination:
                                    currentItem = assetId.split(':')[0]
                                    itemValue = int(theirValuesMain[currentItem])
                                    theirValue += itemValue
                                    if itemValue > theirBiggestVal:
                                        theirBiggestVal, theirBiggestItem = itemValue, currentItem
                                    if currentItem in customValuesThem:
                                        allExtraThem, cValue = False, customValuesThem[currentItem][0]
                                        theirValueAddOriginal += cValue
                                        opLims += 1
                                        if cValue > highestAdd: highestAdd = cValue
                                    if currentItem in self.onlyRares: haveRare = True
                                    if currentItem in customValuesExtra: theirValueAddExtra += customValuesExtra[currentItem][0]

                                if theirValue < config['config']['minimumTradeValue']:
                                    continue

                                if theirValue > 4000:
                                    if theirValue > self.highestValueCombination*1.2 or theirValue > self.myOverallValue*1.2:
                                        continue

                                if len(itemListValue) == len(tCombination):
                                    theirTrade = 'Value'
                                if len(itemListValue) != len(tCombination) and len(itemListValue) > 0:
                                    theirTrade = 'Mixed'

                                for x in self.myCombination:
                                    customMinimum, customMaximum = config['config']['minimum'], config['config']['maximum']
                                    theirValueAdd = theirValueAddOriginal
                                    totalOp = 0

                                    mCombination, myValue, myBiggestVal, myValueAdd, totalOpMe, opLimsMe, highestAddMe, myValueAddExtra, myTrade, myBiggestItem, allExtra, haveRareMe = x[0], x[1], x[2], x[3], x[4], x[5], x[6], x[7], x[8], x[9], x[10], x[11]

                                    if self.noRap == True:
                                        if 'myTrade' == 'Rap':
                                            continue

                                    if myBiggestItem in self.onlyRap and myTrade != 'Rap':
                                        continue

                                    if config['config']['onlyDowngrade'] == True:
                                        #if len(mCombination) >= len(tCombination): continue
                                        if theirBiggestVal >= myBiggestVal:
                                            continue
                                    if config['config']['onlyUpgrade'] == True:
                                        #if len(mCombination) <= len(tCombination): continue
                                        if haveRare == False:
                                            if theirBiggestVal <= myBiggestVal:
                                                continue

                                    if myValueAdd == 0 and theirValueAdd == 0:
                                        if myBiggestVal >= 30000 or theirBiggestVal >= 30000:

                                            valueRatio = theirBiggestVal/myBiggestVal

                                            if valueRatio >= 1:
                                                if valueRatio >= 1.5:
                                                    customMinimum = 0.98
                                                    customMaximum = 1.00
                                                elif valueRatio >= 1.2:
                                                    customMinimum = 0.99
                                                    customMaximum = 1.01
                                                elif valueRatio > 1:
                                                    customMinimum = 1.00
                                                    customMaximum = 1.02
                                                else:
                                                    customMinimum = 1.01
                                                    customMaximum = 1.03
                                            else:
                                                if myBiggestVal <= 50000:
                                                    if valueRatio <= 0.5:
                                                        customMinimum = 1.04
                                                        customMaximum = 1.07
                                                    elif valueRatio <= 0.8:
                                                        customMinimum = 1.03
                                                        customMaximum = 1.06
                                                    elif valueRatio < 1:
                                                        customMinimum = 1.02
                                                        customMaximum = 1.05

                                                elif myBiggestVal < 100000:
                                                    if valueRatio <= 0.5:
                                                        customMinimum = 1.03
                                                        customMaximum = 1.06
                                                    elif valueRatio <= 0.8:
                                                        customMinimum = 1.02
                                                        customMaximum = 1.05
                                                    elif valueRatio < 1:
                                                        customMinimum = 1.01
                                                        customMaximum = 1.04

                                                elif myBiggestVal < 150000:
                                                    if valueRatio <= 0.5:
                                                        customMinimum = 1.06
                                                        customMaximum = 1.09
                                                    elif valueRatio <= 0.8:
                                                        customMinimum = 1.05
                                                        customMaximum = 1.08
                                                    elif valueRatio < 1:
                                                        customMinimum = 1.04
                                                        customMaximum = 1.07

                                                elif myBiggestVal < 200000:
                                                    if valueRatio <= 0.5:
                                                        customMinimum = 1.09
                                                        customMaximum = 1.12
                                                    elif valueRatio <= 0.8:
                                                        customMinimum = 1.08
                                                        customMaximum = 1.11
                                                    elif valueRatio < 1:
                                                        customMinimum = 1.07
                                                        customMaximum = 1.10

                                                elif myBiggestVal < 300000:
                                                    if valueRatio <= 0.5:
                                                        customMinimum = 1.09
                                                        customMaximum = 1.12
                                                    elif valueRatio <= 0.8:
                                                        customMinimum = 1.08
                                                        customMaximum = 1.11
                                                    elif valueRatio < 1:
                                                        customMinimum = 1.07
                                                        customMaximum = 1.10

                                    #if allExtraThem == True or theirBiggestVal < 130000:
                                    #    myValueAdd += myValueAddExtra

                                    #if theirBiggestVal >= myBiggestVal*1.5 and theirBiggestVal >= 130000:
                                    #    myValueAdd = 0
                                    #elif theirBiggestItem in self.onlyRares:
                                    #    myValueAdd = 0

                                    #if allExtra == True:
                                    #    if myBiggestVal*2 <= theirBiggestVal: myValueAdd = 0
                                    #    elif allExtraThem == True:
                                    #        theirValueAdd += theirValueAddExtra*0.5

                                    #if theirValueAdd or myValueAdd > 0:

                                    #    customMinimum = 1.00
                                    #    customMaximum = 1.01

                                    #    if theirValueAdd and myValueAdd > 0:

                                    #        if myValueAdd > theirValueAdd:
                                    #            if theirBiggestVal <= myBiggestVal*0.5:
                                    #                totalOpMe = myValueAdd-theirValueAdd
                                    #            if theirBiggestVal <= myBiggestVal*0.75:
                                    #                totalOpMe = myValueAdd-(theirValueAdd*0.33)
                                    #            elif theirBiggestVal < myBiggestVal:
                                    #                totalOpMe = myValueAdd-(theirValueAdd*0.5)
                                    #            else:
                                    #                if theirBiggestVal >= myBiggestVal*1.5:
                                    #                    totalOpMe = myValueAdd-(theirValueAdd*0.8)
                                    #                elif theirBiggestVal >= myBiggestVal:
                                    #                    totalOpMe = myValueAdd-(theirValueAdd*0.6)

                                    #        elif theirValueAdd > myValueAdd:
                                    #            if opLims == 1:
                                    #                if theirBiggestVal >= 70000 or haveRare == True:
                                    #                    if theirBiggestVal >= myBiggestVal*1.5:
                                    #                        if highestAdd >= highestAddMe*1.5:
                                    #                            totalOp = (theirValueAdd-myValueAdd)
                                    #                        else:
                                    #                            totalOp = (theirValueAdd-myValueAdd)*0.75
                                    #                    elif theirBiggestVal >= myBiggestVal:
                                    #                        if highestAdd >= highestAddMe*1.5:
                                    #                            totalOp = (theirValueAdd-myValueAdd)*0.8
                                    #                        else:
                                    #                            totalOp = (theirValueAdd-myValueAdd)*0.66
                                    #                    else:
                                    #                        if highestAdd >= highestAddMe*1.5:
                                    #                            totalOp = (theirValueAdd-myValueAdd)*0.66
                                    #                        else:
                                    #                            totalOp = (theirValueAdd-myValueAdd)*0.5
                                    #                else:
                                    #                    customMinimum = 1.01
                                    #                    customMaximum = 1.03
                                    #            else:
                                    #                if highestAdd >= highestAddMe:
                                    #                    if theirBiggestVal >= myBiggestVal*1.5:
                                    #                        totalOp = (theirValueAdd-myValueAdd)*0.75
                                    #                    elif theirBiggestVal >= myBiggestVal:
                                    #                        totalOp = (theirValueAdd-myValueAdd)*0.5
                                    #                    else:
                                    #                        totalOp = (theirValueAdd-myValueAdd)*0.33
                                    #                else: continue

                                    #        elif theirValueAdd == myValueAdd:
                                    #            continue
                                    #            if opLims > 1: continue
                                    #            if theirBiggestVal >= myBiggestVal*1.5:
                                    #                if theirBiggestVal >= 150000:
                                    #                    totalOp = theirValueAdd*0.15
                                    #                else:
                                    #                    pass
                                    #            elif theirBiggestVal > myBiggestVal:
                                    #                pass
                                    #            elif theirBiggestVal == myBiggestVal:
                                    #                totalOpMe = myValueAdd*0.2
                                    #            else:
                                    #                if myBiggestVal >= theirBiggestVal*1.5:
                                    #                    totalOpMe = myValueAdd*0.5
                                    #                else:
                                    #                    totalOpMe = myValueAdd*0.25

                                    #    elif theirValueAdd > 0:
                                    #        customMinimum = 1.00
                                    #        customMaximum = 1.02
                                    #        if myBiggestVal > theirBiggestVal:
                                    #            if haveRare == True:
                                    #                totalOp = theirValueAdd*0.8
                                    #            else:
                                    #                totalOp = theirValueAdd*0.25
                                    #        else:
                                    #            if theirBiggestVal >= 130000:
                                    #                if theirBiggestVal > myBiggestVal*1.5:
                                    #                    totalOp = theirValueAdd*0.8
                                    #                else:
                                    #                    totalOp = theirValueAdd*0.5
                                    #            else:
                                    #                totalOp = theirValueAdd*0.5

                                    #    elif myValueAdd > 0:
                                    #        if opLimsMe > 1: continue
                                    #        customMaximum = 1.05
                                    #        if myBiggestVal >= 130000:
                                    #            if theirBiggestVal <= myBiggestVal*0.5:
                                    #                totalOpMe = myValueAdd*1.25
                                    #            else:
                                    #                totalOpMe = myValueAdd
                                    #        else:
                                    #            totalOpMe = myValueAdd


                                    if myValueAdd > 0:
                                        totalOpMe = myValueAdd
                                        customMaximum = 1.00
                                        customMaximum = 1.1
      

                                    if myTrade == theirTrade:
                                        if theirValue+totalOp <= ((myValue+totalOpMe)*customMaximum) and theirValue+totalOp >= ((myValue+totalOpMe)*customMinimum) and myValue > 0 and theirValue > 0 and theirValue-myValue >= config['config']['minimumProfit']: pass
                                        else: continue
                                    elif myTrade == 'Value' and theirTrade == 'Rap':
                                        if theirValue+totalOp <= ((myValue+totalOpMe)*customMaximum) and theirValue+totalOp >= ((myValue+totalOpMe)*customMinimum) and myValue > 0 and theirValue > 0 and theirValue-myValue >= config['config']['minimumProfit']: pass
                                        else: continue
                                    elif myTrade == 'Value' and theirTrade == 'Mixed':
                                        if theirValue+totalOp <= ((myValue+totalOpMe)*customMaximum) and theirValue+totalOp >= ((myValue+totalOpMe)*customMinimum) and myValue > 0 and theirValue > 0 and theirValue-myValue >= config['config']['minimumProfit']: pass
                                        else: continue
                                    else:
                                        if myValue >= 20000 or int(theirBiggestItem) in overallConfig['only_want_rap']:
                                            if myTrade == 'Rap' and theirTrade == 'Mixed':
                                                if theirValue <= (myValue*config['config']['rapMaximum']) and theirValue >= (myValue*config['config']['rapMinimum']) and myValue > 0 and theirValue > 0 and theirValue-myValue >= config['config']['minimumProfit']: pass
                                                else: continue
                                            elif myTrade == 'Rap' and theirTrade == 'Value':
                                                if theirValue <= (myValue*config['config']['rapMaximum']) and theirValue >= (myValue*config['config']['rapMinimum']) and myValue > 0 and theirValue > 0 and theirValue-myValue >= config['config']['minimumProfit']: pass
                                                else: continue
                                            else: continue
                                        else: continue


                                    profitAmount = theirValue-myValue

                                    typeTrade = ''
                                    if myBiggestVal == theirBiggestVal: typeTrade = 'equal'
                                    elif myBiggestVal < theirBiggestVal: typeTrade = 'upgrade'
                                    elif myBiggestVal > theirBiggestVal: typeTrade = 'downgrade'

                                    myNames = [f"(**{myValues[assetId.split(':')[0]].split('|')[0]}**) {myValues[assetId.split(':')[0]].split('|')[1]}" for assetId in mCombination]
                                    theirNames = [f"(**{theirValues[assetId.split(':')[0]].split('|')[0]}**) {theirValues[assetId.split(':')[0]].split('|')[1]}" for assetId in tCombination]

                                    while True:
                                        if len(self.tradesToSend) < queueLimit and self.stopQueue == False:

                                            theirItems = [int(assetId.split(':')[0]) for assetId in tCombination]
                                            myItems = [int(assetId.split(':')[0]) for assetId in mCombination]
                                            theirUaids = [int(assetId.split(':')[1]) for assetId in tCombination]
                                            myUaids = [int(assetId.split(':')[1]) for assetId in mCombination]

                                            self.tradesToSend.append([[int(userId)], theirUaids, myUaids, [myValue], [theirValue], [theirValueAdd], [myValueAdd], myNames, theirNames, myItems, theirItems, typeTrade, [customMinimum, customMaximum]])
                                            self.webhooksToSend.append([int(userId), theirUaids, myUaids, myValue, theirValue, theirValueAdd, myValueAdd, myNames, theirNames, myTrade, theirTrade, totalOp, totalOpMe])

                                            with lock: print(f'{Fore.LIGHTBLACK_EX}({Fore.LIGHTBLUE_EX}{userId}{Fore.LIGHTBLACK_EX}) was added to queue, there are currently {Fore.LIGHTBLUE_EX}{len(self.tradesToSend)}{Fore.LIGHTBLACK_EX} trades in queue')
                                            finish = True
                                            break
                                        else:
                                            sleep(1)
                                    break
                                if finish == True:
                                    break
                        except Exception as err:
                            print(err)
                            pass
                except Exception as err:
                    print(err)
                    continue
            sleep(0.25)

    def sendTrade(self):
        while True:
            if len(self.tradesToSend) >= 1 and self.stopQueue == False:
                try:
                    currentTrade = self.tradesToSend[0]
                    del self.tradesToSend[0]
                    theirUserId, theirUaids, myUaids, myValue, theirValue, theirValueAdd, myValueAdd, myNames, theirNames, myItems, theirItems, typeTrade, customRatios = currentTrade[0], currentTrade[1], currentTrade[2], currentTrade[3], currentTrade[4], currentTrade[5], currentTrade[6], currentTrade[7], currentTrade[8], currentTrade[9], currentTrade[10], currentTrade[11], currentTrade[12]
                    while True:
                        try:
                            csrf = requests.post('https://auth.roblox.com/v1/logout', cookies={'.ROBLOSECURITY': config['cookie']}).headers['X-CSRF-TOKEN']

                            json = {
                                "offers":[
                                    {"userId":theirUserId[0],"userassetIDs":theirUaids,"robux":None},
                                    {"userId":config['userId'],"userassetIDs":myUaids,"robux":None}
                                ]
                            }

                            trade = requests.post('https://trades.roblox.com/v1/trades/send', cookies={'.ROBLOSECURITY': config['cookie']}, headers={'X-CSRF-TOKEN': csrf}, json=json, proxies=random.choice(proxyList), timeout=2).json()
                            if self.debugAll == True:
                                with lock: print(trade)
                            if 'id' in trade:
                                self.tradesSent += 1
                                with lock: print(f'{Fore.LIGHTBLACK_EX}({Fore.GREEN}{theirUserId[0]}{Fore.LIGHTBLACK_EX}) was sent a trade [offering: {Fore.GREEN}{myValue[0]}{Fore.LIGHTBLACK_EX}, receiving: {Fore.GREEN}{theirValue[0]}{Fore.LIGHTBLACK_EX}, type: {Fore.GREEN}{typeTrade}{Fore.LIGHTBLACK_EX}]')
                                with open('outbounds.txt','a') as file:
                                    file.writelines(f'{trade["id"]}:{str(myItems)}:{str(theirItems)}:{str(customRatios)}\n')
                                sleep(60)
                                break
                            elif 'Roblox.com is unavailable' in str(trade):
                                continue
                            elif 'errors' in trade:
                                if trade['errors'][0]['message'] == 'TooManyRequests':
                                    self.tradesFailed += 1
                                    with lock: print(f'{Fore.LIGHTBLACK_EX}({Fore.RED}TooManyRequests{Fore.LIGHTBLACK_EX}) retrying in {Fore.RED}1{Fore.LIGHTBLACK_EX} minute')
                                    sleep(60)
                                    continue
                                elif 'userAssets are invalid' in trade['errors'][0]['message'] or 'not owned' in trade['errors'][0]['message'].lower():
                                    if self.passingQueue == 0:
                                        self.passingQueue += 1
                                        self.myItems()
                                    sleep(60)
                                    break
                                else:
                                    self.tradesFailed += 1
                                    sleep(60)
                                    break
                            else:
                                self.tradesFailed += 1
                                sleep(60)
                                break
                        except Exception as err:
                            sleep(1)
                            continue
                except Exception as err:
                    pass
            else:
                sleep(1)

    def sendWebhook(self):
        while True:
            if len(self.webhooksToSend) > 0:
                for currentTrade in self.webhooksToSend:
                    self.webhooksToSend.remove(currentTrade)
                    theirUserId, theirUaids, myUaids, myValue, theirValue, theirValueAdd, myValueAdd, myNames, theirNames, myTrade, theirTrade, totalOp, totalOpMe = currentTrade[0], currentTrade[1], currentTrade[2], currentTrade[3], currentTrade[4], currentTrade[5], currentTrade[6], '\n'.join(currentTrade[7]), '\n'.join(currentTrade[8]), currentTrade[9], currentTrade[10], currentTrade[11], currentTrade[12]

                    data = {
                      'embeds':[{
                          'color': int('3878b7',16),
                          'fields': [
                              {'name': f'Queued trade with: {theirUserId}','value': f'\u200b','inline':False},
                              {'name': f'📥 Offering: [{myValue}]','value': f'{myNames}','inline':True},
                              {'name': f'📤 Requesting: [{theirValue}]','value': f'{theirNames}','inline':True},
                              {'name': f'\u200b','value': f'\u200b','inline':True},
                              {'name': '🧐 Details:','value': f'OP: {totalOpMe} (**me**)\nOP: {totalOp} (**them**)','inline':True},
                              {'name': '💸 Profit:','value': f'{theirValue-myValue} ({str(round((((theirValue-theirValueAdd)/(myValue-myValueAdd))-1)*100, 2))}%)','inline':True},
                          ],
                          'thumbnail': {
                              'url': f'https://www.roblox.com/headshot-thumbnail/image?userId={theirUserId}&width=420&height=420&format=png',
                              }
                        }]
                    }

                    while True:
                        try:
                            r = requests.post(config['webhook'], json=data, proxies=random.choice(proxyList), timeout=3)
                            if r.status_code == 204: break
                        except Exception as err:
                            continue
            else:
                sleep(1)

    def overall(self):
        Thread(target=self.title).start()
        Thread(target=self.roliUpdater).start()
        sleep(5)

        if config['theirLists']['includeLimiteds'] != []:
            self.assetIds = config['theirLists']['includeLimiteds']
        elif config['config']['theirCustomizations']['receiveOnlyValue']:
            self.assetIds = self.onlyValue
        else:
            self.assetIds = overallConfig['scrape_assets']

        shuffle(self.assetIds)
        Thread(target=self.myItems).start()
        Thread(target=self.debugger).start()
        Thread(target=self.otherScraping).start()
        sleep(3)

        for i in range(config['functionThreads']['sendingWebhook']): Thread(target=self.sendWebhook).start()
        for i in range(config['functionThreads']['playerFilter']): Thread(target=self.checkOnline, args=[i]).start()
        for i in range(config['functionThreads']['findingTrade']): Thread(target=self.findTrade).start()
        for i in range(config['functionThreads']['sendingTrade']): Thread(target=self.sendTrade).start()

        while True:
            threads = []
            if len(self.assetIds) == 1:
                for i in range(1): threads.append(Thread(target=self.scrapeOwners,args=[self.assetIds]))
            else:
                for i in range(config['functionThreads']['scrapingOwners']): threads.append(Thread(target=self.scrapeOwners,args=[self.assetIds[i::config['functionThreads']['scrapingOwners']]]))
            for x in threads:
                x.start()
            for x in threads:
                x.join()

c = User(**config)
