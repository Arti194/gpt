import QtQuick
import QtQuick.Layouts
import QGroundControl
import QGroundControl.Controls
import QGroundControl.FactControls

SettingsGroupLayout {
    heading: qsTr("Multi CAM")
    property var video: QGroundControl.videoManager
    property var settings: QGroundControl.settingsManager.videoSettings
    FactCheckBoxSlider {
        Layout.fillWidth: true
        fact: settings.hikvisionDualEnabled
        text: qsTr("Enable Multi CAM")
    }
    LabelledFactTextField {
        Layout.fillWidth: true
        label: qsTr("Vehicle Model")
        fact: settings.hikvisionVehicleModel
        visible: video.dualHikvisionEnabled
    }
    Repeater {
        model: 5
        ColumnLayout {
            required property int index
            Layout.fillWidth: true
            visible: video.dualHikvisionEnabled && index < video.multiCameraCount
            RowLayout {
                Layout.fillWidth: true
                QGCLabel { text: qsTr("Camera %1").arg(index + 1); Layout.fillWidth: true; font.bold: true }
                QGCButton {
                    text: qsTr("Remove")
                    visible: index >= 2
                    onClicked: video.removeMultiCamera(index + 1)
                }
            }
            LabelledFactTextField {
                Layout.fillWidth: true
                textFieldPreferredWidth: ScreenTools.defaultFontPixelWidth * 40
                label: qsTr("MAIN URL")
                fact: video.multiCameraUrlFact(index + 1, true)
            }
            LabelledFactTextField {
                Layout.fillWidth: true
                textFieldPreferredWidth: ScreenTools.defaultFontPixelWidth * 40
                label: qsTr("SUB URL")
                fact: video.multiCameraUrlFact(index + 1, false)
            }
        }
    }
    QGCButton {
        text: "+"
        visible: video.dualHikvisionEnabled && video.multiCameraCount < 5
        onClicked: video.addMultiCamera()
    }
    FactCheckBoxSlider {
        Layout.fillWidth: true
        fact: settings.hikvisionMainStream
        text: qsTr("Use MAIN Stream")
        visible: video.dualHikvisionEnabled
    }
}
