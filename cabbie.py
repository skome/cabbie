#! /usr/bin/python
import os,sys
from worldcat.request.search import SRURequest
from worldcat.util.extract import extract_elements, pymarc_extract
import csv
import yaml

doc=""" 
Usage: %prog [inputfile] [outputfile]]
"""
cfgFileName = 'cabbie.cfg'

class codesList: #read in file, de-dupe
    def __init__(self, fh):
        self.codeFile = fh
    def listed(self):
        lines = [] # 
        for line in self.codeFile.readlines():
            lines.append(line.strip())
        lines = list(set(lines)) #De-dupe the list
        return lines

def getYAMLConfig(fname):
    try:
        with open(fname,'r') as ymlf:
            config = yaml.load(ymlf)
    except Exception as e:
        print "Error accessing config: ",e
    return config
    
def makeItemList(pymarcResults, lib, lCode):
    lItem = []
    try:#Extract the fields we want from the result set. Some fields we want may be unavailable 
        for r in pymarcResults:
            lItem.append(lib)#the library symbol, if any
            lItem.append(lCode)#the code we sent to look up the results
            for rec in MARCCODES:
               try:
                   lItem.append(r[rec].format_field().encode('utf-8'))
               except AttributeError:
                   lItem.append('{} = n/a'.format(rec))
    except Exception as e:
        print "Error: ",e
    return lItem
    
def search(lCodes):
    lcabsHeld = []
    lcabsNotHeld = []
    numCodes = 0
    heldRate = 0.0

    #loop through the list of book codes, search WC, write results to output file
    for numCodes, lCode in enumerate(lCodes):
        heldRate = float(len(lcabsHeld))/len(lCodes)
        print ('Record: {} / {} Held Rate = {:.2f}\r'.format(numCodes, len(lCodes), heldRate)),
        sys.stdout.flush()
        query = '({}="{}") and (srw.li="{}")'.format(SRUELEM,lCode,LIBS) #Ex: sru.args['query'] = '(srw.no="122347155") and (srw.li="HDC")'
        sru.args['query'] = query # set the query
        results = pymarc_extract(sru.get_response().data) # send the query, extract the results from MARC into list
        if len(results) ==0: #Honnold has no holdings, open the search
            libs='ALL'
            query = '({}="{}")'.format(SRUELEM,lCode) #no library code; search all libs
            sru.args['query'] = query # set the query
            results = pymarc_extract(sru.get_response().data) # send the query, extract the results from MARC into list          
            lcabsNotHeld.append(makeItemList(results,libs,lCode))
        else: #Check Honnold holdings
            libs = LIBS
            lcabsHeld.append(makeItemList(results,libs,lCode))
    return lcabsHeld, lcabsNotHeld
 
if __name__ == "__main__":
    config = getYAMLConfig(cfgFileName)
    WSKEY = config['Auth']['WSKEY']
    LIBS = config['Config']['LIBS']
    SVCLVL = config['Config']['SVCLVL']
    SRUELEM = config['Config']['SRUELEM']
    MARCCODES = config['Config']['MARCCODES']
    lCodes=[]
    # Set up the worldcat SRU request 
    sru = SRURequest(wskey=WSKEY)
    sru.args['servicelevel'] = SVCLVL
    sru.url = 'http://www.worldcat.org/webservices/catalog/search/worldcat/sru'
    fileIn = sys.argv[1]
    fileOut = sys.argv[2]    
    csvHdr = ['Library','ISBN']+MARCCODES
    with open(fileIn, 'r') as cabCodes , open(fileOut, 'w') as bibsOut:
        csvOut = csv.writer(bibsOut, quoting=csv.QUOTE_NONNUMERIC)
        csvOut.writerow(csvHdr)
        bList = codesList(cabCodes) #Returns a de-duped list; results file may be smaller than source file
        lCodes = bList.listed()
        matches, nonmatches = search(lCodes) # look them all up, return worldcat bib data 
        print('{} matches and {} nonmatches, {:.1f}% match rate'.format(len(matches), len(nonmatches),float(len(matches))/len(lCodes)*100))
        for row in matches: # write the results to a csv file
            csvOut.writerow(row) 
        for row in nonmatches:
            csvOut.writerow(row)
        print 'The file {} is complete.'.format(fileOut)
