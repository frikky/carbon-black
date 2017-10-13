import time
import sys
import requests
import config as cfg

requests.packages.urllib3.disable_warnings(\
requests.packages.urllib3.exceptions.InsecureRequestWarning)

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

    # Can be used to find old machines etc too
    def get_sensordata(self, computername):
        urlpath = "/api/v1/sensor?computer_name=%s" % computername
        ret = requests.get("%s%s" % (self.url, urlpath), headers=self.header, verify=False)

        if ret.ok and ret.status_code != 204:
            if len(ret.json()) > 1:
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
            ret = requests.get(
                "%s%s" % (self.url, urlpath), 
                headers=self.header, 
                verify=False
            )

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

            # Creates an active session if it doesnt exist - FIX
            if not cur_session:
                sys.stdout.write("NO ACTIVE SESSION - CREATING!\n")
                cur_session = self.create_new_session(sensordata)

        # Waits for the session to become active before returning
        self.wait_for_session(cur_session)
        return cur_session
            
        #self.grab_file_from_session(cur_session)


