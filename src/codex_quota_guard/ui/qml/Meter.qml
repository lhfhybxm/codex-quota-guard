import QtQuick

Item {
    id: root
    property real value: 0
    property color accent: "#8b8cff"
    implicitHeight: 9

    Rectangle {
        anchors.fill: parent
        radius: height / 2
        color: "#252a33"
    }

    Rectangle {
        width: Math.max(0, Math.min(parent.width, parent.width * root.value / 100))
        height: parent.height
        radius: height / 2
        color: root.accent

        Behavior on width {
            NumberAnimation { duration: 420; easing.type: Easing.OutCubic }
        }
    }
}
