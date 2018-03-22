import praw
import config
import time

def bot_login():
	r = praw.Reddit(username = config.username,
		password = config.password,
		client_id=config.client_id,
		client_secret=config.client_secret,
		user_agent = 'CommentUnlockbot')
	return r

def find_and_crosspost(r):
	frontpage = r.subreddit('all').hot(limit=100)
	time.sleep(2)
	for post in frontpage:
		if post.locked and str(post.subreddit) != "legaladvice":
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
				r.subreddit('commentunlock').submit(crosstitle,url=crossURL)
				time.sleep(5)
			else:
				print("Crosspost already exists at position: "+str(count))
			time.sleep(2)


r = bot_login()
while True:
	print("Loop start.")
	find_and_crosspost(r)
	print("Loop complete.")
	time.sleep(30)
