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
	print(" ")
	print('    Current Locking Statistics for r/' + str(sys.argv[1]))
	#Word
	wordstats(str(sys.argv[1]))
	#Word by Sub
	subwordstats(str(sys.argv[1]))
	#recent threads
	recentThreads(str(sys.argv[1]))
	exit(0)

def open_database(): #connect to db to log data on posts
	global db
	db = MySQLdb.connect('localhost', config.dbUsername, config.dbPassword, 'commentunlock')

def wordstats(sub):
	cursor = db.cursor()
	try:
		cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
		sql = """SELECT SUM(CASE WHEN l.id IS NOT NULL THEN 1 ELSE 0 END) as locked,
			COUNT(*) as tot,
			100*SUM(CASE WHEN l.id IS NOT NULL THEN 1 ELSE 0 END)/COUNT(*) as rate
			FROM frontpage_history f
			LEFT JOIN locked_post l ON l.id = f.id
			WHERE subreddit = %s"""
		cursor.execute(sql, [sub])
		subrows = cursor.fetchall()
		#print results
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
				print("    No frontpage data on this subreddit.")
	except MySQLdb.Error as e:
		db.rollback()
		print("Database Error (word)")
	cursor.close()

def subwordstats(sub):
	cursor = db.cursor()
	try:
		cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
		sql = """SELECT word, locked, seen, 100*locked/seen as rate
			FROM subwords
			WHERE subreddit = %s AND seen >= 3 AND locked > 0
			AND word NOT IN (SELECT word FROM stopwords)
			ORDER BY rate DESC, seen DESC
			LIMIT 10"""
		cursor.execute(sql, [sub])
		subrows = cursor.fetchall()
		#print results
		if len(subrows) > 0:
			print("    ")
			print("    Top 10 Highest Locked Words on r/" + str(sys.argv[1]))
			print("    (seen at least 3 times, excludes stopwords):")
			print("    +-------------------+-------+-------+-------+")
			print("    | WORD              | LOCKD | TOTAL | %RATE |")
			print("    +-------------------+-------+-------+-------+")
			for row in subrows:
				word = row[0] + "                 "
				word = word[:17]
				lock = str(row[1]) + "     "
				lock = lock[:5]
				tot = str(row[2]) + "     "
				tot = tot[:5]
				rate = str(row[3]) + "     "
				rate = rate[:4] + "%"
				print("    | " + word + " | " + lock + " | " + tot + " | " + rate + " |")
			print("    +-------------------+-------+-------+-------+")
	except MySQLdb.Error as e:
		db.rollback()
		print("Database Error (subwordstats)")
	cursor.close()
	
def recentThreads(sub):
	cursor = db.cursor()
	try:
		cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
		sql = """SELECT title, user, firstseen, f.id,
			l.firstlocked AS locktime
			FROM frontpage_history f
			JOIN locked_post l ON l.id = f.id
			WHERE subreddit = %s
			ORDER BY firstseen DESC
			LIMIT 5"""
		cursor.execute(sql, ([sub]))
		subrows = cursor.fetchall()
		#print results
		if len(subrows) > 0:
			print("    ")
			print("    5 most recent locked threads on r/" + str(sys.argv[1]))
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
