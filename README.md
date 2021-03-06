# Carbon black
Used for grabbing data from hosts. It has not been tested thoroughly and the output isn't too good, so errors aren't unexpected.

API reference:<br>
https://developer.carbonblack.com/reference/enterprise-response/5.1/rest-api/

# Usage:
First: Create a file called config.py and fill in the blanks:<br>

```python
url=""
api_key=""
```

* exfil.py <path> <computername>
* memdump.py <computername>
* hunt.py <computername>

# Todo
* [DONE] Create baseline session
* [DONE] Exfil data 
* [DONE] Memdump machine and extract to local folder
* [!] Have a folderchange mechanism in exfil.py that removes "NOT\_CONTENT\_INDEXED" attribute
* [!] Differentiate between unix and windows hosts in scripts.
* [!] Do _some_ automatic hunting
* [!] Live memory analysis

## cb.py - API handler
Used to create sessions to the computername<br>

Add this to your constructor and you have a working session in self.session:<br>

```python
from cb import sensorhandler
self.sensorhandler = sensorhandler()
self.session = self.sensorhandler.find_session(self.sensorhandler.get_sensordata(computername))
```

## exfil.py - Exfiltrate file or folder(s)
MIGHT be buggy on some workstations
Takes argument of a path (directory/file) and exports it to your local machine. There is no failcheck to see if the directory is big, so be careful with this one. If the directory doesn't exist it will give an error.

ISSUE:<br>
Some folders might have the "NOT_CONTENT_INDEXED" attribute, which makes the script unable to grab the data.

## memdump.py - memdump with cbsensor 
Takes an argument of a machine, memdumps if there is enough room followed by downloading locally and deleting the memdump on the remote machine.<br>

Something to remember here:<br>
* Memdumps can be 2x the size of memory
* When using compression it takes a long ass time. If computer is local it might be faster to just transfer the file. (Up to 32gb+ for clients)

## hunt.py - Kansa and Powershell implementation
This is a project made after finding the Kansa project. I will try to implement solutions for using powershell through python with the carbon black API. Memdump.py already has an example implementation of this, so its mostly going to be about finding the best way of doing the analysis and datatransfer. 

* Should include analysis 
* Focus on prefetch and MFT first
