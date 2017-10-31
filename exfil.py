#!/usr/bin/python

import os
import sys
import time
import requests
from cb import sensorhandler 

class exfildir(object):
    def __init__(self, path, computername): 
        # Fix - might be error here
        #if "\\" not in path and not "/" in path:
        #    self.return_path_error(path)

        self.path = r'%s' % path
        self.computername = computername

        self.sensorhandler = sensorhandler()
        sensordata = self.sensorhandler.get_sensordata(self.computername)
        self.session = self.sensorhandler.find_session(sensordata)

    # Local saves archive
    def save_archive_content(self, session):
        sys.stdout.write("\nGetting session archive data!")
        urlpath = "/api/v1/cblr/session/%d/archive" % session["id"]

        commandret = requests.get(
            "%s%s" % (self.sensorhandler.url, urlpath), 
            headers=self.sensorhandler.header, 
            stream=True,
            verify=False
        )

        with open('archive.tar.gz', 'wb') as handle:
            for block in commandret.iter_content(1024):
                handle.write(block)

    def return_path_error(self, path):
        sys.stdout.write("Path %s is not a valid path. Try using quotes.\n" % path)
        exit()

    # Creats 
    def create_multiple_folders(self, path):
        if not os.path.isdir(path):
            print "Creating path %s" % path
            os.makedirs(path) 

    def exfilfile(self, session_id, commanddata, path):
        # To verify if the folder exists
        self.create_multiple_folders(path)

        if isinstance(commanddata, bool):
            return False

        urlpath = "/api/v1/cblr/session/%d/file/%d/content" % (session_id, commanddata["file_id"])

        raw_filedata = requests.get(
            "%s%s" % (self.sensorhandler.url, urlpath), 
            headers=self.sensorhandler.header, 
            stream=True,
            verify=False
        )

        # Windows vs Linux?
        if "\\" in commanddata["object"]:
            filename = commanddata["object"].split("\\")[-1]
        elif "/" in commanddata["object"]:
            filename = commanddata["object"].split("/")[-1]

        with open("%s%s" % (path, filename), 'wb') as handle:
            for block in raw_filedata.iter_content(4096):
                handle.write(block)

    def run_new_command(self, session, command="directory list", curobject=""):
        curid = session["id"]
        urlpath = "/api/v1/cblr/session/%s/command" % curid

        data = {"session_id": curid, "name": command, "object": curobject}

        # Attaches to a running session and runs the command above
        ret = requests.post(
            "%s%s" % (self.sensorhandler.url, urlpath), 
            json=data, 
            headers=self.sensorhandler.header, 
            verify=False
        )

        # Should never happen, but its too be sure
        if not ret.status_code == 200:
            sys.stdout.write("Couldn't connect to the endpoint\n")
            exit()

        # Waits for the command to complete
        commanddata = ""
        while(1):
            urlpath = "/api/v1/cblr/session/%s/command/%d" % (curid, ret.json()["id"])
            commandret = requests.get(
                "%s%s" % (self.sensorhandler.url, urlpath), 
                headers=self.sensorhandler.header, 
                verify=False
            )

            if commandret.json()["status"] == "error":
                print commandret.json()
                print "The filepath most likely doesn't exist anymore."
                exit()

            if commandret.json()["status"] == "complete":
                commanddata = commandret.json()
                break    

            sys.stdout.write("Command not finished, waiting 5 seconds.\n")
            sys.stdout.write("If this continues for more than 30 seconds there might be a session issue.\n")
            time.sleep(5)

        return commanddata

    def create_folder(self, path):
        if not os.path.isdir(path):
            print "Creating %s" % path
            os.mkdir(path)

    # Attempts to download a folder etc. Recursive shit
    # Missing: FILE DOWNLOADS :O
    def recurse_folders(self, commanddata):
        # Sets up folder structure
        self.create_folder("data")
        self.create_folder("data/%s" % self.computername)
            
        rootpath = self.path
        whitelist = [".", ".."]
        directories = [rootpath]

        # This is dumb
        cnt = 0
        for item in rootpath.split("\\"):
            if item == rootpath.split("\\")[-2]:
                self.create_folder("data/%s/%s" % (self.computername, item))
                break

            cnt += 1

        # Create folder first?
        while(len(directories) > 0):
            commanddata = self.sensorhandler.start_new_process(self.session, command="directory list", curobject=directories[0])
            previousfolder = directories[0]
            rootname = previousfolder.split("\\")[-2]

            if isinstance(commanddata, bool):
                time.sleep(2)
                continue

            for item in commanddata["files"]:
                if item["filename"] in whitelist:
                    continue

                # Handles directories before files are downloaded.
                if item["attributes"][0] == "DIRECTORY":
                    directories.append("%s%s\\" % (previousfolder, item["filename"]))
                    foldername = ("%s%s\\" % ("/".join(previousfolder.split("\\")[cnt:]), item["filename"]))[:-1]
                    self.create_folder("data/%s/%s" % (self.computername, foldername))
                else:
                    # Handles individual files
                    foldername = ("%s" % ("/".join(previousfolder.split("\\")[cnt:])))#, item["filename"]))[:-1]
                    new_commanddata = self.sensorhandler.start_new_process(
                        self.session, 
                        command="get file", 
                        curobject="%s%s" % (previousfolder, item["filename"])
                    )

                    self.exfilfile(
                        self.session["id"], 
                        new_commanddata, 
                        "data/%s/%s" % (self.computername, foldername)
                    )

            try:
                directories.remove(previousfolder)
            except ValueError:
                pass

        localfilepath = "data/%s/%s" % (self.computername, rootpath.split("\\")[-2])
        print "\n[!] FINISHED! Folder saved to %s/%s" % (os.getcwd(), localfilepath)

    # Requires an active session
    def grab_file_from_session(self, session):
        curid = session["id"]
        sys.stdout.write("\nAttempting to grabfile from \n")

        # First attempts directory listing to check filetype
        commanddata = self.sensorhandler.start_new_process(session, command="directory list", curobject=self.path)

        if not commanddata:
            sys.stdout.write("Something wrong with initial commanddata return value :)\n")
            exit()

        if len(commanddata["files"]) < 2:
            # FIX - might not always be archive? idk what this means in CB setting
            print commanddata
            arguments = commanddata["files"][0]["attributes"]
            if "ARCHIVE" in arguments:
                new_commanddata = self.sensorhandler.start_new_process(\
                    session, 
                    command="get file", 
                    curobject=self.path
                )
                self.exfilfile(
                    curid, 
                    new_commanddata, 
                    "data/%s/singlefiles/" % self.computername
                )

                #localfilepath = "%s/singlefiles/%s" % (self.computername, new_commanddata["object"].split("\\")[-1]) 
                #print "File saved to %s/data/%s" % (os.getcwd(), localfilepath)
                return True
            elif commanddata["files"][0]["attributes"][0] == "DIRECTORY":
                print "Appending \\ to path as its identified as a folder."
                self.path += "\\"

        self.recurse_folders(commanddata)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.stdout.write("Usage: ./exfil <filepath> <computername>\n")
        exit()

    path = sys.argv[1]
    computername = sys.argv[2]

    grabber = exfildir(path, computername)
    grabber.grab_file_from_session(grabber.session)


