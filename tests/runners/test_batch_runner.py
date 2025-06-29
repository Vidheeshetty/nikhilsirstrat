from utils.runners.base_batch_runner import BatchRunner


def _dummy_worker(instrument_id: str):  # pragma: no cover – simple helper
    return {"instrument_id": instrument_id, "pnl": float(len(instrument_id))}


def test_batch_runner_parallel(tmp_path):
    instruments = ["AAA", "BB", "C"]
    runner = BatchRunner(_dummy_worker, max_workers=3)
    results = runner.run(instruments)

    assert len(results) == len(instruments)
    ids = {r["instrument_id"] for r in results}
    assert ids == set(instruments)

    agg = BatchRunner.aggregate(results)
    assert agg["num_instruments"] == 3
    # PnL should be 3 + 2 + 1 = 6.0 because of len() trick
    assert agg["total_pnl"] == 6.0
