#commentunlockbot
#A reddit bot by fanboat
#fanboat.co, fanboat@gmail.com
#2018-03-21

import praw
import config
import time
import datetime
import MySQLdb
import sys
#import logging

def main():
	#logging.basicConfig(filename='/var/log/commentunlockbot.log', level=logging.INFO, format='%(asctime)s %(message)s')
	r = bot_login()
	open_database()

	#sys.exit(0) #for test executions
	while True:
		print("Loop start.")
		lock_scan(r)
		print("Loop complete.")
		time.sleep(30)


def bot_login():
	r = praw.Reddit(username = config.username,
		password = config.password,
		client_id=config.client_id,
		client_secret=config.client_secret,
		user_agent = 'CommentUnlockbot')
	return r

def open_database():
	global db
	db = MySQLdb.connect('localhost', config.dbUsername, config.dbPassword, 'commentunlock')
	#logging.info('Database connection established.')
	cursor = db.cursor()
	query = """CREATE TABLE IF NOT EXISTS post (
						id VARCHAR(10) PRIMARY KEY,
						cuid VARCHAR(10),
						title VARCHAR(300),
						subreddit VARCHAR(20),
						user VARCHAR(20),
						firstseen DATETIME,
						lastseen DATETIME)"""
	try:
		cursor.execute(query)
		db.commit()
	except MySQLdb.Error as e:
		db.rollback()
		#logging.info("MySQL Error [%d]: %s" % (e.args[0], e.args[1]))
	cursor.close()


def insertnew(shortlink, cushortlink, longtitle, subreddit, user):
	id = shortlink[16:]
	cuid = cushortlink[16:]
	title = longtitle.encode("ascii", "ignore")
	cursor = db.cursor()
	now = datetime.datetime.now()
	try:
		cursor.execute("INSERT INTO post SELECT %s, %s, %s, %s, %s, %s, %s", (id,cuid,title,subreddit,user,str(now),str(now)))
		db.commit()
	except MySQLdb.Error as e:
		db.rollback()
		#log?
	cursor.close()


def updatelastseen(shortlink):
	id = shortlink[16:]
	cursor = db.cursor()

	try:
		#make sure it exists
		cursor.execute("SELECT id, COUNT(*) FROM post WHERE id = %s GROUP BY id", ([id]))
		row_count = cursor.rowcount
		if row_count > 0:
			#update
			now = datetime.datetime.now()
			cursor.execute("UPDATE post SET lastseen = %s WHERE id = %s", (str(now),id))
			db.commit()
			#print("lastseen updated")
	except MySQLdb.Error as e:
		db.rollback()
		#log?


def lock_scan(r):
	frontpage = r.subreddit('all').hot(limit=100)
	time.sleep(2)
	try:
		for post in frontpage:
			if post.locked and str(post.subreddit) != "legaladvice":
				#check if it is on the subreddit, post if not
				crosstitle = "[" + str(post.subreddit) + "] " + post.title[:270] #the correctly formatted crosspost title
				if len(str(post.title)) > 270:
					crosstitle = crosstitle + "..."
				print("Locked Post Found: "+crosstitle)
				count = 0
				maxcount = 15 #how many recent posts to check on commentunlock sub
				commentunlocknew = r.subreddit('commentunlock').new(limit=maxcount)
				for crosspost in commentunlocknew:
					if str(crosspost.title) == crosstitle:
						break
					else:
						count += 1
				if count == maxcount:
					print("No current crosspost in top "+str(maxcount)+" posts of r/commentunlock")
					crossURL = "https://np.reddit.com" + str(post.permalink)
					cupost = r.subreddit('commentunlock').submit(crosstitle,url=crossURL)
					#db entry
					insertnew(post.shortlink,cupost.shortlink,post.title,post.subreddit,post.comments[0].author.name)
					time.sleep(5)
				else:
					print("Crosspost already exists at position: "+str(count))
					#db update
					updatelastseen(post.shortlink)
				time.sleep(2)
	except HttpError:
		print("HTTP error?")
		#logging.warning("HTTP Error caught. Ignoring...")


if __name__ == '__main__':
	main()
