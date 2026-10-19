from streamlit.testing.v1 import AppTest

from finnflip.service import ROOT, load_demo


def test_ui_filters_forms_and_drafts(store, cfg, monkeypatch):
    # Keep the UI integration test isolated from the user's local database.
    import finnflip.storage

    load_demo(store, cfg)
    monkeypatch.setattr(finnflip.storage, "Store", lambda path: store)
    app = AppTest.from_file(ROOT / "app.py", default_timeout=20).run()
    assert not app.exception
    assert app.sidebar.checkbox[0].value is True
    assert 0 < int(app.metric[0].value) < 11
    app.sidebar.checkbox[0].uncheck().run()
    assert app.metric[0].value == "11"
    app.sidebar.selectbox[0].select("garmin").run()
    assert not app.exception
    assert app.metric[0].value == "6"
    app.sidebar.multiselect[0].set_value(["U"]).run()
    assert not app.exception
    assert app.metric[0].value == "3"
    next(button for button in app.button if button.label == "Lag nye e-postutkast").click().run()
    assert not app.exception
    assert any("0 nye utkast" in item.value for item in app.success)


def test_live_view_and_fetch_button(store, cfg, candidates, at, monkeypatch):
    import finnflip.scraper
    import finnflip.storage
    from finnflip.service import run_analysis

    c = candidates["attractive"].model_copy(
        update={"source": "finn_public", "demo": False, "title": "MacBook Air M1 live test"}
    )
    key = f"{c.source}:{c.id}"
    store.import_rows("candidates", [c], {}, at)
    store.see_live_item(key, "MacBook", ["RAM må kontrolleres"], at)
    run_analysis(store, cfg, at)
    monkeypatch.setattr(finnflip.storage, "Store", lambda path: store)
    monkeypatch.setattr(
        finnflip.scraper, "scrape_once", lambda *args, **kwargs: {"candidates": 1, "errors": []}
    )
    app = AppTest.from_file(ROOT / "app.py", default_timeout=20).run()
    assert not app.exception and app.metric[0].value == "0"
    assert app.metric[1].value == "1"
    assert any("Ingen annonser med positivt" in item.value for item in app.info)
    app.sidebar.checkbox[0].uncheck().run()
    assert app.metric[0].value == "1"
    assert app.sidebar.selectbox[1].value == "FINN"
    assert not any("DEMO er" in w.value for w in app.warning)
    next(b for b in app.button if b.label == "Hent fra FINN nå").click().run()
    assert not app.exception
    assert any("Hentet 1 annonser" in x.value for x in app.success)
