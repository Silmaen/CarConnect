import QtQuick

Item {
    id: root

    property real value: 0
    property real minValue: 0
    property real maxValue: 100
    property string unit: ""
    property string label: ""
    property color accent: "#00c2ff"

    implicitWidth: 260
    implicitHeight: 260

    onValueChanged: canvas.requestPaint()
    onAccentChanged: canvas.requestPaint()

    Canvas {
        id: canvas
        anchors.fill: parent
        antialiasing: true

        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            var cx = width / 2
            var cy = height / 2
            var r = Math.min(width, height) / 2 - 16
            var start = Math.PI * 0.75
            var span = Math.PI * 1.5
            var frac = Math.max(0, Math.min(1, (root.value - root.minValue) / (root.maxValue - root.minValue)))

            ctx.lineWidth = 14
            ctx.lineCap = "round"
            ctx.strokeStyle = "#252b38"
            ctx.beginPath()
            ctx.arc(cx, cy, r, start, start + span)
            ctx.stroke()

            if (frac > 0) {
                ctx.strokeStyle = root.accent
                ctx.beginPath()
                ctx.arc(cx, cy, r, start, start + span * frac)
                ctx.stroke()
            }
        }
    }

    Column {
        anchors.centerIn: parent
        spacing: 2

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: Math.round(root.value)
            color: "white"
            font.pixelSize: root.height * 0.2
            font.bold: true
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.unit
            color: "#8a93a6"
            font.pixelSize: root.height * 0.07
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.label
            color: root.accent
            font.pixelSize: root.height * 0.065
            font.capitalization: Font.AllUppercase
        }
    }
}
