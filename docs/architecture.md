# アーキテクチャ定義書: Pythonカンバン型タスクマネジメントツール

## 1. レイヤー構成

アプリケーションを3層に分割する。層をまたぐ呼び出しは必ず上から下の一方向のみとし、
プレゼンテーション層がデータアクセス層に直接触れることを禁止する。

```
┌──────────────────────────────────┐
│         プレゼンテーション層          │
│  PyQt6ウィジェット（View + Presenter）  │
│  画面の描画・ユーザー操作の受付のみ     │
├──────────────────────────────────┤
│          ビジネスロジック層           │
│  業務ルール・バリデーション・集計処理   │
│  UIにもDBにも依存しない              │
├──────────────────────────────────┤
│          データアクセス層            │
│  SQLiteへの読み書きのみ担当           │
│  Repositoryパターンで実装            │
└──────────────────────────────────┘
```

---

## 2. UIパターン: MVP（Model-View-Presenter）

### 役割分担

| コンポーネント | 役割 | 実装 |
|---|---|---|
| View | 画面の描画・ユーザー操作のイベント受付 | PyQt6ウィジェット |
| Presenter | ViewとModelの仲介。ロジックの呼び出しと結果のView反映 | 通常のPythonクラス |
| Model | ビジネスロジック・データの取得と加工 | Serviceクラス＋Repositoryクラス |

### 処理の流れ

```
ユーザー操作
    ↓
View（ボタンクリック等を検知）
    ↓ Presenterのメソッドを呼ぶ
Presenter（ロジックを呼び出す）
    ↓ Serviceのメソッドを呼ぶ
Service（業務ルールを処理する）
    ↓ Repositoryのメソッドを呼ぶ
Repository（SQLiteを操作する）
    ↓ 結果を返す
Service → Presenter → View（画面を更新する）
```

### コードサンプル

#### Viewクラス（PyQt6ウィジェット）

```python
# presentation/views/ticket_view.py
from PyQt6.QtWidgets import QWidget, QPushButton, QLineEdit, QVBoxLayout
from presentation.presenters.ticket_presenter import TicketPresenter

class TicketView(QWidget):
    def __init__(self):
        super().__init__()
        self.presenter = TicketPresenter(view=self)
        self._build_ui()

    def _build_ui(self):
        self.title_input = QLineEdit()
        self.save_button = QPushButton("保存")
        self.save_button.clicked.connect(self._on_save_clicked)

        layout = QVBoxLayout()
        layout.addWidget(self.title_input)
        layout.addWidget(self.save_button)
        self.setLayout(layout)

    def _on_save_clicked(self):
        # Viewはユーザー入力をPresenterに渡すだけ。ロジックは持たない
        self.presenter.on_save(title=self.title_input.text())

    # Presenterから呼ばれるメソッド群（画面更新の窓口）
    def show_success(self, message: str):
        # 成功メッセージを表示する処理
        pass

    def show_error(self, message: str):
        # エラーメッセージを表示する処理
        pass

    def clear_inputs(self):
        self.title_input.clear()
```

#### Presenterクラス

```python
# presentation/presenters/ticket_presenter.py
from service.ticket_service import TicketService

class TicketPresenter:
    def __init__(self, view):
        self.view = view  # Viewへの参照（型ヒントはプロトコルで定義）
        self.ticket_service = TicketService()

    def on_save(self, title: str):
        # バリデーションはServiceに任せる
        result = self.ticket_service.create_ticket(title=title)

        if result.is_ok:
            self.view.show_success("チケットを作成しました")
            self.view.clear_inputs()
        else:
            self.view.show_error(result.error_message)
```

#### Serviceクラス（ビジネスロジック層）

```python
# service/ticket_service.py
from dataclasses import dataclass
from repository.ticket_repository import TicketRepository
from repository.settings_repository import SettingsRepository
from domain.ticket import Ticket

@dataclass
class ServiceResult:
    is_ok: bool
    error_message: str = ""

class TicketService:
    def __init__(self):
        self.ticket_repo = TicketRepository()
        self.settings_repo = SettingsRepository()

    def create_ticket(self, title: str) -> ServiceResult:
        # バリデーション
        if not title.strip():
            return ServiceResult(is_ok=False, error_message="タイトルは必須です")

        # ビジネスロジック（採番など）
        prefix = self.settings_repo.get("ticket_prefix")
        ticket = Ticket(title=title, prefix=prefix)

        # 保存はRepositoryに任せる
        self.ticket_repo.save(ticket)
        return ServiceResult(is_ok=True)
```

#### Repositoryクラス（データアクセス層）

```python
# repository/ticket_repository.py
from db.connection import get_work_db_connection
from domain.ticket import Ticket

class TicketRepository:
    def find_all(self, include_deleted: bool = False) -> list[Ticket]:
        conn = get_work_db_connection()
        query = "SELECT * FROM tickets"
        if not include_deleted:
            query += " WHERE is_deleted = 0"
        rows = conn.execute(query).fetchall()
        return [Ticket.from_row(row) for row in rows]

    def find_by_id(self, ticket_id: int) -> Ticket | None:
        conn = get_work_db_connection()
        row = conn.execute(
            "SELECT * FROM tickets WHERE id = ?", (ticket_id,)
        ).fetchone()
        return Ticket.from_row(row) if row else None

    def save(self, ticket: Ticket) -> None:
        conn = get_work_db_connection()
        if ticket.id is None:
            # 新規作成
            conn.execute(
                "INSERT INTO tickets (title, status_id, ..., created_at, updated_at) VALUES (?, ?, ..., ?, ?)",
                (ticket.title, ticket.status_id, ..., now(), now())
            )
        else:
            # 更新
            conn.execute(
                "UPDATE tickets SET title=?, updated_at=? WHERE id=?",
                (ticket.title, now(), ticket.id)
            )
        conn.commit()
```

---

## 3. ディレクトリ構成

```
project_root/
├── main.py                  # エントリーポイント
├── CLAUDE.md                # Claude Code向けルールブック
├── requirements.txt
│
├── presentation/            # プレゼンテーション層
│   ├── views/               # PyQt6ウィジェット（View）
│   │   ├── kanban_view.py
│   │   ├── ticket_view.py
│   │   ├── gantt_view.py
│   │   └── ...
│   ├── presenters/          # Presenter
│   │   ├── kanban_presenter.py
│   │   ├── ticket_presenter.py
│   │   └── ...
│   └── components/          # 再利用する共通ウィジェット
│       ├── filter_widget.py
│       ├── date_range_picker.py
│       └── ...
│
├── service/                 # ビジネスロジック層
│   ├── ticket_service.py
│   ├── import_service.py    # 進捗取り込み
│   ├── export_service.py    # テキストエクスポート
│   ├── gantt_service.py
│   └── prompt_service.py    # プロンプト自動生成
│
├── repository/              # データアクセス層
│   ├── ticket_repository.py
│   ├── member_repository.py
│   ├── status_repository.py
│   ├── tag_repository.py
│   └── settings_repository.py
│
├── domain/                  # ドメインモデル（データクラス）
│   ├── ticket.py
│   ├── member.py
│   ├── status.py
│   └── tag.py
│
├── db/                      # DB接続管理
│   ├── connection.py        # 接続・WAL設定・リトライ機構
│   └── migrations/          # 初期テーブル作成SQL
│       ├── rules_init.sql
│       └── work_init.sql
│
├── lock/                    # managerロック制御
│   └── manager_lock.py
│
└── tests/                   # テスト
    ├── test_ticket_service.py
    ├── test_import_service.py
    └── ...
```

---

## 4. ドメインモデル

各テーブルに対応するデータクラスをdomain/に定義する。
Repositoryはこのクラスを受け取り・返すことでSQLの結果をアプリ内で扱いやすくする。

```python
# domain/ticket.py
from dataclasses import dataclass, field
from datetime import date

@dataclass
class Ticket:
    title: str
    status_id: int
    id: int | None = None
    assignee_id: int | None = None
    start_date: date | None = None
    end_date: date | None = None
    note: str = ""
    is_deleted: bool = False

    @staticmethod
    def from_row(row) -> "Ticket":
        # SQLiteのrowをTicketオブジェクトに変換する
        return Ticket(
            id=row["id"],
            title=row["title"],
            status_id=row["status_id"],
            assignee_id=row["assignee_id"],
            start_date=row["start_date"],
            end_date=row["end_date"],
            note=row["note"] or "",
            is_deleted=bool(row["is_deleted"]),
        )

    def display_number(self, prefix: str) -> str:
        return f"{prefix}-{self.id}"
```

---

## 5. コーディング規約

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

### 禁止事項

- プレゼンテーション層からRepositoryを直接呼ぶことを禁止する
- プレゼンテーション層にSQLを書くことを禁止する
- Repositoryにビジネスロジック（バリデーション等）を書くことを禁止する
- グローバル変数の使用を禁止する（DB接続はconnection.pyで管理する）

### ServiceResultパターン

ServiceのメソッドはServiceResultを返す。例外ではなくResultオブジェクトで成否を伝える。

```python
@dataclass
class ServiceResult:
    is_ok: bool
    error_message: str = ""
    data: Any = None  # 必要に応じて結果データを持たせる
```

---

## 6. PyQt6シグナル/スロット方針

- シグナル/スロットはView内部の部品間接続にのみ使用する
- ViewからPresenterへの呼び出しは通常のメソッド呼び出しで行う
- PresenterからViewへの呼び出しも通常のメソッド呼び出しで行う（コールバック方式）
- カスタムシグナルは原則として使用しない（追いにくくなるため）

---

*作成日: 2026-02-22*
*ステータス: 初版（コンポーネント設計・外部設計待ち）*
