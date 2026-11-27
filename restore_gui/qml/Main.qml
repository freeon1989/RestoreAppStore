// Главное окно RestoreAppStore. Состояние и действия — backend, палитра — backend.pal.
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: win
    width: 1240; height: 840
    minimumWidth: 1100; minimumHeight: 660
    visible: startVisible
    title: backend.displayName + " " + backend.version
    color: backend.pal.bg
    font.family: backend.pal.font
    palette.window: backend.pal.card; palette.windowText: backend.pal.text; palette.base: backend.pal.field; palette.text: backend.pal.text
    palette.button: backend.pal.second; palette.buttonText: backend.pal.text; palette.highlight: backend.pal.accent; palette.highlightedText: "white"
    palette.light: backend.pal.card; palette.mid: backend.pal.border; palette.dark: backend.pal.muted; palette.placeholderText: backend.pal.muted
    palette.toolTipBase: backend.pal.card; palette.toolTipText: backend.pal.text

    // Фон в стиле Apple: мягкая заливка и героиня справа, слева текст остаётся читаемым.
    Rectangle { anchors.fill: parent; color: backend.pal.bg }
    Image {
        id: heroine
        visible: backend.heroineUrl !== ""
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.topMargin: 20
        anchors.bottomMargin: 20
        anchors.rightMargin: 12
        // ширина по высоте кадра 3:4, фигура целиком, без обрезки
        width: Math.min(parent.width * 0.36, (height) * 0.68)
        fillMode: Image.PreserveAspectFit
        horizontalAlignment: Image.AlignRight
        verticalAlignment: Image.AlignVCenter
        source: backend.heroineUrl
        asynchronous: true
        opacity: 1
        readonly property real paintedX: width - paintedWidth
        readonly property real paintedY: (height - paintedHeight) / 2
        readonly property var orb: backend.heroineOrb
        readonly property bool hasOrb: visible && status === Image.Ready && typeof orb.x === "number"
        readonly property real orbPad: hasOrb ? orb.r * 1.35 : 0.10
        // карточки не заходят на лицо (не меньше 48% ширины) и не закрывают сферу
        readonly property real contentRightPad: {
            if (!visible)
                return 0
            var floor = Math.max(24, Math.round(12 + width * 0.48))
            if (!hasOrb)
                return floor
            var pad = 12 + width - paintedWidth * (orb.x - orbPad)
            return Math.max(floor, Math.round(pad))
        }
    }
    Rectangle {
        visible: heroine.visible
        x: heroine.x + heroine.paintedX
        y: heroine.y + heroine.paintedY + heroine.paintedHeight - height
        width: heroine.paintedWidth
        height: Math.max(72, Math.round(heroine.paintedHeight * 0.22))
        gradient: Gradient {
            GradientStop { position: 0.00; color: backend.pal.bgClear }
            GradientStop { position: 0.40; color: backend.pal.bgFade }
            GradientStop { position: 1.00; color: backend.pal.bg }
        }
    }
    Rectangle {
        anchors.fill: parent
        visible: heroine.visible
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.00; color: backend.pal.bg }
            GradientStop { position: 0.50; color: backend.pal.bg }
            GradientStop { position: 0.70; color: backend.pal.bgFade }
            GradientStop { position: 1.00; color: backend.pal.bgClear }
        }
    }
    Item {
        id: orbGlow
        visible: heroine.hasOrb
        x: heroine.x + heroine.paintedX
        y: heroine.y + heroine.paintedY
        width: heroine.paintedWidth
        height: heroine.paintedHeight
        readonly property real cx: (heroine.orb.x || 0) * width
        readonly property real cy: (heroine.orb.y || 0) * height
        readonly property real base: (heroine.orb.r || 0.08) * width
        readonly property color tint: heroine.orb.color || "#88FFCC"
        readonly property bool animate: !backend.reduceMotion

        Item {
            id: glow
            width: orbGlow.base * 3.2
            height: width
            x: orbGlow.cx - width / 2
            y: orbGlow.cy - height / 2
            property real pulse: orbGlow.animate ? 0.7 : 0.78
            Repeater {
                model: 3
                Rectangle {
                    anchors.centerIn: parent
                    width: glow.width * (0.40 + index * 0.30)
                    height: width
                    radius: width / 2
                    color: orbGlow.tint
                    opacity: glow.pulse * (index === 0 ? 0.50 : index === 1 ? 0.26 : 0.11)
                }
            }
        }
        SequentialAnimation {
            running: orbGlow.visible && orbGlow.animate
            loops: Animation.Infinite
            ParallelAnimation {
                NumberAnimation { target: glow; property: "pulse"; from: 0.52; to: 1.0; duration: 1400; easing.type: Easing.InOutSine }
                NumberAnimation { target: glow; property: "scale"; from: 0.92; to: 1.08; duration: 1400; easing.type: Easing.InOutSine }
            }
            ParallelAnimation {
                NumberAnimation { target: glow; property: "pulse"; from: 1.0; to: 0.52; duration: 1400; easing.type: Easing.InOutSine }
                NumberAnimation { target: glow; property: "scale"; from: 1.08; to: 0.92; duration: 1400; easing.type: Easing.InOutSine }
            }
        }
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        SideRail {
            Layout.fillHeight: true
            onHelpRequested: dialogs.openHelp()
            onSettingsRequested: dialogs.openSettings()
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            // карточки не заходят на лицо и торс героини справа
            Layout.rightMargin: heroine.contentRightPad
            spacing: 0
            enabled: !detail.visible && !dialogs.anyOpen

            StackLayout {
                id: pages
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.margins: 32
                Layout.bottomMargin: 8
                currentIndex: ["home", "apps", "mine", "ipa"].indexOf(backend.page)
                HomePage { onHelpRequested: dialogs.openHelp() }
                AppsPage {}
                MinePage {}
                IpaPage {}
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.leftMargin: 32; Layout.rightMargin: 32
                Layout.preferredHeight: backend.selectedCount > 0 ? 58 : 0
                visible: Layout.preferredHeight > 0
                clip: true
                radius: 14; color: backend.pal.accentSoft; border.color: backend.pal.accentDim
                Behavior on Layout.preferredHeight { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }
                RowLayout {
                    anchors.fill: parent; anchors.leftMargin: 16; anchors.rightMargin: 12
                    Text { text: backend.selectedText; color: backend.pal.text; font.family: backend.pal.font; font.pixelSize: 15
                           font.weight: Font.Bold; Layout.fillWidth: true }
                    Btn { text: "Снять"; kind: "ghost"; lock: false; onClicked: backend.clearSelection() }
                    Btn { text: "Поставить выбранные"; kind: "primary"; onClicked: backend.installSelected() }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 32; Layout.rightMargin: 32; Layout.topMargin: 8; Layout.bottomMargin: 10
                spacing: 8

                ColumnLayout {
                    visible: backend.jobActive
                    Layout.fillWidth: true
                    spacing: 6
                    Text {
                        textFormat: Text.PlainText
                        text: backend.jobOverall
                        color: backend.pal.text; font.family: backend.pal.font; font.pixelSize: 13; font.weight: Font.DemiBold
                        visible: backend.jobOverall !== ""
                    }
                    // Скачивание
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 3
                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: "Скачивание"; color: backend.pal.muted; font.family: backend.pal.font; font.pixelSize: 12 }
                            Text { textFormat: Text.PlainText; text: backend.downloadText; color: backend.pal.text; font.family: backend.pal.font; font.pixelSize: 12
                                   elide: Text.ElideRight; Layout.fillWidth: true; horizontalAlignment: Text.AlignRight }
                        }
                        Rectangle {
                            Layout.fillWidth: true; implicitHeight: 6; radius: 3; color: backend.pal.border
                            clip: true
                            Rectangle {
                                anchors.left: parent.left; anchors.top: parent.top; anchors.bottom: parent.bottom
                                radius: 3; color: backend.pal.accent
                                width: parent.width * (backend.downloadPct < 0 ? 0.35 : Math.max(0, Math.min(1, backend.downloadPct / 100)))
                                Behavior on width { NumberAnimation { duration: 160 } }
                            }
                        }
                    }
                    // Установка
                    ColumnLayout {
                        visible: backend.installText !== ""
                        Layout.fillWidth: true
                        spacing: 3
                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: "Установка"; color: backend.pal.muted; font.family: backend.pal.font; font.pixelSize: 12 }
                            Text { textFormat: Text.PlainText; text: backend.installText; color: backend.pal.text; font.family: backend.pal.font; font.pixelSize: 12
                                   elide: Text.ElideRight; Layout.fillWidth: true; horizontalAlignment: Text.AlignRight }
                        }
                        Rectangle {
                            Layout.fillWidth: true; implicitHeight: 6; radius: 3; color: backend.pal.border
                            clip: true
                            Rectangle {
                                anchors.left: parent.left; anchors.top: parent.top; anchors.bottom: parent.bottom
                                radius: 3; color: backend.pal.ok
                                width: parent.width * (backend.installPct < 0 ? 0.35 : Math.max(0, Math.min(1, backend.installPct / 100)))
                                Behavior on width { NumberAnimation { duration: 160 } }
                            }
                        }
                    }
                    Repeater {
                        model: backend.jobs
                        delegate: RowLayout {
                            required property string title
                            required property string phase
                            required property string downloadText
                            required property string installText
                            required property real downloadPct
                            required property real installPct
                            required property string state
                            visible: backend.jobCount > 1
                            Layout.fillWidth: true
                            spacing: 8
                            Text { textFormat: Text.PlainText; text: title; color: backend.pal.text; font.family: backend.pal.font; font.pixelSize: 12
                                   elide: Text.ElideRight; Layout.preferredWidth: 160 }
                            Rectangle {
                                Layout.fillWidth: true; implicitHeight: 4; radius: 2; color: backend.pal.border
                                clip: true
                                Rectangle {
                                    anchors.left: parent.left; anchors.top: parent.top; anchors.bottom: parent.bottom
                                    radius: 2; color: state === "install" || state === "done" ? backend.pal.ok : backend.pal.accent
                                    width: parent.width * Math.max(0, Math.min(1, (state === "install" || state === "done" ? installPct : downloadPct) / 100))
                                }
                            }
                            Text { textFormat: Text.PlainText; text: phase; color: backend.pal.muted; font.family: backend.pal.font; font.pixelSize: 11
                                   elide: Text.ElideRight; Layout.preferredWidth: 140; horizontalAlignment: Text.AlignRight }
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    Text { textFormat: Text.PlainText; text: backend.status; color: backend.pal.muted; font.family: backend.pal.font; font.pixelSize: 13
                           elide: Text.ElideRight; Layout.fillWidth: true }
                    ProgressBar {
                        visible: backend.busy && !backend.jobActive
                        indeterminate: true
                        implicitWidth: 160; implicitHeight: 4
                        background: Rectangle { radius: 2; color: backend.pal.border }
                        contentItem: Item {
                            clip: true
                            Rectangle {
                                id: runner
                                width: parent.width * 0.35; height: parent.height; radius: 2; color: backend.pal.accent
                                XAnimator {
                                    target: runner; running: backend.busy && !backend.jobActive; loops: Animation.Infinite
                                    from: -50; to: 160; duration: 1100; easing.type: Easing.InOutQuad
                                }
                            }
                        }
                    }
                    Btn { visible: backend.busy || backend.jobActive; text: "Остановить"; kind: "danger"; lock: false; implicitHeight: 28
                          onClicked: backend.stop() }
                    Btn { text: backend.logOpen ? "Скрыть журнал" : "Журнал"; kind: "ghost"; lock: false; implicitHeight: 28
                          onClicked: backend.logOpen = !backend.logOpen }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.leftMargin: 32; Layout.rightMargin: 32; Layout.bottomMargin: backend.logOpen ? 16 : 0
                Layout.preferredHeight: backend.logOpen ? 190 : 0
                visible: Layout.preferredHeight > 0
                Behavior on Layout.preferredHeight { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }
                radius: 14; color: backend.pal.card; border.color: backend.pal.border
                clip: true
                ScrollView {
                    id: logScroll
                    anchors.fill: parent; anchors.margins: 6
                    TextArea {
                        id: logText; textFormat: TextEdit.PlainText
                        readOnly: true; selectByMouse: true
                        wrapMode: TextEdit.Wrap
                        color: backend.pal.logText; selectionColor: backend.pal.accentDim
                        font.family: backend.pal.mono; font.pixelSize: 13
                        background: null
                    }
                }
            }
        }
    }

    DetailPanel { id: detail }
    Dialogs { id: dialogs }

    Connections {
        target: backend
        function onLogAppended(text) {
            logText.append(text)
            if (logText.length > 400000) {
                const cut = logText.text.indexOf("\n", logText.length - 300000)
                logText.remove(0, cut + 1)
            }
            logText.cursorPosition = logText.length
        }
        function onTaskFinished() { if (!win.active) win.alert(0) }
    }
}
