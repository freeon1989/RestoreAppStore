import QtQuick
import QtQuick.Layouts

Rectangle {
    id: row
    required property int index
    required property var appId
    required property string title
    required property string sub
    required property string letter
    required property string tint
    required property string icon
    required property string status
    required property string statusKind
    required property bool selected
    property string listName: "apps"
    readonly property bool last: ListView.view ? index === ListView.view.count - 1 : true

    width: ListView.view ? ListView.view.width - 10 : 600
    height: 72
    radius: 10
    color: selected ? backend.pal.accentSoft : (hover.hovered ? backend.pal.cardHover : backend.pal.card)
    Behavior on color { ColorAnimation { duration: 110 } }

    HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
    TapHandler { id: tap; onTapped: backend.openDetail(row.listName, row.index) }

    Rectangle {
        visible: !row.last && !row.selected && !hover.hovered
        anchors.bottom: parent.bottom
        x: 14 + 22 + 12 + 42 + 12
        width: parent.width - x - 12; height: 1
        color: backend.pal.border
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 14
        anchors.rightMargin: 14
        spacing: 12
        CheckDot { checked: row.selected; onToggled: backend.toggleSelected(row.listName, row.index) }
        AppIcon {
            icon: row.icon; letter: row.letter; tint: row.tint
            scale: tap.pressed ? 0.94 : 1
            Behavior on scale { NumberAnimation { duration: 90 } }
        }
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 1
            Text { textFormat: Text.PlainText; text: row.title; color: backend.pal.text; font.family: backend.pal.font; font.pixelSize: 15; font.weight: Font.DemiBold
                   elide: Text.ElideRight; Layout.fillWidth: true }
            Text { textFormat: Text.PlainText; text: row.sub; color: backend.pal.muted; font.family: backend.pal.font; font.pixelSize: 13
                   visible: text.length > 0; elide: Text.ElideRight; Layout.fillWidth: true }
        }
        Text {
            visible: row.status !== ""
            textFormat: Text.PlainText
            text: row.status
            font.family: backend.pal.font; font.pixelSize: 13; font.weight: Font.DemiBold
            color: row.statusKind === "ok" ? backend.pal.ok : backend.pal.muted
        }
        Text { text: "›"; color: hover.hovered ? backend.pal.accentText : backend.pal.disabled; font.pixelSize: 20 }
    }
}
