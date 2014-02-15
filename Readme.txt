+--------------------------------------------------------------+
|                        README                                |
|--------------------------------------------------------------|
|                                                              |
| AUTHOR:  Tahir Khan <tkhan9@gmu.edu                          |
| DATE:    10FEB2014                                           |
| VERSION: 1.0                                                 |
| LANG:    PYTHON                                              |
| VERSION: 3.3.2                                               |
| CLASS:   ISA785                                              |
| PROF:    Dr. Avinash Srinivasan                              |
|                                                              |
+--------------------------------------------------------------+

+--------------------------------------------------------------+
|                                                              |
|  Program is executed with by running python frag.py          |
|  Required:                                                   |
|   -f/--file    The file to fragment in the FAT               |
|   -n/--number  The amount of fragments to be created         |
|   -v/--volume  The volume to write to (Must be FAT32)        |
|   -d/--debug   The level of debugging                        |
|                                                              |
|                                                              |
|Conditions:                                                   |
|  Only works on linux.                                        |
|  Minimum file length based on sector size and byte/sec       |
|  No long filenames                                           |
|  Datetime Stamps do not function 100% correctly              |
|  Files are only written in the root directory                |
|  Check for duplicate filenames is not performed              |
|  Attributes not supported                                    |
|  Python 3.3.2 required                                       |
|                                                              |
|Tested with:                                                  |
| 128 Thumb drive                                              |
| 128/256/512MB dd images made with mkdosfs                    |
| file: readme.txt                                             |
| file: hexedit.exe                                            |
|                                                              |
|Verified with:                                                |
| fsstat                                                       |
|                                                              |
+--------------------------------------------------------------+