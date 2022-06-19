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
AUTH = os.getenv('AUTH')


def get_pulls(log):
    conn = http.client.HTTPSConnection("www.fflogs.com")

    payload = "{\"query\":\"query{\\n  reportData{\\n\\t\\treport(code: \\\"" + log + "\\\"){\\n\\t\\t\\tstartTime\\n\\t\\t\\tfights(encounterID: 1065){\\n\\t\\t\\t\\tid\\n\\t\\t\\t\\tlastPhase\\n\\t\\t\\t\\tlastPhaseIsIntermission\\n\\t\\t\\t\\tstartTime\\n\\t\\t\\t\\tendTime\\n\\t\\t\\t\\t}\\n\\t\\t}\\n\\t}\\n}\\n\\t\"}"

    headers = {
        'Content-Type': "application/json",
        'Authorization': AUTH}
    conn.request("GET", "/api/v2/user?=", payload, headers)

    res = conn.getresponse()
    data = res.read()

    dec = json.loads(data.decode("utf-8"))

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
            pulls.append([4.5, time])
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

    p = {1: [], 2: [], 3: [], 4: [], 4.5: [], 5: [], 6: [], 7: []}
    for day in pulls.keys():
        for phase in fight.keys():
            p[phase].append([pull[0] for pull in pulls[day].values()].count(phase))

    days_number = np.arange(1, len(days) + 1, 1)

    prog_point = 0
    for day in pulls.keys():
        prog_point = max(prog_point, max([pull[0] for pull in pulls[day].values()]))
    fights_filtered = {k: v for k, v in fight.items() if k <= prog_point}

    fig, chart = plt.subplots(1, 1, figsize=(max(2 * len(days), 7), 5))
    fig.set_tight_layout(True)

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
    for day in pulls.keys():
        prog_point = max(prog_point, max([pull[0] for pull in pulls[day].values()]))
    fights_filtered = {k: v for k, v in fight.items() if k <= prog_point}
    fig, chart = plt.subplots(1, 1, figsize=(max(2 * len(days), 7), 5))
    fig.set_tight_layout(True)

    for day in days_number:
        for offset, pull in zip(np.arange(-0.175 * (len(pulls[day])) / 2, 0.175 * (len(pulls[day])) / 2, 0.175),
                                [p for p in pulls[day].values()]):
            chart.bar(days_number[day] + offset, pull[1]/60, width=0.1, color=fights_filtered[pull[0]][1])

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


fights = {"dsr": {1: ["A&C&G", "#EF9958"],
                  2: ["Thordan 1", "#62C562"],
                  3: ["Nidhogg", "#E20000"],
                  4: ["Eyes", "#D4F5EF"],
                  4.5: ["Rewind", "#F0802C"],
                  5: ["Thordan 2", "#073029"],
                  6: ["N&H", "#39C6B6"],
                  7: ["El Thordan", "#DFD624"]
                  }
          }
servers_requesting = {}
"""
Used as a "cache" storing servers dark_theme preference and logs uploaded during the last session.

servers_requesting = {
                     (str)server_id: {
                                     (str)"dark_theme": (bool)True/False,
                                     (array of str)"urls": [(str)url1, (str)url2, ...],
                                     ...
                                     }
                     ...
                     }
"""

intents = discord.Intents.all()

bot = commands.Bot(command_prefix='%', intents=intents, help_command=None)
bot.activity = discord.Activity(type=discord.ActivityType.playing, name="%help")


@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!\n')

    for guild in bot.guilds:
        print("Server: {}\nOwner: {}\n".format(guild.name, guild.owner))
    print("####################################\n")

    try:
        with open(os.getcwd() + r"\servers.json", "r") as f:
            servers = json.load(f)
            print(servers)
    except OSError:
        print("Error during server.json loading.")


@bot.command()
async def help(ctx):
    await ctx.send("This bot allows you to transform your log(s) into bar and pie charts in order to have a better "
                   "view of how your session was.\n\nFirst of all, make sure to have loaded in the logs you want to "
                   "analyze through **%load**.\n\nExample: %load https://www.fflogs.com/reports/0123456789abcdef/,"
                   "https://www.fflogs.com/reports/abcdef0123456789/\nYou have loaded your logs correctly if you "
                   "receive the message `Logs correctly loaded.`\n\nYou can now decide what kind of chart you want "
                   "the bot to print based on your preferences. If you are interested in an individual view for each "
                   "log you loaded you may want to use _single_(s) charts while if you are interested in an "
                   "aggregate view of all the logs you loaded you may want to use _multi_(m) charts.\n\n**Single**\n"
                   "**%plot s_bar**: bar chart for each log uploaded showing for each pull what was its pull length "
                   "and wipe phase.\n**%plot s_pie**: pie chart for each log uploaded showing the percentage of time "
                   "(in minutes) spent for each phase.\n\n**Multi**\n**%plot m_bar_split**: bar chart for all "
                   "loaded logs showing for each pull what was its pull length and wipe phase.\n"
                   "**%plot m_bar_compact**: bar chart showing for each day the amount of wipe pulls for each phase.\n"
                   "**%plot m_pie**: pie chart for all loaded logs showing the percentage of time (in minutes) spent "
                   "for each phase.\n\nIn case you want the charts to be created using dark theme, you can enable that"
                   " through the command **%dark_theme enabled**. In case you want to go back to light theme charts "
                   "you can do that through **%dark_theme disabled**.\n\n\nFor more info and image examples for each "
                   "chart you can check the GitHub page of the bot: github.com/SacchXN/Tergicristalli\nBot invite link:"
                   " https://discord.com/api/oauth2/authorize?client_id=979718043993247774&permissions=35840&scope=bot"
                   "\nIn case of any issues with the bot feel free to dm Sekkeisha#5511")


@bot.command()
async def dark_theme(ctx, arg):
    with open(os.getcwd() + r"\servers.json", "r") as f:
        servers = json.load(f)
    if arg == 'enabled':
        servers[str(ctx.guild.id)] = True
        if str(ctx.guild.id) in servers_requesting.keys():
            servers_requesting[str(ctx.guild.id)]["dark_theme"] = True
        await ctx.send("Dark mode enabled.")
    elif arg == 'disabled':
        servers[str(ctx.guild.id)] = False
        if str(ctx.guild.id) in servers_requesting.keys():
            servers_requesting[str(ctx.guild.id)]["dark_theme"] = False
        await ctx.send("Dark mode disabled.")
    else:
        await ctx.send("Parameter used is not correct.")
    with open(os.getcwd() + r"\servers.json", "w") as f:
        json.dump(servers, f)


@bot.event
async def on_guild_join(guild):
    print("The server {} has been joined\nAdmin: {}\n\n".format(guild.name, guild.owner))
    try:
        with open(os.getcwd() + r"\servers.json", "r+") as f:
            servers = json.load(f)
            f.seek(0)
            f.truncate()
            servers[str(guild.id)] = False
            json.dump(servers, f)
    except OSError:
        print("Error during server.json loading.")


@bot.event
async def on_guild_remove(guild):
    print("Got kicked from {}".format(guild.name))
    try:
        with open(os.getcwd() + r"\servers.json", "r+") as f:
            servers = json.load(f)
            f.seek(0)
            f.truncate()
            del servers[str(guild.id)]
            json.dump(servers, f)
    except OSError:
        print("Error during server.json loading.")


@bot.event
async def on_command_error(ctx, error):
    print(error)
    await ctx.send("Command not found, type %help for commands info.")


@bot.command()
async def load(ctx, arg=None):
    if arg is not None:
        print("Request load from\nServer: {}\nAuthor: {}\n".format(ctx.guild.name, ctx.author))
        # Checks if server making a request has already done a request in this bot session. If not, add it to
        # servers_requesting.
        if ctx.guild.id not in servers_requesting.keys():
            with open(os.getcwd() + r"\servers.json", "r") as f:
                servers = json.load(f)
                servers_requesting[str(ctx.guild.id)] = dict({"dark_theme": servers[str(ctx.guild.id)], "urls": None})
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
            await ctx.send("Logs correctly loaded.")
    else:
        await ctx.send("No urls have been inserted.")


@bot.command()
async def plot(ctx, arg=None):
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
                    day, pulls = get_pulls(item)
                    # Check in case two logs from the same day are being provided and in case merge them.
                    if day not in logs.keys():
                        logs[day] = {k: v for k, v in enumerate(pulls, start=1)}
                    else:
                        for k, v in enumerate(pulls, start=max(p for p in logs[day].keys())+1):
                            logs[day][k] = v
            except TypeError as e:
                print("EXCEPTION API error: {}".format(e))
                await ctx.send("Log code not valid")
            # Set dark_theme or not.
            if servers_requesting[str(ctx.guild.id)]["dark_theme"]:
                plt.style.use('dark_background')
            else:
                plt.style.use('default')
            # Chart choice.
            match arg:
                case 's_bar':
                    try:
                        for day in list(logs.keys()):
                            files.append(single_bar(fights["dsr"], day, logs[day]))
                    except Exception as e:
                        print("EXCEPTION Single Bar: {}".format(e))
                        await ctx.send("Error occurred during single bar chart printing.")
                case 's_pie':
                    partial_mins = partial_time(fights["dsr"], logs)
                    try:
                        for day in partial_mins.keys():
                            files.append(pie_single(fights["dsr"], day, partial_mins[day]))
                    except Exception as e:
                        print("EXCEPTION Single Pie: {}".format(e))
                        await ctx.send("Error occurred during single pie chart printing.")
                case 'm_bar_compact':
                    try:
                        files.append(multi_bar_compact(fights["dsr"], list(logs.keys()), logs))
                    except Exception as e:
                        print("EXCEPTION Multi Bar Compact: {}".format(e))
                        await ctx.send("Error occurred during bar multi chart printing.")
                case 'm_bar_split':
                    try:
                        files.append(multi_bar_split(fights["dsr"], list(logs.keys()), logs))
                    except Exception as e:
                        print("EXCEPTION Multi Bar Split: {}".format(e))
                        await ctx.send("Error occurred during bar multi chart printing.")
                case 'm_pie':
                    total_mins = total_time(fights["dsr"], logs)
                    try:
                        files.append(multi_pie(fights["dsr"], total_mins))
                    except Exception as e:
                        print("EXCEPTION Pie Multi: {}".format(e))
                        await ctx.send("Error occurred during pie multi chart printing.")
            for item in files:
                await ctx.send(file=discord.File(item, 'picture.png'))
        else:
            await ctx.send("No chart command has been selected.")
    else:
        await ctx.send("Current server has no urls loaded.")


bot.run(TOKEN)
