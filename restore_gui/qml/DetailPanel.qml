// Панель приложения Ink (выезжает справа): проверки, копии, версии, скачивание.
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Drawer {
    id: panel
    edge: Qt.RightEdge
    width: Math.min(620, Math.max(520, parent.width * 0.5))
    height: parent.height
    modal: true
    dragMargin: 0  // открывается только по нажатию на приложение
    Overlay.modal: Rectangle { color: backend.pal.shade }
    background: Rectangle {
        color: backend.pal.card
        Rectangle { width: 1; height: parent.height; color: backend.pal.border }
    }
    onClosed: if (backend.detailOpen) backend.closeDetail()

    Connections {
        target: backend
        function onDetailOpenChanged() { backend.detailOpen ? panel.open() : panel.close() }
    }

    function kindColor(kind) {
        return kind === "ok" ? backend.pal.ok : kind === "warn" ? backend.pal.warn : kind === "muted" ? backend.pal.muted : backend.pal.text
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 12

        // ---------- шапка ----------
        RowLayout {
            Layout.fillWidth: true
            spacing: 14
            AppIcon { size: 60; icon: backend.detailApp.icon || ""; letter: backend.detailApp.letter || "?"
                      tint: backend.detailApp.tint || backend.pal.accent }
            ColumnLayout {
                Layout.fillWidth: true; spacing: 2
                Text { textFormat: Text.PlainText; text: backend.detailApp.name || ""; color: backend.pal.text; font.family: backend.pal.font; font.pixelSize: 19
                       font.weight: Font.Bold; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                Text {
                    text: "App ID " + (backend.detailApp.id || "")
                    color: idHover.hovered ? backend.pal.text : backend.pal.muted; font.family: backend.pal.font; font.pixelSize: 13
                    HoverHandler { id: idHover; cursorShape: Qt.PointingHandCursor }
                    TapHandler { onTapped: backend.copyText(String(backend.detailApp.id)) }
                    ToolTip.visible: idHover.hovered; ToolTip.text: "Скопировать"
                }
                Text {
                    visible: backend.accountStorefrontName !== ""
                    text: "Ваша витрина: " + backend.accountStorefrontName
                    color: backend.pal.muted; font.family: backend.pal.font; font.pixelSize: 12
                    wrapMode: Text.WordWrap; Layout.fillWidth: true
                }
            }
            Btn { text: "✕"; kind: "ghost"; lock: false; implicitWidth: 40; implicitHeight: 40; leftPadding: 0
                  rightPadding: 0; onClicked: panel.close() }
        }

        ScrollView {
            id: scroll
            Layout.fillWidth: true
            Layout.fillHeight: true
            contentWidth: availableWidth
            clip: true
            ScrollBar.vertical: ThinScrollBar { parent: scroll; x: scroll.width - width; height: scroll.height }

            ColumnLayout {
                width: scroll.availableWidth - 12
                spacing: 12

                // ---------- проверки ----------
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: checksCol.implicitHeight + 24
                    radius: 14; color: backend.pal.card
                    ColumnLayout {
                        id: checksCol
                        anchors.fill: parent; anchors.margins: 12; anchors.leftMargin: 16
                        spacing: 6
                        Repeater {
                            model: [["acc", "Apple ID"], ["phone", "iPhone"], ["store", "App Store"]]
                            delegate: RowLayout {
                                required property var modelData
                                readonly property var check: backend.detailChecks[modelData[0]] || ({})
                                Layout.fillWidth: true
                                spacing: 10
                                Text { text: modelData[1]; color: backend.pal.muted; font.family: backend.pal.font; font.pixelSize: 14
                                       Layout.preferredWidth: 80 }
                                Text { textFormat: Text.PlainText; text: check.text || ""; color: panel.kindColor(check.kind)
                                       font.family: backend.pal.font; font.pixelSize: 14; font.weight: Font.Bold
                                       wrapMode: Text.WordWrap; Layout.fillWidth: true }
                            }
                        }
                    }
                }

                // ---------- версии ----------
                Text { textFormat: Text.PlainText; text: backend.versionHead; color: backend.pal.muted; font.family: backend.pal.font; font.pixelSize: 14
                       font.weight: Font.Bold; Layout.topMargin: 4 }

                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: versionsCol.implicitHeight + 20
                    radius: 14; color: backend.pal.card
                    ColumnLayout {
                        id: versionsCol
                        anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                        anchors.margins: 10
                        spacing: 2

                        RowLayout {  // идёт проверка
                            visible: backend.versionMode === "loading"
                            Layout.margins: 14
                            spacing: 10
                            BusyIndicator { running: parent.visible; implicitWidth: 24; implicitHeight: 24 }
                            Text { text: "Проверяю…"; color: backend.pal.muted; font.family: backend.pal.font; font.pixelSize: 14 }
                        }

                        ColumnLayout {  // проверка не прошла
                            visible: backend.versionMode === "error"
                            Layout.fillWidth: true; Layout.margins: 6
                            spacing: 8
                            Text { text: "Не удалось получить версии — проверка не прошла. Это ошибка, а не «нет в истории»: "
                                         + "приложение может быть в ваших покупках."
                                   color: backend.pal.warn; font.family: backend.pal.font; font.pixelSize: 14; font.weight: Font.Bold
                                   wrapMode: Text.WordWrap; Layout.fillWidth: true }
                            Text { textFormat: Text.PlainText; text: backend.detailErr; color: backend.pal.text; font.family: backend.pal.font; font.pixelSize: 14
                                   wrapMode: Text.WordWrap; Layout.fillWidth: true }
                            Text { text: "Ответ Apple (ipatool)"; color: backend.pal.muted; font.family: backend.pal.font; font.pixelSize: 12
                                   font.weight: Font.Bold }
                            TextArea {
                                Layout.fillWidth: true
                                textFormat: TextEdit.PlainText; text: backend.detailAnswer
                                readOnly: true; selectByMouse: true; wrapMode: TextEdit.Wrap
                                color: backend.pal.text; font.family: backend.pal.mono; font.pixelSize: 13
                                background: Rectangle { radius: 8; color: backend.pal.field }
                            }
                            Btn { text: "Повторить проверку"; lock: false; implicitHeight: 34; onClicked: backend.detailRecheck() }
                        }

                        Text {  // нет в истории
                            visible: backend.versionMode === "none"
                            Layout.margins: 14
                            text: "Список версий пуст. Если приложение платное, сначала купите его в App Store."
                            color: backend.pal.muted; font.family: backend.pal.font; font.pixelSize: 14; wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }

                        ColumnLayout {
                            visible: backend.versionMode === "need_purchase"
                            Layout.fillWidth: true; Layout.margins: 6
                            spacing: 8
                            Text {
                                text: "Версии появятся после добавления приложения в этот Apple ID. Если оно бесплатное, можно получить его прямо отсюда."
                                color: backend.pal.text; font.family: backend.pal.font; font.pixelSize: 14
                                wrapMode: Text.WordWrap; Layout.fillWidth: true
                            }
                            Btn {
                                text: "Получить бесплатно и показать версии"
                                kind: "primary"; lock: false; implicitHeight: 36
                                onClicked: backend.purchaseAndListVersions()
                            }
                        }

                        Repeater {  // список версий
                            model: backend.versions
                            delegate: Rectangle {
                                id: ver
                                required property string value
                                required property string title
                                required property string sub
                                required property bool mine
                                required property bool legacy
                                required property string note
                                readonly property bool chosen: backend.selectedVersion === value
                                Layout.fillWidth: true
                                height: 50; radius: 10
                                color: chosen ? backend.pal.accentSoft : (verHover.hovered ? backend.pal.cardHover : backend.pal.card)
                                Behavior on color { ColorAnimation { duration: 120 } }
                                HoverHandler { id: verHover; cursorShape: Qt.PointingHandCursor }
                                TapHandler { onTapped: backend.selectedVersion = ver.value }
                                RowLayout {
                                    anchors.fill: parent; anchors.leftMargin: 10; anchors.rightMargin: 10
                                    spacing: 12
                                    Rectangle {
                                        width: 18; height: 18; radius: 9
                                        color: "transparent"; border.width: 2
                                        border.color: ver.chosen ? backend.pal.accent : backend.pal.borderLight
                                        Rectangle { anchors.centerIn: parent; width: 8; height: 8; radius: 4
                                                    color: backend.pal.accent; visible: ver.chosen }
                                    }
                                    ColumnLayout {
                                        Layout.fillWidth: true; spacing: 0
                                        Text { textFormat: Text.PlainText; text: ver.title; color: backend.pal.text; font.family: backend.pal.font; font.pixelSize: 14
                                               font.weight: Font.Bold; Layout.fillWidth: true }
                                        Text { textFormat: Text.PlainText; text: ver.sub; color: ver.legacy ? backend.pal.warn : (ver.mine ? backend.pal.ok : backend.pal.muted); font.family: backend.pal.font
                                               font.pixelSize: 12; Layout.fillWidth: true }
                                    }
                                }
                            }
                        }

                        Btn {
                            visible: backend.moreText !== ""
                            text: backend.moreText; kind: "ghost"; lock: false; implicitHeight: 32
                            Layout.alignment: Qt.AlignHCenter
                            onClicked: backend.detailMore()
                        }

                        Text {
                            visible: backend.detailAvailability !== ""
                            text: backend.detailAvailability
                            color: backend.pal.muted; font.family: backend.pal.font; font.pixelSize: 13
                            wrapMode: Text.WordWrap; Layout.fillWidth: true; Layout.topMargin: 8
                        }
                        Text {
                            visible: backend.detailSwitchHint !== ""
                            text: backend.detailSwitchHint
                            color: backend.pal.warn; font.family: backend.pal.font; font.pixelSize: 13
                            wrapMode: Text.WordWrap; Layout.fillWidth: true
                        }
                        Btn {
                            visible: backend.detailSwitchAccountId !== ""
                            text: "Переключить аккаунт"
                            kind: "second"; lock: false; implicitHeight: 34
                            onClicked: backend.switchAccount(backend.detailSwitchAccountId)
                        }
                        Text {
                            visible: backend.installHint !== ""
                            text: backend.installHint
                            color: backend.pal.warn; font.family: backend.pal.font; font.pixelSize: 13
                            font.weight: Font.DemiBold
                            wrapMode: Text.WordWrap; Layout.fillWidth: true; Layout.topMargin: 6
                        }
                        RowLayout {
                            visible: backend.newerVersionReady || backend.installAnywayReady
                            Layout.fillWidth: true
                            spacing: 8
                            Btn {
                                visible: backend.newerVersionReady
                                text: "Выбрать более новую версию"
                                kind: "primary"; lock: false; implicitHeight: 36
                                onClicked: backend.selectNewerVersion()
                            }
                            Btn {
                                visible: backend.installAnywayReady
                                text: "Всё равно установить"
                                kind: "ghost"; lock: false; implicitHeight: 36
                                onClicked: backend.installAnyway()
                            }
                        }
                    }
                }

                // ---------- копии под другими названиями ----------
                ColumnLayout {
                    visible: backend.cloneHead !== ""
                    Layout.fillWidth: true
                    spacing: 6
                    Text { textFormat: Text.PlainText; text: backend.cloneHead; color: backend.cloneHeadOk ? backend.pal.ok : backend.pal.muted; font.family: backend.pal.font
                           font.pixelSize: 14; font.weight: Font.Bold }
                    Text { text: "Это же приложение публиковали под видом других программ. Если вы ставили такую копию, "
                                 + "она в истории вашего Apple ID под своим ID — нажмите на неё, чтобы увидеть её версии."
                           color: backend.pal.muted; font.family: backend.pal.font; font.pixelSize: 13; wrapMode: Text.WordWrap
                           Layout.fillWidth: true }
                    Repeater {
                        model: backend.clones
                        delegate: Rectangle {
                            id: clone
                            required property int index
                            required property string title
                            required property string sub
                            required property string letter
                            required property string tint
                            required property string icon
                            required property string status
                            required property string statusKind
                            Layout.fillWidth: true
                            height: 52; radius: 12
                            color: cloneHover.hovered ? backend.pal.cardHover : backend.pal.card
                            Behavior on color { ColorAnimation { duration: 120 } }
                            HoverHandler { id: cloneHover; cursorShape: Qt.PointingHandCursor }
                            TapHandler { onTapped: backend.openDetail("clones", clone.index) }
                            RowLayout {
                                anchors.fill: parent; anchors.leftMargin: 10; anchors.rightMargin: 10
                                spacing: 10
                                AppIcon { size: 32; icon: clone.icon; letter: clone.letter; tint: clone.tint }
                                ColumnLayout {
                                    Layout.fillWidth: true; spacing: 0
                                    Text { textFormat: Text.PlainText; text: clone.title; color: backend.pal.text; font.family: backend.pal.font; font.pixelSize: 14
                                           font.weight: Font.Bold; elide: Text.ElideRight; Layout.fillWidth: true }
                                    Text { textFormat: Text.PlainText; text: clone.sub; color: backend.pal.muted; font.family: backend.pal.font; font.pixelSize: 12
                                           elide: Text.ElideRight; Layout.fillWidth: true }
                                }
                                Text { textFormat: Text.PlainText; text: clone.status; color: panel.kindColor(clone.statusKind)
                                       font.family: backend.pal.font; font.pixelSize: 13 }
                                Text { text: "›"; color: backend.pal.muted; font.pixelSize: 18 }
                            }
                        }
                    }
                }
            }
        }

        // ---------- внизу ----------
        Text {
            text: "Apple не хранит и не отдаёт список версий, которые вы скачивали раньше. Здесь только версии, "
                  + "доступные именно вашему Apple ID, и только если приложение есть в его истории. Отметка "
                  + "«скачано через программу» — версии, которые вы уже брали здесь."
            color: backend.pal.muted; font.family: backend.pal.font; font.pixelSize: 12; wrapMode: Text.WordWrap; Layout.fillWidth: true
        }
        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            Btn {
                text: "Скачать и установить"; kind: "primary"; Layout.fillWidth: true; implicitHeight: 44
                enabled: backend.actionsEnabled && !backend.busy
                onClicked: backend.detailAction(true)
            }
            Btn {
                text: "Только скачать IPA"; implicitHeight: 44
                enabled: backend.actionsEnabled && !backend.busy
                onClicked: backend.detailAction(false)
            }
        }
    }
}
