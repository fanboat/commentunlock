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
	statTime = getStatTime()
	print(" ")
	print("    Current Locking Statistics from 2018-03-29 to " + str(statTime))
	genstats() #general overview stats
	substats() #subreddit stats
	#userstats() #user stats
	wordstats() #title word stats
	subwordstats() #title word stats by subreddit
	now = datetime.datetime.now()
	print("    Statistics complete at time: " + str(now))
	exit(0)

def open_database(): #connect to db to log data on posts
	global db
	db = MySQLdb.connect('localhost', config.dbUsername, config.dbPassword, 'commentunlock')

def getStatTime():
	cursor = db.cursor()
	try:
		cursor.execute("SELECT date FROM important_dates WHERE name = 'wordgen'")
		results = cursor.fetchone()
		statTime = results[0]
	except MySQLdb.Error as e:
		db.rollback()
		print("Database Error (getStatTime)")
	return statTime

def genstats():
	cursor = db.cursor()
	try:
		cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
		#get all historical data
		sql = """SELECT 100*SUM(CASE WHEN l.id IS NOT NULL THEN 1 ELSE 0 END)/COUNT(*) AS rate,
				SUM(CASE WHEN l.id IS NOT NULL THEN 1 ELSE 0 END) AS lockd,
				COUNT(*) as total
			FROM frontpage_history f
			LEFT JOIN locked_post l ON l.id = f.id
			WHERE firstseen >= (SELECT date FROM important_dates WHERE name = 'fph_start')"""
		cursor.execute(sql)
		adata = cursor.fetchone()
		arate = str(adata[0])
		alockd = str(adata[1])
		atotal = str(adata[2])
		#get last month's historical data
		sql = """SELECT 100*SUM(CASE WHEN l.id IS NOT NULL THEN 1 ELSE 0 END)/COUNT(*) AS rate,
				SUM(CASE WHEN l.id IS NOT NULL THEN 1 ELSE 0 END) AS lockd,
				COUNT(*) as total
			FROM frontpage_history f
			LEFT JOIN locked_post l ON l.id = f.id
			WHERE firstseen >= DATE_ADD(CURDATE(), INTERVAL -1 MONTH)"""
		cursor.execute(sql)
		mdata = cursor.fetchone()
		mrate = str(mdata[0])
		mlockd = str(mdata[1])
		mtotal = str(mdata[2])
		#print data
		print("    Total record: " + alockd + " (" + arate + "%) of " + atotal + " front-page posts locked.")
		print("    In the past month, " + mlockd + " (" + mrate + "%) of " + mtotal + " front-page posts were locked.")
	except MySQLdb.Error as e:
		db.rollback()
		print("Database Error (genstats)")
	cursor.close()

def substats():
	cursor = db.cursor()
	try:
		cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
		sql = """SELECT subreddit,
				SUM(CASE WHEN lp.id is not null then 1 else 0 END) AS locked,
				COUNT(*) AS seen,
				100*SUM(CASE WHEN lp.id is not null then 1 else 0 END)/COUNT(*) AS rate
			FROM frontpage_history fph
			LEFT JOIN locked_post lp on lp.id = fph.id
			GROUP BY subreddit
			HAVING COUNT(*) >= 10
			ORDER BY rate DESC, seen DESC
			LIMIT 10"""
		cursor.execute(sql)
		subrows = cursor.fetchall()
		#print results
		print("    Top 10 Subreddits by Lock Rate (at least 10 front-page posts):")
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
		print("Database Error (sub)")
	cursor.close()

def userstats():
	cursor = db.cursor()
	try:
		cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
		sql = """SELECT user,
				SUM(CASE WHEN lp.id is not null then 1 else 0 END) AS locked,
				COUNT(*) AS seen,
				100*SUM(CASE WHEN lp.id is not null then 1 else 0 END)/COUNT(*) AS rate
			FROM frontpage_history fph
			LEFT JOIN locked_post lp on lp.id = fph.id
			GROUP BY user
			HAVING COUNT(*) >= 10
			AND SUM(CASE WHEN lp.id IS NOT NULL THEN 1 ELSE 0 END) >= 3
			ORDER BY rate DESC, seen DESC
			LIMIT 5"""
		cursor.execute(sql)
		subrows = cursor.fetchall()
		#print results
		print("    Top 5 Users by Lock Rate")
		print("    (at least 10 front-page posts, at least 3 locked posts):")
		print("    +-------------------+-------+-------+-------+")
		print("    | USER              | LOCKD | TOTAL | %RATE |")
		print("    +-------------------+-------+-------+-------+")
		for row in subrows:
			user = row[0] + "                 "
			user = user[:17]
			lock = str(row[1]) + "     "
			lock = lock[:5]
			tot = str(row[2]) + "     "
			tot = tot[:5]
			rate = str(row[3]) + "     "
			rate = rate[:4] + "%"
			print("    | " + user + " | " + lock + " | " + tot + " | " + rate + " |")
		print("    +-------------------+-------+-------+-------+")
	except MySQLdb.Error as e:
		db.rollback()
		print("Database Error (user)")
	cursor.close()

def wordstats():
	cursor = db.cursor()
	try:
		cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
		sql = """SELECT word, locked, seen, 100*locked/seen as rate
			FROM words
			WHERE seen >= 5
			ORDER BY rate DESC, seen DESC
			LIMIT 10"""
		cursor.execute(sql)
		subrows = cursor.fetchall()
		#print results
		print("    Top 10 Title Words by Lock Rate (at least 5 front-page posts):")
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
		print("Database Error (word)")
	cursor.close()

def subwordstats():
	cursor = db.cursor()
	try:
		cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
		sql = """SELECT subreddit, word, locked, seen, 100*locked/seen as rate
			FROM subwords
			WHERE seen >= 5
			AND word NOT IN (SELECT word FROM stopwords)
			AND subreddit != 'legaladvice'
			ORDER BY rate DESC, seen DESC
			LIMIT 10"""
		cursor.execute(sql)
		subrows = cursor.fetchall()
		#print results
		print("    Top 10 Title Words by Subreddit by Lock Rate")
		print("    (at least 5 front-page posts, excludes stopwords, excludes r/legaladvice):")
		print("    +-------------------+-------------------+-------+-------+-------+")
		print("    | SUBREDDIT         | WORD              | LOCKD | TOTAL | %RATE |")
		print("    +-------------------+-------------------+-------+-------+-------+")
		for row in subrows:
			sub = row[0] + "                 "
			sub = sub[:17]
			word = row[1] + "                 "
			word = word[:17]
			lock = str(row[2]) + "     "
			lock = lock[:5]
			tot = str(row[3]) + "     "
			tot = tot[:5]
			rate = str(row[4]) + "     "
			rate = rate[:4] + "%"
			print("    | " + sub + " | " + word + " | " + lock + " | " + tot + " | " + rate + " |")
		print("    +-------------------+-------------------+-------+-------+-------+")
	except MySQLdb.Error as e:
		db.rollback()
		print("Database Error (word)")
	cursor.close()

if __name__ == '__main__':
	main()
