#Quicklook parser
#Author: Mari DeGrazia
#http://az4n6.blogspot.com/
#arizona4n6@gmail.com
#
#This will parse the Mac quicklook database which holds metadata for viewed thumbnails in the Mac Finder
#This includes parsing out the embedded plist file in the version field as well as extracting thumbnails from the thumbnails.data folder
#
#To launch the GUI interface, run quicklook_parser.py with no command line arguments: 
#	python quicklook_parser.py
#
#Command line, run quicklook_parser.py with arguments:
#	python quicklook_parser.py -d "C:\com.apple.QuickLook.thumbnailcache" -o "C:\report_folder"
#
#To read all about the QuickLook artifact, read the white paper by Sara Newcomer: 
#iacis.org/iis/2014/10_iis_2014_421-430.pdf
#
#SQL query based off of blog post from Dave: 
#http://www.easymetadata.com/2015/01/sqlite-analysing-the-quicklook-database-in-macos/
#
#This program requires that the biplist and Pillow be installed
# Easyinstall can be used to install biplist
# Linux -> sudo easy_install biplist
# 
# Windows -> C:\Python27\Scripts\easy_install biplist
#
#
#This program requires that the Pillow be installed
# Easyinstall can be used to install biplist
# Linux -> sudo pip install Pillow
# 
# Windows -> C:\Python27\Scripts\pip install Pillow
#
#
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
# v2   9/21/2016 added in the ability to carve out the thumbnails
# v3   10/04/2016 added in GUI and excel formats
#usage:


from Tkinter import *
from tkFileDialog   import askopenfilename,asksaveasfilename,askdirectory
import tkMessageBox
import os
import ttk

import argparse
import sqlite3 as lite
import datetime
import os
import sys
import subprocess

try:
	from biplist import *
except:
	print "This script requires that the biplist library be installed"
	print "Try sudo easy_install biplist"
	print "Or on Windows C:\<PYTHONDIR>\script\easy_install.exe biplist."
	exit()
	
try:
	from PIL import Image
except:
	print "This script requires that the Pil Image library be installed"
	print "Try sudo pip install Pillow"
	print "Or on Windows use the pip in the C:\<PYTHONDIR>\scripts\pip.exe install Pillow"
	exit()
	
try:
	import xlsxwriter
	xlsxwriter_installed = True	
except:
	print "If you would like to generate an Excel report, the xlsxwriter library needs to be installed"
	print "Try easy_install xlsxwriter"
	print "Or on Windows C:\<PYTHONDIR>\script\easy_install.exe xlsxwriter"
	xlsxwriter_installed = False	

#convert mac absolute time (seconds from 1/1/2001) to human readable
def convert_absolute(mac_absolute_time):
    try:
        bmd = datetime.datetime(2001,1,1,0,0,0)
        humantime = bmd + datetime.timedelta(0,mac_absolute_time)  
    except:
        return("Error on conversion")
    return(humantime)

def get_parser():
	parser =  argparse.ArgumentParser(description='This will parse the quicklook index.sqlite db. Run without options to start GUI')
	parser.add_argument('-d', '--thumbcache_dir', dest="thumbcache_dir",help="com.apple.QuickLook.thumbnailcache folder")
	parser.add_argument('-o', '--output_folder', dest="output_folder",help="Full path to empty folder to hold report and thumbnails")
	parser.add_argument('-t', '--type', action='store', dest='out_format', default="tsv", choices=['excel', 'tab'], help='Output format, default to TSV')
		
	return parser
	
	
#run command line interface
def command_line(args):
	
	if args.output_folder is None:
		print "-o OUTPUT_FOLDER argument required"
		exit()
	if args.thumbcache_dir is None:
		print " -d THUMBCACHE_DIR argument required"
		exit()
		
	error = verify_files(args.thumbcache_dir)
	if error is not True:
		print error
		exit()
		
	
	stats = process_database(args.thumbcache_dir,args.output_folder,args.out_format)
	if stats[0] == "Error":
		print stats[1]
		exit()
		
	print "Processing Complete\nRecords in table: " + str(stats[0]) + "\n" + "Thumbnails available: " + str(stats[1]) + "\nThumbnails extracted: " + str(stats[2])
	
def verify_files(thumbcache_dir):

#check to see if it is a valid database file
	index = os.path.join(thumbcache_dir,"index.sqlite")
	thumbnails = os.path.join(thumbcache_dir,"thumbnails.data")
	
	if not os.path.exists(index):
		error = "Could not locate the index.sqlite file in the folder " + thumbcache_dir
		return error
	
	if not os.path.exists(thumbnails):
		error = "Could not locate the thumbnails.data file in the folder " + thumbcache_dir
		return error
	return True
	
def process_database(openfolder,savefolder,out_format):
	
	db = os.path.join(openfolder,"index.sqlite")
	thumbnails_data = os.path.join(openfolder,"thumbnails.data")
	
	try:
		thumbnails_file = open(thumbnails_data, 'rb')
	except:
		error = "Error opening " + thumbnails_data
		return ("Error",error)
	
	thumbnails_exported = 0
	
	if out_format != "excel":
		report = os.path.join(savefolder,"report.tsv")
		try:
			report_file = open(report,"w")
		except:
			error = "Error opening report to write to. Verify file is not already open."
			return ("Error",error)
	
	thumbnails_folder = os.path.join(savefolder,"thumbnails")
	if not os.path.exists(thumbnails_folder):
		os.makedirs(thumbnails_folder)
	
	error_log = os.path.join(savefolder,"error.log")
	try:
		el = open(error_log,'w')
	except:
		error = "Error opening log file to write to. Verify file is not already open."
		return ("Error",error)
	
	con = lite.connect(db)

	#get number of thumbnails:
	with con:
		cur=con.cursor()
		sql = "SELECT rowid from thumbnails"
		cur.execute(sql)
		try:
			cur.execute(sql)
		except:
			error = "Error executing SQL. May not be a valid sqlite database, or may not contain the proper fields.\nError may also occur with older versions of sqlite.dll on Windows. Update instructions here: https://deshmukhsuraj.wordpress.com/2015/02/07/windows-python-users-update-your-sqlite3/ "
			return("Error",error)
	
	rows = cur.fetchall()
	total_thumbnails = len(rows)
	
		
	with con:	
		cur = con.cursor()
		
		#SQL syntax taken/modified from #http://www.easymetadata.com/2015/01/sqlite-analysing-the-quicklook-database-in-macos/ and modified to show converted timestamp in UTC
		sql = "select distinct f_rowid,k.folder,k.file_name,k.version,t.hit_count,t.last_hit_date, t.bitsperpixel,t.bitmapdata_location,bitmapdata_length,t.width,t.height,datetime(t.last_hit_date + strftime('%s', '2001-01-01 00:00:00'), 'unixepoch') As [decoded-last_hit_date],fs_id from (select rowid as f_rowid,folder,file_name,fs_id,version from files) k left join thumbnails t on t.file_id = k.f_rowid order by t.hit_count DESC"
		cur.execute(sql)
		try:
			cur.execute(sql)
		except:
			error = "Error executing SQL. May not be a valid sqlite database, or may not contain the proper fields.\nError may also occur with older versions of sqlite.dll on Windows. Update instructions here: https://deshmukhsuraj.wordpress.com/2015/02/07/windows-python-users-update-your-sqlite3/ "
			return("Error",error)
					
		rows = cur.fetchall()
		total_rows = len(rows)
			
		if rows:
			
			total_rows = len(rows)
			
			
			if out_format == "excel":
				x_report = os.path.join(savefolder,"report.xlsx")
				workbook = xlsxwriter.Workbook(x_report)
				worksheet = workbook.add_worksheet()
								
				style_header = workbook.add_format({'bold': True})

				#write column headers
				worksheet.write(0,0,"File Row ID",style_header)
				worksheet.write(0,1,"Folder", style_header)
				worksheet.write(0,2,"Filename", style_header)
				worksheet.write(0,3, "Hit Count", style_header)
				worksheet.write(0,4, "Last Hit Date Raw", style_header)
				worksheet.write(0,5, "Last Hit Date (UTC)", style_header)
				worksheet.write(0,6, "Has thumbnail", style_header)
				worksheet.write(0,7, "Image",style_header)
				worksheet.write(0,8,"Original File Last Modified Raw",style_header)
				worksheet.write(0,9,"Original File Last Modified(UTC)",style_header)
				worksheet.write(0,10,"Original File Size",style_header)
				worksheet.write(0,11,"Generator",style_header)
				worksheet.write(0,12, "FS ID", style_header)
			
			else:
				report_file.write("File Row ID\tFolder\tFilename\tHit Count\tLast Hit Date\tLast Hit Date (UTC)\tHas thumbnail\tOriginal File Last Modified Raw\tOriginal File Last Modified(UTC)\tOriginal File Size\tGenerator\tFS ID\n")
			
			count = 0			
			for row in rows:
				rowid = row[0]
				folder = row[1]
				file_name = row[2]
				hit_count = row[4]
				last_hit_date = row[5]
				bitsperpixel = row[6]
				bitmapdata_location = row[7]
				bitmapdata_length = row[8]
				width = row[9]
				height = row[10]
				decoded_last_hit_date = row[11]
				fs_id = row[12]
				
				count = count + 1
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
						version_last_modified_raw = str(value)
						version_converted_date = str(converted_date)
						version_string = "Raw date:" + str(value) + ", Converted Date (UTC): " + str(converted_date)
					else: 
						version_string =  version_string + "," + str(key) + ": " + str(value)
						
						if "gen" in str(key):
							version_generator = str(value)
						if "size" in str(key):
							version_org_size = str(value)
						
				#remove temp plist file
				try:
					os.remove(filename)
				except:
					error = "Error removing temp file"
					return("Error",error)
					
					
				
				#run query for thumbnails. loop through and carve thumbnail for each image
				with con:
					cur=con.cursor()
					sql = "SELECT file_id,size,width,height,bitspercomponent,bitsperpixel,bytesperrow,bitmapdata_location,bitmapdata_length from thumbnails where file_id = " + str(rowid)
					cur.execute(sql)
					try:
						cur.execute(sql)
					except:
						el.write("Error on thumbnails data query for file id " + rowid)
						
				

				thumb_rows = cur.fetchall()
				
				if len(thumb_rows) == 0:
					has_thumbnail = "FALSE"
				else:	
					count_thumb = 0
					for thumb in thumb_rows:
						count_thumb = count_thumb + 1					
						if out_format == "excel":
							worksheet.write(count,6,"TRUE")
						else:
							has_thumbnail = "TRUE"
						
						try:	
							#now carve out raw bitmap
							
							bitspercomponent = thumb[4]
							bytesperrow = thumb[6]
							bitmapdata_location = thumb[7]
							bitmpatdata_length = thumb[8]
							
							#compute the width from the bytes per row as sometimes the width stored in database is funky
							width = bytesperrow / (bitsperpixel/bitspercomponent)
							
							x = width
							y = thumb[3]
							thumbnails_file.seek(bitmapdata_location)
							raw_bitmap = thumbnails_file.read(bitmpatdata_length)
							
							#copy out file
							
							png = os.path.join(thumbnails_folder,str(row[0]) + "." + row[2] + "_" + str(count_thumb) + ".png")
							if not os.path.exists(png):
							
								imgSize = (x,y)
								
								img = Image.frombytes('RGBA', imgSize, raw_bitmap, decoder_name='raw')
								img.save(png)
								thumbnails_exported = thumbnails_exported + 1
								if out_format == "excel":
															
									worksheet.insert_image(count, 7,png)
									
									#make the cell size as big as the biggest image
									if y <= 64:
										worksheet.set_row(count,64)
									else:	
										worksheet.set_row(count,y)
						
						
						except:
							el.write("Error with thumbnail for row id " + str(row[0]) + "\n")
				
				if out_format == "excel":
					
					worksheet.write(count,0,rowid)
					worksheet.write(count,1,folder.encode('ascii','ignore'))
					worksheet.write(count,2,file_name.encode('ascii','ignore'))
					worksheet.write(count,3,str(hit_count))
					worksheet.write(count,4,last_hit_date)
					worksheet.write(count,5,decoded_last_hit_date)
					worksheet.write(count,8,version_last_modified_raw)
					worksheet.write(count,9,version_converted_date)
					worksheet.write(count,10,version_org_size)
					worksheet.write(count,11,version_generator)
					worksheet.write(count,12,fs_id)
				
				else:				
					report_file.write(str(rowid) + "\t" + folder.encode('ascii','ignore')+ "\t" + file_name.encode('ascii','ignore')+ "\t" + str(hit_count)+ "\t" + str(last_hit_date) + "\t" + str(decoded_last_hit_date) + "\t"
					+  has_thumbnail + "\t" + version_last_modified_raw + "\t" + version_converted_date + "\t" + version_org_size + "\t" + version_generator + "\t" + fs_id + "\n")
				
	if out_format == "excel":
		workbook.close()
	else:
		report_file.close()
	el.close()
	
		
	return(total_rows,total_thumbnails,thumbnails_exported)

def gui():	
	
	def About():
			tkMessageBox.showinfo("About", "Quicklook Parser v.3\nMari DeGrazia\narizona4n6@gmail.com")
			
	def Help():
			tkMessageBox.showinfo("Help", 'This will parse the index.sqlite and thumbnails.data files from com.apple.QuickLook.thumbnailcache folder.\n\nSelect the com.apple.QuickLook.thumbnailcache folder, or a folder containing these files\n\nSelect an empty output folder. A report will be generated with the metadata for the thumbnails,and a subfolder named "thumbnails" will be created containg the thumbnail images.')
			
	def clear_textbox():
		ttk.e1.delete(0, END)
		ttk.e2.delete(0, END)



	def openfolder():
		
		folder1= askdirectory()
		ttk.e1.insert(10,folder1)
		
		#check to see if it is a valid database file
		
		error = verify_files(folder1)
		if error is not True:
			tkMessageBox.showinfo("Error", error)
			ttk.e1.insert(10,"")
			return False
	
	def savefolder():
		
		folder2= askdirectory()
		ttk.e2.insert(10,folder2)
			
	def process():
		master.config(cursor="watch")
		master.update()
		
		openfolder = ttk.e1.get()
		savefolder = ttk.e2.get()
		thisReportType = ReportType.get()
		if thisReportType == 1:
			out_format = "tab"
		else:
			out_format = "excel"
		
		
		stats = process_database(openfolder,savefolder,out_format)
		if stats[0] == "Error":
			tkMessageBox.showinfo("Error",stats[1])
			master.config(cursor="")
			master.update()
			return()
			

		master.config(cursor="")
		master.update()
		tkMessageBox.showinfo("Processing Complete","Records in table: " + str(stats[0]) + "\n" + "Thumbnails available: " + str(stats[1]) + "\nThumbnails extracted: " + str(stats[2]))
		if sys.platform == "win32":
			os.startfile(savefolder)
						
					
	master = Tk()
	master.wm_title("Quicklook Parser")
	script_path = os.path.dirname(sys.argv[0])
		
	icon_file=os.path.join("resources","qlook.ico")
	icon = os.path.join(script_path,icon_file)
	
	#only set icon for windows
	if 'nt' == os.name:
		if os.path.exists(icon):
			master.iconbitmap(icon)
					
	menu = Menu(master)
	master.config(menu=menu)
	helpmenu = Menu(menu)
	menu.add_cascade(label="Help", menu=helpmenu)
	helpmenu.add_command(label="About...", command=About)
	helpmenu.add_command(label="Instructions...", command=Help)

	#ttk.Label(master,justify=LEFT,text="Open QuickLook thumbnailcache folder:").grid(row=6,column=0,sticky=W)
	ttk.Button(text='Open thumbnailcache folder...',command=openfolder,width=30).grid(row=7,column=0,sticky=W)
	ttk.e1 = Entry(master,width=50)
	ttk.e1.grid(row=7, column=1,sticky=E)

	ttk.Button(text='Save Report and Thumbnails...',command=savefolder,width=30).grid(row=8,column=0,sticky=W)
	ttk.e2 = Entry(master,width=50)
	ttk.e2.grid(row=8, column=1,sticky=E)
	
	ReportType = IntVar()
	ReportType.set(1) 
	
	tsv_button = Radiobutton(master, text="TSV", variable=ReportType,value=1).grid(row=1, column=0, sticky=W)
	if xlsxwriter_installed is True:
		excel_button = Radiobutton(master, text="Excel", variable=ReportType,value=2).grid(row=2, column=0, sticky=W)
	else:
		excel_button = Radiobutton(master, text="Excel(Install xlsxwriter library)", variable=ReportType,value=2,state=DISABLED).grid(row=2, column=0, sticky=W)
	
	ttk.Button(text='Process', command=process,width=30).grid(row=11,column=0,sticky=W)

	ttk.Button(text='Clear', command=clear_textbox,width=30).grid(row=12,column=0,sticky=W)

	mainloop( )


	
if __name__ == "__main__":

	parser=get_parser()
	args=parser.parse_args()
	
	if args.thumbcache_dir or args.output_folder:
		command_line(args)
		
	else:
		gui()
