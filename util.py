import random
import ast
import discord
from discord.ui import View, Button
import requests
import csv
from PIL import Image, ImageDraw, ImageSequence
from datetime import datetime, timedelta, timezone
from io import BytesIO, StringIO

url = f"https://docs.google.com/spreadsheets/d/1liKVpqp1I6E-aVjLsv1A3MQnH-48SM7FJxbl0j-FbvI/export?format=csv&gid=0"

tiers = {
    "Bronze": {
        "color": "#bc732f",
        "weight": 0.65,
        "logo": "./media/bronze.png",
        "text": "男銅",
        "emoji": "<:tokugawa:1228747556306161774>"
    },
    "Silver": {
        "color": "#c0c0c0",
        "weight": 0.25,
        "logo": "./media/silver.png",
        "text": "手銀",
        "emoji": "<:tokugawa_silver:1389281436527235174>"

    },
    "Gold": {
        "color": "#ffd700",
        "weight": 0.08,
        "logo": "./media/gold.png",
        "text": "射金", 
        "emoji": "<:tokugawa_gold:1389281491229474896>"
    },
    "WhiteGold": {
        "color": "#FFFFFF",
        "weight": 0.015,
        "logo": "./media/whitegold.png",
        "text": "白金、Semen", 
        "emoji": "<:tokugawa_whitegold:1389281538528641116>"

    },
    "BlackGold": {
        "color": "#000000",
        "weight": 0.0045,
        "logo": "./media/blackgold.png",
        "text": "黑金、雪", 
        "emoji":"<:tokugawa_blackgold:1389281576936017950>"
    },
    "Rainbow": {
        "color": "#FFFFFF",
        "weight": 0.0005,
        "logo": "./media/rainbow.png",
        "text": "彩虹、Ultra HOMO", 
        "emoji": "<:tokugawa_rainbow:1389281619994611834>"
    }
}

TIER_ORDER = {
        "\u0020\u767d\u91d1\u3001\u0053\u0065\u006d\u0065\u006e": 0,
        "\u9ed1\u91d1\u3001\u96ea" : 1,
        "\u767d\u91d1\u3001\u0053\u0065\u006d\u0065\u006e" : 2,
        "\u5c04\u91d1" : 3,
        "\u624b\u9280" : 4,
        "\u7537\u9285" : 5,
    }


response = requests.get(url)
content = response.content.decode("utf-8")

reader = csv.reader(StringIO(content))
next(reader)  # Skip header row
rows = list(reader)
num_rows = len(rows)


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

    return now, now-saved_time >= timedelta(hours=delta), f"{hours}小時{minutes}分{seconds}秒"

def get_random_char():
    random_index = random.randint(0, num_rows - 1)
    chars = rows[random_index]

    tk = list(tiers.keys())
    weights = [tiers[key]["weight"] for key in tk]
    choice = random.choices(tk, weights=weights, k=1)[0]

    movies = ast.literal_eval(chars[6])

    return chars[0], chars[3], chars[4], chars[5], movies, tiers[choice]

def char_embed(name, desc, img, corp, movies, tier):
    embed = discord.Embed(title=name,
                          url = "https://laxd.com",
                      description=desc,
                      colour=discord.Colour.from_str(tier["color"]))

    img_file = char_img(img, tier)
    embed.set_author(name=corp)
    
    if tier["text"] != "彩虹、Ultra HOMO":
        embed.set_image(url="attachment://image.png")
    else: #return a animated image
        embed.set_image(url="attachment://animated.gif")

    embed.set_footer(text=tier["text"])
    embed.add_field(name = "出演作品", value = "\n".join(movies))

    return embed, img_file

def char_img(base_img, tier):
    response = requests.get(base_img)
    img = Image.open(BytesIO(response.content)).convert("RGBA")
    img = resize_and_crop_center(img)  # Now it's 640x480

    if tier["text"] =="白金、Semen":
        img = gradient(img, (255, 255, 255,0), (255, 215, 0, 140))
    elif tier["text"] =="黑金、雪":
        img = gradient(img, (255, 255, 255,0), (0, 0, 0, 160))

    border_width = 15
    width, height = img.size

    # Load overlay image
    overlay = Image.open(tier["logo"]).convert("RGBA")
    max_width = width - 2 * border_width
    max_height = height - 2 * border_width #resize
    overlay.thumbnail((max_width, max_height), Image.LANCZOS)  # type: ignore

    #if rainbow card
    if tier["text"] == "彩虹、Ultra HOMO":
        return rainbow_img(img, overlay)

    img.paste(overlay, (0, 0), overlay)


    img_with_border = img.copy()
    draw = ImageDraw.Draw(img_with_border)
    draw.rectangle([0, 0, width, border_width], fill=tier["color"]) #top 
    draw.rectangle([0, height - border_width, width, height], fill=tier["color"]) #bottom
    draw.rectangle([0, 0, border_width, height], fill=tier["color"]) #left
    draw.rectangle([width - border_width, 0, width, height], fill=tier["color"]) #right


    buffer = BytesIO()
    img_with_border.save(buffer, format="PNG")
    buffer.seek(0)
    img_file = discord.File(fp=buffer, filename="image.png")
    return img_file 

def rainbow_img(img, logo ):
    gradient_gif = Image.open("./media/rainbow.gif")

    frames = []

    for frame in ImageSequence.Iterator(gradient_gif):

        base = img.copy()
        base.paste(logo, (0, 0), logo) #paste logo

        rainbow_frame = frame.convert("RGBA").resize(base.size, Image.LANCZOS)  # type: ignore
        white_bg = Image.new("RGB", base.size, (255, 255, 255))
        white_bg.paste(rainbow_frame, (0, 0), rainbow_frame)  # Use rainbow frame as mask
        
        base = base.convert("RGB")
        colored = Image.blend(base, white_bg, 0.3)

        frames.append(colored)

    buffer = BytesIO()
    frames[0].save(
        buffer,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=gradient_gif.info.get("duration", 100),  # ms per frame
        loop=0,
        disposal=2,
        transparency=0,
    )
    buffer.seek(0)
    return discord.File(fp=buffer, filename="animated.gif")

def resize_and_crop_center(img):
    src_w, src_h = img.size

    # Compute aspect ratios
    target_ratio = 640 / 480 
    src_ratio = src_w / src_h

    if src_ratio > target_ratio:
        scale_h = 480 
        scale_w = int(scale_h * src_ratio)
    else:
        # Image is too tall or just right
        scale_w = 640
        scale_h = int(scale_w / src_ratio)

    # Resize while preserving aspect ratio
    img_resized = img.resize((scale_w, scale_h), Image.LANCZOS)  # type: ignore  

    # Now center-crop
    left = (scale_w - 640) // 2
    top = (scale_h - 480) // 2
    right = left +640  
    bottom = top + 480 

    img_cropped = img_resized.crop((left, top, right, bottom))
    return img_cropped

def gradient(img, start, end):
    width, height = img.size
    # Create the gradient overlay
    gradient = Image.new("RGBA", (width, height))
    for y in range(height):
        ratio = y / height
        r = int(start[0] * (1 - ratio) + end[0] * ratio)
        g = int(start[1] * (1 - ratio) + end[1] * ratio)
        b = int(start[2] * (1 - ratio) + end[2] * ratio)
        a = int(start[3] * (1 - ratio) + end[3] * ratio)
        
        for x in range(width):
            gradient.putpixel((x, y), (r, g, b, a))

    # Blend it over the base image
    result = Image.alpha_composite(img, gradient)
    return result

ITEMS_PER_PAGE = 10

class InventoryView(View):
    def __init__(self, ctx, inventory, captain=None):
        super().__init__(timeout=60)  # auto disable after 60s
        self.ctx = ctx
        self.inventory = sorted(
            inventory,
            key=lambda card: TIER_ORDER.get(card[5]["text"], float("inf"))
        )
        self.current_page = 0
        self.message = None
        self.captain = captain
        if self.captain: # create a captain img file to be reused later
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
            colour=0xffffff
        )
        embed.set_author(name="My Homos")
        embed.set_thumbnail(url=self.ctx.author.display_avatar.url)
        if self.captain:
            _, _, _, _, _, tier, _ = self.captain
            if tier["text"] != "彩虹、Ultra HOMO":
                embed.set_image(url="attachment://image.png")
            else:
                embed.set_image(url="attachment://animated.gif")

        embed.set_footer(text=f"第 {self.current_page + 1} 頁 / 共 {self.total_pages} 頁")
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
                await interaction.response.edit_message(embed=embed, view=self, attachments=[self.img_file])
            else:
                await interaction.response.edit_message(embed=embed, view=self, attachments=[])

    async def go_next(self, interaction: discord.Interaction):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_button_states()
            embed  = self.get_page_embed()
            if self.captain:
                self.img_file.fp.seek(0)
                await interaction.response.edit_message(embed=embed, view=self, attachments=[self.img_file])
            else:
                await interaction.response.edit_message(embed=embed, view=self, attachments=[])

    def update_button_states(self):
        self.prev_button.disabled = (self.current_page == 0)
        self.next_button.disabled = (self.current_page >= self.total_pages - 1)
