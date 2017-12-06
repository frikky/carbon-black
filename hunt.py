# This is an idea to use Kansa and Powerforensics to help forensic investigations through Carbon Black.
# Methodology is to send a command using base64, decoding it on the target, outputting using out-csv or similar, and getting the file > before getting it.

import sys
reload(sys)
sys.setdefaultencoding('utf-8')

import os
import io
import time
import base64
import requests
from cb import sensorhandler 

class hunting(object):
    def __init__(self, computername): 
        self.computername = computername
        self.directory = "C:\\temp\\"

        self.sensorhandler = sensorhandler()
        sensordata = self.sensorhandler.get_sensordata(self.computername)
        self.session = self.sensorhandler.find_session(sensordata)

    def get_module_base64(self, filepath): 
        return base64.b64encode(unicode(open(filepath, "r").read()))
        #return base64.b64encode(open(filepath, "r").read().encode('utf8'))

    def get_module(self, filepath):
        return open(filepath, "r").read() 

    # Doesn't save data, but returns it raw
    def read_data(self, session_id, commanddata, path):
        urlpath = "/api/v1/cblr/session/%d/file/%d/content" % (session_id, commanddata["file_id"])
        contentheader = self.sensorhandler.header
        contentheader["Content-Type"] = "text/plain"

        raw_filedata = requests.get(
            "%s%s" % (self.sensorhandler.url, urlpath), 
            headers=contentheader,
            stream=True,
            verify=False
        )

        data = ""
        for block in raw_filedata.iter_content(1024):
            data = data+block 

        return data 

    # FIX - Needs a lot of work here prolly :)
    # Current errors: unicode version e.g. utf8 unicode vs windows-western something  

    # Copies over the exe
    def appcompatcache(self): 
        pass
        

    def check_special_commands(self, commandname):
        print commandname[0]
        return {
            "Get-AppCompatCache": self.appcompatcache(),
        }.get(commandname, False)

    # Prolly hella slow compared to PS-Session or wmic
    def send_command(self, commandname, b64_command):
        self.check_special_commands(commandname.split("/")[-1:])
        exit()

        powershell = "C:\Windows\system32\WindowsPowerShell\\v1.0\powershell.exe"
        powershell_cmd = "%s -EncodedCommand %s" % (powershell, b64_command[:-1])
        #powershell = "powershell.exe \"(gwmi win32_logicaldisk | Where-Object {$_.DeviceID -eq \'C:\'}).freespace; (gwmi win32_physicalmemory | Measure Capacity -Sum).sum\""

        output_file = "%scbdata.txt" % self.directory

        powershellret = self.sensorhandler.start_new_process(self.session, \
            command="create process", curobject=powershell_cmd, output_file=output_file)

        print powershellret
        if powershellret["status"] == "complete":
            output_file = powershellret["output_file"]

        time.sleep(2)

        # Gets the file metadata
        fileret = self.sensorhandler.start_new_process(
            self.session, 
            command="get file", 
            curobject=output_file
        )

        # Returns the data in the file
        filedata = self.read_data(
            self.session["id"], 
            fileret, 
            output_file
        )

        time.sleep(2)

        self.sensorhandler.start_new_process(
            self.session, 
            command="delete file", 
            curobject=output_file
        )

        # This should in the testcase print the prefetchfiles available
        print filedata

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.stdout.write("Usage: ./hunt.py <computername>\n")
        exit()

    computername = sys.argv[1]

    hunt = hunting(computername)
    filename = "hunting/Get-PrefetchListing"
    # shimcache
    # appcompatcache
    # 
    huntdata = hunt.get_module(filename)
    hunt.send_command(filename, huntdata) 
