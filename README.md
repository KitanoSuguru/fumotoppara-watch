# ふもとっぱら 空き監視

指定日が「×」→「△/〇」に変わったら Slack（または LINE）に通知します。
予約日選択ページの表（4か月分）を読み取って判定します。

## セットアップ（Slack）

1. Slack で Incoming Webhook を作成（api.slack.com/apps → Create App → Incoming Webhooks を On → 通知先チャンネルを選んで URL を発行）
2. このフォルダ一式を GitHub リポジトリに push
3. Settings → Secrets and variables → Actions
   - Secrets: `FUMO_ID` / `FUMO_PW` / `SLACK_WEBHOOK_URL`
   - Variables:
     - `TARGET_DATES` 例 `2026-11-21,2026-11-28`（カンマ区切り）
     - `SITES`（任意）初期値 `キャンプ宿泊`。複数可 例 `キャンプ宿泊,毛無山荘`
       選べる名前: キャンプ日帰り / キャンプ宿泊 / コテージ柏 / 翠山荘 / 毛無山荘 / 金山キャビン / コロッケ
4. Actions タブ → fumotoppara-watch → Run workflow で初回テスト

## LINE にしたい場合
`SLACK_WEBHOOK_URL` を設定せず、`LINE_CHANNEL_ACCESS_TOKEN` と `LINE_USER_ID` を Secrets に入れる。

## 補足
- 初回実行時点ですでに △/〇 の日は1回通知されます
- 予約サイトの表示範囲（約4か月先まで）外の日付はスキップ
