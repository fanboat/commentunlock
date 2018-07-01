#statcheckbot
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

def main():
	r = bot_login()
	#installdb() #Uncomment to install database on first run
	open_database()
	#main loop
	while True:
		now = datetime.datetime.now()
		print(" ")
		print("!! STAT CHECK BEGIN at time: " + str(now))
		#Likelihoodthresholds
		titlelike = 0.15
		sublike = 0.15
		bothlike = 0.25
		userlike = 0.12
		mindataword = 10
		mindatasub = 5
		mindataboth = 5
		mindatauser = 5
		print("Thresholds:")
		print("Greater than " + str(100*titlelike) + "% for Title words")
		print("Greater than " + str(100*sublike) + "% for Subreddit")
		print("Greater than " + str(100*bothlike) + "% for both")
		print("Greater than " + str(100*userlike) + "% for user")
		print("At least " + str(mindataword) + " data points for front page title words")
		print("At least " + str(mindatasub) + " data points for subreddit")
		print("At least " + str(mindataboth) + " data points for sub-specific front page title words")
		print("At least " + str(mindatauser) + " data points for User")
		print(" ")
		stat_scan(r, sublike, titlelike, bothlike, userlike, mindataword, mindatasub, mindataboth, mindatauser)
		now = datetime.datetime.now()
		print("!! STAT CHECK COMPLETE at time: " + str(now))
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
			if title_likelihood[0] > titlelike or sub_likelihood > sublike or both_likelihood[0] > bothlike or user_likelihood > userlike:
				#print info
				print("   Sub   : " + str(post.subreddit))
				print("   Title : " + post.title[:69])
				print("   User  : " + user)
				print("   ID    : " + post.shortlink[16:])
				if post.locked:
					print("   Status: LOCKED")
				else:
					print("   Status: unlocked")
				print("Likelihood by subreddit: " + str(100*sub_likelihood)[:4] + '%')
				print("Likelihood by title    : " + str(100*title_likelihood[0])[:4] + '%')
				print("Most offensive word    : " + title_likelihood[1])
				print("Likelihood by title+sub: " + str(100*both_likelihood[0])[:4] + '%')
				print("Most offensive word    : " + both_likelihood[1])
				print("Likelihood by user     : " + str(100*user_likelihood)[:4] + '%')
				print(" ")
	except praw.exceptions.PRAWException:
		print("PRAW Error, location 1")

if __name__ == '__main__':
	main()
