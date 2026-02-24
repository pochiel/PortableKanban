"""domain/service_result.py - Service層の返り値を統一するデータクラス。"""

from dataclasses import dataclass
from typing import Any


@dataclass
class ServiceResult:
    """Service メソッドが返す共通結果オブジェクト。

    例外ではなく is_ok フラグで成否を伝える。
    成功時は data に結果データを持たせ、失敗時は error_message にメッセージを入れる。
    """

    is_ok: bool
    error_message: str = ""
    data: Any = None

    @staticmethod
    def ok(data: Any = None) -> "ServiceResult":
        return ServiceResult(is_ok=True, data=data)

    @staticmethod
    def err(message: str, data: Any = None) -> "ServiceResult":
        return ServiceResult(is_ok=False, error_message=message, data=data)
