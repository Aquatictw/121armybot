from openai import OpenAI
from typing import Dict, List
from dotenv import load_dotenv
from util import TIER_ORDER
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROMPT_PATH = os.path.join(BASE_DIR, "initial_prompt.txt")
with open(PROMPT_PATH, "r", encoding="utf-8") as f:
    system_prompt = f.read()

load_dotenv(
    os.path.join(os.path.dirname(BASE_DIR), ".env")
)  # load env variables into env
openai_client = OpenAI(api_key=os.getenv("OPENAI_KEY"))

chat_sessions: Dict[int, List[Dict[str, str]]] = {}


async def init_chat(user_id, user_name, inv):
    if user_id not in chat_sessions:
        inventory = sorted(
            inv, key=lambda card: TIER_ORDER.get(card[5]["text"], float("inf"))
        )
        output_lines = [f"用戶: {user_name}", "前20名角色:"]
        for idx, card in enumerate(inventory[:20], start=1):
            name = card[1]
            tier = card[5]["text"]
            description = card[2].strip()
            appearances = "\n".join(card[4])

            block = (
                f"[角色#{idx}] {name}\n"
                f"[等第] {tier}\n"
                f"[介紹] {description}\n"
                f"[參演作品]\n{appearances}"
            )
            output_lines.append(block)

        prompt = system_prompt + "\n\n".join(output_lines)

        chat_sessions[user_id] = [
            {"role": "developer", "content": prompt},
        ]
        return "淫夢AI模式啟動，你可以開始說話了，輸入 `!stopchat` 可結束對話。"
    else:
        return "你已經在淫夢AI對話中。"


async def chat_reply(user_id, user_message):
    if user_id not in chat_sessions:
        return None
    else:
        chat_sessions[user_id].append({"role": "user", "content": user_message})
        print(user_message)
        try:
            response = openai_client.chat.completions.create(
                model="gpt-4.1", messages=chat_sessions[user_id]
            )
            ai_reply = response.choices[0].message.content
            chat_sessions[user_id].append({"role": "assistant", "content": ai_reply})
            return ai_reply

        except Exception as e:
            print(f"{e} for user {user_id}")


def stop_chat(user_id: int) -> str:
    if user_id in chat_sessions:
        del chat_sessions[user_id]
        return "淫夢AI對話已結束(悲)"
    else:
        return "你目前沒有啟動對話模式。"
