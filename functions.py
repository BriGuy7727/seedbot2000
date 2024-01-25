import json
import os.path
import random
import string
import sqlite3
from zipfile import ZipFile

import aiohttp
import discord
import requests


async def generate_v1_seed(flags, seed_desc, dev):
    if dev == "dev":
        url = "https://devapi.ff6worldscollide.com/api/seed"
        if seed_desc:
            payload = json.dumps({
                "key": os.getenv("dev_api_key"),
                "flags": flags,
                "description": seed_desc
            })
            headers = {
                'Content-Type': 'application/json'
            }
        else:
            payload = json.dumps({
                "key": os.getenv("dev_api_key"),
                "flags": flags
            })
            headers = {
                'Content-Type': 'application/json'
            }
    else:
        url = "https://api.ff6worldscollide.com/api/seed"
        if seed_desc:
            payload = json.dumps({
                "key": os.getenv("new_api_key"),
                "flags": flags,
                "description": seed_desc
            })
            headers = {
                'Content-Type': 'application/json'
            }
        else:
            payload = json.dumps({
                "key": os.getenv("new_api_key"),
                "flags": flags
            })
            headers = {
                'Content-Type': 'application/json'
            }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, data=payload) as r:
            data = await r.json()
            if 'url' not in data:
                return KeyError(f'API returned {data} for the following flagstring:\n```{flags}```')
            return data['url']


def get_vers(s):
    url = "https://api.ff6worldscollide.com/api/wc"
    response = requests.request("GET", url)
    data = response.json()
    return data


def init_db():
    con = sqlite3.connect('db/seeDBot.sqlite')
    cur = con.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS presets (preset_name text, creator_id int, creator_name text, created_at text, flags text, description text, arguments text, official int)")
    cur.execute("CREATE TABLE IF NOT EXISTS seedlist (creator_id int, creator_name text, seed_type text, share_url text, timestamp text, server_name text, server_id int, channel_name text, channel_id int)")
    con.commit()
    con.close()


async def update_seedlist(m):
    con = sqlite3.connect('db/seeDBot.sqlite')
    cur = con.cursor()
    try:
        cur.execute("INSERT INTO seedlist VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (m['creator_id'], m['creator_name'], m['seed_type'], m['share_url'], m['timestamp'], m['server_name'], m['server_id'], m['channel_name'], m['channel_id']))
        con.commit()
        con.close()
    except Exception as e:
        print(f"Something went wrong: {e}")


def update_metrics(m):
    if not os.path.exists('db/metrics.json') or os.path.getsize('db/metrics.json') == 0:
        with open('db/metrics.json', 'w') as new_file:
            new_file.write(json.dumps({}))
    try:
        m_data = json.load(open('db/metrics.json'))
        index = len(m_data) + 1
        m_data[index] = m
        with open('db/metrics.json', 'w') as update_file:
            update_file.write(json.dumps(m_data))
    except json.JSONDecodeError as e:
        print(f'There was an issue writing to the metric file: {e}, please review {m}')


def last(args):
    try:
        with open("db/metrics.json") as f:
            j = json.load(f)
            lenmetrics = len(j)
            lenarg = int(args[0])
            if lenarg > lenmetrics:
                lastmsg = f"You asked for the last {lenarg} seeds, but I've only rolled {lenmetrics}! Slow down, turbo!"
            elif lenarg <= 0:
                lastmsg = f"I see you, WhoDat."
            else:
                newj = []
                for x in reversed(j):
                    newj.append(j[str(x)])
                counter = 0
                lastmsg = f'Here are the last {lenarg} seeeds rolled:\n'
                while counter < lenarg:
                    lastmsg += f'> {newj[counter]["creator_name"]} rolled a' \
                               f' {newj[counter]["seed_type"]} seed: {newj[counter]["share_url"]}\n '
                    counter += 1
    except (ValueError, IndexError):
        lastmsg = f'Invalid input! Try !last <number>'
    return lastmsg


def myseeds(author):
    with open("db/metrics.json") as f:
        j = json.load(f)
        x = ""
        for k in j:
            if author.id == j[k]['creator_id']:
                x += f'{j[k]["timestamp"]}: {j[k]["seed_type"]} @ {j[k]["share_url"]}\n'
        f.close()
        if x != "":
            with open('db/myseeds.txt', 'w') as update_file:
                update_file.write(x)
            update_file.close()
            has_seeds = True
        else:
            has_seeds = False
    return has_seeds


def getmetrics():
    with open("db/metrics.json") as f:
        counts = {}
        j = json.load(f)
        seedcount = 0
        metric_list = []
        for k in j:
            if ("request_channel" in j[k] and "test" not in j[k]["request_channel"]) or "request_channel" not in j[k]:
                seedcount += 1
                metric_list.append(j[k])
                creator = j[k]['seed_type']
                if not creator in counts.keys():
                    counts[creator] = 0
                counts[creator] += 1
        firstseed = j['1']['timestamp']
        creator_counts = []
        for creator in reversed({k: v for k, v in sorted(counts.items(), key=lambda item: item[1])}):
            creator_counts.append(tuple((creator, counts[creator])))
        top5 = creator_counts[:5]
        m_msg = f"Since {firstseed}, I've rolled {seedcount} seeds! The top 5 seed types are:\n"
        for roller_seeds in top5:
            roller = roller_seeds[0]
            seeds = roller_seeds[1]
            m_msg += f"> **{roller}**: rolled {seeds} times\n"
        f.close()
    return m_msg


async def add_preset(message):
    flagstring = ' '.join(message.content.split("--flags")[1:]).split("--")[0].strip()
    p_name = ' '.join(message.content.split()[1:]).split("--")[0].strip()
    p_id = p_name.lower()
    d_name = ' '.join(message.content.split("--desc")[1:]).split("--")[0].strip()
    a_name = ' '.join(message.content.split("--args")[1:]).split("--")[0].strip()
    o_name = ' '.join(message.content.split("--official")[1:]).split("--")[0].strip()
    h_name = ' '.join(message.content.split("--hidden")[1:]).split("--")[0].strip()
    if o_name.casefold() == "true":
        try:
            if "Racebot Admin" in str(message.author.roles):
                official = True
            else:
                return await message.channel.send("Only Racebot Admins can create official presets!")
        except AttributeError:
            return await message.channel.send("Races cannot be set as `official` in DMs")
    else:
        official = False
    if h_name.casefold() == "true":
        hidden = "true"
    else:
        hidden = "false"
    if "&" in flagstring:
        return await message.channel.send("Presets don't support additional arguments. Save your preset with __FF6WC"
                                          " flags only__, then you can add arguments when you roll the preset with"
                                          " the **!preset <name>** command later.")
    if not p_name:
        await message.channel.send("Please provide a name for your preset with: **!add <name> --flags <flags> "
                                   "[--desc <optional description>]**")
    else:
        if len(p_name) > 64:
            return await message.channel.send("That name is too long! Make sure it's less than 64 characters!")
        if not os.path.exists('db/user_presets.json'):
            with open('db/user_presets.json', 'w') as newfile:
                newfile.write(json.dumps({}))
        with open('db/user_presets.json') as preset_file:
            preset_dict = json.load(preset_file)
        if p_id in preset_dict.keys():
            await message.channel.send(f"Preset name already exists! Try another name or use **!update_preset"
                                       f" {p_name} --flags <flags> [--desc <optional description>]** to overwrite")
        else:
            preset_dict[p_id] = {"name": p_name, "creator_id": message.author.id, "creator": message.author.name,
                                 "flags": flagstring, "description": d_name, "arguments": a_name.replace("&", ""),
                                 "official": official, "hidden": hidden}
            with open('db/user_presets.json', 'w') as updatefile:
                updatefile.write(json.dumps(preset_dict))
            await message.channel.send(f"Preset saved successfully! Use the command **!preset {p_name}** to roll it!")


async def add_preset_v2(ctx, name, flags, desc):
    p_id = name.lower()
    if "&" in flags:
        return await ctx.followup.send("Presets don't support additional arguments. Save your preset with "
                                       "__FF6WC "
                                       " flags only__, then you can add arguments when you roll the preset with"
                                       " the **!preset <name>** command later.", ephemeral=True)
    if not os.path.exists('db/user_presets.json'):
        with open('db/user_presets.json', 'w') as newfile:
            newfile.write(json.dumps({}))
    with open('db/user_presets.json') as preset_file:
        preset_dict = json.load(preset_file)
    if p_id in preset_dict.keys():
        return await ctx.followup.send(f"Preset name already exists! Try another name.", ephemeral=True)
    else:
        preset_dict[p_id] = {"name": name, "creator_id": ctx.user.id, "creator": ctx.user.name,
                             "flags": flags, "description": desc}
        with open('db/user_presets.json', 'w') as updatefile:
            updatefile.write(json.dumps(preset_dict))
        message = f"Preset saved successfully! Use the command **!preset {name}** to roll it!"
    return message


async def update_preset(message):
    flagstring = ' '.join(message.content.split("--flags")[1:]).split("--")[0].strip()
    p_name = ' '.join(message.content.split()[1:]).split("--")[0].strip()
    p_id = p_name.lower()
    d_name = ' '.join(message.content.split("--desc")[1:]).split("--")[0].strip()
    a_name = ' '.join(message.content.split("--args")[1:]).split("--")[0].strip()
    o_name = ' '.join(message.content.split("--official")[1:]).split("--")[0].strip()
    h_name = ' '.join(message.content.split("--hidden")[1:]).split("--")[0].strip()
    plist = ""
    n = 0
    if o_name.casefold() == "true":
        try:
            if "Racebot Admin" in str(message.author.roles):
                official = True
            else:
                return await message.channel.send("Only Racebot Admins can create official presets!")
        except AttributeError:
            return await message.channel.send("Races cannot be set as `official` in DMs")
    elif not o_name:
        pass
    else:
        official = False
    if h_name.casefold() == "true":
        hidden = "true"
    else:
        hidden = "false"
    if "&" in flagstring:
        return await message.channel.send("Presets don't support additional arguments. Save your preset with __FF6WC"
                                          " flags only__, then you can add arguments when you roll the preset with"
                                          " the **!preset <name>** command later.")
    if not p_name:
        await message.channel.send("Please provide a name for your preset with: **!update <name> --flags <flags> "
                                   "[--desc <optional description>]**")
    else:
        if not os.path.exists('db/user_presets.json'):
            with open('db/user_presets.json', 'w') as newfile:
                newfile.write(json.dumps({}))
        with open('db/user_presets.json') as preset_file:
            preset_dict = json.load(preset_file)
        if p_id not in preset_dict.keys():
            await message.channel.send("I couldn't find a preset with that name!")
            for x, y in preset_dict.items():
                if y["creator_id"] == message.author.id:
                    n += 1
                    plist += f'{n}. {x}\nDescription: {y["description"]}\n'
            if plist:
                await message.channel.send(f"Here are all of the presets I have registered for"
                                           f" you:\n```{plist}```")
            else:
                await message.channel.send("I don't have any presets registered for you yet. Use **!add "
                                           "<name> --flags <flags> [--desc <optional description>]** to add a"
                                           " new one.")
        elif preset_dict[p_id]["creator_id"] == message.author.id:
            p_name = preset_dict[p_id]["name"]
            if not flagstring:
                flagstring = preset_dict[p_id]["flags"]
            if not d_name:
                d_name = preset_dict[p_id]["description"]
            if not a_name:
                try:
                    a_name = preset_dict[p_id]["arguments"]
                except KeyError:
                    preset_dict[p_id]["arguments"] = ""
            if not o_name:
                try:
                    official = preset_dict[p_id]["official"]
                except KeyError:
                    official = False
            preset_dict[p_id] = {"name": p_name, "creator_id": message.author.id, "creator": message.author.name,
                                 "flags": flagstring, "description": d_name, "arguments": a_name.replace("&", ""),
                                 "official": official, "hidden": hidden}
            with open('db/user_presets.json', 'w') as updatefile:
                updatefile.write(json.dumps(preset_dict))
            await message.channel.send(f"Preset updated successfully! Use the command **!preset {p_name}** to roll it!")
        else:
            await message.channel.send("Sorry, you can't update a preset that you didn't create!")


async def del_preset(message):
    p_name = ' '.join(message.content.split()[1:]).split("--flags")[0].strip()
    p_id = p_name.lower()
    plist = ""
    n = 0
    if not p_name:
        await message.channel.send("Please provide a name for the preset to delete with: **!delete <name>**")
    else:
        if not os.path.exists('db/user_presets.json'):
            with open('db/user_presets.json', 'w') as newfile:
                newfile.write(json.dumps({}))
        with open('db/user_presets.json') as preset_file:
            preset_dict = json.load(preset_file)
        if p_id not in preset_dict.keys():
            await message.channel.send("I couldn't find a preset with that name!")
            for x, y in preset_dict.items():
                if y["creator_id"] == message.author.id:
                    n += 1
                    plist += f'{n}. {x}\n'
            if plist:
                await message.channel.send(f"Here are all of the presets I have registered for"
                                           f" you:\n```{plist}```")
            else:
                await message.channel.send("I don't have any presets registered for you yet. Use **!add "
                                           "<name> --flags <flags> [--desc <optional description>]** to add a"
                                           " new one.")
        elif preset_dict[p_id]["creator_id"] == message.author.id:
            preset_dict.pop(p_id)
            with open('db/user_presets.json', 'w') as updatefile:
                updatefile.write(json.dumps(preset_dict))
            await message.channel.send(f"Preset deleted successfully!")
        else:
            await message.channel.send("Sorry, you can't delete a preset that you didn't create!")


async def my_presets(message):
    if not os.path.exists('db/user_presets.json'):
        with open('db/user_presets.json', 'w') as newfile:
            newfile.write(json.dumps({}))
    with open('db/user_presets.json') as checkfile:
        preset_dict = json.load(checkfile)
    plist = ""
    n = 0
    if any(message.author.id in d.values() for d in preset_dict.values()):
        for x, y in preset_dict.items():
            if y['creator_id'] == message.author.id:
                n += 1
                try:
                    if y["official"]:
                        plist += f'{n}. **{y["name"]}**\nDescription: *__(Official)__* {y["description"]}\n'
                    else:
                        plist += f'{n}. **{y["name"]}**\nDescription: {y["description"]}\n'
                except KeyError:
                    plist += f'{n}. **{y["name"]}**\nDescription: {y["description"]}\n'
        await message.channel.send(f"Here are all of the presets I have registered for"
                                   f" you:\n")
        embed = discord.Embed()
        embed.title = f'{message.author.display_name}\'s Presets'
        embed.description = plist
        try:
            await message.channel.send(embed=embed)
        except:
            with open("db/my_presets.txt", "w", encoding="utf-8") as preset_file:
                preset_file.write(plist)
            return await message.channel.send(file=discord.File(r'db/my_presets.txt'))

    else:
        await message.channel.send("I don't have any presets registered for you yet. Use **!add "
                                   "<name> --flags <flags> [--desc <optional description>]** to add a"
                                   " new one.")


async def all_presets(message):
    if not os.path.exists('db/user_presets.json'):
        return await message.channel.send("There are no presets saved yet!")
    with open("db/user_presets.json") as f:
        a_presets = json.load(f)
        n_a_presets = "--------------------------------------------\n"
        for x, y in a_presets.items():
            xtitle = ""
            try:
                if y['official']:
                    xtitle = "--(Official)-- "
            except KeyError:
                pass
            try:
                if y['hidden'] == "true":
                    flags = "Hidden"
                else:
                    flags = y['flags']
            except KeyError:
                flags = y['flags']
            try:
                n_a_presets += f"Title: {x}\nCreator: {y['creator']}\nDescription:" \
                               f" {xtitle}{y['description']}\nFlags: {flags}\nAdditional Arguments: {y['arguments']}\n" \
                               f"--------------------------------------------\n"
            except KeyError:
                n_a_presets += f"Title: {x}\nCreator: {y['creator']}\nDescription:" \
                               f" {xtitle}{y['description']}\nFlags: {flags}\n" \
                               f"--------------------------------------------\n"
        with open("db/all_presets.txt", "w", encoding="utf-8") as preset_file:
            preset_file.write(n_a_presets)
        return await message.channel.send(f"Hey {message.author.display_name},"
                                          f" here are all saved presets:")


async def p_flags(message):
    p_name = ' '.join(message.content.split()[1:])
    p_id = p_name.lower()
    plist = ""
    n = 0
    if not p_name:
        await message.channel.send("Please provide the name for the preset!")
    else:
        if not os.path.exists('db/user_presets.json'):
            with open('db/user_presets.json', 'w') as newfile:
                newfile.write(json.dumps({}))
        with open('db/user_presets.json') as preset_file:
            preset_dict = json.load(preset_file)
        if p_id not in preset_dict.keys():
            await message.channel.send("I couldn't find a preset with that name!")
            for x, y in preset_dict.items():
                if y["creator_id"] == message.author.id:
                    n += 1
                    plist += f'{n}. {y["name"]}\n'
            if plist:
                await message.channel.send(f"Here are all of the presets I have registered for"
                                           f" you:\n```{plist}```")
            else:
                await message.channel.send("I don't have any presets registered for you yet. Use **!add "
                                           "<name> --flags <flags> [--desc <optional description>]** to add a"
                                           " new one.")
        else:
            with open('db/user_presets.json') as checkfile:
                preset_dict = json.load(checkfile)
                preset = preset_dict[p_id]
            try:
                if preset['hidden'] == "true":
                    if message.author.id == preset['creator_id']:
                        await message.author.send(f'The flags for **{preset["name"]}** are:\n```{preset["flags"]}```')
                    return await message.channel.send(
                        f'This is a hidden preset. If you are the author of this preset, check your DMs!')
                else:
                    await message.channel.send(f'The flags for **{preset["name"]}** are:\n```{preset["flags"]}```')
                try:
                    if preset["arguments"]:
                        await message.channel.send(f'Additional arguments:\n```{preset["arguments"]}```')
                except KeyError:
                    pass
            except KeyError:
                await message.channel.send(f'The flags for **{preset["name"]}** are:\n```{preset["flags"]}```')
                try:
                    if preset["arguments"]:
                        await message.channel.send(f'Additional arguments:\n```{preset["arguments"]}```')
                except KeyError:
                    pass


def blamethebot(message):
    seedtype = random.choices(['!rando', '!chaos', '!true_chaos', '!shuffle'], weights=[5, 3, 1, 15], k=1)
    loot_arg = random.choices(["", '&loot', '&true_loot', '&all_pally', '&top_tier', '&poverty'],
                              weights=[30, 4, 2, 1, 1, 2], k=1)
    tune_arg = random.choices(["", '&tunes', '&ctunes'], weights=[20, 5, 2], k=1)
    sprite_arg = random.choices(["", '&paint', '&kupo', '&palette'], weights=[20, 5, 2, 10], k=1)
    hundo = random.choices(['', '&hundo'], weights=[30, 1], k=1)
    steve = random.choices(["", '&steve'], weights=[40, 1], k=1)
    obj = random.choices(["", "&obj"], weights=[20, 1], k=1)
    nsl = random.choices(["", "&nospoiler"], weights=[10, 1], k=1)
    final_args = ' '.join([loot_arg[0], tune_arg[0], sprite_arg[0], hundo[0], steve[0], obj[0], nsl[0]])
    desc = f"&desc Blame the Bot! Type: {''.join(seedtype[0].strip('!') + ' ' + final_args.strip().replace('&', '')).replace('  ', ' ')} - Generated by: {message.author.display_name}"
    final_msg = seedtype[0] + final_args + desc
    return final_msg, final_args


def generate_file_name():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=6))


async def send_local_seed(message, silly, preset_dict, preset, views, filename, jdm_spoiler, mtype):
    try:
        directory = "WorldsCollide/seeds/"
        # create a ZipFile object
        zipObj = ZipFile(directory + filename + '.zip', 'w')
        # Add multiple files to the zip
        if jdm_spoiler:
            zipObj.write(directory + filename + "_spoiler.txt", arcname=mtype + '_' + filename + "_music_swaps.txt")
        zipObj.write(directory + filename + '.smc', arcname=mtype + '_' + filename + '.smc')
        zipObj.write(directory + filename + '.txt', arcname=mtype + '_' + filename + '.txt')
        # close the Zip File
        zipObj.close()
        zipfilename = mtype + '_' + filename + ".zip"
        if "preset" in mtype:
            await message.channel.send(
                f"Here\'s your preset seed - {silly}\n**Preset Name**: {preset_dict[preset]['name']}\n**Created By**:"
                f" {preset_dict[preset]['creator']}\n**Description**:"
                f" {preset_dict[preset]['description']}",
                file=discord.File(directory + filename + '.zip', filename=zipfilename),
                view=views.ReRollView(message))
        else:
            await message.channel.send(f"Here's your {mtype} seed - {silly}",
                                       file=discord.File(directory + filename + '.zip', filename=zipfilename),
                                       view=views.ReRollView(message))
        purge_seed_files(filename, directory)
    except AttributeError:
        await message.channel.send("There was a problem generating this seed - please try again!")


def purge_seed_files(f, d):
    filetypes = ['.smc', '.zip', '.txt', '_spoiler.txt']
    base = d + f
    for x in filetypes:
        file = base + x
        if os.path.isfile(file):
            os.remove(file)
