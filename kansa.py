import os
import cb
import zipfile 
import requests
import argparse 
from shutil import copy, copytree, rmtree

parser = argparse.ArgumentParser("Kansa", description="Carbon Black parser for Kansa")

# Send target
parser.add_argument("-targetlist", default="", help="Add a targetlist")
#parser.add_argument("--TargetCount", help="Do stuff")
parser.add_argument("-target", default="", help="Add a target")
parser.add_argument("-ModulePath", default="", help="Add modules to be used")
parser.add_argument("-Pushbin", default=False, help="Push depencies")

class Kansa(object):
    def __init__(self): 
        self.args = parser.parse_args()
        self.targets = []
        self.modules = []

        print self.args

    def handle_arguments(self):
        targets = []
        if self.args.targetlist:
            if self.check_target_list():
                self.targets = open(self.args.targetlist, "r").read().splitlines()
            else:
                print "File \"%s\" doesn't exist" % self.args.targetlist
                exit()

        # Doesnt overwrite targetlist
        if self.args.target and not self.args.targetlist:
            self.targets.append(self.args.target)

        if self.args.ModulePath:
            for item in self.args.ModulePath.split(","):
                self.modules.append(item)

            print "\n".join(self.modules)

    # FIX - don't have stuff hardcoded :) - POC 
    def pack_target_data(self, foldername):
        if os.path.exists(foldername):
            rmtree(foldername)

        # Need executables and stuff
        os.mkdir(foldername)
        copy("kansa.ps1", "%s/%s" % (foldername, "kansa.ps1"))

        copytree("Modules", "%s/%s" % (foldername, "Modules"))

    def compress_target_data(self, foldername):
        folderzip = zipfile.ZipFile("%s.zip" % foldername, "w", zipfile.ZIP_DEFLATED)
        for root, dirs, files in os.walk(foldername):
            for file in files:
                folderzip.write(os.path.join(root, file))

        folderzip.close()
        return "%s.zip" % foldername

    def check_target_list(self):
        return os.path.exists(self.args.targetlist)

    def loop_targets(self, zipname):
        for target in self.targets:
            sensorhandler = cb.sensorhandler()
            sensordata = sensorhandler.get_sensordata(target)
            session = sensorhandler.find_session(sensordata)

            self.run_commands(sensorhandler, session, zipname)

    def upload_file(self, sensorhandler, session, fp):
        url = "%s/api/v1/cblr/session/%s/file" % (sensorhandler.url, session["id"])
        resp = requests.post(url, files={"file:": fp}, verify=False)
        return resp
        #return resp.get("id")

    # Crashes here somewhere
    def run_commands(self, sensorhandler, session, zipname):
        #with open(zipname, "rb") as tmp:
        with open("targets", "rb") as tmp:
            ret = self.upload_file(sensorhandler, session, tmp.read())
            print ret.status_code
            print ret.text
            print ret.url

        destpath = "C:\\temp\%s" % zipname

if __name__ == "__main__":
    kansa = Kansa()
    foldername = "targetdata"

    kansa.handle_arguments()

    kansa.pack_target_data(foldername)
    zipname = kansa.compress_target_data(foldername)

    kansa.loop_targets(zipname)
