#Display Current Locking Statistics
#A set of queries by fanboat
#reddit.com/r/commentunlock
#fanboat.co, fanboat@gmail.com
#2018-12-06

import config
import time
import datetime
import MySQLdb
import sys
from urllib.error import HTTPError
import re

def main():
	#installdb() #Uncomment to install database on first run
	open_database()
	now = datetime.datetime.now()
	print("    ")
	print('    Current Locking Statistics for \'' + str(sys.argv[2]) + '\' on r/' + str(sys.argv[1]))
	#Word
	subwordstats(str(sys.argv[1]), str(sys.argv[2]))
	#Word by Sub
	recentThreads(str(sys.argv[1]),str(sys.argv[2]))
	exit(0)

def open_database(): #connect to db to log data on posts
	global db
	db = MySQLdb.connect('localhost', config.dbUsername, config.dbPassword, 'commentunlock')

def subwordstats(sub, word):
	cursor = db.cursor()
	try:
		cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
		sql = """SELECT locked, seen, 100*locked/seen as rate
			FROM subwords
			WHERE subreddit = %s AND word = %s"""
		cursor.execute(sql, ([sub],[word]))
		subrows = cursor.fetchall()
		#print results
		if len(subrows) > 0:
			for row in subrows:
				lock = str(row[0]) + "     "
				lock = lock[:5]
				tot = str(row[1]) + "     "
				tot = tot[:5]
				rate = str(row[2]) + "     "
				rate = rate[:4] + "%"
				if row[1] > 0:
					print("    Times seen  : " + tot)
					print("    Times locked: " + lock)
					print("    Lock rate   : " + rate)
				else:
					print("    No frontpage data for this subreddit and word.")
		else:
			print("    No frontpage data for this subreddit and word.")
	except MySQLdb.Error as e:
		db.rollback()
		print("Database Error (subwordstats)")
	cursor.close()

def recentThreads(sub, word):
	cursor = db.cursor()
	try:
		cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
		sql = """SELECT title, user, firstseen, f.id,
			CASE WHEN firstlocked IS NOT NULL THEN firstlocked ELSE 'Not Locked' END AS locktime
			FROM frontpage_history f
			LEFT JOIN locked_post l ON l.id = f.id
			WHERE subreddit = %s AND title like %s
			ORDER BY firstseen DESC
			LIMIT 5"""
		cursor.execute(sql, ([sub],['%' + word + '%']))
		subrows = cursor.fetchall()
		#print results
		if len(subrows) > 0:
			print("    ")
			print("    5 most recent threads on r/" + str(sys.argv[1]))
			print('    containing \'' + str(sys.argv[2]) + '\':')
			print("    +--------+--------------------------------------------+---------------------+---------------------+")
			print("    | ID     | TITLE                                      | FIRST SEEN          | FIRST LOCKED        |")
			print("    +--------+--------------------------------------------+---------------------+---------------------+")
			for row in subrows:
				title = row[0] + "                                                             "
				title = title[:42]
				#user = str(row[1]) + "                         "
				#user = user[:13]
				firstseen = str(row[2]) + "           "
				firstseen = firstseen[:19]
				id = str(row[3]) + "      "
				id = id[:6]
				firstlocked = str(row[4]) + "           "
				firstlocked = firstlocked[:19]
				print("    | " + id + " | " + title + " | " + firstseen + " | " + firstlocked + " |")
			print("    +--------+--------------------------------------------+---------------------+---------------------+")
	except MySQLdb.Error as e:
		db.rollback()
		print("Database Error (recentThreads)")
	cursor.close()

if __name__ == '__main__':
	main()
