# Autosub autosub/checkRss.py - http://code.google.com/p/auto-sub/
#
# The Autosub checkRss module
#

import logging
import urllib2
import os

from library.beautifulsoup import BeautifulStoneSoup

#from operator import itemgetter

import autosub.Helpers

log = logging.getLogger('thelogger')

class checkRss():
    """
    Check the RSS feed for subtitles of episodes that are in the WANTEDQUEUE.
    If the subtitles are found, they are added to the TODOWNLOADQUEUE
    """
    def run(self):    
        log.debug("checkRSS: Starting round of RSS checking")

        if autosub.TODOWNLOADQUEUELOCK or autosub.WANTEDQUEUELOCK:
            log.debug("checkRSS: Exiting, another threat is using the queues")
            return False
        else:
            autosub.TODOWNLOADQUEUELOCK = True
            autosub.WANTEDQUEUELOCK = True

        toDelete_wantedQueue = []

        langs = ["nl"]
        # default is to only check for Dutch subs
        # but if English should be downloaden, check them too
        # It is very important that the dutch language is run first!
        if autosub.FALLBACKTOENG or autosub.DOWNLOADENG:
            langs.append("en")
            log.debug("checkRSS: We also want to check the English RSS feed")
        
        for lang in langs:
            if lang == "en":
                RSSURL = autosub.ENRSSURL
                log.debug("checkRSS: Now using the English RSS feed")
            else:
                RSSURL = autosub.NLRSSURL
                log.debug("checkRSS: Now using the Dutch RSS feed")
            
            try:
                req = urllib2.Request(RSSURL)
                req.add_header("User-agent", autosub.USERAGENT) 
                response = urllib2.urlopen(req,None,autosub.TIMEOUT)
                log.debug("checkRss: Succussfully connected to %s" %RSSURL)
                
                soup = BeautifulStoneSoup(response)
                response.close()
            except:
                log.error("checkRss: The server returned an error for request %s" % RSSURL)
                autosub.TODOWNLOADQUEUELOCK = False
                autosub.WANTEDQUEUELOCK = False
                continue
            
            # Parse all the item-tags from the RSSFeed
            # The information that is parsed is: title, link and show_id
            # The show_id is later used to match with the wanted items
            # The title is used the determine the quality / source / releasegrp
            
            rssItemList = []
            items = soup.findAll('item')
            
            if not len(items) > 0:
                log.error("checkRss: invalid RssFeed")
                log.debug("checkRss: dumping Rssfeed %s" %(soup.prettify())) 
            else:
                log.debug("checkRss: Valid RssFeed")
            
            for x in items:
                soupx = BeautifulStoneSoup(str(x))
                title = soupx.find('title').string
                show_id = soupx.find('show_id').string
                link = soupx.find('link').string
                item = {}
                item['title'] = title
                item['link'] = link
                item['show_id'] = show_id
                log.debug("checkRSS: Parsed from RSSFEED: %s %s %s" %(title,link,show_id))
                rssItemList.append(item)
            
            normalizedRssTitleList = []
            
            # Now we create a new rsslist, containing information like: episode, season, etc
            for item in rssItemList:
                title = item['title']
                link = item['link']
                show_id = item['show_id']
                log.debug("checkRSS: Normalizing the following entry in the RSS results: %s" % title)
                normalizedRssTitle = autosub.Helpers.ProcessFileName(str(title),'')
                normalizedRssTitle['rssfile'] = title
                normalizedRssTitle['link'] = link
                normalizedRssTitle['show_id'] = str(show_id)
                if 'title' in normalizedRssTitle.keys():
                    if 'season' in normalizedRssTitle.keys():
                        if 'episode' in normalizedRssTitle.keys():        
                            normalizedRssTitleList.append(normalizedRssTitle)
            
            #check versus wantedItem list
            for index, wantedItem in enumerate(autosub.WANTEDQUEUE):
                wantedItemquality = None
                wantedItemreleasegrp = None
                wantedItemsource = None
                wantedItemtitle = wantedItem['title']
                wantedItemseason = wantedItem['season']
                wantedItemepisode = wantedItem['episode']
                originalfile = wantedItem['originalFileLocationOnDisk']
                
                if lang not in wantedItem['lang']:
                    continue
                
                if 'quality' in wantedItem.keys(): wantedItemquality = wantedItem['quality']
                if 'releasegrp' in wantedItem.keys(): wantedItemreleasegrp = wantedItem['releasegrp']
                if 'source' in wantedItem.keys(): wantedItemsource = wantedItem['source']
                
                #lets try to find a showid
                showid = autosub.Helpers.getShowid(wantedItemtitle)
            
                #no showid? skip this item
                if not showid:
                    continue
                

                for normalizedRssTitle in normalizedRssTitleList:
                    toDownloadItem = None
                    downloadLink = None
                    normalizedRssTitlequality = None
                    normalizedRssTitlereleasegrp = None
                    normalizedRssTitlesource = None
                    normalizedRssTitletitle = normalizedRssTitle['title']
                    normalizedRssTitleseason = normalizedRssTitle['season']
                    normalizedRssTitleepisode = normalizedRssTitle['episode']
                    normalizedRssTitlerssfile = normalizedRssTitle['rssfile']
                    normalizedRssTitleshowid = normalizedRssTitle['show_id']
                    normalizedRssTitlelink = normalizedRssTitle['link']
                    
                    if 'quality' in normalizedRssTitle.keys(): normalizedRssTitlequality = normalizedRssTitle['quality']
                    if 'releasegrp' in normalizedRssTitle.keys(): normalizedRssTitlereleasegrp = normalizedRssTitle['releasegrp']
                    if 'source' in normalizedRssTitle.keys(): normalizedRssTitlesource = normalizedRssTitle['source']

                    if showid == normalizedRssTitleshowid and wantedItemseason == normalizedRssTitleseason and wantedItemepisode == normalizedRssTitleepisode:
                        log.debug("checkRSS:  The episode %s - Season %s Episode %s was found in the RSS list, attempting to match a proper match" % (wantedItemtitle, wantedItemseason, wantedItemepisode))

                        score = autosub.Helpers.scoreMatch(normalizedRssTitlerssfile, wantedItemquality, wantedItemreleasegrp, wantedItemsource)
                        if score >= autosub.MINMATCHSCORERSS:
                            log.debug ("checkRss: A match got a high enough score. MinMatchscore is %s " % autosub.MINMATCHSCORERSS)
                            downloadLink = normalizedRssTitlelink + autosub.APIRSS
                            log.info ("checkRss: Got a match, matching file is: %s" %normalizedRssTitlerssfile)       
                            log.debug("checkRss: Dumping downloadlink for debug purpose: %s" %downloadLink)
                        if downloadLink:
                            originalfile = wantedItem['originalFileLocationOnDisk']
                            # Dutch subs
                            if autosub.SUBNL != "" and lang == "nl":
                                srtfile = os.path.join(originalfile[:-4] + "." + autosub.SUBNL + ".srt")
                            elif lang == "nl":
                                srtfile = os.path.join(originalfile[:-4] + ".srt")
                            # English subs
                            if autosub.SUBENG != "" and lang == "en":
                                srtfile = os.path.join(originalfile[:-4] + "." + autosub.SUBENG + ".srt")
                            elif lang == "en":
                                srtfile = os.path.join(originalfile[:-4] + ".srt")
                            wantedItem['downloadLink'] = downloadLink
                            wantedItem['destinationFileLocationOnDisk'] = srtfile
                            log.info("checkRSS: The episode %s - Season %s Episode %s has a matching subtitle on the RSSFeed, adding to toDownloadQueue" % (wantedItemtitle, wantedItemseason, wantedItemepisode))
                            
                            downloadItem = wantedItem.copy()
                            downloadItem['downlang'] = lang
                            autosub.TODOWNLOADQUEUE.append(downloadItem)
                            
                            if lang == 'nl' and (autosub.FALLBACKTOENG and not autosub.DOWNLOADENG) and 'en' in wantedItem['lang']:
                                log.debug('checkRss: We found a dutch subtitle and fallback is true. Removing the english subtitle from the wantedlist.')
                                wantedItem['lang'].remove('en')
                            
                            wantedItem['lang'].remove(lang)

                            if len(wantedItem['lang']) == 0:
                                toDelete_wantedQueue.append(index)
                                
                            break
                        else:
                            log.debug("checkRss: Matching score is not high enough. Score is %s should be %s" %(str(score),autosub.MINMATCHSCORERSS))
            i = len(toDelete_wantedQueue)-1
            while i >= 0:
                log.debug("checkRSS: Removed item from the wantedQueue at index %s" % toDelete_wantedQueue[i])
                autosub.WANTEDQUEUE.pop(toDelete_wantedQueue[i])
                i = i-1
            # Resetting the toDelete queue for the next run (if need)
            toDelete_wantedQueue =[]
    
        log.debug("checkRSS: Finished round of RSS checking")
        autosub.TODOWNLOADQUEUELOCK = False
        autosub.WANTEDQUEUELOCK = False
        return True
