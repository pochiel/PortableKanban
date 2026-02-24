-- rules_init.sql
-- rules.db 初期テーブル作成SQL
-- IF NOT EXISTS を使用しているため、既存DBに対して再実行しても安全。

-- 担当者テーブル
-- is_active=0 で論理的に無効化する（チケットの参照整合性を保つため物理削除しない）
CREATE TABLE IF NOT EXISTS members (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL,
    email      TEXT,
    is_active  INTEGER NOT NULL DEFAULT 1,
    created_at TEXT    NOT NULL,
    updated_at TEXT    NOT NULL
);

-- ステータス定義テーブル
-- display_order の昇順でカンバンボードの列を左→右に生成する
CREATE TABLE IF NOT EXISTS statuses (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT    NOT NULL,
    display_order INTEGER NOT NULL,
    created_at    TEXT    NOT NULL,
    updated_at    TEXT    NOT NULL
);

-- タグ定義テーブル
-- field_type: 'text' または 'date'
CREATE TABLE IF NOT EXISTS tag_definitions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL,
    field_type TEXT    NOT NULL,
    created_at TEXT    NOT NULL,
    updated_at TEXT    NOT NULL
);

-- テキストエクスポートテンプレートテーブル
-- Jinja2テンプレートを保存する（条件付き実装）
CREATE TABLE IF NOT EXISTS export_templates (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT    NOT NULL,
    template_body TEXT    NOT NULL,
    created_at    TEXT    NOT NULL,
    updated_at    TEXT    NOT NULL
);

-- 設定テーブル（key-value形式）
-- ticket_prefix: チケット番号プレフィックス（例: ABC）
-- default_hidden_status_ids: デフォルト非表示ステータスIDのカンマ区切り（例: "3,4"）
CREATE TABLE IF NOT EXISTS settings (
    key        TEXT    PRIMARY KEY,
    value      TEXT    NOT NULL,
    updated_at TEXT    NOT NULL
);
