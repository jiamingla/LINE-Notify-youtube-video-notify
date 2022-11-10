# LINE Notify 每日新影片通知

## 這是提醒我每天禱告的小專案

### 用到什麼

- 使用 Line bot 串 Line Notify
- 打免費配額的 Youtube API
- 使用免費配額的 Google Cloud Run 以 dockerize 的方式部署
- 使用 Python 的 Flask 後端框架
- 使用免費額度的 Firestore 作為資料庫
- 使用 Google Cloud 的 Google Scheduler

### 學到什麼

- 從有想法到寫出來的過程
- 讀了 LINE bot Message API、LINE Notify API、Youtube API、Firebase 的文件

### 如果要做類似的東西要注意的事情

- LINE 加入群組或多人聊天室 選 接受邀請加入群組或多人聊天室，這樣才能邀進去，只要在群組內輸入「群組訂閱」就可以訂閱了，別像我傻傻的一樣一直在和 LINE Bot 的一對一私訊中打群組訂閱然後納悶為什麼沒有 Group id 哭哭
- 本地未打包、打包後都能讀取到 config.ini，部署上 Cloud Run 就讀取不到，我想是 Cloud Run 有保留 config.ini 作為其他用途吧
- 在 Dockerfile 使用 Pipenv 好像有點麻煩，輸出成 requirements.txt 就容易點了
- Python 3.10-alpine 是檔案容量很小的版本
- LINE Bot 有 Group id 就可以打 API 取得 Group name 和縮圖網址

### 心得

- 實習用到 AWS 幾個雲端服務後，覺得 Google Cloud 的服務相對簡潔，如果專案只有一個人使用還不錯
- 免費仔從 Heroku 跑來 Google Cloud 了，不知道帳單會不會超過 0 元

### 之後預計要做的事情

- 新增 Notify 取消連動功能
- 把之前爬衛理公會網站的內容也加進去
- 寫好文件
- 寫成教學
- 寫成 youtube 頻道新影片通知的開發模板，讓其他人可以 fork 自己用
