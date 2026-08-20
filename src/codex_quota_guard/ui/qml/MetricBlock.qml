import QtQuick
import QtQuick.Layouts

Rectangle {
    id: root
    property string label: ""
    property string value: "—"
    property color valueColor: "#f3f5f7"

    color: "#111419"
    border.width: 1
    border.color: "#252a33"
    radius: 10
    implicitHeight: 76
    Layout.fillWidth: true

    Column {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 7

        Text {
            text: root.label
            color: "#7f8998"
            font.family: "Segoe UI Variable Text"
            font.pixelSize: 11
        }

        Text {
            width: parent.width
            text: root.value
            color: root.valueColor
            elide: Text.ElideRight
            font.family: "Segoe UI Variable Text"
            font.pixelSize: 14
            font.weight: Font.DemiBold
        }
    }
}
