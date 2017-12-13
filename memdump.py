#!/usr/bin/python

import os
import sys
import time
import requests
from cb import sensorhandler 
from exfil import exfildir
from time import gmtime, strftime 

class dumpmemory(object):
    def __init__(self, computername): 
        self.computername = computername

        self.sensorhandler = sensorhandler()
        sensordata = self.sensorhandler.get_sensordata(self.computername)
        self.session = self.sensorhandler.find_session(sensordata)
        self.directory = "C:\\temp\\"

    def get_time(self):
        return strftime("%H:%M:%S", gmtime())

    # Returns whether there is enough diskspace to do a memdump. 
    # Based on: diskspace > (memory*2+5gb~)
    def check_diskspace(self):
        # Only works for windows (powershell)
        # FIX - Remove hardcoded stuff path and add unix stuff. Might also need to check other disks
        
        # This command measures remaining disk space and max memory size
        powershell = "powershell.exe \"(gwmi win32_logicaldisk | Where-Object {$_.DeviceID -eq \'C:\'}).freespace; (gwmi win32_physicalmemory | Measure Capacity -Sum).sum\""

        output_file = "%scbdata.txt" % self.directory
            
        powershellret = self.start_new_process(self.session, \
            command="create process", curobject=powershell, output_file=output_file)

        # Replaces the file location in case of errors
        if powershellret["status"] == "complete":
            output_file = powershellret["output_file"]
        else:
            exit()

        time.sleep(2)

        # Waits for file to be fully created
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

        time.sleep(2)

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
            print "%s: Might not be enough space on disk. Only %d left, but memory is %d" \
                % (self.get_time(), diskspace, memory)
            return False
            
        return True

    def create_multiple_folders(self, path):
        if not path.endswith("\\"): 
            path += "\\"

        if not os.path.isdir(path):
            print "%s: Creating path %s" % (self.get_time(), path)
            os.makedirs(path) 

    # Gets the actual memory
    def get_memory(self):
        output_location = "%smemdump.dmp" % self.directory
        compress_check=True

        #Runs the memdump process - This takes a while if compress_check is True
        fileret = self.start_new_process(
            self.session, 
            command="memdump", 
            curobject=output_location,
            compress=compress_check
        )

        try:
            if fileret.startswith("Command not supported"):
                print "%s: Sensor version is < 5.1 and cannot be executed properly." % self.get_time()
                exit()
        except AttributeError:
            pass

        # If compressing is done on the remote host, the original dump will be deleted.
            # Deletes the dump file 

        exfil = exfildir("", self.computername)

        if compress_check:
            output_location = output_location+".tgz"

        new_commanddata = self.start_new_process(\
            self.session, 
            command="get file", 
            curobject=output_location
        )

        exfil.exfilfile(
            self.session["id"], 
            new_commanddata, 
            "data/%s/dumpfile/" % self.computername
        )

        # Sleeps because errors with file deletion might occur while file is in use
        time.sleep(5)

        self.start_new_process(
            self.session, 
            command="delete file", 
            curobject=output_location
        )

        if compress_check:
            output_location = output_location[:-4]
            self.start_new_process(
                self.session, 
                command="delete file", 
                curobject=output_location
            )

        return True

        """
        Response Object

        return_code: return code of the memory dump process
        compressing: boolean flag indicating if compression is enabled
        complete: boolean flag indicating if memory dump is completed
        percentdone: percent of the process completed
        dumping: boolean flag indicating if memory dump is in progress
        """

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
        curobject="", wait="", output_file="", compress=True):

        curid = session["id"]
        urlpath = "/api/v1/cblr/session/%s/command" % curid

        data = {"session_id": curid, "name": command, "object": curobject}
        print "%s: Running command \'%s\' with argument %s" % \
            (self.get_time(), command, curobject)

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
            sys.stdout.write("%s: Couldn't connect to the endpoint. Raw error:\n%s" % (self.get_time(), ret.text))
            exit()

        # Verifies if the command is finished or not.
        commanddata = ""
        refreshcnt = 0
        while(1):
            # Creates a request to verify whether the command is finished or not
            urlpath = "/api/v1/cblr/session/%s/command/%d" % (curid, ret.json()["id"])
            commandret = requests.get(
                "%s%s" % (self.sensorhandler.url, urlpath), 
                headers=self.sensorhandler.header, 
                verify=False
            )
                
            # Exits if an error occurs. This means the command was injected badly.
            if commandret.json()["status"] == "error":
                # Errors in delete file..
                print "%s: An error occurred while issuing the command. Raw:\n%s" % (self.get_time(), commandret.json())
                exit()

            # Returns the commanddata if the command is finished
            if commandret.json()["status"] == "complete":
                commanddata = commandret.json()
                break    

            # Hardcoded for memdump
            # Should maybe give % finished?
            if command == "memdump" and compress: 
                if refreshcnt is 0:
                    sys.stdout.write("%s: Memdump takes a long time when compressing. Checking if complete every 60 seconds. Raw:\n%s\n" % (self.get_time(), commandret.json()))
                time.sleep(60)
            else:
                if refreshcnt is 0:
                    sys.stdout.write("%s: Checking whether the command is finished every 10 seconds. Raw: \n%s\n" % (self.get_time(), commandret.json()))
                time.sleep(10)

            refreshcnt += 1

            if refreshcnt > 10:
                refreshcnt = 0

        return commanddata

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.stdout.write("Usage: ./memdump <computername>\n")
        exit()

    computername = sys.argv[1]
    dump = dumpmemory(computername)

    diskcheck = dump.check_diskspace()
    if not diskcheck:
        exit()

    memdumpcheck = dump.get_memory()
    if memdumpcheck:
        print "Dump should now be available in the data/%s/dumpfile/ folder." % computername
    else:
        print "Something went wrong during memdump?"

