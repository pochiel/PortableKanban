"""service/gantt_service.py - plotly を使ったガントチャートHTML生成。"""

import webbrowser

from domain.service_result import ServiceResult
from domain.ticket import Ticket


class GanttService:
    """ガントチャートHTMLを生成してファイルに保存する。

    start_date と end_date が両方設定されているチケットのみ対象とする。
    plotly がインストールされていない場合はエラーを返す。
    """

    def generate_html(
        self,
        tickets: list[Ticket],
        member_map: dict[int, str],
        status_map: dict[int, str],
        prefix: str,
        output_path: str,
    ) -> ServiceResult:
        """tickets からガントチャートHTMLを生成して output_path に保存する。"""
        try:
            import plotly.express as px
        except ImportError:
            return ServiceResult.err(
                "plotly がインストールされていません。\n"
                "pip install plotly を実行してください。"
            )

        rows = []
        for t in tickets:
            if not t.start_date or not t.end_date:
                continue
            display_num = f"{prefix}-{t.id}" if prefix else str(t.id)
            assignee = member_map.get(t.assignee_id, "未アサイン") if t.assignee_id else "未アサイン"
            status_name = status_map.get(t.status_id, "不明")
            rows.append(
                {
                    "Task": f"{display_num} {t.title}",
                    "Start": t.start_date,
                    "Finish": t.end_date,
                    "担当者": assignee,
                    "ステータス": status_name,
                }
            )

        if not rows:
            return ServiceResult.err(
                "開始日と終了予定日が両方設定されているチケットがありません。"
            )

        try:
            fig = px.timeline(
                rows,
                x_start="Start",
                x_end="Finish",
                y="Task",
                color="ステータス",
                hover_data=["担当者"],
                title="カンバンガントチャート",
            )
            fig.update_yaxes(autorange="reversed")
            fig.update_layout(
                xaxis_title="日付",
                yaxis_title="チケット",
                legend_title="ステータス",
                height=max(400, len(rows) * 40 + 150),
            )
            fig.write_html(output_path)
        except Exception as e:
            return ServiceResult.err(f"HTML生成中にエラーが発生しました: {e}")

        return ServiceResult.ok(output_path)

    def open_browser(self, file_path: str) -> ServiceResult:
        """デフォルトブラウザで HTML ファイルを開く。"""
        try:
            webbrowser.open(f"file:///{file_path.replace(chr(92), '/')}")
        except Exception as e:
            return ServiceResult.err(f"ブラウザを開けませんでした: {e}")
        return ServiceResult.ok()
