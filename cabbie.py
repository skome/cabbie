#! /usr/bin/python

import os,sys,time
import urllib2
from xml.dom import minidom
from worldcat.request.search import SRURequest
from worldcat.util.extract import extract_elements, pymarc_extract
import csv

#Ex: Whole list of LINK+ libraries
#LIBS = "ALLIU,CAP,CBC,CCO,CDS,CFS,CFV,CLO,CLV,CMM,CPO,CPS,CPT,CPU,CRP,CSF,CSH,CSJ,CSO,CTU,CUF,CWC,GH0,HAY,JQA,JQF,JQJ,JRR,JRS,JRZ,LIV,LLU,LML,LMR,MIS,MVP,NNY,PAP,PN#,PP2,QP9,SDG,SFR,SJP,STA,SVW,SXP,UNL,UOA"
LIBS = "HDC"
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


def search(lCodes):
   lcabsHeld = []
   numCodes = 0
   #loop through the list of book codes, search WC, write results to output file
   for numCodes, lCode in enumerate(lCodes):
      print ('{} / {}\r'.format(numCodes, len(lCodes))),
      sys.stdout.flush()
      #Ex: sru.args['query'] = '(srw.no="122347155") and (srw.li="HDC")'
      query = '({}="{}") and (srw.li="{}")'.format(SRUELEM,lCode,LIBS)
      sru.args['query'] = query 
      results = pymarc_extract(sru.get_response().data)

      try:#Extract the fields we want from the result set. Some fields we want may be unavailable 
         for r in results:
            lItem = []
            lItem.append(lCode)#the code we sent to look up the results
            for rec in MARCCODES:
               try:
                  lItem.append(r[rec].format_field().encode('utf-8'))
               except AttributeError:
                  lItem.append('{}=n/a'.format(rec))
                  #Ex what tags are present: taglist = [x.tag for x in results[0].get_fields()]
                  #for t in taglist:
                  #   print t,#r[t].format_field(),
            print lItem      
            lcabsHeld.append(lItem) 
      except Exception as e:
         print "Error: ",e
   #print lcabsHeld
   return lcabsHeld
 
if __name__ == "__main__":
    fileIn = sys.argv[1]
    fileOut = sys.argv[2]    
    with open(fileIn, 'r') as cabCodes , open(fileOut, 'w') as bibsOut:
        csvOut = csv.writer(bibsOut, quoting=csv.QUOTE_NONNUMERIC)
        csvOut.writerow(['ISBN','code1','code2'])
        bList = codesList(cabCodes) #Returns a de-duped list
        lCodes = bList.listed()
        results = search(lCodes) # look them all up, return worldcat bib data 
        print('Found {} matches'.format(len(results)))
        for row in results: # write the resutls to a csv file
            csvOut.writerow(row) 
        print 'The file {} is complete.'.format(fileOut)
