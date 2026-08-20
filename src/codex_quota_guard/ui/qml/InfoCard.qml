import QtQuick
import QtQuick.Layouts

Rectangle {
    id: root
    property string kicker: ""
    property string title: ""
    property string body: ""
    property color accent: "#8b8cff"

    color: "#15181e"
    border.width: 1
    border.color: "#282d36"
    radius: 14
    implicitHeight: 152

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 7

        RowLayout {
            spacing: 8
            Rectangle { width: 7; height: 7; radius: 4; color: root.accent }
            Text {
                text: root.kicker
                color: root.accent
                font.family: "Segoe UI Variable Text"
                font.pixelSize: 9
                font.weight: Font.Bold
                font.letterSpacing: 0.7
            }
        }
        Text {
            Layout.fillWidth: true
            text: root.title
            color: "#eef1f4"
            font.family: "Segoe UI Variable Text"
            font.pixelSize: 15
            font.weight: Font.DemiBold
        }
        Text {
            Layout.fillWidth: true
            Layout.fillHeight: true
            text: root.body
            color: "#8b95a4"
            wrapMode: Text.Wrap
            font.family: "Segoe UI Variable Text"
            font.pixelSize: 11
            lineHeight: 1.25
        }
    }
}
