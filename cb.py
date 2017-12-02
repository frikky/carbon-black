import time
import sys
import requests
import config as cfg
from time import gmtime, strftime 

requests.packages.urllib3.disable_warnings(\
requests.packages.urllib3.exceptions.InsecureRequestWarning)

# FIX - Check out keepalive stuff

"""
Using the following in another file will give you an active session you can play with:

self.sensorhandler = sensorhandler()
sensordata = self.sensorhandler.get_sensordata(computername)
self.session = self.sensorhandler.find_session(sensordata)
"""

# Minor API for handling sessions etc
class sensorhandler(object):
    def __init__(self):
        self.url=cfg.url
        self.header = {
            "X-Auth-Token": cfg.api_key,
            "Content-Type": "application/json"
        }

    def get_time(self):
        return strftime("%H:%M:%S", gmtime())

    # Can be used to find old machines etc too
    def get_sensordata(self, computername):
        urlpath = "/api/v1/sensor?computer_name=%s" % computername
        ret = requests.get("%s%s" % (self.url, urlpath), headers=self.header, verify=False)

        if ret.ok and ret.status_code != 204:
            if len(ret.json()) > 2:
                sys.stdout.write("Found %d sensors for machine name %s\n" % (len(ret.json()), computername))
                exit()

            return ret.json()[0]
        else:
            sys.stdout.write("No sensor with machinename %s exists.\n" % computername)
            exit()

    # Waits for the pending session to become active
    def wait_for_session(self, session):
        sys.stdout.write("\nWaiting for session %d to become active.\n" % session["id"])
        urlpath = "/api/v1/cblr/session/%d?wait=True" % session["id"]

        # Reconnects every 5 second untill the pending session becomes active
        while(1):
            time.sleep(5)

            # Don't you die on me!
            try:
                ret = requests.get(
                    "%s%s" % (self.url, urlpath), 
                    headers=self.header, 
                    verify=False
                )
            except requests.exceptions.ConnectionError:
                print "CB unavailable for a moment. Retrying"
                continue

            if ret.json()["status"] == "active":
                break

        sys.stdout.write("\n")

    def create_new_session(self, sensordata):
        curid = sensordata["id"]
        sys.stdout.write("Creating new session for %s\n" % curid)
        urlpath = "/api/v1/cblr/session"
        data = {"sensor_id": curid}

        # Creates a new session
        ret = requests.post(
            "%s%s" % (self.url, urlpath), 
            json=data, 
            headers=self.header, 
            verify=False
        )

        if ret.status_code != 200:
            sys.stdout.write("COULD NOT CREATE NEW SESSION!!\n")
            exit()

        return ret.json()

    # Finds active or creates a new session
    def find_session(self, sensordata):
        sensorid = sensordata["id"]
        urlpath = "/api/v1/cblr/session"
        ret = requests.get("%s%s" % (self.url, urlpath), headers=self.header, verify=False)

        # First attempts to find an active session
        sessions = []
        if ret.ok:
            for item in ret.json():
                if item["hostname"] == sensordata["computer_name"]:
                    sessions.append(item) 

            # Attempts to find an active session
            cur_session = ""
            if sessions:
                # Finds an active or pending (unused) session
                for item in sessions:
                    if item["status"] == "active" or item["status"] == "pending":
                        cur_session = item
                        break

            # Creates an active session if it doesnt exist - might need FIX
            if not cur_session:
                sys.stdout.write("NO ACTIVE SESSION - CREATING!\n")
                cur_session = self.create_new_session(sensordata)

        # Waits for the session to become active before returning
        self.wait_for_session(cur_session)
        return cur_session
            
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
            "%s%s" % (self.url, urlpath), 
            json=data, 
            headers=self.header, 
            verify=False
        )

        #print ret.json()
        time.sleep(5)

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
                "%s%s" % (self.url, urlpath), 
                headers=self.header, 
                verify=False
            )
                
            # Exits if an error occurs. This means the command was injected badly.
            if commandret.json()["status"] == "error":
                print "%s: An error occurred while issuing the command. Raw:\n%s" % (self.get_time(), commandret.json())
                return False

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

