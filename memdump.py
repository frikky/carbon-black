#!/usr/bin/python

import os
import sys
import time
import requests
from cb import sensorhandler 

class dumpmemory(object):
    def __init__(self, computername): 
        self.computername = computername

        self.sensorhandler = sensorhandler()
        sensordata = self.sensorhandler.get_sensordata(self.computername)
        self.session = self.sensorhandler.find_session(sensordata)

    # Returns whether there is enough diskspace to do a memdump. 
    # Based on: diskspace > (memory*2+5gb~)
    def check_diskspace(self, username):
        # Only works for windows (powershell)
        # FIX - Remove hardcoded stuff path and add unix stuff. Might also need to check other disks
        
        # This command measures remaining disk space and max memory size
        powershell = "powershell.exe \"(gwmi win32_logicaldisk | Where-Object {$_.DeviceID -eq \'C:\'}).freespace; (gwmi win32_physicalmemory | Measure Capacity -Sum).sum\""

        output_file = "C:\Users\\%s\AppData\Local\\temp\\cbdata.txt" % username
            
        powershellret = self.start_new_process(self.session, \
            command="create process", curobject=powershell, output_file=output_file)

        # Replaces the file location in case of errors
        if powershellret["status"] == "complete":
            output_file = powershellret["output_file"]
        else:
            exit()

        # Waits for file to be fully created
        time.sleep(2)

        # Grabs the filedata (e.g. file_id)
        fileret = self.start_new_process(
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

        # Deletes the file
        self.start_new_process(
            self.session, 
            command="delete file", 
            curobject=output_file
        )

        # Finds the values saved
        filesplit = filedata.split("\n")
        
        # Disk might be stupid big
        diskspace = long(filesplit[0][:-1])
        memory = int(filesplit[1][:-1])
        
        # Change diskspaceoffset (~5gb right now)
        sizeoffset = 5000000000

        if (diskspace-(memory*2)) < sizeoffset:
            print "Might not be enough space on disk. Only %d left, but memory is %d" \
                % (diskspace, memory)
            return False
            
        return True

    # Gets the actual memory
    def get_memory(self, username):
        output_location = "C:\Users\\%s\AppData\Local\\temp\\" % username

        #Runs the memdump process
        fileret = self.start_new_process(
            self.session, 
            command="memdump", 
            curobject=output_location,
            compress="true"
        )

        print fileret
        
        """
        Response Object

        return_code: return code of the memory dump process
        compressing: boolean flag indicating if compression is enabled
        complete: boolean flag indicating if memory dump is completed
        percentdone: percent of the process completed
        dumping: boolean flag indicating if memory dump is in progress
        """


        # Returns the data in the file

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

    # Runs commands on the Carbon black endpoint
    def start_new_process(self, session, command="create process", \
        curobject="", wait="", output_file="", compress=""):

        curid = session["id"]
        urlpath = "/api/v1/cblr/session/%s/command" % curid

        data = {"session_id": curid, "name": command, "object": curobject}
        print "Running command \'%s\' with argument %s" % \
            (command, curobject)

        # Appends stuff
        if output_file:
            data["output_file"] = output_file
        if wait:
            data["wait"] = wait
        if compress:
            data["compress"] = compress

        # Attaches to a running session and runs the command above
        ret = requests.post(
            "%s%s" % (self.sensorhandler.url, urlpath), 
            json=data, 
            headers=self.sensorhandler.header, 
            verify=False
        )

        # Should never happen, but its too be sure
        if not ret.status_code == 200:
            sys.stdout.write("Couldn't connect to the endpoint. Raw error:\n")
            print ret.text
            exit()

        # Verifies if the command is finished or not.
        commanddata = ""
        while(1):
            urlpath = "/api/v1/cblr/session/%s/command/%d" % (curid, ret.json()["id"])
            commandret = requests.get(
                "%s%s" % (self.sensorhandler.url, urlpath), 
                headers=self.sensorhandler.header, 
                verify=False
            )

            if commandret.json()["status"] == "error":
                print "An error occurred while issuing the command. Raw:\n%s" % commandret.json()
                exit()

            if commandret.json()["status"] == "complete":
                commanddata = commandret.json()
                break    

            sys.stdout.write("Command not finished, waiting 5 seconds.\n")
            sys.stdout.write("If this continues for more than 30 seconds there might be a session issue.\n")
            time.sleep(5)

        return commanddata

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.stdout.write("Usage: ./memdump <computername>\n")
        exit()

    computername = sys.argv[1]
    dump = dumpmemory(computername)

    # Hardcoded for now
    username = "User"
    diskcheck = dump.check_diskspace(username)
    if not diskcheck:
        exit()

    memdumpcheck = dump.get_memory(username)
