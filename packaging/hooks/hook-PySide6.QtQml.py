"""PyInstaller hook that bundles only the QML modules used by this app.

The upstream hook intentionally collects every installed QML module. PySide6's
wheel includes modules such as WebEngine, 3D, multimedia, charts, and virtual
keyboard that Codex Quota Guard never imports. Keeping an explicit allowlist
makes the Windows package reviewable and substantially smaller.
"""

from pathlib import Path, PurePath

from PyInstaller.utils.hooks.qt import add_qt6_dependencies, pyside6_library_info


hiddenimports, binaries, datas = add_qt6_dependencies(__file__)

qml_root = Path(pyside6_library_info.location["QmlImportsPath"])
qml_destination = PurePath(pyside6_library_info.qt_rel_dir) / "qml"


def collect_tree(relative: str) -> None:
    source = qml_root / relative
    files = [source] if source.is_file() else source.rglob("*")
    for item in files:
        if not item.is_file():
            continue
        destination = qml_destination / item.relative_to(qml_root).parent
        entry = (str(item), str(destination))
        if item.suffix.lower() in {".dll", ".so", ".dylib"}:
            binaries.append(entry)
        else:
            datas.append(entry)


for required_module in (
    "QtCore",
    "QtQml",
    "QtQuick/qmldir",
    "QtQuick/plugins.qmltypes",
    "QtQuick/qtquick2plugin.dll",
    "QtQuick/Controls/qmldir",
    "QtQuick/Controls/plugins.qmltypes",
    "QtQuick/Controls/qtquickcontrols2plugin.dll",
    "QtQuick/Controls/Basic",
    "QtQuick/Controls/impl",
    "QtQuick/Layouts",
    "QtQuick/Templates",
    "QtQuick/Window",
):
    collect_tree(required_module)
