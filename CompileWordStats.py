#CompileWordStats.py
#A database population script by fanboat
#reddit.com/r/commentunlock
#fanboat.co, fanboat@gmail.com
#2018-03-21

import config
import time
import datetime
import MySQLdb
import sys
from urllib.error import HTTPError

def main():
	#installdb() #Uncomment to install database on first run
	open_database()
	sdate = getstartdate()
	print("start time = " + str(sdate))
	edate = datetime.datetime.now()
	edate = edate.replace(hour = 0, minute = 0, second = 0)
	edate = edate + datetime.timedelta(days = -2)
	print("end time = " + str(edate))
	#main loop
	while sdate < edate + datetime.timedelta(seconds = -1): #this comparison is weird because edate usually has a time of 00:00:00.123 or something
		now = datetime.datetime.now()
		print(" ")
		print("!! - MAIN LOOP BEGIN at time: " + str(now))
		print("running for " + str(sdate))
		wordgen(sdate)
		sdate = sdate + datetime.timedelta(hours=1)
	updatestartdate(edate)
	rebuildwordstable()

def installdb():
	cursor = db.cursor()
	query = """CREATE TABLE IF NOT EXISTS wordsraw (
		id VARCHAR(10),
		subreddit VARCHAR(50),
		word VARCHAR(300),
		seen smallint(6),
		locked smallint(6));

	CREATE TABLE IF NOT EXISTS words (
		subreddit VARCHAR(50),
		word VARCHAR(300),
		seen int(11),
		locked int(11));"""
	try:
		cursor.execute(query)
		db.commit()
	except MySQLdb.Error as e:
		db.rollback()
	cursor.close()

def open_database(): #connect to db
	global db
	db = MySQLdb.connect('localhost', config.dbUsername, config.dbPassword, 'commentunlock')

def getstartdate():
	cursor = db.cursor()
	try:
		cursor.execute("select date from important_dates where name = 'wordgen'")
		output = cursor.fetchone()
	except MySQLdb.Error as e:
		db.rollback()
	if output is not None:
		return output[0]
	else:
		return datetime.datetime.now()
	cursor.close()

def updatestartdate(date):
	cursor = db.cursor()
	try:
		cursor.execute("""UPDATE important_dates i
				SET i.date = %s
				WHERE i.name = 'wordgen';""", [(date)])
		db.commit()
	except MySQLdb.Error as e:
		db.rollback()
	cursor.close()

def wordgen(sdate):
	cursor = db.cursor()
	try:
		cursor.execute("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;")
		cursor.execute("""insert ignore into wordsraw
				select DISTINCT fph.id, fph.subreddit,
				substring_index(substring_index(alphanum(fph.title), ' ', t.id), ' ', -1),
				1 as seen,
				case when lp.id is not null then 1 else 0 end as locked
				from tally t
				join frontpage_history fph
				left join locked_post lp on lp.id = fph.id
				where fph.title IS NOT NULL
				and t.id <= 1 + CHAR_LENGTH(alphanum(fph.title)) - CHAR_LENGTH(REPLACE(alphanum(fph.title), ' ', ''))
				and firstseen >= %s and firstseen < DATE_ADD(%s, INTERVAL 1 HOUR);""", (sdate, sdate))
		db.commit()
		print("   Inserted words for one hour past " + str(sdate))
	except MySQLdb.Error as e:
		db.rollback()
	cursor.close()

def rebuildwordstable():
	cursor = db.cursor()
	try:
		cursor.execute("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;")
		cursor.execute("DELETE FROM words;")
		cursor.execute("""DELETE FROM wordsraw
				WHERE CHAR_LENGTH(word) = 0;""")
		cursor.execute("""INSERT INTO words
				SELECT subreddit, word, sum(seen), sum(locked)
				FROM wordsraw
				GROUP BY subreddit, word;""")
		db.commit()
	except MySQLdb.Error as e:
		db.rollback()
	cursor.close()

if __name__ == '__main__':
	main()
