import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: appWindow
    width: 1180
    height: 760
    minimumWidth: 900
    minimumHeight: 620
    visible: true
    color: "#0c0e12"
    title: "Codex Quota Guard"

    property int currentPage: 0
    property bool compactSidebar: width < 1040
    property string pageTitle: currentPage === 0 ? "Quota overview" : (currentPage === 1 ? "Calibration history" : "Provider & privacy")
    property string pageSubtitle: currentPage === 0
        ? "Official percentages with locally calibrated absolute estimates"
        : (currentPage === 1 ? "Reset epochs and their confidence trail" : "Every operation the monitor may perform")

    onClosing: function(close) {
        close.accepted = false
        backend.requestClose()
    }

    Rectangle {
        anchors.fill: parent
        color: "#0c0e12"

        RowLayout {
            anchors.fill: parent
            spacing: 0

            Rectangle {
                id: sidebar
                Layout.fillHeight: true
                Layout.preferredWidth: appWindow.compactSidebar ? 78 : 218
                color: "#0e1014"
                border.width: 0

                Behavior on Layout.preferredWidth {
                    NumberAnimation { duration: 160; easing.type: Easing.OutCubic }
                }

                Rectangle {
                    anchors.right: parent.right
                    width: 1
                    height: parent.height
                    color: "#20242b"
                }

                ColumnLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 13
                    anchors.rightMargin: 13
                    anchors.topMargin: 17
                    anchors.bottomMargin: 15
                    spacing: 8

                    RowLayout {
                        Layout.fillWidth: true
                        Layout.leftMargin: appWindow.compactSidebar ? 3 : 6
                        Layout.rightMargin: 3
                        Layout.bottomMargin: 20
                        spacing: 11

                        Item {
                            width: 34
                            height: 34

                            Rectangle {
                                anchors.fill: parent
                                radius: 10
                                color: "#171a20"
                                border.width: 1
                                border.color: "#303541"
                            }
                            Rectangle {
                                anchors.centerIn: parent
                                width: 18
                                height: 18
                                radius: 9
                                color: "transparent"
                                border.width: 3
                                border.color: "#8b8cff"
                            }
                            Rectangle {
                                x: 23
                                y: 22
                                width: 6
                                height: 6
                                radius: 3
                                color: "#51d88a"
                            }
                        }

                        Column {
                            Layout.fillWidth: true
                            visible: !appWindow.compactSidebar
                            spacing: 1
                            Text {
                                text: "Quota Guard"
                                color: "#f2f4f7"
                                font.family: "Segoe UI Variable Text"
                                font.pixelSize: 14
                                font.weight: Font.DemiBold
                            }
                            Text {
                                text: "LOCAL MONITOR"
                                color: "#606978"
                                font.family: "Segoe UI Variable Text"
                                font.pixelSize: 8
                                font.weight: Font.Bold
                                font.letterSpacing: 0.9
                            }
                        }
                    }

                    NavButton {
                        Layout.fillWidth: true
                        glyph: "Q"
                        label: "Overview"
                        compact: appWindow.compactSidebar
                        selected: appWindow.currentPage === 0
                        onClicked: appWindow.currentPage = 0
                    }
                    NavButton {
                        Layout.fillWidth: true
                        glyph: "H"
                        label: "History"
                        compact: appWindow.compactSidebar
                        selected: appWindow.currentPage === 1
                        onClicked: appWindow.currentPage = 1
                    }
                    NavButton {
                        Layout.fillWidth: true
                        glyph: "S"
                        label: "Provider & privacy"
                        compact: appWindow.compactSidebar
                        selected: appWindow.currentPage === 2
                        onClicked: appWindow.currentPage = 2
                    }

                    Item { Layout.fillHeight: true }

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: appWindow.compactSidebar ? 48 : 72
                        radius: 10
                        color: "#12151a"
                        border.width: 1
                        border.color: "#242932"

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 11
                            spacing: 10

                            Rectangle {
                                width: 9
                                height: 9
                                radius: 5
                                color: backend.freshnessColor
                            }
                            Column {
                                Layout.fillWidth: true
                                visible: !appWindow.compactSidebar
                                spacing: 3
                                Text {
                                    text: backend.freshness
                                    color: "#d9dde3"
                                    font.family: "Segoe UI Variable Text"
                                    font.pixelSize: 11
                                    font.weight: Font.DemiBold
                                }
                                Text {
                                    width: parent.width
                                    text: backend.lastUpdated
                                    color: "#67717f"
                                    elide: Text.ElideRight
                                    font.family: "Segoe UI Variable Text"
                                    font.pixelSize: 9
                                }
                            }
                        }
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 0

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 80
                    color: "#101217"

                    Rectangle {
                        anchors.bottom: parent.bottom
                        width: parent.width
                        height: 1
                        color: "#22262e"
                    }

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 28
                        anchors.rightMargin: 26
                        spacing: 12

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 3
                            Text {
                                text: appWindow.pageTitle
                                color: "#f4f6f8"
                                font.family: "Segoe UI Variable Display"
                                font.pixelSize: 20
                                font.weight: Font.DemiBold
                            }
                            Text {
                                visible: appWindow.width >= 1030
                                text: appWindow.pageSubtitle
                                color: "#737d8c"
                                font.family: "Segoe UI Variable Text"
                                font.pixelSize: 10
                            }
                        }

                        Rectangle {
                            implicitWidth: liveText.implicitWidth + 28
                            implicitHeight: 30
                            radius: 15
                            color: "#15191e"
                            border.width: 1
                            border.color: "#2b3039"
                            Row {
                                anchors.centerIn: parent
                                spacing: 8
                                Rectangle {
                                    anchors.verticalCenter: parent.verticalCenter
                                    width: 7
                                    height: 7
                                    radius: 4
                                    color: backend.freshnessColor
                                }
                                Text {
                                    id: liveText
                                    text: backend.freshness
                                    color: "#c9ced6"
                                    font.family: "Segoe UI Variable Text"
                                    font.pixelSize: 10
                                    font.weight: Font.DemiBold
                                }
                            }
                        }

                        Button {
                            id: refreshButton
                            implicitWidth: 104
                            implicitHeight: 38
                            hoverEnabled: true
                            Accessible.name: "Refresh read-only quota data"
                            onClicked: backend.requestRefresh()
                            background: Rectangle {
                                radius: 9
                                color: refreshButton.down ? "#7476dc" : (refreshButton.hovered ? "#9899ff" : "#8587ed")
                            }
                            contentItem: Text {
                                text: "↻  Refresh"
                                color: "#ffffff"
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                                font.family: "Segoe UI Variable Text"
                                font.pixelSize: 11
                                font.weight: Font.DemiBold
                            }
                        }
                    }
                }

                StackLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    currentIndex: appWindow.currentPage

                    // Overview
                    ScrollView {
                        id: overviewScroll
                        clip: true
                        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                        contentWidth: availableWidth

                        ColumnLayout {
                            width: overviewScroll.availableWidth
                            spacing: 16

                            Item { Layout.preferredHeight: 10 }

                            Rectangle {
                                Layout.fillWidth: true
                                Layout.leftMargin: 26
                                Layout.rightMargin: 26
                                Layout.preferredHeight: visible ? 52 : 0
                                visible: backend.quotaAlert.length > 0
                                radius: 12
                                color: "#251b14"
                                border.width: 1
                                border.color: "#594125"
                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 16
                                    anchors.rightMargin: 16
                                    spacing: 11
                                    Rectangle { width: 8; height: 8; radius: 4; color: "#f5b84b" }
                                    Text {
                                        Layout.fillWidth: true
                                        text: backend.quotaAlert
                                        color: "#e2c38a"
                                        elide: Text.ElideRight
                                        font.family: "Segoe UI Variable Text"
                                        font.pixelSize: 10
                                        font.weight: Font.DemiBold
                                    }
                                }
                            }

                            GridLayout {
                                Layout.fillWidth: true
                                Layout.leftMargin: 26
                                Layout.rightMargin: 26
                                columns: appWindow.width >= 1110 ? 2 : 1
                                columnSpacing: 14
                                rowSpacing: 14

                                WindowCard {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 350
                                    windowData: backend.fiveHour
                                }
                                WindowCard {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 350
                                    windowData: backend.weekly
                                }
                            }

                            GridLayout {
                                Layout.fillWidth: true
                                Layout.leftMargin: 26
                                Layout.rightMargin: 26
                                columns: appWindow.width >= 1080 ? 2 : 1
                                columnSpacing: 14
                                rowSpacing: 14

                                Rectangle {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 205
                                    color: "#15181e"
                                    border.width: 1
                                    border.color: "#282d36"
                                    radius: 14

                                    ColumnLayout {
                                        anchors.fill: parent
                                        anchors.margins: 18
                                        spacing: 8

                                        RowLayout {
                                            Layout.fillWidth: true
                                            Text {
                                                Layout.fillWidth: true
                                                text: "Calibration signal"
                                                color: "#eef1f4"
                                                font.family: "Segoe UI Variable Text"
                                                font.pixelSize: 14
                                                font.weight: Font.DemiBold
                                            }
                                            Text {
                                                text: "THEIL–SEN"
                                                color: "#7f89f2"
                                                font.family: "Segoe UI Variable Text"
                                                font.pixelSize: 8
                                                font.weight: Font.Bold
                                                font.letterSpacing: 0.8
                                            }
                                        }

                                        Item {
                                            Layout.fillWidth: true
                                            Layout.fillHeight: true

                                            Canvas {
                                                anchors.fill: parent
                                                onPaint: {
                                                    const ctx = getContext("2d")
                                                    ctx.reset()
                                                    ctx.strokeStyle = "#252a33"
                                                    ctx.lineWidth = 1
                                                    for (let x = 0; x <= width; x += width / 6) {
                                                        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, height); ctx.stroke()
                                                    }
                                                    for (let y = 0; y <= height; y += height / 4) {
                                                        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(width, y); ctx.stroke()
                                                    }
                                                    ctx.strokeStyle = "#6266a6"
                                                    ctx.lineWidth = 2
                                                    ctx.setLineDash([5, 5])
                                                    ctx.beginPath(); ctx.moveTo(8, height - 18); ctx.lineTo(width - 8, 18); ctx.stroke()
                                                }
                                            }
                                            Column {
                                                anchors.centerIn: parent
                                                spacing: 6
                                                Text {
                                                    anchors.horizontalCenter: parent.horizontalCenter
                                                    text: "Learning from normal Codex usage"
                                                    color: "#cbd0d8"
                                                    font.family: "Segoe UI Variable Text"
                                                    font.pixelSize: 11
                                                    font.weight: Font.DemiBold
                                                }
                                                Text {
                                                    anchors.horizontalCenter: parent.horizontalCenter
                                                    text: "No prompts, turns, or responses are generated"
                                                    color: "#6e7785"
                                                    font.family: "Segoe UI Variable Text"
                                                    font.pixelSize: 9
                                                }
                                            }
                                        }
                                    }
                                }

                                Rectangle {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 205
                                    color: "#15181e"
                                    border.width: 1
                                    border.color: "#282d36"
                                    radius: 14

                                    ColumnLayout {
                                        anchors.fill: parent
                                        anchors.margins: 18
                                        spacing: 10

                                        Text {
                                            text: "Collection quality"
                                            color: "#eef1f4"
                                            font.family: "Segoe UI Variable Text"
                                            font.pixelSize: 14
                                            font.weight: Font.DemiBold
                                        }
                                        Text {
                                            Layout.fillWidth: true
                                            text: backend.usageSummary
                                            color: "#939cab"
                                            wrapMode: Text.Wrap
                                            font.family: "Segoe UI Variable Text"
                                            font.pixelSize: 11
                                        }
                                        Rectangle { Layout.fillWidth: true; height: 1; color: "#252a33" }
                                        RowLayout {
                                            Layout.fillWidth: true
                                            Text { text: "Provider"; color: "#707a89"; font.family: "Segoe UI Variable Text"; font.pixelSize: 10 }
                                            Text { Layout.fillWidth: true; text: backend.provider; horizontalAlignment: Text.AlignRight; color: "#d2d6dd"; font.family: "Segoe UI Variable Text"; font.pixelSize: 10; elide: Text.ElideLeft }
                                        }
                                        RowLayout {
                                            Layout.fillWidth: true
                                            Text { text: "Plan"; color: "#707a89"; font.family: "Segoe UI Variable Text"; font.pixelSize: 10 }
                                            Text { Layout.fillWidth: true; text: backend.plan; horizontalAlignment: Text.AlignRight; color: "#d2d6dd"; font.family: "Segoe UI Variable Text"; font.pixelSize: 10 }
                                        }
                                        Text {
                                            Layout.fillWidth: true
                                            visible: backend.error.length > 0
                                            text: backend.error
                                            color: "#ff8a90"
                                            elide: Text.ElideRight
                                            font.family: "Segoe UI Variable Text"
                                            font.pixelSize: 9
                                        }
                                        Item { Layout.fillHeight: true }
                                    }
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                Layout.leftMargin: 26
                                Layout.rightMargin: 26
                                Layout.bottomMargin: 22
                                implicitHeight: 54
                                radius: 12
                                color: "#111820"
                                border.width: 1
                                border.color: "#243142"

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 16
                                    anchors.rightMargin: 16
                                    spacing: 12
                                    Rectangle { width: 8; height: 8; radius: 4; color: "#51d88a" }
                                    Text {
                                        Layout.fillWidth: true
                                        text: "Zero-inference guarantee  ·  Only initialize, account/rateLimits/read, and account/usage/read are allowed"
                                        color: "#aeb7c3"
                                        elide: Text.ElideRight
                                        font.family: "Segoe UI Variable Text"
                                        font.pixelSize: 10
                                    }
                                    Text {
                                        text: "LOCAL ONLY"
                                        color: "#51d88a"
                                        font.family: "Segoe UI Variable Text"
                                        font.pixelSize: 8
                                        font.weight: Font.Bold
                                        font.letterSpacing: 0.8
                                    }
                                }
                            }
                        }
                    }

                    // History
                    Item {
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 26
                            spacing: 14

                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 72
                                color: "#15181e"
                                border.width: 1
                                border.color: "#282d36"
                                radius: 13
                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 18
                                    anchors.rightMargin: 18
                                    spacing: 12
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 3
                                        Text { text: "Reset-aware calibration epochs"; color: "#eef1f4"; font.family: "Segoe UI Variable Text"; font.pixelSize: 14; font.weight: Font.DemiBold }
                                        Text { text: "5-hour and weekly windows are never mixed; each reset starts a new fit."; color: "#778190"; font.family: "Segoe UI Variable Text"; font.pixelSize: 10 }
                                    }
                                    Rectangle {
                                        implicitWidth: historyCount.implicitWidth + 22
                                        implicitHeight: 28
                                        radius: 14
                                        color: "#1b1e25"
                                        border.width: 1
                                        border.color: "#2e333d"
                                        Text { id: historyCount; anchors.centerIn: parent; text: historyView.count + " epochs"; color: "#aeb5c0"; font.family: "Segoe UI Variable Text"; font.pixelSize: 10 }
                                    }
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                color: "#15181e"
                                border.width: 1
                                border.color: "#282d36"
                                radius: 13
                                clip: true

                                ColumnLayout {
                                    anchors.fill: parent
                                    spacing: 0

                                    Rectangle {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 46
                                        color: "#181b21"
                                        RowLayout {
                                            anchors.fill: parent
                                            anchors.leftMargin: 17
                                            anchors.rightMargin: 17
                                            spacing: 14
                                            Text { Layout.preferredWidth: 80; text: "WINDOW"; color: "#687280"; font.family: "Segoe UI Variable Text"; font.pixelSize: 9; font.weight: Font.Bold }
                                            Text { Layout.fillWidth: true; text: "PERIOD"; color: "#687280"; font.family: "Segoe UI Variable Text"; font.pixelSize: 9; font.weight: Font.Bold }
                                            Text { Layout.preferredWidth: 115; text: "OBSERVED"; color: "#687280"; font.family: "Segoe UI Variable Text"; font.pixelSize: 9; font.weight: Font.Bold }
                                            Text { Layout.preferredWidth: 150; text: "ESTIMATE"; color: "#687280"; font.family: "Segoe UI Variable Text"; font.pixelSize: 9; font.weight: Font.Bold }
                                            Text { Layout.preferredWidth: 75; text: "CONF."; color: "#687280"; font.family: "Segoe UI Variable Text"; font.pixelSize: 9; font.weight: Font.Bold }
                                            Text { Layout.preferredWidth: 70; text: "STATUS"; color: "#687280"; font.family: "Segoe UI Variable Text"; font.pixelSize: 9; font.weight: Font.Bold }
                                        }
                                    }

                                    ListView {
                                        id: historyView
                                        Layout.fillWidth: true
                                        Layout.fillHeight: true
                                        clip: true
                                        model: historyModel
                                        delegate: Rectangle {
                                            required property string windowName
                                            required property string period
                                            required property string observed
                                            required property string estimate
                                            required property string confidence
                                            required property string status
                                            width: historyView.width
                                            height: 54
                                            color: index % 2 === 0 ? "#15181e" : "#14171c"
                                            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: "#22262e" }
                                            RowLayout {
                                                anchors.fill: parent
                                                anchors.leftMargin: 17
                                                anchors.rightMargin: 17
                                                spacing: 14
                                                Text { Layout.preferredWidth: 80; text: windowName; color: "#d7dbe1"; font.family: "Segoe UI Variable Text"; font.pixelSize: 10; font.weight: Font.DemiBold }
                                                Text { Layout.fillWidth: true; text: period; color: "#8993a1"; font.family: "Segoe UI Variable Text"; font.pixelSize: 10; elide: Text.ElideRight }
                                                Text { Layout.preferredWidth: 115; text: observed; color: "#a6aebb"; font.family: "Segoe UI Variable Text"; font.pixelSize: 10 }
                                                Text { Layout.preferredWidth: 150; text: estimate; color: "#d7dbe1"; font.family: "Segoe UI Variable Text"; font.pixelSize: 10; elide: Text.ElideRight }
                                                Text { Layout.preferredWidth: 75; text: confidence; color: "#a6aebb"; font.family: "Segoe UI Variable Text"; font.pixelSize: 10 }
                                                Text { Layout.preferredWidth: 70; text: status; color: status === "Active" ? "#51d88a" : "#7f8998"; font.family: "Segoe UI Variable Text"; font.pixelSize: 10; font.weight: Font.DemiBold }
                                            }
                                        }

                                        Text {
                                            anchors.centerIn: parent
                                            visible: historyView.count === 0
                                            text: "No calibration epochs yet\nThe first successful sample will appear here."
                                            horizontalAlignment: Text.AlignHCenter
                                            color: "#68717f"
                                            font.family: "Segoe UI Variable Text"
                                            font.pixelSize: 11
                                            lineHeight: 1.5
                                        }
                                    }
                                }
                            }
                        }
                    }

                    // Provider and privacy
                    ScrollView {
                        id: privacyScroll
                        clip: true
                        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                        contentWidth: availableWidth

                        ColumnLayout {
                            width: privacyScroll.availableWidth
                            spacing: 14

                            Item { Layout.preferredHeight: 10 }

                            GridLayout {
                                Layout.fillWidth: true
                                Layout.leftMargin: 26
                                Layout.rightMargin: 26
                                columns: appWindow.width >= 1080 ? 2 : 1
                                columnSpacing: 14
                                rowSpacing: 14

                                InfoCard {
                                    Layout.fillWidth: true
                                    kicker: "PROVIDER"
                                    title: backend.provider
                                    body: "Reads the local Codex App Server over JSONL stdio. No browser cookies, API keys, or account credentials are stored by this project."
                                    accent: "#8b8cff"
                                }
                                InfoCard {
                                    Layout.fillWidth: true
                                    kicker: "ALLOWLIST"
                                    title: "Three read-only operations"
                                    body: "initialize · account/rateLimits/read · account/usage/read. Incoming rate-limit update notifications may wake the collector."
                                    accent: "#51d88a"
                                }
                                InfoCard {
                                    Layout.fillWidth: true
                                    kicker: "HARD BLOCK"
                                    title: "Inference operations cannot pass"
                                    body: "turn/start, thread/start, response/chat, credit consumption, reset consumption, account writes, and unknown RPC methods are rejected before transport."
                                    accent: "#ff6b72"
                                }
                                InfoCard {
                                    Layout.fillWidth: true
                                    kicker: "LOCAL DATA"
                                    title: "SQLite history with explicit units"
                                    body: "Percentages, timestamps, token counters, estimates, and health state stay on this PC. Tokens are never relabeled as credits or dollars."
                                    accent: "#f5b84b"
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                Layout.leftMargin: 26
                                Layout.rightMargin: 26
                                Layout.bottomMargin: 22
                                implicitHeight: 116
                                color: "#15181e"
                                border.width: 1
                                border.color: "#282d36"
                                radius: 14

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: 18
                                    spacing: 16
                                    Rectangle {
                                        width: 42
                                        height: 42
                                        radius: 12
                                        color: backend.trayAvailable ? "#14251d" : "#281a1d"
                                        border.width: 1
                                        border.color: backend.trayAvailable ? "#28513a" : "#563037"
                                        Text { anchors.centerIn: parent; text: backend.trayAvailable ? "✓" : "!"; color: backend.trayAvailable ? "#51d88a" : "#ff6b72"; font.pixelSize: 18; font.weight: Font.Bold }
                                    }
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 4
                                        Text { text: backend.trayAvailable ? "Windows tray ready" : "Windows tray unavailable"; color: "#eef1f4"; font.family: "Segoe UI Variable Text"; font.pixelSize: 14; font.weight: Font.DemiBold }
                                        Text { Layout.fillWidth: true; text: backend.trayDetail; color: "#818b99"; wrapMode: Text.Wrap; font.family: "Segoe UI Variable Text"; font.pixelSize: 10 }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
