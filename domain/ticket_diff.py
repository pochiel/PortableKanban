"""domain/ticket_diff.py - 進捗取り込み時の差分表示用データクラス。"""

from dataclasses import dataclass, field


@dataclass
class FieldDiff:
    """1フィールドの変更前後を表す。"""

    field_name: str
    before: str
    after: str


@dataclass
class TicketDiff:
    """取り込みJSONと現在のDBを比較した1チケット分の差分。"""

    ticket_id: int
    ticket_title: str
    diffs: list[FieldDiff] = field(default_factory=list)

    def has_changes(self) -> bool:
        return len(self.diffs) > 0
