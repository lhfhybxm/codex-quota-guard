import QtQuick
import QtQuick.Controls

Button {
    id: control
    property string glyph: ""
    property string label: ""
    property bool selected: false
    property bool compact: false

    implicitHeight: 46
    hoverEnabled: true
    Accessible.name: label
    ToolTip.visible: compact && hovered
    ToolTip.text: label
    ToolTip.delay: 450

    background: Rectangle {
        radius: 9
        color: control.selected ? "#1d2028" : (control.hovered ? "#171a20" : "transparent")
        border.width: control.selected ? 1 : 0
        border.color: "#2c303a"
    }

    contentItem: Row {
        anchors.left: parent.left
        anchors.leftMargin: control.compact ? 0 : 13
        anchors.verticalCenter: parent.verticalCenter
        width: control.compact ? parent.width : implicitWidth
        spacing: 12

        Rectangle {
            width: 24
            height: 24
            radius: 7
            color: control.selected ? "#8b8cff" : "#20242c"
            anchors.verticalCenter: parent.verticalCenter

            Text {
                anchors.centerIn: parent
                text: control.glyph
                color: control.selected ? "#ffffff" : "#a5adba"
                font.family: "Segoe UI Variable Text"
                font.pixelSize: 12
                font.weight: Font.DemiBold
            }
        }

        Text {
            visible: !control.compact
            anchors.verticalCenter: parent.verticalCenter
            text: control.label
            color: control.selected ? "#f5f6f8" : "#9aa3b2"
            font.family: "Segoe UI Variable Text"
            font.pixelSize: 13
            font.weight: control.selected ? Font.DemiBold : Font.Normal
        }
    }
}
