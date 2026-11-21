# X 定期投稿bot

`posts.csv` に書いた告知を、決めた時刻に X へ自動投稿します。GitHub Actions が30分ごとに動くので、PCを付けておく必要はありません。

## 告知の書き方（posts.csv）

| 列 | 内容 |
|---|---|
| id | 告知ごとに重ならない名前（英数字） |
| datetime | 初回の投稿日時（日本時間、`2026-11-06 21:00` の形） |
| repeat | 空欄なら1回だけ。`daily` で毎日、`weekly` で毎週同じ曜日・時刻 |
| text | 投稿する本文 |
| image | 画像か動画を付けるときはファイル名（例 `images/stream.png`、`videos/shorts_001.mp4`）。空欄なら何も付けない |

アナリティクスの分析では、告知は朝9〜11時に画像付きで出すと最も伸びる見込みです。投稿時刻はこの時間帯に、画像は `images/` フォルダに入れて image 列で指定するのがおすすめです。

## 動画（YouTube Shorts など）を付ける

image 列に `.mp4` か `.mov` のファイルを書くと動画付きで投稿します。動画は `videos/` フォルダに入れてください。

- 1投稿に付けられる動画は1本だけです（画像との併用もできません）
- 動画のアップロードや変換に失敗したときは、文字だけでは投稿せずエラーにします（画像は従来どおり、失敗しても文字だけで投稿します）
- X側の変換を最大10分待ちます。Shorts程度の長さなら通常1分以内に終わります
- GitHub は1ファイル100MBまで、ブラウザからのアップロードは25MBまでです。縦720×1280・30fps程度に縮めると、60秒のShortsでも10〜20MBに収まります
  `ffmpeg -i 元.mp4 -vf scale=720:-2 -r 30 -c:v libx264 -profile:v high -pix_fmt yuv420p -b:v 2500k -c:a aac -b:a 128k -movflags +faststart videos/shorts_001.mp4`
- 動画を貯めすぎるとリポジトリが重くなるので、投稿が終わった動画は時々消してください

Excel で編集する場合は「CSV UTF-8」で保存してください。予定時刻から3時間以上過ぎた分は投稿しません（止まっていた後に一気に流れるのを防ぐため）。

## 費用（2026年10月、X公式の料金ページで確認）

- URLなしの投稿：1件 $0.015
- URLを含む投稿：1件 $0.20
- 月額固定費なし。開発者コンソールで先にクレジットを買い、使った分だけ減ります。上限額を設定できます。
- GitHub Actions は非公開リポジトリでも月2,000分まで無料。30分ごとの実行で月約1,440分なので無料枠に収まります（15分ごとにすると超えるので注意）。

## 準備の手順

1. [X 開発者コンソール](https://console.x.com) でアプリを作り、権限を「Read and write」にする
2. API Key / API Secret / Access Token / Access Token Secret を発行する（権限を変えた後に Access Token を作り直す）
3. クレジットを購入し、月の上限額を設定する
4. GitHub に新しいリポジトリを作り、このフォルダの中身を入れる
5. リポジトリの Settings → Secrets and variables → Actions に4つのキーを登録する
   `X_API_KEY` `X_API_SECRET` `X_ACCESS_TOKEN` `X_ACCESS_TOKEN_SECRET`
6. Actions タブの「scheduled-post」から「Run workflow」で手動実行して動作を確認する

キーを登録する前は「DRY RUN」として、投稿予定の内容を表示するだけで実際には投稿しません。
