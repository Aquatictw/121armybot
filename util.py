import random
import re
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
    "\u5f69\u8679\u3001Ultra HOMO": 0,
    "\u9ed1\u91d1\u3001\u96ea": 1,
    "\u767d\u91d1\u3001\u0053\u0065\u006d\u0065\u006e": 2,
    "\u5c04\u91d1": 3,
    "\u624b\u9280": 4,
    "\u7537\u9285": 5,
}

EXCHANGE_RATES = {"Gold": 1, "WhiteGold": 6, "BlackGold": 18, "Rainbow": 160}

response = requests.get(url)
content = response.content.decode("utf-8")

reader = csv.reader(StringIO(content))
next(reader)  # Skip header row
rows = list(reader)
num_rows = len(rows)


def parse_emoji_expression(input_str):
    input_str = input_str.replace(" ", "")  # remove spaces

    def replace(match):
        emoji_name = match.group(1)
        if not emoji_name:
            return "1"
        else:
            return emoji_name.lstrip("_0")  # will always match

    emoji_regex = re.compile(r"<:tokugawa(_\d+)?:\d+>")
    result = emoji_regex.sub(replace, input_str)
    return result


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


def lvlupall_logic(inventory):
    promotion_order = list(tiers.keys())
    upgraded_summary = {}

    while True:
        upgrades_made_in_pass = 0
        # Iterate through a copy of inventory as it's modified during the loop
        for card_to_lvlup in list(inventory):
            card_name = card_to_lvlup[1]
            tier_info = card_to_lvlup[5]
            count = card_to_lvlup[6]

            current_tier_key = next(
                (
                    key
                    for key, value in tiers.items()
                    if value["text"] == tier_info["text"]
                ),
                None,
            )

            if not current_tier_key:
                continue

            current_tier_index = promotion_order.index(current_tier_key)
            if current_tier_index == len(promotion_order) - 1:
                continue  # Skip max tier

            lvlup_req = tiers[current_tier_key].get("lvlup_req")
            if not lvlup_req or count < lvlup_req:
                continue

            # Perform level up
            num_new_cards = count // lvlup_req
            remaining_cards = count % lvlup_req
            upgrades_made_in_pass += num_new_cards

            next_tier_key = promotion_order[current_tier_index + 1]
            next_tier_info = tiers[next_tier_key]

            if remaining_cards > 0:
                card_to_lvlup[6] = remaining_cards
            else:
                inventory.remove(card_to_lvlup)

            # Add to higher tier
            higher_tier_card = next(
                (
                    c
                    for c in inventory
                    if c[1] == card_name and c[5]["text"] == next_tier_info["text"]
                ),
                None,
            )

            if higher_tier_card:
                higher_tier_card[6] += num_new_cards
            else:
                corp, _, desc, img, movies = get_card_by_name(card_name)
                new_card = [
                    corp,
                    card_name,
                    desc,
                    img,
                    movies,
                    next_tier_info,
                    num_new_cards,
                ]
                inventory.append(new_card)

            # Track summary
            summary_key = (card_name, current_tier_key, next_tier_key)
            upgraded_summary[summary_key] = (
                upgraded_summary.get(summary_key, 0) + num_new_cards
            )

        if upgrades_made_in_pass == 0:
            break
    return upgraded_summary


ITEMS_PER_PAGE = 10


class InventoryView(View):
    def __init__(self, ctx, inventory, coins, captain=None):
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
            self.captain_url = img_url
            self.captain_tier = tier
        self.coins = coins

        self.prev_button = Button(label="⬅️", style=discord.ButtonStyle.secondary)
        self.next_button = Button(label="➡️", style=discord.ButtonStyle.secondary)

        self.prev_button.callback = self.go_prev
        self.next_button.callback = self.go_next

        self.add_item(self.prev_button)
        self.add_item(self.next_button)

        self.update_button_states()

    @property
    def total_cards(self):
        return sum(item[6] for item in self.inventory)

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
            description += (
                f"\n\n淫幣數量: **{self.coins}** <:yjsnpicoin:1397831330267398225>"
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
            text=f"第 {self.current_page + 1} 頁 / 共 {self.total_pages} 頁 | 總卡片數: {self.total_cards}"
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
            if self.captain:  # player has a captain
                img_file = char_img(self.captain_url, self.captain_tier)
                await interaction.response.edit_message(
                    embed=embed, view=self, attachments=[img_file]
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
            if self.captain:  # player has a captain
                img_file = char_img(self.captain_url, self.captain_tier)
                await interaction.response.edit_message(
                    embed=embed, view=self, attachments=[img_file]
                )
            else:
                await interaction.response.edit_message(
                    embed=embed, view=self, attachments=[]
                )

    def update_button_states(self):
        self.prev_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page >= self.total_pages - 1


class ShopView(discord.ui.View):
    def __init__(self, user_id, users):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.users = users

        self.add_roll_button = Button(
            label="細馬眼棒", emoji="🦯", style=discord.ButtonStyle.primary
        )
        self.add_chance_button = Button(
            label="拓也の射精", emoji="🥛", style=discord.ButtonStyle.primary
        )

        self.add_roll_button.callback = self.add_roll

        self.add_item(self.add_roll_button)
        self.add_item(self.add_chance_button)

        self.update_button_states()

    def get_page_embed(self):
        embed = discord.Embed(title="🏪 肛門訓練器商店", color=0x0099FF)
        embed.set_author(name="商店")
        embed.add_field(
            name="你的淫幣數量",
            value=f"{self.users[self.user_id]["coins"]} <:yjsnpicoin:1397831330267398225>",
            inline=False,
        )
        items = "🦯 **細馬眼棒 — 120 <:yjsnpicoin:1397831330267398225>** \n(每兩小時 +1 roll)\n\n"
        items += "🥛 **拓也の射精 — 3000 <:yjsnpicoin:1397831330267398225>**\n"
        embed.add_field(name="商品", value=items, inline=False)
        embed.set_footer(text="點擊按鈕購買商品！")
        return embed

    async def add_roll(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("阿你是在點三小", ephemeral=True)
            return

        self.users[self.user_id]["coins"] -= 120
        self.users[self.user_id]["max_roll"] += 1

        embed = self.get_page_embed()
        self.update_button_states()

        await interaction.response.edit_message(embed=embed, view=self)
        await interaction.followup.send(
            f"**購買成功！**\n\n你購買了細馬眼棒 (+1 roll)！\n剩餘淫幣: {self.users[self.user_id]["coins"]} <:yjsnpicoin:1397831330267398225>",
            ephemeral=True,
        )

    def update_button_states(self):
        coins = self.users[self.user_id]["coins"]
        self.add_roll_button.disabled = coins < 120
        self.add_chance_button.disabled = coins < 3000


class LvlupView(discord.ui.View):
    def __init__(self, ctx, inventory, save_callback):
        super().__init__(timeout=120)
        self.ctx = ctx
        self.inventory = inventory
        self.save_callback = save_callback
        self.eligible_cards = self.get_eligible_cards()
        self.add_item(self.create_card_select())
        self.add_item(self.create_lvlup_button())

    def get_eligible_cards(self):
        eligible = []
        promotion_order = list(tiers.keys())
        for card in self.inventory:
            tier_text = card[5]["text"]
            current_tier_key = next(
                (key for key, value in tiers.items() if value["text"] == tier_text),
                None,
            )
            if not current_tier_key:
                continue

            current_tier_index = promotion_order.index(current_tier_key)
            if current_tier_index == len(promotion_order) - 1:
                continue  # Skip max tier

            lvlup_req = tiers[current_tier_key].get("lvlup_req")
            if lvlup_req and card[6] >= lvlup_req:
                eligible.append(card)
        return eligible

    def create_card_select(self):
        options = []
        if not self.eligible_cards:
            return discord.ui.Select(
                placeholder="選擇要升級的卡片...",
            )

        for card in self.eligible_cards:
            card_name = card[1]
            tier_name = card[5]["text"]
            count = card[6]
            options.append(
                discord.SelectOption(
                    label=f"{card_name} ({tier_name}) x{count}",
                    value=f"{card_name}|{tier_name}",
                )
            )
        select = discord.ui.Select(
            placeholder="選擇要升級的卡片...",
            min_values=1,
            max_values=len(options),
            options=options,
        )
        select.callback = self.select_callback
        return select

    async def select_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()

    def create_lvlup_button(self):
        button = discord.ui.Button(label="升級", style=discord.ButtonStyle.success)
        button.callback = self.lvlup_callback
        return button

    async def lvlup_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        selected_options = self.children[0].values  # pyright: ignore
        if not selected_options or selected_options[0] == "none":
            await interaction.followup.send("請選擇要升級的卡片。")
            return

        upgraded_summary = {}
        promotion_order = list(tiers.keys())

        for option_value in selected_options:
            card_name, tier_name_text = option_value.split("|")

            card_to_lvlup = next(
                (
                    c
                    for c in self.inventory
                    if c[1] == card_name and c[5]["text"] == tier_name_text
                ),
                None,
            )

            if not card_to_lvlup:
                continue

            current_tier_key = next(
                (
                    key
                    for key, value in tiers.items()
                    if value["text"] == tier_name_text
                ),
                None,
            )
            if not current_tier_key:
                continue

            lvlup_req = tiers[current_tier_key].get("lvlup_req")
            if not lvlup_req or card_to_lvlup[6] < lvlup_req:
                continue

            num_new_cards = card_to_lvlup[6] // lvlup_req
            remaining_cards = card_to_lvlup[6] % lvlup_req

            current_tier_index = promotion_order.index(current_tier_key)
            next_tier_key = promotion_order[current_tier_index + 1]
            next_tier_info = tiers[next_tier_key]

            if remaining_cards > 0:
                card_to_lvlup[6] = remaining_cards
            else:
                self.inventory.remove(card_to_lvlup)

            higher_tier_card = next(
                (
                    c
                    for c in self.inventory
                    if c[1] == card_name and c[5]["text"] == next_tier_info["text"]
                ),
                None,
            )

            if higher_tier_card:
                higher_tier_card[6] += num_new_cards
            else:
                corp, _, desc, img, movies = get_card_by_name(card_name)
                new_card = [
                    corp,
                    card_name,
                    desc,
                    img,
                    movies,
                    next_tier_info,
                    num_new_cards,
                ]
                self.inventory.append(new_card)

            summary_key = (card_name, current_tier_key, next_tier_key)
            upgraded_summary[summary_key] = (
                upgraded_summary.get(summary_key, 0) + num_new_cards
            )

        if not upgraded_summary:
            await interaction.followup.send("沒有可以升級的卡片。")
        else:
            self.save_callback()
            summary_lines = [
                f"將 {tiers[old_tier]['lvlup_req'] * new_cards} 張 **{name} ({tiers[old_tier]['text']}{tiers[old_tier]['emoji']})** "
                + f"合成為 {new_cards} 張 **{name} ({tiers[new_tier]['text']}{tiers[new_tier]['emoji']})**"
                for (name, old_tier, new_tier), new_cards in upgraded_summary.items()
            ]
            await interaction.followup.send(
                "✨ 升級完畢！\n" + "\n".join(summary_lines)
            )


EMOJI_REGEX = re.compile(
    r"^(?:<a?:\w+:\d+>|\s|[\u2000-\u3300\U0001F000-\U0001FAFF"
    r"\U00002702-\U000027B0\U0001F600-\U0001F64F"
    r"\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF"
    r"\U0001F1E6-\U0001F1FF]+)+$"
)


def is_emoji_only(text: str) -> bool:
    return bool(EMOJI_REGEX.fullmatch(text.strip()))
