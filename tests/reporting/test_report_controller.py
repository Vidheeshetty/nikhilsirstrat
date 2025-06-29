from utils.reporting.controller import ReportController


def test_report_controller_creates_files(tmp_path):
    results = [
        {"instrument_id": "AAA", "pnl": 1},
        {"instrument_id": "BBB", "pnl": 2},
    ]
    ctrl = ReportController(root=tmp_path)
    out_dir = ctrl.generate(results)

    assert (out_dir / "trade_details.csv").exists()
    assert (out_dir / "trade_details.json").exists()
    assert (out_dir / "assets" / "report.css").exists()
    assert (out_dir / "summary.html").exists()


def test_report_controller_single(tmp_path):
    results = [{"instrument_id": "AAA", "pnl": 5}]
    ctrl = ReportController(root=tmp_path)
    out_dir = ctrl.generate(results)
    assert (out_dir / "AAA.html").exists()
    assert (out_dir / "AAA.csv").exists()
    assert (out_dir / "assets" / "report.css").exists()
