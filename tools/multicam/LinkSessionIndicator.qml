import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QGroundControl
import QGroundControl.Controls
Item {
    property var stats: QGroundControl.videoManager.linkSessionStats
    visible: QGroundControl.multiVehicleManager.activeVehicle !== null
    width: values.implicitWidth
    ColumnLayout {
        id: values
        anchors.verticalCenter: parent.verticalCenter
        spacing: 0
        QGCLabel { text: stats.connected && stats.pingMs >= 0 ? qsTr("Ping: %1 ms").arg(stats.pingMs) : qsTr("Ping: —") }
        QGCLabel { text: qsTr("RX: %1 MB").arg(stats.trafficMB.toFixed(1)) }
    }
    MouseArea {
        id: hover
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.NoButton
    }
    ToolTip.visible: hover.containsMouse
    ToolTip.text: qsTr("Received QGC telemetry + video (1 MB = 1,000,000 bytes). Excludes network overhead and other Starlink traffic. Brief outages up to 60 seconds keep the counter.")
}
