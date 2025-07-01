import discord
import re
import json
import os
from discord.ext import commands
from sympy import sympify
from datetime import datetime, timedelta
from util import *
from dotenv import load_dotenv 


load_dotenv()
token = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
ROLL_RESET_HOURS = 2
MAX_ROLLS = 10

users = {}
current_count = 0
last_user_id = 0
high_score = 0
high_score_time ='' 

with open("count.txt", "r") as f:
    p1, p2, p3, high_score_time = f.read().strip().split(",")
    current_count, last_user_id, high_score = map(int, (p1, p2, p3))

with open("users.json", "r") as f:
    data = json.load(f)
    for uid, d in data.items():
        d["last_reset"] = datetime.fromisoformat(d["last_reset"])
        if "inventory" not in d:
            d["inventory"] = [] #fallback
    users = {int(k): v for k, v in data.items()}

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)
bot_channelId = 1341007196917469275
roll_channelId = 1388890411443028118
aquatic_id = 274463901037494274

tokugawa_map = {
    '<:tokugawa:1228747556306161774>' : '1', 
    '<:tokugawa_02:1282511585281314869>' : '2',
    '<:tokugawa_03:1289519032008966227>' : '3', 
    '<:tokugawa_04:1314835422609674243>' : '4',
    '<:tokugawa_05:1329192567627059213>' : '5', 
    '<:tokugawa_06:1332371207907053579>' : '6', 
    '<:tokugawa_07:1332371319253106689>' : '7', 
    '<:tokugawa_08:1332371687517192223>' : '8', 
    '<:tokugawa_09:1332650900740767744>' : '9', 
    '<:tokugawa_10:1333780328447213599>' : '0'
}

def parse_emoji_expression(input_str):
    emoji_pattern = '|'.join(re.escape(k) for k in tokugawa_map.keys())
    emoji_regex = re.compile(emoji_pattern)

    input_str = input_str.replace(' ', '')  # remove spaces

    def replace(match):
        full_emoji = match.group(0)
        return tokugawa_map.get(full_emoji, '')  # will always match

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
                "inventory": v.get("inventory", [])
            } for uid, v in users.items()
        }
        json.dump(serializable, f, indent=2)

        
def can_roll(user_id):
    if not users.get(user_id):
        users[user_id] = {'last_reset': datetime.now(timezone(timedelta(hours=8))), 'rolls': MAX_ROLLS, "inventory": []}
        return True

    now, flag, _ = have_time_passed(users[user_id]['last_reset'], 2)

    if flag:
        users[user_id]['last_reset'] = now
        users[user_id]['rolls'] = MAX_ROLLS

    return users[user_id]['rolls'] > 0


async def handle_roll(ctx):
    user_id = ctx.author.id

    if can_roll(user_id):
        users[user_id]['rolls'] -= 1
        character = get_random_char()
        corp, name, desc, img, movies, tier = character

        await ctx.send(f"{ctx.author.mention}✨ 你抽中了 **{name}**  (剩**{users[user_id]["rolls"]}**個Roll)")
        users[user_id]["inventory"].append(character)
        embed, img_file = char_embed(name, desc, img, corp, movies, tier)

        await ctx.send(embed = embed, file = img_file)
    
    else:
        _, _, delta = have_time_passed(users[user_id]['last_reset'], 2)
        await ctx.send(f"{ctx.author.mention} 你沒有Roll了! Roll將在 **{delta}** 後重置")

    save_count()

@bot.event
async def on_ready():
    print(f'{bot.user} has connected')

@bot.command()
async def jingshi(ctx):
    with open("./media/jingshi.mp4", 'rb') as f:
        mp4_file = discord.File(f, filename='my_video.mp4')
        await ctx.send(file=mp4_file)
    
@bot.command()
async def yjsnpi(ctx):
    with open("./media/114514.mp4", 'rb') as f:
        mp4_file = discord.File(f, filename='my_video.mp4')
        await ctx.send(file=mp4_file)

@bot.command(aliases=["hm"])
async def homo(ctx):
    if ctx.channel.id != roll_channelId:
        embed = discord.Embed(title="請在``#惡臭抽卡``抽",
            description="請勿隨地脫雪，謝謝 ",
            colour=0xff0000)
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
    view = InventoryView(ctx, inventory)
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
    if (ctx.author.id == aquatic_id):
        await ctx.channel.purge(limit=10)
        await ctx.send("deleted", delete_after =5)
        # embed, file = char_embed("健介", "「先輩！好きッス！」", "https://wiki.yjsnpi.nu/w/images/0/07/%E5%81%A5%E4%BB%8B06.jpg", "IKUZE06",["IKUZE06","女王様お許し下さい","IKUZE07 男欲男職場","BLACK HOLE 3 拷問地獄"] ,tiers["Rainbow"]) 
        # await ctx.send(embed = embed, file = file)

@bot.command()
async def help(ctx):
    embed = discord.Embed(title="⚙️迫真指揮官使用手冊⚙️",
                      description="``!jingshi``: 正在跳舞的男高中生.bb\n``!yjsnpi``: 野獸吼叫",
                      url="https://video.laxd.com/a/content/20200422UhsQT474",
                      colour=0x804000)

    embed.set_author(name="迫真指揮官")

    embed.add_field(name="德川接龍💩",
                value="🔴 僅限 ``#惡臭接龍``\n🔴 不接受使用正常數字表示法\n> **:tokugawa:** 表示 1，**:tokugawa_2:** 表示 2，依此類推，**:tokugawa_10:** 表示 0。\n\n``!highscore``:  顯示**目前雪量**及**最高紀錄雪量**🏆\n---------\n",
                inline=False)
    embed.add_field(name="破真角色抽卡",
                    value="🔴 僅限 ``#惡臭抽卡``\n``!homo/hm``: 抽取破真角色 \n``!myhomo/mh/inv``: 查看同性戀戰隊\n\n> 每兩小時十抽，從重置後第一抽開始倒數\n\n* 卡片等級 | 概率\n**男銅** | 65%\n**手銀** | 25%\n**射金** | 8%\n**白金 - Semen** | 1.5%\n**黑金 - 雪** | 0.45%\n**彩虹 - Ultra HOMO** | 0.05%",
                    inline=False)

    embed.set_image(url="https://megapx-assets.dcard.tw/images/f9c8cc97-8502-4772-8668-c8484c6474bd/640.jpeg")

    embed.set_footer(text="肛門灌活鰻魚🐍")

    await ctx.send(embed=embed)

@bot.event
async def on_message(message):
    if message.author == bot.user: # check if message is from bot 
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
            parsed = sympify(msg, evaluate=True)
            if parsed.is_number:
                print(f"{message.author.display_name} counted {parsed} ({msg})") #debug 

                if (not any(tokugawa in message.content for tokugawa in tokugawa_map)): # check if tokugawa
                    embed = discord.Embed(title="請用德川表示法",
                        description="本機器人不接受使用正常數字表示法",
                        colour=0xff0000)
                    await message.reply(embed=embed)
                    return

                if message.author.id == last_user_id: # continous count
                    await message.add_reaction("<:tokugawa_02:1282511585281314869>")
                    await message.reply(f"## {message.author.mention} 食雪了! 不能連續數兩次，下一個數字是 <:tokugawa:1228747556306161774>")
                    current_count = 0
                    last_user_id = 0 
                elif int(parsed) == current_count + 1: # correct count
                    current_count+=1
                    last_user_id = message.author.id
                    if current_count > high_score:
                        high_score = current_count
                        high_score_time = (datetime.utcnow() + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
                    await message.add_reaction("<:tokugawa:1228747556306161774>")
                    print(f" == counter increase to {current_count}")
                else:
                    current_count = 0
                    last_user_id = 0
                    await message.add_reaction("<:tokugawa_02:1282511585281314869>")
                    await message.reply(f"## {message.author.mention} 食雪了! 下一個數字是 <:tokugawa:1228747556306161774>")
                    print(f" == counter reset")

                save_count()

        except Exception as e:
            pass

    await bot.process_commands(message) # also process the message as commands

if __name__ == "__main__":
    bot.run(token)

