"""service/setup_service.py - 新規プロジェクトの初期化処理。"""

from pathlib import Path

from db.connection import init_rules_db, init_work_db, set_db_paths
from domain.service_result import ServiceResult
from repository.settings_repository import SettingsRepository
from service.auth_service import AuthService

_RULES_DB_NAME = "rules.db"
_WORK_DB_NAME = "work.db"


class SetupService:
    """新規プロジェクト（DBファイル一式）の作成を担当する。

    1. folder_path 配下に rules.db / work.db を作成
    2. マイグレーションSQLを実行（テーブル作成）
    3. ticket_prefix と manager_password を settings に保存
    """

    def create_project(
        self,
        folder_path: str,
        prefix: str,
        password: str,
        confirm: str,
    ) -> ServiceResult:
        """新規プロジェクトを作成する。

        Args:
            folder_path: DBファイルを配置するディレクトリのパス。
            prefix: チケット番号プレフィックス（例: ABC）。空文字不可。
            password: manager パスワード。空文字不可。
            confirm: パスワード確認入力。password と一致必要。

        Returns:
            is_ok=True: 作成成功。data に {"rules_db": ..., "work_db": ...} を持つ。
            is_ok=False: バリデーションエラーまたは作成失敗。
        """
        # バリデーション
        if not prefix.strip():
            return ServiceResult.err("プレフィックスを入力してください。")
        if not password:
            return ServiceResult.err("パスワードを入力してください。")
        if password != confirm:
            return ServiceResult.err("パスワードが一致しません。")

        folder = Path(folder_path)
        if not folder.exists():
            return ServiceResult.err(f"フォルダが存在しません: {folder_path}")

        rules_db_path = str(folder / _RULES_DB_NAME)
        work_db_path = str(folder / _WORK_DB_NAME)

        if Path(rules_db_path).exists() or Path(work_db_path).exists():
            return ServiceResult.err(
                "指定フォルダに既存のDBファイルが存在します。"
                "別のフォルダを選択するか、既存のDBを開いてください。"
            )

        try:
            # DBファイル作成＋テーブル初期化
            init_rules_db(rules_db_path)
            init_work_db(work_db_path)

            # 接続を切り替えてから設定を保存
            set_db_paths(rules_db_path, work_db_path)

            settings_repo = SettingsRepository()
            settings_repo.set("ticket_prefix", prefix.strip())

            auth_service = AuthService(settings_repo)
            result = auth_service.save_password(password)
            if not result.is_ok:
                return result

            # デフォルトステータスを挿入
            from service.status_service import StatusService
            ss = StatusService()
            for name in ("未着手", "仕掛り中", "完了", "保留", "CLOSE"):
                ss.create(name)

            # "CLOSE" をデフォルト非表示に設定
            all_statuses = ss.get_all()
            close_ids = [s.id for s in all_statuses if s.name == "CLOSE"]
            if close_ids:
                ss.update_default_hidden(close_ids)

        except Exception as exc:
            return ServiceResult.err(f"プロジェクト作成に失敗しました: {exc}")

        return ServiceResult.ok(
            data={"rules_db": rules_db_path, "work_db": work_db_path}
        )

    @staticmethod
    def open_project(folder_path: str) -> ServiceResult:
        """既存プロジェクトを開く（DBパスをセットする）。

        Returns:
            is_ok=True: オープン成功。
            is_ok=False: DBファイルが存在しない。
        """
        folder = Path(folder_path)
        rules_db_path = folder / _RULES_DB_NAME
        work_db_path = folder / _WORK_DB_NAME

        if not rules_db_path.exists():
            return ServiceResult.err(
                f"rules.db が見つかりません: {rules_db_path}"
            )
        if not work_db_path.exists():
            return ServiceResult.err(
                f"work.db が見つかりません: {work_db_path}"
            )

        set_db_paths(str(rules_db_path), str(work_db_path))
        return ServiceResult.ok(
            data={"rules_db": str(rules_db_path), "work_db": str(work_db_path)}
        )
