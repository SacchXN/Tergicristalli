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
import pymongo

load_dotenv()

TOKEN = os.getenv('TOKEN')
AUTH = os.getenv('AUTH')
ID = os.getenv('ID')
PW = os.getenv('PW')


def get_pulls(log, encounter_id):
    conn = http.client.HTTPSConnection("www.fflogs.com")

    payload = "{\"query\":\"query{\\n  reportData{\\n\\t\\treport(code: \\\"" + log + "\\\"){\\n\\t\\t\\tstartTime\\n\\t\\t\\tfights(encounterID:" + encounter_id + "){\\n\\t\\t\\t\\tid\\n\\t\\t\\t\\tlastPhase\\n\\t\\t\\t\\tlastPhaseIsIntermission\\n\\t\\t\\t\\tstartTime\\n\\t\\t\\t\\tendTime\\n\\t\\t\\t\\t}\\n\\t\\t}\\n\\t}\\n}\\n\\t\"}"

    headers = {
        'Content-Type': "application/json",
        'Authorization': AUTH}
    conn.request("GET", "/api/v2/user?=", payload, headers)

    res = conn.getresponse()
    data = res.read()

    dec = json.loads(data.decode("utf-8"))
    if not dec["data"]["reportData"]["report"]["fights"]:
        raise Exception("One or more logs inserted have no pulls or the pulls in the log don't match the "
                        "selected encounter.")
    pulls = []

    date = dec["data"]["reportData"]["report"]["startTime"]
    first_pull_relative = dec["data"]["reportData"]["report"]["fights"][0]["startTime"]
    first_pull_absolute = date + first_pull_relative
    day = datetime.utcfromtimestamp(first_pull_absolute / 1000).strftime("%d-%m")

    for item in dec["data"]["reportData"]["report"]["fights"]:
        time = round((item["endTime"] - item["startTime"]) / 1000)
        if not item["lastPhaseIsIntermission"]:
            pulls.append([item["lastPhase"], time])
        else:
            if encounter_id == "1065":
                pulls.append([4.5, time])
            else:
                pulls.append([item["lastPhase"] + 0.5, time])
    return day, pulls


def partial_time(fight, pull):
    pt = {}
    for day in pull.keys():
        pt[day] = {phase: round(sum(pull[1] for pull in pull[day].values() if pull[0] == phase)) for phase in
                   fight.keys()}

    return pt


def total_time(fight, pulls):
    pt = {}
    for day in pulls.keys():
        pt[day] = {phase: round(sum(pull[1] for pull in pulls[day].values() if pull[0] == phase)) for phase in
                   fight.keys()}

    return {phase: sum(pt[day][phase] for day in pt.keys()) for phase in fight.keys()}


def single_bar(fight, day, pulls):
    pull_number = np.arange(1, len(pulls) + 1, 1)
    pt_length = [p[1] / 60 for p in pulls.values()]

    prog_point = max(p[0] for p in pulls.values())
    fights_filtered = {k: v for k, v in fight.items() if k <= prog_point}

    fig, chart = plt.subplots(1, 1, figsize=(max(6.4, len(pulls) / 4, 5), 5))
    fig.set_tight_layout(True)
    chart.bar(pull_number, pt_length, color=[fight[p[0]][1] for p in pulls.values()])

    chart.set_ylabel("Pull length")
    chart.set_xlabel(day)
    chart.xaxis.set_label_coords(0.5, 1.075)
    chart.set_xticks(pull_number)
    chart.set_xticklabels(pull_number, rotation=90)

    handles = [plt.Rectangle((0, 0), 1, 1, color=color[1]) for color in fights_filtered.values()]
    chart.legend(handles, [phase[0] for phase in fights_filtered.values()], loc="upper center",
                 bbox_to_anchor=(0.5, -0.18), ncol=round((len(fights_filtered.keys())) / 2))

    buf = io.BytesIO()
    fig.savefig(buf)
    buf.seek(0)
    fig.clear()
    plt.close(fig)
    return buf


def pie_single(fight, day, pulls):
    pt_filtered = {k: v / 60 for k, v in pulls.items() if v}
    fights_filtered = {k: v for k, v in fight.items() if k in list(pt_filtered.keys())}

    fig, chart = plt.subplots(1, 1, figsize=(7, 7))
    chart.set_xlabel(day)
    fig.set_tight_layout(True)

    chart.pie(pt_filtered.values(),
              autopct=lambda p: "{:.0f}%\n{:.0f}m".format(p, round(sum(list(pt_filtered.values())) * p / 100)),
              labels=[v[0] for v in fights_filtered.values()], startangle=90,
              colors=[v[1] for v in fights_filtered.values()])

    buf = io.BytesIO()
    fig.savefig(buf)
    buf.seek(0)
    fig.clear()
    plt.close(fig)
    return buf


"""
def pulls_length(fight, day, pull_time, dark_mode):
    if dark_mode:
        plt.style.use('dark_background')
    else:
        plt.style.use('default')

    pt_length = [p[1] / 60 for p in pull_time]
    colors = []
    for x, y in zip(pt_length[:-1], pt_length[1:]):
        if x > y:
            colors.append("red")
        else:
            colors.append("green")

    pull_number = np.arange(1, len(pt_length) + 1, 1)

    fig, chart = plt.subplots(1, 1, figsize=(max(6.4, len(pt_length) / 4, 5), 5))
    fig.set_tight_layout(True)

    for x, y, z in zip(pt_length[:-1], pt_length[1:], np.arange(0, len(pt_length), 1)):
        chart.plot([pull_number[z], pull_number[z + 1]], [x, y], color=colors[z], marker='D', markeredgecolor='black',
                   markerfacecolor='white')

    chart.set_ylabel("Pull length in minutes")
    chart.set_xlabel(day)
    chart.xaxis.set_label_coords(0.5, 1.05)
    chart.set_xticks(pull_number)
    chart.set_xticklabels(pull_number, rotation=90)

    buf = io.BytesIO()
    fig.savefig(buf)
    buf.seek(0)
    fig.clear()
    plt.close(fig)
    return buf
"""


def multi_bar_compact(fight, days, pulls):
    # For each phase there is an array of value whose elements are the number of wipes in that phase and the indeces
    # are the days in the logs given order.
    p = {phase: [] for phase in fight.keys()}
    for day in pulls.keys():
        for phase in fight.keys():
            p[phase].append([pull[0] for pull in pulls[day].values()].count(phase))

    days_number = np.arange(1, len(days) + 1, 1)

    prog_point = 0
    total_time_spent = 0
    total_pull = 0
    for day in pulls.keys():
        prog_point = max(prog_point, max([pull[0] for pull in pulls[day].values()]))
        total_time_spent += sum([pull[1] for pull in pulls[day].values()])
        total_pull += len(pulls[day])
    fights_filtered = {k: v for k, v in fight.items() if k <= prog_point}

    fig, chart = plt.subplots(1, 1, figsize=(max(2 * len(days), 7), 5))
    fig.set_tight_layout(True)
    plt.text(0, 1.02, "Total time: {}:{}\nTotal pulls: {}".format(str(round(total_time_spent / 3600)),
                                                                  str(round(total_time_spent % 60)),
                                                                  str(total_pull)), fontsize=10,
             transform=chart.transAxes)

    for offset, phase in zip(np.arange(-0.4, 0.4, 0.1), fights_filtered.keys()):
        chart.bar(days_number + offset, p[phase], width=0.1, color=fights_filtered[phase][1])

    chart.set_ylabel("Amount of pulls")
    chart.set_xticks(days_number)
    chart.set_xticklabels(days, rotation=90)

    handles = [plt.Rectangle((0, 0), 1, 1, color=color[1]) for color in fights_filtered.values()]
    chart.legend(handles, [phase[0] for phase in fights_filtered.values()], loc='upper center',
                 bbox_to_anchor=(0.5, -0.18), ncol=round((len(fights_filtered.keys())) / 2))

    buf = io.BytesIO()
    fig.savefig(buf)
    buf.seek(0)
    fig.clear()
    plt.close(fig)
    return buf


def multi_bar_split(fight, days, pulls):
    days_number = {days[0]: 0}
    for x, y in zip(days[:-1], days[1:]):
        days_number[y] = ((len(pulls[y]) + len(pulls[x])) / 10) + days_number[x]

    prog_point = 0
    total_time_spent = 0
    total_pull = 0
    for day in pulls.keys():
        prog_point = max(prog_point, max([pull[0] for pull in pulls[day].values()]))
        total_time_spent += sum([pull[1] for pull in pulls[day].values()])
        total_pull += len(pulls[day])

    fights_filtered = {k: v for k, v in fight.items() if k <= prog_point}
    fig, chart = plt.subplots(1, 1, figsize=(max(2 * len(days), 7), 5))
    fig.set_tight_layout(True)
    plt.text(0, 1.02, "Total time: {}:{}\nTotal pulls: {}".format(str(round(total_time_spent / 3600)),
                                                                  str(round(total_time_spent % 60)),
                                                                  str(total_pull)), fontsize=10,
             transform=chart.transAxes)
    for day in days_number:
        for offset, pull in zip(np.arange(-0.175 * (len(pulls[day])) / 2, 0.175 * (len(pulls[day])) / 2, 0.175),
                                [p for p in pulls[day].values()]):
            chart.bar(days_number[day] + offset, pull[1] / 60, width=0.1, color=fights_filtered[pull[0]][1])

    chart.set_ylabel("Pull length")
    chart.set_xticks([v for v in days_number.values()])
    chart.set_xticklabels(days)

    handles = [plt.Rectangle((0, 0), 1, 1, color=color[1]) for color in fights_filtered.values()]
    chart.legend(handles, [phase[0] for phase in fights_filtered.values()], loc='upper center',
                 bbox_to_anchor=(0.5, -0.18), ncol=round((len(fights_filtered.keys())) / 2))

    buf = io.BytesIO()
    fig.savefig(buf)
    buf.seek(0)
    fig.clear()
    plt.close(fig)
    return buf


def multi_pie(fight, pulls):
    pt_filtered = {k: v / 60 for k, v in pulls.items() if v}
    fights_filtered = {k: v for k, v in fight.items() if k in list(pt_filtered.keys())}

    fig, chart = plt.subplots(1, 1, figsize=(7, 7))
    fig.set_tight_layout(True)

    chart.pie(pt_filtered.values(),
              autopct=lambda p: '{:.0f}%\n{:.0f}m'.format(p, round(sum(list(pt_filtered.values())) * p / 100)),
              labels=[v[0] for v in fights_filtered.values()], startangle=90,
              colors=[v[1] for v in fights_filtered.values()])

    buf = io.BytesIO()
    fig.savefig(buf)
    buf.seek(0)
    fig.clear()
    plt.close(fig)
    return buf


fights = {"dsr": [
    {"encounter": "1065"},
    {1: ["A&C&G", "#EF9958"],
     2: ["Thordan 1", "#62C562"],
     3: ["Nidhogg", "#E20000"],
     4: ["Eyes", "#A4D5DF"],
     4.5: ["Rewind", "#F0802C"],
     5: ["Thordan 2", "#073029"],
     6: ["N&H", "#39C6B6"],
     7: ["El Thordan", "#DFD624"]}
],
    "tea": [
        {"encounter": "1062"},
        {1: ["PepsiMan", "#036BFC"],
         1.5: ["Limit Cut", "#ED6C4C"],
         2: ["BJ&CC", "#92D132"],
         2.5: ["Temp. Stasis", "#BAC9A3"],
         3: ["Alex Prime", "#F7EA54"],
         4: ["Perfect Alex", "#FCE3F8"]}
    ],
    "ucob": [
        {"encounter": "1060"},
        {1: ["Twintania", "#0B7533"],
         2: ["Nael", "#9D5EDB"],
         3: ["Bahamut", "#5EB6DB"],
         4: ["T&N", "#E62E25"],
         5: ["Golden Bahamut", "#F5E31D"]}
    ],
    "uwu": [
        {"encounter": "1061"},
        {1: ["Garuda", "#169E18"],
         2: ["Ifrit", "#F03611"],
         3: ["Titan", "#91790F"],
         4: ["Magitek bits", "#A3A093"],
         5: ["Ultima", "#3BF2F5"]}
    ]
}
servers_requesting = {}
"""
Used as a "cache" storing servers color_theme preference and logs uploaded during the last session.

servers_requesting = {
                     (str)server_id: {
                                     (str)"encounter": None/(str)"ucob"/"uwu"/"tea"/"dsr"/...,
                                     (str)"color_theme": (str)"default"/"dark_background",
                                     (array of str)"urls": [(str)url1, (str)url2, ...],
                                     ...
                                     }
                     ...
                     }
"""

intents = discord.Intents.all()

bot = commands.Bot(command_prefix='%', intents=intents, help_command=None)
bot.activity = discord.Activity(type=discord.ActivityType.playing, name="%help")
client = pymongo.MongoClient(
        "mongodb+srv://{}:{}@clusterc.g5clm.mongodb.net/?retryWrites=true&w=majority".format(ID, PW))


@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!\n')

    for guild in bot.guilds:
        print("Server: {}\nOwner: {}\n".format(guild.name, guild.owner))
    print("####################################\n")


@bot.command()
async def help(ctx):
    await ctx.send("This bot allows you to transform your log(s) into bar and pie charts in order to have a better "
                   "view of how your session was.\n\nFirst of all, load the logs you want to "
                   "analyze through **%load**.\nExample: %load https://www.fflogs.com/reports/0123456789abcdef/,"
                   "https://www.fflogs.com/reports/abcdef0123456789/\n\nThe bot has read the logs url(s) if you "
                   "receive the message `Logs url(s) have been read.`You have to now set the encounter you want to "
                   "analyze using **%encounter**. Unless you want to change fight to analyze you don't have to set "
                   "this value everytime since it is stored by the bot.\nExample: %encounter dsr\nThe fights you "
                   "can choose between are "
                   "**ucob**, **uwu**, **tea** and **dsr**.\n\nYou can now decide what kind of chart you want "
                   "to create: _single_(s) for individual view for each log and _multi_(m) for an aggregate view."
                   "\n\n**Single**\n"
                   "**%plot s_bar**: bar chart for each log uploaded showing for each pull what was its pull length "
                   "and wipe phase.\n**%plot s_pie**: pie chart for each log uploaded showing the percentage of time "
                   "(in minutes) spent for each phase.\n\n**Multi**\n**%plot m_bar_split**: bar chart for all "
                   "loaded logs showing for each pull what was its pull length and wipe phase.\n"
                   "**%plot m_bar_compact**: bar chart showing for each day the amount of wipe pulls for each phase.\n"
                   "**%plot m_pie**: pie chart for all loaded logs showing the percentage of time (in minutes) spent "
                   "for each phase.\n**m_bar_compact** and **m_bar_split** also show the amount of total pulls and"
                   " time spent.\n\nThe bot currently allows you to create charts using both light, "
                   "**%color_theme light**, and dark, **%color_theme dark** theme.")
    await ctx.send("For more info and image examples for each chart you can check the GitHub page of the bot: "
                   "https://github.com/SacchXN/Tergicristalli\nBot invite link:"
                   " https://discord.com/api/oauth2/authorize?client_id=979718043993247774&permissions=35840&scope=bot"
                   "\nIn case you have any suggestions for adding new functionalities to the bot or any issues with "
                   "it, feel free to dm Sekkeisha#5511")


@bot.command()
async def color_theme(ctx, arg):
    if arg == 'dark':
        try:
            client['tergicristalli']['servers'].update_one({"id": str(ctx.guild.id)}, {"$set": {
                "settings.color_theme": "dark_background"}})
            if str(ctx.guild.id) in servers_requesting.keys():
                servers_requesting[str(ctx.guild.id)]["color_theme"] = "dark_background"
            await ctx.send("Dark theme has been set.")
        except Exception:
            print(Exception)
            await ctx.send("An error has occurred during color theme selection")
    elif arg == 'light':
        try:
            client['tergicristalli']['servers'].update_one({"id": str(ctx.guild.id)}, {"$set": {
                "settings.color_theme": "default"}})
            if str(ctx.guild.id) in servers_requesting.keys():
                servers_requesting[str(ctx.guild.id)]["color_theme"] = "default"
            await ctx.send("Light theme has been set.")
        except Exception:
            print(Exception)
            await ctx.send("An error has occurred during color theme selection")
    else:
        await ctx.send("Parameter used is not correct.")


@bot.command()
async def encounter(ctx, arg):
    if arg in fights.keys():
        try:
            client['tergicristalli']['servers'].update_one({"id": str(ctx.guild.id)}, {"$set": {
                "settings.encounter": arg}})
            if str(ctx.guild.id) in servers_requesting.keys():
                servers_requesting[str(ctx.guild.id)]["encounter"] = arg
        except Exception:
            print(Exception)
            await ctx.send("An error has occurred during encounter selection.")
        await ctx.send("Encounter has been set.")
    else:
        await ctx.send("Parameter used is not correct.")


@bot.event
async def on_guild_join(guild):
    print("The server {} has been joined\nAdmin: {}\n\n".format(guild.name, guild.owner))
    try:
        client['tergicristalli']['servers'].insert_one({"id": str(guild.id), "settings": {
            "encounter": None, "color_theme": "default"}})
    except Exception:
        print(Exception)


@bot.event
async def on_guild_remove(guild):
    print("Got kicked from {}".format(guild.name))
    try:
        client['tergicristalli']['servers'].delete_one({"id": str(guild.id)})
    except Exception:
        print(Exception)


@bot.event
async def on_command_error(ctx, error):
    print(error)
    await ctx.send("Command not found, type %help for commands info.")


@bot.command()
async def load(ctx, arg=None):
    if arg is not None:
        try:
            print("Request load from\nServer: {}\nAuthor: {}\n".format(ctx.guild.name, ctx.author))
            # Checks if server making a request has already done a request in this bot session. If not, add it to
            # servers_requesting.
            if ctx.guild.id not in servers_requesting.keys():
                fltr = {
                    'id': str(ctx.guild.id)
                }
                result = list(client['tergicristalli']['servers'].find(
                    filter=fltr,
                ))[0]["settings"]
                if result:
                    servers_requesting[str(ctx.guild.id)] = dict({"encounter": result["encounter"],
                                                                  "color_theme": result["color_theme"],
                                                                  "urls": None})
                else:
                    try:
                        client['tergicristalli']['servers'].insert_one({"id": str(ctx.guild.id), "settings": {
                            "encounter": None, "color_theme": "default"}})
                    except Exception:
                        print(Exception)
                    servers_requesting[str(ctx.guild.id)] = dict({"encounter": None, "color_theme": "default",
                                                                  "urls": None})
        except Exception:
            print(Exception)
            await ctx.send("An error occurred during log url(s) reading, retry.")

        # Input validation
        urls = []
        try:
            for item in arg.split(','):
                code = (item.split('/reports/')[1].split('/')[0])
                if len(code) == 16:
                    urls.append(code)
                else:
                    raise ValueError("The report code has not the correct length.")
        except TypeError as e:
            print("EXCEPTION Log code not valid: {}".format(e))
            await ctx.send("Log code not valid")
        except ValueError as e:
            print("EXCEPTION Log code length: {}".format(e))
            await ctx.send(e)
        except Exception as e:
            print("EXCEPTION Log Read: {}".format(e))
            await ctx.send("Wrong input")

        if urls:
            servers_requesting[str(ctx.guild.id)]["urls"] = urls
            print("Logs correctly loaded.\nServer: {}\nAuthor: {}\n".format(ctx.guild.name, ctx.author))
            await ctx.send("Logs urls(s) have been read.")
    else:
        print("No logs have been inserted.\nServer: {}\nAuthor: {}\n".format(ctx.guild.name, ctx.author))
        await ctx.send("No logs urls(s) have been inserted.")


@bot.command()
async def plot(ctx, arg=None):
    if servers_requesting[str(ctx.guild.id)]["encounter"] is not None:
        if servers_requesting[str(ctx.guild.id)]["urls"] is not None:
            if arg is not None:
                logs = {}
                """
                logs = {
                       (str)"day": {
                                   (int)pull_number: [(int)phase wiped on, (int)pull length in seconds],
                                   ...
                                   }
                       ...
                       }
                """
                files = []
                # Extracts data from the urls.
                try:
                    for item in servers_requesting[str(ctx.guild.id)]["urls"]:
                        day, pulls = get_pulls(item,
                                               fights[servers_requesting[str(ctx.guild.id)]["encounter"]][0][
                                                   "encounter"])
                        # Check in case two logs from the same day are being provided and in case merge them.
                        if day not in logs.keys():
                            logs[day] = {k: v for k, v in enumerate(pulls, start=1)}
                        else:
                            for k, v in enumerate(pulls, start=max(p for p in logs[day].keys()) + 1):
                                logs[day][k] = v
                except Exception as e:
                    print("EXCEPTION API error: {}".format(e))
                    await ctx.send(e)
                    arg = "error"

                # Set color_theme or not.
                plt.style.use(servers_requesting[str(ctx.guild.id)]["color_theme"])

                # Chart choice.
                match arg:
                    case 's_bar':
                        print("Single bar chart request.\nServer: {}\nAuthor: {}\n".format(ctx.guild.name, ctx.author))
                        try:
                            for day in list(logs.keys()):
                                files.append(single_bar(fights[servers_requesting[str(ctx.guild.id)]["encounter"]][1],
                                                        day, logs[day]))
                        except Exception as e:
                            print("EXCEPTION Single Bar: {}".format(e))
                            await ctx.send("Error occurred during single bar chart printing.")
                    case 's_pie':
                        print("Single pie chart request.\nServer: {}\nAuthor: {}\n".format(ctx.guild.name, ctx.author))
                        partial_mins = partial_time(fights[servers_requesting[str(ctx.guild.id)]["encounter"]][1], logs)
                        try:
                            for day in partial_mins.keys():
                                files.append(pie_single(fights[servers_requesting[str(ctx.guild.id)]["encounter"]][1],
                                                        day, partial_mins[day]))
                        except Exception as e:
                            print("EXCEPTION Single Pie: {}".format(e))
                            await ctx.send("Error occurred during single pie chart printing.")
                    case 'm_bar_compact':
                        print("Multi bar compact chart request.\nServer: {}\nAuthor: {}\n".format(ctx.guild.name,
                                                                                                  ctx.author))
                        try:
                            files.append(multi_bar_compact(
                                fights[servers_requesting[str(ctx.guild.id)]["encounter"]][1], list(logs.keys()), logs))
                        except Exception as e:
                            print("EXCEPTION Multi Bar Compact: {}".format(e))
                            await ctx.send("Error occurred during bar multi chart printing.")
                    case 'm_bar_split':
                        print("Multi bar split chart request.\nServer: {}\nAuthor: {}\n".format(ctx.guild.name,
                                                                                                ctx.author))
                        try:
                            files.append(multi_bar_split(fights[servers_requesting[str(ctx.guild.id)]["encounter"]][1],
                                                         list(logs.keys()), logs))
                        except Exception as e:
                            print("EXCEPTION Multi Bar Split: {}".format(e))
                            await ctx.send("Error occurred during bar multi chart printing.")
                    case 'm_pie':
                        print("Multi pie chart request.\nServer: {}\nAuthor: {}\n".format(ctx.guild.name, ctx.author))
                        total_mins = total_time(fights[servers_requesting[str(ctx.guild.id)]["encounter"]][1], logs)
                        try:
                            files.append(multi_pie(fights[servers_requesting[str(ctx.guild.id)]["encounter"]][1],
                                                   total_mins))
                        except Exception as e:
                            print("EXCEPTION Pie Multi: {}".format(e))
                            await ctx.send("Error occurred during pie multi chart printing.")
                    case _:
                        print("Error in get_pulls.\n")
                        await ctx.send("Retry.")
                for item in files:
                    await ctx.send(file=discord.File(item, 'picture.png'))
            else:
                await ctx.send(
                    "No chart command has been selected.\nServer: {}\nAuthor: {}\n".format(ctx.guild.name, ctx.author))
        else:
            await ctx.send(
                "Current server has no logs loaded.\nServer: {}\nAuthor: {}\n".format(ctx.guild.name, ctx.author))
    else:
        await ctx.send("Current server has no encountered selected.")


bot.run(TOKEN)
