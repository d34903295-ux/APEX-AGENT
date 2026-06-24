from __future__ import annotations

from apex.obs.metrics import Registry


def test_counter_and_labels():
    r = Registry()
    c = r.counter("apex_fills_total", "fills")
    c.inc(strategy="grid", side="buy")
    c.inc(strategy="grid", side="buy")
    c.inc(strategy="dca", side="sell")
    text = r.render()
    assert 'apex_fills_total{side="buy",strategy="grid"} 2.0' in text
    assert 'apex_fills_total{side="sell",strategy="dca"} 1.0' in text


def test_gauge_set_and_inc():
    r = Registry()
    g = r.gauge("apex_equity", "equity")
    g.set(10000)
    g.inc(50)
    assert "apex_equity 10050.0" in r.render()


def test_render_has_help_and_type():
    r = Registry()
    r.counter("apex_ticks_total", "ticks ingested")
    text = r.render()
    assert "# HELP apex_ticks_total ticks ingested" in text
    assert "# TYPE apex_ticks_total counter" in text
    # empty counter still renders a zero sample (valid for scraping)
    assert "apex_ticks_total 0" in text


def test_prometheus_exposition_is_wellformed():
    r = Registry()
    r.counter("a_total", "a").inc()
    r.gauge("b", "b").set(3)
    text = r.render()
    # every non-comment line must be "name[{labels}] value"
    for line in text.strip().splitlines():
        if line.startswith("#"):
            continue
        assert len(line.rsplit(" ", 1)) == 2
        float(line.rsplit(" ", 1)[1])  # value parses as float
