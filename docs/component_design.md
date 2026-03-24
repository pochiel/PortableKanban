# コンポーネント設計書: Pythonカンバン型タスクマネジメントツール

## 1. 全体構成図

```
main.py
  └→ AppController（アプリ起動・画面管理）
        │
        ├── presentation/
        │     ├── views/          # PyQt6ウィジェット
        │     ├── presenters/     # Presenter
        │     └── components/     # 共通ウィジェット
        │
        ├── service/              # ビジネスロジック
        │
        ├── repository/           # データアクセス
        │
        ├── domain/               # データクラス
        │
        ├── db/                   # DB接続管理
        │
        └── lock/                 # managerロック制御
```

---

## 2. プレゼンテーション層

### 2.1 Views（PyQt6ウィジェット）

#### StartupView（SCR-001 起動画面）
```
ファイル: presentation/views/startup_view.py
責務: DBパス指定・ログイン・新規作成のUI表示
対応Presenter: StartupPresenter
主要シグナル受付:
  - フォルダ選択ボタン押下
  - ログインボタン押下
  - 新規作成ボタン押下
Presenterから呼ばれるメソッド:
  - set_db_path(path: str)        # パス欄を更新する
  - show_error(message: str)      # エラーメッセージを表示する
  - go_to_initial_setup()         # SCR-002へ遷移する
  - go_to_kanban_board(role: str) # SCR-004へ遷移する
```

#### InitialSetupView（SCR-002 初期設定画面）
```
ファイル: presentation/views/initial_setup_view.py
責務: 新規DB作成・プレフィックス・パスワード設定のUI表示
対応Presenter: InitialSetupPresenter
主要シグナル受付:
  - 作成ボタン押下
  - キャンセルボタン押下
Presenterから呼ばれるメソッド:
  - show_error(message: str)
  - go_to_kanban_board()
  - go_to_startup()
```

#### KanbanSettingsView（SCR-003 カンバン設定画面）
```
ファイル: presentation/views/kanban_settings_view.py
責務: 担当者・ステータス・タグ定義管理のUI表示（タブ形式）
対応Presenter: KanbanSettingsPresenter
主要シグナル受付:
  - 各タブの追加・編集・削除・並び順変更ボタン押下
  - デフォルト非表示ステータスのチェックボックス変更
Presenterから呼ばれるメソッド:
  - load_members(members: list[Member])
  - load_statuses(statuses: list[Status])
  - load_tag_definitions(tags: list[TagDefinition])
  - show_error(message: str)
  - show_success(message: str)
```

#### KanbanBoardView（SCR-004 カンバンボード画面）
```
ファイル: presentation/views/kanban_board_view.py
責務: カンバンボードのメイン画面表示
対応Presenter: KanbanBoardPresenter
主要シグナル受付:
  - カードクリック
  - カードドラッグ&ドロップ（全ロール）
  - 新規チケットボタン押下
  - ↻ 更新ボタン押下
  - フィルター条件変更
  - メニュー各項目選択
Presenterから呼ばれるメソッド:
  - render_board(columns: list[StatusColumn])  # 列とカードを描画する
  - show_manager_warning(locker_info: str)     # 編集中警告バナーを表示する
  - hide_manager_warning()
  - set_role(role: str)                        # ロールに応じてUI制御する
  - open_ticket_detail(ticket_id: int)
  - get_current_filter() -> FilterCondition    # 現在のフィルター条件を返す
  - restore_filter(condition: FilterCondition) # フィルター条件を復元する（reload後に呼ぶ）
```

#### TicketDetailView（SCR-005 チケット詳細・編集画面）
```
ファイル: presentation/views/ticket_detail_view.py
責務: チケット詳細の表示と編集UI
対応Presenter: TicketDetailPresenter
主要シグナル受付:
  - 保存ボタン押下
  - 削除ボタン押下（manager限定）
  - コピーして新規作成ボタン押下（全ロール・既存チケットのみ）
  - 戻るボタン押下
Presenterから呼ばれるメソッド:
  - load_ticket(ticket: Ticket, tags: list[TagValue])
  - load_members(members: list[Member])
  - load_statuses(statuses: list[Status])
  - load_tag_definitions(tags: list[TagDefinition])
  - set_editable(editable: bool, can_delete: bool)  # ロールに応じて入力欄・ボタンを制御する
  - show_error(message: str)
  - go_to_kanban_board()
  - go_to_ticket_detail(ticket_id: int)  # コピー後に複製チケット詳細へ遷移
```

#### GanttView（SCR-006 ガントチャート出力画面）
```
ファイル: presentation/views/gantt_view.py
責務: ガントチャートの生成・出力UI（別ウィンドウ）
対応Presenter: GanttPresenter
主要シグナル受付:
  - フィルター条件変更
  - HTML出力ボタン押下
  - ブラウザで開くボタン押下
Presenterから呼ばれるメソッド:
  - load_preview(tickets: list[Ticket])
  - set_output_ready(path: str)    # 出力完了後にブラウザで開くボタンを活性化する
  - show_error(message: str)
```

#### ExportView（SCR-007 テキストエクスポート画面）
```
ファイル: presentation/views/export_view.py
責務: テキストエクスポートのUI（別ウィンドウ）
対応Presenter: ExportPresenter
主要シグナル受付:
  - テンプレート選択変更
  - フィルター条件変更
  - エクスポートボタン押下
  - クリップボードコピーボタン押下
Presenterから呼ばれるメソッド:
  - load_templates(templates: list[ExportTemplate])
  - show_preview(text: str)
  - show_error(message: str)
```

#### ImportView（SCR-008 進捗取り込み画面）
```
ファイル: presentation/views/import_view.py
責務: 進捗取り込みのステップUI（別ウィンドウ）
対応Presenter: ImportPresenter
主要シグナル受付:
  - ファイル選択ボタン押下
  - 取り込み実行ボタン押下
  - キャンセルボタン押下
Presenterから呼ばれるメソッド:
  - show_validation_errors(errors: list[str])
  - show_diff_preview(diffs: list[TicketDiff])
  - show_success(message: str)
  - show_error(message: str)        # ロールバック済みの旨を含む
```

#### PromptView（SCR-009 エクスポート画面）
```
ファイル: presentation/views/prompt_view.py
責務: データベース情報とJSONフォーマットの表示UI（別ウィンドウ）
対応Presenter: PromptPresenter
主要シグナル受付:
  - クリップボードコピーボタン押下
  - 再生成ボタン押下
Presenterから呼ばれるメソッド:
  - show_prompt(prompt: str)
  - show_format(format_json: str)
```

---

### 2.2 Presenters

#### StartupPresenter
```
ファイル: presentation/presenters/startup_presenter.py
依存Service: AuthService, ConfigService
主要メソッド:
  - on_select_folder()           # フォルダ選択ダイアログを開く
  - on_login(password: str)      # 認証処理を呼び出す
  - on_new_project()             # 新規作成画面へ遷移する
```

#### InitialSetupPresenter
```
ファイル: presentation/presenters/initial_setup_presenter.py
依存Service: SetupService, AuthService
主要メソッド:
  - on_create(prefix: str, password: str, confirm: str)
```

#### KanbanSettingsPresenter
```
ファイル: presentation/presenters/kanban_settings_presenter.py
依存Service: MemberService, StatusService, TagService
主要メソッド:
  - on_load()
  - on_add_member(name: str, email: str)
  - on_edit_member(member_id: int, name: str, email: str)
  - on_deactivate_member(member_id: int)
  - on_add_status(name: str, order: int)
  - on_edit_status(status_id: int, name: str)
  - on_delete_status(status_id: int)
  - on_reorder_status(status_id: int, direction: str)
  - on_update_default_hidden(status_ids: list[int])
  - on_add_tag(name: str, field_type: str)
  - on_edit_tag(tag_id: int, name: str, field_type: str)
  - on_delete_tag(tag_id: int)
```

#### KanbanBoardPresenter
```
ファイル: presentation/presenters/kanban_board_presenter.py
依存Service: TicketService, StatusService, LockService
主要メソッド:
  - on_load(role: str)
  - on_filter_changed(filter: FilterCondition)
  - reload_and_render()   # マスタ再取得 + フィルター保持のまま再描画（更新ボタン・別ウィンドウclose時に呼ぶ）
  - on_card_dropped(ticket_id: int, new_status_id: int)
  - on_card_clicked(ticket_id: int)
  - on_new_ticket()
```

#### TicketDetailPresenter
```
ファイル: presentation/presenters/ticket_detail_presenter.py
依存Service: TicketService, MemberService, StatusService, TagService
主要メソッド:
  - on_load(ticket_id: int | None, role: str)  # Noneなら新規作成
  - on_save(ticket_data: dict, tag_values: dict)
  - on_delete(ticket_id: int)
  - on_clone()  # 同内容でタイトルに「 のコピー」を付けて新規作成し複製チケット詳細へ遷移
```

#### GanttPresenter
```
ファイル: presentation/presenters/gantt_presenter.py
依存Service: TicketService, GanttService
主要メソッド:
  - on_load()
  - on_filter_changed(filter: FilterCondition)
  - on_export_html(output_path: str)
  - on_open_browser()
```

#### ExportPresenter
```
ファイル: presentation/presenters/export_presenter.py
依存Service: ExportService, TicketService
主要メソッド:
  - on_load()
  - on_template_changed(template_id: int)
  - on_filter_changed(filter: FilterCondition)
  - on_export(output_path: str)
  - on_copy_to_clipboard()
```

#### ImportPresenter
```
ファイル: presentation/presenters/import_presenter.py
依存Service: ImportService
主要メソッド:
  - on_select_file(file_path: str)
  - on_execute_import()
  - on_cancel()
```

#### PromptPresenter
```
ファイル: presentation/presenters/prompt_presenter.py
依存Service: PromptService
主要メソッド:
  - on_load()
  - on_regenerate()
  - on_copy_to_clipboard(content: str)
```

---

### 2.3 共通コンポーネント

#### FilterWidget
```
ファイル: presentation/components/filter_widget.py
責務: 担当者・ステータス・タグ・日付によるフィルター条件入力UI
使用画面: SCR-004, SCR-006, SCR-007
インターフェース:
  - set_members(members: list[Member])
  - set_statuses(statuses: list[Status])
  - set_tag_definitions(tags: list[TagDefinition])
  - set_default_hidden_statuses(status_ids: list[int])
  - get_condition() -> FilterCondition            # 現在の条件を返す
  - restore_condition(condition: FilterCondition) # チェックボックス状態を復元する（reload後に呼ぶ）
  シグナル:
  - condition_changed                             # 条件変更時に発火
```

#### KanbanCardWidget
```
ファイル: presentation/components/kanban_card_widget.py
責務: カンバンボード上の1チケットカードのUI
表示項目: チケット番号・タイトル・担当者・終了予定日
インターフェース:
  - set_ticket(ticket: Ticket)
  - set_draggable(enabled: bool)   # ロールに応じてドラッグ制御
```

#### KanbanColumnWidget
```
ファイル: presentation/components/kanban_column_widget.py
責務: カンバンボードの1列（ステータス列）のUI
インターフェース:
  - set_status(status: Status)
  - add_card(card: KanbanCardWidget)
  - clear_cards()
  シグナル:
  - card_dropped(ticket_id: int, status_id: int)  # ドロップ時に発火
```

#### DateRangePickerWidget
```
ファイル: presentation/components/date_range_picker_widget.py
責務: FROM/TO日付範囲の入力UI
FilterWidgetから利用する
インターフェース:
  - get_range() -> tuple[date | None, date | None]
  - clear()
```

---

## 3. ビジネスロジック層（Service）

#### AuthService
```
ファイル: service/auth_service.py
責務: manager認証・パスワードのハッシュ化
主要メソッド:
  - authenticate(password: str) -> ServiceResult  # 認証成功/失敗を返す
  - hash_password(password: str) -> str
  - save_password(hashed: str) -> ServiceResult
```

#### ConfigService
```
ファイル: service/config_service.py
責務: config.iniの読み書き
主要メソッド:
  - get_last_db_path() -> str | None
  - save_last_db_path(path: str) -> None
```

#### SetupService
```
ファイル: service/setup_service.py
責務: 新規プロジェクトの初期化
主要メソッド:
  - create_project(folder_path: str, prefix: str, password: str, confirm: str) -> ServiceResult
```

#### MemberService
```
ファイル: service/member_service.py
責務: 担当者のCRUD
主要メソッド:
  - get_all_active() -> list[Member]
  - create(name: str, email: str) -> ServiceResult
  - update(member_id: int, name: str, email: str) -> ServiceResult
  - deactivate(member_id: int) -> ServiceResult
```

#### StatusService
```
ファイル: service/status_service.py
責務: ステータス定義のCRUD・表示順管理
主要メソッド:
  - get_all() -> list[Status]
  - create(name: str) -> ServiceResult
  - update(status_id: int, name: str) -> ServiceResult
  - delete(status_id: int) -> ServiceResult   # 使用中チェックあり
  - reorder(status_id: int, direction: str) -> ServiceResult
  - get_default_hidden_ids() -> list[int]
  - update_default_hidden(status_ids: list[int]) -> ServiceResult
```

#### TagService
```
ファイル: service/tag_service.py
責務: タグ定義のCRUD
主要メソッド:
  - get_all() -> list[TagDefinition]
  - create(name: str, field_type: str) -> ServiceResult
  - update(tag_id: int, name: str, field_type: str) -> ServiceResult
  - delete(tag_id: int) -> ServiceResult   # 使用中チェックあり
```

#### TicketService
```
ファイル: service/ticket_service.py
責務: チケットのCRUD・フィルター検索
主要メソッド:
  - get_all(filter: FilterCondition) -> list[Ticket]
  - get_by_id(ticket_id: int) -> Ticket | None
  - create(title: str, status_id: int, ..., tag_values: dict) -> ServiceResult
  - update(ticket_id: int, ..., tag_values: dict) -> ServiceResult
  - soft_delete(ticket_id: int) -> ServiceResult
  - change_status(ticket_id: int, new_status_id: int) -> ServiceResult
```

#### GanttService
```
ファイル: service/gantt_service.py
責務: plotlyを使ったガントチャートHTML生成
主要メソッド:
  - generate_html(tickets: list[Ticket], output_path: str) -> ServiceResult
```

#### ExportService
```
ファイル: service/export_service.py
責務: Jinja2テンプレートを使ったテキストエクスポート
主要メソッド:
  - get_all_templates() -> list[ExportTemplate]
  - render(template_id: int, tickets: list[Ticket]) -> str
  - export_to_file(text: str, output_path: str) -> ServiceResult
```

#### ImportService
```
ファイル: service/import_service.py
責務: JSONファイルの取り込み・バリデーション・DB反映
      ticket_id あり → 既存チケットの更新
      ticket_id なし → 新規チケットの作成（title 必須）
主要メソッド:
  - load_and_validate(file_path: str) -> ServiceResult
  - get_diff() -> list[TicketDiff]
  - execute() -> ServiceResult   # トランザクション制御
```

#### PromptService
```
ファイル: service/prompt_service.py
責務: ルールデータからデータベース情報とJSONフォーマットを動的生成
主要メソッド:
  - generate_prompt() -> str
  - generate_format() -> str
```

#### LockService
```
ファイル: service/lock_service.py
責務: managerロックファイルの制御
主要メソッド:
  - acquire() -> ServiceResult      # ロック取得（先客いれば失敗）
  - release() -> None               # ロック解放
  - is_locked_by_other() -> bool    # 他managerがロック中か確認
  - get_locker_info() -> str | None # ロック中のmanager情報を返す
  - start_heartbeat() -> None       # バックグラウンドでハートビート開始
  - stop_heartbeat() -> None
```

---

## 4. データアクセス層（Repository）

#### MemberRepository
```
ファイル: repository/member_repository.py
主要メソッド:
  - find_all_active() -> list[Member]
  - find_by_id(member_id: int) -> Member | None
  - save(member: Member) -> None
  - deactivate(member_id: int) -> None
```

#### StatusRepository
```
ファイル: repository/status_repository.py
主要メソッド:
  - find_all() -> list[Status]
  - find_by_id(status_id: int) -> Status | None
  - save(status: Status) -> None
  - delete(status_id: int) -> None
  - is_in_use(status_id: int) -> bool
```

#### TagRepository
```
ファイル: repository/tag_repository.py
主要メソッド:
  - find_all() -> list[TagDefinition]
  - find_by_id(tag_id: int) -> TagDefinition | None
  - save(tag: TagDefinition) -> None
  - delete(tag_id: int) -> None
  - is_in_use(tag_id: int) -> bool
```

#### TicketRepository
```
ファイル: repository/ticket_repository.py
主要メソッド:
  - find_all(filter: FilterCondition, include_deleted: bool = False) -> list[Ticket]
  - find_by_id(ticket_id: int) -> Ticket | None
  - save(ticket: Ticket) -> None
  - soft_delete(ticket_id: int) -> None
```

#### TagValueRepository
```
ファイル: repository/tag_value_repository.py
主要メソッド:
  - find_by_ticket(ticket_id: int) -> list[TagValue]
  - save_all(ticket_id: int, tag_values: list[TagValue]) -> None  # 既存を削除して全件insert
```

#### TicketChangeHistoryRepository
```
ファイル: repository/ticket_change_history_repository.py
責務: ticket_change_history テーブルへのINSERT専用（読み取りは外部分析ツール想定）
主要メソッド:
  - record(ticket_id, field_name, old_value, new_value) -> None
  - record_many(records: list[tuple]) -> None  # (ticket_id, field_name, old, new) のリスト
```

#### SettingsRepository
```
ファイル: repository/settings_repository.py
主要メソッド:
  - get(key: str) -> str | None
  - set(key: str, value: str) -> None
```

#### ExportTemplateRepository
```
ファイル: repository/export_template_repository.py
主要メソッド:
  - find_all() -> list[ExportTemplate]
  - find_by_id(template_id: int) -> ExportTemplate | None
  - save(template: ExportTemplate) -> None
```

---

## 5. ドメインモデル（Domain）

```
domain/
  - ticket.py          # Ticket dataclass
  - member.py          # Member dataclass
  - status.py          # Status dataclass
  - tag_definition.py  # TagDefinition dataclass
  - tag_value.py       # TagValue dataclass
  - export_template.py # ExportTemplate dataclass
  - filter_condition.py # FilterCondition dataclass（フィルター条件の集約）
  - ticket_diff.py     # TicketDiff dataclass（進捗取り込みの差分表示用）
  - service_result.py  # ServiceResult dataclass（全Service共通）
```

#### FilterCondition（重要）
```python
# domain/filter_condition.py
from dataclasses import dataclass, field
from datetime import date

@dataclass
class TagFilter:
    tag_def_id: int
    value: str
    operator: str  # "and" / "or" / "not"

@dataclass
class FilterCondition:
    assignee_ids: list[int] = field(default_factory=list)
    # 空なら全員対象。複数選択時はOR条件（どれかが担当のチケットを表示）

    status_ids: list[int] = field(default_factory=list)
    # 空なら全ステータス対象。複数選択時はOR条件
    # default_hidden_status_idsに基づきアプリ起動時にチェックを外した状態で初期化する

    tag_filters: list[TagFilter] = field(default_factory=list)
    # タグはAND/OR/NOT全対応（複数タグの組み合わせ検索があるため）

    start_date_from: date | None = None
    start_date_to: date | None = None
    end_date_from: date | None = None
    end_date_to: date | None = None
```

---

## 6. DB接続管理

#### connection.py
```
ファイル: db/connection.py
責務: DBへの接続・WAL設定・リトライ機構・接続のシングルトン管理
主要関数:
  - get_rules_db() -> sqlite3.Connection
  - get_work_db() -> sqlite3.Connection
  - init_rules_db(db_path: str) -> None   # 初回作成時にSQLを実行
  - init_work_db(db_path: str) -> None
設定:
  - WALモード有効化
  - row_factory = sqlite3.Row（カラム名でアクセス可能にする）
  - タイムアウト・リトライ回数は定数で管理
```

---

## 7. その他

#### AppController
```
ファイル: main.py または app_controller.py
責務: アプリ起動・QApplicationの初期化・画面管理（メインウィンドウの切り替え）
```

#### lock/manager_lock.py
```
責務: ロックファイルの物理的な読み書き（LockServiceから呼ばれる）
ロックファイル形式（JSON）:
  {
    "manager": "user_name",
    "timestamp": "2026-02-22T10:00:00"
  }
```

---

*作成日: 2026-02-22*
*ステータス: 初版*
