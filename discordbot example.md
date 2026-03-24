#!/usr/bin/env python

#imports
import discord
from discord.ext import commands
from pathlib import Path 
import mysql.connector # type: ignore
import os

#imports - local
from Scripts import config
from Scripts import mail_fn

#useful variables
password = config.emailPassword2
sender = config.emailUsername2
token = os.getenv('DISCORD_TOKEN', 'change_me')
saveFolder = os.getenv('DOWNLOAD_PATH', '/mnt/hdd2/media/downloads/discordBot/')
showChat = 0

#mysql creds
mydb = mysql.connector.connect(
  host=config.mysqlHost,
  user=config.mysqlUserName,
  password=config.mysqlPassword,
  database=config.mysqlDbName
)
mycursor = mydb.cursor()

# create empty list
watch_channel_list = []
subscribed_channel_list = []
watch_channel_list.append('storyupdates')

# get subscribers list
sql = 'select distinct s.DiscordChannel, u.PersonalEmail, u.DestinationEmail, s.StoryName'
sql = sql + ' from Stories s'
sql = sql + ' left join UserStories us on s.StoryID = us.StoryID'
sql = sql + ' left join Users u on u.UserID = us.UserID'
sql = sql + ' where s.DiscordChannel is not null '
sql = sql + ' and us.OnHold = 0;'

mycursor.execute(sql)
rows = mycursor.fetchall()
subscribedStories = [(row[0], row[1], row[2], row[3]) for row in rows]
subscribedStories.append(['storyupdates', 'zelazny@gmail.com', 'zelkin21@kindle.com', 'Testing'])
mycursor.close()
mydb.close()

class MyClient(discord.Client):   
    async def on_ready(self):
        print('Logged on as', self.user)
        for guild in self.guilds:
          for channel in guild.text_channels:
            watch_channel_list.append(channel.name)
        # print(watch_channel_list)
        watch_channel_list.remove('welcome')
        watch_channel_list.remove('requests-suggestions')
        watch_channel_list.remove('important-info')
        watch_channel_list.remove('roles')
        watch_channel_list.remove('kemono-list')
        watch_channel_list.remove('general')
        watch_channel_list.remove('kemono-stuff')
        watch_channel_list.remove('recommendation')
        watch_channel_list.remove('trash')
        watch_channel_list.remove('level-ups')
        watch_channel_list.remove('memes-i-guess')
        watch_channel_list.remove('not-books-but-whatever')
        # watch_channel_list.remove('nerd-wars')
        watch_channel_list.remove('the-archives')
        watch_channel_list.remove('web-novels')
        watch_channel_list.remove('translated-novels')
        watch_channel_list.remove('anime-lightnovels')
        watch_channel_list.remove('published-novels')
        watch_channel_list.remove('russian-translations')

    async def on_message(self, message):
        # only respond to ourselves
        if message.channel.name == 'storyupdates':
          print(message.content)
        if showChat == 1:
          print(f"{message.channel.name}-{message.author.name}-{message.content}")
        if message.attachments:
          # save the attachment as a local file
          # ignore memes-i-guess
          if message.channel.name not in watch_channel_list:
            return
          for a in message.attachments:
            if a.filename.endswith('epub'):
              Path(f"{saveFolder}{message.channel.name}").mkdir(parents=True, exist_ok=True)
              print(f"Saving attachment as {saveFolder}{message.channel.name}/{a.filename}")
              await a.save(f"{saveFolder}{message.channel.name}/{a.filename}")
              for discordChannel, PersonalEmail, DestinationEmail, StoryName in subscribedStories:
                if discordChannel == message.channel.name:
                  #send email to user
                  print('sending email to user')
                  subject = 'New discord file for '+StoryName
                  body = 'A new file called '+a.filename+' has been published for '+StoryName+' - it will be with you shortly'
                  body = config.DestinationEmailBody
                  recipients = [PersonalEmail]
                  print(f"subject: {subject}")
                  print(f"body: {body}")
                  print(f"recipients: {recipients}")
                  print(f"sender: {sender}")
                  # print(f"password: {password}")
                  mail_fn.send_plain_email(subject, body, recipients)
                  recipients = [DestinationEmail]
                  file = f"{saveFolder}{message.channel.name}/{a.filename}"
                  print(f"second recipients: {recipients}")
                  print(f"file: {file}")
                  mail_fn.send_email_file(subject, body, recipients, file)
                  print('email sent')
                  # send message to channel
                  channel = client.get_channel(1293979524060549181)
                  message = 'New file downloaded for '+StoryName+' - filename: '+a.filename
                  await channel.send(message)

client = MyClient()
client.run(token)
