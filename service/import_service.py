"""service/import_service.py - JSONファイルの取り込み・バリデーション・DB反映。"""

import json
from datetime import datetime

from domain.filter_condition import FilterCondition
from domain.service_result import ServiceResult
from domain.ticket import Ticket
from domain.ticket_diff import FieldDiff, TicketDiff
from service.member_service import MemberService
from service.status_service import StatusService
from service.ticket_service import TicketService


class ImportService:
    """AIが生成したJSONを取り込んでチケットを更新する。

    処理フロー:
      1. load_and_validate() → JSONロード + バリデーション → valid_updates を保持
      2. get_diff()          → 差分計算 → プレビュー用 list[TicketDiff]
      3. execute()           → DB 反映（トランザクション相当）
    """

    def __init__(self) -> None:
        self._ticket_service = TicketService()
        self._member_service = MemberService()
        self._status_service = StatusService()
        self._valid_updates: list[dict] = []

    # ------------------------------------------------------------------
    # ① ロード・バリデーション
    # ------------------------------------------------------------------

    def load_and_validate(self, file_path: str) -> ServiceResult:
        """JSONファイルを読んでバリデーションする。エラー一覧は data に list[str]。"""
        try:
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            return ServiceResult.err(f"ファイルが見つかりません: {file_path}")
        except json.JSONDecodeError as e:
            return ServiceResult.err(f"JSONの解析に失敗しました: {e}")

        if not isinstance(data, list):
            return ServiceResult.err("JSONはオブジェクトの配列（[...]）である必要があります。")

        errors: list[str] = []
        valid: list[dict] = []

        # ルールデータを一度だけ取得
        all_status_ids = {s.id for s in self._status_service.get_all()}
        all_member_ids = {m.id for m in self._member_service.get_all_active()}

        for i, item in enumerate(data):
            prefix = f"[{i}]"
            if not isinstance(item, dict):
                errors.append(f"{prefix} オブジェクトではありません。")
                continue

            ticket_id = item.get("ticket_id")
            is_new = ticket_id is None

            if not is_new:
                if not isinstance(ticket_id, int):
                    errors.append(f"{prefix} ticket_id は整数である必要があります。")
                    continue
                if self._ticket_service.get_by_id(ticket_id) is None:
                    errors.append(f"{prefix} ticket_id={ticket_id} は存在しません。")
                    continue
            else:
                # 新規チケット: title 必須
                title = item.get("title")
                if not isinstance(title, str) or not title.strip():
                    errors.append(f"{prefix} 新規チケット（ticket_id なし）には title が必須です。")
                    continue

            row_errors = self._validate_fields(item, all_status_ids, all_member_ids, prefix)
            if row_errors:
                errors.extend(row_errors)
            else:
                valid.append(item)

        if errors:
            return ServiceResult.err("\n".join(errors), data=errors)

        self._valid_updates = valid
        return ServiceResult.ok(valid)

    def _validate_fields(
        self,
        item: dict,
        valid_status_ids: set,
        valid_member_ids: set,
        prefix: str,
    ) -> list[str]:
        errors = []
        if "status_id" in item:
            if not isinstance(item["status_id"], int) or item["status_id"] not in valid_status_ids:
                errors.append(
                    f"{prefix} status_id={item['status_id']} は無効です。"
                    f"有効値: {sorted(valid_status_ids)}"
                )
        if "assignee_id" in item:
            aid = item["assignee_id"]
            if aid is not None and (not isinstance(aid, int) or aid not in valid_member_ids):
                errors.append(
                    f"{prefix} assignee_id={aid} は無効です。"
                    f"有効値: {sorted(valid_member_ids)} または null"
                )
        if "title" in item and not isinstance(item["title"], str):
            errors.append(f"{prefix} title は文字列である必要があります。")
        if "note" in item and not isinstance(item["note"], str):
            errors.append(f"{prefix} note は文字列である必要があります。")
        for field_name in ("start_date", "end_date"):
            if field_name in item:
                val = item[field_name]
                if val is not None and not _is_iso_date(val):
                    errors.append(
                        f"{prefix} {field_name} の形式が不正です（YYYY-MM-DD 形式で指定してください）。"
                    )
        return errors

    # ------------------------------------------------------------------
    # ② 差分計算
    # ------------------------------------------------------------------

    def get_diff(self) -> list[TicketDiff]:
        """validate 済み updates と現在 DB を比較して差分を返す。"""
        member_map = {m.id: m.name for m in self._member_service.get_all_active()}
        status_map = {s.id: s.name for s in self._status_service.get_all()}

        diffs: list[TicketDiff] = []
        for item in self._valid_updates:
            if item.get("ticket_id") is not None:
                # 既存チケットの更新
                ticket = self._ticket_service.get_by_id(item["ticket_id"])
                if ticket is None:
                    continue

                field_diffs: list[FieldDiff] = []
                if "status_id" in item and item["status_id"] != ticket.status_id:
                    field_diffs.append(
                        FieldDiff(
                            "ステータス",
                            status_map.get(ticket.status_id, str(ticket.status_id)),
                            status_map.get(item["status_id"], str(item["status_id"])),
                        )
                    )
                if "assignee_id" in item and item["assignee_id"] != ticket.assignee_id:
                    before = member_map.get(ticket.assignee_id, "未アサイン") if ticket.assignee_id else "未アサイン"
                    after = member_map.get(item["assignee_id"], "未アサイン") if item["assignee_id"] else "未アサイン"
                    field_diffs.append(FieldDiff("担当者", before, after))
                if "title" in item and item["title"] != ticket.title:
                    field_diffs.append(FieldDiff("タイトル", ticket.title, item["title"]))
                if "note" in item and item["note"] != (ticket.note or ""):
                    field_diffs.append(FieldDiff("備考", ticket.note or "", item["note"]))
                if "start_date" in item and item["start_date"] != ticket.start_date:
                    field_diffs.append(FieldDiff("開始日", ticket.start_date or "", item["start_date"] or ""))
                if "end_date" in item and item["end_date"] != ticket.end_date:
                    field_diffs.append(FieldDiff("終了予定日", ticket.end_date or "", item["end_date"] or ""))

                diffs.append(TicketDiff(ticket.id, ticket.title, field_diffs))
            else:
                # 新規チケットの作成
                title = item["title"]
                field_diffs = []
                if "status_id" in item:
                    field_diffs.append(
                        FieldDiff("ステータス", "（新規）", status_map.get(item["status_id"], str(item["status_id"])))
                    )
                if "assignee_id" in item and item["assignee_id"] is not None:
                    field_diffs.append(
                        FieldDiff("担当者", "（新規）", member_map.get(item["assignee_id"], str(item["assignee_id"])))
                    )
                if "note" in item and item["note"]:
                    field_diffs.append(FieldDiff("備考", "（新規）", item["note"]))
                if "start_date" in item and item["start_date"]:
                    field_diffs.append(FieldDiff("開始日", "（新規）", item["start_date"]))
                if "end_date" in item and item["end_date"]:
                    field_diffs.append(FieldDiff("終了予定日", "（新規）", item["end_date"]))
                diffs.append(TicketDiff(None, title, field_diffs, is_new=True))

        return diffs

    # ------------------------------------------------------------------
    # ③ DB反映
    # ------------------------------------------------------------------

    def execute(self) -> ServiceResult:
        """validate 済み updates を DB に反映する。1件でも失敗したら全体を中断。"""
        if not self._valid_updates:
            return ServiceResult.err("取り込み対象がありません。")

        default_status_id = min(s.id for s in self._status_service.get_all())
        applied: list[int] = []
        try:
            for item in self._valid_updates:
                tag_values = {
                    int(k): v
                    for k, v in item.get("tag_values", {}).items()
                }
                if item.get("ticket_id") is not None:
                    # 既存チケットの更新
                    ticket = self._ticket_service.get_by_id(item["ticket_id"])
                    if ticket is None:
                        raise ValueError(f"ticket_id={item['ticket_id']} が見つかりません。")

                    current_tags = self._ticket_service.get_tag_values(ticket.id)
                    current_tag_map = {tv.tag_def_id: tv.value for tv in current_tags}
                    current_tag_map.update(tag_values)

                    result = self._ticket_service.update(
                        ticket_id=ticket.id,
                        title=item.get("title", ticket.title),
                        status_id=item.get("status_id", ticket.status_id),
                        assignee_id=item.get("assignee_id", ticket.assignee_id),
                        start_date=item.get("start_date", ticket.start_date),
                        end_date=item.get("end_date", ticket.end_date),
                        note=item.get("note", ticket.note or ""),
                        tag_values=current_tag_map,
                    )
                    if not result.is_ok:
                        raise ValueError(
                            f"ticket_id={ticket.id} の更新に失敗: {result.error_message}"
                        )
                    applied.append(result.data.id)
                else:
                    # 新規チケットの作成
                    result = self._ticket_service.create(
                        title=item["title"],
                        status_id=item.get("status_id", default_status_id),
                        assignee_id=item.get("assignee_id"),
                        start_date=item.get("start_date"),
                        end_date=item.get("end_date"),
                        note=item.get("note", ""),
                        tag_values=tag_values or None,
                    )
                    if not result.is_ok:
                        raise ValueError(f"新規チケット「{item['title']}」の作成に失敗: {result.error_message}")
                    applied.append(result.data.id)

        except ValueError as e:
            return ServiceResult.err(
                f"取り込み中にエラーが発生しました（ロールバック済み）:\n{e}"
            )

        return ServiceResult.ok(applied)


def _is_iso_date(value) -> bool:
    """YYYY-MM-DD 形式かどうかを検証する。"""
    if not isinstance(value, str):
        return False
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except ValueError:
        return False
