// Окно «Настройки»: разделы слева, содержимое справа. Всё меняется сразу и запоминается (prefs.py).
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Popup {
    id: win
    property int section: 0
    signal supportRequested()
    parent: Overlay.overlay
    anchors.centerIn: parent
    width: Math.min(780, parent.width - 60)
    height: Math.min(640, parent.height - 48)
    modal: true
    popupType: Popup.Item
    focus: true
    padding: 0
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    onAboutToShow: backend.openSettings()

    Overlay.modal: Rectangle { color: backend.pal.shade }
    background: Rectangle { radius: 16; color: backend.pal.card; border.color: backend.pal.border }
    enter: Transition {
        NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 140 }
        NumberAnimation { property: "scale"; from: 0.96; to: 1; duration: 140; easing.type: Easing.OutCubic }
    }
    exit: Transition { NumberAnimation { property: "opacity"; from: 1; to: 0; duration: 100 } }

    contentItem: RowLayout {
        spacing: 0

        // ---------- разделы ----------
        Rectangle {
            Layout.fillHeight: true
            Layout.preferredWidth: 210
            radius: 16
            color: backend.pal.rail
            Rectangle { anchors.right: parent.right; width: 18; height: parent.height; color: backend.pal.rail }  // правый край прямой
            Rectangle { anchors.right: parent.right; width: 1; height: parent.height; color: backend.pal.border }

            ColumnLayout {
                anchors.fill: parent; anchors.margins: 14; anchors.topMargin: 22
                spacing: 2
                Text { text: "Настройки"; color: backend.pal.text; font.family: backend.pal.font; font.pixelSize: 20
                       font.weight: Font.ExtraBold; Layout.leftMargin: 10; Layout.bottomMargin: 14 }
                Repeater {
                    model: [["◐", "Оформление"], ["⇣", "Загрузки"], ["⌂", "App Store"], ["◔", "Уведомления"],
                            ["ⓘ", "О программе"]]
                    delegate: Rectangle {
                        id: nav
                        required property var modelData
                        required property int index
                        readonly property bool current: win.section === index
                        Layout.fillWidth: true
                        implicitHeight: 40
                        radius: 10
                        color: current ? backend.pal.accentSoft : (navHover.hovered ? backend.pal.secondHover : backend.pal.rail)
                        Behavior on color { ColorAnimation { duration: 110 } }
                        RowLayout {
                            anchors.fill: parent; anchors.leftMargin: 12; spacing: 10
                            Text { text: nav.modelData[0]; color: nav.current ? backend.pal.accentText : backend.pal.muted
                                   font.pixelSize: 19; Layout.preferredWidth: 20; horizontalAlignment: Text.AlignHCenter }
                            Text { text: nav.modelData[1]; color: nav.current ? backend.pal.accentText : backend.pal.text
                                   font.family: backend.pal.font; font.pixelSize: 15
                                   font.weight: nav.current ? Font.Bold : Font.Medium; Layout.fillWidth: true }
                        }
                        HoverHandler { id: navHover; cursorShape: Qt.PointingHandCursor }
                        TapHandler { onTapped: win.section = nav.index }
                    }
                }
                Item { Layout.fillHeight: true }
                Text { text: backend.displayName + " " + backend.version; color: backend.pal.disabled; font.family: backend.pal.font; font.pixelSize: 13
                       Layout.leftMargin: 10 }
            }
        }

        // ---------- содержимое ----------
        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 28; Layout.rightMargin: 14; Layout.topMargin: 14
                Item { Layout.fillWidth: true }
                Btn { text: "✕"; kind: "ghost"; lock: false; implicitWidth: 36; implicitHeight: 36; leftPadding: 0
                      rightPadding: 0; onClicked: win.close() }
            }

            ScrollView {
                id: scroll
                Layout.fillWidth: true
                Layout.fillHeight: true
                contentWidth: availableWidth
                clip: true
                ScrollBar.vertical: ThinScrollBar { parent: scroll; x: scroll.width - width - 2; height: scroll.height }

                StackLayout {
                    width: scroll.availableWidth - 56
                    x: 28
                    currentIndex: win.section

                    // ===== Оформление =====
                    ColumnLayout {
                        spacing: 14
                        Heading { title: "Оформление"; sub: "Меняется сразу, без перезапуска." }
                        Label2 { text: "Тема" }
                        RowLayout {
                            spacing: 12
                            Repeater {
                                model: [["system", "Как в системе"], ["light", "Светлая"], ["dark", "Тёмная"]]
                                delegate: ThemeCard { required property var modelData; mode: modelData[0]
                                                      title: modelData[1] }
                            }
                        }
                        Label2 { text: "Цвет акцента"; Layout.topMargin: 8 }
                        RowLayout {
                            spacing: 18
                            Repeater {
                                model: backend.accents
                                delegate: Swatch { required property var modelData; info: modelData }
                            }
                        }
                        Label2 { text: "Героиня на фоне"; Layout.topMargin: 10 }
                        Text {
                            text: "Справа на фоне, в спокойном стиле. Можно выключить."
                            color: backend.pal.muted; font.family: backend.pal.font; font.pixelSize: 13
                            wrapMode: Text.WordWrap; Layout.fillWidth: true
                        }
                        Flow {
                            Layout.fillWidth: true
                            spacing: 8
                            Repeater {
                                model: backend.heroines
                                delegate: Rectangle {
                                    id: hcard
                                    required property var modelData
                                    readonly property bool on: backend.heroineName === modelData.key
                                    width: 70; height: 112
                                    radius: 16
                                    color: on ? backend.pal.accentSoft : (hHover.hovered ? backend.pal.secondHover : backend.pal.second)
                                    border.color: on ? backend.pal.accent : backend.pal.border
                                    border.width: on ? 2 : 1
                                    clip: true
                                    Column {
                                        anchors.fill: parent; anchors.margins: 6; spacing: 4
                                        Rectangle {
                                            width: parent.width; height: 70; radius: 10
                                            color: backend.pal.bg
                                            clip: true
                                            Image {
                                                visible: hcard.modelData.url !== ""
                                                anchors.fill: parent
                                                fillMode: Image.PreserveAspectCrop
                                                source: hcard.modelData.url
                                                asynchronous: true
                                            }
                                            Text {
                                                visible: hcard.modelData.url === ""
                                                anchors.centerIn: parent
                                                text: "✕"
                                                color: backend.pal.muted
                                                font.pixelSize: 20
                                            }
                                        }
                                        Text {
                                            text: hcard.modelData.title
                                            color: hcard.on ? backend.pal.accentText : backend.pal.text
                                            font.family: backend.pal.font; font.pixelSize: 12
                                            font.weight: hcard.on ? Font.DemiBold : Font.Medium
                                            width: parent.width; elide: Text.ElideRight; horizontalAlignment: Text.AlignHCenter
                                        }
                                    }
                                    HoverHandler { id: hHover; cursorShape: Qt.PointingHandCursor }
                                    TapHandler { onTapped: backend.heroineName = hcard.modelData.key }
                                }
                            }
                        }
                    }

                    // ===== Загрузки =====
                    ColumnLayout {
                        spacing: 14
                        Heading { title: "Загрузки"; sub: "Куда сохраняются скачанные .ipa. Повторно одну и ту же версию программа не скачивает." }
                        Group {
                            Row2 {
                                title: "Папка"
                                sub: backend.ipaDir
                                subElide: Text.ElideMiddle
                                Btn { text: "Изменить…"; lock: false; implicitHeight: 34; onClicked: backend.chooseIpaDir() }
                                Btn { text: "Открыть"; kind: "ghost"; lock: false; implicitHeight: 34
                                      onClicked: backend.openFolder() }
                            }
                            Row2 {
                                visible: backend.ipaDir !== backend.defaultIpaDir
                                title: "Вернуть папку по умолчанию"
                                sub: backend.defaultIpaDir
                                subElide: Text.ElideMiddle
                                Btn { text: "Вернуть"; kind: "ghost"; lock: false; implicitHeight: 34
                                      onClicked: backend.resetIpaDir() }
                            }
                            Row2 {
                                title: "Скачанные файлы"
                                sub: backend.ipaSummary
                                Btn { text: "Очистить…"; kind: "danger"; lock: false; implicitHeight: 34
                                      enabled: backend.ipaSummary !== "Скачанных файлов нет" && !backend.busy
                                      onClicked: backend.clearIpa() }
                            }
                            Row2 {
                                last: true
                                title: "Удалять .ipa после установки"
                                sub: "Экономит место. Чтобы поставить приложение снова, файл придётся скачать заново."
                                Toggle { Layout.fillWidth: false; checked: backend.deleteAfterInstall
                                         onToggled: backend.deleteAfterInstall = checked }
                            }
                        }
                    }

                    // ===== App Store =====
                    ColumnLayout {
                        spacing: 14
                        Heading { title: "App Store"; sub: "Как программа проверяет наличие приложений и скачивает их." }
                        Group {
                            Row2 {
                                title: "Страна магазина"
                                sub: "Код страны для проверки, есть ли приложение в App Store (ru, us, kz …)"
                                Field { Layout.fillWidth: false; implicitWidth: 64; implicitHeight: 38
                                        horizontalAlignment: Text.AlignHCenter
                                        text: backend.country; maximumLength: 2; onTextEdited: backend.country = text }
                            }
                            Row2 {
                                title: "Только удалённые в «Моих удалённых»"
                                sub: "Скрывать приложения из истории Apple ID, которые сейчас есть в App Store"
                                Toggle { Layout.fillWidth: false; checked: backend.onlyRemoved; onToggled: backend.setOnlyRemoved(checked) }
                            }
                            Row2 {
                                last: true
                                title: "Получать лицензию"
                                sub: "Если приложение ещё продаётся в App Store, бесплатно «купить» его на ваш Apple ID перед скачиванием"
                                Toggle { Layout.fillWidth: false; checked: backend.purchase; onToggled: backend.purchase = checked }
                            }
                        }
                    }

                    // ===== Уведомления =====
                    ColumnLayout {
                        spacing: 14
                        Heading { title: "Уведомления"; sub: "Скачивание и установка могут идти несколько минут — можно заняться другим." }
                        Group {
                            Row2 {
                                last: true
                                title: "Сообщать, когда всё готово"
                                sub: "Значок Restore на панели задач замигает, если окно в это время не на переднем плане"
                                Toggle { Layout.fillWidth: false; checked: backend.notifyDone; onToggled: backend.notifyDone = checked }
                            }
                        }
                    }

                    // ===== О программе =====
                    ColumnLayout {
                        spacing: 14
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 16
                            Layout.topMargin: 6
                            Logo { size: 64 }
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                Text { text: backend.displayName + " " + backend.version; color: backend.pal.text; font.family: backend.pal.font
                                       font.pixelSize: 22; font.weight: Font.ExtraBold }
                                Text { text: "Приложения из истории покупок Apple ID — снова на iPhone"
                                       color: backend.pal.muted; font.family: backend.pal.font; font.pixelSize: 15
                                       Layout.fillWidth: true; wrapMode: Text.WordWrap }
                            }
                        }

                        Group {
                            Row2 { title: "Проверять обновления при запуске"
                                   sub: "Только релизы этого проекта на GitHub, без установки «в тихую»."
                                Toggle { Layout.fillWidth: false; checked: backend.autoUpdate; onToggled: backend.autoUpdate = checked } }
                            Row2 { title: "Проверить сейчас"
                                   sub: backend.updateText !== "" ? backend.updateText : "Сверка с GitHub Releases."
                                   subColor: backend.updateUrl !== "" ? backend.pal.ok : backend.pal.muted
                                   last: backend.updateUrl === ""
                                Btn { text: "Проверить"; lock: false; implicitHeight: 34; onClicked: backend.checkUpdates() } }
                            Row2 { visible: backend.updateUrl !== ""
                                   title: "Доступна новая версия"
                                   sub: "Откроется страница релиза. Сверьте SHA-256 перед заменой файла."
                                   last: true
                                Btn { text: "Открыть релиз"; kind: "primary"; lock: false; implicitHeight: 34
                                      onClicked: backend.openUrl(backend.updateUrl) } }
                        }

                    }
                }
            }
        }
    }

    // ---------- детали ----------
    component Heading: ColumnLayout {
        property string title: ""
        property string sub: ""
        Layout.fillWidth: true
        spacing: 4
        Text { text: parent.title; color: backend.pal.text; font.family: backend.pal.font; font.pixelSize: 20; font.weight: Font.ExtraBold }
        Text { text: parent.sub; color: backend.pal.muted; font.family: backend.pal.font; font.pixelSize: 14; wrapMode: Text.WordWrap
               Layout.fillWidth: true; visible: text !== "" }
    }

    component Label2: Text {
        color: backend.pal.muted; font.family: backend.pal.font; font.pixelSize: 13; font.weight: Font.Bold
        font.capitalization: Font.AllUppercase; font.letterSpacing: 0.6
    }

    // группа строк настроек: рамка вокруг, строки через разделитель
    component Group: Rectangle {
        default property alias rows: col.data
        Layout.fillWidth: true
        implicitHeight: col.implicitHeight
        radius: 14
        color: backend.pal.card
        border.color: backend.pal.border
        ColumnLayout { id: col; width: parent.width; spacing: 0 }
    }

    // строка: название и пояснение слева, управление справа (дочерние элементы)
    component Row2: Item {
        id: row
        property string title: ""
        property string sub: ""
        property color subColor: backend.pal.muted
        property int subElide: Text.ElideNone
        property bool last: false
        default property alias controls: ctl.data
        Layout.fillWidth: true
        implicitHeight: Math.max(60, texts.implicitHeight + 26)
        RowLayout {
            anchors.fill: parent; anchors.leftMargin: 16; anchors.rightMargin: 14
            spacing: 14
            ColumnLayout {
                id: texts
                Layout.fillWidth: true
                spacing: 2
                Text { text: row.title; color: backend.pal.text; font.family: backend.pal.font; font.pixelSize: 15; font.weight: Font.DemiBold
                       Layout.fillWidth: true; wrapMode: Text.WordWrap }
                Text { text: row.sub; color: row.subColor; font.family: backend.pal.font; font.pixelSize: 13
                       Layout.fillWidth: true; visible: text !== ""
                       wrapMode: row.subElide === Text.ElideNone ? Text.WordWrap : Text.NoWrap; elide: row.subElide }
            }
            RowLayout { id: ctl; spacing: 6 }
        }
        Rectangle { visible: !row.last; anchors.bottom: parent.bottom; x: 16; width: parent.width - 16; height: 1
                    color: backend.pal.border }
    }

    // тема: карточка с маленьким макетом окна
    component ThemeCard: ColumnLayout {
        id: card
        property string mode: "system"
        property string title: ""
        readonly property bool on: backend.themeMode === mode
        spacing: 8
        Rectangle {
            implicitWidth: 150; implicitHeight: 96
            radius: 12
            color: backend.pal.card
            border.width: card.on ? 2 : 1
            border.color: card.on ? backend.pal.accent : (cardHover.hovered ? backend.pal.borderLight : backend.pal.border)
            Row {
                anchors.fill: parent; anchors.margins: card.on ? 6 : 5
                Mock { width: card.mode === "system" ? parent.width / 2 : parent.width; height: parent.height
                       dark: card.mode === "dark"; leftRound: true; rightRound: card.mode !== "system" }
                Mock { visible: card.mode === "system"; width: parent.width / 2; height: parent.height
                       dark: true; leftRound: false; rightRound: true }
            }
            HoverHandler { id: cardHover; cursorShape: Qt.PointingHandCursor }
            TapHandler { onTapped: backend.themeMode = card.mode }
        }
        RowLayout {
            spacing: 6
            Rectangle { width: 14; height: 14; radius: 7; color: card.on ? backend.pal.accent : backend.pal.card; border.width: 2
                        border.color: card.on ? backend.pal.accent : backend.pal.borderLight
                        Rectangle { anchors.centerIn: parent; width: 6; height: 6; radius: 3; color: "white"
                                    visible: card.on } }
            Text { text: card.title; color: backend.pal.text; font.family: backend.pal.font; font.pixelSize: 14
                   font.weight: card.on ? Font.Bold : Font.Medium }
        }
    }

    // макет окна внутри карточки темы (цвета нарочно постоянные: это картинка светлой/тёмной темы)
    component Mock: Rectangle {
        id: mock
        property bool dark: false
        property bool leftRound: true
        property bool rightRound: true
        radius: 8
        color: dark ? "#161311" : "#F3EEE6"
        Rectangle { visible: !mock.leftRound; width: 8; height: parent.height; color: parent.color }
        Rectangle { visible: !mock.rightRound; anchors.right: parent.right; width: 8; height: parent.height
                    color: parent.color }
        Rectangle { width: parent.width; height: 14; radius: mock.radius; color: mock.dark ? "#1C1916" : "#FFFBF6"
                    Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 6; color: parent.color } }
        Rectangle { x: 8; y: 24; width: parent.width * 0.55; height: 6; radius: 3
                    color: mock.dark ? "#F3EEE6" : "#1C1814"; opacity: 0.85 }
        Rectangle { x: 8; y: 36; width: parent.width - 16; height: 22; radius: 5; color: mock.dark ? "#221E1A" : "#FFFBF6" }
        Rectangle { x: 8; y: 64; width: parent.width * 0.4; height: 10; radius: 5; color: backend.pal.accent }
    }

    // цвет акцента: круг с градиентом и подпись
    component Swatch: ColumnLayout {
        id: sw
        property var info: ({})
        readonly property bool on: backend.accentName === info.key
        spacing: 6
        Rectangle {
            Layout.alignment: Qt.AlignHCenter
            width: 46; height: 46; radius: 23
            color: backend.pal.card
            border.width: 2
            border.color: sw.on ? sw.info.color : (swHover.hovered ? backend.pal.borderLight : backend.pal.card)
            Rectangle {
                anchors.centerIn: parent
                width: 36; height: 36; radius: 18
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0; color: sw.info.grad1 }
                    GradientStop { position: 1; color: sw.info.grad2 }
                }
                Text { anchors.centerIn: parent; text: "✓"; color: "white"; font.pixelSize: 17; font.bold: true
                       visible: sw.on }
            }
            HoverHandler { id: swHover; cursorShape: Qt.PointingHandCursor }
            TapHandler { onTapped: backend.accentName = sw.info.key }
        }
        Text { text: sw.info.title; color: sw.on ? backend.pal.text : backend.pal.muted; font.family: backend.pal.font; font.pixelSize: 13
               font.weight: sw.on ? Font.Bold : Font.Medium; Layout.alignment: Qt.AlignHCenter }
    }
}
