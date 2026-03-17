"""service/prompt_service.py - ルールデータからAIプロンプトとJSONフォーマットを動的生成。"""

import json

from domain.filter_condition import FilterCondition
from domain.member import Member
from domain.status import Status
from domain.tag_definition import TagDefinition
from domain.ticket import Ticket
from service.member_service import MemberService
from service.status_service import StatusService
from service.tag_service import TagService
from service.ticket_service import TicketService


class PromptService:
    """ルールデータと現在チケット一覧からAI向けプロンプト・JSONフォーマットを生成する。"""

    def __init__(self) -> None:
        self._member_service = MemberService()
        self._status_service = StatusService()
        self._tag_service = TagService()
        self._ticket_service = TicketService()

    def generate_prompt(self) -> str:
        """AIに渡す進捗確認プロンプトを生成する。"""
        members = self._member_service.get_all_active()
        statuses = self._status_service.get_all()
        tags = self._tag_service.get_all()
        tickets = self._ticket_service.get_all(FilterCondition())
        prefix = self._ticket_service.get_prefix()

        member_list = "\n".join(
            f"  - id={m.id}, 名前={m.name}" for m in members
        )
        status_list = "\n".join(
            f"  - id={s.id}, 名前={s.name}" for s in statuses
        )
        tag_list = "\n".join(
            f"  - id={t.id}, 名前={t.name}, 型={t.field_type}" for t in tags
        ) or "  （タグ定義なし）"

        ticket_lines = []
        for t in tickets:
            display_num = f"{prefix}-{t.id}" if prefix else str(t.id)
            assignee = next((m.name for m in members if m.id == t.assignee_id), "未アサイン")
            status = next((s.name for s in statuses if s.id == t.status_id), "不明")
            ticket_lines.append(
                f"  [{display_num}] {t.title} / 担当:{assignee} / "
                f"ステータス:{status} / 終了予定:{t.end_date or '未設定'}"
            )
        ticket_list = "\n".join(ticket_lines) or "  （チケットなし）"

        return (
            "## 現在のカンバンボード状況\n\n"
            f"### 担当者一覧\n{member_list}\n\n"
            f"### ステータス一覧\n{status_list}\n\n"
            f"### タグ定義\n{tag_list}\n\n"
            f"### チケット一覧\n{ticket_list}\n\n"
            "---\n\n"
            "上記チケット一覧を確認し、以下の点について担当者にヒアリングした結果を\n"
            "JSON形式で返してください。\n\n"
            "- 各チケットの現在のステータス（変更がある場合のみ記載）\n"
            "- 担当者の変更（変更がある場合のみ記載）\n"
            "- タイトルや備考の更新（必要な場合のみ記載）\n\n"
            "変更がないチケットは含めないでください。\n"
            "出力は以下の「JSONフォーマット」タブに記載したスキーマに従ってください。"
        )

    def generate_format(self) -> str:
        """AIが返すべきJSONのフォーマット仕様を生成する。"""
        statuses = self._status_service.get_all()
        members = self._member_service.get_all_active()
        tags = self._tag_service.get_all()

        status_ids = [s.id for s in statuses]
        member_ids = [m.id for m in members]
        tag_ids = [t.id for t in tags]

        schema = {
            "description": "変更・追加があるチケットのみ含める配列",
            "type": "array",
            "items": {
                "ticket_id": "<整数: 任意 / 省略時は新規チケット作成>",
                "status_id": f"<整数: 任意 / 有効値={status_ids}>",
                "assignee_id": f"<整数またはnull: 任意 / 有効値={member_ids}>",
                "title": "<文字列: 任意（新規チケットの場合は必須）>",
                "note": "<文字列: 任意>",
            },
        }
        if tag_ids:
            schema["items"]["tag_values"] = {
                f"<tag_def_id={tid}>": "<文字列: 任意>" for tid in tag_ids
            }

        example = [
            {"ticket_id": 1, "status_id": statuses[1].id if len(statuses) > 1 else 2},
            {"ticket_id": 3, "assignee_id": members[0].id if members else 1},
            {"title": "新しいタスク名", "assignee_id": members[0].id if members else 1},
        ]

        return (
            "## JSONフォーマット仕様\n\n"
            "### スキーマ\n"
            f"```json\n{json.dumps(schema, ensure_ascii=False, indent=2)}\n```\n\n"
            "### 出力例\n"
            f"```json\n{json.dumps(example, ensure_ascii=False, indent=2)}\n```"
        )
