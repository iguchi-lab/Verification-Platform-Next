# Claude Code - 開発者向けセットアップ

このディレクトリには、プロジェクト用の Claude Code 設定が格納されています。

## ファイル一覧

| ファイル | 説明 |
|----------|------|
| `settings.json` | プロジェクト共通設定（コミット対象） |
| `settings.local.json` | 個人設定 — gitignore 済み、コミット不可 |
| `settings.local.sample.json` | `settings.local.json` のサンプル |

## オプション: GitHub MCP 連携

GitHub MCP を設定すると、Claude Code から Issue / PR の検索、リポジトリの内容参照、ブランチ比較などが行えるようになります。

### セットアップ手順

**1. GitHub Personal Access Token を発行**

GitHub > Settings > Developer settings > Personal access tokens > Generate new token

必要なスコープ: `repo`, `read:org`

**2. `.env` ファイルを作成してトークンを設定**

```bash
cp .env.sample .env
```

作成した `.env` 内の `your_token_here` を実際のトークンに書き換えてください。

MCP サーバーの設定は `.mcp.json`（リポジトリルート）に記載されており、変更不要です。

**3. Claude Code を再起動**して設定を反映させます。

### 注意事項

- `.env` は gitignore 済みのため、トークンがコミットされることはありません
- `.mcp.json` はリポジトリに含まれるプロジェクト共通設定です
- この設定は任意です。設定しない開発者には影響しません
