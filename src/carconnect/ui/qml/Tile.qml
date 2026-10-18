import QtQuick
import QtQuick.Layouts

Rectangle {
    property string label: ""
    property string value: "—"
    property string unit: ""

    Layout.fillWidth: true
    implicitHeight: 90
    radius: 12
    color: "#161b24"

    Column {
        anchors.centerIn: parent
        spacing: 4

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: label
            color: "#8a93a6"
            font.pixelSize: 13
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: value + " " + unit
            color: "white"
            font.pixelSize: 24
            font.bold: true
        }
    }
}
