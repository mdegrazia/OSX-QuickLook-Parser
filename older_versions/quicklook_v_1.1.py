#Quicklook parser
#Author: Mari DeGrazia
#http://az4n6.blogspot.com/
#arizona4n6@gmail.com
#
#This will parse the Mac quicklook database which holds metadata for viewed thumbnails in the Mac Finder
#This includes parsing out the embedded plist file in the version field
#
#usage: quicklook.py -f index.sqlite >> output.tsv
#
#To read all about the QuickLook artifact, read the white paper by Sara Newcomer: 
#iacis.org/iis/2014/10_iis_2014_421-430.pdf
#
#SQL query based off of blog post from Dave: 
#http://www.easymetadata.com/2015/01/sqlite-analysing-the-quicklook-database-in-macos/
#
#This program requires that the biplist library be installed
# Easyinstall can be used to install it:
# Linux -> sudo easy_install biplist
# 
# Windows -> Windows box, you can install the setup tools from python.org which contain easy_install. 
#            It will place easy_install.exe into your python directory in the scripts folder. 
#            To get biplist, just change into the scripts directory and run easy_install biplist.
#
#This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You can view the GNU General Public License at <http://www.gnu.org/licenses/>
#
# Version History:
# v1.0 5/15/2016
# v1.1 5/17/2016 added in the row_id and fs_id to the output
#
#usage:
#quicklook.py index.sqlite >> output.tsv


import argparse
import sqlite3 as lite
import datetime
import os

try:
	from biplist import *
except:
	print "This script requires that the biplist library be installed"
	print "Try sudo easy_install biplist"
	print "Or on Windows use the setup tools from python.org which contains easy_install."
	exit()

parser =  argparse.ArgumentParser(description='This will parse the quicklook index.sqlite db')
parser.add_argument('-f', '--file', dest="database",help="Path to index.sqlite file",required=True)
args = parser.parse_args()
db=args.database

#convert mac absolute time (seconds from 1/1/2001) to human readable
def convert_absolute(mac_absolute_time):
    try:
        bmd = datetime.datetime(2001,1,1,0,0,0)
        humantime = bmd + datetime.timedelta(0,mac_absolute_time)  
    except:
        return("Error on conversion")
    return(humantime)

con = lite.connect(db)

with con:	
	cur = con.cursor()
	
	#SQL syntax taken from #http://www.easymetadata.com/2015/01/sqlite-analysing-the-quicklook-database-in-macos/ and modified to show converted timestamp in UTC
	sql = "select distinct f_rowid,k.folder,k.file_name,k.version,t.hit_count,t.last_hit_date, datetime(t.last_hit_date + strftime('%s', '2001-01-01 00:00:00'), 'unixepoch') As [decoded-last_hit_date],fs_id from (select rowid as f_rowid,folder,file_name,fs_id,version from files) k left join thumbnails t on t.file_id = k.f_rowid order by t.hit_count DESC"
	cur.execute(sql)
	try:
		cur.execute(sql)
	except:
		print "Error executing SQL. May not be a valid sqlite database, or may not contain the proper fields."
		print "Error may also occur with older versions of sqlite.dll on Windows. Update instructions here: https://deshmukhsuraj.wordpress.com/2015/02/07/windows-python-users-update-your-sqlite3/ "
		exit()
	
	rows = cur.fetchall()
	
	print "File Row ID\tFolder\tFilename\tHit Count\tLast Hit Date\tDecoded Hit Date (UTC)\tFS ID\tVersion"
	
	for row in rows:
		version_string = ""
		
		#create a temp file and extract the plist blob out into the temp file
		filename = "temp.plist"
		with open(filename, 'wb') as output_file:
			output_file.write(row[3])
		
		#use the plist library to read in the plist file
		plist= readPlist(filename)
		
		#read in all the key values in the plist file
		for key,value in plist.iteritems():
			
			if key == "date":
				converted_date =  convert_absolute(value) 
				version_string = "Raw date:" + str(value) + ", Converted Date (UTC): " + str(converted_date)
			else: 
				version_string =  version_string + "," + str(key) + ": " + str(value)
				
		#remove temp plist file
		try:
			os.remove(filename)
		except:
			print "Error removing temp file"
		
		#print row
		#print str(row[0]) + "\t" + row[1].encode('ascii','ignore') + "\t" + row[2].encode('ascii','ignore') + "\t" + str(row[4]) + "\t" + str(row[5]) + "\t" + str(row[6]) + + "\t" + str(row[7]) + "\t" + str(version_string)
		print str(row[0]) +  "\t" + row[1].encode('ascii','ignore') + "\t" + row[2].encode('ascii','ignore') + "\t" + str(row[4]) + "\t" + str(row[5]) + "\t" + str(row[6]) + "\t" + str(row[7]) + "\t" + str(version_string)
	