"""domain/filter_condition.py - フィルター条件の集約データクラス。"""

from dataclasses import dataclass, field
from datetime import date


@dataclass
class TagFilter:
    """タグフィルターの1条件。"""

    tag_def_id: int
    value: str
    operator: str  # "and" / "or" / "not"


@dataclass
class FilterCondition:
    """カンバンボード・ガントチャート・エクスポートで共用するフィルター条件。

    各フィールドが空リスト / None の場合は「絞り込みなし」を意味する。

    assignee_ids: 空なら全員対象。複数選択時は OR 条件。
    status_ids:   空なら全ステータス対象。複数選択時は OR 条件。
                  カンバン起動時は default_hidden_status_ids を除外した初期値をセットする。
    tag_filters:  AND / OR / NOT の組み合わせ検索が可能。
    """

    assignee_ids: list[int] = field(default_factory=list)
    status_ids: list[int] = field(default_factory=list)
    tag_filters: list[TagFilter] = field(default_factory=list)
    start_date_from: date | None = None
    start_date_to: date | None = None
    end_date_from: date | None = None
    end_date_to: date | None = None
