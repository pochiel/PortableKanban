# CLAUDE.md - PortableKanban 開発ガイド

## プロジェクト概要

**PortableKanban** はJTC（日本の伝統的企業）環境で使える、数名規模チーム向けの軽量カンバン型タスクマネジメントツール。

- 言語: Python
- UIフレームワーク: PyQt6
- DB: SQLite（Samba共有フォルダ上に配置）
- 配布形式: PyInstallerによる単一exe

詳細は `docs/` 配下の設計ドキュメントを参照すること。

---

## 設計ドキュメント一覧

実装前に必ず該当ドキュメントを読むこと。

| ファイル | 内容 |
|---|---|
| docs/requirements.md | 要求仕様書 |
| docs/wbs.md | WBS（実装タスク一覧・実装順序の基準） |
| docs/schema.md | スキーマ設計書（DBテーブル定義） |
| docs/architecture.md | アーキテクチャ定義書（MVPパターン・レイヤー構成） |
| docs/external_design.md | 外部設計書（画面一覧・画面遷移・UI仕様） |
| docs/component_design.md | コンポーネント設計書（クラス構成・依存関係） |

---

## ディレクトリ構成

```
PortableKanban/
├── CLAUDE.md
├── main.py                  # エントリーポイント
├── requirements.txt
├── docs/                    # 設計ドキュメント
├── presentation/
│   ├── views/               # PyQt6ウィジェット（View）
│   ├── presenters/          # Presenter
│   └── components/          # 再利用する共通ウィジェット
├── service/                 # ビジネスロジック層
├── repository/              # データアクセス層
├── domain/                  # ドメインモデル（dataclass）
├── db/                      # DB接続管理
│   └── migrations/          # 初期テーブル作成SQL
├── lock/                    # managerロック制御
└── tests/                   # テスト
```

---

## アーキテクチャ原則

### レイヤー構成（厳守）

```
プレゼンテーション層（views/ presenters/ components/）
　　　↓ 呼び出しは上から下の一方向のみ
ビジネスロジック層（service/）
　　　↓
データアクセス層（repository/）
　　　↓
DB（SQLite）
```

### 禁止事項（絶対に守ること）

- `views/` や `presenters/` から `repository/` を直接呼ぶことを禁止する
- `views/` や `presenters/` にSQLを書くことを禁止する
- `repository/` にバリデーションやビジネスロジックを書くことを禁止する
- グローバル変数の使用を禁止する（DB接続は `db/connection.py` で管理する）

---

## MVPパターン

### 処理の流れ

```
ユーザー操作 → View → Presenter → Service → Repository → DB
                                                        ↓
             View ← Presenter ← Service ← Repository
```

### ViewとPresenterの関係

- ViewはPresenterのメソッドを呼ぶだけ。ロジックを持たない
- PresenterはViewのメソッドを呼んで画面を更新する（コールバック方式）
- カスタムシグナルは原則として使用しない

```python
# Viewの書き方
def _on_save_clicked(self):
    self.presenter.on_save(title=self.title_input.text())  # Presenterを呼ぶだけ

# PresenterからViewを更新する
def on_save(self, title: str):
    result = self.ticket_service.create_ticket(title)
    if result.is_ok:
        self.view.show_success("保存しました")
        self.view.clear_inputs()
    else:
        self.view.show_error(result.error_message)
```

### ServiceResult パターン

Serviceのメソッドは必ず `ServiceResult` を返す。例外でなくResultオブジェクトで成否を伝える。

```python
# domain/service_result.py
@dataclass
class ServiceResult:
    is_ok: bool
    error_message: str = ""
    data: Any = None
```

---

## コーディング規約

### 命名規則

| 対象 | 規則 | 例 |
|---|---|---|
| クラス名 | UpperCamelCase | `TicketRepository` |
| メソッド・変数名 | snake_case | `find_by_id`, `ticket_id` |
| 定数 | UPPER_SNAKE_CASE | `DEFAULT_LOCK_TIMEOUT` |
| ファイル名 | snake_case | `ticket_repository.py` |

### 型ヒント

全関数・メソッドに型ヒントを必ず付ける。

```python
# 良い例
def find_by_id(self, ticket_id: int) -> Ticket | None: ...

# 悪い例
def find_by_id(self, ticket_id): ...
```

### ドメインモデル

各テーブルに対応するdataclassを `domain/` に定義する。
Repositoryはこのクラスを受け取り・返す。

```python
@dataclass
class Ticket:
    title: str
    status_id: int
    id: int | None = None
    ...

    @staticmethod
    def from_row(row) -> "Ticket":
        # sqlite3.Rowをdataclassに変換する
        ...
```

---

## DB接続ルール

- 接続は `db/connection.py` の `get_rules_db()` / `get_work_db()` 経由でのみ行う
- WALモードを有効化する（初期化時に設定済み）
- `row_factory = sqlite3.Row` を設定する（カラム名でアクセス可能にする）
- Samba越しのロックタイムアウト対策としてリトライ機構を実装する
- rules.dbとwork.dbをまたぐ外部キー制約はSQLiteが非対応のため、アプリ層のバリデーションで担保する

---

## ロール制御ルール

- ロールは `"manager"` / `"member"` の2種類
- ロール判定はアプリ起動時の認証結果を元に行い、以降はセッション中保持する
- manager権限が必要な処理はServiceレイヤーでロールチェックを行う
- UIの権限制御（ボタンdisable・メニュー非表示）はPresenterがViewのメソッドを呼んで行う

---

## ファイル・命名の対応表

| 画面ID | View | Presenter |
|---|---|---|
| SCR-001 | startup_view.py | startup_presenter.py |
| SCR-002 | initial_setup_view.py | initial_setup_presenter.py |
| SCR-003 | kanban_settings_view.py | kanban_settings_presenter.py |
| SCR-004 | kanban_board_view.py | kanban_board_presenter.py |
| SCR-005 | ticket_detail_view.py | ticket_detail_presenter.py |
| SCR-006 | gantt_view.py | gantt_presenter.py |
| SCR-007 | export_view.py | export_presenter.py |
| SCR-008 | import_view.py | import_presenter.py |
| SCR-009 | prompt_view.py | prompt_presenter.py |

---

## 実装の進め方

1. タスクは小さく切って1セッション1機能を基本とする
2. 実装前に必ず関連する設計ドキュメントを読む
3. 実装順序はWBS（docs/wbs.md）に従う。WBSのタスク番号を基準に進捗を管理する
4. 1タスク完了したらWBSの該当項目に完了マークをつけてから次に進む
5. テストはビジネスロジック層（service/）を優先して書く

---

*更新日: 2026-02-22*
