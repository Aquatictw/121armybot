import discord
from discord import app_commands
from discord.ext import commands, tasks
from typing import List
import re
import json
import os
import random
from sympy import sympify
from datetime import datetime, timedelta
from util import *
from battle import BattleConfirmation, BattleView
from image_util import *
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
ROLL_RESET_HOURS = 2
MAX_ROLLS = 10
vc_client = None
vc_channel = None

users = {}
current_count = 0
last_user_id = 0
high_score = 0
high_score_time = ""

with open("count.txt", "r") as f:
    p1, p2, p3, high_score_time = f.read().strip().split(",")
    current_count, last_user_id, high_score = map(int, (p1, p2, p3))

with open("users.json", "r") as f:
    data = json.load(f)
    for uid, d in data.items():
        d["last_reset"] = datetime.fromisoformat(d["last_reset"])
        if "inventory" not in d:
            d["inventory"] = []  # fallback
        if "captain" not in d:
            d["captain"] = None
        if "deck" not in d:
            d["deck"] = []
    users = {int(k): v for k, v in data.items()}

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)
bot_channelId = 1341007196917469275
roll_channelId = 1388890411443028118
test_channelId = 1389936899917090877
aquatic_id = 274463901037494274
guild_id = 1043107075150065694
vcChannel_id = 1390329071442985110

tokugawa_map = {
    "<:tokugawa:1228747556306161774>": "1",
    "<:tokugawa_02:1282511585281314869>": "2",
    "<:tokugawa_03:1289519032008966227>": "3",
    "<:tokugawa_04:1314835422609674243>": "4",
    "<:tokugawa_05:1329192567627059213>": "5",
    "<:tokugawa_06:1332371207907053579>": "6",
    "<:tokugawa_07:1332371319253106689>": "7",
    "<:tokugawa_08:1332371687517192223>": "8",
    "<:tokugawa_09:1332650900740767744>": "9",
    "<:tokugawa_10:1333780328447213599>": "0",
}


def parse_emoji_expression(input_str):
    emoji_pattern = "|".join(re.escape(k) for k in tokugawa_map.keys())
    emoji_regex = re.compile(emoji_pattern)

    input_str = input_str.replace(" ", "")  # remove spaces

    def replace(match):
        full_emoji = match.group(0)
        return tokugawa_map.get(full_emoji, "")  # will always match

    result = emoji_regex.sub(replace, input_str)
    return result


def save_count():
    with open("count.txt", "w") as f:
        f.write(f"{current_count},{last_user_id},{high_score},{high_score_time}")
    with open("users.json", "w") as f:
        serializable = {
            str(uid): {
                "last_reset": v["last_reset"].isoformat(),
                "rolls": v["rolls"],
                "inventory": v.get("inventory", []),
                "captain": v.get("captain"),
            }
            for uid, v in users.items()
        }
        json.dump(serializable, f, indent=2)


def can_roll(user_id):
    if not users.get(user_id):
        users[user_id] = {
            "last_reset": datetime.now(timezone(timedelta(hours=8))),
            "rolls": MAX_ROLLS,
            "inventory": [],
        }
        return True

    now, flag, _ = have_time_passed(users[user_id]["last_reset"], 2)

    if flag:
        users[user_id]["last_reset"] = now
        users[user_id]["rolls"] = MAX_ROLLS

    return users[user_id]["rolls"] > 0


async def handle_roll(ctx):
    user_id = ctx.author.id

    if can_roll(user_id):
        users[user_id]["rolls"] -= 1
        character = get_random_char()
        corp, name, desc, img, movies, tier = character

        await ctx.send(
            f"{ctx.author.mention}✨ 你抽中了 **{name}**  (剩**{users[user_id]["rolls"]}**個Roll)"
        )

        # Check if the character already exists in the inventory
        existing_character = next(
            (
                item
                for item in users[user_id]["inventory"]
                if item[1] == name and item[5]["text"] == tier["text"]
            ),
            None,
        )

        if existing_character:
            existing_character[6] += 1  # Increment count
        else:
            character_with_count = list(character) + [
                1
            ]  # create new character, initilize count
            users[user_id]["inventory"].append(character_with_count)

        embed, img_file = char_embed(name, desc, img, corp, movies, tier)
        await ctx.send(embed=embed, file=img_file)

    else:
        _, _, delta = have_time_passed(users[user_id]["last_reset"], 2)
        await ctx.send(
            f"{ctx.author.mention} 你沒有Roll了! Roll將在 **{delta}** 後重置"
        )

    save_count()


@bot.event
async def on_ready():
    global vc_channel
    synced = await bot.tree.sync(
        guild=discord.Object(id=guild_id)
    )  # sync slash commands
    vc_channel = bot.get_channel(vcChannel_id)  # initilize vc_channel
    play_audio_loop.start()
    print(f"Synced {len(synced)} commands.")
    print(f"{bot.user} has connected")


@bot.command()
async def jingshi(ctx):
    with open("./media/jingshi.mp4", "rb") as f:
        mp4_file = discord.File(f, filename="my_video.mp4")
        await ctx.send(file=mp4_file)


@bot.command()
async def yjsnpi(ctx):
    with open("./media/114514.mp4", "rb") as f:
        mp4_file = discord.File(f, filename="my_video.mp4")
        await ctx.send(file=mp4_file)


@bot.command(aliases=["hm"])
async def homo(ctx):
    if ctx.channel.id != roll_channelId and ctx.channel.id != test_channelId:
        embed = discord.Embed(
            title="請在``#惡臭抽卡``抽",
            description="請勿隨地脫雪，謝謝 ",
            colour=0xFF0000,
        )
        await ctx.reply(embed=embed)
    else:
        await handle_roll(ctx)


@bot.command(aliases=["myhomo", "mh"])
async def inv(ctx):
    user_id = ctx.author.id
    if user_id not in users:
        await ctx.reply(f"你他媽沒有牌")
        return

    inventory = users[user_id].get("inventory", [])
    captain = users[user_id].get("captain")
    view = InventoryView(ctx, inventory, captain)
    embed = view.get_page_embed()
    if view.captain:
        await ctx.send(embed=embed, view=view, file=view.img_file)
    else:
        await ctx.send(embed=embed, view=view)


@bot.command(aliases=["ct"])
async def checktime(ctx):
    user_id = ctx.author.id
    _, _, delta = have_time_passed(users[user_id]["last_reset"], 2)
    await ctx.send(f"{ctx.author.mention} 你的Roll將在 **{delta}** 後重置")


@bot.hybrid_command(
    name="homocaptain",
    with_app_command=True,
    description="將角色設為同性戀隊長",
    aliases=["hc"],
)
@app_commands.guilds(discord.Object(id=guild_id))
async def homocaptain(ctx: commands.Context, name: str, tier_name: str):
    user_id = ctx.author.id
    if user_id not in users:
        await ctx.reply(f"你他媽沒有牌")
        return

    inventory = users[user_id].get("inventory", [])

    captain_char = next(
        (
            item
            for item in inventory
            if item[1] == name and item[5]["text"] == tier_name
        ),
        None,
    )

    if captain_char:
        users[user_id]["captain"] = captain_char
        save_count()
        await ctx.reply(f"你已將 **{name} ({captain_char[5]["text"]})** 設為你的隊長！")
    else:
        await ctx.reply(f"找不到卡片 {name} ({tier_name})")


@homocaptain.autocomplete("name")
async def card_name_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> List[app_commands.Choice[str]]:
    user_id = interaction.user.id
    if user_id not in users:
        return []

    inventory = users[user_id].get("inventory", [])
    card_names = sorted(list(set([item[1] for item in inventory])))

    filtered_card_names = [
        card_name for card_name in card_names if current.lower() in card_name.lower()
    ]
    return [
        app_commands.Choice(name=card_name, value=card_name)
        for card_name in filtered_card_names[
            :25
        ]  # return max 25 completions (discord limit)
    ]


@homocaptain.autocomplete("tier_name")
async def tier_name_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> List[app_commands.Choice[str]]:
    user_id = interaction.user.id
    if user_id not in users:
        return []

    inventory = users[user_id].get("inventory", [])
    selected_card_name = (
        interaction.namespace.name
    )  # Get the value of the 'name' parameter

    if not selected_card_name:
        return []

    available_tiers = sorted(
        list(
            set(
                [item[5]["text"] for item in inventory if item[1] == selected_card_name]
            )
        )
    )

    return [
        app_commands.Choice(name=tier, value=tier)
        for tier in available_tiers
        if current.lower() in tier.lower()
    ]


@bot.hybrid_command(
    name="search",
    with_app_command=True,
    description="查詢卡片",
    aliases=["s"],
)
@app_commands.guilds(discord.Object(id=guild_id))
async def search(ctx: commands.Context, input_name: str, tier_name: str):
    await ctx.defer()
    corp, name, desc, img, movies = get_card_by_name(input_name)
    if movies == 0:
        await ctx.reply(f"找不到卡片 {input_name} ({tier_name})")
        return
    embed, img_file = char_embed(name, desc, img, corp, movies, tiers[tier_name])
    await ctx.reply(embed=embed, file=img_file)


@search.autocomplete("input_name")
async def search_name_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> List[app_commands.Choice[str]]:

    card_names = [row[3] for row in rows]
    filtered_card_names = [
        card_name for card_name in card_names if current.lower() in card_name.lower()
    ]
    return [
        app_commands.Choice(name=card_name, value=card_name)
        for card_name in filtered_card_names[
            :25
        ]  # return max 25 completions (discord limit)
    ]


@search.autocomplete("tier_name")
async def search_tier_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> List[app_commands.Choice[str]]:

    filtered_card_names = [
        tier for tier in list(tiers.keys()) if current.lower() in tier.lower()
    ]
    return [
        app_commands.Choice(name=card_name, value=card_name)
        for card_name in filtered_card_names[
            :25
        ]  # return max 25 completions (discord limit)
    ]


@bot.command()
async def highscore(ctx):
    await ctx.send(
        f"💩📈 目前雪量 : **{current_count}**\n"
        f"💩🏆 最高紀錄雪量 : **{high_score}** (脫糞時間 {high_score_time})"
    )


@bot.command()
@commands.has_permissions(manage_messages=True)
async def purge(ctx):
    if ctx.author.id == aquatic_id:
        await ctx.channel.purge(limit=10)
        await ctx.send("deleted", delete_after=5)


@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="⚙️迫真指揮官使用手冊⚙️",
        description="``!jingshi``: 正在跳舞的男高中生.bb\n``!yjsnpi``: 野獸吼叫",
        url="https://video.laxd.com/a/content/20200422UhsQT474",
        colour=0x804000,
    )

    embed.set_author(name="迫真指揮官")

    embed.add_field(
        name="德川接龍💩",
        value="🔴 僅限 ``#惡臭接龍``\n🔴 不接受使用正常數字表示法\n> **:tokugawa:** 表示 1，**:tokugawa_2:** 表示 2，依此類推，**:tokugawa_10:** 表示 0。\n\n``!highscore``:  顯示**目前雪量**及**最高紀錄雪量**🏆\n---------\n",
        inline=False,
    )
    embed.add_field(
        name="破真角色抽卡",
        value="🔴 僅限 ``#惡臭抽卡``\n``!homo/hm``: 抽取破真角色 \n``!myhomo/mh/inv``: 查看同性戀戰隊\n``!search [角色名稱] [等級代號]``: 查詢卡牌\n``!homocaptain/hc [角色名稱] [等級代號]``: 將角色設為同性戀隊長\n> 等級代號: Bronze, Silver, Gold, WhiteGold, BlackGold, Rainbow\n\n> 每兩小時十抽，從重置後第一抽開始倒數\n\n* 卡片等級 | 概率\n**男銅** | 65%\n**手銀** | 25%\n**射金** | 8%\n**白金 - Semen** | 1.5%\n**黑金 - 雪** | 0.45%\n**彩虹 - Ultra HOMO** | 0.05%",
        inline=False,
    )

    embed.set_image(
        url="https://megapx-assets.dcard.tw/images/f9c8cc97-8502-4772-8668-c8484c6474bd/640.jpeg"
    )

    embed.set_footer(text="肛門灌活鰻魚🐍")

    await ctx.send(embed=embed)


@bot.event
async def on_message(message):
    if message.author == bot.user:  # check if message is from bot
        return
    if message.stickers:
        return

    if message.channel.id == bot_channelId:
        msg = parse_emoji_expression(message.content)
        global current_count
        global last_user_id
        global high_score
        global high_score_time
        try:
            parsed = sympify(msg, evaluate=True)  # type: ignore
            if parsed.is_number:
                print(
                    f"{message.author.display_name} counted {parsed} ({msg})"
                )  # debug

                if not any(
                    tokugawa in message.content for tokugawa in tokugawa_map
                ):  # check if tokugawa
                    embed = discord.Embed(
                        title="請用德川表示法",
                        description="本機器人不接受使用正常數字表示法",
                        colour=0xFF0000,
                    )
                    await message.reply(embed=embed)
                    return

                if message.author.id == last_user_id:  # continous count
                    await message.add_reaction("<:tokugawa_02:1282511585281314869>")
                    await message.reply(
                        f"## {message.author.mention} 食雪了! 不能連續數兩次，下一個數字是 <:tokugawa:1228747556306161774>"
                    )
                    current_count = 0
                    last_user_id = 0
                elif int(parsed) == current_count + 1:  # correct count
                    current_count += 1
                    last_user_id = message.author.id
                    if current_count > high_score:
                        high_score = current_count
                        high_score_time = (
                            datetime.utcnow() + timedelta(hours=8)
                        ).strftime("%Y-%m-%d %H:%M:%S")
                    await message.add_reaction("<:tokugawa:1228747556306161774>")
                    print(f" == counter increase to {current_count}")
                else:
                    current_count = 0
                    last_user_id = 0
                    await message.add_reaction("<:tokugawa_02:1282511585281314869>")
                    await message.reply(
                        f"## {message.author.mention} 食雪了! 下一個數字是 <:tokugawa:1228747556306161774>"
                    )
                    print(f" == counter reset")

                save_count()

        except Exception:
            pass

    await bot.process_commands(message)  # also process the message as commands


@tasks.loop(minutes=3.0)
async def play_audio_loop():
    global vc_client
    try:
        if vc_client is None or not vc_client.is_connected():
            vc_client = await vc_channel.connect(reconnect=True)  # type: ignore

        if vc_client is not None and not vc_client.is_playing():
            vc_client.play(discord.FFmpegPCMAudio("./media/restaurant.mp3"))

    except Exception as e:
        print(f"[Audio Error] {e}")


@bot.hybrid_command(
    name="lvlup",
    with_app_command=True,
    description="升級卡片",
    aliases=["merge"],
)
@app_commands.guilds(discord.Object(id=guild_id))
async def lvlup(ctx, card_name: str, tier_name: str):
    user_id = ctx.author.id
    if user_id not in users:
        await ctx.send("你沒有任何卡片。")
        return

    inventory = users[user_id].get("inventory", [])

    tier_name_map = {
        "Bronze": "男銅",
        "Silver": "手銀",
        "Gold": "射金",
        "WhiteGold": "白金、Semen",
        "BlackGold": "黑金、雪",
        "Rainbow": "彩虹、Ultra HOMO"
    }
    actual_tier_name = tier_name_map.get(tier_name, tier_name)

    # Find the card to level up
    card_to_lvlup = None
    for card in inventory:
        if card[1] == card_name and card[5]["text"] == actual_tier_name:
            card_to_lvlup = card
            break

    if card_to_lvlup is None:
        await ctx.send(f"你沒有叫做 **{card_name} ({tier_name})** 的卡片。")
        return

    if card_to_lvlup[6] < 5:
        await ctx.send(f"你的 **{card_name} ({tier_name})** 卡片數量少於五張，無法合成。")
        return

    # Tier promotion logic
    promotion_tiers = ["男銅", "手銀", "射金", "白金、Semen", "黑金、雪", "彩虹、Ultra HOMO"]
    
    current_tier_index = -1
    try:
        current_tier_index = promotion_tiers.index(actual_tier_name)
    except ValueError:
        await ctx.send(f"未知的等級: {tier_name}")
        return

    if current_tier_index == len(promotion_tiers) - 1:
        await ctx.send("這張卡已經是最高等級了！")
        return

    next_tier_name = promotion_tiers[current_tier_index + 1]

    # Subtract 5 cards
    card_to_lvlup[6] -= 5
    # if count becomes 0, remove the card from inventory
    if card_to_lvlup[6] == 0:
        inventory.remove(card_to_lvlup)

    # Get the full tier dictionary for the next tier
    next_tier_info = None
    for tier_key, tier_value in tiers.items():
        if tier_value["text"] == next_tier_name:
            next_tier_info = tier_value
            break
    
    if not next_tier_info:
        # This should not happen if promotion_tiers is correct
        await ctx.send("升級時發生內部錯誤。")
        return

    # Check if user already has the higher tier card
    higher_tier_card = None
    for card in inventory:
        if card[1] == card_name and card[5]["text"] == next_tier_name:
            higher_tier_card = card
            break

    if higher_tier_card:
        higher_tier_card[6] += 1
    else:
        # Create new card for the higher tier
        corp, _, desc, img, movies = get_card_by_name(card_name)
        if corp is None:
            await ctx.send(f"找不到卡片 '{card_name}' 的基本資訊。")
            # Revert the change for safety
            card_to_lvlup[6] += 5
            if card_to_lvlup[6] == 5 and card_to_lvlup not in inventory:
                inventory.append(card_to_lvlup)
            return

        new_card = [corp, card_name, desc, img, movies, next_tier_info, 1]
        inventory.append(new_card)

    save_count()
    await ctx.send(f"成功將 5 張 **{card_name} ({tier_name})** 合成為 1 張 **{card_name} ({next_tier_name})**！")
    
@lvlup.autocomplete("card_name")
async def lvlup_name_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> List[app_commands.Choice[str]]:

    card_names = [row[3] for row in rows]
    filtered_card_names = [
        card_name for card_name in card_names if current.lower() in card_name.lower()
    ]
    return [
        app_commands.Choice(name=card_name, value=card_name)
        for card_name in filtered_card_names[
            :25
        ]  # return max 25 completions (discord limit)
    ]
@lvlup.autocomplete("tier_name")
async def lvlup_tier_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> List[app_commands.Choice[str]]:

    filtered_card_names = [
        tier for tier in list(tiers.keys()) if current.lower() in tier.lower()
    ]
    return [
        app_commands.Choice(name=card_name, value=card_name)
        for card_name in filtered_card_names[
            :25
        ]  # return max 25 completions (discord limit)
    ]


@bot.command()
async def battle(ctx, member: discord.Member):
    if member == ctx.author:
        await ctx.send("你不能挑戰自己。")
        return

    p1_id = ctx.author.id
    p2_id = member.id

    # check if there is enough cards to battle
    p1_inventory = users.get(p1_id, {}).get("inventory", [])
    p2_inventory = users.get(p2_id, {}).get("inventory", [])

    if len(p1_inventory) < 5:
        await ctx.send(f"{ctx.author.mention} 你必須至少有5張卡才能戰鬥。")
        return
    if len(p2_inventory) < 5:
        await ctx.send(f"{member.mention} 必須至少有5張卡才能戰鬥。")
        return

    view = BattleConfirmation(ctx.author, member)
    await ctx.send(
        f"{member.mention}, {ctx.author.mention} 想要挑戰你，是否接受？", view=view
    )

    await view.wait()  # wait for battle confimation

    if view.battle_accepted:  # create battle view
        p1_inventory = users[p1_id]["inventory"]
        p2_inventory = users[p2_id]["inventory"]
        battle_view = BattleView(ctx.author, member, p1_inventory, p2_inventory)
        battle_image = create_table_image(
            battle_view.p1_cards,
            battle_view.p2_cards,
            ctx.author.display_name,
            member.display_name,
        )
        embed = battle_view.create_embed()
        message = await ctx.send(embed=embed, view=battle_view, file=battle_image)


@bot.command()
async def draw(ctx):
    user_id = ctx.author.id
    inventory = users[user_id].get("inventory", [])

    users[user_id]["deck"] = []  # clear inventory
    index = random.randrange(0, len(inventory) - 1)
    users[user_id]["deck"].append(inventory[index])  # add the random card

    deck = users[user_id].get("deck", [])
    view = InventoryView(ctx, deck)
    embed = view.get_page_embed()
    embed = view.get_page_embed()
    await ctx.send(embed=embed, view=view)
    
if __name__ == "__main__":
    bot.run(token)  # pyright: ignore
