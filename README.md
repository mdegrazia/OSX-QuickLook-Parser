# OSX-QuickLook-Parser
Parse the Mac Quicklook index.sqlite database

This script will parse the Mac / OSX QuickLook index.sqlite database. This database contains information about thumbnails that have been generated on a Mac. This includes information like the file path to the original file, a hit count, the last date and time the thumbnail was accessed, the original file size and last modified date of the original file.
While an SQL query works for most of the data, there is a "version" field that contains a BLOB. This BLOB conatinas a binary plist file with additional data. This script parses out this BLOB data in addtion to the other fields.  

Required libraries for the python script: biplist - which can be installed using sudo easy_install biplist

Usage:

quicklook.py -f index.sqlite >> output.tsv

