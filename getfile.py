import sys
import requests
from cb import sensorhandler 

class exfilfile(object):
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

    # Requires an active session
    def grab_file_from_session(self, session):
        sys.stdout.write("\nAttempting to grabfile from \n%s.\n" % session)

        curid = session["id"]
        urlpath = "/api/v1/cblr/session/%s/command" % curid

        data = {"session_id": curid, "name": "get file", "object": self.path}

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
                print "The file most likely doesn't exist anymore."
                exit()

            if commandret.json()["status"] == "complete":
                commanddata = commandret.json()
                break    

            sys.stdout.write("Command not finished, waiting 5 seconds.\n")
            sys.stdout.write("If this continues for more than 30 seconds there might be a session issue.\n")
            time.sleep(5)

        # Gets a file
        if commanddata:
            self.exfilfile(curid, commanddata)
        else:
            sys.stdout.write("Something wrong with commanddata return value :)\n")
            exit()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.stdout.write("Usage: python getfile.py <filepath> <computername>\n")
        exit()

    path = sys.argv[1]
    computername = sys.argv[2]

    grabber = exfilfile(path, computername)
    grabber.grab_file_from_session(grabber.session)
