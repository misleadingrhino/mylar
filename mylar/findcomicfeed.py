#!/usr/bin/env python

import os
import sys
import time
import feedparser
import re
import logger
import mylar
import unicodedata
import urllib

def Startit(searchName, searchIssue, searchYear, ComicVersion, IssDateFix, booktype=None):
    cName = searchName

    #clean up searchName due to webparse/redudant naming that would return too specific of results.
    commons = ['and', 'the', '&', '-']
    for x in commons:
        cnt = 0
        for m in re.finditer(x, searchName.lower()):
            cnt +=1
            tehstart = m.start()
            tehend = m.end()
            if any([x == 'the', x == 'and']):
                if len(searchName) == tehend:
                    tehend =-1
                if all([tehstart == 0, searchName[tehend] == ' ']) or all([tehstart != 0, searchName[tehstart-1] == ' ', searchName[tehend] == ' ']):
                    searchName = searchName.replace(x, ' ', cnt)
                else:
                    continue
            else:
                searchName = searchName.replace(x, ' ', cnt)

    searchName = re.sub('\s+', ' ', searchName)
    searchName = re.sub("[\,\:]", "", searchName).strip()
    #logger.fdebug("searchname: %s" % searchName)
    #logger.fdebug("issue: %s" % searchIssue)
    #logger.fdebug("year: %s" % searchYear)
    encodeSearch = urllib.quote_plus(searchName)
    splitSearch = encodeSearch.split(" ")

    tmpsearchIssue = searchIssue

    if any([booktype == 'One-Shot', booktype == 'TPB']):
        tmpsearchIssue = '1'
        loop = 4
    elif len(searchIssue) == 1:
        loop = 3
    elif len(searchIssue) == 2:
        loop = 2
    else:
        loop = 1

    if "-" in searchName:
        searchName = searchName.replace("-", '((\\s)?[-:])?(\\s)?')
    regexName = searchName.replace(" ", '((\\s)?[-:])?(\\s)?') 

    if mylar.CONFIG.USE_MINSIZE is True:
        minsize = str(mylar.CONFIG.MINSIZE)
    else:
        minsize = '10'
    size_constraints = "&minsize=" + minsize

    if mylar.CONFIG.USE_MAXSIZE is True:
        maxsize = str(mylar.CONFIG.MAXSIZE)
    else:
        maxsize = '0'
    size_constraints += "&maxsize=" + maxsize

    if mylar.CONFIG.USENET_RETENTION is not None:
        max_age = "&maxage=" + str(mylar.CONFIG.USENET_RETENTION)
    else:
        max_age = "&maxage=0"

    feeds = []
    i = 1
    while (i <= loop):
        if i == 1:
            searchmethod = tmpsearchIssue
        elif i == 2:
            searchmethod = '0' + tmpsearchIssue
        elif i == 3:
            searchmethod = '00' + tmpsearchIssue
        elif i == 4:
            searchmethod = tmpsearchIssue
        else:
            break

        if i == 4:
            logger.fdebug('Now searching experimental for %s to try and ensure all the bases are covered' % cName)
            joinSearch = "+".join(splitSearch)
        else:
            logger.fdebug('Now searching experimental for issue number: %s to try and ensure all the bases are covered' % searchmethod)
            joinSearch = "+".join(splitSearch) + "+" +searchmethod



        if mylar.CONFIG.PREFERRED_QUALITY == 1: joinSearch = joinSearch + " .cbr"
        elif mylar.CONFIG.PREFERRED_QUALITY == 2: joinSearch = joinSearch + " .cbz"

        feeds.append(feedparser.parse("http://beta.nzbindex.com/search/rss?q=%s&max=50&minage=0%s&hidespam=1&hidepassword=1&sort=agedesc%s&complete=0&hidecross=0&hasNFO=0&poster=&g[]=85" % (joinSearch, max_age, size_constraints)))
        time.sleep(5)
        if mylar.CONFIG.ALTEXPERIMENTAL:
            feeds.append(feedparser.parse("http://beta.nzbindex.com/search/rss?q=%s&max=50&minage=0%s&hidespam=1&hidepassword=1&sort=agedesc%s&complete=0&hidecross=0&hasNFO=0&poster=&g[]=86" % (joinSearch, max_age, size_constraints)))
            time.sleep(5)
        i+=1

    entries = []
    mres = {}
    tallycount = 0

    for feed in feeds:
        totNum = len(feed.entries)
        tallycount += len(feed.entries)

        #keyPair = {}
        keyPair = []
        regList = []
        countUp = 0

        while countUp < totNum:
     	    urlParse = feed.entries[countUp].enclosures[0]
	    #keyPair[feed.entries[countUp].title] = feed.entries[countUp].link
	    #keyPair[feed.entries[countUp].title] = urlParse["href"]
            keyPair.append({"title":     feed.entries[countUp].title,
                            "link":      urlParse["href"],
                            "length":    urlParse["length"],
                            "pubdate":   feed.entries[countUp].updated})
            countUp=countUp +1

        # thanks to SpammyHagar for spending the time in compiling these regEx's!

        regExTest=""

        regEx = "(%s\\s*(0)?(0)?%s\\s*\\(%s\\))" %(regexName, searchIssue, searchYear)
        regExOne = "(%s\\s*(0)?(0)?%s\\s*\\(.*?\\)\\s*\\(%s\\))" %(regexName, searchIssue, searchYear)

        #Sometimes comics aren't actually published the same year comicVine says - trying to adjust for these cases
        regExTwo = "(%s\\s*(0)?(0)?%s\\s*\\(%s\\))" %(regexName, searchIssue, int(searchYear) +1)
        regExThree = "(%s\\s*(0)?(0)?%s\\s*\\(%s\\))" %(regexName, searchIssue, int(searchYear) -1)
        regExFour = "(%s\\s*(0)?(0)?%s\\s*\\(.*?\\)\\s*\\(%s\\))" %(regexName, searchIssue, int(searchYear) +1)
        regExFive = "(%s\\s*(0)?(0)?%s\\s*\\(.*?\\)\\s*\\(%s\\))" %(regexName, searchIssue, int(searchYear) -1)

        regexList=[regEx, regExOne, regExTwo, regExThree, regExFour, regExFive]

        except_list=['releases', 'gold line', 'distribution', '0-day', '0 day', '0day', 'o-day']

        for entry in keyPair:
            title = entry['title']
            #logger.fdebug("titlesplit: " + str(title.split("\"")))
            splitTitle = title.split("\"")
            noYear = 'False'
            _digits = re.compile('\d')

            for subs in splitTitle:
                #logger.fdebug('sub:' + subs)
                regExCount = 0
                if len(subs) >= len(cName) and not any(d in subs.lower() for d in except_list) and bool(_digits.search(subs)) is True:
                #Looping through dictionary to run each regEx - length + regex is determined by regexList up top.
#                while regExCount < len(regexList):
#                    regExTest = re.findall(regexList[regExCount], subs, flags=re.IGNORECASE)
#                    regExCount = regExCount +1
#                    if regExTest:
#                        logger.fdebug(title)
#                        entries.append({
#                                  'title':   subs,
#                                  'link':    str(link)
#                                  })
                    # this will still match on crap like 'For SomeSomayes' especially if the series length < 'For SomeSomayes'
                    if subs.lower().startswith('for'):
                        if cName.lower().startswith('for'):
                            pass
                        else:
                            #this is the crap we ignore. Continue (commented else, as it spams the logs)
                            #logger.fdebug('this starts with FOR : ' + str(subs) + '. This is not present in the series - ignoring.')
                            continue
                    #logger.fdebug('match.')
                    if IssDateFix != "no":
                        if IssDateFix == "01" or IssDateFix == "02": ComicYearFix = str(int(searchYear) - 1)
                        else: ComicYearFix = str(int(searchYear) + 1)
                    else:
                        ComicYearFix = searchYear

                    if searchYear not in subs and ComicYearFix not in subs:
                        noYear = 'True'
                        noYearline = subs

                    if (searchYear in subs or ComicYearFix in subs) and noYear == 'True':
                        #this would occur on the next check in the line, if year exists and
                        #the noYear check in the first check came back valid append it
                        subs = noYearline + ' (' + searchYear + ')'
                        noYear = 'False'

                    if noYear == 'False':

                        entries.append({
                                  'title':     subs,
                                  'link':      entry['link'],
                                  'pubdate':   entry['pubdate'],
                                  'length':    entry['length']
                                  })
                        break  # break out so we don't write more shit.

#    if len(entries) >= 1:
    if tallycount >= 1:
        mres['entries'] = entries
        return mres
    else:
        logger.fdebug("No Results Found")
        return "no results"
