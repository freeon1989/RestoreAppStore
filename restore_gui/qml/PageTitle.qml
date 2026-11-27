import QtQuick
import QtQuick.Layouts

ColumnLayout {
    property string title: ""
    property string sub: ""
    Layout.fillWidth: true
    spacing: 6
    Text { text: parent.title; color: backend.pal.text; font.family: backend.pal.font; font.pixelSize: 32; font.weight: Font.ExtraBold }
    Text { text: parent.sub; color: backend.pal.muted; font.family: backend.pal.font; font.pixelSize: 15; visible: text !== ""
           wrapMode: Text.WordWrap; Layout.fillWidth: true; lineHeight: 1.25 }
}
