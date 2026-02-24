"""service/export_service.py - Jinja2テンプレートを使ったテキストエクスポート。"""

from domain.export_template import ExportTemplate
from domain.filter_condition import FilterCondition
from domain.member import Member
from domain.service_result import ServiceResult
from domain.status import Status
from domain.tag_definition import TagDefinition
from domain.tag_value import TagValue
from domain.ticket import Ticket
from repository.export_template_repository import ExportTemplateRepository
from service.member_service import MemberService
from service.status_service import StatusService
from service.tag_service import TagService
from service.ticket_service import TicketService


class ExportService:
    """Jinja2 テンプレートを使ってチケット一覧をテキストに変換する。

    Jinja2 がインストールされていない場合はエラーを返す。
    """

    def __init__(self) -> None:
        self._template_repo = ExportTemplateRepository()
        self._ticket_service = TicketService()
        self._member_service = MemberService()
        self._status_service = StatusService()
        self._tag_service = TagService()

    def get_all_templates(self) -> list[ExportTemplate]:
        return self._template_repo.find_all()

    def render(
        self,
        template_id: int,
        filter_condition: FilterCondition,
    ) -> ServiceResult:
        """テンプレートとフィルターを受け取ってテキストを生成する。"""
        try:
            from jinja2 import Environment, BaseLoader, TemplateError
        except ImportError:
            return ServiceResult.err(
                "Jinja2 がインストールされていません。\n"
                "pip install Jinja2 を実行してください。"
            )

        template = self._template_repo.find_by_id(template_id)
        if template is None:
            return ServiceResult.err(f"テンプレートID={template_id} が見つかりません。")

        tickets = self._ticket_service.get_all(filter_condition)
        members = self._member_service.get_all_active()
        statuses = self._status_service.get_all()
        tag_defs = self._tag_service.get_all()
        prefix = self._ticket_service.get_prefix()

        member_map = {m.id: m.name for m in members}
        status_map = {s.id: s.name for s in statuses}
        tag_def_map = {t.id: t.name for t in tag_defs}

        # チケットに付加情報を付けた辞書リストを生成
        ticket_dicts = []
        for t in tickets:
            tag_values = self._ticket_service.get_tag_values(t.id)
            tag_map = {tag_def_map.get(tv.tag_def_id, str(tv.tag_def_id)): tv.value for tv in tag_values}
            display_num = f"{prefix}-{t.id}" if prefix else str(t.id)
            ticket_dicts.append(
                {
                    "id": t.id,
                    "number": display_num,
                    "title": t.title,
                    "status": status_map.get(t.status_id, ""),
                    "assignee": member_map.get(t.assignee_id, "未アサイン") if t.assignee_id else "未アサイン",
                    "start_date": t.start_date or "",
                    "end_date": t.end_date or "",
                    "note": t.note or "",
                    "tags": tag_map,
                }
            )

        try:
            env = Environment(loader=BaseLoader())
            tmpl = env.from_string(template.template_body)
            text = tmpl.render(tickets=ticket_dicts)
        except TemplateError as e:
            return ServiceResult.err(f"テンプレートのレンダリングに失敗しました: {e}")

        return ServiceResult.ok(text)

    def export_to_file(self, text: str, output_path: str) -> ServiceResult:
        """テキストをファイルに保存する。"""
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(text)
        except OSError as e:
            return ServiceResult.err(f"ファイルの書き込みに失敗しました: {e}")
        return ServiceResult.ok(output_path)

    # ------------------------------------------------------------------
    # テンプレート CRUD
    # ------------------------------------------------------------------

    def create_template(self, name: str, body: str) -> ServiceResult:
        """テンプレートを新規作成する。"""
        if not name.strip():
            return ServiceResult.err("テンプレート名を入力してください。")
        if not body.strip():
            return ServiceResult.err("テンプレート本文を入力してください。")
        t = ExportTemplate(name=name.strip(), template_body=body)
        self._template_repo.save(t)
        return ServiceResult.ok()

    def update_template(self, template_id: int, name: str, body: str) -> ServiceResult:
        """テンプレートを更新する。"""
        if not name.strip():
            return ServiceResult.err("テンプレート名を入力してください。")
        if not body.strip():
            return ServiceResult.err("テンプレート本文を入力してください。")
        t = self._template_repo.find_by_id(template_id)
        if t is None:
            return ServiceResult.err(f"テンプレートID={template_id} が見つかりません。")
        t.name = name.strip()
        t.template_body = body
        self._template_repo.save(t)
        return ServiceResult.ok()

    def delete_template(self, template_id: int) -> ServiceResult:
        """テンプレートを削除する。"""
        t = self._template_repo.find_by_id(template_id)
        if t is None:
            return ServiceResult.err(f"テンプレートID={template_id} が見つかりません。")
        self._template_repo.delete(template_id)
        return ServiceResult.ok()
