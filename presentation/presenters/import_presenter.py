"""presentation/presenters/import_presenter.py - SCR-008 進捗取り込み画面の Presenter。"""

from service.import_service import ImportService


class ImportPresenter:
    """進捗取り込み画面（SCR-008）のビジネスロジック仲介。

    ステップ: ファイル選択 → バリデーション → 差分プレビュー → 取り込み実行
    """

    def __init__(self, view: object) -> None:
        self._view = view
        self._service = ImportService()

    def on_select_file(self, file_path: str) -> None:
        """ファイル選択後に自動でバリデーションを実行する。"""
        if not file_path:
            return

        result = self._service.load_and_validate(file_path)
        if not result.is_ok:
            errors = result.data if isinstance(result.data, list) else [result.error_message]
            self._view.show_validation_errors(errors)
        else:
            diffs = self._service.get_diff()
            if not diffs:
                self._view.show_validation_errors(["変更対象のチケットがありません。"])
            else:
                self._view.show_diff_preview(diffs)

    def on_execute_import(self) -> None:
        """取り込み実行ボタン押下時の処理。"""
        result = self._service.execute()
        if result.is_ok:
            count = len(result.data) if result.data else 0
            self._view.show_success(f"{count} 件のチケットを更新しました。")
        else:
            self._view.show_error(result.error_message)

    def on_cancel(self) -> None:
        """キャンセルボタン押下時の処理。"""
        self._view.close()
