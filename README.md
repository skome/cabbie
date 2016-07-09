# cabbie
Search tools for Course Adopted Books at Claremont

##Usage
cabbie.py [input file] [output file]

Input file should consist of a list of single ISBN codes.  They can be 10 or 13 digit.

Output file will consist of a csv file containing bibliographic data for the ISBN codes. The Worldcat library(/ies) to search arre configurable. The MARC fields returned can be configured in cabbie.py

###To do: 
* output a csv file of bibliographic data for records NOT found in the Worldcat library symbol(s).
