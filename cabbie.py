#! /usr/bin/python2.7
# get library catalog URL for a library and record
# You can provide more than one OCLC symbol in the request. Separate multiple values with a comma, for example:
# but we can't ask for all 50 at once...
# request format is:
# http://www.worldcat.org/webservices/catalog/content/libraries/15550774?oclcsymbol=OSU,STF&wskey=[key] 
# http://worldcat.org/devnet/wiki/SearchAPIDetails
#
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
%prog [inputfile] [outputfile]]
"""
lCodes=[]
# Set up the worldcat SRU request 
sru = SRURequest(wskey=WSKEY)
sru.args['servicelevel'] = SVCLVL
sru.url = 'http://www.worldcat.org/webservices/catalog/search/worldcat/sru'

class inputFile:
    def __init__(self, sInFileName):
        self.iname = sInFileName
    def opened(self):
        try:
            searchFile = open(self.iname,'r')
            return searchFile
        except:
            return "Badness"
        
class outputFile:
    def __init__(self,sOutFileName):
        self.iname = sOutFileName
    def opened(self):
      try:
        outFile = open(self.iname,'w')
        return outFile
      except:
            print "Unexpected error:", sys.exc_info()[0]
            raise

class codesList:
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
   for lCode in lCodes:
      numCodes +=1
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
    bf = inputFile(fileIn)
    rf = outputFile(fileOut)
    bfh = bf.opened()
    rfh = rf.opened()
    csvOut = csv.writer(rfh, quoting=csv.QUOTE_NONNUMERIC)
    csvOut.writerow(['ISBN','code1','code2'])
    bList = codesList(bfh) #Returns a de-duped list
    lCodes = bList.listed()
    results = search(lCodes)
    print('Found {} matches'.format(len(results)))
    for row in results:
       csvOut.writerow(row) 
    rfh.close()
    print 'The file {} is complete.'.format(fileOut)
