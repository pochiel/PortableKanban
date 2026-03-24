-- work_init.sql
-- work.db 初期テーブル作成SQL
-- IF NOT EXISTS を使用しているため、既存DBに対して再実行しても安全。

-- チケットテーブル
-- assignee_id, status_id はアプリ層でrules.dbとの参照整合性を担保する
-- is_deleted=1 のチケットは全画面で非表示（論理削除のみ、物理削除なし）
CREATE TABLE IF NOT EXISTS tickets (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT    NOT NULL,
    assignee_id INTEGER,
    status_id   INTEGER NOT NULL,
    start_date  TEXT,
    end_date    TEXT,
    note        TEXT,
    is_deleted  INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT    NOT NULL,
    updated_at  TEXT    NOT NULL
);

-- チケット検索・カンバン表示で頻繁に使用するカラムにインデックスを設定する
CREATE INDEX IF NOT EXISTS idx_tickets_status_id   ON tickets (status_id);
CREATE INDEX IF NOT EXISTS idx_tickets_assignee_id ON tickets (assignee_id);
CREATE INDEX IF NOT EXISTS idx_tickets_start_date  ON tickets (start_date);
CREATE INDEX IF NOT EXISTS idx_tickets_end_date    ON tickets (end_date);
CREATE INDEX IF NOT EXISTS idx_tickets_is_deleted  ON tickets (is_deleted);

-- タグ実体値テーブル（EAV: Entity-Attribute-Value パターン）
-- (ticket_id, tag_def_id) の組み合わせを UNIQUE にして重複登録を防ぐ
-- value はすべて TEXT で保存し、型変換はアプリ層が担当する
CREATE TABLE IF NOT EXISTS tag_values (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id  INTEGER NOT NULL,
    tag_def_id INTEGER NOT NULL,
    value      TEXT,
    created_at TEXT    NOT NULL,
    updated_at TEXT    NOT NULL,
    UNIQUE (ticket_id, tag_def_id)
);

-- タグ検索で頻繁に使用するカラムにインデックスを設定する
CREATE INDEX IF NOT EXISTS idx_tag_values_ticket_id        ON tag_values (ticket_id);
CREATE INDEX IF NOT EXISTS idx_tag_values_tag_def_id_value ON tag_values (tag_def_id, value);

-- チケット変更履歴テーブル
-- status / start_date / end_date の変更を時系列で記録する（分析用）
-- old_value=NULL は新規作成 or 未設定からの変更を表す
CREATE TABLE IF NOT EXISTS ticket_change_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id   INTEGER NOT NULL,
    field_name  TEXT    NOT NULL,  -- 'status' / 'start_date' / 'end_date'
    old_value   TEXT,              -- 変更前の値（NULL = 新規作成時 or 未設定）
    new_value   TEXT,              -- 変更後の値（NULL = 日付クリア）
    changed_at  TEXT    NOT NULL   -- ISO8601
);

CREATE INDEX IF NOT EXISTS idx_ticket_change_history_ticket_id   ON ticket_change_history (ticket_id);
CREATE INDEX IF NOT EXISTS idx_ticket_change_history_field_name  ON ticket_change_history (field_name);
