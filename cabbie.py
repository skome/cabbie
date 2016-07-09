#! /usr/bin/python
import os,sys
from worldcat.request.search import SRURequest
from worldcat.util.extract import extract_elements, pymarc_extract
import csv

#Ex: Whole list of LINK+ libraries
#LIBS = "ALLIU,CAP,CBC,CCO,CDS,CFS,CFV,CLO,CLV,CMM,CPO,CPS,CPT,CPU,CRP,CSF,CSH,CSJ,CSO,CTU,CUF,CWC,GH0,HAY,JQA,JQF,JQJ,JRR,JRS,JRZ,LIV,LLU,LML,LMR,MIS,MVP,NNY,PAP,PN#,PP2,QP9,SDG,SFR,SJP,STA,SVW,SXP,UNL,UOA"
LIBS = "HDC" #empty string means ALL libraries
WSKEY = 'EOdqmdJaycDuD5oEdJgAei89D1qEfmY4xS7iAah4arZYUWhHP4KVP7i6C5Dg4YYegw04dgYLn0mB6LqH'
SVCLVL = 'full'
SRUELEM = 'srw.bn'#ISBN
#SRUELEM = 'srw.no'#OCLC Num 
MARCCODES = ['001','020','050','245','264']
doc=""" 
Usage: %prog [inputfile] [outputfile]]
"""
lCodes=[]
# Set up the worldcat SRU request 
sru = SRURequest(wskey=WSKEY)
sru.args['servicelevel'] = SVCLVL
sru.url = 'http://www.worldcat.org/webservices/catalog/search/worldcat/sru'

class codesList: #read in file, de-dupe
    def __init__(self, fh):
        self.codeFile = fh
    def listed(self):
        lines = [] # 
        for line in self.codeFile.readlines():
            lines.append(line.strip())
        lines = list(set(lines)) #De-dupe the list
        return lines

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
        if len(results) ==0:
            libs='ALL'
            query = '({}="{}")'.format(SRUELEM,lCode) #no library code; search all libs
            sru.args['query'] = query # set the query
            results = pymarc_extract(sru.get_response().data) # send the query, extract the results from MARC into list          
            lcabsNotHeld.append(makeItemList(results,libs,lCode))
        else:
            libs = LIBS
            lcabsHeld.append(makeItemList(results,libs,lCode))
    return lcabsHeld, lcabsNotHeld
 
if __name__ == "__main__":
    fileIn = sys.argv[1]
    fileOut = sys.argv[2]    
    csvHdr = ['Library','ISBN']+MARCCODES
    with open(fileIn, 'r') as cabCodes , open(fileOut, 'w') as bibsOut:
        csvOut = csv.writer(bibsOut, quoting=csv.QUOTE_NONNUMERIC)
        csvOut.writerow(csvHdr)
        bList = codesList(cabCodes) #Returns a de-duped list
        lCodes = bList.listed()
        matches, nonmatches = search(lCodes) # look them all up, return worldcat bib data 
        print('{} matches and {} nonmatches, {:.1f}% match rate'.format(len(matches), len(nonmatches),float(len(matches))/len(lCodes)*100))
        for row in matches: # write the results to a csv file
            csvOut.writerow(row) 
        for row in nonmatches:
            csvOut.writerow(row)
        print 'The file {} is complete.'.format(fileOut)
