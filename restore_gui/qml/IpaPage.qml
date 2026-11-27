import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    spacing: 12

    PageTitle { title: "Файлы .ipa"; sub: "Поставить готовый файл без Apple ID. Скачанное программой тоже хранится здесь." }

    RowLayout {
        Layout.topMargin: 4
        spacing: 8
        Btn { text: "Выбрать .ipa с диска…"; kind: "primary"; onClicked: backend.installFile() }
        Btn { text: "Открыть папку с IPA"; lock: false; onClicked: backend.openFolder() }
        Btn {
            visible: backend.leftoverCount > 0
            text: "Удалить незавершённые"
            kind: "ghost"; lock: false
            onClicked: backend.cleanLeftovers()
        }
    }
    Text {
        visible: backend.leftoverCount > 0
        text: backend.leftoverHint
        color: backend.pal.warn; font.family: backend.pal.font; font.pixelSize: 13
        wrapMode: Text.WordWrap; Layout.fillWidth: true
    }
    Text {
        text: backend.ipaDir
        textFormat: Text.PlainText
        color: backend.pal.muted; font.family: backend.pal.font; font.pixelSize: 13
        wrapMode: Text.WrapAnywhere; Layout.fillWidth: true
    }
    Text { text: "Если файл скачан с чужого Apple ID, при первом запуске приложение попросит пароль того аккаунта."
           color: backend.pal.muted; font.family: backend.pal.font; font.pixelSize: 13; wrapMode: Text.WordWrap; Layout.fillWidth: true }

    Item {
        Layout.fillWidth: true
        Layout.fillHeight: true
        Layout.topMargin: 4
        Rectangle {
            width: parent.width
            height: Math.min(parent.height, files.count * 72 + 8)
            visible: files.count > 0
            radius: 14
            color: backend.pal.card

            ListView {
                id: files
                anchors.fill: parent
                anchors.margins: 4
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                model: backend.ipaFiles
                ScrollBar.vertical: ThinScrollBar {}
                delegate: Rectangle {
                    id: row
                    required property int index
                    required property string path
                    required property string title
                    required property string info
                    required property string letter
                    required property string tint
                    required property string icon
                    width: ListView.view.width - 10
                    height: 72; radius: 10
                    color: rowHover.hovered ? backend.pal.cardHover : backend.pal.card
                    Behavior on color { ColorAnimation { duration: 110 } }
                    HoverHandler { id: rowHover }
                    Rectangle {
                        visible: row.index < files.count - 1 && !rowHover.hovered
                        anchors.bottom: parent.bottom
                        x: 14 + 40 + 12
                        width: parent.width - x - 12; height: 1
                        color: backend.pal.border
                    }
                    RowLayout {
                        anchors.fill: parent; anchors.leftMargin: 14; anchors.rightMargin: 10
                        spacing: 12
                        AppIcon { icon: row.icon; letter: row.letter; tint: row.tint; size: 40 }
                        ColumnLayout {
                            Layout.fillWidth: true; spacing: 1
                            Text { textFormat: Text.PlainText; text: row.title; color: backend.pal.text; font.family: backend.pal.font; font.pixelSize: 15
                                   font.weight: Font.DemiBold; elide: Text.ElideMiddle; Layout.fillWidth: true }
                            Text { text: row.info; color: backend.pal.muted; font.family: backend.pal.font; font.pixelSize: 13 }
                        }
                        Btn { text: "Установить"; kind: "ghost"; implicitHeight: 34; onClicked: backend.installIpa(row.path) }
                    }
                }
            }
        }
        Empty { visible: files.count === 0; title: "Здесь появятся скачанные .ipa"
                sub: "Скачайте приложение или выберите файл с диска." }
    }
}
