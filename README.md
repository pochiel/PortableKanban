# PortableKanban

Python製のカンバン型タスクマネジメントツール。Samba共有フォルダ上のSQLiteファイルを複数PCで共有できるように設計されています。

## 機能概要

- **カンバンボード** (SCR-004): ステータス列にチケットカードを表示。D&Dでステータス変更。
- **チケット管理** (SCR-005): タイトル・担当者・日付・タグ・備考の編集（新規作成・編集は member も可）。
- **フィルター**: 担当者・ステータス・タグ（AND/OR/NOT）・日付範囲で絞り込み。
- **カンバン設定** (SCR-003): 担当者・ステータス・タグ定義のCRUD。
- **ガントチャート出力** (SCR-006): plotlyでHTMLガントチャートを生成。
- **AIプロンプト生成** (SCR-009): 現在のボード状況をAIに渡すプロンプトを自動生成。
- **進捗取り込み** (SCR-008): AIが返したJSONを取り込んでチケットを一括更新。
- **テキストエクスポート** (SCR-007): Jinja2テンプレートでチケット一覧をテキスト出力。

## インストール

```bash
pip install -r requirements.txt
```

## 起動方法

```bash
python main.py
```

## 使い方

### 初回（新規プロジェクト）

1. 「新規作成」ボタンでフォルダを選択
2. チケットプレフィックス（例: `PROJ`）とパスワードを設定して「作成」
3. カンバン設定 (⚙ 設定) でステータス・担当者・タグを追加

### 以降の起動

1. フォルダを選択してログイン
2. パスワードあり → manager（全操作可）
3. パスワードなし → member（設定・削除以外の操作可）

## ロール

| 操作 | manager | member |
|---|:---:|:---:|
| チケット作成・編集 | ○ | ○ |
| D&Dでステータス変更 | ○ | ○ |
| ガントチャート・AI プロンプト・エクスポート | ○ | ○ |
| チケット削除 | ○ | — |
| 設定画面（担当者・ステータス・タグ管理） | ○ | — |

※ manager は同時に1名まで（ロックファイルで制御）。

## AIプロンプト機能の使い方

1. カンバンボードの「AI プロンプト」ボタンを押す
2. 「プロンプト」タブの内容をコピーしてAI（Claude等）に貼り付け
3. AIの出力（JSON）をコピーしてファイルに保存
4. 「進捗取り込み」ボタンでファイルを選択し、差分確認後に「取り込み実行」

### AI向けJSONフォーマット例

```json
[
  {"ticket_id": 1, "status_id": 3},
  {"ticket_id": 2, "assignee_id": 2, "note": "完了見込み3/15"},
  {"ticket_id": 5, "status_id": 2, "assignee_id": 1},
  {"title": "進捗会議で発生した新タスク", "assignee_id": 2}
]
```

`ticket_id` を省略すると新規チケットとして採番・作成される。`ticket_id` を省略する場合は `title` が必須。

## テキストエクスポート（Jinja2テンプレート）

カンバン設定 → テンプレートタブでテンプレートを登録し、エクスポート画面で出力できます。

### 利用可能な変数

テンプレート内では `tickets` というリストが使用できます。各要素 `t` のフィールドは以下の通りです。

| 変数 | 内容 | 例 |
|---|---|---|
| `t.number` | チケット番号（プレフィックス付き） | `PROJ-12` |
| `t.title` | タイトル | `ビーム発射機能の設計` |
| `t.status` | ステータス名 | `仕掛` |
| `t.assignee` | 担当者名 | `田中` |
| `t.start_date` | 開始日（ISO形式） | `2026-03-01` |
| `t.end_date` | 終了日（ISO形式） | `2026-03-18` |
| `t.note` | 備考 | `レビュー待ち` |
| `t.tags['タグ名']` | タグ値 | `t.tags['バージョン']` → `1.0` |

### カスタムフィルター

| フィルター | 説明 | 例 |
|---|---|---|
| `\| jdate` | ISO日付を日本語表記に変換 | `{{ t.end_date \| jdate }}` → `2026年03月18日(水)` |

### テンプレート例

```jinja2
{% for t in tickets %}
[{{ t.number }}] {{ t.title }}
  担当: {{ t.assignee }} / ステータス: {{ t.status }}
  期限: {{ t.end_date | jdate }}
  備考: {{ t.note }}
{% endfor %}
```

## ファイル構成

```
PortableKanban/
  main.py                  # エントリーポイント
  requirements.txt
  db/                      # DB接続管理・マイグレーションSQL
  domain/                  # データクラス
  repository/              # SQLiteアクセス
  service/                 # ビジネスロジック
  presentation/
    views/                 # PyQt6ウィジェット
    presenters/            # MVP Presenter
    components/            # 共通コンポーネント
  kanban_lock/             # managerロックファイル
  tests/                   # pytest テスト
  docs/                    # 設計ドキュメント
```

## テスト実行

```bash
pytest tests/ -v
```

## ビルド（PyInstaller）

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name PortableKanban main.py
```

生成された `dist/PortableKanban.exe` を配布先にコピーしてください。
初回起動時に同じディレクトリに `config.ini` が作成されます。

## 動作要件

- Python 3.10.11 以上（PyInstaller でビルドする場合は不要）
- Windows 10/11 推奨（macOS・Linux も基本的に動作）
- Samba共有フォルダ利用時: WALモード + リトライ機構で書き込み競合を軽減

## ライセンス

未定（内部利用向け。OSSリリース可否は今後判断）
