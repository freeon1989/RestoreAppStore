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

            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 32; Layout.rightMargin: 32; Layout.topMargin: 8; Layout.bottomMargin: 10
                spacing: 10
                Text { textFormat: Text.PlainText; text: backend.status; color: backend.pal.muted; font.family: backend.pal.font; font.pixelSize: 13
                       elide: Text.ElideRight; Layout.fillWidth: true }
                ProgressBar {
                    visible: backend.busy
                    indeterminate: true
                    implicitWidth: 160; implicitHeight: 4
                    background: Rectangle { radius: 2; color: backend.pal.border }
                    contentItem: Item {
                        clip: true
                        Rectangle {
                            id: runner
                            width: parent.width * 0.35; height: parent.height; radius: 2; color: backend.pal.accent
                            XAnimator {
                                target: runner; running: backend.busy; loops: Animation.Infinite
                                from: -50; to: 160; duration: 1100; easing.type: Easing.InOutQuad
                            }
                        }
                    }
                }
                Btn { visible: backend.busy; text: "Остановить"; kind: "danger"; lock: false; implicitHeight: 28
                      onClicked: backend.stop() }
                Btn { text: backend.logOpen ? "Скрыть журнал" : "Журнал"; kind: "ghost"; lock: false; implicitHeight: 28
                      onClicked: backend.logOpen = !backend.logOpen }
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
