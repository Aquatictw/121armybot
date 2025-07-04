import random
import ast
import discord
from discord.ui import View, Button
import requests
import csv
from datetime import datetime, timedelta, timezone
from io import StringIO
from image_util import *

url = f"https://docs.google.com/spreadsheets/d/1liKVpqp1I6E-aVjLsv1A3MQnH-48SM7FJxbl0j-FbvI/export?format=csv&gid=0"

tiers = {
    "Bronze": {
        "color": "#bc732f",
        "weight": 0.65,
        "logo": "./media/bronze.png",
        "text": "男銅",
        "emoji": "<:tokugawa:1228747556306161774>",
        "lvlup_req": 3,
    },
    "Silver": {
        "color": "#c0c0c0",
        "weight": 0.25,
        "logo": "./media/silver.png",
        "text": "手銀",
        "emoji": "<:tokugawa_silver:1389281436527235174>",
        "lvlup_req": 5,
    },
    "Gold": {
        "color": "#ffd700",
        "weight": 0.08,
        "logo": "./media/gold.png",
        "text": "射金",
        "emoji": "<:tokugawa_gold:1389281491229474896>",
        "lvlup_req": 8,
    },
    "WhiteGold": {
        "color": "#FFFFFF",
        "weight": 0.015,
        "logo": "./media/whitegold.png",
        "text": "白金、Semen",
        "emoji": "<:tokugawa_whitegold:1389281538528641116>",
        "lvlup_req": 8,
    },
    "BlackGold": {
        "color": "#000000",
        "weight": 0.0045,
        "logo": "./media/blackgold.png",
        "text": "黑金、雪",
        "emoji": "<:tokugawa_blackgold:1389281576936017950>",
        "lvlup_req": 10,
    },
    "Rainbow": {
        "color": "#FFFFFF",
        "weight": 0.0005,
        "logo": "./media/rainbow.png",
        "text": "彩虹、Ultra HOMO",
        "emoji": "<:tokugawa_rainbow:1389281619994611834>",
    },
}

TIER_ORDER = {
    "\u0020\u767d\u91d1\u3001\u0053\u0065\u006d\u0065\u006e": 0,
    "\u9ed1\u91d1\u3001\u96ea": 1,
    "\u767d\u91d1\u3001\u0053\u0065\u006d\u0065\u006e": 2,
    "\u5c04\u91d1": 3,
    "\u624b\u9280": 4,
    "\u7537\u9285": 5,
}


response = requests.get(url)
content = response.content.decode("utf-8")

reader = csv.reader(StringIO(content))
next(reader)  # Skip header row
rows = list(reader)
num_rows = len(rows)


def get_card_by_name(
    name: str,
):
    for row in rows:
        if row[3] == name:
            movies = ast.literal_eval(row[6])
            return row[0], row[3], row[4], row[5], movies
    return None, None, None, None, None


def have_time_passed(saved_time, delta):
    UTC_PLUS_8 = timezone(timedelta(hours=8))
    now = datetime.now(UTC_PLUS_8)

    # Convert string to datetime if needed
    if isinstance(saved_time, str):
        saved_time = datetime.strptime(saved_time, "%Y-%m-%d %H:%M:%S")
        saved_time = saved_time.replace(tzinfo=UTC_PLUS_8)

    reset_time = saved_time + timedelta(hours=2)
    till_reset = reset_time - now
    total_seconds = int(till_reset.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    return (
        now,
        now - saved_time >= timedelta(hours=delta),
        f"{hours}小時{minutes}分{seconds}秒",
    )


def get_random_char():
    random_index = random.randint(0, num_rows - 1)
    chars = rows[random_index]

    tk = list(tiers.keys())
    weights = [tiers[key]["weight"] for key in tk]
    choice = random.choices(tk, weights=weights, k=1)[0]

    movies = ast.literal_eval(chars[6])

    return chars[0], chars[3], chars[4], chars[5], movies, tiers[choice]


def char_embed(name, desc, img, corp, movies, tier):
    embed = discord.Embed(
        title=name,
        url="https://laxd.com",
        description=desc,
        colour=discord.Colour.from_str(tier["color"]),
    )

    img_file = char_img(img, tier)
    embed.set_author(name=corp)

    if tier["text"] != "彩虹、Ultra HOMO":
        embed.set_image(url="attachment://image.png")
    else:  # return a animated image
        embed.set_image(url="attachment://animated.gif")

    embed.set_footer(text=tier["text"])
    embed.add_field(name="出演作品", value="\n".join(movies))

    return embed, img_file


ITEMS_PER_PAGE = 10


class InventoryView(View):
    def __init__(self, ctx, inventory, captain=None):
        super().__init__(timeout=60)  # auto disable after 60s
        self.ctx = ctx
        self.inventory = sorted(
            inventory, key=lambda card: TIER_ORDER.get(card[5]["text"], float("inf"))
        )
        self.current_page = 0
        self.message = None
        self.captain = captain
        if self.captain:  # create a captain img file to be reused later
            _, _, _, img_url, _, tier, _ = self.captain
            self.img_file = char_img(img_url, tier)

        self.prev_button = Button(label="⬅️", style=discord.ButtonStyle.secondary)
        self.next_button = Button(label="➡️", style=discord.ButtonStyle.secondary)

        self.prev_button.callback = self.go_prev
        self.next_button.callback = self.go_next

        self.add_item(self.prev_button)
        self.add_item(self.next_button)

        self.update_button_states()

    def get_page_embed(self):
        start = self.current_page * ITEMS_PER_PAGE
        end = start + ITEMS_PER_PAGE
        page_items = self.inventory[start:end]

        if not page_items:
            description = "阿你怎麼連卡片都沒有"
        else:
            description = "\n".join(
                f"{'📌' if item == self.captain else ''}**{item[1]}** | {item[5]['text']}{item[5]['emoji']}{f' (x{item[6]})' if item[6] >= 2 else ''}"
                for item in page_items
            )

        embed = discord.Embed(
            title=f"{self.ctx.author.display_name} 的 Homo 陣營",
            url="https://www.laxd.com",
            description=description,
            colour=0xFFFFFF,
        )
        embed.set_author(name="My Homos")
        embed.set_thumbnail(url=self.ctx.author.display_avatar.url)
        if self.captain:
            _, _, _, _, _, tier, _ = self.captain
            if tier["text"] != "彩虹、Ultra HOMO":
                embed.set_image(url="attachment://image.png")
            else:
                embed.set_image(url="attachment://animated.gif")

        embed.set_footer(
            text=f"第 {self.current_page + 1} 頁 / 共 {self.total_pages} 頁"
        )
        return embed

    @property
    def total_pages(self):
        return (len(self.inventory) - 1) // ITEMS_PER_PAGE + 1

    async def go_prev(self, interaction: discord.Interaction):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_button_states()
            embed = self.get_page_embed()
            if self.captain:
                self.img_file.fp.seek(0)
                await interaction.response.edit_message(
                    embed=embed, view=self, attachments=[self.img_file]
                )
            else:
                await interaction.response.edit_message(
                    embed=embed, view=self, attachments=[]
                )

    async def go_next(self, interaction: discord.Interaction):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_button_states()
            embed = self.get_page_embed()
            if self.captain:
                self.img_file.fp.seek(0)
                await interaction.response.edit_message(
                    embed=embed, view=self, attachments=[self.img_file]
                )
            else:
                await interaction.response.edit_message(
                    embed=embed, view=self, attachments=[]
                )

    def update_button_states(self):
        self.prev_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page >= self.total_pages - 1
