from PIL import Image, ImageDraw, ImageSequence, ImageFont
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
    cache_key = hashlib.md5((base_img + tier_str).encode("utf-8")).hexdigest()

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
        with open(cached_file_path, "wb") as f:  # cache files
            f.write(img_file.fp.read())
        img_file.fp.seek(0)  # Reset for current return
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
        with open(cached_file_path, "wb") as f:  # cache files
            f.write(buffer.read())
        buffer.seek(0)
        img_file = discord.File(fp=buffer, filename="image.png")

    # Update cache map and save
    _char_img_cache_map[cache_key] = cached_file_name
    with open(CACHE_MAP_FILE, "w") as f:
        json.dump(_char_img_cache_map, f)

    return img_file


def rainbow_img(img, logo):
    gradient_gif = Image.open("./media/rainbow.gif")

    frames = []

    for frame in ImageSequence.Iterator(gradient_gif):

        base = img.copy()
        base.paste(logo, (0, 0), logo)  # paste logo

        rainbow_frame = frame.convert("RGBA").resize(base.size, Image.LANCZOS)  # type: ignore
        white_bg = Image.new("RGB", base.size, (255, 255, 255))
        white_bg.paste(
            rainbow_frame, (0, 0), rainbow_frame
        )  # Use rainbow frame as mask

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


font = ImageFont.truetype("./media/GenWanMin2-M.ttc", 40)
small_font = ImageFont.truetype("./media/GenWanMin2-M.ttc", 28)


def _process_cards(cards):
    processed_cards = []
    total_height = 0
    for card in cards:
        _, name, _, img_url, _, tier = card[:6]
        try:
            discord_file = char_img(img_url, tier)
            card_img = Image.open(discord_file.fp).convert("RGBA")
            card_img.thumbnail((200, 200))
            processed_cards.append((card_img, name))
            total_height += card_img.height
        except Exception as e:
            print(f"Error processing image for card: {name} - {e}")
    return processed_cards, total_height


def create_table_image(p1_cards, p2_cards, player1_name, player2_name):

    PADDING = 20

    p1_processed, p1_card_content_height = _process_cards(p1_cards)
    p2_processed, p2_card_content_height = _process_cards(p2_cards)
    player_name_font = ImageFont.truetype("./media/GenWanMin2-M.ttc", 30)  # player name
    player_name_height = player_name_font.getbbox("測試")[
        3
    ]  # Get height of a sample text

    # Determine the font for "空" and its height
    empty_font = ImageFont.truetype("./media/GenWanMin2-M.ttc", 80)
    empty_text = "空"
    _, empty_text_height = empty_font.getbbox(empty_text)[2:]
    min_height_for_empty_text = (
        empty_text_height + 2 * PADDING
    )  # Add some padding around "空"

    # Calculate heights for each side, considering player name and empty state
    p1_display_height = 0
    if p1_processed:  # if there are cards
        p1_display_height = (
            p1_card_content_height
            + PADDING * (len(p1_processed) + 1)
            + player_name_height
            + PADDING
        )
    else:
        p1_display_height = min_height_for_empty_text + player_name_height + PADDING

    p2_display_height = 0
    if p2_processed:
        p2_display_height = (
            p2_card_content_height
            + PADDING * (len(p2_processed) + 1)
            + player_name_height
            + PADDING
        )
    else:
        p2_display_height = min_height_for_empty_text + player_name_height + PADDING

    image_height = max(
        p1_display_height, p2_display_height
    )  # calculate the max height of the whole image

    background = Image.new("RGBA", (1200, image_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(background)

    # Draw Player 1 name
    p1_name_x = 20
    p1_name_y = PADDING
    draw.text(
        (p1_name_x, p1_name_y),
        player1_name,
        font=player_name_font,
        fill=(255, 215, 0, 255),
    )  # Gold color

    # Player 1 cards and names
    if p1_processed:
        y_offset = PADDING + player_name_height + PADDING  # Start below player name
        for card_img, name in p1_processed:
            img_x = 20
            img_y = y_offset
            current_font = (
                small_font if len(name) > 7 else font
            )  # font size dependent on name length
            text_x = img_x + card_img.width + 10
            text_y = img_y + (card_img.height - current_font.getbbox(name)[3]) // 2
            background.paste(card_img, (img_x, img_y), card_img)
            draw.text(
                (text_x, text_y), name, font=current_font, fill=(255, 255, 255, 255)
            )
            y_offset += card_img.height + PADDING
    else:
        # Draw "空" for Player 1
        text_width, text_height = empty_font.getbbox(empty_text)[2:]
        text_x = (600 - text_width) // 2  # Center in the left half (width 600)
        text_y = (image_height - text_height) // 2
        draw.text(
            (text_x, text_y), empty_text, font=empty_font, fill=(255, 255, 255, 255)
        )

    # Draw Player 2 name
    p2_name_text_width = player_name_font.getbbox(player2_name)[2]
    p2_name_x = 1200 - p2_name_text_width - 20
    p2_name_y = PADDING
    draw.text(
        (p2_name_x, p2_name_y),
        player2_name,
        font=player_name_font,
        fill=(255, 215, 0, 255),
    )  # Gold color

    # Draw Player 2 cards and Names
    if p2_processed:
        y_offset = PADDING + player_name_height + PADDING  # Start below player name
        for card_img, name in p2_processed:
            img_x = 1200 - card_img.width - 20
            img_y = y_offset
            current_font = small_font if len(name) > 7 else font
            text_x = img_x - 10 - current_font.getbbox(name)[2]
            text_y = img_y + (card_img.height - current_font.getbbox(name)[3]) // 2
            background.paste(card_img, (img_x, img_y), card_img)
            draw.text(
                (text_x, text_y), name, font=current_font, fill=(255, 255, 255, 255)
            )
            y_offset += card_img.height + PADDING
    else:
        # Draw "空" for Player 2
        text_width, text_height = empty_font.getbbox(empty_text)[2:]
        text_x = 600 + (600 - text_width) // 2  # Center in the right half (width 600)
        text_y = (image_height - text_height) // 2
        draw.text(
            (text_x, text_y), empty_text, font=empty_font, fill=(255, 255, 255, 255)
        )

    # Draw the dividing line
    line_x = 600
    for y in range(0, image_height, 20):
        draw.line([(line_x, y), (line_x, y + 10)], fill="white", width=2)

    # Add vertical text 對決
    vs_font = ImageFont.truetype("./media/GenWanMin2-M.ttc", 80)
    vs_text = "對決"
    text_width, text_height = vs_font.getbbox(vs_text)[2:]
    text_x = line_x - text_width // 4
    text_y = (image_height - (text_height * len(vs_text))) // 2

    for i, char in enumerate(vs_text):
        draw.text((text_x, text_y + i * text_height), char, font=vs_font, fill="red")

    buffer = BytesIO()
    background.save(buffer, format="PNG")
    buffer.seek(0)
    return discord.File(fp=buffer, filename="battle.png")
