+--------------------------------------------------------------+
|                        README                                |
|--------------------------------------------------------------|
|                                                              |
| AUTHOR:  Tahir Khan <tkhan9@gmu.edu>                         |
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
|Sample command lines:                                         |
|  python3.2 frag.py -v /dev/sdb1 -f sample.txt -n 3           |
|  python3.2 frag.py -v /dev/sdb1 -f sample.txt -n 3 -d 2      |
|  python3.2 frag.py -v fat32.dd -f sample.txt -n 3            |
|                                                              |
|Conditions:                                                   |
|  Only works on linux.                                        |
|  Minimum file length based on sector size and byte/sec       |
|  No long filenames                                           |
|  Datetime Stamps do not function 100% correctly              |
|  Files are only written in the root directory                |
|  Attributes not supported                                    |
|  Python 3.3.2 required                                       |
|  Filenames occasionally have a space in them                 |
|                                                              |
|Tested with:                                                  |
| 128 Thumb drive                                              |
| 1.5 Gb Thumb drive                                           |
| 128/256/512MB dd images made with mkdosfs                    |
| file: readme.txt                                             |
| file: hexedit.exe                                            |
| file: sample.txt                                             |
|                                                              |
|Verified with:                                                |
| fsstat                                                       |
|                                                              |
+--------------------------------------------------------------+