import discord
from discord.ext import commands
import matplotlib.pyplot as plt
import numpy as np
import http.client
import json
from datetime import datetime
import io
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('TOKEN')
AUTH =  os.getenv('AUTH')

def get_pulls(log):
  conn = http.client.HTTPSConnection("www.fflogs.com")

  payload = "{\"query\":\"query{\\n  reportData{\\n\\t\\treport(code: \\\""+ log + "\\\"){\\n\\t\\t\\tstartTime\\n\\t\\t\\tfights(encounterID: 1065){\\n\\t\\t\\t\\tid\\n\\t\\t\\t\\tlastPhase\\n\\t\\t\\t\\tlastPhaseIsIntermission\\n\\t\\t\\t\\tstartTime\\n\\t\\t\\t\\tendTime\\n\\t\\t\\t\\t}\\n\\t\\t}\\n\\t}\\n}\\n\\t\"}"

  headers = {
    'Content-Type': "application/json",
    'Authorization': AUTH}
  conn.request("GET", "/api/v2/user?=", payload, headers)

  res = conn.getresponse()
  data = res.read()
  
  dec = json.loads(data.decode("utf-8"))

  pulls = []
  pull_time = []

  date = dec["data"]["reportData"]["report"]["startTime"]
  day = datetime.utcfromtimestamp(date/1000).strftime("%d-%m")

  for item in dec["data"]["reportData"]["report"]["fights"]:
    time = round((item["endTime"] - item["startTime"])/1000)
    if item["lastPhaseIsIntermission"] == False:
      pulls.append(item["lastPhase"])
      pull_time.append([item["lastPhase"],time])
    else:
      pulls.append(4.5)
      pull_time.append([4.5, time])
  return day, pulls, pull_time


def partial_time(fights, pull_time):
  pt = {}
  for day in pull_time.keys():
    pt[day] = {phase: round(sum(pull[1] for pull in pull_time[day] if pull[0]==phase)) for phase in fights.keys()}
   
  return pt

def total_time(fights, pull_time):
  pt = {}
  for day in pull_time.keys():
    pt[day] = {phase: round(sum(pull[1] for pull in pull_time[day] if pull[0]==phase)) for phase in fights.keys()}

  return {phase: sum(pt[day][phase] for day in pt.keys()) for phase in fights.keys()}

def bar_single(fights, day, pulls):
  pull_number = np.arange(1, len(pulls)+1, 1)

  fig, plot = plt.subplots(1,1, figsize=(max(6.4,len(pulls)/4,5),5))
  fig.set_tight_layout(True)
  plot.bar(pull_number, pulls, color=[fights[phase][1] for phase in pulls])

  plot.set_ylabel("Phase")
  plot.set_xlabel(day)
  plot.xaxis.set_label_coords(0.5, -0.13)
  plot.set_xticks(pull_number)
  plot.set_xticklabels(pull_number, rotation=90)

  handles = [plt.Rectangle((0,0),1,1, color=color[1]) for color in fights.values()]
  plot.legend(handles, [phase[0] for phase in fights.values()], loc='upper center', bbox_to_anchor=(0.5, -0.18), ncol=round((len(fights.keys()))/2))

  buf = io.BytesIO()
  fig.savefig(buf)
  buf.seek(0)
  fig.clear()
  plt.close(fig)
  return buf


def pie_single(fights, day, pull_time):
  pt_filtered = {k: v/60 for k, v in pull_time.items() if v}
  fights_filtered = {k: v for k, v in fights.items() if k in list(pt_filtered.keys())}
 
  
  fig, plot = plt.subplots(1,1, figsize=(7,7))
  plot.set_xlabel(day)
  fig.set_tight_layout(True)
  
  plot.pie(pt_filtered.values(), [0.03]*(len(pt_filtered.keys())),  autopct = lambda p: '{:.0f}%\n{:.0f}m'.format(p,round(sum(list(pt_filtered.values()))*p/100)), 
           labels = [v[0] for v in fights_filtered.values()], startangle=90, colors = [v[1] for v in fights_filtered.values()])


  buf = io.BytesIO()
  fig.savefig(buf)
  buf.seek(0)
  fig.clear()
  plt.close(fig)
  return buf

def pulls_length(fights, day, pull_time):
  pt_length = [p[1]/60 for p in pull_time]
  colors = []
  for x, y in zip(pt_length[:-1], pt_length[1:]):
    if x > y:
      colors.append("red")
    else:
      colors.append("green")
    
  pull_number = np.arange(1, len(pt_length)+1, 1)

  fig, plot = plt.subplots(1,1, figsize=(max(6.4,len(pt_length)/4,5),5))
  fig.set_tight_layout(True)
  for x, y, z in zip(pt_length[:-1], pt_length[1:], np.arange(0, len(pt_length), 1)):
    plot.plot([pull_number[z], pull_number[z+1]], [x, y], color = colors[z], marker='D', markeredgecolor='black', markerfacecolor='white')

  plot.set_ylabel("Pull length in minutes")
  plot.set_xlabel(day)
  plot.xaxis.set_label_coords(0.5, -0.1)
  plot.set_xticks(pull_number)
  plot.set_xticklabels(pull_number, rotation=90)
  
  buf = io.BytesIO()
  fig.savefig(buf)
  buf.seek(0)
  fig.clear()
  plt.close(fig)
  return buf

def bar_multi(fights, days, pulls):
  # p = for each phase there is an array of value whose elements are the number of wipes in that phase and the indeces are the days in the logs given order
  p = {1:[], 2:[], 3:[], 4:[], 4.5:[], 5:[], 6:[], 7:[]}
  for day in pulls.keys():
      for phase in fights.keys():
          p[phase].append(pulls[day].count(phase))
  
  days_number = np.arange(1, len(days)+1, 1)

  fig, plot = plt.subplots(1,1, figsize=(max(2*len(days),6.4),5))
  fig.set_tight_layout(True)

  for offset, phase in zip(np.arange(-0.3, 0.4, 0.1), fights.keys()):
      plot.bar(days_number + offset, p[phase], width=0.1, color=fights[phase][1])

  plot.set_ylabel("Amount of pulls")
  plot.set_xticks(days_number)
  plot.set_xticklabels(days, rotation=90)

  handles = [plt.Rectangle((0,0),1,1, color=color[1]) for color in fights.values()]
  plot.legend(handles, [phase[0] for phase in fights.values()], loc='upper center', bbox_to_anchor=(0.5, -0.18), ncol=round((len(fights.keys()))/2))

  buf = io.BytesIO()
  fig.savefig(buf)
  buf.seek(0)
  fig.clear()
  plt.close(fig)
  return buf

def pie_multi(fights, pull_time):
  pt_filtered = {k: v/60 for k, v in pull_time.items() if v}
  fights_filtered = {k: v for k, v in fights.items() if k in list(pt_filtered.keys())}
    
  fig, plot = plt.subplots(1,1, figsize=(7,7))
  fig.set_tight_layout(True)
  
  plot.pie(pt_filtered.values(), [0.03]*(len(pt_filtered.keys())),  autopct = lambda p: '{:.0f}%\n{:.0f}m'.format(p,round(sum(list(pt_filtered.values()))*p/100)), 
           labels = [v[0] for v in fights_filtered.values()], startangle=90, colors = [v[1] for v in fights_filtered.values()])


  buf = io.BytesIO()
  fig.savefig(buf)
  buf.seek(0)
  fig.clear()
  plt.close(fig)
  return buf
  
fights = {"dsr": {1: ["C&G", "#EF9958"],
                  2: ["Thordan 1","#62C562"],
                  3: ["Nidhogg","#E20000"],
                  4: ["Eyes","#D4F5EF"],
                  4.5: ["Rewind","#F0802C"],
                  5: ["Thordan 2","#073029"],
                  6: ["N&H","#39C6B6"],
                  7: ["El Thordan","#DFD624"]
                  }
          }

intents = discord.Intents.all()

bot = commands.Bot(command_prefix='%', intents=intents, help_command=None)
bot.activity = discord.Activity(type=discord.ActivityType.playing, name="%help")


@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!\n')

    for guild in bot.guilds:
      print("Server: {}\nOwner: {}\n".format(guild.name, guild.owner))
    print("####################################\n")

@bot.command()
async def help(ctx):
  await ctx.send("This bot allows you to transform your log(s) into bar and pie chart in order to have a better view of how your session(s) was.\n\n**%plot_s** creates for every single log used as input a bar chart showing on what phase every single pull ended and a pie chart showing how much time (percentage and minute wise) was spent on every phase.\nSyntax: %plot_s https://www.fflogs.com/reports/abcde/,https://www.fflogs.com/reports/vwxyz/\n\n**%plot_m** creates a single bar chart showing the number of wipes in every phase for every log used as input and a single pie chart showing how much time (percentage and minute wise) was spent on every phase.\nSyntax: %plot_m https://www.fflogs.com/reports/abcde/,https://www.fflogs.com/reports/vwxyz/\n\n\nThanks for using my bot and in case of any issue feel free to DM Sekkeisha#5511")

@bot.command()
async def plot_s(ctx, arg):
    print("Request plot_s from\nServer: {}\nAuthor: {}\n".format(ctx.guild.name, ctx.author))
    urls = []
    try:
      for item in arg.split(','):
        code = (item.split('/reports/')[1].split('/')[0])
        if len(code) == 16:
          urls.append(code)
        else:
          raise ValueError("The report code has not the correct length or is not valid.")
    except TypeError as e:
      print("EXCEPTION Log code not valid: {}".format(e))
      await ctx.send("Log code not valid")
    except ValueError as e:
      print("EXCEPTION Log code length: {}".format(e))
      await ctx.send(e)
    except Exception as e:
      print("EXCEPTION Log Read: {}".format(e))
      await ctx.send("Wrong input")

    logs = {}
    pull_time = {}

    try:
      for item in urls:
        day, pulls, p_time = get_pulls(item)
        logs[day] = pulls
        pull_time[day] = p_time
    except TypeError as e:
        print("EXCEPTION Log code not valid: {}".format(e))
        await ctx.send("Log code not valid")
    if len(logs.keys()):
      files = []
      partial_mins = {}
      total_mins = {}

      try:
        for item in list(logs.keys()):
          files.append(bar_single(fights["dsr"], item, logs[item]))
      except Exception as e:
        print("EXCEPTION Bar Single: {}".format(e))
        await ctx.send("Error occurred during bar single chart printing.")
      
      partial_mins = partial_time(fights["dsr"], pull_time)

      try:
        for item in partial_mins.keys():
          files.append(pie_single(fights["dsr"], item, partial_mins[item]))
      except Exception as e:
        print("EXCEPTION Pie Single: {}".format(e))
        await ctx.send("Error occurred during pie single chart printing.")

      try:
      for item in pull_time.keys():
        files.append(pulls_length(fights["dsr"], item, pull_time[item]))
      except Exception as e:
        print("EXCEPTION Pulls Length: {}".format(e))
        await ctx.send("Error occurred during pulls length chart printing.")
        
      for item in files:
        await ctx.send(file=discord.File(item, 'picture.png'))
        
@bot.command()
async def plot_m(ctx, arg):
    print("Request plot_m from\nServer: {}\nAuthor: {}\n".format(ctx.guild.name, ctx.author))
    urls = []
    try:
      for item in arg.split(','):
          code = (item.split('/reports/')[1].split('/')[0])
          if len(code) == 16:
            urls.append(code)
          else:
            raise ValueError("The report code has not the correct length or is not valid.")
    except ValueError as e:
      print("EXCEPTION Log code length: {}".format(e))
      await ctx.send(e)
    except Exception as e:
      print("EXCEPTION Log Read: {}".format(e))
      await ctx.send("Wrong input")

    logs = {}
    pull_time = {}
    try:
      for item in urls:
        day, pulls, p_time = get_pulls(item)
        logs[day] = pulls
        pull_time[day] = p_time
    except TypeError as e:
      print("EXCEPTION Log code not valid: {}".format(e))
      await ctx.send("Log code not valid")

    if len(logs.keys()):  
      files = []
      partial_mins = {}
      total_mins = {}

      try:
        files.append(bar_multi(fights["dsr"], list(logs.keys()), logs))
      except Exception as e:
        print("EXCEPTION Bar Multi: {}".format(e))
        await ctx.send("Error occurred during bar multi chart printing.")

      total_mins = total_time(fights["dsr"], pull_time)

      try:
        files.append(pie_multi(fights["dsr"], total_mins))
      except Exception as e:
        print("EXCEPTION Pie Multi: {}".format(e))
        await ctx.send("Error occurred during pie multi chart printing.")

      for item in files:
        await ctx.send(file=discord.File(item, 'picture.png'))
        
bot.run(TOKEN)
