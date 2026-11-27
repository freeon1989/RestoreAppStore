import QtQuick

Column {
    property string title: ""
    property string sub: ""
    anchors.centerIn: parent
    spacing: 8
    width: Math.min(parent.width - 48, 420)
    Text {
        anchors.horizontalCenter: parent.horizontalCenter
        width: parent.width
        horizontalAlignment: Text.AlignHCenter
        text: parent.title
        color: backend.pal.text
        font.family: backend.pal.font; font.pixelSize: 22; font.weight: Font.ExtraBold
        wrapMode: Text.WordWrap
    }
    Text {
        anchors.horizontalCenter: parent.horizontalCenter
        width: parent.width
        horizontalAlignment: Text.AlignHCenter
        text: parent.sub
        color: backend.pal.muted
        font.family: backend.pal.font; font.pixelSize: 15
        visible: text !== ""
        wrapMode: Text.WordWrap
    }
}
