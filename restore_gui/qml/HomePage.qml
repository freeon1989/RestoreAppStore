import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: home
    signal helpRequested()
    spacing: 16

    ColumnLayout {
        spacing: 8
        Text {
            text: backend.greeting
            color: backend.pal.accentText
            font.family: backend.pal.font; font.pixelSize: 12; font.weight: Font.DemiBold
            font.letterSpacing: 1.2
        }
        Text { text: "Снова на iPhone"; color: backend.pal.text; font.family: backend.pal.font; font.pixelSize: 34; font.weight: Font.ExtraBold }
        Text {
            text: "Найдите в истории покупок своего Apple ID приложения, которых уже нет в App Store, и поставьте их обратно."
            color: backend.pal.muted; font.family: backend.pal.font; font.pixelSize: 15; wrapMode: Text.WordWrap
            Layout.fillWidth: true; lineHeight: 1.3
        }
    }

    RowLayout {
        Layout.fillWidth: true
        Layout.topMargin: 8
        spacing: 12

        Step {
            number: 1
            done: backend.loggedIn
            title: "Apple ID"
            sub: backend.loggedIn ? backend.account : "войдите в аккаунт, где были приложения"
            onClicked: backend.openLogin()
        }
        Step {
            number: 2
            done: backend.deviceState === "ok"
            warn: backend.deviceState === "trust"
            title: backend.deviceState === "ok" ? "iPhone подключён" : "Подключить iPhone"
            sub: backend.deviceState === "none" ? "подключите кабелем и нажмите «Доверять»" : backend.deviceText
            onClicked: backend.connectDevice()
        }
        Step {
            number: 3
            main: true
            title: "Найти мои приложения"
            sub: "проверим историю Apple ID"
            onClicked: backend.findMine()
        }
    }

    Rectangle {
        visible: backend.deviceState !== "ok"
        Layout.fillWidth: true
        implicitHeight: hintCol.implicitHeight + 24
        radius: 16
        color: backend.pal.accentSoft
        border.color: backend.pal.accentDim
        ColumnLayout {
            id: hintCol
            anchors.left: parent.left; anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            anchors.leftMargin: 16; anchors.rightMargin: 16
            spacing: 10
            Text {
                text: "Не видно iPhone? Установите «Устройства Apple» из Microsoft Store, подключите кабель и нажмите «Доверять» на телефоне."
                color: backend.pal.text; font.family: backend.pal.font; font.pixelSize: 14
                wrapMode: Text.WordWrap; Layout.fillWidth: true; lineHeight: 1.3
            }
            Btn {
                text: "Открыть Microsoft Store"; kind: "primary"; lock: false
                implicitHeight: 36
                onClicked: backend.openAppleDevicesStore()
            }
        }
    }

    RowLayout {
        Layout.topMargin: 16
        Text { text: "Популярное"; color: backend.pal.text; font.family: backend.pal.font; font.pixelSize: 20; font.weight: Font.Bold }
        Item { Layout.fillWidth: true }
        Text {
            text: "Весь каталог"
            color: allHover.hovered ? backend.pal.accent : backend.pal.accentText
            font.family: backend.pal.font; font.pixelSize: 14; font.weight: Font.DemiBold
            HoverHandler { id: allHover; cursorShape: Qt.PointingHandCursor }
            TapHandler { onTapped: backend.showPage("apps") }
        }
    }

    GridView {
        id: grid
        Layout.fillWidth: true
        Layout.fillHeight: true
        clip: true
        model: backend.popular
        readonly property int cols: Math.max(4, Math.floor(width / 128))
        cellWidth: Math.floor(width / cols)
        cellHeight: 136
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: ThinScrollBar {}
        delegate: Item {
            id: cell
            required property int index
            required property var model
            width: grid.cellWidth; height: grid.cellHeight
            AppTile {
                anchors.fill: parent; anchors.margins: 4
                index: cell.index
                appId: cell.model.appId; title: cell.model.title; letter: cell.model.letter
                tint: cell.model.tint; icon: cell.model.icon; status: cell.model.status
                statusKind: cell.model.statusKind; selected: cell.model.selected; copies: cell.model.copies
            }
        }
    }

    component Step: Rectangle {
        id: step
        property int number: 1
        property bool done: false
        property bool warn: false
        property bool main: false
        property string title: ""
        property string sub: ""
        signal clicked()
        Layout.fillWidth: true
        Layout.preferredWidth: 1
        implicitHeight: 128
        radius: 16
        color: main ? (stepHover.hovered ? backend.pal.accentHover : backend.pal.accent) : (stepHover.hovered ? backend.pal.cardHover : backend.pal.card)
        border.color: main ? "transparent" : (done ? backend.pal.okDim : backend.pal.border)
        scale: stepTap.pressed ? 0.98 : 1
        Behavior on color { ColorAnimation { duration: 130 } }
        Behavior on scale { NumberAnimation { duration: 90 } }
        HoverHandler { id: stepHover; cursorShape: Qt.PointingHandCursor }
        TapHandler { id: stepTap; onTapped: step.clicked() }

        ColumnLayout {
            anchors.fill: parent; anchors.margins: 16
            spacing: 8
            Rectangle {
                width: 28; height: 28; radius: 8
                color: step.main ? Qt.rgba(1, 1, 1, 0.2) : step.done ? backend.pal.okBg : step.warn ? backend.pal.warnDim : backend.pal.second
                Text {
                    anchors.centerIn: parent
                    text: step.done ? "✓" : step.number
                    color: step.main ? "white" : step.done ? backend.pal.ok : step.warn ? backend.pal.warn : backend.pal.muted
                    font.family: backend.pal.font; font.pixelSize: 14; font.weight: Font.ExtraBold
                }
            }
            Text { text: step.title; color: step.main ? "white" : backend.pal.text; font.family: backend.pal.font; font.pixelSize: 16
                   font.weight: Font.Bold; wrapMode: Text.WordWrap; maximumLineCount: 2; elide: Text.ElideRight; Layout.fillWidth: true }
            Text { textFormat: Text.PlainText; text: step.sub; color: step.main ? Qt.rgba(1, 1, 1, 0.88) : step.warn ? backend.pal.warn : backend.pal.muted
                   font.family: backend.pal.font; font.pixelSize: 13; wrapMode: Text.WordWrap; maximumLineCount: 3
                   elide: Text.ElideRight; Layout.fillWidth: true }
        }
    }
}
