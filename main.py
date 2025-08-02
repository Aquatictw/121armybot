import discord
from discord import app_commands
from discord.ext import commands, tasks
from typing import List
import json
import copy
import os
from sympy import sympify
from datetime import datetime, timedelta
from util import *
from chatbot.chat import *
from battle import *
from image_util import *
from dotenv import load_dotenv
from commit_notifier import CommitNotifier

load_dotenv()
token = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
ROLL_RESET_HOURS = 2
MAX_ROLLS = 10
vc_client = None
vc_channel = None
roll_channel = None  # checktime channel
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
        if "mentioned" not in d:
            d["mentioned"] = False
        if "coins" not in d:
            d["coins"] = 0
        if "max_roll" not in d:
            d["max_roll"] = MAX_ROLLS
    users = {int(k): v for k, v in data.items()}

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)
commit_notifier = CommitNotifier(bot)
COUNT_CHANNEL_ID = 1341007196917469275
ROLL_CHANNEL_ID = 1388890411443028118
DEV_CHANNEL_ID = 1389936899917090877
VC_CHANNEL_ID = 1390329071442985110
AQUAITC_ID = int(os.getenv("AQUATIC_ID", "0"))  # provide fallback value
BANGCHI_ID = int(os.getenv("BANGCHI_ID", "0"))
GUILD_ID = int(os.getenv("GUILD_ID", "0"))


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
                "mentioned": v.get("mentioned", False),
                "coins": v.get("coins", 0),
                "max_roll": v.get("max_roll", MAX_ROLLS),
            }
            for uid, v in users.items()
        }
        json.dump(serializable, f, indent=2)


def can_roll(user_id):
    if not users.get(user_id):  # initialize a user
        users[user_id] = {
            "last_reset": datetime.now(timezone(timedelta(hours=8))),
            "rolls": MAX_ROLLS,
            "inventory": [],
            "captain": None,
            "mentioned": False,
            "coins": 0,
            "max_roll": MAX_ROLLS,
        }
        return True

    now, flag, _ = have_time_passed(users[user_id]["last_reset"], 2)

    if flag:
        users[user_id]["last_reset"] = now
        users[user_id]["rolls"] = users[user_id][
            "max_roll"
        ]  # reset player's roll count

    return users[user_id]["rolls"] > 0


async def handle_roll(ctx):
    user_id = ctx.author.id

    if can_roll(user_id):
        if users[user_id].get("mentioned", False):
            users[user_id]["mentioned"] = False
        users[user_id]["rolls"] -= 1
        character = get_random_char()
        corp, name, desc, img, movies, tier = character
        is_special_tier = tier["text"] in [
            "白金、Semen",
            "黑金、雪",
            "彩虹、Ultra HOMO",
        ]
        kwargs = (
            {} if is_special_tier else {"delete_after": 30.0}
        )  # pass in auto delete karg if tier is not special
        await ctx.send(
            f"{ctx.author.mention}✨ 你抽中了 **{name}**  (剩**{users[user_id]["rolls"]}**個Roll)",
            **kwargs,
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
        await ctx.send(embed=embed, file=img_file, **kwargs)

    else:
        _, _, delta = have_time_passed(users[user_id]["last_reset"], 2)
        await ctx.send(
            f"{ctx.author.mention} 你沒有Roll了! Roll將在 **{delta}** 後重置",
            delete_after=30.0,
        )

    save_count()


@bot.event
async def on_ready():
    global vc_channel, roll_channel
    synced = await bot.tree.sync(
        guild=discord.Object(id=GUILD_ID)
    )  # sync slash commands
    vc_channel = bot.get_channel(VC_CHANNEL_ID)  # initilize vc_channel
    roll_channel = bot.get_channel(ROLL_CHANNEL_ID)
    play_audio_loop.start()
    checktime_loop.start()
    await commit_notifier.check_and_notify_commits()
    print(f"{bot.user} has connected")


@bot.command()
async def jingshi(ctx):
    with open("./media/jingshi.mp4", "rb") as f:
        mp4_file = discord.File(f, filename="my_video.mp4")
        await ctx.send(file=mp4_file)


@bot.command()
async def claimjingshi(ctx):
    user_id = ctx.author.id
    card_name = "耿忠富"
    tier_name = "Gold"

    if user_id not in users:
        users[user_id] = {
            "last_reset": datetime.now(timezone(timedelta(hours=8))),
            "rolls": MAX_ROLLS,
            "inventory": [],
            "captain": None,
            "mentioned": False,
            "coins": 0,
            "max_roll": MAX_ROLLS,
        }

    inventory = users[user_id].get("inventory", [])

    card_info = get_card_by_name(card_name)
    tier_info = tiers[tier_name]

    existing_card = next(
        (
            item
            for item in inventory
            if item[1] == card_name and item[5]["text"] == tier_info["text"]
        ),
        None,
    )

    if existing_card:
        await ctx.reply(f"你已經有 **{card_name} ({tier_info['text']})**了!")

    else:
        corp, name, desc, img, movies = card_info
        new_card = [corp, name, desc, img, movies, tier_info, 1]
        inventory.append(new_card)

        users[user_id]["inventory"] = inventory
        save_count()

        await ctx.reply(f"你領取了 **{card_name} ({tier_info['text']})**!")
        embed, img_file = char_embed(name, desc, img, corp, movies, tiers[tier_name])
        await ctx.reply(embed=embed, file=img_file)

        with open("./media/jingshi.mp4", "rb") as f:
            mp4_file = discord.File(f, filename="my_video.mp4")
            await ctx.send(file=mp4_file)
            await ctx.send("## そう高く 果てなく")


@bot.command()
async def holocaust(ctx):
    await ctx.send("# The Holocaust is NOT REAL")
    await ctx.send("The Jewish are lying to you, gatekeeping wealth from the society.")
    await ctx.send("The Jewish are the most greediest race.")
    await ctx.send(
        "https://www.adl.org/sites/default/files/images/2023-04/holocaust-denial-1020-3.gif"
    )


@bot.command()
async def yjsnpi(ctx):
    with open("./media/114514.mp4", "rb") as f:
        mp4_file = discord.File(f, filename="my_video.mp4")
        await ctx.send(file=mp4_file)


@bot.command(aliases=["hm"])
async def homo(ctx):
    if ctx.channel.id != ROLL_CHANNEL_ID:
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
    coins = users[user_id].get("coins", 0)
    view = InventoryView(ctx, inventory, coins, captain)
    embed = view.get_page_embed()
    if view.captain:
        img_file = char_img(view.captain_url, view.captain_tier)
        await ctx.send(embed=embed, view=view, file=img_file)
    else:
        await ctx.send(embed=embed, view=view)


@tasks.loop(seconds=30.0)
async def checktime_loop():
    for id, data in users.items():
        _, flag, _ = have_time_passed(data["last_reset"], 2)
        if flag and not data.get("mentioned", False):
            target_user = await bot.fetch_user(int(id))
            await roll_channel.send(f"{target_user.mention} 你可以Roll了!")
            data["mentioned"] = True
            save_count()


@bot.command(aliases=["ct"])
async def checktime(ctx):
    user_id = ctx.author.id
    _, flag, delta = have_time_passed(users[user_id]["last_reset"], 2)
    if not flag:
        await ctx.send(f"{ctx.author.mention} 你的Roll將在 **{delta}** 後重置")
    else:
        await ctx.send(f"{ctx.author.mention} 你可以Roll了!")


@bot.hybrid_command(
    name="homocaptain",
    with_app_command=True,
    description="將角色設為同性戀隊長",
    aliases=["hc"],
)
@app_commands.guilds(discord.Object(id=GUILD_ID))
async def homocaptain(ctx: commands.Context, name: str, tier_name: str):
    user_id = ctx.author.id
    if user_id not in users:
        await ctx.reply(f"你他媽沒有牌")
        return

    inventory = users[user_id].get("inventory", [])

    if tier_name not in tiers:
        await ctx.reply(f"找不到等級 {tier_name}")
        return

    tier_info = tiers[tier_name]
    captain_char = next(
        (
            item
            for item in inventory
            if item[1] == name and item[5]["text"] == tier_info["text"]
        ),
        None,
    )

    if captain_char:
        users[user_id]["captain"] = captain_char
        save_count()
        await ctx.reply(f"你已將 **{name} ({tier_info['text']})** 設為你的隊長！")
    else:
        await ctx.reply(f"找不到卡片 {name} ({tier_info['text']})")


@homocaptain.autocomplete("name")
async def hc_name_autocomplete(
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
async def hc_tier_autocomplete(
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

    available_tiers = []
    for item in inventory:
        if item[1] == selected_card_name:
            tier_text = item[5]["text"]
            for tier_key, tier_value in tiers.items():
                if tier_value["text"] == tier_text:
                    available_tiers.append(tier_key)

    return [
        app_commands.Choice(name=tier_key, value=tier_key)
        for tier_key in available_tiers
        if current.lower() in tier_key.lower()
    ]


@bot.hybrid_command(
    name="search",
    with_app_command=True,
    description="查詢卡片",
    aliases=["s"],
)
@app_commands.guilds(discord.Object(id=GUILD_ID))
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


# Add the exchange command
@bot.hybrid_command(
    name="exchange",
    with_app_command=True,
    description="將卡片兌換成淫幣",
    aliases=["ex"],
)
@app_commands.guilds(discord.Object(id=GUILD_ID))
async def exchange(ctx: commands.Context, tier_name: str, name: str, amount: int = 1):
    user_id = ctx.author.id
    if user_id not in users:
        await ctx.reply("你沒有任何卡片。")
        return

    if tier_name not in EXCHANGE_RATES:
        await ctx.reply("只能兌換射金、白金、黑金或彩虹卡片。")
        return

    if amount <= 0:
        await ctx.reply("兌換數量必須大於0。")
        return

    inventory = users[user_id].get("inventory", [])
    tier_info = tiers[tier_name]

    target_card = next(
        (
            item
            for item in inventory
            if item[1] == name and item[5]["text"] == tier_info["text"]
        ),
        None,
    )

    if not target_card:
        await ctx.reply(f"你沒有 **{name} ({tier_info['text']})**。")
        return

    if target_card[6] < amount:
        await ctx.reply(
            f"你只有 {target_card[6]} 張 **{name} ({tier_info['text']})**，無法兌換 {amount} 張。"
        )
        return

    # Perform exchange
    coins_earned = EXCHANGE_RATES[tier_name] * amount
    target_card[6] -= amount

    if target_card[6] == 0:
        inventory.remove(target_card)
        # Check if this was the captain card
        if users[user_id].get("captain") == target_card:
            users[user_id]["captain"] = None

    users[user_id]["coins"] = users[user_id].get("coins", 0) + coins_earned
    save_count()

    await ctx.reply(
        f"成功兌換 {amount} 張 **{name} ({tier_info['text']}{tier_info['emoji']})** "
        f"獲得 **{coins_earned} 淫幣<:yjsnpicoin:1397831330267398225>**！\n"
        f"目前淫幣: **{users[user_id]['coins']} <:yjsnpicoin:1397831330267398225>**"
    )


@exchange.autocomplete("tier_name")
async def exchange_tier_autocomplete(interaction: discord.Interaction, current: str):
    if interaction.user.id not in users:
        return []

    inventory = users[interaction.user.id].get("inventory", [])
    available_tiers = {
        tier_key
        for item in inventory
        for tier_key, tier_value in tiers.items()
        if tier_value["text"] == item[5]["text"] and tier_key in EXCHANGE_RATES
    }

    return [
        app_commands.Choice(name=tier, value=tier)
        for tier in sorted(available_tiers)
        if current.lower() in tier.lower()
    ][:25]


@exchange.autocomplete("name")
async def exchange_name_autocomplete(interaction: discord.Interaction, current: str):
    user_id = interaction.user.id
    selected_tier = interaction.namespace.tier_name

    if user_id not in users or not selected_tier or selected_tier not in EXCHANGE_RATES:
        return []

    inventory = users[user_id].get("inventory", [])
    tier_info = tiers[selected_tier]

    available_names = {
        item[1] for item in inventory if item[5]["text"] == tier_info["text"]
    }

    return [
        app_commands.Choice(name=name, value=name)
        for name in sorted(available_names)
        if current.lower() in name.lower()
    ][:25]


@exchange.autocomplete("amount")
async def exchange_amount_autocomplete(interaction: discord.Interaction, current: str):
    user_id = interaction.user.id
    selected_tier = interaction.namespace.tier_name
    selected_name = interaction.namespace.name

    if (
        user_id not in users
        or not selected_tier
        or not selected_name
        or selected_tier not in EXCHANGE_RATES
    ):
        return []

    inventory = users[user_id].get("inventory", [])
    tier_info = tiers[selected_tier]

    target_card = next(
        (
            item
            for item in inventory
            if item[1] == selected_name and item[5]["text"] == tier_info["text"]
        ),
        None,
    )

    if not target_card:
        return []

    max_amount = min(target_card[6], 25)  # Limit to 25 choices or actual amount
    amounts = [str(i) for i in range(1, max_amount + 1) if current in str(i)]

    return [
        app_commands.Choice(name=f"{amount} 張", value=int(amount))
        for amount in amounts
    ]


@bot.command()
async def shop(ctx):
    user_id = ctx.author.id
    coins = users[user_id].get("coins", 0)
    if coins == 0:
        await ctx.reply("你沒有淫幣，他媽窮鬼")
    else:
        view = ShopView(user_id, users)
        embed = view.get_page_embed()
        await ctx.send(embed=embed, view=view)


@bot.command()
async def highscore(ctx):
    await ctx.send(
        f"💩📈 目前雪量 : **{current_count}**\n"
        f"💩🏆 最高紀錄雪量 : **{high_score}** (脫糞時間 {high_score_time})"
    )


@bot.command()
@commands.has_permissions(manage_messages=True)
async def purge(ctx):
    if ctx.author.id == AQUAITC_ID:
        await ctx.channel.purge(limit=10)
        await ctx.send("deleted", delete_after=5)


@bot.command(name="help")
async def help_command(ctx):
    embed = discord.Embed(
        title="⚙️ 指令列表 ⚙️",
        url="https://video.laxd.com/a/content/20200422UhsQT474",
        color=0xFFFFFF,
    )

    embed.set_author(name="迫真指揮官 Discord Bot 使用手冊")

    # 基礎指令
    basic_commands = (
        "`!help` - 顯示完整使用手冊\n" "`!highscore` - 查看當前雪量和最高紀錄"
    )
    embed.add_field(name="🔧 基礎指令", value=basic_commands, inline=False)

    # 抽卡相關
    gacha_commands = (
        "`!homo` / `!hm` - 抽取角色卡片\n"
        "`!myhomo` / `!mh` / `!inv` - 查看個人背包\n"
        "`/homocaptain` / `/hc [角色名] [等級]` - 設定隊長\n"
        "`/search [角色名] [等級]` - 搜尋特定卡片\n"
        "`/exchange [等級] [角色名] [數量]` - 兌換卡片為淫幣\n"
        "`/lvlup` - 升級卡片\n"
        "`/lvlupall` - 自動升級所有可升級卡片\n"
        "`!checktime` / `!ct` - 查看抽卡重置時間"
    )
    embed.add_field(name="🎴 抽卡相關", value=gacha_commands, inline=False)

    # 稀有度機率
    rarity_rates = (
        "男銅 (65%)\n"
        "手銀 (25%)\n"
        "射金 (8%)\n"
        "白金 - Semen (1.5%)\n"
        "黑金 - 雪 (0.45%)\n"
        "彩虹 - Ultra HOMO (0.05%)"
    )
    embed.add_field(name="🎲 等級機率", value=rarity_rates, inline=True)

    # 合成規則
    synthesis_rules = (
        "3張男銅 → 1張手銀\n"
        "5張手銀 → 1張射金\n"
        "8張射金 → 1張白金\n"
        "8張白金 → 1張黑金\n"
        "10張黑金 → 1張彩虹"
    )
    embed.add_field(name="⚗️ 合成規則", value=synthesis_rules, inline=True)

    # 兌換比率
    exchange_rates = (
        "射金: 1 <:yjsnpicoin:1397831330267398225>\n"
        "白金: 6 <:yjsnpicoin:1397831330267398225>\n"
        "黑金: 18 <:yjsnpicoin:1397831330267398225>\n"
        "彩虹: 160 <:yjsnpicoin:1397831330267398225>"
    )
    embed.add_field(name="💰 兌換比率", value=exchange_rates, inline=True)

    # 社交功能
    social_commands = (
        "`!leaderboard` / `!lb` - 查看排行榜\n"
        "`!battle [@用戶]` - 挑戰其他玩家\n"
        "`!chat` - 開啟AI聊天模式\n"
        "`!stopchat` - 關閉AI聊天模式\n"
        "`!shop` - 開啟商店"
    )
    embed.add_field(name="🤝 社交功能", value=social_commands, inline=False)

    # 娛樂指令
    entertainment_commands = (
        "`!jingshi` - 正在跳舞的男高中生\n"
        "`!yjsnpi` - 野獸吼叫\n"
        "`!claimjingshi` - 領取特殊角色"
    )
    embed.add_field(name="🎮 娛樂指令", value=entertainment_commands, inline=False)

    links = (
        "[角色列表](https://docs.google.com/spreadsheets/d/1liKVpqp1I6E-aVjLsv1A3MQnH-48SM7FJxbl0j-FbvI/edit?gid=0#gid=0)\n"
        "[GitHub開源](https://github.com/Aquatictw/121armybot)"
    )
    embed.add_field(name="🔗 相關連結", value=links, inline=False)

    embed.set_image(url="https://i.postimg.cc/0N26gbb6/Screenshot-1.png")

    embed.set_footer(text="肛門灌活鰻魚🐍")

    await ctx.send(embed=embed)


@bot.event
async def on_message(message):
    if message.author == bot.user:  # check if message is from bot
        return
    if message.stickers:
        return

    if message.channel.id == COUNT_CHANNEL_ID:
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

                if not "tokugawa" in message.content:  # check if tokugawa
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

    if (
        message.channel.id == ROLL_CHANNEL_ID
        and bot.user in message.mentions
        and not message.content.startswith("!")
        and not is_emoji_only(message.content)
    ):  # ai chatbot

        content = message.content.replace(f"<@{bot.user.id}>", "").strip()
        reply = await chat_reply(message.author.id, content)
        if reply:
            await message.channel.send(reply)

    await bot.process_commands(message)  # also process the message as commands


@tasks.loop(seconds=30.0)
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
@app_commands.guilds(discord.Object(id=GUILD_ID))
async def lvlup(ctx):
    user_id = ctx.author.id
    if user_id not in users:
        await ctx.send("你沒有任何卡片。")
        return

    inventory = users[user_id].get("inventory", [])
    view = LvlupView(ctx, inventory, save_count)
    if not view.eligible_cards:
        await ctx.send("沒有可以升級的卡片。")
        return
    await ctx.send("請選擇要升級的卡片:", view=view)


@bot.hybrid_command(
    name="lvlupall",
    with_app_command=True,
    description="自動升級所有滿足條件的卡片",
    aliases=["mergeall"],
)
@app_commands.guilds(discord.Object(id=GUILD_ID))
async def lvlupall(ctx):
    user_id = ctx.author.id
    if user_id not in users:
        await ctx.send("你沒有任何卡片。")
        return

    inventory = users[user_id].get("inventory", [])
    upgraded_summary = lvlupall_logic(inventory)

    if not upgraded_summary:
        await ctx.send("沒有可以升級的卡片。")
    else:
        save_count()
        summary_lines = [
            f"將 {tiers[old_tier]["lvlup_req"] * new_cards} 張 **{name} ({tiers[old_tier]["text"]}{tiers[old_tier]["emoji"]})** "
            + f"合成為 {new_cards} 張 **{name} ({tiers[new_tier]["text"]}{tiers[new_tier]["emoji"]})**"
            for (name, old_tier, new_tier), new_cards in upgraded_summary.items()
        ]

        # Split into batches to avoid Discord's 2000 character limit
        batches = []
        current_batch = []
        current_length = len("✨ 升級完畢！\n")

        for line in summary_lines:
            line_length = len(line) + 1
            if current_length + line_length > 2000 and current_batch:
                batches.append(current_batch)
                current_batch = [line]
                current_length = len(line) + 1
            else:
                current_batch.append(line)
                current_length += line_length

        if current_batch:
            batches.append(current_batch)

        # Send batches
        for i, batch in enumerate(batches):
            if i == 0:
                await ctx.send("✨ 升級完畢！\n" + "\n".join(batch))
            else:
                await ctx.send("\n".join(batch))


@bot.command()
async def battle(ctx, member: discord.Member):
    if member == ctx.author:
        await ctx.reply("你不能挑戰自己。")
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
        p1_inventory = copy.deepcopy(
            users[p1_id]["inventory"]
        )  # deep copy to prevent altering inventory
        p2_inventory = copy.deepcopy(users[p2_id]["inventory"])
        battle_view = BattleView(ctx.author, member, p1_inventory, p2_inventory)

        battle_image = create_table_image(
            battle_view.p1_table,
            battle_view.p2_table,
            ctx.author.display_name,
            member.display_name,
        )
        embed = battle_view.create_embed()
        await ctx.send(embed=embed, view=battle_view, file=battle_image)


@bot.command(aliases=["lb"])
async def leaderboard(ctx):
    leaderboard_data = []
    for user_id, data in users.items():
        inventory = data.get("inventory", [])
        rainbow_count = 0
        blackgold_count = 0
        whitegold_count = 0

        for card in inventory:
            tier_text = card[5]["text"]
            card_count = card[6]
            if "彩虹" in tier_text:
                rainbow_count += card_count
            elif "黑金" in tier_text:
                blackgold_count += card_count
            elif "白金" in tier_text:
                whitegold_count += card_count

        total_score = rainbow_count * 90 + blackgold_count * 10 + whitegold_count * 3
        user = await bot.fetch_user(user_id)
        leaderboard_data.append(
            {
                "user_id": user_id,
                "user_name": user.display_name,
                "Rainbow": rainbow_count,
                "BlackGold": blackgold_count,
                "WhiteGold": whitegold_count,
                "score": total_score,
            }
        )

    leaderboard_data.sort(key=lambda x: x["score"], reverse=True)

    embed = discord.Embed(
        title="🌈 同性戀排行榜 🏆 Top 5", color=0xFFFFFF, url="https://www.laxd.com"
    )
    embed.set_author(name="121軍團中央指揮部", url="https://www.laxd.com")

    if leaderboard_data:
        top_user = await bot.fetch_user(leaderboard_data[0]["user_id"])
        embed.set_thumbnail(url=top_user.display_avatar.url)

    description = ""
    for i, entry in enumerate(leaderboard_data[:5]):
        description += (
            f"{i+1}. **{entry["user_name"]}**  "
            f"{tiers["Rainbow"]["emoji"]}彩虹: {entry['Rainbow']} | "
            f"{tiers["BlackGold"]["emoji"]}黑金: {entry['BlackGold']} | "
            f"{tiers["WhiteGold"]["emoji"]}白金: {entry['WhiteGold']}\n\n"
        )

    if not description:
        description = "No one is on the leaderboard yet."

    embed.description = description
    embed.set_footer(text="分數加權: 彩虹*90 + 黑金*10 + 白金*3")

    file = create_leaderboard_image(leaderboard_data[:5])
    embed.set_image(url="attachment://leaderboard.png")

    await ctx.send(embed=embed, file=file)


@bot.command()
async def chat(ctx):
    if ctx.channel.id != ROLL_CHANNEL_ID:
        embed = discord.Embed(
            title="請在``#惡臭抽卡``聊天",
            description="請勿隨地脫雪，謝謝 ",
            colour=0xFF0000,
        )
        await ctx.reply(embed=embed)
    else:
        inventory = users[ctx.author.id].get("inventory", [])
        msg = await init_chat(ctx.author.id, ctx.author.display_name, inventory)
        await ctx.send(msg)


@bot.command()
async def stopchat(ctx):
    if ctx.channel.id != ROLL_CHANNEL_ID:
        embed = discord.Embed(
            title="請在``#惡臭抽卡``聊天",
            description="請勿隨地脫雪，謝謝 ",
            colour=0xFF0000,
        )
        await ctx.reply(embed=embed)
    else:
        reply = stop_chat(ctx.author.id)
        await ctx.send(reply)


if __name__ == "__main__":
    bot.run(token)  # pyright: ignore
