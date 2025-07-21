# P5X_SubpackageBundleInfo_Extract
File data extractor for P5X Subpackages.  
  
Works on all SubpackageBundleInfo and SubpackageOptionalTagInfo.

## Simple Usage
- To json
```python
from subpackage import Subpackage

filename = "SubpackageBundleInfo.txt"
subpackage = Subpackage.read(filename)
subpackage.to_json("SubpackageBundleInfo.json")
```
- To enumerate all files
```python
from subpackage import Subpackage

filename = "SubpackageBundleInfo.txt"
subpackage = Subpackage.read(filename)

for map in subpackage.all_maps:
    for file in map.files:
        print(f"File: {file.filename}, Size: {file.filesize}, Offset: {file.file_offset}")
```

Note that I didn't implement download feature. You need to make it yourself!
