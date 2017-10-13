# Carbon black
Used for grabbing data from hosts. It has not been tested thoroughly and the output isn't too good, so errors aren't unexpected.

# Usage:
* exfil.py <path> <computername>

# cb.py
Used to create sessions to the computername<br>

Add this to your constructor and you have a working session in self.session:<br>

```python
self.sensorhandler = sensorhandler()
self.session = self.sensorhandler.find_session(self.sensorhandler.get_sensordata(computername))
```

# exfil.py 
Takes argument of a path (directory/file) and exports it. There is no failcheck to see if the directory is big, so be careful with this one. If the directory doesn't exist it will give an error.
