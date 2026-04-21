"""presentation/presenters/export_presenter.py - SCR-007 テキストエクスポート画面の Presenter。"""

from domain.filter_condition import FilterCondition
from service.export_service import ExportService
from service.member_service import MemberService
from service.status_service import StatusService
from service.tag_service import TagService


class ExportPresenter:
    """テキストエクスポート画面（SCR-007）のビジネスロジック仲介。"""

    def __init__(self, view: object) -> None:
        self._view = view
        self._export_service = ExportService()
        self._member_service = MemberService()
        self._status_service = StatusService()
        self._tag_service = TagService()
        self._current_template_id: int | None = None
        self._current_filter = FilterCondition()
        self._current_text: str = ""

    def on_load(self, initial_filter=None) -> None:
        """画面表示時の初期化。"""
        templates = self._export_service.get_all_templates()
        members = self._member_service.get_all_active()
        statuses = self._status_service.get_all()
        tag_defs = self._tag_service.get_all()

        self._view.load_templates(templates)
        self._view.init_filter(members, statuses, tag_defs)

        if initial_filter is not None:
            self._current_filter = initial_filter
            self._view.restore_filter(initial_filter)

        if templates:
            self._current_template_id = templates[0].id
            self._render()

    def on_template_changed(self, template_id: int) -> None:
        self._current_template_id = template_id
        self._render()

    def on_filter_changed(self, filter_condition: FilterCondition) -> None:
        self._current_filter = filter_condition
        self._render()

    def on_export(self, output_path: str) -> None:
        if not self._current_text:
            self._view.show_error("出力するテキストがありません。")
            return
        result = self._export_service.export_to_file(self._current_text, output_path)
        if result.is_ok:
            self._view.show_error(f"出力完了: {output_path}")
        else:
            self._view.show_error(result.error_message)

    def on_copy_to_clipboard(self) -> None:
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(self._current_text)
        self._view.show_error("クリップボードにコピーしました。")

    def _render(self) -> None:
        if self._current_template_id is None:
            self._view.show_preview("テンプレートが選択されていません。")
            return
        result = self._export_service.render(self._current_template_id, self._current_filter)
        if result.is_ok:
            self._current_text = result.data
            self._view.show_preview(result.data)
        else:
            self._view.show_error(result.error_message)
