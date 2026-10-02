#!/usr/bin/env python3
"""Extend the pinned dual-camera + UDP recipe with Multi CAM and session stats."""
from pathlib import Path
import json
import shutil
ROOT = Path.cwd()
ASSETS = Path(__file__).resolve().parent / 'multicam'
def read(path): return (ROOT / path).read_text(encoding='utf-8')
def write(path, text): (ROOT / path).write_text(text, encoding='utf-8')
def rep(text, old, new):
    if old not in text: raise RuntimeError(f'Multi CAM patch marker missing: {old[:100]}')
    return text.replace(old, new, 1)
def edit(path, old, new): write(path, rep(read(path), old, new))
def block(text, start, end, new):
    i = text.index(start); j = text.index(end, i)
    return text[:i] + new + text[j:]

# Keep the existing setting keys, so the user's camera URLs survive upgrades.
extra = ['multiCameraCount'] + [f'hikvisionCam{i}{mode}Url' for i in range(3,6) for mode in ('Main','Sub')]
p='src/Settings/VideoSettings.h'
edit(p,'    DEFINE_SETTINGFACT(hikvisionMainStream)', ''.join(f'    DEFINE_SETTINGFACT({n})\n' for n in extra)+'    DEFINE_SETTINGFACT(hikvisionMainStream)')
p='src/Settings/VideoSettings.cc'
s=read(p)
s=rep(s,'DECLARE_SETTINGSFACT(VideoSettings, hikvisionMainStream)', ''.join(f'DECLARE_SETTINGSFACT(VideoSettings, {n})\n' for n in extra)+'DECLARE_SETTINGSFACT(VideoSettings, hikvisionMainStream)')
# One-time removal of the old prefilled name, without touching custom names.
s=rep(s,'    // Set default value for videoSource', '''    {
        QSettings settings;
        settings.beginGroup(settingsGroup);
        if (!settings.value("multiCamNameMigrated", false).toBool()) {
            if (settings.value(hikvisionVehicleModelName).toString() == QString::fromUtf8("Змій"))
                hikvisionVehicleModel()->setRawValue(QString());
            settings.setValue("multiCamNameMigrated", true);
        }
        settings.endGroup();
    }
    // Set default value for videoSource''')
s=block(s,'    if (hikvisionDualEnabled()->rawValue().toBool()) {','    //-- First, check if it\'s autoconfigured', '''    if (hikvisionDualEnabled()->rawValue().toBool()) {
        const bool main = hikvisionMainStream()->rawValue().toBool();
        const QList<Fact *> urls = main
            ? QList<Fact *>{hikvisionCam1MainUrl(), hikvisionCam2MainUrl(), hikvisionCam3MainUrl(), hikvisionCam4MainUrl(), hikvisionCam5MainUrl()}
            : QList<Fact *>{hikvisionCam1SubUrl(), hikvisionCam2SubUrl(), hikvisionCam3SubUrl(), hikvisionCam4SubUrl(), hikvisionCam5SubUrl()};
        const int count = qBound(2, multiCameraCount()->rawValue().toInt(), 5);
        for (int i = 0; i < count; ++i) if (!urls[i]->rawValue().toString().trimmed().isEmpty()) return true;
        return false;
    }
''')
write(p,s)
p='src/Settings/Video.SettingsGroup.json'; d=json.loads(read(p)); facts=d['QGC.MetaData.Facts']
for f in facts:
    if f['name']=='hikvisionVehicleModel': f.update(default='',shortDesc='Optional vehicle profile name.',longDesc='Optional name for this Multi CAM profile.')
    if f['name']=='hikvisionDualEnabled': f.update(label='Enable Multi CAM',shortDesc='Enable Multi CAM with two to five independent cameras.',longDesc='One main video and up to four previews. All cameras share the MAIN/SUB selection.')
    if f['name']=='hikvisionMainStream': f.update(shortDesc='Use MAIN streams for all Multi CAM cameras.')
facts.append(dict(name='multiCameraCount',type='uint32',default=2,min=2,max=5,label='Camera count',shortDesc='Number of Multi CAM cameras (2–5).'))
for i in range(3,6):
    for mode in ('Main','Sub'):
        facts.append(dict(name=f'hikvisionCam{i}{mode}Url',type='string',default='',label=f'Camera {i} {mode.upper()} URL',shortDesc=f'Camera {i} {mode.upper()} RTSP URL.'))
write(p,json.dumps(d,ensure_ascii=False,indent=4)+'\n')
p='src/AppSettings/pages/Video.SettingsUI.json'; d=json.loads(read(p))
for g in d['groups']:
    if g.get('heading')=='Vehicle Model / Dual Hikvision':
        g.clear(); g.update(heading='Multi CAM',component='MultiCamSettings',keywords=['camera','multi cam','main','sub','vehicle model'])
    if g.get('heading') in ('Settings','Local Video Storage'): g['showWhen']='!sourceDisabled || dualHikvisionEnabled'
write(p,json.dumps(d,ensure_ascii=False,indent=4)+'\n')
shutil.copyfile(ASSETS/'MultiCamSettings.qml',ROOT/'src/AppSettings/MultiCamSettings.qml')
edit('src/AppSettings/CMakeLists.txt','              MockLink.qml','              MultiCamSettings.qml\n              MockLink.qml')

# Fixed sink slots are always instantiated, including inactive slots. Receivers
# retain their widgets; inactive slots have an empty URI and consume no stream.
p='src/VideoManager/VideoManager.h'; s=read(p)
s=rep(s,'class QQuickWindow;', 'class LinkSessionStats;\nclass Fact;\nclass QQuickWindow;')
s=rep(s,'    Q_MOC_INCLUDE("Vehicle.h")','''    Q_MOC_INCLUDE("Vehicle.h")
    Q_MOC_INCLUDE("Fact.h")
    Q_MOC_INCLUDE("LinkSessionStats.h")''')
s=rep(s,'    friend class VideoManagerInitTest;', '''    Q_PROPERTY(int multiCameraCount READ multiCameraCount NOTIFY multiCameraCountChanged)
    Q_PROPERTY(int multiCameraDecodingRevision READ multiCameraDecodingRevision NOTIFY multiCameraDecodingChanged)
    Q_PROPERTY(int hikvisionCameraOrderRevision READ hikvisionCameraOrderRevision NOTIFY hikvisionCameraOrderChanged)
    Q_PROPERTY(LinkSessionStats *linkSessionStats READ linkSessionStats CONSTANT)

    friend class VideoManagerInitTest;''')
s=rep(s,'    Q_INVOKABLE void swapHikvisionCameras();','''    Q_INVOKABLE void swapHikvisionCameras();
    Q_INVOKABLE void selectMultiCamera(int camera);
    Q_INVOKABLE void addMultiCamera();
    Q_INVOKABLE void removeMultiCamera(int camera);
    Q_INVOKABLE Fact *multiCameraUrlFact(int camera, bool main) const;
    Q_INVOKABLE int multiCameraForSlot(int slot) const;
    Q_INVOKABLE bool multiCameraDecoding(int slot) const;
    int multiCameraCount() const;
    int multiCameraDecodingRevision() const { return _multiCameraDecodingRevision; }
    int hikvisionCameraOrderRevision() const { return _hikvisionCameraOrderRevision; }
    LinkSessionStats *linkSessionStats() const { return _linkSessionStats; }
    void takeReceivedVideoBytes();''')
s=s.replace('return _cameraOrderSwapped ? 2 : 1;', 'return _primaryCamera;').replace('return _cameraOrderSwapped ? 1 : 2;', 'return multiCameraForSlot(2);')
s=rep(s,'    void secondaryDecodingChanged();','    void secondaryDecodingChanged();\n    void multiCameraCountChanged();\n    void multiCameraDecodingChanged();')
s=rep(s,'    bool _cameraOrderSwapped = false;', '''    int _primaryCamera = 1;
    int _cameraOrder[6] = {0, 1, 2, 3, 4, 5};
    bool _multiCameraUpdating = false;
    int _multiCameraDecodingRevision = 0;
    int _hikvisionCameraOrderRevision = 0;
    bool _slotDecoding[6] = {};
    quint64 _receivedVideoBytes = 0;
    LinkSessionStats *_linkSessionStats = nullptr;
    static int _slotForReceiver(const VideoReceiver *receiver);''')
write(p,s)
p='src/VideoManager/VideoManager.cc'; s=read(p)
s=rep(s,'#include "VideoManager.h"','#include "VideoManager.h"\n#include "LinkSessionStats.h"')
s=rep(s,'    qCDebug(VideoManagerLog) << this;','    _linkSessionStats = new LinkSessionStats(this);\n    qCDebug(VideoManagerLog) << this;')
s=block(s,'void VideoManager::swapHikvisionCameras()','void VideoManager::startVideoBackendInit()', '''int VideoManager::multiCameraCount() const {
    return qBound(2, _videoSettings->multiCameraCount()->rawValue().toInt(), 5);
}
Fact *VideoManager::multiCameraUrlFact(int camera, bool main) const {
    switch (camera) {
    case 1: return main ? _videoSettings->hikvisionCam1MainUrl() : _videoSettings->hikvisionCam1SubUrl();
    case 2: return main ? _videoSettings->hikvisionCam2MainUrl() : _videoSettings->hikvisionCam2SubUrl();
    case 3: return main ? _videoSettings->hikvisionCam3MainUrl() : _videoSettings->hikvisionCam3SubUrl();
    case 4: return main ? _videoSettings->hikvisionCam4MainUrl() : _videoSettings->hikvisionCam4SubUrl();
    case 5: return main ? _videoSettings->hikvisionCam5MainUrl() : _videoSettings->hikvisionCam5SubUrl();
    default: return nullptr;
    }
}
int VideoManager::_slotForReceiver(const VideoReceiver *receiver) {
    if (receiver->name() == QStringLiteral("videoContent")) return 1;
    for (int slot = 2; slot <= 5; ++slot)
        if (receiver->name() == QStringLiteral("camera%1Video").arg(slot)) return slot;
    return 0;
}
int VideoManager::multiCameraForSlot(int slot) const {
    if (slot < 1 || slot > multiCameraCount()) return 0;
    return _cameraOrder[slot];
}
bool VideoManager::multiCameraDecoding(int slot) const {
    return slot >= 1 && slot <= 5 && _slotDecoding[slot];
}
void VideoManager::selectMultiCamera(int camera) {
    if (!dualHikvisionEnabled() || camera < 1 || camera > multiCameraCount() || camera == _primaryCamera) return;
    for (int slot = 2; slot <= multiCameraCount(); ++slot) {
        if (_cameraOrder[slot] == camera) { std::swap(_cameraOrder[1], _cameraOrder[slot]); break; }
    }
    _primaryCamera = _cameraOrder[1];
    ++_hikvisionCameraOrderRevision;
    emit hikvisionCameraOrderChanged();
    _videoSourceChanged();
}
void VideoManager::swapHikvisionCameras() { selectMultiCamera(secondaryHikvisionCamera()); }
void VideoManager::addMultiCamera() {
    if (dualHikvisionEnabled() && multiCameraCount() < 5)
        _videoSettings->multiCameraCount()->setRawValue(multiCameraCount() + 1);
}
void VideoManager::removeMultiCamera(int camera) {
    if (!dualHikvisionEnabled() || camera < 3 || camera > multiCameraCount()) return;
    const int count = multiCameraCount();
    _multiCameraUpdating = true;
    // Shift later cameras together, preserving both URLs for each camera.
    for (int i = camera; i < count; ++i) {
        multiCameraUrlFact(i, true)->setRawValue(multiCameraUrlFact(i + 1, true)->rawValue());
        multiCameraUrlFact(i, false)->setRawValue(multiCameraUrlFact(i + 1, false)->rawValue());
    }
    multiCameraUrlFact(count, true)->setRawValue(QString());
    multiCameraUrlFact(count, false)->setRawValue(QString());
    if (_primaryCamera == camera) _primaryCamera = 1;
    else if (_primaryCamera > camera) --_primaryCamera;
    for (int slot = 1; slot <= 5; ++slot) _cameraOrder[slot] = slot;
    std::swap(_cameraOrder[1], _cameraOrder[_primaryCamera]);
    _multiCameraUpdating = false;
    _videoSettings->multiCameraCount()->setRawValue(count - 1);
}
QString VideoManager::_hikvisionUriForReceiver(const VideoReceiver *receiver) const {
    if (!receiver || !dualHikvisionEnabled()) return QString();
    const int camera = multiCameraForSlot(_slotForReceiver(receiver));
    Fact *url = multiCameraUrlFact(camera, hikvisionMainStream());
    return url ? url->rawValue().toString().trimmed() : QString();
}
void VideoManager::takeReceivedVideoBytes() {
    quint64 total = 0;
    for (const VideoReceiver *receiver : std::as_const(_videoReceivers)) total += receiver->receivedBytes();
    if (_linkSessionStats && total >= _receivedVideoBytes) _linkSessionStats->addVideoBytes(total - _receivedVideoBytes);
    _receivedVideoBytes = total;
}

''')
s=block(s,'    const auto hikvisionConfigChanged', '    (void) connect(_videoSettings->aspectRatio()', '''    const auto configChanged = [this](const QVariant &) { if (_multiCameraUpdating) return; emit hasVideoChanged(); emit isStreamSourceChanged(); _videoSourceChanged(); };
    for (int camera = 1; camera <= 5; ++camera) {
        connect(multiCameraUrlFact(camera, true), &Fact::rawValueChanged, this, configChanged);
        connect(multiCameraUrlFact(camera, false), &Fact::rawValueChanged, this, configChanged);
    }
    connect(_videoSettings->multiCameraCount(), &Fact::rawValueChanged, this, [this](const QVariant &) {
        if (_primaryCamera > multiCameraCount()) {
            _primaryCamera = 1;
            for (int slot = 1; slot <= 5; ++slot) _cameraOrder[slot] = slot;
        }
        ++_hikvisionCameraOrderRevision;
        emit multiCameraCountChanged(); emit hikvisionCameraOrderChanged(); emit hasVideoChanged();
        _videoSourceChanged();
    });
    connect(_videoSettings->hikvisionMainStream(), &Fact::rawValueChanged, this, [this](const QVariant &) {
        emit hikvisionStreamModeChanged(); emit hasVideoChanged(); _videoSourceChanged();
    });
    connect(_videoSettings->hikvisionDualEnabled(), &Fact::rawValueChanged, this, [this](const QVariant &) {
        _primaryCamera = 1;
        for (int slot = 1; slot <= 5; ++slot) _cameraOrder[slot] = slot;
        ++_hikvisionCameraOrderRevision;
        emit dualHikvisionChanged(); emit hikvisionCameraOrderChanged(); emit hasVideoChanged(); emit isStreamSourceChanged();
        _videoSourceChanged();
    });
''')
s=rep(s,'        "camera2Video"\n', '        "camera2Video",\n        "camera3Video",\n        "camera4Video",\n        "camera5Video"\n')
# Replace the full implementation without matching its own start as the end.
i=s.index('bool VideoManager::hasVideo() const'); j=s.index('\n}\n',i)+3
s=s[:i]+'''bool VideoManager::hasVideo() const {
    return _videoSettings->streamEnabled()->rawValue().toBool() && _videoSettings->streamConfigured();
}
'''+s[j:]
s=s.replace('receiver->name() == QStringLiteral("videoContent") || receiver->name() == QStringLiteral("camera2Video")', '_slotForReceiver(receiver) > 0')
s=rep(s,'    if (receiver->name() == QStringLiteral("camera2Video")) {\n        settingsChanged |= _updateVideoUri(receiver, QString());','    if (_slotForReceiver(receiver) >= 2) {\n        settingsChanged |= _updateVideoUri(receiver, QString());')
s=rep(s,'            emit secondaryDecodingChanged();\n        }\n    });', '''            emit secondaryDecodingChanged();
        }
        const int slot = _slotForReceiver(receiver);
        if (slot > 0) { _slotDecoding[slot] = active; ++_multiCameraDecodingRevision; emit multiCameraDecodingChanged(); }
    });''')
# Clear old frames immediately when switching URLs, so their badge cannot
# advertise the newly selected stream over a frame from the previous stream.
s=rep(s,'    if (dualHikvisionEnabled()) return false;\n    const QGCVideoStreamInfo *pInfo', '    if (dualHikvisionEnabled() || _slotForReceiver(receiver) >= 2) return false;\n    const QGCVideoStreamInfo *pInfo')
s=rep(s,'    receiver->setUri(uri);', '''    const int slot = _slotForReceiver(receiver);
    if (slot > 0) {
        _slotDecoding[slot] = false; ++_multiCameraDecodingRevision; emit multiCameraDecodingChanged();
        if (slot == 1) { _decoding = false; emit decodingChanged(); }
    }
    receiver->setUri(uri);''')
# For Multi CAM, preserve unchanged pipelines when selecting a preview.
s=rep(s, '    bool changed = false;\n    if (_activeVehicle)', '    bool changed = false;\n    QList<VideoReceiver *> changedReceivers;\n    if (_activeVehicle)')
s=s.replace('            changed |= _updateSettings(receiver);', '            if (_updateSettings(receiver)) { changed = true; changedReceivers.append(receiver); }')
s=rep(s, '        if (hasVideo()) {\n            _restartAllVideos();', '        if (hasVideo()) {\n            if (dualHikvisionEnabled()) {\n                for (VideoReceiver *receiver : std::as_const(changedReceivers)) _restartVideo(receiver);\n            } else {\n                _restartAllVideos();\n            }')
# Pending restart callbacks must not reopen streams after disabling video.
s=rep(s, '    if (receiver->uri().isEmpty()) {', '    if (!hasVideo() || receiver->uri().isEmpty()) {')
write(p,s)
# Removing a camera clears its URI before asynchronous stop runs. The original
# empty-URI guard otherwise leaves its pipeline running and using bandwidth.
edit('src/VideoManager/VideoReceiver/GStreamer/GstVideoReceiver.cc', '    if (_uri.isEmpty()) {\n        qCDebug(GstVideoReceiverLog) << "Stop called on empty URI (no-op)";', '    if (_uri.isEmpty() && !_pipeline) {\n        qCDebug(GstVideoReceiverLog) << "Stop called on empty URI with no pipeline (no-op)";')

# Fly view: four stable preview widgets (so late added cameras have sinks).
p='src/FlyView/FlyView.qml'; s=read(p)
s=block(s,'        HikvisionSecondVideo {','        FlyViewWidgetLayer {', '''        Column {
            id: multiCamPreviews
            anchors.left: parent.left
            anchors.leftMargin: _toolsMargin
            anchors.top: parent.top
            anchors.topMargin: toolbar.height + ScreenTools.defaultFontPixelHeight * 2 + _toolsMargin
            spacing: _toolsMargin
            width: Math.min(parent.width * 0.22, ScreenTools.defaultFontPixelWidth * 30)
            visible: QGroundControl.videoManager.dualHikvisionEnabled && QGroundControl.videoManager.hasVideo && !_mainWindowIsMap
            z: QGroundControl.zOrderWidgets + 10
            Repeater {
                model: 4
                MultiCamPreview {
                    required property int index
                    slot: index + 2
                    width: multiCamPreviews.width
                    height: Math.max(1, Math.min(width * 9 / 16,
                        (mapHolder.height - toolbar.height - ScreenTools.defaultFontPixelHeight * 2 - (_pipView.visible ? _pipView.height : 0) - _toolsMargin * 7) / Math.max(1, QGroundControl.videoManager.multiCameraCount - 1)))
                    visible: slot <= QGroundControl.videoManager.multiCameraCount
                }
            }
        }
        QGCButton {
            objectName: "multiCamStreamSwitch"
            anchors.right: parent.right
            anchors.rightMargin: _toolsMargin
            anchors.verticalCenter: parent.verticalCenter
            visible: QGroundControl.videoManager.dualHikvisionEnabled && QGroundControl.videoManager.hasVideo && !_mainWindowIsMap
            z: QGroundControl.zOrderWidgets + 20
            text: QGroundControl.videoManager.hikvisionMainStream ? qsTr("Switch to SUB") : qsTr("Switch to MAIN")
            onClicked: QGroundControl.videoManager.toggleHikvisionStream()
        }

''')
# Multi CAM starts with video filling the main view; map remains available in PiP.
s=rep(s,'            item1IsFullSettingsKey: "MainFlyWindowIsMap"','            item1IsFullSettingsKey: QGroundControl.videoManager.dualHikvisionEnabled ? "MultiCamMainFlyWindowIsMap" : "MainFlyWindowIsMap"')
s=rep(s, '            item1:                  _mapControl', '            item1IsFullDefault:     !QGroundControl.videoManager.dualHikvisionEnabled\n            item1:                  _mapControl')
write(p,s)
edit('src/QmlControls/PipView.qml', '    property bool   show:', '    property bool   item1IsFullDefault: true\n    onItem1IsFullSettingsKeyChanged: _initForItems()\n    property bool   show:')
edit('src/QmlControls/PipView.qml', 'loadBoolGlobalSetting(item1IsFullSettingsKey, true)', 'loadBoolGlobalSetting(item1IsFullSettingsKey, item1IsFullDefault)')
p='src/FlyView/FlyViewVideo.qml'; s=read(p)
s=block(s,'    Column {','    QGCLabel {\n        text: qsTr("Double-click', '''    Rectangle {
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.topMargin: QGroundControl.videoManager.fullScreen ? ScreenTools.defaultFontPixelHeight : ScreenTools.defaultFontPixelHeight * 4
        anchors.leftMargin: ScreenTools.defaultFontPixelWidth
        width: cameraLabel.implicitWidth + ScreenTools.defaultFontPixelWidth * 2
        height: cameraLabel.implicitHeight + ScreenTools.defaultFontPixelHeight * 0.5
        radius: 4
        color: "#b3000000"
        visible: QGroundControl.videoManager.dualHikvisionEnabled
        z: 100
        QGCLabel {
            id: cameraLabel
            anchors.centerIn: parent
            color: "white"
            font.bold: true
            text: qsTr("CAM %1 · %2").arg(QGroundControl.videoManager.primaryHikvisionCamera).arg(
                QGroundControl.videoManager.decoding ? (QGroundControl.videoManager.hikvisionMainStream ? "MAIN" : "SUB") : qsTr("Connecting…"))
        }
    }

''')
write(p,s)
shutil.copyfile(ASSETS/'MultiCamPreview.qml',ROOT/'src/FlyView/MultiCamPreview.qml')
edit('src/FlyView/CMakeLists.txt','        HikvisionSecondVideo.qml','        MultiCamPreview.qml')
(ROOT/'src/FlyView/HikvisionSecondVideo.qml').unlink()

# Battery's existing persistent display setting already defaults to percent.
edit('src/Toolbar/BatteryIndicator.qml','        onClicked:      mainWindow.showIndicatorDrawer(batteryPopup, control)', '''        acceptedButtons: Qt.LeftButton | Qt.RightButton
        onClicked: function(mouse) {
            if (mouse.button === Qt.RightButton) mainWindow.showIndicatorDrawer(batteryPopup, control)
            else {
                _indicatorDisplay.rawValue = _indicatorDisplay.rawValue === 1 ? 0 : 1
                control._recalcLowestBatteryId()
            }
        }
        onPressAndHold: mainWindow.showIndicatorDrawer(batteryPopup, control)''')
shutil.copyfile(ASSETS/'LinkSessionIndicator.qml',ROOT/'src/Toolbar/LinkSessionIndicator.qml')
edit('src/Toolbar/CMakeLists.txt','        JoystickIndicator.qml','        JoystickIndicator.qml\n        LinkSessionIndicator.qml')
edit('src/Toolbar/FlyViewToolBarIndicators.qml','        Repeater {\n            id:     toolIndicatorsRepeater', '''        LinkSessionIndicator {
            anchors.top: parent.top
            anchors.bottom: parent.bottom
        }

        Repeater {
            id:     toolIndicatorsRepeater''')
for filename in ('SessionState.h','LinkSessionStats.h','LinkSessionStats.cc'):
    shutil.copyfile(ASSETS/filename, ROOT/'src/VideoManager'/filename)
edit('src/VideoManager/CMakeLists.txt','        VideoManager.h','        VideoManager.h\n        LinkSessionStats.h\n        LinkSessionStats.cc\n        SessionState.h')
edit('src/Vehicle/Vehicle.h', 'signals:\n', 'signals:\n    void userDisconnectRequested();\n')
edit('src/Vehicle/Vehicle.cc', 'void Vehicle::closeVehicle()                                        { _vehicleLinkManager->closeVehicle(); }', 'void Vehicle::closeVehicle() { emit userDisconnectRequested(); _vehicleLinkManager->closeVehicle(); }')
# Raw link bytes include malformed/lost MAVLink frames, not just parsed messages.
edit('src/Comms/MAVLinkProtocol.h','    void messageReceived(', '    void receivedByteCount(LinkInterface *link, qint64 amount);\n    void messageReceived(')
edit('src/Comms/MAVLinkProtocol.cc','    for (uint8_t byte : data) {','    emit receivedByteCount(link, data.size());\n    for (uint8_t byte : data) {')
edit('src/Comms/LinkManager.h','signals:\n','signals:\n    void userDisconnectRequested(LinkInterface *link);\n')
p='src/Comms/LinkManager.cc'; s=read(p)
s=rep(s,'    link->disconnect();\n}\n\nvoid LinkManager::disconnectLinkConfiguration', '    emit userDisconnectRequested(link);\n    link->disconnect();\n}\n\nvoid LinkManager::disconnectLinkConfiguration')
s=rep(s,'    if (LinkInterface *const link = config->link()) {\n        link->disconnect();','    if (LinkInterface *const link = config->link()) {\n        emit userDisconnectRequested(link);\n        link->disconnect();')
s=rep(s,'void LinkManager::disconnectAll()\n{','void LinkManager::disconnectAll()\n{\n    emit userDisconnectRequested(nullptr);')
write(p,s)

# Counters are atomic and lifetime-safe across GStreamer worker threads.
p='src/VideoManager/VideoReceiver/VideoReceiver.h'
edit(p,'#include <atomic>', '#include <atomic>\n#include <memory>')
edit(p,'    bool isThermal() const', '''    std::shared_ptr<std::atomic<quint64>> trafficCounter() const { return _trafficCounter; }
    quint64 receivedBytes() const { return _trafficCounter->load(std::memory_order_relaxed); }

    bool isThermal() const''')
edit(p,'    Q_OBJECT','    std::shared_ptr<std::atomic<quint64>> _trafficCounter = std::make_shared<std::atomic<quint64>>(0);\n    Q_OBJECT')
p='src/VideoManager/VideoReceiver/GStreamer/GstSourceFactory.h'
edit(p,'#include <QtCore/QString>','#include <atomic>\n#include <memory>\n#include <QtCore/QString>')
edit(p,'    int latencyMs = 80;', '    std::shared_ptr<std::atomic<quint64>> receivedBytes;\n    int latencyMs = 80;')
edit('src/VideoManager/VideoReceiver/GStreamer/GstVideoReceiver.cc','        _source = GStreamer::SourceFactory::create(_uri, sourceConfig);','        sourceConfig.receivedBytes = trafficCounter();\n        _source = GStreamer::SourceFactory::create(_uri, sourceConfig);')
p='src/VideoManager/VideoReceiver/GStreamer/GstSourceFactory.cc'; s=read(p)
s=rep(s,'GstElement* create(const QString& uri, const Config& config)',(ASSETS/'TrafficProbe.inc').read_text()+'\nGstElement* create(const QString& uri, const Config& config)')
s=rep(s,'        GstElement* upstream = source;\n        source = nullptr;', '''        GstElement* upstream = source;
        if (config.receivedBytes) {
            if (isRtsp) {
                // udpsrc elements are created lazily when RTSP negotiation runs.
                g_signal_connect_data(source, "deep-element-added", G_CALLBACK(attachRtspTrafficCounter),
                    new TrafficCounter(config.receivedBytes),
                    [](gpointer p, GClosure *) { delete static_cast<TrafficCounter *>(p); }, GConnectFlags(0));
            } else {
                attachTrafficCounter(source, config.receivedBytes);
            }
        }
        source = nullptr;''')
write(p,s)
print('Multi CAM (2–5), session traffic/ping, and battery click toggle applied')
