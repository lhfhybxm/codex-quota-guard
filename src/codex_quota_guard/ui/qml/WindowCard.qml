import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: card
    property var windowData

    color: "#15181e"
    border.width: 1
    border.color: "#282d36"
    radius: 14
    implicitHeight: 350

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 0

        RowLayout {
            Layout.fillWidth: true
            spacing: 10

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 3

                Text {
                    text: card.windowData.title
                    color: "#f3f5f7"
                    font.family: "Segoe UI Variable Text"
                    font.pixelSize: 16
                    font.weight: Font.DemiBold
                }
                Text {
                    text: card.windowData.subtitle
                    color: "#7f8998"
                    font.family: "Segoe UI Variable Text"
                    font.pixelSize: 11
                }
            }

            Rectangle {
                implicitWidth: badgeText.implicitWidth + 18
                implicitHeight: 25
                radius: 12
                color: "#1b1e25"
                border.width: 1
                border.color: card.windowData.badgeColor

                Text {
                    id: badgeText
                    anchors.centerIn: parent
                    text: card.windowData.badge
                    color: card.windowData.badgeColor
                    font.family: "Segoe UI Variable Text"
                    font.pixelSize: 9
                    font.weight: Font.Bold
                    font.letterSpacing: 0.7
                }
            }
        }

        Item { Layout.preferredHeight: 22 }

        RowLayout {
            Layout.fillWidth: true
            spacing: 12

            Text {
                text: card.windowData.percentText
                color: "#f7f8fa"
                font.family: "Segoe UI Variable Display"
                font.pixelSize: 33
                font.weight: Font.DemiBold
            }

            Text {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignBottom
                Layout.bottomMargin: 5
                text: card.windowData.available ? "official used" : "official status"
                color: "#707988"
                font.family: "Segoe UI Variable Text"
                font.pixelSize: 11
            }

            Text {
                Layout.alignment: Qt.AlignBottom
                Layout.bottomMargin: 5
                text: card.windowData.resetText
                color: "#9aa3b2"
                font.family: "Segoe UI Variable Text"
                font.pixelSize: 11
            }
        }

        Meter {
            Layout.fillWidth: true
            Layout.topMargin: 8
            value: card.windowData.usedPercent
            accent: card.windowData.badge === "UNAVAILABLE" ? "#4b5361" : "#8b8cff"
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.topMargin: 18
            spacing: 9

            MetricBlock { label: card.windowData.totalLabel; value: card.windowData.total }
            MetricBlock { label: "USED"; value: card.windowData.used }
            MetricBlock { label: "REMAINING"; value: card.windowData.remaining; valueColor: "#9fa8ff" }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.topMargin: 15
            spacing: 8

            Text {
                Layout.fillWidth: true
                text: card.windowData.range
                color: "#c2c8d1"
                elide: Text.ElideRight
                font.family: "Segoe UI Variable Text"
                font.pixelSize: 11
                font.weight: Font.DemiBold
            }
            Text {
                text: card.windowData.confidence
                color: "#8b95a4"
                font.family: "Segoe UI Variable Text"
                font.pixelSize: 11
            }
        }

        Text {
            Layout.fillWidth: true
            Layout.topMargin: 9
            text: card.windowData.detail
            color: "#717b8a"
            wrapMode: Text.Wrap
            maximumLineCount: 2
            elide: Text.ElideRight
            font.family: "Segoe UI Variable Text"
            font.pixelSize: 10
            lineHeight: 1.2
        }

        Item { Layout.fillHeight: true }

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            Text {
                Layout.fillWidth: true
                text: card.windowData.sampleCount
                color: "#5f6876"
                font.family: "Segoe UI Variable Text"
                font.pixelSize: 10
            }
            Text {
                text: card.windowData.span
                color: "#5f6876"
                font.family: "Segoe UI Variable Text"
                font.pixelSize: 10
            }
        }
    }
}
