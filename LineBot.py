from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *
import google.generativeai as genai
import json, os
from datetime import datetime
from flask import jsonify


GEMINI_API_KEY = 'AIzaSyCKvCEH9Eet14AacEBeYXJHJiNSjnyW5SU'
genai.configure(api_key=GEMINI_API_KEY)

# 建議使用 gemini-1.5-pro 或 gemini-1.5-flash，兩個都是支援 text 的
model = genai.GenerativeModel(model_name="gemini-1.5-flash")

app = Flask(__name__)

# 請把這兩個換成你 LINE Developers 後台的資料
LINE_CHANNEL_ACCESS_TOKEN = 'eCZ59rtmJXnbTQtHoWbLxt7O/AmEGOIsCEyD8GMNtedwCXv7YCLIWyegNMXzrTG3/SQ+fGoebTp1tWtKa1OyovBE9ZE7jUYCH+BBnFq7nYIcoCo+fDDtfVwFYg9Gjat6EeFuIce/jJrQJLwmpzFG6QdB04t89/1O/w1cDnyilFU='
LINE_CHANNEL_SECRET = '4512a2bd71b165e2e2a1e34598bcc6cd'

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

HISTORY_FILE = "history.json"

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    print("⚠️ history.json 是空的，回傳空字典")
                    return {}
                return json.loads(content)
        except json.JSONDecodeError as e:
            print(f"❌ JSON 解碼錯誤：{e}")
            return {}
        except Exception as e:
            print(f"❌ 發生未知錯誤：{e}")
            return {}
    else:
        print("📂 history.json 不存在，建立新的")
        return {}

def save_history(data):
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"❌ 儲存 history.json 發生錯誤：{e}")

def add_to_history(user_id, user_msg, bot_reply):
    data = load_history()
    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user": user_msg,
        "bot": bot_reply
    }
    if user_id in data:
        data[user_id].append(entry)
    else:
        data[user_id] = [entry]
    save_history(data)


@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except Exception as e:
        print("Error:", e)
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    print(f"使用者ID：{user_id}")  # 加這行印出來
    
    user_msg = event.message.text

    if user_msg.startswith('故事'):
        topic = user_msg[2:].strip()
        if topic:
            prompt = f"請寫一段主題為「{topic}」的小故事，100到200字以內。"
        else:
            prompt = "請寫一段有趣的小故事，字數控制在100到200字之間。"
        response = model.generate_content(prompt)
        reply = response.text
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply)
        )
    else:
        reply = f"你說的是：{user_msg}"
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply)
        )
    add_to_history(event.source.user_id, user_msg, reply)

# === 處理貼圖 ===
@handler.add(MessageEvent, message=StickerMessage)
def handle_sticker(event):
    package_id = event.message.package_id
    sticker_id = event.message.sticker_id
    reply = f"你傳了一個貼圖（package_id: {package_id}, sticker_id: {sticker_id}）"
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply)
    )
    

# === 處理圖片 ===
@handler.add(MessageEvent, message=ImageMessage)
def handle_image(event):
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="你傳了一張圖片！")
    )

# === 處理影片 ===
@handler.add(MessageEvent, message=VideoMessage)
def handle_video(event):
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="你傳了一部影片！")
    )

# === 處理位置 ===
@handler.add(MessageEvent, message=LocationMessage)
def handle_location(event):
    title = event.message.title or "地點"
    address = event.message.address
    lat = event.message.latitude
    lon = event.message.longitude
    reply = f"你傳來的位置：\n{title}\n地址：{address}\n座標：{lat}, {lon}"
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply)
    )

# ====== RESTful API：GET / DELETE ======
@app.route("/history/<user_id>", methods=['GET'])
def get_history(user_id):
    data = load_history()
    if user_id in data:
        return jsonify(data[user_id])
    return jsonify({"message": "沒有找到該使用者的紀錄"}), 404

@app.route("/history/<user_id>", methods=['DELETE'])
def delete_history(user_id):
    data = load_history()
    if user_id in data:
        del data[user_id]
        save_history(data)
        return jsonify({"message": f"{user_id} 的紀錄已刪除"}), 200
    else:
        return jsonify({"message": "沒有找到該使用者的紀錄"}), 404

if __name__ == "__main__":
    app.run()
