
#commentunlockbot
#A reddit bot by fanboat
#part of the commentunlock project
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
from twython import Twython
import json
from urllib.error import HTTPError

def main():
	r = bot_login()
	#installdb() #Uncomment to install database on first run
	open_database()
	open_twitter_database()
	t = twitter_login('commentunlock')
	#main loop
	while True:
		now = datetime.datetime.utcnow()
		print(" ")
		print("cubot.py")
		print("!! - MAIN LOOP BEGIN at time: " + str(now))
		lock_scan(r, t)
		print("Lock scan complete, Scanning front page")
		time.sleep(1)
		fp_scan(r)
		print("Front page scanned, database updated")
		print("---")
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

def open_twitter_database():
	global tdb
	tdb = MySQLdb.connect('localhost', config.dbUsername, config.dbPassword, 'twitter')

def twitter_login(username): #interface with the twitter api via twython library
	keys = get_access_keys_from_db(username) #set account to post from here (must be authorized and logged in db)
	access_token_key = keys[0]
	access_token_secret = keys[1]
	t = Twython(
		config.consumer_key,
		config.consumer_secret,
		access_token_key,
		access_token_secret
		)
	return t

def get_access_keys_from_db(username):
	cursor = tdb.cursor()
	keys = ("","")
	query = """SELECT u.authkey, u.authsecret
		FROM users u
		WHERE u.username = '{}'""".format(username)
	try:
		cursor.execute(query)
		keys = cursor.fetchone()
	except MySQLdb.Error as e:
		tdb.rollback()
		print("Error (get_access_keys_from_db)")
	cursor.close()
	return keys

def installdb(): #Only needs to be run on initial execution. Any alterations to the db will need to be made either here before the first run, or in the db itself.
	cursor = db.cursor()
	query = """CREATE TABLE IF NOT EXISTS locked_post (
			id VARCHAR(10) PRIMARY KEY,
			cuid VARCHAR(10),
			firstlocked DATETIME,
			lastlocked DATETIME,
			lockkarma INT
			special_case VARCHAR(50));

		CREATE TABLE IF NOT EXISTS blocked (
			id VARCHAR(10) PRIMARY KEY,
			comment VARCHAR(255));

		CREATE TABLE IF NOT EXISTS frontpage_history (
			id VARCHAR(10) PRIMARY KEY,
			title VARCHAR(300),
			user VARCHAR(20),
			subreddit VARCHAR(50),
			firstseen datetime,
			created datetime,
			lastseen datetime,
			firstkarma int,
			lastkarma int,
			peakkarma int,
			peakkarmatime datetime);

		CREATE TABLE IF NOT EXISTS canary (
			word VARCHAR(30));

		CREATE TABLE IF NOT EXISTS important_dates (
			name VARCHAR(30),
			date DATETIME,
			comment VARCHAR(300));

		CREATE TABLE IF NOT EXISTS comments (
			postid VARCHAR(10),
			commid VARCHAR(10) PRIMARY KEY);"""
	try:
		cursor.execute(query)
		db.commit()
	except MySQLdb.Error as e:
		db.rollback()
	cursor.close()

def insertnew(shortlink, cushortlink, karma, special_case):
	id = shortlink[16:]
	if cushortlink is not None:
		cuid = cushortlink[16:]
	else:
		cuid = None
	cursor = db.cursor()
	now = datetime.datetime.utcnow()
	try:
		cursor.execute("""INSERT INTO locked_post SELECT %s, %s, %s, %s, %s, %s
					ON DUPLICATE KEY UPDATE lastlocked = %s""", (id, cuid, str(now), str(now), karma, special_case, str(now)))
		db.commit()
		print("   Inserted (or updated) database for locked_post " + id)
	except MySQLdb.Error as e:
		db.rollback()
		print("insertnew error")
	cursor.close()

def lock_scan(r, t):
	try:
		frontpage = r.subreddit('all').hot(limit=100)
		time.sleep(1)
		for post in frontpage:
			#print(str(post.link_flair_text))
			if post.locked or (str(post.subreddit).lower() == 'blackpeopletwitter' and str(post.link_flair_text).lower() == 'country club thread'):
				special_case = None
				if str(post.subreddit).lower() == 'blackpeopletwitter' and str(post.link_flair_text).lower() == 'country club thread':
					special_case = 'Country Club Thread'
				#check if it is on the subreddit, post if not
				crosstitle = "[" + str(post.subreddit) + "] " + post.title
				if len(str(crosstitle)) > 300:
					crosstitle = crosstitle[:297] + "..."
				print("Locked Post Found: ")
				print("   Sub  : " + str(post.subreddit))
				print("   Title: " + post.title[:70])
				print("   URL  : redd.it/" + post.shortlink[16:])
				count = 0
				maxcount = 20 #how many recent posts to check on commentunlock sub
				commentunlocknew = r.subreddit('commentunlock').new(limit=maxcount)
				for crosspost in commentunlocknew:
					if str(crosspost.title) == crosstitle:
						cushortlink = crosspost.shortlink
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
							if str(post.author.name) == 'GallowBoob':
								cupost.mod.flair(text = 'gallowboob', css_class = '')
							if str(post.subreddit).lower() == 'blackpeopletwitter' and str(post.link_flair_text).lower() == 'country club thread':
								cupost.mod.flair(text = 'Country Club Thread', css_class = '')
							#If /u/totesmessenger has a comment in this post, upvote it
							#will have to use replace_more() since totes is probably at the bottom?
							tweet(t, crosstitle, cushortlink)
						else:
							cushortlink = None #else case unnecessary?
					except HttpError:
						print("HTTP error position 3")
					except praw.exceptions.PRAWException:
						print("PRAW Error, location 2")
					except prawcore.exceptions.InvalidToken:
						print("prawcore 2")
					#db entry
					insertnew(post.shortlink, cushortlink, post.score, special_case)
					time.sleep(5)
				else:
					print("   Crosspost already exists at position: "+str(count))
					#db update
					insertnew(post.shortlink, cushortlink, post.score, special_case)
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
			fp_insert(id, title, user, subreddit, datetime.datetime.fromtimestamp(post.created_utc), post.score)
	#except HttpError:
		#print("HTTP error2?")
	except prawcore.exceptions.ResponseException:
		print("ResponseException 2")
	except praw.exceptions.PRAWException:
		print("PRAW Error, location 5")
	except prawcore.exceptions.InvalidToken:
		print("prawcore 3")

def fp_insert(id, title, user, subreddit, created, karma):
	cursor = db.cursor()
	now = datetime.datetime.utcnow()
	try:
		#this (on duplicate key) replaces the functionality of the deprecated updatelastseen function
		cursor.execute("""INSERT IGNORE INTO frontpage_history
			SELECT %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
			ON DUPLICATE KEY UPDATE lastseen = %s,
				lastkarma = %s,
				peakkarmatime = CASE WHEN %s > peakkarma OR peakkarma IS NULL THEN %s ELSE peakkarmatime END,
				peakkarma = CASE WHEN %s > peakkarma OR peakkarma IS NULL THEN %s ELSE peakkarma END
			""",(id, title, user, subreddit, now, created, now, karma, karma, karma, now, now, karma, karma, now, karma, karma))
		#print("(id, title, user, subreddit, now, created, now, karma, karma, karma, now, now, karma, karma, now, karma, karma))")
		#print(id, title, user, subreddit, now, created, now, karma, karma, karma, now, now, karma, karma, now, karma, karma)
		#time.sleep(1)
	except MysSQLdb.Error as e:
		print("Error fp_insert")
		db.rollback()
	except:
		print("Error fp_insert")
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
		elif subreddit == "legaladvice":
			print("   Post is from r/legaladvice")
			return False
		elif existcheck is not None:
			print("   Surrogate post exists in DB, presume removed by moderator")
			return False
		else:
			print("   Post is allowed")
			return True
	except MySQLdb.Error as e:
		db.rollback()
		return False
	cursor.close()

def canary(r):
	#This function will check the frontpage for posts containing ultra-high-risk phrases and place a link comment in them
	#canary words are manually identified and stored in the db table canary
	cursor = db.cursor()
	now = datetime.datetime.utcnow()
	try:
		#obtain list of ids which we want to post comments on
		cursor.execute("""SELECT fph.id, fph.title, c.word, fph.subreddit
				from frontpage_history fph
				join canary c on fph.title like c.word
				left join locked_post lp on lp.id = fph.id
				where lp.id is null and fph.lastseen >= DATE_ADD(%s, INTERVAL -1 MINUTE);""", [str(now)])
		if cursor.rowcount > 0:
			idlist = cursor.fetchall()
			for id in idlist:
				print("CANARY ALERT!")
				trigword = id[2][1:-1]
				print("   Word : " + trigword)
				print("   Sub  : " + id[3])
				print("   Title: " + id[1][:70])
				print("   URL  : redd.it/" + id[0])
				#comment on post
				#canarycomment(r, id[0], trigword, id[3])
		else:
			print("No canary alerts")
	except MySQLdb.Error as e:
		db.rollback()
	cursor.close()

def canarycomment(r, postid, word, sub):
	#This function will (if it has not already) make a comment on a canary-targeted thread
	#check if comment already exists
	#get comments on post
	post = r.submission(id = postid)
	#check db for comment
	cursor = db.cursor()
	try:
		cursor.execute("SELECT commid FROM comments WHERE postid = %s", ([postid]))
		if cursor.rowcount > 0:
			postcheck = cursor.fetchone()
			print("Comment posted (id: " + str(postcheck[0]) + ")")
		else:
			postcheck = None
			print("No comment exists; proceed to comment")
	except MySQLdb.Error as e:
		db.rollback()
		print("Database Error (canarycomment 1)")
		postcheck = ['ERROR']
	#if no comment
	if postcheck is None:
		botcomment = canarytext(postid, word, sub)
		if botcomment is not None:
			print("Posting comment")
			#post comment
			print("Adding to database")
			#place in db

def canarytext(postid, word, sub):
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
		wordstats = cursor.fetchone()
	except MySQLdb.Error as e:
		db.rollback()
		print("Database Error (canarytext 1)")
		wordstats = None
	try:
		cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
		sql = """SELECT SUM(CASE WHEN lp.id is not null then 1 else 0 end) as locked, count(*) as total
			FROM frontpage_history fph
			LEFT JOIN locked_post lp on lp.id = fph.id
			WHERE fph.subreddit = %s
			AND fph.id != %s"""
		cursor.execute(sql, ([sub], [postid]))
		substats = cursor.fetchone()
	except MySQLdb.Error as e:
		db.rollback()
		print("Database Error (canarytext 2)")
		substats = None
	if wordstats is not None and substats is not None:
		text = "Did you know? Of the " + str(wordstats[1]) + " front page posts containing the string \'" + word + ",\' " + str(wordstats[0]) + " of them have been locked since late March?  "
		text += "\nr/" + sub + " has locked " + str(substats[0]) + " out of " + str(substats[1]) + " front page posts (" + str(round(100*substats[0]/substats[1],2)) + "%) in this time.  "
		text += "\nYou can continue discussing locked threads (within the bounds of reddit sitewide rules) on r/commentunlock."
	else:
		text = None
	return text

def tweet(t, title, URL):
	print("Attempting to tweet about:")
	print(title)
	body = title + " " + URL
	tweet = t.update_status(status = body)
	cursor = tdb.cursor()
	body = body.replace("'","''")
	posttime = datetime.datetime.strptime(tweet["created_at"],"%a %b %d %H:%M:%S +0000 %Y")
	query = """INSERT INTO tweets (body, postdate, twid, type) VALUES
		('{}','{}','{}',3)""".format(body,posttime,tweet["id"])
	try:
		cursor.execute(query)
		tdb.commit()
	except MySQLdb.Error as e:
		tdb.rollback()
		print("insert error (tweet)")
	cursor.close()

if __name__ == '__main__':
	main()
