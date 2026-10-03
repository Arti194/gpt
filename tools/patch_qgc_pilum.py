#!/usr/bin/env python3
"""Apply Pilum branding without changing QGC's existing settings namespace."""

from pathlib import Path
import shutil


ROOT = Path.cwd()
ASSETS = Path(__file__).resolve().parent / "pilum"
DISPLAY_NAME = "QGroundControl Pilum"


def edit(path: str, old: str, new: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"Pilum patch marker missing in {path}: {old[:100]}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


# Application name and organization still select the previous camera/settings file.
edit(
    "src/QGCApplication.cc",
    "    setApplicationName(applicationName);",
    "    setApplicationName(applicationName);\n"
    f'    setApplicationDisplayName(QStringLiteral("{DISPLAY_NAME}"));',
)
edit(
    "src/MainWindow/MainWindow.qml",
    "    id:         mainWindow\n",
    "    id:         mainWindow\n    title:      Qt.application.displayName\n",
)
edit(
    "src/QmlControls/QGroundControlQmlGlobal.cc",
    "    return QCoreApplication::applicationName();",
    "    return QGuiApplication::applicationDisplayName();",
)

for property_name in ("QT_TARGET_DESCRIPTION", "QT_TARGET_PRODUCT_NAME"):
    edit(
        "cmake/platform/Windows.cmake",
        f'{property_name} "${{CMAKE_PROJECT_NAME}}"',
        f'{property_name} "{DISPLAY_NAME}"',
    )
for value in ("FileDescription", "ProductName"):
    edit(
        "deploy/windows/QGroundControl.rc.in",
        f'VALUE "{value}", "@CMAKE_PROJECT_NAME@"',
        f'VALUE "{value}", "{DISPLAY_NAME}"',
    )

edit(
    "cmake/install/CPack/CreateCPackNSIS.cmake",
    'set(CPACK_NSIS_DISPLAY_NAME "${CMAKE_PROJECT_NAME}")',
    f'set(CPACK_NSIS_DISPLAY_NAME "{DISPLAY_NAME}")',
)
edit(
    "cmake/install/CPack/CreateCPackNSIS.cmake",
    'set(CPACK_NSIS_PACKAGE_NAME "${CMAKE_PROJECT_NAME} ${CMAKE_SYSTEM_PROCESSOR} ${CMAKE_PROJECT_VERSION}")',
    f'set(CPACK_NSIS_PACKAGE_NAME "{DISPLAY_NAME} ${{CMAKE_SYSTEM_PROCESSOR}} ${{CMAKE_PROJECT_VERSION}}")',
)
# Keep the same executable/upgrade registry identity, but label Windows shortcuts with the new name.
nsis = ROOT / "cmake/install/CPack/CreateCPackNSIS.cmake"
text = nsis.read_text(encoding="utf-8")
text = text.replace("@CMAKE_PROJECT_NAME@.lnk", f"{DISPLAY_NAME}.lnk")
text = text.replace("@CMAKE_PROJECT_NAME@ (GPU Safe Mode).lnk", f"{DISPLAY_NAME} (GPU Safe Mode).lnk")
nsis.write_text(text, encoding="utf-8")

for destination in ("resources/QGCLogoFull.svg", "resources/QGCLogoWhite.svg"):
    shutil.copyfile(ASSETS / "pilum.svg", ROOT / destination)
for destination in ("resources/icons/qgroundcontrol.ico", "deploy/windows/WindowsQGC.ico"):
    shutil.copyfile(ASSETS / "pilum.ico", ROOT / destination)
shutil.copyfile(ASSETS / "pilum.png", ROOT / "resources/icons/qgroundcontrol.png")
shutil.copyfile(ASSETS / "installheader.bmp", ROOT / "deploy/windows/installheader.bmp")

print(f"Applied branding: {DISPLAY_NAME}")
