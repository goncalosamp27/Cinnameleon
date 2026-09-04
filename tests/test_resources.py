from __future__ import annotations

from types import SimpleNamespace

from cinnameleon import resources


def test_discovers_desktop_resources(
    tmp_path,
    monkeypatch,
):
    home = tmp_path / "home"
    data_home = tmp_path / "data"

    monkeypatch.setenv(
        "HOME",
        str(home),
    )

    monkeypatch.setenv(
        "XDG_DATA_HOME",
        str(data_home),
    )

    monkeypatch.setenv(
        "XDG_DATA_DIRS",
        "",
    )

    gtk_theme = (
        data_home
        / "themes"
        / "TestGTK"
    )

    (gtk_theme / "gtk-3.0").mkdir(
        parents=True
    )

    (
        gtk_theme
        / "gtk-3.0"
        / "gtk.css"
    ).write_text("")

    cinnamon_theme = (
        data_home
        / "themes"
        / "TestCinnamon"
    )

    (
        cinnamon_theme
        / "cinnamon"
    ).mkdir(
        parents=True
    )

    (
        cinnamon_theme
        / "cinnamon"
        / "cinnamon.css"
    ).write_text("")

    border_theme = (
        data_home
        / "themes"
        / "TestBorder"
    )

    (
        border_theme
        / "metacity-1"
    ).mkdir(
        parents=True
    )

    (
        border_theme
        / "metacity-1"
        / "metacity-theme-3.xml"
    ).write_text("")

    icon_theme = (
        data_home
        / "icons"
        / "TestIcons"
    )

    icon_theme.mkdir(
        parents=True
    )

    (
        icon_theme
        / "index.theme"
    ).write_text("")

    cursor_theme = (
        data_home
        / "icons"
        / "TestCursor"
    )

    (
        cursor_theme
        / "cursors"
    ).mkdir(
        parents=True
    )

    resources.refresh_resource_cache()

    assert (
        resources.list_gtk_themes()
        == ("TestGTK",)
    )

    assert (
        resources.list_cinnamon_themes()
        == ("TestCinnamon",)
    )

    assert (
        resources.list_window_border_themes()
        == ("TestBorder",)
    )

    assert (
        resources.list_icon_themes()
        == ("TestIcons",)
    )

    assert (
        resources.list_cursor_themes()
        == ("TestCursor",)
    )

    assert resources.gtk_theme_exists(
        "TestGTK"
    )

    assert resources.cinnamon_theme_exists(
        "TestCinnamon"
    )

    assert (
        resources.window_border_theme_exists(
            "TestBorder"
        )
    )

    assert resources.icon_theme_exists(
        "TestIcons"
    )

    assert resources.cursor_theme_exists(
        "TestCursor"
    )


def test_lists_font_families(
    monkeypatch,
):
    def fake_run(*args, **kwargs):
        return SimpleNamespace(
            returncode=0,
            stdout=(
                "Inter,Inter Display\n"
                "JetBrains Mono\n"
                "Inter\n"
            ),
        )

    monkeypatch.setattr(
        resources.subprocess,
        "run",
        fake_run,
    )

    resources.refresh_resource_cache()

    assert resources.list_font_families() == (
        "Inter",
        "Inter Display",
        "JetBrains Mono",
    )