import QtQuick
import QtMultimedia
import QGroundControl
import QGroundControl.Controls

Item {
    id: root
    property int slot: 2
    property var manager: QGroundControl.videoManager
    property bool decoded: manager.multiCameraDecodingRevision >= 0 && manager.multiCameraDecoding(slot)
    property int camera: manager.hikvisionCameraOrderRevision >= 0 ? manager.multiCameraForSlot(slot) : 0
    clip: true
    Rectangle { anchors.fill: parent; color: "black" }
    Image {
        anchors.fill: parent
        source: "/res/NoVideoBackground.jpg"
        fillMode: Image.PreserveAspectCrop
        visible: !root.decoded
    }
    VideoOutput {
        objectName: "camera" + root.slot + "Video"
        anchors.fill: parent
        visible: root.decoded
        fillMode: VideoOutput.PreserveAspectFit
    }
    Rectangle {
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.margins: ScreenTools.defaultFontPixelWidth * 0.5
        width: badge.implicitWidth + ScreenTools.defaultFontPixelWidth
        height: badge.implicitHeight + ScreenTools.defaultFontPixelHeight * 0.3
        color: "#b3000000"
        radius: 3
        QGCLabel {
            id: badge
            anchors.centerIn: parent
            color: "white"
            font.bold: true
            text: qsTr("CAM %1 · %2").arg(root.camera).arg(root.decoded ? (manager.hikvisionMainStream ? "MAIN" : "SUB") : qsTr("Connecting…"))
        }
    }
    Rectangle { anchors.fill: parent; color: "transparent"; border.color: "#99ffffff"; border.width: 1 }
    MouseArea {
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        onClicked: manager.selectMultiCamera(root.camera)
    }
}
