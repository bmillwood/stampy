#!/usr/bin/env python3

#https://realpython.com/how-to-make-a-discord-bot-python/#how-to-make-a-discord-bot-in-python

import os
import sys
import traceback

from datetime import datetime, timezone, timedelta
import html
import json
import re

import numpy as np

import unicodedata

import discord
from dotenv import load_dotenv

import googleapiclient.discovery

import sentience

intents = discord.Intents.default()
intents.members = True  # we need this to be able to get the whole list of members
client = discord.Client(intents=intents)


class Module(object):
	"""Informal Interface specification for modules
	These represent packets of functionality. For each message,
	we show it to each module and ask if it can process the message,
	then give it to the module that's most confident"""

	def canProcessMessage(self, message, client=None):
		"""Look at the message and decide if you want to handle it
		Return a pair of values: (confidence rating out of 10, message)
		Including a response message is optional, use an empty string to just indicate a confidence
		If confidence is more than zero, and the message is empty, `processMessage` may be called
		`canProcessMessage` should contain only operations which can be executed safely even if another module reports a higher confidence and ends up being the one to respond.
		If your module is going to do something that only makes sense if it gets to repond, put that in `processMessage` instead

		Rough Guide:
		0 -> "This message isn't meant for this module, I have no idea what to do with it"
		1 -> "I could give a generic reply if I have to, as a last resort"
		2 -> "I can give a slightly better than generic reply, if I have to. e.g. I realise this is a question but don't know what it's asking"
		3 -> "I can probably handle this message with ok results, but I'm a frivolous/joke module"
		4 -> 
		5 -> "I can definitely handle this message with ok results, but probably other modules could too"
		6 -> "I can definitely handle this message with good results, but probably other modules could too"
		7 -> "This is a valid command specifically for this module, and the module is 'for fun' functionality"
		8 -> "This is a valid command specifically for this module, and the module is medium importance functionality"
		9 -> "This is a valid command specifically for this module, and the module is important functionality"
		10 -> "This is a valid command specifically for this module, and the module is critical functionality"

		Ties are broken in module priority order. You can also return a float if you really want
		"""
		# By default, we have 0 confidence that we can answer this, and our response is ""
		return (0, "")

	async def processMessage(self, message, client=None):
		"""Handle the message, return a string which is your response.
		This is an async function so it can interact with the Discord API if it needs to"""
		return (0, "")

	# def canProcessReaction(self, reaction, client=None):
	#   return (0, "")

	async def processReactionEvent(self, reaction, user, eventtype='REACTION_ADD', client=None):
		"""eventtype can be 'REACTION_ADD' or 'REACTION_REMOVE'
		Use this to allow modules to handle adding and removing reactions on messages"""
		return (0, "")

	async def processRawReactionEvent(self, event, client=None):
		"""event is a discord.RawReactionActionEvent object
		Use this to allow modules to handle adding and removing reactions on messages"""
		return (0, "")

	def __str__(self):
		return "Dummy Module"


def isatme(message):
	"""Determine if the message is directed at Stampy
	If it's not, return False. If it is, strip away the name part and return the remainder of the message"""

	text = message.content
	atme = False
	re_atme = re.compile(r"^@?[Ss]tampy\W? ")
	text, subs = re.subn("<@!?736241264856662038>|<@&737709107066306611>", 'Stampy', text)
	if subs:
		atme = True
	
	if (re_atme.match(text) is not None) or re.search(r'^[sS][,:]? ', text):
		atme = True
		print("X At me because re_atme matched or starting with [sS][,:]? ")
		text = text.partition(" ")[2]
	elif re.search(",? @?[sS](tampy)?[.!?]?$", text):  # name can also be at the end
		text = re.sub(",? @?[sS](tampy)?$", "", text)
		atme = True
		print("X At me because it ends with stampy")

	if type(message.channel) == discord.DMChannel:
		print("X At me because DM")
		atme = True  # DMs are always at you

	if atme:
		return text
	else:
		print("Message is Not At Me")
		return False


class QQManager(Module):
	"""Module to manage commands about the question queue"""
	def __init__(self):
		self.re_nextq = re.compile(r"""(([wW]hat(’|'| i)?s|([Cc]an|[Mm]ay) (we|[iI]) (have|get)|[Ll]et(’|')?s have|[gG]ive us)?( ?[Aa](nother)?|( the)? ?[nN]ext) question,?( please)?\??|
?([Dd]o you have|([Hh]ave you )?[gG]ot)?( ?[Aa]ny( more| other)?| another) questions?( for us)?\??)!?""")

	def canProcessMessage(self, message, client=None):
		if isatme(message):
			text = isatme(message)

			if re.match(r"([hH]ow many questions (are (there )?)?(left )?in|[hH]ow (long is|long's)) (the|your)( question)? queue( now)?\??", text):
				if qq:
					if len(qq) == 1:
						result = "There's one question in the queue"
					else:
						result = "There are %d questions in the queue" % len(qq)
				else:
					result = "The question queue is empty"
				return (9, result)
			elif self.re_nextq.match(text):  # we're being asked for the next question
				return (9, "")  # Popping a question off the stack modifies things, so just return a "yes, we can handle this" and let processMessage do it

		# This is either not at me, or not something we can handle
		return (0, "")

	async def processMessage(self, message, client):
		if isatme(message):
			text = isatme(message)

			if self.re_nextq.match(text):
				result = get_latest_question()
				if result:
					return (10, result)
				else:
					return (8, "There are no questions in the queue")
			else:
				print("Shouldn't be able to get here")
				return (0, "") 

	def __str__(self):
		return "Question Queue Manager"


@client.event
async def on_ready():
	print(f'{client.user} has connected to Discord!')
	guild = discord.utils.find(lambda g: g.name == guildname, client.guilds)

	print(guild.id, guild.name)

	members = '\n - '.join([member.name for member in guild.members])
	print(f'Guild Members:\n - {members}')


@client.event
async def on_message(message):
	# don't react to our own messages
	if message.author == client.user:
		return

	print("########################################################")
	print(message)
	print(message.reference)
	print(message.author, message.content)

	if hasattr(message.channel, 'name') and message.channel.name == "general":
		print("Last message was no longer us")
		global lastmessagewasYTquestion
		lastmessagewasYTquestion = False

	if message.content == 'bot test':
		response = "I'm alive!"
		await message.channel.send(response)
	elif message.content.lower() == "Klaatu barada nikto".lower():
		await message.channel.send("I must go now, my planet needs me")
		exit()
	if message.content == 'reply test':
		if message.reference:
			reference = await message.channel.fetch_message(message.reference.message_id)
			reftext = reference.content
			replyURL = reftext.split("\n")[-1].strip()

			response = "This is a reply to message %s:\n\"%s\"" % (message.reference.message_id, reftext)
			response += "which should be taken as an answer to the question at: \"%s\"" % replyURL
		else:
			response = "This is not a reply"
		await message.channel.send(response)
	if message.content == "resetinviteroles" and message.author.id == 181142785259208704:
		print("[resetting can-invite roles]")
		guild = discord.utils.find(lambda g: g.name == guildname, client.guilds)
		print(guildname, guild)
		role = discord.utils.get(guild.roles, name="can-invite")
		print("there are", len(guild.members), "members")
		for member in guild.members:
			if sm.get_user_stamps(member) > 0:
				print(member.name, "can invite")
				await member.add_roles(role)
			else:
				print(member.name, "has 0 stamps, can't invite")
		await message.channel.send("[Invite Roles Reset]")
		return
	# elif message.content.lower() == "mh":
	#   guild = discord.utils.find(lambda g: g.name == guildname, client.guilds)
	#   #general = discord.utils.find(lambda c: c.name == "general", guild.channels)
		
	#   with open("stamps.csv", 'w') as stamplog:
	#       stamplog.write("msgid,type,from,to\n")

	#       for channel in guild.channels:
	#           print("#### Considering", channel.type, channel.name, "####")
	#           if channel.type == discord.TextChannel:
	#               print("#### Logging", channel.name, "####")
	#               async for message in channel.history(limit=None):
	#                   # print("###########")
	#                   # print(message.content[:20])
	#                   reactions = message.reactions
	#                   if reactions:
	#                       # print(reactions)
	#                       for reaction in reactions:
	#                           reacttype = getattr(reaction.emoji, 'name', '')
	#                           if reacttype in ["stamp", "goldstamp"]:
	#                               # print("STAMP")
	#                               users = await reaction.users().flatten()
	#                               for user in users:
	#                                   string = "%s,%s,%s,%s" % (message.id, reacttype, user.id, message.author.id)
	#                                   print(string)
	#                                   stamplog.write(string + "\n")
	#                                   # print("From", user.id, user)
	#   return


	# elif message.content.lower() == "invite test" and message.author.name == "robertskmiles":
	#   guild = discord.utils.find(lambda g: g.name == guildname, client.guilds)
	#   welcome = discord.utils.find(lambda c: c.name == "welcome", guild.channels)
	#   invite = await welcome.create_invite(max_uses=1,
	#                                       temporary=True,
	#                                       unique=True,
	#                                       reason="Requested by %s" % message.author.name)
	#   print(invite)
	#   await message.channel.send(invite.url)

	result = None

	# What are the options for responding to this message?
	# Prepopulate with a dummy module, with 0 confidence about its proposed response of ""
	options = [(Module(), 0, "")]

	for module in modules:
		print("Asking module: %s" % str(module))
		output = module.canProcessMessage(message, client)
		print("output is", output)
		confidence, result = output
		if confidence > 0:
			options.append((module, confidence, result))

	# Go with whichever module was most confident in its response
	options = sorted(options, key=(lambda o: o[1]), reverse=True)
	print(options)  
	module, confidence, result = options[0]

	if confidence > 0:  # if the module had some confidence it could reply
		if not result:  # but didn't reply in canProcessMessage()
			confidence, result = await module.processMessage(message, client)

	if not result:  # no results from the modules, try the sentience core
		try:
			result = sentience.processMessage(message, client)
		except Exception as e:
			if hasattr(message.channel, 'name') and message.channel.name in ("bot-dev", "bot-dev-priv", "181142785259208704"):
				try:
					errortype = sentience.dereference("{{$errorType}}")  # grab a random error type from the factoid db
				except:
					errortype = "SeriousError"  # if the dereference failed, it's bad
				x = sys.exc_info()[2].tb_next
				print(e, type(e))
				traceback.print_tb(x)
				lineno = sys.exc_info()[2].tb_next.tb_lineno
				result = "%s %s: %s" % (errortype, lineno, str(e))
			else:
				x = sys.exc_info()[2].tb_next
				print(e, type(e))
				traceback.print_tb(x)

	if result:
		await message.channel.send(result)

	print("########################################################")


def tds(s):
	"""Make a timedelta object of s seconds"""
	return timedelta(seconds=s)


def check_for_new_youtube_comments():
	"""Consider getting the latest comments from the channel
	Returns a list of dicts if there are new comments
	Returns [] if it checked and there are no new ones 
	Returns None if it didn't check because it's too soon to check again"""

	# print("Checking for new YT comments")

	global latestcommentts
	global lastcheckts
	global ytcooldown

	now = datetime.now(timezone.utc)

	# print("It has been this long since I last called the YT API: " + str(now - lastcheckts))
	# print("Current cooldown is: " + str(ytcooldown))
	if (now - lastcheckts) > ytcooldown:
		print("Hitting YT API")
		lastcheckts = now
	else:
		print("YT waiting >%s\t- " % str(ytcooldown - (now - lastcheckts)), end='')
		return None

	api_service_name = "youtube"
	api_version = "v3"
	DEVELOPER_KEY = YTAPIKEY

	youtube = googleapiclient.discovery.build(api_service_name, api_version, developerKey=DEVELOPER_KEY)

	request = youtube.commentThreads().list(
		part="snippet",
		allThreadsRelatedToChannelId="UCLB7AzTwc6VFZrBsO2ucBMg"
	)
	response = request.execute()

	items = response.get('items', None)
	if not items:
		print("YT comment checking broke. I got this response:")
		print(response)
		ytcooldown = ytcooldown * 10  # something broke, slow way down
		return None

	newestts = latestcommentts

	newitems = []
	for item in items:
		# Find when the comment was published
		pubTsStr = item['snippet']['topLevelComment']['snippet']['publishedAt']
		# For some reason fromisoformat() doesn't like the trailing 'Z' on timestmaps
		# And we add the "+00:00" so it knows to use UTC
		pubTs = datetime.fromisoformat(pubTsStr[:-1] + "+00:00")

		# If this comment is newer than the newest one from last time we called API, keep it
		if pubTs > latestcommentts:
			newitems.append(item)

		# Keep track of which is the newest in this API call
		if pubTs > newestts:
			newestts = pubTs

	print("Got %s items, most recent published at %s" % (len(items), newestts))

	# save the timestamp of the newest comment we found, so next API call knows what's fresh
	latestcommentts = newestts

	newcomments = []
	for item in newitems:
		videoId = item['snippet']['topLevelComment']['snippet']['videoId']
		commentId = item['snippet']['topLevelComment']['id']
		username = item['snippet']['topLevelComment']['snippet']['authorDisplayName']
		text = item['snippet']['topLevelComment']['snippet']['textOriginal']
		# print("dsiplay text:" + item['snippet']['topLevelComment']['snippet']['textDisplay'])
		# print("original text:" + item['snippet']['topLevelComment']['snippet']['textOriginal'])

		comment = {'url': "https://www.youtube.com/watch?v=%s&lc=%s" % (videoId, commentId),
					'username': username,
					'text': text,
					'title': ""
				  }

		newcomments.append(comment)

	print("Got %d new comments since last check" % len(newcomments))

	if not newcomments:
		# we got nothing, double the cooldown period (but not more than 20 minutes)
		ytcooldown = min(ytcooldown * 2, tds(1200))
		print("No new comments, increasing cooldown timer to %s" % ytcooldown)

	return newcomments



latestquestionposted = None

def get_latest_question():
	"""Pull the oldest question from the queue
	Returns False if the queue is empty, the question string otherwise"""
	global qq
	if not qq:
		return False

	# comment = qq.pop(0)   
	# pop from the end, meaning this is actually a stack not a queue
	# This was changed when all the historical questions were added in. So now it's newest first
	comment = qq.pop()

	global latestquestionposted
	latestquestionposted = comment

	text = comment['text']
	if len(text) > 1500:
		text = text[:1500] + " [truncated]"
	comment['textquoted'] = "> " + "\n> ".join(text.split("\n"))

	title = comment.get("title", "")
	if title:
		report = """YouTube user \'%(username)s\' asked this question, on the video \'%(title)s\'!:
%(textquoted)s
Is it an interesting question? Maybe we can answer it!
<%(url)s>""" % comment

	else:
		report = """YouTube user \'%(username)s\' just asked a question!:
%(textquoted)s
Is it an interesting question? Maybe we can answer it!
<%(url)s>""" % comment

	print("==========================")
	print(report)
	print("==========================")

	with open("qq.json", 'w') as qqfile:   # we modified the queue, put it in a file to persist
		json.dump(qq, qqfile, indent="\t")

	global lastqaskts
	lastqaskts = datetime.now(timezone.utc)  # reset the question waiting timer

	return report


@client.event
async def on_socket_raw_receive(msg):
	"""This event fires whenever basically anything at all happens.
		Anyone joining, leaving, sending anything, even typing and not sending...
		So I'm going to use it as a kind of 'update' or 'tick' function, for things the bot needs to do regularly. Yes this is hacky.
		Rate limit these things, because this function might be firing a lot"""
	
	global lastmessagewasYTquestion

	# never fire more than once a second
	global lasttickts
	tickcooldown = timedelta(seconds=1)  
	now = datetime.now(timezone.utc)

	if (now - lasttickts) > tickcooldown:
		print("|", end='')
		# print("last message was yt question?:", lastmessagewasYTquestion)
		lasttickts = now
	else:
		print(".", end='')
		return

	# check for new youtube comments
	newcomments = check_for_new_youtube_comments()
	if newcomments:
		for comment in newcomments:
			if "?" in comment['text']:
				qq.append(comment)
		with open("qq.json", 'w') as qqfile:  # we modified the queue, put it in a file to persist
			json.dump(qq, qqfile, indent="\t")

	if qq:
		# ask a new question if it's been long enough since we last asked one
		global lastqaskts
		qaskcooldown = timedelta(hours=6)

		if (now - lastqaskts) > qaskcooldown:
			if not lastmessagewasYTquestion:  # Don't ask anything if the last thing posted in the chat was us asking a question
				lastqaskts = now
				report = get_latest_question()
				guild = discord.utils.find(lambda g: g.name == guildname, client.guilds)
				general = discord.utils.find(lambda c: c.name == "general", guild.channels)
				await general.send(report)
				lastmessagewasYTquestion = True
			else:
				lastqaskts = now  # wait the full time again
				print("Would have asked a question, but the last post in the channel was a question we asked. So we wait")
		else:
			print("%s Questions in queue, waiting %s to post" % (len(qq), str(qaskcooldown - (now - lastqaskts))))
			return

			# await message.channel.send(result)





class ReplyModule(Module):

	def __str__(self):
		return "YouTube Reply Posting Module"

	def isPostRequest(self, text):
		"""Is this message asking us to post a reply?"""
		print(text)
		if text:
			return text.lower().endswith("post this") or text.lower().endswith("send this")
		else:
			return False

	def isAllowed(self, message, client):
		"""[Deprecated] Is the message author authorised to make stampy post replies?"""
		postingrole = discord.utils.find(lambda r: r.name == 'poaster', message.guild.roles)
		return postingrole in message.author.roles

	def extractReply(self, text):
		"""Pull the text of the reply out of the message"""
		lines = text.split("\n")
		replymessage = ""
		for line in lines:
			# pull out the quote syntax "> " and a user if there is one
			match = re.match("([^#]+#\d\d\d\d )?> (.*)", line)
			if match:
				replymessage += match.group(2) + "\n"

		return replymessage

	def postReply(self, text, questionid):
		"""Actually post the reply to YouTube. Currently this involves a horrible hack"""

		#first build the dictionary that will be passed to youtube.comments().insert as the 'body' arg
		body = {'snippet': {
					'parentId': questionid,
					'textOriginal': text,
					'authorChannelId': {
						'value': 'UCFDiTXRowzFvh81VOsnf5wg'
						}
					}
				}

		# now we're going to put it in a json file, which CommentPoster.py will read and send it
		with open("topost.json") as postfile:
			topost = json.load(postfile)

		topost.append(body)

		with open("topost.json", 'w') as postfile:
			json.dump(topost, postfile, indent="\t")

		print("dummy, posting %s to %s" % (text, questionid))

	def canProcessMessage(self, message, client=None):
		"""From the Module() Interface. Is this a message we can process?"""
		if isatme(message):
			text = isatme(message)

			if self.isPostRequest(text):
				print("this is a posting request")
				# if self.isAllowed(message, client):
				#   print("the user is allowed")
				#   return (9, "")
				# else:
				#   return (9, "Only people with the `poaster` role can do that")
				return (9, "Ok, I'll post this when it has more than 30 stamp points")
	
		return (0, "")

	async def processMessage(self, message, client):
		"""From the Module() Interface. Handle a reply posting request message"""
		return (0, "")


	async def postMessage(self, message, approvers=[]):

		approvers.append(message.author)
		approvers = [a.name for a in approvers]
		approvers = list(set(approvers))  # deduplicate

		if len(approvers) == 1:
			approverstring = approvers[0]
		elif len(approvers) == 2:
			approverstring = " and ".join(approvers)
		else:
			approvers[-1] = "and " + approvers[-1]
			approverstring = ", ".join(approvers)  # oxford comma baybee

		text = isatme(message)  # strip off stampy's name
		replymessage = self.extractReply(text)
		replymessage += "\n -- _I am a bot. This reply was approved by %s_" % approverstring

		report = ""


		if message.reference:  # if this is a reply
			reference = await message.channel.fetch_message(message.reference.message_id)
			reftext = reference.content
			questionURL = reftext.split("\n")[-1].strip("<> \n")
			if "youtube.com" not in questionURL:
				return "I'm confused about what YouTube comment to reply to..."
		else:
			global latestquestionposted
			if not latestquestionposted:
				# return (10, "I can't do that because I don't remember the URL of the last question I posted here. I've probably been restarted since that happened")
				report = "I don't remember the URL of the last question I posted here, so I've probably been restarted since that happened. I'll just post to the dummy thread instead...\n\n"
				latestquestionposted = {'url': "https://www.youtube.com/watch?v=vuYtSDMBLtQ&lc=Ugx2FUdOI6GuxSBkOQd4AaABAg"}  # use the dummy thread

			questionURL = latestquestionposted['url']

		questionid = re.match(r".*lc=([^&]+)", questionURL).group(1)

		quotedreplymessage = "> " + replymessage.replace("\n", "\n> ")
		report += "Ok, posting this:\n %s\n\nas a response to this question: <%s>" % (quotedreplymessage, questionURL)

		self.postReply(replymessage, questionid)

		return report



	async def evaluateMessageStamps(self, message):
		"Return the total stamp value of all the stamps on this message, and a list of who approved it"
		total = 0
		print("Evaluating message")

		approvers = []

		reactions = message.reactions
		if reactions:
			print(reactions)
			for reaction in reactions:
				reacttype = getattr(reaction.emoji, 'name', '')
				if reacttype in ["stamp", "goldstamp"]:
					print("STAMP")
					users = await reaction.users().flatten()
					for user in users:
						approvers.append(user)
						print("  From", user.id, user)
						stampvalue = sm.get_user_stamps(user)
						total += stampvalue
						print("  Worth", stampvalue)

		return (total, approvers)

	def hasBeenRepliedTo(self, message):
		reactions = message.reactions
		print("Testing if question has already been replied to")
		print("The message has these reactions:", reactions)
		if reactions:
			for reaction in reactions:
				reacttype = getattr(reaction.emoji, 'name', reaction.emoji)
				print(reacttype)
				if reacttype in ['📨', ":incoming_envelope:"]:
					print("Message has envelope emoji, it's already replied to")
					return True
				elif reacttype in ['🚫', ":no_entry_sign:"]:
					print("Message has no entry sign, it's vetoed")
					return True

		print("Message has no envelope emoji, it has not already replied to")
		return False

	async def processRawReactionEvent(self, event, client=None):
		eventtype = event.event_type
		emoji = getattr(event.emoji, 'name', event.emoji)

		if emoji in ['stamp', 'goldstamp']:
			guild = discord.utils.find(lambda g: g.name == guildname, client.guilds)
			channel = discord.utils.find(lambda c: c.id == event.channel_id, guild.channels)
			message = await channel.fetch_message(event.message_id)
			if isatme(message) and self.isPostRequest(isatme(message)):
			#   self.maybePostMessage(message)

			# print("isatme:", isatme(message))
			# print("isPostRequest", self.isPostRequest(isatme(message)))
			# print(await self.evaluateMessageStamps(message))

				if self.hasBeenRepliedTo(message):  # did we already reply?
					return

				stampscore, approvers = await self.evaluateMessageStamps(message)
				if stampscore > 30:
					report = await self.postMessage(message, approvers)
					await message.add_reaction("📨")  # mark it with an envelope to show it was sent
					await channel.send(report)
				else:
					report = "This reply has %s stamp points. I will send it when it has 30" % stampscore
					await channel.send(report)




		# if message.author.id == 736241264856662038:  # votes for stampy don't affect voting
		#   return
		# if message.author.id == event.user_id:  # votes for yourself don't affect voting
		#   if eventtype == 'REACTION_ADD' and emoji in ['stamp', 'goldstamp']:
		#       await channel.send("<@" + str(event.user_id) + "> just awarded a stamp to themselves...")
		#   return


		# if emoji in ['stamp', 'goldstamp']:

		#   msgid = event.message_id
		#   fromid = event.user_id
		#   toid = message.author.id
		#   # print(msgid, re)
		#   string = "%s,%s,%s,%s" % (msgid, emoji, fromid, toid)
		#   print(string)

		#   print("### STAMP AWARDED ###")
		#   self.addvote(emoji, fromid, toid, negative=(eventtype=='REACTION_REMOVE'))
		#   self.save_votesdict_to_json()
		#   print("Score before stamp:", self.get_user_stamps(toid))
		#   self.calculate_stamps()
		#   print("Score after stamp:", self.get_user_stamps(toid))
		#   # "msgid,type,from,to"


class StampsModule(Module):
	def __str__(self):
		return "Stamps Module"

	def __init__(self):
		self.goldmultiplier = 5  # gold stamp is worth how many red stamps?
		self.gamma = 1.0  # what proportion of the karma you get is passed on by your votes?

		self.reset_stamps()  # this initialises all the vote counting data structures empty
		self.load_votesdict_from_json()
		self.calculate_stamps()


	def reset_stamps(self):
		print("WIPING STAMP RECORDS")

		robid = '181142785259208704'
		godid = "0"

		# votesdict is a dictionary of users and their voting info
		# keys are user ids
		# values are dicts containing:
		#    'votecount: how many times this user has voted
		#    'votes': A dict mapping user ids to how many times this user voted for them
		self.votesdict = {}
		# god is user id 0, and votes once, for rob (id 181142785259208704)
		self.votesdict[godid] = {'votecount': 1, 'votes': {robid: 1}}

		self.users = set([godid, robid])  # a set of all the users mentioned in votes
		self.ids = [godid, robid]  # an ordered list of the users' IDs

		self.totalvotes = 0

		self.scores = []

	def addvote(self, stamptype, fromid, toid, negative=False):
		toid = str(toid)
		fromid = str(fromid)

		if toid == '736241264856662038':  # votes for stampy do nothing
			return

		if toid == fromid:  # votes for yourself do nothing
			return

		# ensure both users are in the users set
		self.users.add(fromid)
		self.users.add(toid)

		if stamptype == "stamp":
			votestrength = 1
		elif stamptype == "goldstamp":
			votestrength = self.goldmultiplier

		if negative:  # are we actually undoing a vote?
			votestrength = -votestrength

		self.totalvotes += votestrength

		u = self.votesdict.get(fromid, {'votecount': 0, 'votes': {}})
		u['votecount'] = u.get('votecount', 0) + votestrength
		u['votes'][toid] = u['votes'].get(toid, 0) + votestrength

		self.votesdict[fromid] = u

	def update_ids_list(self):
		for fromid, u in self.votesdict.items():
			self.users.add(fromid)
			for toid, _ in u['votes'].items():
				self.users.add(toid)

		self.ids = sorted(list(self.users))
		self.index = {"0": 0}
		for userid in self.ids:
			self.index[str(userid)] = self.ids.index(userid)

	def calculate_stamps(self):
		"""Set up and solve the system of linear equations"""
		print("RECALCULATING STAMP SCORES")

		self.update_ids_list()

		usercount = len(self.ids)

		A = np.zeros((usercount, usercount))
		for fromid, u in self.votesdict.items():
			fromi = self.index[fromid]

			for toid, votes in u['votes'].items():
				toi = self.index[toid]
				score = (self.gamma * votes) / u['votecount']

				A[toi, fromi] = score

		# set the diagonal to -1
		# c_score = a_score*a_votes_for_c + b_score*b_votes_for_c
		# becomes
		# a_score*a_votes_for_c + b_score*b_votes_for_c - c_score = 0
		# so the second array can be all zeros
		for i in range(1, usercount):
			print(sum(A[i]), sum(A[:,i]))
			A[i, i] = -1.0
		A[0, 0] = 1.0

		B = np.zeros(usercount)
		B[0] = 1.0  # God has 1 karma

		self.scores = list(np.linalg.solve(A, B))

		self.print_all_scores()


	def print_all_scores(self):
		totalstamps = 0
		for uid in self.users:
			name = client.get_user(int(uid))
			if not name:
				name = "<@" + uid + ">"
			stamps = self.get_user_stamps(uid)
			totalstamps += stamps
			print(name, "\t", stamps)

		print("Total votes:", self.totalvotes)
		print("Total Stamps:", totalstamps)

	def index_dammit(self, user):
		"""Get an index into the scores array from whatever you get"""

		if user in self.index:  # maybe we got given a valid ID?
			return self.index[user]
		elif str(user) in self.index:
			return self.index[str(user)]

		uid = getattr(user, 'id', None)  # maybe we got given a User or Member object that has an ID?
		if uid:
			return self.index_dammit(str(uid))

		return None

	def get_user_score(self, user):
		index = self.index_dammit(user)
		if index:
			return self.scores[index]
		else:
			return 0.0

	def get_user_stamps(self, user):
		index = self.index_dammit(user)
		# stamps = int(self.scores[index] * self.totalvotes)
		# if not stamps:
		#   stamps = self.scores[index] * self.totalvotes
		if index:
			stamps = self.scores[index] * self.totalvotes
		else:
			stamps = 0.0
		return stamps

	def load_votes_from_csv(self, filename="stamps.csv"):
		# stampyid = 736241264856662038
		# robid = 181142785259208704

		with open(filename, "r") as stampsfile:
			stampsfile.readline()  # throw away the first line, it's headers
			for line in stampsfile:
				msgid, reacttype, fromid, toid = line.strip().split(",")
				msgid = int(msgid)
				fromid = int(fromid)
				toid = int(toid)
				
				print(msgid, reacttype, fromid, toid)
				self.addvote(reacttype, fromid, toid)

		self.save_votesdict_to_json()
		self.calculate_stamps()

	async def load_votes_from_history(self):
		"""Load up every time any stamp has been awarded by anyone in the whole history of the Discord
		This is omega slow, should basically only need to be called once"""
		guild = discord.utils.find(lambda g: g.name == guildname, client.guilds)

		with open("stamps.csv", 'w') as stamplog:
			stamplog.write("msgid,type,from,to\n")

			for channel in guild.channels:
				print("#### Considering", channel.type, type(channel.type), channel.name, "####")
				if channel.type == discord.ChannelType.text:
					print("#### Logging", channel.name, "####")
					async for message in channel.history(limit=None):
						# print("###########")
						# print(message.content[:20])
						reactions = message.reactions
						if reactions:
							# print(reactions)
							for reaction in reactions:
								reacttype = getattr(reaction.emoji, 'name', '')
								if reacttype in ["stamp", "goldstamp"]:
									# print("STAMP")
									users = await reaction.users().flatten()
									for user in users:
										string = "%s,%s,%s,%s" % (message.id, reacttype, user.id, message.author.id)
										print(string)
										stamplog.write(string + "\n")
										self.addvote(reacttype, user.id, message.author.id)
										# print("From", user.id, user)

		self.save_votesdict_to_json()
		self.calculate_stamps()


	def load_votesdict_from_json(self, filename="stamps.json"):
		with open(filename) as stampsfile:
			self.votesdict = json.load(stampsfile)

		self.totalvotes = 0
		for fromid, u in self.votesdict.items():
			self.totalvotes += u['votecount']

	def save_votesdict_to_json(self, filename="stamps.json"):
		with open(filename, 'w') as stampsfile:   # we modified the queue, put it in a file to persist
			json.dump(self.votesdict, stampsfile, indent="\t")

	async def processReactionEvent(self, reaction, user, eventtype='REACTION_ADD', client=None):
		# guild = discord.utils.find(lambda g: g.name == guildname, client.guilds)
		emoji = getattr(reaction.emoji, 'name', reaction.emoji)
		if emoji == 'stamp':
			print("### STAMP AWARDED ###")
			msgid = reaction.message.id
			fromid = user.id
			toid = reaction.message.audthor.id
			# print(msgid, re)
			string = "%s,%s,%s,%s" % (msgid, emoji, fromid, toid)
			print(string)
			# "msgid,type,from,to"

	async def processRawReactionEvent(self, event, client=None):
		eventtype = event.event_type
		guild = discord.utils.find(lambda g: g.name == guildname, client.guilds)
		channel = discord.utils.find(lambda c: c.id == event.channel_id, guild.channels)
		if not channel:
			return
		message = await channel.fetch_message(event.message_id)
		emoji = getattr(event.emoji, 'name', event.emoji)

		if message.author.id == 736241264856662038:  # votes for stampy don't affect voting
			return
		if message.author.id == event.user_id:  # votes for yourself don't affect voting
			# if eventtype == 'REACTION_ADD' and emoji in ['stamp', 'goldstamp']:
			#   await channel.send("<@" + str(event.user_id) + "> just awarded a stamp to themselves...")
			return


		if emoji in ['stamp', 'goldstamp']:

			msgid = event.message_id
			fromid = event.user_id
			toid = message.author.id
			# print(msgid, re)
			string = "%s,%s,%s,%s" % (msgid, emoji, fromid, toid)
			print(string)

			print("### STAMP AWARDED ###")
			self.addvote(emoji, fromid, toid, negative=(eventtype=='REACTION_REMOVE'))
			self.save_votesdict_to_json()
			print("Score before stamp:", self.get_user_stamps(toid))
			self.calculate_stamps()
			print("Score after stamp:", self.get_user_stamps(toid))
			# "msgid,type,from,to"


	def canProcessMessage(self, message, client=None):
		if isatme(message):
			text = isatme(message)

			if re.match(r"(how many stamps am i worth)\??", text.lower()):
				return (9, "You're worth %.2f stamps to me" % self.get_user_stamps(message.author))

			elif text == "reloadallstamps" and message.author.name == "robertskmiles":
				return (10, "")

		return (0, "")

	async def processMessage(self, message, client=None):
		if isatme(message):
			text = isatme(message)

		if text == "reloadallstamps" and message.author.name == "robertskmiles":
			print("FULL STAMP HISTORY RESET BAYBEEEEEE")
			self.reset_stamps()
			await self.load_votes_from_history()
			return (10, "Working on it, could take a bit")

		return (0, "")


@client.event
async def on_raw_reaction_add(payload):
	print("RAW REACTION ADD")
	if len(payload.emoji.name) == 1:
		print(unicodedata.name(payload.emoji.name))
	else:
		print(payload.emoji.name.upper())
	print(payload)

	for module in modules:
		await module.processRawReactionEvent(payload, client)


@client.event
async def on_raw_reaction_remove(payload):
	print("RAW REACTION REMOVE")
	print(payload)

	for module in modules:
		await module.processRawReactionEvent(payload, client)

	# result = None

	# # What are the options for responding to this message?
	# # Prepopulate with a dummy module, with 0 confidence about its proposed response of ""
	# options = [(Module(), 0, "")]

	# for module in modules:
	#   print("Asking module: %s" % str(module))
	#   output = module.canProcessReaction(payload, client)
	#   print("output is", output)
	#   confidence, result = output
	#   if confidence > 0:
	#       options.append((module, confidence, result))

	# # Go with whichever module was most confident in its response
	# options = sorted(options, key=(lambda o: o[1]), reverse=True)
	# print(options)    
	# module, confidence, result = options[0]

	# if confidence > 0:  # if the module had some confidence it could reply
	#   if not result:  # but didn't reply in canProcessMessage()
	#       confidence, result = await module.processReactionEvent(payload, client)


# @client.event
# async def on_reaction_add(reaction, user):
#   if user == client.user:
#       return
#   print("REACTION", reaction, user)

#   for module in modules:
#       await module.processReactionEvent(self, reaction, user, eventtype='REACTION_ADD', client=client)


# @client.event
# async def on_reaction_remove(reaction, user):
#   if user == client.user:
#       return
#   print("REACTION", reaction, user)

#   for module in modules:
#       await module.processReactionEvent(self, reaction, user, eventtype='REACTION_REMOVE', client=client)

sm = StampsModule()


if __name__ == "__main__":
	load_dotenv()
	TOKEN = os.getenv('DISCORD_TOKEN')
	GUILD = os.getenv('DISCORD_GUILD')
	YTAPIKEY = os.getenv('YOUTUBE_API_KEY')


	# when was the most recent comment we saw posted?
	latestcommentts = datetime.now(timezone.utc)  # - timedelta(hours=8)

	# when did we last hit the API to check for comments?
	lastcheckts = datetime.now(timezone.utc)

	# how many seconds should we wait before we can hit YT API again
	# this the start value. It doubles every time we don't find anything new
	ytcooldown = tds(60)


	# timestamp of when we last ran the tick function
	lasttickts = datetime.now(timezone.utc)

	# Load the question queue from the file
	with open("qq.json") as qqfile:
		qq = json.load(qqfile)
	print("Loaded Question Queue from file")
	print("%s questions loaded" % len(qq))

	# timestamp of last time we asked a youtube question
	lastqaskts = datetime.now(timezone.utc)

	guildname = "Rob Miles AI Discord"


	# Was the last message posted in #general by anyone, us asking a question from YouTube?
	lastmessagewasYTquestion = True  # We start off not knowing, but it's better to assume yes than no

	from videosearch import VideoSearchModule
	from InviteManagerModule import InviteManagerModule


	modules = [sm, QQManager(), VideoSearchModule(), ReplyModule(), InviteManagerModule()]


	client.run(TOKEN)
