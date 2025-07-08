import json
import requests
import csv
from io import StringIO
import ast

# This is used as a one time tool to refetch Google sheet data, updating users.json (as users_new.json)

url = "https://docs.google.com/spreadsheets/d/1liKVpqp1I6E-aVjLsv1A3MQnH-48SM7FJxbl0j-FbvI/export?format=csv&gid=0"

tiers = {
    "Bronze": {
        "color": "#bc732f",
        "weight": 0.65,
        "logo": "./media/bronze.png",
        "text": "男銅",
        "emoji": "<:tokugawa:1228747556306161774>",
    },
    "Silver": {
        "color": "#c0c0c0",
        "weight": 0.25,
        "logo": "./media/silver.png",
        "text": "手銀",
        "emoji": "<:tokugawa_silver:1389281436527235174>",
    },
    "Gold": {
        "color": "#ffd700",
        "weight": 0.08,
        "logo": "./media/gold.png",
        "text": "射金",
        "emoji": "<:tokugawa_gold:1389281491229474896>",
    },
    "WhiteGold": {
        "color": "#FFFFFF",
        "weight": 0.015,
        "logo": "./media/whitegold.png",
        "text": "白金、Semen",
        "emoji": "<:tokugawa_whitegold:1389281538528641116>",
    },
    "BlackGold": {
        "color": "#000000",
        "weight": 0.0045,
        "logo": "./media/blackgold.png",
        "text": "黑金、雪",
        "emoji": "<:tokugawa_blackgold:1389281576936017950>",
    },
    "Rainbow": {
        "color": "#FFFFFF",
        "weight": 0.0005,
        "logo": "./media/rainbow.png",
        "text": "彩虹、Ultra HOMO",
        "emoji": "<:tokugawa_rainbow:1389281619994611834>",
    },
}


def get_sheet_data():
    response = requests.get(url)
    content = response.content.decode("utf-8")
    reader = csv.reader(StringIO(content))
    next(reader)  # Skip header row
    return list(reader)


def refresh_card_data():
    try:
        with open("users.json", "r") as f:
            users_data = json.load(f)
    except FileNotFoundError:
        print("users.json not found. Exiting.")
        return

    sheet_rows = get_sheet_data()

    updated_users_data = {}
    for user_id, user_info in users_data.items():
        updated_inventory = []
        for card in user_info.get("inventory", []):
            card_name = card[1]
            card_tier_text = card[5]["text"]

            found_in_sheet = False
            for row in sheet_rows:
                if row[3] == card_name:  # Match by name
                    # Update corp, desc, img, movies
                    updated_corp = row[0]
                    updated_desc = row[4]
                    updated_img = row[5]
                    updated_movies = ast.literal_eval(
                        row[6]
                    )  # Convert string representation of list to actual list

                    # Reconstruct the card with updated info, keeping the original tier and count
                    updated_card = (
                        updated_corp,
                        card_name,
                        updated_desc,
                        updated_img,
                        updated_movies,
                        card[5],
                        card[6],
                    )
                    updated_inventory.append(updated_card)
                    found_in_sheet = True
                    break

            if not found_in_sheet:
                print(
                    f"Warning: Card '{card_name}' (Tier: {card_tier_text}) for user {user_id} not found in Google Sheet. Keeping original data."
                )
                updated_inventory.append(card)  # Keep original if not found

        user_info["inventory"] = updated_inventory
        updated_users_data[user_id] = user_info

    with open("users_new.json", "w") as f:
        json.dump(updated_users_data, f, indent=2)
    print("Card data refreshed successfully in users.json!")


if __name__ == "__main__":
    refresh_card_data()
