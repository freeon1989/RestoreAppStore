// Боковая навигация Ink: знак, разделы, статус iPhone, вход и меню.
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: rail
    signal helpRequested()
    signal settingsRequested()
    implicitWidth: 220
    color: backend.pal.rail

    Rectangle { anchors.right: parent.right; width: 1; height: parent.height; color: backend.pal.border }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        anchors.bottomMargin: 14
        spacing: 6

        RowLayout {
            Layout.topMargin: 6
            Layout.bottomMargin: 18
            spacing: 10
            Logo { size: 32 }
            ColumnLayout {
                spacing: 0
                Text { text: "Restore"; color: backend.pal.text; font.family: backend.pal.font; font.pixelSize: 15; font.weight: Font.ExtraBold }
                Text { text: "AppStore"; color: backend.pal.muted; font.family: backend.pal.font; font.pixelSize: 11; font.weight: Font.DemiBold
                       font.letterSpacing: 0.8 }
            }
        }

        component NavItem: Rectangle {
            property string pageId
            property string title
            readonly property bool current: backend.page === pageId
            Layout.fillWidth: true
            implicitHeight: 40
            radius: 10
            color: current ? backend.pal.accentSoft : (navHover.hovered ? backend.pal.secondHover : backend.pal.rail)
            Text {
                anchors.verticalCenter: parent.verticalCenter
                anchors.left: parent.left; anchors.right: parent.right
                anchors.leftMargin: 12; anchors.rightMargin: 12
                text: parent.title
                font.family: backend.pal.font; font.pixelSize: 14
                font.weight: parent.current ? Font.Bold : Font.Medium
                color: parent.current ? backend.pal.accentText : (navHover.hovered ? backend.pal.text : backend.pal.muted)
                elide: Text.ElideRight
            }
            HoverHandler { id: navHover; cursorShape: Qt.PointingHandCursor }
            TapHandler { onTapped: backend.showPage(pageId) }
        }
        NavItem { pageId: "home"; title: "Главная" }
        NavItem { pageId: "apps"; title: "Каталог" }
        NavItem { pageId: "mine"; title: "Мои удалённые" }
        NavItem { pageId: "ipa"; title: "Файлы .ipa" }

        Item { Layout.fillHeight: true }

        // iPhone
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: phoneCol.implicitHeight + 16
            radius: 10
            color: backend.pal.card
            border.color: backend.pal.border
            HoverHandler { id: phoneHover; cursorShape: Qt.PointingHandCursor }
            TapHandler { onTapped: backend.connectDevice() }
            ColumnLayout {
                id: phoneCol
                anchors.left: parent.left; anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                anchors.margins: 10
                spacing: 4
                RowLayout {
                    spacing: 8
                    Rectangle {
                        width: 8; height: 8; radius: 4
                        color: backend.deviceState === "ok" ? backend.pal.ok : backend.deviceState === "trust" ? backend.pal.warn : backend.pal.borderLight
                    }
                    Text { text: "Устройство"; color: backend.pal.muted; font.family: backend.pal.font; font.pixelSize: 11
                           font.weight: Font.DemiBold; font.letterSpacing: 0.6 }
                }
                Text {
                    textFormat: Text.PlainText
                    text: backend.deviceState === "ok" ? backend.deviceText
                        : backend.deviceState === "trust" ? backend.deviceText
                        : "Подключить"
                    color: backend.deviceState === "trust" ? backend.pal.warn : backend.pal.text
                    font.family: backend.pal.font; font.pixelSize: 13; font.weight: Font.Medium
                    wrapMode: Text.WordWrap; Layout.fillWidth: true
                    maximumLineCount: 2; elide: Text.ElideRight
                }
            }
        }
        Text {
            visible: backend.deviceState !== "ok"
            text: "Установить «Устройства Apple»"
            color: storeHover.hovered ? backend.pal.accent : backend.pal.accentText
            font.family: backend.pal.font; font.pixelSize: 12; font.weight: Font.DemiBold
            wrapMode: Text.WordWrap; Layout.fillWidth: true
            HoverHandler { id: storeHover; cursorShape: Qt.PointingHandCursor }
            TapHandler { onTapped: backend.openAppleDevicesStore() }
        }

        Btn {
            visible: !backend.loggedIn
            Layout.fillWidth: true
            text: "Войти в Apple ID"; kind: "primary"; lock: false; implicitHeight: 38
            onClicked: backend.openLogin()
        }
        ColumnLayout {
            visible: backend.loggedIn
            Layout.fillWidth: true
            spacing: 6
            Text {
                textFormat: Text.PlainText
                text: backend.account
                color: backend.pal.text; font.family: backend.pal.font; font.pixelSize: 13; font.weight: Font.DemiBold
                elide: Text.ElideMiddle; Layout.fillWidth: true
            }
            Btn { Layout.fillWidth: true; text: "Выйти"; kind: "danger"; lock: false; implicitHeight: 34
                  onClicked: backend.logout() }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.topMargin: 4
            spacing: 6
            Btn {
                Layout.fillWidth: true
                text: "Настройки"; kind: "second"; lock: false; implicitHeight: 36
                onClicked: rail.settingsRequested()
            }
            Btn {
                id: more
                text: "⋯"; kind: "second"; lock: false
                implicitWidth: 36; implicitHeight: 36; leftPadding: 0; rightPadding: 0
                font.pixelSize: 18
                onClicked: menu.popup(more, 0, more.height + 6)
                Menu {
                    id: menu
                    font.family: backend.pal.font
                    MenuItem { text: "Подключить устройство / повторить"; onTriggered: backend.connectDevice() }
                    MenuItem { text: "Справка"; onTriggered: rail.helpRequested() }
                    MenuItem { text: "Открыть папку с IPA"; onTriggered: backend.openFolder() }
                    MenuItem { text: "Проверить связь с Apple"; onTriggered: backend.netCheck() }
                }
            }
        }
    }
}
