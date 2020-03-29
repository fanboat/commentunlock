
#responderbot
#A reddit bot by fanboat
#part of the commentunlock project
#reddit.com/r/commentunlock
#fanboat.co, fanboat@gmail.com
#2019-02-02

import praw
import prawcore
import config
import time
import datetime
import MySQLdb
import sys
from urllib.error import HTTPError
from praw.models import Comment
import re

def main():
	r = bot_login()
	open_database()
	#main loop
	while True:
		now = datetime.datetime.utcnow()
		print(" ")
		print("responderbot.py")
		print("!! - MAIN LOOP BEGIN at time: " + str(now))
		print("Checking for data requests")
		responsebot(r)
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

def responsebot(r):
	#Check for data requests from users, respond
	for item in r.inbox.unread(limit=None):
		if isinstance(item, Comment):
			print("!! - Inbox item identified")
			#print("Waiting 10 seconds before doing anything to try to prevent crash")
			#time.sleep(10)
			#print("Done waiting")
			fullcomment = item.body.lower().split()
			if fullcomment[0] == '/u/commentunlockbot' or fullcomment[0] == 'u/commentunlockbot':
				#check for stats, substats or wordstats
				text = 'Error'
				if fullcomment[1] == 'stats' and str(item.subreddit).lower() == 'commentunlock':
					#only running large output on r/commentunlock
					titlestats = titlestatstextCU(str(item.submission.title))
					text = titlestats[0] + '\n'
					statword = titlestats[1]
					if text != 'Error':
						text += '\n' + substatstextCU(str(item.submission.title)) + '\n\n'
					else:
						text = ''
					sub = str(item.submission.title)[1:]
					sub = sub[:sub.find(']')]
					if statword != '':
						recentThreads = subword_recentLockedThreads(sub, statword)
						if recentThreads != 'Error':
							text += recentThreads
					text += genstattext()
				if fullcomment[1] == 'stats' and str(item.subreddit).lower() != 'commentunlock':
					#if not on r/commentunlock, just report on the subreddit it was called from
					input = '/u/commentunlockbot substats '+str(item.subreddit).lower()
					titlestats = titlestatstext(str(item.subreddit), str(item.submission.title))
					text = titlestats[0] + '\n'
					statword = titlestats[1]
					text += substatstext(input.split())
					if statword != '':
						recentThreads = subword_recentLockedThreads(str(item.subreddit).lower(), statword)
						if recentThreads != 'Error':
							text += recentThreads
				if fullcomment[1] == 'substats':
					text = substatstext(fullcomment)
				if fullcomment[1] == 'wordstats':
					text = wordstatstext(fullcomment)
				if fullcomment[1] == 'subwordstats':
					text = subwordstatstext(fullcomment)
				if text != 'Error':
					#text += "\n\nThis bot can be summoned by commenting its name followed directly by any of these requests:  "
					#text += "\n**stats** - A general breakdown of locking statistics.  "
					#text += "\n**substats <*subreddit*>** - Specific statistics on a given subreddit.  "
					#text += "\n**wordstats <*word*>** - Locking statistics on a given word.  "
					#text += "\n**subwordstats <*subreddit*> <*word*>** - Statistics of a specific word on a specific subreddit.  "
					text += "\n\nThis bot was created by fanboat for r/CommentUnlock and is in development. Data recording began on 2018-03-29 and all statistics are based on the 100 hot posts on r/all since this time. I also broke the data recording without realizing it between 2019-04-19 and 2019-05-08, so that entire time range has been omitted from results. Please contact fanboat for any concerns.  "
					text += "\n[Stopwords](https://www.ranks.nl/stopwords) have been excluded from most of this reported data and some information may be a few days old. Times are in UTC.  "
					text += "\n[More info](https://old.reddit.com/r/CommentUnlock/comments/am92ey/the_bot_is_now_capable_of_being_summoned_for/).  "
					#reply to user
					item.reply(text)
					print("!! - RESPONDED")
				else:
					print("!! - Error")
			item.mark_read()

def subwordstatstext(input):
	text = 'Error'
	if len(input) > 3:
		sub = input[2]
		word = input[3]
		if sub[:1].lower() == '/':
			sub = sub[1:]
		if sub[:2].lower() == 'r/':
			sub = sub[2:]
		text = 'Current Locking Statistics for \'' + word + '\' on r/' + sub + ':  '
		subword = subword_subwordstats(sub, word)
		recentThreadstext = subword_recentThreads(sub, word)
		if subword != 'Error' and recentThreadstext != 'Error':
			if subword != '\nNo data found for this word on this subreddit.  ':
				text += subword + recentThreadstext
			else:
				text += subword
		else:
			text = 'Error'
	return text

def subword_subwordstats(sub, word):
	text = '\nNo data found for this word on this subreddit.  '
	cursor = db.cursor()
	try:
		cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
		sql = """SELECT locked, seen, 100*locked/seen as rate
			FROM subwords
			WHERE subreddit = %s AND word = %s"""
		cursor.execute(sql, ([sub],[word]))
		subrows = cursor.fetchall()
		#print results
		if len(subrows) > 0:
			for row in subrows:
				lock = str(row[0]) + "     "
				lock = lock[:5]
				tot = str(row[1]) + "     "
				tot = tot[:5]
				rate = str(row[2]) + "     "
				rate = rate[:4] + "%"
				if row[1] > 0:
					text = "\nTimes seen: " + tot + '  '
					text += "\nTimes locked: " + lock + '  '
					text += "\nLock rate: " + rate + '  '
				else:
					text = "Error"
		else:
			text = '\nNo data found for this word on this subreddit.  '
	except MySQLdb.Error as e:
		db.rollback()
		print("Database Error (subwordstats)")
		text = 'Error'
	cursor.close()
	return text

def subword_recentThreads(sub, word):
	text = ''
	cursor = db.cursor()
	try:
		cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
		sql = """SELECT title, user, firstseen, f.id,
			CASE WHEN firstlocked IS NOT NULL THEN firstlocked ELSE 'Not Locked' END AS locktime
			FROM frontpage_history f
			LEFT JOIN locked_post l ON l.id = f.id
			WHERE subreddit = %s AND title like %s
			ORDER BY firstseen DESC
			LIMIT 5"""
		cursor.execute(sql, ([sub],['%' + word + '%']))
		subrows = cursor.fetchall()
		#print results
		if len(subrows) > 0:
			text = "\nUp to 5 of the most recent threads on r/" + sub + ' containing \'' + word + '\'  '
			text += "\n(these results may have errors which are not reflected in other stats due to substring searching shortcuts):  "
			text += "\n\nTITLE | FIRST SEEN | FIRST LOCKED"
			text += "\n:--|:--:|:--:"
			for row in subrows:
				title = row[0][:60]
				#user = str(row[1])
				firstseen = str(row[2])[:19]
				id = str(row[3])
				url = "https://redd.it/" + id[:6]
				#title = "[" + title + "](" + url + ")"
				firstlocked = str(row[4])[:19]
				text += "\n" + title + " | " + firstseen + " | " + firstlocked
	except MySQLdb.Error as e:
		db.rollback()
		print("Database Error (subword_recentThreads)")
		text = 'Error'
	cursor.close()
	return text

def subword_recentLockedThreads(sub, word):
	text = ''
	cursor = db.cursor()
	try:
		cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
		sql = """SELECT title, user, firstseen, f.id, l.firstlocked AS locktime
			FROM frontpage_history f
			JOIN locked_post l ON l.id = f.id
			WHERE subreddit = %s AND title like %s
			ORDER BY firstseen DESC
			LIMIT 5"""
		cursor.execute(sql, ([sub],['%' + word + '%']))
		subrows = cursor.fetchall()
		#print results
		if len(subrows) > 0:
			text = "\nUp to 5 of the most recent locked threads on r/" + sub + ' containing \'' + word + '\'  '
			text += "\n(these results may have errors which are not reflected in other stats due to substring searching shortcuts):  "
			text += "\n\nTITLE | FIRST SEEN | FIRST LOCKED"
			text += "\n:--|:--:|:--:"
			for row in subrows:
				title = row[0][:60]
				#user = str(row[1])
				firstseen = str(row[2])[:19]
				id = str(row[3])
				url = "https://redd.it/" + id[:6]
				#title = "[" + title + "](" + url + ")"
				firstlocked = str(row[4])[:19]
				text += "\n" + title + " | " + firstseen + " | " + firstlocked
	except MySQLdb.Error as e:
		db.rollback()
		print("Database Error (subword_recentThreads)")
		text = 'Error'
	cursor.close()
	return text

def wordstatstext(input):
	text = 'Error'
	if len(input) > 2:
		word = input[2]
		text = 'Current Locking Statistics for \'' + word + '\':  '
		wordstats = word_wordstats(word)
		subwordstats = word_subwordstats(word)
		recentThreadstext = word_recentThreads(word)
		if wordstats != 'Error' and subwordstats != 'Error':
			if wordstats != '\nNo Frontpage data for this word.  ':
				text += wordstats + subwordstats
				if recentThreadstext != 'Error':
					text += recentThreadstext
			else:
				text += wordstats
		else:
			text = 'Error'
	return text

def word_wordstats(word):
	text = '\nNo Frontpage data for this word.  '
	cursor = db.cursor()
	try:
		cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
		sql = """SELECT locked, seen, 100*locked/seen as rate
			FROM words
			WHERE word = %s AND locked > 0
			ORDER BY rate DESC"""
		cursor.execute(sql, [word])
		subrows = cursor.fetchall()
		#print results
		if len(subrows) == 0:
			text = '\nNo Frontpage data for this word.  '
		for row in subrows:
			lock = str(row[0])
			tot = str(row[1])
			rate = str(row[2])[:5] + '%'
			text = "\nTimes seen: " + tot + '  '
			text += "\nTimes locked: " + lock + '  '
			text += "\nLock rate: " + rate + '  '
	except MySQLdb.Error as e:
		db.rollback()
		print("Database Error (wordstats)")
		text = 'Error'
	cursor.close()
	return text

def word_subwordstats(word):
	text = '\n'
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
			text = "\n\nTop 10 Highest Lock Rates by Subreddit  "
			text += "\n\nSUBREDDIT | LOCKD | TOTAL | %RATE"
			text += "\n:--|--:|--:|--:"
			for row in subrows:
				sub = row[0]
				lock = str(row[1])
				tot = str(row[2])
				rate = str(row[3])[:5] + "%"
				text += "\n" + sub + " | " + lock + " | " + tot + " | " + rate
	except MySQLdb.Error as e:
		db.rollback()
		print("Database Error (word)")
		text = 'Error'
	cursor.close()
	return text

def word_recentThreads(word):
	text = ''
	cursor = db.cursor()
	try:
		cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
		sql = """SELECT subreddit, title, user, firstseen, f.id, l.firstlocked AS locktime
			FROM frontpage_history f
			JOIN locked_post l ON l.id = f.id
			WHERE title like %s
			ORDER BY firstseen DESC
			LIMIT 5"""
		cursor.execute(sql, (['%' + word + '%']))
		subrows = cursor.fetchall()
		#print results
		if len(subrows) > 0:
			text = "\nUp to 5 of the most recent locked threads containing '" + word + '\'  '
			text += "\n(these results may have errors which are not reflected in other stats due to substring searching shortcuts):  "
			text += "\n\nSUBREDDIT | TITLE | FIRST SEEN | LOCKED"
			text += "\n:--|:--|:--:|:--:"
			for row in subrows:
				subreddit = row[0]
				title = row[1][:60]
				#user = str(row[2])
				firstseen = str(row[3])[:19]
				id = str(row[4])
				url = "https://redd.it/" + id[:6]
				#title = "[" + title + "](" + url + ")"
				firstlocked = str(row[5])[:19]
				text += "\n" + subreddit + " | " + title + " | " + firstseen + " | " + firstlocked
	except MySQLdb.Error as e:
		db.rollback()
		print("Database Error (word_recentThreads)")
		text = 'Error'
	cursor.close()
	return text

def substatstext(input):
	text = 'Error'
	if len(input) > 2:
		sub = input[2]
		if sub[:1].lower() == '/':
			sub = sub[1:]
		if sub[:2].lower() == 'r/':
			sub = sub[2:]
		text = 'Current Locking Statistics for r/' + sub + ':  '
		substats = sub_substats(sub)
		wordstats = sub_wordstats(sub)
		recentThreadstext = sub_recentThreads(sub)
		if substats != 'Error' and wordstats != 'Error':
			if substats != '/nNo frontpage data on this subreddit.  ':
				text += substats + wordstats
				if recentThreadstext != 'Error':
					text += recentThreadstext
			else:
				text += substats
		else:
			text = 'Error'
	return text

def substatstextCU(cutitle):
	#special case converter for posts that are on r/commentunlock
	text = ''
	title = cutitle [1:]
	sub = title[:title.find(']')]
	input = '/u/commentunlockbot substats ' + sub
	text = substatstext(input.lower().split())
	return text

def sub_substats(sub):
	cursor = db.cursor()
	text = '\nNo frontpage data on this subreddit.  '
	try:
		#full historical
		cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
		sql = """SELECT 100*SUM(CASE WHEN l.id IS NOT NULL THEN 1 ELSE 0 END)/COUNT(*) AS rate
			FROM frontpage_history f
			LEFT JOIN locked_post l ON l.id = f.id
			WHERE firstseen >= (SELECT date FROM important_dates WHERE name = 'fph_start')"""
		cursor.execute(sql)
		adata = cursor.fetchone()
		fullave = str(adata[0])
		sql = """SELECT 100*SUM(CASE WHEN l.id IS NOT NULL THEN 1 ELSE 0 END)/COUNT(*) AS rate
			FROM frontpage_history f
			LEFT JOIN locked_post l ON l.id = f.id
			WHERE firstseen >= DATE_ADD(CURDATE(), INTERVAL -1 MONTH)"""
		cursor.execute(sql)
		mdata = cursor.fetchone()
		monthave = str(mdata[0])
		#sub historical
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
			lock = str(row[0])
			tot = str(row[1])
			rate = str(row[2])[:5] + "%"
			if row[1] > 0:
				text = "\nTimes seen: " + tot + '  '
				text += "\nTimes locked: " + lock + '  '
				text += "\nLock rate: " + rate + '  '
				text += "\n\nreddit's average front-page lock rate since 2018-03-29 is " + fullave + "%, with a " + monthave + "% average for the last month.  "
			else:
				text = '\nNo Frontpage data on this subreddit.  '
	except MySQLdb.Error as e:
		db.rollback()
		print("Database Error (word)")
		text = 'Error'
	cursor.close()
	return text

def sub_wordstats(sub):
	cursor = db.cursor()
	text = ''
	try:
		cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
		sql = """SELECT word, locked, seen, 100*locked/seen as rate
			FROM subwords
			WHERE subreddit = %s AND seen >= 3 AND locked > 0
			AND word NOT IN (SELECT word FROM stopwords WHERE type = 0)
			ORDER BY rate DESC, seen DESC
			LIMIT 10"""
		cursor.execute(sql, [sub])
		subrows = cursor.fetchall()
		#print results
		if len(subrows) > 0:
			text += "\n\nTop 10 Highest Locked Words on r/" + sub + '  '
			text += "\n(seen at least 3 times, excludes stopwords):  "
			text += "\n\nWORD | LOCKD | TOTAL | %RATE"
			text += "\n:--|--:|--:|--:"
			for row in subrows:
				word = row[0]
				lock = str(row[1])[:5]
				tot = str(row[2])[:5]
				rate = str(row[3])[:5] + "%"
				text += "\n" + word + " | " + lock + " | " + tot + " | " + rate
	except MySQLdb.Error as e:
		db.rollback()
		print("Database Error (subwordstats)")
		text = 'Error'
	cursor.close()
	return text

def sub_recentThreads(sub):
	text = ''
	cursor = db.cursor()
	try:
		cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
		sql = """SELECT title, user, firstseen, f.id, firstlocked AS locktime
			FROM frontpage_history f
			JOIN locked_post l ON l.id = f.id
			WHERE subreddit = %s
			ORDER BY firstseen DESC
			LIMIT 5"""
		cursor.execute(sql, ([sub]))
		subrows = cursor.fetchall()
		#print results
		if len(subrows) > 0:
			text = "\nUp to 5 of the most recent locked threads on r/" + sub + ':  '
			text += "\n\nTITLE | FIRST SEEN | LOCKED"
			text += "\n:--|:--:|:--:"
			for row in subrows:
				title = row[0][:60]
				#user = str(row[1])
				firstseen = str(row[2])[:19]
				id = str(row[3])
				url = "https://redd.it/" + id[:6]
				#title = "[" + title + "](" + url + ")"
				firstlocked = str(row[4])[:19]
				text += "\n" + title + " | " + firstseen + " | " + firstlocked
	except MySQLdb.Error as e:
		db.rollback()
		print("Database Error (sub_recentThreads)")
		text = 'Error'
	cursor.close()
	return text

def genstattext():
	statTime = getStatTime()
	text = "\n\n***\n"
	text += "\n**r/CommentUnlock exclusive data** (this section will not appear when 'stats' are requested outside of this subreddit):  \nCurrent Locking Statistics from 2018-03-29 to " + str(statTime) + "  "
	text += genstats() #general overview stats
	text += gen_substats() #subreddit stats
	text += gen_wordstats() #title word stats
	text += gen_subwordstats() #title word stats by subreddit
	text += "\n\n***\n\n"
	return text

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
	text = ''
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
		#compile results into string
		text = "\nTotal record: " + alockd + " (" + arate + "%) of " + atotal + " front-page posts locked.  "
		text += "\nIn the past month, " + mlockd + " (" + mrate + "%) of " + mtotal + " front-page posts were locked.  "
	except MySQLdb.Error as e:
		db.rollback()
		print("Database Error (genstats)")
		text = 'Error'
	cursor.close()
	return text

def gen_substats():
	cursor = db.cursor()
	text = ''
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
		#compile results into string
		text = "\n\nTop 10 Subreddits by Lock Rate (at least 10 front-page posts):  "
		text += "\n\nSUBREDDIT | LOCKD | TOTAL | %RATE"
		text += "\n:--|--:|--:|--:"
		for row in subrows:
			sub = row[0]
			lock = str(row[1])[:5]
			tot = str(row[2])[:5]
			rate = str(row[3])[:5] + "%"
			text += "\n" + sub + " | " + lock + " | " + tot + " | " + rate
	except MySQLdb.Error as e:
		db.rollback()
		print("Database Error (sub)")
		text = 'Error'
	cursor.close()
	return text

def gen_wordstats():
	cursor = db.cursor()
	text = ''
	try:
		cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
		sql = """SELECT word, locked, seen, 100*locked/seen as rate
			FROM words
			WHERE seen >= 10
			ORDER BY rate DESC, seen DESC
			LIMIT 10"""
		cursor.execute(sql)
		subrows = cursor.fetchall()
		#compile results into string
		text = "\n\nTop 10 Title Words by Lock Rate (at least 10 front-page posts):"
		text += "\n\nWORD | LOCKD | TOTAL | %RATE"
		text += "\n:--|--:|--:|--:"
		for row in subrows:
			word = row[0]
			lock = str(row[1])[:5]
			tot = str(row[2])[:5]
			rate = str(row[3])[:5] + "%"
			text += "\n" + word + " | " + lock + " | " + tot + " | " + rate
	except MySQLdb.Error as e:
		db.rollback()
		print("Database Error (word)")
		text = 'Error'
	cursor.close()
	return text

def gen_subwordstats():
	cursor = db.cursor()
	text = ''
	try:
		cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
		sql = """SELECT subreddit, word, locked, seen, 100*locked/seen as rate
			FROM subwords
			WHERE seen >= 10
			AND word NOT IN (SELECT word FROM stopwords WHERE type = 0)
			AND subreddit != 'legaladvice'
			ORDER BY rate DESC, seen DESC
			LIMIT 10"""
		cursor.execute(sql)
		subrows = cursor.fetchall()
		#compile results into string
		text = "\n\nTop 10 Title Words by Subreddit by Lock Rate  "
		text += "\n(at least 10 front-page posts, excludes stopwords, excludes r/legaladvice):"
		text += "\n\nSUBREDDIT | WORD | LOCKD | TOTAL | %RATE"
		text += "\n:--|:--|--:|--:|--:"
		for row in subrows:
			sub = row[0]
			word = row[1]
			lock = str(row[2])[:5]
			tot = str(row[3])[:5]
			rate = str(row[4])[:5] + "%"
			text += "\n" + sub + " | " + word + " | " + lock + " | " + tot + " | " + rate
	except MySQLdb.Error as e:
		db.rollback()
		print("Database Error (word)")
	cursor.close()
	return text

def titlestatstext(sub, title):
	text = ''
	statword = ''
	mindataword = 5
	mindatasubword = 3
	worddata = statcheck_title(title, mindataword)
	if worddata[0] > 0:
		text = "\n\nThe most likely title word to be locked in this post by reddit trends is: '" + worddata[1] + ",' which has a " + str(100 * worddata[0])[:5] + "% general rate of locking.  "
	else:
		text = "No words in this post's title have a substantial history of being locked on the front page in general.  "
	subworddata = statcheck_both(title, sub, mindatasubword)
	if subworddata[0] > 0:
		statword = subworddata[1]
		text += "\nThe most likely title word to be locked in this post by r/" + sub + " is '" + statword + ",' which has a " + str(100* subworddata[0])[:5] + "% rate of locking.  "
	else:
		text += "\nNo words in this post's title have a substantial history of being locked specifically by r/" + sub + ".  "
	text += "\n"
	return text, statword

def titlestatstextCU(cutitle):
	#special case converter for posts that are on r/commentunlock
	text = ''
	statword = ''
	title = cutitle [1:]
	sub = title[:title.find(']')]
	if title.find(']') > 0:
		title = title[title.find(']')+2:]
		titlestats = titlestatstext(sub, title)
		text = titlestats[0]
		statword = titlestats[1]
	else:
		text = 'Error'
	return text, statword

def statcheck_both(title, subreddit, mindata):
	cursor = db.cursor()
	wordlist = re.sub("[^\w]", " ",  title).split()
	likelihood = 0
	statword = ''
	for word in wordlist:
		if len(word) >= 3:
			try:
				cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
				sql = """SELECT locked/seen as perc
						FROM subwords
						WHERE seen >= %s
						AND word = %s
						AND subreddit = %s
						AND word NOT IN (SELECT word FROM stopwords WHERE type = 0);"""
				cursor.execute(sql, ([mindata], [word], [subreddit]))
				row = cursor.fetchone()
				if row is None:
					row = 0
				else:
					row = row[0]
				if row > likelihood:
					likelihood = row
					statword = word
			except MySQLdb.Error as e:
				db.rollback()
				print("Database Error (both)")
	cursor.close()
	return (likelihood,statword)

def statcheck_title(title, mindata):
	cursor = db.cursor()
	wordlist = re.sub("[^\w]", " ",  title).split()
	likelihood = 0
	statword = ''
	for word in wordlist:
		if len(word) >= 3:
			try:
				cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
				sql = """SELECT locked/seen as perc
						FROM words
						WHERE word = %s
						AND seen >= %s
						AND word NOT IN (SELECT word FROM stopwords WHERE type = 0);"""
				cursor.execute(sql, ([word], [mindata]))
				row = cursor.fetchone()
				if row is None:
					row = 0
				else:
					row = row[0]
				if row > likelihood:
					likelihood = row
					statword = word
			except MySQLdb.Error as e:
				db.rollback()
				print("Database Error (title)")
	cursor.close()
	return (likelihood,statword)

if __name__ == '__main__':
	main()
