import random
import discord
import requests
import csv
from PIL import Image, ImageDraw
from datetime import datetime, timedelta, timezone
import requests
from io import BytesIO, StringIO

url = f"https://docs.google.com/spreadsheets/d/1liKVpqp1I6E-aVjLsv1A3MQnH-48SM7FJxbl0j-FbvI/export?format=csv&gid=0"


tiers = {
    "Bronze": {
        "color": "#bc732f",
        "weight": 0.65,
        "logo": "./media/bronze.png"
    },
    "Silver": {
        "color": "#c0c0c0",
        "weight": 0.25,
        "logo": "./media/silver.png"
    },
    "Gold": {
        "color": "#ffd700",
        "weight": 0.08,
        "logo": "./media/gold.png"
    },
    "WhiteGold": {
        "color": "#FFFFFF",
        "weight": 0.015
    },
    "BlackGold": {
        "color": "#000000",
        "weight": 0.0045
    },
    "Rainbow": {
        "color": "#ff0000",
        "weight": 0.0005
    }
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

    return chars[0], chars[3], chars[4], chars[5], tiers[choice]

def char_embed(name, desc, img, corp, tier):
    embed = discord.Embed(title=name,
                          url = "https://laxd.com",
                      description=desc,
                      colour=discord.Colour.from_str(tier["color"]))

    img_file = char_img(img, tier)
    embed.set_author(name=corp)
    embed.set_image(url="attachment://image.png")

    return embed, img_file

def char_img(base_img, tier):
    response = requests.get(base_img)
    img = Image.open(BytesIO(response.content)).convert("RGBA")
    img = resize_and_crop_center(img)  # Now it's 640x480

    # Ensure image has an alpha channel
    img_with_border = img.copy()
    draw = ImageDraw.Draw(img_with_border)

    border_width = 15
    width, height = img.size

    draw.rectangle([0, 0, width, border_width], fill=tier["color"]) #top 
    draw.rectangle([0, height - border_width, width, height], fill=tier["color"]) #bottom
    draw.rectangle([0, 0, border_width, height], fill=tier["color"]) #left
    draw.rectangle([width - border_width, 0, width, height], fill=tier["color"]) #right

    # Load overlay image
    overlay = Image.open(tier["logo"]).convert("RGBA")

    # Calculate maximum overlay size (fit inside border)
    max_width = width - 2 * border_width
    max_height = height - 2 * border_width
    # Resize overlay to fit inside border
    overlay.thumbnail((max_width, max_height), Image.LANCZOS)

    img_with_border.paste(overlay, (0, 0), overlay) # paste overlay

    buffer = BytesIO()
    img_with_border.save(buffer, format="PNG")
    buffer.seek(0)
    img_file = discord.File(fp=buffer, filename="image.png")
    return img_file 


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
    img_resized = img.resize((scale_w, scale_h), Image.LANCZOS)

    # Now center-crop
    left = (scale_w - 640) // 2
    top = (scale_h - 480) // 2
    right = left +640  
    bottom = top + 480 

    img_cropped = img_resized.crop((left, top, right, bottom))
    return img_cropped
