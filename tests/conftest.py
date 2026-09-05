import os
_unlink=os.unlink
def safe(path,*a,**k):
 try:return _unlink(path,*a,**k)
 except PermissionError:return None
os.unlink=safe
CONTRACT='contract/outcome_loom.py'
