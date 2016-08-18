#!/usr/bin/python
import os,sys
from worldcat.request.search import SRURequest
from worldcat.util.extract import extract_elements, pymarc_extract
import csv
import yaml

doc=""" 
Usage: %prog [inputfile] [outputfile]]
"""
cfgFileName = 'cabbie.cfg' #OCLC key and some settings live here
FRBRgrouping = 'on' # control how related works are returned

class codesList: #read in a file with a list of values, de-dupe the values
    def __init__(self, fh):
        self.codeFile = fh
    def listed(self):
        lines = [] # 
        for line in self.codeFile.readlines():
            lines.append(line.strip())
        lines = list(set(lines)) #De-dupe the list
        return lines

def getYAMLConfig(fname): # read the config file values
    try:
        with open(fname,'r') as ymlf:
            config = yaml.load(ymlf)
    except Exception as e:
        print "Error accessing config: ",e
    return config
    
def makeItemList(pymarcResults, lib, lCode): #get the oclc results out from the pymarc object and create a list from them
    lItem = []
    try:#Extract the fields we want from the result set. Some fields we want may be unavailable 
        for r in pymarcResults:
            lItem = []
            lItem.append(lib)#the library symbol, if any
            lItem.append(lCode)#the code we sent to look up the results
            for rec in MARCCODES: 
               try:
                   lItem.append(r[rec].format_field().encode('utf-8'))#add the pymarc record to the list
               except AttributeError: # no Worldcat data in that marc field
                   lItem.append('{} = n/a'.format(rec)) 
    except Exception as e:
        print "Error: ",e
    return lItem

           
def search(lCodes): #loop through the list of book codes, search WC, write results to output file
    lcabsHeld = []
    lcabsNotHeld = []
    numCodes = 0
    for numCodes, lCode in enumerate(lCodes):#search HDC by ISBN first. Build lists of hits and misses
        print ('ISBN Search: {} / {} {}').format(numCodes, len(lCodes),'\r'),#print status
        sys.stdout.flush()
        query = '({}="{}") and (srw.li="{}")'.format(SRUELEM,lCode,LIBS) #Ex: sru.args['query'] = '(srw.no="122347155") and (srw.li="HDC")'
        sru.args['query'] = query # set the query
        results = pymarc_extract(sru.get_response().data) # send the query
        if len(results) ==0: #Honnold has no holdings, open the search to worldwide libraries
            libs='ALL' 
            query = '({}="{}")'.format(SRUELEM,lCode) #no library code; search all libs
            sru.args['query'] = query # set the query
            results = pymarc_extract(sru.get_response().data) # send the query
            lcabsNotHeld.append(makeItemList(results,libs,lCode))
        else: #Honnold has holdings
            libs = LIBS
            lcabsHeld.append(makeItemList(results,libs,lCode))
    return lcabsHeld, lcabsNotHeld

def search245(resultsList):#specifically doing a title/author search, this subroutine needs to be integrated
    lcabsHeld = []
    lcabsNotHeld = []
    for numCodes, item in enumerate(resultsList):
        if len(item)>0: #empty items happen and they don't help
            try:# make a short title string to search because the full title prolly won't match
                shortTitleWords = item[6].split(' ')[0:2] #playing 1, 2, or 3 words
                shortTitle = ' '.join(shortTitleWords)
            except IndexError: #some titles have only one word
                shortTitle = item[6].split(' ')[0]
            author = item[-1].split(' ')[0].strip(',') #just taking the author's last name
            query = '({} = "{}*") and ({}="{}*") and (srw.li="{}")'.format('srw.ti',shortTitle,'srw.au',author,LIBS) #Ex: sru.args['query'] = '(srw.no="122347155") and (srw.li="HDC")'
            print ('Title Search: {} / {} {}{}').format(numCodes, len(resultsList),query,'\r'),
            sys.stdout.flush()
            sru.args['query'] = query # set the query
            results = pymarc_extract(sru.get_response().data) # send the query
            if len(results) == 0: #Honnold has no holdings
                libs=LIBS
                lcabsNotHeld.append(makeItemList(results,libs,item[1]))
            else: #Honnold holdings-ish
                libs = 'HDC-ish'
                lcabsHeld.append(makeItemList(results,libs,item[1]))
    return lcabsHeld, lcabsNotHeld
 
if __name__ == "__main__":
    config = getYAMLConfig(cfgFileName) #read in config values
    WSKEY = config['Auth']['WSKEY']
    LIBS = config['Config']['LIBS']
    SVCLVL = config['Config']['SVCLVL']
    SRUELEM = config['Config']['SRUELEM']
    MARCCODES = config['Config']['MARCCODES']
    lCodes=[]
    sru = SRURequest(wskey=WSKEY)     # Set up the worldcat SRU request object
    sru.args['servicelevel'] = SVCLVL
    sru.args['FRBRgrouping'] = FRBRgrouping
    sru.url = 'http://www.worldcat.org/webservices/catalog/search/worldcat/sru'
    fileIn = sys.argv[1]
    fileOut = sys.argv[2]    
    csvHdr = ['Library','ISBN']+MARCCODES
    with open(fileIn, 'r') as cabCodes , open(fileOut, 'w') as bibsOut:
        csvOut = csv.writer(bibsOut, quoting=csv.QUOTE_NONNUMERIC)# set up a csv file
        csvOut.writerow(csvHdr)
        bList = codesList(cabCodes) # get the codes from the file
        lCodes = bList.listed() #a de-duped list of the codes in the file
        matches, nonmatches = search(lCodes) # look them all up by ISBN, return worldcat bib data 
        for row in matches: # write the direct matches (on ISBN) to a csv file
            csvOut.writerow(row) 
        titlematches, nontitlematches = search245(nonmatches) #look for title/author matches
        for row in titlematches:
            #print('{}\n\n').format(row)
            csvOut.writerow(row)
    print 'The file {} is complete.'.format(fileOut)
