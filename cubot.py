#commentunlockbot
#A reddit bot by fanboat
#reddit.com/r/commentunlock
#fanboat.co, fanboat@gmail.com
#2018-03-21

import praw
import config
import time
import datetime
import MySQLdb
import sys

def main():
	r = bot_login()
	#installdb() #Uncomment to install database on first run
	open_database()
	#main loop
	while True:
		print("Loop start")
		lock_scan(r)
		time.sleep(1)
		fp_scan(r)
		print("Front page scanned, database updated")
		fp_trim()
		print("Old posts removed from database")
		#update lastseen on posts which have been locked but are no longer
		unlockedupkeep()
		print("Loop complete")
		time.sleep(15)

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

def installdb(): #Only needs to be run on initial execution. Any alterations to the db will need to be made either here before the first run, or in the db itself.
	cursor = db.cursor()
	query = """CREATE TABLE IF NOT EXISTS post (
			id VARCHAR(10) PRIMARY KEY,
			cuid VARCHAR(10),
			title VARCHAR(300),
			subreddit VARCHAR(20),
			user VARCHAR(20),
			firstlocked DATETIME,
			lastlocked DATETIME,
			created DATETIME,
			firstseen DATETIME,
			lastseen DATETIME);

		CREATE TABLE IF NOT EXISTS frontpage (
			id VARCHAR(10) PRIMARY KEY,
			firstseen DATETIME,
			locked TINYINT,
			current TINYINT DEFAULT 0);

		CREATE TABLE IF NOT EXISTS blocked (
			id VARCHAR(10) PRIMARY KEY,
			comment VARCHAR(255));"""
	try:
		cursor.execute(query)
		db.commit()
	except MySQLdb.Error as e:
		db.rollback()
	cursor.close()

def insertnew(shortlink, cushortlink, longtitle, subreddit, user, created):
	id = shortlink[16:]
	if cushortlink is not None:
		cuid = cushortlink[16:]
	else:
		cuid = None
	title = longtitle.encode("ascii", "ignore")
	cursor = db.cursor()
	now = datetime.datetime.now()
	try:
		cursor.execute("SELECT firstseen from frontpage WHERE id = %s""", ([id]))
		firstseen = cursor.fetchone()
		cursor.execute("INSERT INTO post SELECT %s, %s, %s, %s, %s, %s, %s, %s, %s, %s", (id,cuid,title,subreddit,user,str(now),str(now),created,firstseen,str(now)))
		cursor.execute("UPDATE frontpage SET locked = 1 where id = %s", ([id]))
		db.commit()
	except MySQLdb.Error as e:
		db.rollback()
	cursor.close()

def updatelastlocked(shortlink, title, subreddit, user, created):
	id = shortlink[16:]
	cursor = db.cursor()
	try:
		cursor.execute("SELECT id, COUNT(*) FROM post WHERE id = %s GROUP BY id", ([id]))
		row_count = cursor.rowcount
		if row_count > 0:
			now = datetime.datetime.now()
			cursor.execute("UPDATE post SET lastlocked = %s WHERE id = %s", (str(now),id))
			db.commit()
			print("Updated database for post " + id)
		else:
			insertnew(shortlink, None, title, subreddit, user, created)
	except MySQLdb.Error as e:
		db.rollback()
	cursor.close()

def lock_scan(r):
	frontpage = r.subreddit('all').hot(limit=100)
	time.sleep(1)
	try:
		for post in frontpage:
			if post.locked and str(post.subreddit) != "legaladvice":
				#check if it is on the subreddit, post if not
				crosstitle = "[" + str(post.subreddit) + "] " + post.title
				if len(str(crosstitle)) > 300:
					crosstitle = crosstitle[:297] + "..."
				print("Locked Post Found: " + post.shortlink[16:] + " - " + post.title[:60])
				count = 0
				maxcount = 20 #how many recent posts to check on commentunlock sub
				commentunlocknew = r.subreddit('commentunlock').new(limit=maxcount)
				for crosspost in commentunlocknew:
					if str(crosspost.title) == crosstitle:
						break
					else:
						count += 1
				if count == maxcount:
					print("No current crosspost in top "+str(maxcount)+" posts of r/commentunlock")
					crossURL = "https://np.reddit.com" + str(post.permalink)
					if checkblocked(post.shortlink[16:]):
						cupost = r.subreddit('commentunlock').submit(crosstitle,url=crossURL)
						cushortlink = cupost.shortlink
					else:
						cushortlink = None
					#db entry
						insertnew(post.shortlink, cushortlink, post.title, post.subreddit, post.author.name, datetime.datetime.fromtimestamp(post.created))
					time.sleep(5)
				else:
					print("Crosspost already exists at position: "+str(count))
					#db update
					updatelastlocked(post.shortlink, post.title, post.subreddit, post.author.name, datetime.datetime.fromtimestamp(post.created))
				time.sleep(1)
			elif str(post.subreddit) == "commentunlock":
				#We're on the front page??
				print("Front Page!?")
				#modcomment = post.reply("We seem to be on the front page. I do not believe /u/fanboat is prepared for this.")
				#modcomment.distinguish("yes",True)
	except HttpError:
		print("HTTP error?")

def fp_scan(r):
	frontpage = r.subreddit('all').hot(limit=100)
	time.sleep(1)
	try:
		for post in frontpage:
			#insert any which are not in db
			id = str(post.shortlink)[16:]
			if post.locked:
				locked = 1
			else:
				locked = 0
			fp_insert(id,locked)
	except HttpError:
		print("HTTP error2?")

def fp_insert(id, locked):
	cursor = db.cursor()
	now = datetime.datetime.now()
	try:
		cursor.execute("""INSERT INTO frontpage
			SELECT %s, %s, %s, 1
			ON DUPLICATE KEY UPDATE current = 1, locked = %s""", (id, now, locked, locked))
		db.commit()
	except MySQLdb.Error as e:
                db.rollback()
	cursor.close()

def fp_trim():
	fp_trimA()
	fp_trimB()

def fp_trimA():
	cursor = db.cursor()
	try:
		cursor.execute("DELETE FROM frontpage WHERE current = 0")
		db.commit()
	except MySQLdb.Error as e:
		db.rollback()
	cursor.close()

def fp_trimB():
	cursor = db.cursor()
	try:
		cursor.execute("UPDATE frontpage SET current = 0")
		db.commit()
	except MySQLdb.Error as e:
		db.rollback()
	cursor.close()

def checkblocked(id):
	cursor = db.cursor()
	try:
		cursor.execute("SELECT id from blocked WHERE id = %s", ([id]))
		blockcheck = cursor.fetchone()
		if blockcheck is None:
			print("Post is allowed")
			return True
		else:
			print("Post is in blocked list")
			return False
	except MySQLdb.Error as e:
		db.rollback()
		return False
	cursor.close()

def unlockedupkeep():
	#This function will check up on posts which were once locked on the front page, but were unlocked before they fell off
	cursor = db.cursor()
	now = datetime.datetime.now()
	try:
		cursor.execute("""UPDATE post p
				inner join frontpage f on
					f.id = p.id
				set p.lastseen = %s;""", [str(now)])
		db.commit()
		print("Lastseen updated")
	except MySQLdb.Error as e:
		db.rollback()
	cursor.close()

if __name__ == '__main__':
	main()
