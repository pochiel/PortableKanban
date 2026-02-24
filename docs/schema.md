# スキーマ設計書: Pythonカンバン型タスクマネジメントツール

## 概要

- DBエンジン: SQLite
- ファイル構成:
  - `rules.db`: ルールデータ（チームのセットアップ情報）
  - `work.db`: 実務データ（日常業務で作成・更新されるデータ）
- 共通設定: 全DBでWALモードを有効化
- 共通カラム: 全テーブルに `created_at`, `updated_at` を設ける

---

## rules.db

### members（担当者テーブル）

チームメンバーを管理する。

| カラム名 | 型 | 制約 | 説明 |
|---|---|---|---|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 担当者ID |
| name | TEXT | NOT NULL | 担当者名 |
| email | TEXT | | メールアドレス |
| is_active | INTEGER | NOT NULL DEFAULT 1 | 有効フラグ（1:有効 / 0:無効） |
| created_at | TEXT | NOT NULL | 作成日時（ISO8601） |
| updated_at | TEXT | NOT NULL | 更新日時（ISO8601） |

**備考:**
- 担当者を削除する代わりに `is_active=0` で無効化する（チケットの参照整合性を保つため）

---

### statuses（ステータス定義テーブル）

カンバンボードの列に対応するステータスを定義する。CLOSEDに相当するステータスも含め、すべてこのテーブルで管理する。

| カラム名 | 型 | 制約 | 説明 |
|---|---|---|---|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | ステータスID |
| name | TEXT | NOT NULL | ステータス名（例: 未着手、CLOSED） |
| display_order | INTEGER | NOT NULL | 表示順（カンバン列の左→右順） |
| created_at | TEXT | NOT NULL | 作成日時（ISO8601） |
| updated_at | TEXT | NOT NULL | 更新日時（ISO8601） |

**備考:**
- `display_order` の昇順でカンバンボードの列を左から右に生成する
- CLOSEDのような「完了・非表示にしたいステータス」はManagerがsettingsテーブルの `default_hidden_status_ids` に登録することでデフォルト非表示にできる
- 将来的に同様の仕組みが必要な項目（優先度など）が生じた場合、このテーブルを汎用化する拡張を検討する（初期バージョンはステータス専用）

---

### tag_definitions（タグ定義テーブル）

チケットに付与できるカスタムフィールドを定義する。フラットなリスト構造で管理し、階層・グループ構造は持たない。

| カラム名 | 型 | 制約 | 説明 |
|---|---|---|---|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | タグ定義ID |
| name | TEXT | NOT NULL | タグ名（例: 機種名、会社名） |
| field_type | TEXT | NOT NULL | フィールド型（後述） |
| created_at | TEXT | NOT NULL | 作成日時（ISO8601） |
| updated_at | TEXT | NOT NULL | 更新日時（ISO8601） |

**field_typeの値:**

| 値 | 説明 |
|---|---|
| text | テキスト |
| date | 日付（ISO8601形式で保存） |

**備考:**
- タグの組み合わせ管理はフィルター機能のAND/OR/NOT検索で実現する
- 初期バージョンは `text` と `date` のみサポート。必要に応じて `number` 等を追加する

---

### export_templates（テキストエクスポートテンプレートテーブル）

テキストエクスポート機能で使用するJinja2テンプレートを保存する。

| カラム名 | 型 | 制約 | 説明 |
|---|---|---|---|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | テンプレートID |
| name | TEXT | NOT NULL | テンプレート名 |
| template_body | TEXT | NOT NULL | Jinja2テンプレート本文 |
| created_at | TEXT | NOT NULL | 作成日時（ISO8601） |
| updated_at | TEXT | NOT NULL | 更新日時（ISO8601） |

**備考:**
- テキストエクスポート機能は条件付き実装（リリース可否は実装後に判断）
- テーブル自体は初期バージョンから作成しておき、機能実装に備える

---

### settings（設定テーブル）

チーム全体の設定値をkey-valueで管理する。

| カラム名 | 型 | 制約 | 説明 |
|---|---|---|---|
| key | TEXT | PRIMARY KEY | 設定キー |
| value | TEXT | NOT NULL | 設定値 |
| updated_at | TEXT | NOT NULL | 更新日時（ISO8601） |

**設定値一覧:**

| key | value例 | 説明 |
|---|---|---|
| ticket_prefix | ABC | チケット番号のプレフィックス（Manager初期設定時に必須入力） |
| default_hidden_status_ids | 3,4 | デフォルトでカンバンボードに表示しないステータスIDのカンマ区切りリスト。Managerが設定する |

**備考:**
- 将来の設定項目追加はこのテーブルにレコードを追加するだけでよい
- `default_hidden_status_ids` が空の場合はすべてのステータスを表示する

---

## work.db

### tickets（チケットテーブル）

チケットの本体データを管理する。マストフィールドのみ固定カラムとして持つ。

| カラム名 | 型 | 制約 | 説明 |
|---|---|---|---|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | チケットID（表示番号にも使用） |
| title | TEXT | NOT NULL | チケット名 |
| assignee_id | INTEGER | | 担当者ID（membersテーブル参照） |
| status_id | INTEGER | NOT NULL | ステータスID（statusesテーブル参照） |
| start_date | TEXT | | 開始日（ISO8601） |
| end_date | TEXT | | 終了予定日（ISO8601） |
| note | TEXT | | 備考 |
| is_deleted | INTEGER | NOT NULL DEFAULT 0 | 削除フラグ（1:削除済み）Manager限定で変更可能 |
| created_at | TEXT | NOT NULL | 作成日時（ISO8601） |
| updated_at | TEXT | NOT NULL | 更新日時（ISO8601） |

**備考:**
- チケットの表示番号は `{settings.ticket_prefix}-{id}` の形式で生成する（例: ABC-12）
- `assignee_id` はNULL許容（未アサインチケットを許容する）
- `assignee_id`, `status_id` はアプリ層で参照整合性を担保する（SQLiteの外部キー制約も有効化する）
- `is_deleted=1` のチケットは原則すべての画面で非表示。一度削除したチケットの復元は想定しない
- 物理削除は行わない（論理削除のみ）

---

### tag_values（タグ実体値テーブル）

各チケットに付与されたタグの実際の値を管理する。EAV（Entity-Attribute-Value）パターン。

| カラム名 | 型 | 制約 | 説明 |
|---|---|---|---|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | レコードID |
| ticket_id | INTEGER | NOT NULL | チケットID（ticketsテーブル参照） |
| tag_def_id | INTEGER | NOT NULL | タグ定義ID（tag_definitionsテーブル参照） |
| value | TEXT | | タグの値 |
| created_at | TEXT | NOT NULL | 作成日時（ISO8601） |
| updated_at | TEXT | NOT NULL | 更新日時（ISO8601） |

**制約:**
- `(ticket_id, tag_def_id)` の組み合わせにUNIQUE制約を設ける（同一チケットへの同一タグの重複登録を防ぐ）

**備考:**
- `value` はすべてTEXT型で保存する。`field_type` に応じた型変換はアプリ層で行う
- チケットは物理削除しないため、CASCADE削除は不要

---

## テーブル間の関係図

```
rules.db
  members ──────────────────┐
  statuses ─────────────────┤
  tag_definitions ──────────┤  （参照のみ、外部キーはwork.db側）
  export_templates          │
  settings                  │
                            │
work.db                     │
  tickets ──────────────────┘
    │ id
    └── tag_values.ticket_id
          │ tag_def_id
          └──→ tag_definitions.id（rules.db）
```

**注意:** SQLiteは異なるファイル間の外部キー制約をネイティブにサポートしない。`rules.db` と `work.db` をまたぐ参照整合性はアプリ層のバリデーションで担保する。

---

## チケット表示番号の生成

表示番号は `{prefix}-{id}` の形式で生成する。

- `prefix` は `settings.ticket_prefix` から取得（例: ABC）
- `id` は ticketsテーブルの AUTOINCREMENT id をそのまま使用
- 例: `ABC-1`, `ABC-12`, `ABC-334`
- チケット削除（論理削除）による欠番は許容する（番号の再利用はしない）

---

## フィルター機能のNOT条件

タグ検索およびステータス検索でNOT条件を指定できる。

- ステータスのデフォルト非表示は `settings.default_hidden_status_ids` で制御する
- カンバンボード起動時に `default_hidden_status_ids` に登録されたステータスをフィルターから自動的に除外した状態で表示する
- ユーザーはフィルターUIから手動でこの設定を上書きできる

---

## インデックス設計

| テーブル | カラム | 理由 |
|---|---|---|
| tickets | status_id | カンバンボードの列生成で頻繁に使用 |
| tickets | assignee_id | 担当者フィルターで使用 |
| tickets | start_date, end_date | 日付範囲フィルターで使用 |
| tickets | is_deleted | 削除済みチケットの除外で使用 |
| tag_values | ticket_id | チケットに紐づくタグ取得で使用 |
| tag_values | tag_def_id, value | タグ検索で使用 |

---

*作成日: 2026-02-22*
*ステータス: 初版（アーキテクチャ定義・コンポーネント設計待ち）*
