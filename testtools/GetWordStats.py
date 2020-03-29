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
	print('    Current Locking Statistics for \'' + str(sys.argv[1]) + '\'')
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

def wordstats(word):
	cursor = db.cursor()
	try:
		cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
		sql = """SELECT locked, seen, 100*locked/seen as rate
			FROM words
			WHERE word = %s
			ORDER BY rate DESC"""
		cursor.execute(sql, [word])
		subrows = cursor.fetchall()
		#print results
		if len(subrows) == 0:
			print("    No results found.")
		for row in subrows:
			lock = str(row[0]) + "     "
			lock = lock[:5]
			tot = str(row[1]) + "     "
			tot = tot[:5]
			rate = str(row[2]) + "     "
			rate = rate[:4] + "%"
			print("    Times seen  : " + tot)
			print("    Times locked: " + lock)
			print("    Lock rate   : " + rate)
	except MySQLdb.Error as e:
		db.rollback()
		print("Database Error (wordstats)")
	cursor.close()

def subwordstats(word):
	cursor = db.cursor()
	try:
		cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
		sql = """SELECT subreddit, locked, seen, 100*locked/seen as rate
			FROM subwords
			WHERE word = %s
			ORDER BY rate DESC, seen DESC
			LIMIT 10"""
		cursor.execute(sql, [word])
		subrows = cursor.fetchall()
		#print results
		if len(subrows) > 0:
			print("    ")
			print("    Top 10 Highest Lock Rates by Subreddit")
			print("    +-------------------+-------+-------+-------+")
			print("    | SUBREDDIT         | LOCKD | TOTAL | %RATE |")
			print("    +-------------------+-------+-------+-------+")
			for row in subrows:
				sub = row[0] + "                 "
				sub = sub[:17]
				lock = str(row[1]) + "     "
				lock = lock[:5]
				tot = str(row[2]) + "     "
				tot = tot[:5]
				rate = str(row[3]) + "     "
				rate = rate[:4] + "%"
				print("    | " + sub + " | " + lock + " | " + tot + " | " + rate + " |")
			print("    +-------------------+-------+-------+-------+")
	except MySQLdb.Error as e:
		db.rollback()
		print("Database Error (word)")
	cursor.close()

def recentThreads(word):
	cursor = db.cursor()
	try:
		cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
		sql = """SELECT title, user, firstseen, f.id, l.firstlocked AS locktime
			FROM frontpage_history f
			JOIN locked_post l ON l.id = f.id
			WHERE title like %s
			ORDER BY firstseen DESC
			LIMIT 5"""
		cursor.execute(sql, (['%' + word + '%']))
		subrows = cursor.fetchall()
		#print results
		if len(subrows) > 0:
			print("    ")
			print("    5 most recent locked threads containing '" + word + '\':')
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
