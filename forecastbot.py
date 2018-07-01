#forecastbot
#A reddit bot by fanboat
#reddit.com/r/commentunlock
#fanboat.co, fanboat@gmail.com
#2018-05-22

import praw
import config
import time
import datetime
import MySQLdb
import sys
from urllib.error import HTTPError
import re
import prawcore

now = datetime.datetime.now()
frmt = "\n    " #format to do code blocks on reddit
poststring = "    Beginning Forecast compilation at time: " + str(now) + frmt

def main():
	print("Begin Forecast compilation...")
	global poststring
	global frmt
	r = bot_login()
	#installdb() #Uncomment to install database on first run
	open_database()
	#main loop
	#Likelihoodthresholds
	titlelike = 0.15
	sublike = 0.15
	bothlike = 0.25
	userlike = 0.12
	mindataword = 10
	mindatasub = 5
	mindataboth = 5
	mindatauser = 5
	poststring += frmt + "Thresholds:"
	poststring += frmt  + "Greater than " + str(100*titlelike) + "% for Title words"
	poststring += frmt  + "Greater than " + str(100*sublike) + "% for Subreddit"
	poststring += frmt  + "Greater than " + str(100*bothlike) + "% for both"
	#poststring += frmt + "Greater than " + str(100*userlike) + "% for user"
	poststring += frmt + "At least " + str(mindataword) + " data points for front page title words"
	poststring += frmt + "At least " + str(mindatasub) + " data points for subreddit"
	poststring += frmt + "At least " + str(mindataboth) + " data points for sub-specific front page title words"
	#poststring += frmt + "At least " + str(mindatauser) + " data points for User"
	stat_scan(r, sublike, titlelike, bothlike, userlike, mindataword, mindatasub, mindataboth, mindatauser)
	now = datetime.datetime.now()
	poststring += frmt + frmt + "Forecast Compilation complete at time: " + str(now)
	print("Forecast compiled")
	postforecast(r)
	print("Forecast posted")
	exit(0)

def bot_login(): #interface with reddit's bot API
	r = praw.Reddit(username = config.username,
		password = config.password,
		client_id=config.client_id,
		client_secret=config.client_secret,
		user_agent = 'CommentUnlockbot')
	return r

def open_database(): #connect to db to log data on posts
	global db
	db = MySQLdb.connect('localhost', config.dbUsername, config.dbPassword, 'commentunlock')

def statcheck_title(title, mindata, id):
	cursor = db.cursor()
	wordlist = re.sub("[^\w]", " ",  title).split()
	likelihood = 0
	statword = ''
	for word in wordlist:
		if len(word) >= 3:
			search = '%' + bytearray(word, 'ascii', 'ignore').decode('ascii', 'ignore') + '%'
			#print(search)
			try:
				cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
				sql = """SELECT CASE WHEN COUNT(*) >= %s THEN SUM(CASE WHEN lp.id is not null then 1 else 0 end)/count(*)
							ELSE 0 END as perc
						FROM frontpage_history fph
						LEFT JOIN locked_post lp on lp.id = fph.id
						WHERE fph.title like %s
						AND fph.id != %s"""
				cursor.execute(sql, ([mindata], [search], [id]))
				row = cursor.fetchone()[0]
				if row > likelihood:
					likelihood = row
					statword = word
			except MySQLdb.Error as e:
				db.rollback()
				print("Database Error (title)")
	cursor.close()
	return (likelihood,statword)

def statcheck_subreddit(subreddit, mindata, id):
	cursor = db.cursor()
	likelihood = 0
	try:
		cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
		sql = """SELECT CASE WHEN COUNT(*) >= %s THEN SUM(CASE WHEN lp.id is not null then 1 else 0 end)/count(*)
				ELSE 0 END as perc
			FROM frontpage_history fph
			LEFT JOIN locked_post lp on lp.id = fph.id
			WHERE subreddit = %s
			AND fph.id != %s"""
		cursor.execute(sql, ([mindata], [subreddit], [id]))
		likelihood = cursor.fetchone()[0]
	except MySQLdb.Error as e:
		db.rollback()
		print("Database Error (sub)")
	cursor.close()
	return likelihood

def statcheck_both(title, subreddit, mindata, id):
	cursor = db.cursor()
	wordlist = re.sub("[^\w]", " ",  title).split()
	likelihood = 0
	statword = ''
	for word in wordlist:
		if len(word) >= 3:
			search = '%' + bytearray(word, 'ascii', 'ignore').decode('ascii', 'ignore') + '%'
			#print(word)
			try:
				cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
				sql = """SELECT CASE WHEN COUNT(*) >= %s THEN SUM(CASE WHEN lp.id is not null then 1 else 0 end)/count(*)
							ELSE 0 END as perc
						FROM frontpage_history fph
						LEFT JOIN locked_post lp on lp.id = fph.id
						WHERE fph.title like %s AND subreddit = %s
						AND fph.id != %s"""
				cursor.execute(sql, ([mindata], [search], [subreddit], [id]))
				row = cursor.fetchone()[0]
				if row > likelihood:
					likelihood = row
					statword = word
			except MySQLdb.Error as e:
				db.rollback()
				print("Database Error (both)")
	cursor.close()
	return (likelihood,statword)

def statcheck_user(user, mindata, id):
	cursor = db.cursor()
	likelihood = 0
	try:
		cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
		sql = """SELECT CASE WHEN COUNT(*) >= %s THEN SUM(CASE WHEN lp.id is not null then 1 else 0 end)/count(*)
				ELSE 0 END as perc
			FROM frontpage_history fph
			LEFT JOIN locked_post lp on lp.id = fph.id
			WHERE user = %s
			AND fph.id != %s"""
		cursor.execute(sql, ([mindata], [user], [id]))
		likelihood = cursor.fetchone()[0]
	except MySQLdb.Error as e:
		db.rollback()
		print("Database Error (user)")
	cursor.close()
	return likelihood

def stat_scan(r, sublike, titlelike, bothlike, userlike, mindataword, mindatasub, mindataboth, mindatauser):
	global poststring
	global frmt
	try:
		frontpage = r.subreddit('all').hot(limit=100)
		for post in frontpage:
			#print("   Title: " + post.title[:70])
			#get stats
			id = post.shortlink[16:]
			title_likelihood = statcheck_title(post.title, mindataword, id)
			sub_likelihood = statcheck_subreddit(str(post.subreddit), mindatasub, id)
			both_likelihood = statcheck_both(post.title, str(post.subreddit), mindataboth, id)
			if post.author is not None:
				user_likelihood = statcheck_user(post.author.name, mindatauser, id)
				user = post.author.name
			else:
				user_likelihood = 0
				user = '[deleted]'
			if title_likelihood[0] > titlelike or sub_likelihood > sublike or both_likelihood[0] > bothlike:
				#place info in string
				poststring += frmt
				poststring += frmt + "   Sub   : " + str(post.subreddit)
				poststring += frmt + "   Title : " + post.title[:69]
				#poststring += frmt + "   User  : " + user
				#poststring += frmt + "   ID    : " + post.shortlink[16:]
				if post.locked:
					poststring += frmt + "   Status: LOCKED"
				else:
					poststring += frmt + "   Status: unlocked"
				poststring += frmt + "Likelihood by subreddit: " + str(100*sub_likelihood)[:4] + '%'
				poststring += frmt + "Likelihood by title    : " + str(100*title_likelihood[0])[:4] + '%'
				poststring += frmt + "Most offensive word    : " + title_likelihood[1]
				poststring += frmt + "Likelihood by title+sub: " + str(100*both_likelihood[0])[:4] + '%'
				poststring += frmt + "Most offensive word    : " + both_likelihood[1]
				#poststring += frmt + "Likelihood by user     : " + str(100*user_likelihood)[:4] + '%'
	except praw.exceptions.PRAWException:
		print("PRAW Error, location 1")

def postforecast(r):
	global poststring
	now = datetime.datetime.now()
	title = "Forecast (Beta) - posts at high risk of locking - " + str(now)
	try:
		fpost = r.subreddit('commentunlock').submit(title,selftext=poststring) #add flairtext
		fshortlink = fpost.shortlink[16:]
		dbinsert(fshortlink)
	except praw.exceptions.PRAWException:
		print("praw")
	except prawcore.exceptions.InvalidToken:
		print("prawcore")

def dbinsert(fpost):
	cursor = db.cursor()
	now = datetime.datetime.now()
	try:
		cursor.execute("INSERT IGNORE INTO forecasts SELECT %s, %s", (fpost, str(now)))
		db.commit()
	except MySQLdb.Error as e:
		db.rollback()
		print("db error")
	cursor.close()

if __name__ == '__main__':
	main()
