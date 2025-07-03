from PIL import Image, ImageDraw, ImageSequence
from io import BytesIO
import discord
import requests
import json
import hashlib
import os

CACHE_DIR = "./cached_images"
CACHE_MAP_FILE = os.path.join(CACHE_DIR, "image_cache_map.json")

try:
    with open(CACHE_MAP_FILE, "r") as f:
        _char_img_cache_map = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    _char_img_cache_map = {}

def char_img(base_img, tier):
    # Create a unique key for the cache
    tier_str = json.dumps(tier, sort_keys=True)
    cache_key = hashlib.md5((base_img + tier_str).encode('utf-8')).hexdigest()
    
    # Determine file extension based on tier type
    file_extension = "gif" if tier["text"] == "彩虹、Ultra HOMO" else "png"
    cached_file_name = f"{cache_key}.{file_extension}"
    cached_file_path = os.path.join(CACHE_DIR, cached_file_name)

    # return cached image if exists
    if cache_key in _char_img_cache_map and os.path.exists(cached_file_path):
        with open(cached_file_path, "rb") as f:
            buffer = BytesIO(f.read())
        buffer.seek(0)
        if tier["text"] == "彩虹、Ultra HOMO":
            return discord.File(fp=buffer, filename="animated.gif")
        else:
            return discord.File(fp=buffer, filename="image.png")

    response = requests.get(base_img)
    img = Image.open(BytesIO(response.content)).convert("RGBA")
    img = resize_to_width(img)  # Now it's 640x480

    if tier["text"] == "白金、Semen":
        img = gradient(img, (255, 255, 255, 0), (255, 215, 0, 140))
    elif tier["text"] == "黑金、雪":
        img = gradient(img, (255, 255, 255, 0), (0, 0, 0, 160))

    border_width = 15
    width, height = img.size

    # Load overlay image
    overlay = Image.open(tier["logo"]).convert("RGBA")
    max_width = width - 2 * border_width
    max_height = height - 2 * border_width
    overlay.thumbnail((max_width, max_height), Image.LANCZOS)

    # If rainbow card
    if tier["text"] == "彩虹、Ultra HOMO":
        img_file = rainbow_img(img, overlay)
        img_file.fp.seek(0)
        with open(cached_file_path, "wb") as f: #cache files
            f.write(img_file.fp.read())
        img_file.fp.seek(0) # Reset for current return
    else:
        img.paste(overlay, (0, 0), overlay)

        img_with_border = img.copy()
        draw = ImageDraw.Draw(img_with_border)
        draw.rectangle([0, 0, width, border_width], fill=tier["color"])
        draw.rectangle([0, height - border_width, width, height], fill=tier["color"])
        draw.rectangle([0, 0, border_width, height], fill=tier["color"])
        draw.rectangle([width - border_width, 0, width, height], fill=tier["color"])

        buffer = BytesIO()
        img_with_border.save(buffer, format="PNG")
        buffer.seek(0)
        with open(cached_file_path, "wb") as f: # cache files
            f.write(buffer.read())
        buffer.seek(0)
        img_file = discord.File(fp=buffer, filename="image.png")

    # Update cache map and save
    _char_img_cache_map[cache_key] = cached_file_name
    with open(CACHE_MAP_FILE, "w") as f:
        json.dump(_char_img_cache_map, f)

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

def resize_to_width(img, target_width=640):
    src_w, src_h = img.size
    target_height = int(src_h * (target_width / src_w))
    img_resized = img.resize((target_width, target_height), Image.LANCZOS)
    return img_resized

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
