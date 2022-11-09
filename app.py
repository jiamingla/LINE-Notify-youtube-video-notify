from __future__ import unicode_literals
import configparser
import json
import os
import sys
import urllib
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from youtube_crawl import YoutubeSpider
parent_dir = os.path.dirname(os.path.abspath(__file__))
cred = credentials.Certificate(os.path.join(
    parent_dir, "path/to/serviceAccountKey.json"))
default_app = firebase_admin.initialize_app(cred)

db = firestore.client()

app = Flask(__name__)

# LINE 聊天機器人的基本資料
config = configparser.ConfigParser()
config.read(os.path.join(parent_dir, 'config.txt'))


try:
    channel_access_token = config.get('line-bot', 'channel_access_token')
    channel_secret = config.get('line-bot', 'channel_secret')
    # Notify 的 Clinet_ID
    notify_client_id = config.get('notify', 'notify_client_id')
    # Notify 的 Clinet_Secret
    notify_client_secret = config.get('notify', 'notify_client_secret')

    youtube_api_key = config.get('youtube', 'youtube_api_key')
    youtube_channel_id = config.get('youtube', 'youtube_channel_id')
except configparser.NoSectionError:
    print('could not read configuration file')
    sys.exit(1)

line_bot_api = LineBotApi(channel_access_token)
handler = WebhookHandler(channel_secret)

# 回傳地點,你的 Notify 的網址
public_url = os.environ["PUBLIC_URL"] or "0.0.0.0"
redirect_uri = f"{public_url}/callback/notify"
youtube_spider = YoutubeSpider(youtube_api_key)


# 把回傳結果包成我們能綁定的網址


def create_auth_link(user_id, client_id=notify_client_id, redirect_uri=redirect_uri) -> str:
    # 把資料包成jason檔格式 => data
    data = {
        'response_type': 'code',
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'scope': 'notify',
        'state': user_id
    }
    query_str = urllib.parse.urlencode(data)

    return f'https://notify-bot.line.me/oauth/authorize?{query_str}'
    # 最後把它包成我們能跟 Line 交換 Access_Token 的網址,也就是綁定的網址
#==============================================================================================#
# 拿取幫綁訂人的 Access_token
#==============================================================================================#


def get_token(code, client_id=notify_client_id, client_secret=notify_client_secret, redirect_uri=redirect_uri):
    url = 'https://notify-bot.line.me/oauth/token'
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': redirect_uri,
        'client_id': client_id,
        'client_secret': client_secret
    }
    data = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=data, headers=headers)
    page = urllib.request.urlopen(req).read()
    res = json.loads(page.decode('utf-8'))
    return res['access_token']  # 拆解後拿取 Access_Token
#==============================================================================================#

# 操作firestore資料庫
#==============================================================================================#


def write_token_to_db(name, target_id, access_token, timestamp) -> None:
    # 這樣應該不會家道重複的人
    doc_ref = db.collection(u'users').document(target_id)
    dict_ = {
        u'name': name,
        u'access_token': access_token,
        u'timestamp': timestamp,
        u'subscribe': True
    }
    doc_ref.set(dict_)


def get_tokens_list() -> list:
    token_list = []
    doc_ref = db.collection(u'users')
    docs = doc_ref.get()
    for doc in docs:
        token_list.append(doc.to_dict()['access_token'])
    return token_list


#==============================================================================================#

# 透過Youtube API爬取今天影片資訊
#==============================================================================================#
def get_youtube_last_video() -> str:
    uploads_id = youtube_spider.get_channel_uploads_id(youtube_channel_id)
    video_ids = youtube_spider.get_playlist(uploads_id, max_results=1)
    text = ""
    # 原本預期會抓三支影片，目前先以最新的一支影片就好
    for video_id in video_ids:
        video_info = youtube_spider.get_video(video_id)
        text = text + video_info['title'] + \
            "\n" + video_info['video_url'] + "\n"
    return text

#==============================================================================================#

# 利用notify發出訊息
#==============================================================================================#


def send_message(access_token, text_message):
    url = 'https://notify-api.line.me/api/notify'
    headers = {"Authorization": "Bearer " + access_token}
    text_message = "\n" + text_message
    data = {'message': text_message}
    data = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=data, headers=headers)
    # 看是否成功 Ex: {"status":200,"message":"ok"}
    page = urllib.request.urlopen(req).read()
#==============================================================================================#


# 利用 handler 處理 LINE 觸發事件
#==============================================================================================#
Group_id = ''  # 用來紀錄群組id
Group_name = ''  # 用來紀錄群組名稱
User_name = ''  # 用來紀錄使用者名稱


@ handler.add(MessageEvent, message=TextMessage)  # 監聽當有新訊息時
def handle_message(event):
    global Group_id, User_id, Group_name, User_name
    if event.message.text == "個人訂閱":
        url = create_auth_link(event)
        # 回傳 url 給傳訊息的那 個人 or 群組
        line_bot_api.reply_message(
            event.reply_token, TextSendMessage(text=url))
        # 這邊是利用 event 內的 user_id 去跟 Line 拿到使用者的當前 Line 使用的名子 Ex: Zi-Yu(林子育)
        User_name = line_bot_api.get_profile(event.source.user_id).display_name
        Group_id = ''
        Group_name = ''
    elif event.message.text == "群組訂閱":
        url = create_auth_link(event)
        line_bot_api.reply_message(
            event.reply_token, TextSendMessage(text=url))
        # 因為 event 內只會回傳個人訊息所以無法找到 Group 的名稱,所以只能改拿 Group 的 id
        Group_id = (event.source.group_id)  # Group_id get!
        url = f'https://api.line.me/v2/bot/group/{Group_id}/summary'
        headers = {'Authorization': f'Bearer {channel_access_token}'}
        req = urllib.request.Request(url, headers=headers)
        page = urllib.request.urlopen(req).read()
        res = json.loads(page.decode('utf-8'))
        Group_name = res['groupName']
        User_name = ''
    elif event.message.text == "取消訂閱":
        url = 'https://notify-api.line.me/api/revoke'
        """
        可選功能
        1.讀取對方的id
        2.將ID拿取資料庫搜尋找到對應的access token
        3.將access token 打POST https://notify-api.line.me/api/revoke
        這裡有API doc https://notify-bot.line.me/doc/en/
        4.去資料庫把這筆資料刪掉
        5.躺躺
        """

        #==============================================================================================#

        # 接收 LINE 的資訊


@ app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']

    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        print(body, signature)
        handler.handle(body, signature)

    except InvalidSignatureError:
        abort(400)

    return 'OK'


# 當 /callback/notify 這個網頁收到 GET 時會做動


@ app.route("/callback/notify", methods=['GET'])
def callback_notify():
    code = request.args.get('code')
    state = json.loads(request.args.get('state'))

    target_id = state['source']['userId']
    timestamp = state['timestamp']
    # Get Access-Token
    access_token = get_token(code, notify_client_id,
                             notify_client_secret, redirect_uri)
    global Group_id, User_name, Group_name
    if(Group_id == ''):
        write_token_to_db(name=User_name,
                          target_id=target_id, access_token=access_token, timestamp=timestamp)
    else:
        write_token_to_db(name=Group_name,
                          target_id=Group_id, access_token=access_token, timestamp=timestamp)
    send_message(
        access_token, text_message="恭喜你訂閱成功，每天六點十分、十二點十分、十八點十分都會發通知")  # 發訊息

    return '恭喜完成 LINE Notify 連動！請關閉此視窗。'  # 網頁顯示

# 當有人傳訊息給我的時候會觸發這個


@ app.route("/", methods=['GET'])
def index():
    token_list = get_tokens_list()
    print(token_list)
    return '這是Line bot，還敢偷看阿'


@ app.route("/morningcall", methods=['GET'])
def morningcall():
    morningcall = request.args.get('morningcall')
    if(morningcall == 'cplus'):
        token_list = get_tokens_list()
        text = get_youtube_last_video()
        for access_token in token_list:
            send_message(access_token=access_token, text_message=text)
        return '已發送每日youtube通知', 200


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
