"""presentation/presenters/prompt_presenter.py - SCR-009 プロンプト生成画面の Presenter。"""

from service.prompt_service import PromptService


class PromptPresenter:
    """プロンプト生成画面（SCR-009）のビジネスロジック仲介。"""

    def __init__(self, view: object) -> None:
        self._view = view
        self._service = PromptService()

    def on_load(self) -> None:
        """画面表示時にプロンプトとフォーマットを生成して表示する。"""
        self._generate_and_show()

    def on_regenerate(self) -> None:
        """再生成ボタン押下時。"""
        self._generate_and_show()

    def on_copy_to_clipboard(self, content: str) -> None:
        """クリップボードコピーボタン押下時。"""
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(content)
        self._view.show_copied()

    def _generate_and_show(self) -> None:
        prompt = self._service.generate_prompt()
        fmt = self._service.generate_format()
        self._view.show_prompt(prompt)
        self._view.show_format(fmt)
