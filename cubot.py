#commentunlockbot
#A reddit bot by fanboat
#reddit.com/r/commentunlock
#fanboat.co, fanboat@gmail.com
#2018-03-21

import praw
import prawcore
import config
import time
import datetime
import MySQLdb
import sys
from urllib.error import HTTPError

def main():
	r = bot_login()
	#installdb() #Uncomment to install database on first run
	open_database()
	#main loop
	while True:
		now = datetime.datetime.now()
		print(" ")
		print("!! - MAIN LOOP BEGIN at time: " + str(now))
		lock_scan(r)
		time.sleep(1)
		fp_scan(r)
		print("Front page scanned, database updated")
		fp_trim()
		print("Old posts removed from shortlist")
		#update lastseen on posts which have been locked but are no longer
		unlockedupkeep()
		print("Running canary routine")
		canary(r)
		print("!! - MAIN LOOP COMPLETE, 5 second coffee break")
		print("   ( (     ")
		print("    ) )    ")
		print(" ........  ")
		print(" |      |] ")
		print(" \      /  ")
		print("  `----'   ")
		time.sleep(5)

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
	query = """CREATE TABLE IF NOT EXISTS locked_post (
			id VARCHAR(10) PRIMARY KEY,
			cuid VARCHAR(10),
			firstlocked DATETIME,
			lastlocked DATETIME,
			created DATETIME,
			lastseen DATETIME);

		CREATE TABLE IF NOT EXISTS frontpage (
			id VARCHAR(10) PRIMARY KEY,
			firstseen DATETIME,
			locked TINYINT,
			current TINYINT DEFAULT 0);

		CREATE TABLE IF NOT EXISTS blocked (
			id VARCHAR(10) PRIMARY KEY,
			comment VARCHAR(255));

		CREATE TABLE IF NOT EXISTS frontpage_history (
			id VARCHAR(10) PRIMARY KEY,
			title VARCHAR(300),
			user VARCHAR(20),
			subreddit VARCHAR(50),
			firstseen datetime);

		CREATE TABLE IF NOT EXISTS canary (
			word VARCHAR(30));"""
	try:
		cursor.execute(query)
		db.commit()
	except MySQLdb.Error as e:
		db.rollback()
	cursor.close()

def insertnew(shortlink, cushortlink, created):
	id = shortlink[16:]
	if cushortlink is not None:
		cuid = cushortlink[16:]
	else:
		cuid = None
	cursor = db.cursor()
	now = datetime.datetime.now()
	try:
		cursor.execute("""INSERT INTO locked_post SELECT %s, %s, %s, %s, %s, %s
					ON DUPLICATE KEY UPDATE lastseen = %s, lastlocked = %s""", (id, cuid, str(now), str(now), created, str(now), str(now), str(now)))
		cursor.execute("UPDATE frontpage SET locked = 1 where id = %s", ([id]))
		db.commit()
		print("   Inserted (or updated) database for locked_post " + id)
	except MySQLdb.Error as e:
		db.rollback()
	cursor.close()

def updatelastlocked(shortlink, created):
	id = shortlink[16:]
	cursor = db.cursor()
	try:
		cursor.execute("SELECT id, COUNT(*) FROM locked_post WHERE id = %s GROUP BY id", ([id]))
		row_count = cursor.rowcount
		if row_count > 0:
			now = datetime.datetime.now()
			cursor.execute("UPDATE locked_post SET lastlocked = %s WHERE id = %s", (str(now),id))
			db.commit()
			print("   Updated database for locked_post " + id)
		else:
			insertnew(shortlink, None, created)
	except MySQLdb.Error as e:
		db.rollback()
	cursor.close()

def lock_scan(r):
	try:
		frontpage = r.subreddit('all').hot(limit=100)
		time.sleep(1)
		for post in frontpage:
			if post.locked:
				#check if it is on the subreddit, post if not
				crosstitle = "[" + str(post.subreddit) + "] " + post.title
				if len(str(crosstitle)) > 300:
					crosstitle = crosstitle[:297] + "..."
				print("Locked Post Found: ")
				print("   Sub  : " + str(post.subreddit))
				print("   Title: " + post.title[:70])
				print("   ID   : " + post.shortlink[16:])
				count = 0
				maxcount = 20 #how many recent posts to check on commentunlock sub
				commentunlocknew = r.subreddit('commentunlock').new(limit=maxcount)
				for crosspost in commentunlocknew:
					if str(crosspost.title) == crosstitle:
						break
					else:
						count += 1
				if count == maxcount:
					print("   No current crosspost in top "+str(maxcount)+" posts of r/commentunlock")
					crossURL = "https://np.reddit.com" + str(post.permalink)
					cushortlink = None
					try:
						if checkblocked(post.shortlink[16:], str(post.subreddit)):
							cupost = r.subreddit('commentunlock').submit(crosstitle,url=crossURL)
							cushortlink = cupost.shortlink
							#Experimental tagging
							#if str(post.author.name) == 'GallowBoob':
								#post.set_flair('GallowBoob')
						else:
							cushortlink = None #else case unnecessary?
					except HttpError:
						print("HTTP error position 3")
					except praw.exceptions.PRAWException:
						print("PRAW Error, location 2")
					except prawcore.exceptions.InvalidToken:
						print("prawcore 2")
					#db entry
					insertnew(post.shortlink, cushortlink, datetime.datetime.fromtimestamp(post.created_utc))
					time.sleep(5)
				else:
					print("   Crosspost already exists at position: "+str(count))
					#db update
					updatelastlocked(post.shortlink, datetime.datetime.fromtimestamp(post.created_utc))
				time.sleep(1)
			elif str(post.subreddit) == "commentunlock":
				#We're on the front page??
				print("Front Page!?")
				#modcomment = post.reply("We seem to be on the front page. I do not believe /u/fanboat is prepared for this.")
				#modcomment.distinguish("yes",True)
	except prawcore.exceptions.ResponseException:
		print("ResponseException 1")
	except praw.exceptions.PRAWException:
		print("PRAW Error, location 1")
	except prawcore.exceptions.InvalidToken:
		print("prawcore 1")

def fp_scan(r):
	try:
		frontpage = r.subreddit('all').hot(limit=100)
		time.sleep(1)
		for post in frontpage:
			#insert any which are not in db
			id = str(post.shortlink)[16:]
			if post.author is not None:
				user = str(post.author.name)
			else:
				user = None
			subreddit = str(post.subreddit)
			title = str(post.title).encode("ascii", "ignore")
			if post.locked:
				locked = 1
			else:
				locked = 0
			fp_insert(id, title, user, subreddit, locked)
	#except HttpError:
		#print("HTTP error2?")
	except prawcore.exceptions.ResponseException:
		print("ResponseException 2")
	except praw.exceptions.PRAWException:
		print("PRAW Error, location 5")
	except prawcore.exceptions.InvalidToken:
		print("prawcore 3")

def fp_insert(id, title, user, subreddit, locked):
	cursor = db.cursor()
	now = datetime.datetime.now()
	try:
		cursor.execute("""INSERT INTO frontpage
			SELECT %s, %s, %s, 1
			ON DUPLICATE KEY UPDATE current = 1, locked = %s;""", (id, now, locked, locked))
		db.commit()
	except MySQLdb.Error as e:
                db.rollback()
	try:
		cursor.execute("""INSERT IGNORE INTO frontpage_history
			SELECT %s, %s, %s, %s, %s
			ON DUPLICATE KEY UPDATE id = id""", (id, title, user, subreddit, now))
	except MysSQLdb.Error as e:
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

def checkblocked(id, subreddit):
	cursor = db.cursor()
	try:
		cursor.execute("SELECT id from blocked WHERE id = %s", ([id]))
		blockcheck = cursor.fetchone()
		cursor.execute("SELECT cuid from locked_post WHERE id = %s", ([id]))
		existcheck = cursor.fetchone()
		if blockcheck is not None:
			print("   Post is in blocked list")
			return False
		elif existcheck is not None:
			print("   Surrogate post exists in DB, presume removed by moderator")
			return False
		elif subreddit == "legaladvice":
			print("   Post is from r/legaladvice")
			return False
		else:
			print("   Post is allowed")
			return True
	except MySQLdb.Error as e:
		db.rollback()
		return False
	cursor.close()

def unlockedupkeep():
	#This function will check up on posts which were once locked on the front page, but were unlocked before they fell off
	cursor = db.cursor()
	now = datetime.datetime.now()
	try:
		cursor.execute("""UPDATE locked_post p
				inner join frontpage f on
					f.id = p.id
				set p.lastseen = %s;""", [str(now)])
		db.commit()
		print("Lastseen updated")
	except MySQLdb.Error as e:
		db.rollback()
	cursor.close()

def canary(r):
	#This function will check the frontpage for posts containing ultra-high-risk phrases and place a link comment in them
	#canary words are manually identified and stored in the db table canary
	cursor = db.cursor()
	try:
		#obtain list of ids which we want to post comments on
		cursor.execute("""SELECT fp.id, fph.title, c.word
				from frontpage fp
				join frontpage_history fph on fph.id = fp.id
				join canary c on fph.title like c.word
				left join locked_post lp on lp.id = fph.id
				where lp.id is null;""")
		if cursor.rowcount > 0:
			idlist = cursor.fetchall()
			for id in idlist:
				print("CANARY ALERT!")
				print("     URL: redd.it/" + id[0])
				print("   Title: " + id[1][:70])
				trigword = id[2][1:-1]
				print("    Word: " + trigword)
				#comment on post
				#canarycomment(r, id[0], trigword)
		else:
			print("No canary alerts")
	except MySQLdb.Error as e:
		db.rollback()
	cursor.close()

def canarycomment(r, postid, word):
	#This function will (if it has not already) make a comment on a canary-targeted thread
	#check if comment already exists
	#get comments on post
	post = r.submission(id = postid)
	for comment in post.comments:
		#check if commentunlockbot has made a comment
		if str(comment.author) == 'nobody_likes_soda':
			print("Comment posted!")

def canarytext(postid, word):
	cursor = db.cursor()
	searchword = '%' + word + '%'
	try:
		cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
		sql = """SELECT SUM(CASE WHEN lp.id is not null then 1 else 0 end) as lockcount, count(*) as total
			FROM frontpage_history fph
			LEFT JOIN locked_post lp on lp.id = fph.id
			WHERE fph.title like %s
			AND fph.id != %s"""
		cursor.execute(sql, ([searchword], [postid]))
		stats = cursor.fetchone()
	except MySQLdb.Error as e:
		db.rollback()
		print("Database Error (canarytext)")
		stats = None
	if stats is not None:
		text = "Did you know? Of the " + str(stats[1]) + "front page posts containing the string \'" + word + ",\' " + str(stats[0]) + " of them have been locked since late March?  "
		text += "\nYou can continue discussing locked threads on r/commentunlock."
	else:
		text = None

if __name__ == '__main__':
	main()
