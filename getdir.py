import os
import sys
import requests
from cb import sensorhandler 

class exfildir(object):
    def __init__(self, path, computername): 
        if "\\" not in path and not "/" in path:
            self.return_path_error(path)

        self.path = r'%s' % path
        self.computername = computername

        self.sensorhandler = sensorhandler()
        sensordata = self.sensorhandler.get_sensordata(self.computername)
        self.session = self.sensorhandler.find_session(sensordata)

    # Local saves
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

    def exfilfile(self, session_id, commanddata):
        urlpath = "/api/v1/cblr/session/%d/file/%d/content" % (session_id, commanddata["file_id"])

        raw_filedata = requests.get(
            "%s%s" % (self.sensorhandler.url, urlpath), 
            headers=self.sensorhandler.header, 
            stream=True,
            verify=False
        )

        if "\\" in self.path:
            filename = self.path.split("\\")[-1]
        elif "/" in self.path:
            filename = self.path.split("/")[-1]

        with open(filename, 'wb') as handle:
            for block in raw_filedata.iter_content(1024):
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
            commanddata = self.run_new_command(self.session, curobject=directories[0])
            previousfolder = directories[0]
            rootname = previousfolder.split("\\")[-2]
                
            for item in commanddata["files"]:
                if item["filename"] in whitelist:
                    continue

                # Something like this has to be done for files as well GAHH
                if item["attributes"][0] == "DIRECTORY":
                    directories.append("%s%s\\" % (previousfolder, item["filename"]))
                    foldername = ("%s%s\\" % ("/".join(previousfolder.split("\\")[cnt:]), item["filename"]))[:-1]
                    self.create_folder("data/%s/%s" % (self.computername, foldername))

            try:
                directories.remove(previousfolder)
            except ValueError:
                pass

    # Requires an active session
    def grab_file_from_session(self, session):
        curid = session["id"]
        sys.stdout.write("\nAttempting to grabfile from \n")

        # First attempts directory listing to check filetype
        commanddata = self.run_new_command(session, curobject=self.path)

        # LOOL
        if commanddata:
            if len(commanddata["files"]) < 2:
                if commanddata["files"][0]["attributes"][0] == "ARCHIVE":
                    new_commanddata = self.run_new_command(\
                        session, command="get file", curobject=self.path)
                    self.exfilfile(curid, new_commanddata)
                elif commanddata["files"][0]["attributes"][0] == "DIRECTORY":
                    print "Appending \\ to path as its identified as a folder."
                    self.path += "\\"

            self.recurse_folders(commanddata)

        else:
            sys.stdout.write("Something wrong with commanddata return value :)\n")
            exit()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.stdout.write("Usage: python getfile.py <filepath> <computername>\n")
        exit()

    path = sys.argv[1]
    computername = sys.argv[2]

    grabber = exfildir(path, computername)
    grabber.grab_file_from_session(grabber.session)