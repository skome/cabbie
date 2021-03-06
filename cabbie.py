#!/usr/bin/python
import os,sys
from worldcat.request.search import SRURequest
from worldcat.util.extract import extract_elements, pymarc_extract
import csv
import yaml

doc=""" 
Usage: %prog inputfile outputfile
Input file should consist of a list of single ISBN codes. They can be 10 or 13 digit.
Output file will consist of a csv file containing bibliographic data for the ISBN codes. The first field shows the holding library or 'All'
The Worldcat library(/ies) to search are configurable in the .cfg; the MARC fields returned can be configured in cabbie.py
"""
cfgFileName = 'cabbie.cfg' #OCLC key and some settings live here
FRBRgrouping = 'on' # control how related works are returned

class codesList: 
    """input: file with a list of (ISBN) values. Return:de-duped list."""
    def __init__(self, fh):
        self.codeFile = fh
    def listed(self):
        lines = [] # 
        for line in self.codeFile.readlines():
            lines.append(line.strip())
        lines = list(set(lines)) #De-dupe the list
        return lines

def getYAMLConfig(fname): 
    """ input: yamlfile path. return: yaml"""
    try:
        with open(fname,'r') as ymlf:
            config = yaml.load(ymlf)
    except Exception as e:
        print "Error accessing config: ",e
    return config
    
def makeItemList(pymarcResults, lib, lCode): 
    """input: pymarc. return: list of config'd marc fields"""
    lItem = []
    try:#Extract the fields we want from the result set. Some fields we want may be unavailable 
        for r in pymarcResults:
            lItem = []
            lItem.append(lib)#the library symbol, if any
            lItem.append(lCode)#the code we sent to look up the results
            for rec in MARCCODES: #if rec is '245' don't take the subfield(s), e.g. (r['245']['a'])
               try:
                   lItem.append(r[rec].format_field().encode('utf-8'))#add the pymarc record to the list
               except AttributeError: # no Worldcat data in that marc field
                   lItem.append('{} = n/a'.format(rec)) 
    except Exception as e:
        print "Error: ",e
    return lItem

           
def search(lCodes): 
    """input: list of (ISBN) codes. Query WC SRU with them. Return enhanced lists of held and not held items"""
    lcabsHeld = []
    lcabsNotHeld = []
    numCodes = 0
    for numCodes, lCode in enumerate(lCodes):#search HDC by ISBN first. Build lists of hits and misses
        print ('ISBN Search: {} / {} {}').format(numCodes, len(lCodes),'\r'),#print status
        sys.stdout.flush()
        query = '({}="{}") and (srw.li="{}")'.format(SRUELEM,lCode,LIBS) #Ex: sru.args['query'] = '(srw.no="122347155") and (srw.li="HDC")'
        sru.args['query'] = query # set the query
        results = pymarc_extract(sru.get_response().data) # send the query
        if len(results) == 0: #Honnold has no holdings, open the search to worldwide libraries
            libs='ALL' 
            query = '({}="{}")'.format(SRUELEM,lCode) #no library code; search all libs
            sru.args['query'] = query # set the query
            results = pymarc_extract(sru.get_response().data) # send the query
            lcabsNotHeld.append(makeItemList(results,libs,lCode))
        else: #Honnold has holdings
            libs = LIBS
            lcabsHeld.append(makeItemList(results,libs,lCode))
    return lcabsHeld, lcabsNotHeld

def search245(resultsList):
    """perform SRU title/author search -- for non-matched items (this needs to be integrated)"""
    lcabsHeld = []
    lcabsNotHeld = []
    for numCodes, item in enumerate(resultsList):
        if len(item)>0: #empty items happen and they don't help
            if len(item[6]) == 1: #title for matches (ugly code)
                shortTitle = item[6]
            else:
                try:# make a short title string to search because the full title prolly won't match
                    shortTitleWords = item[6].split(' ')[0:2] #try 1, 2, or 3 words
                    shortTitle = ' '.join(shortTitleWords)
                except IndexError: #some titles have only one word
                    shortTitle = item[6].split(' ')[0]
                except TypeError: 
                    print('TypeError: {}').format(item)
            author = item[-1].split(' ')[0].strip(',') #author's last name
            query = '({} = "{}*") and ({}="{}*") and (srw.li="{}")'.format('srw.ti',shortTitle,'srw.au',author,LIBS) #Ex: sru.args['query'] = '(srw.no="122347155") and (srw.li="HDC")'
            print ('Title Search: {} / {} {}{}').format(numCodes, len(resultsList),query,'\r'),
            sys.stdout.flush()
            sru.args['query'] = query # set the query
            results = pymarc_extract(sru.get_response().data) # send the query
            if len(results) == 0: #Honnold has no holdings
                libs='ALL'
                lcabsNotHeld.append(makeItemList(results,libs,item[1]))
            else: #Honnold holdings-ish
                libs = 'HDC-ish'
                lcabsHeld.append(makeItemList(results,libs,item[1]))
    return lcabsHeld, lcabsNotHeld
 
if __name__ == "__main__":
    config = getYAMLConfig(cfgFileName) #read in config values
    WSKEY = config['Auth']['WSKEY_SEARCH']
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
            csvOut.writerow(row)
        print('{} unique codes in the original file.').format(len(lCodes))
        print('{} code matches').format(len(matches))
        print('{} title/author matches').format(len(titlematches))
    print 'The file {} is complete.'.format(fileOut)
