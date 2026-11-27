import QtQuick

Rectangle {
    id: c
    property bool checked: false
    signal toggled()
    width: 22; height: 22; radius: 6
    color: checked ? backend.pal.accent : backend.pal.card
    border.color: checked ? backend.pal.accent : (area.containsMouse ? backend.pal.accent : backend.pal.borderLight)
    border.width: 2
    Behavior on color { ColorAnimation { duration: 120 } }
    Text { anchors.centerIn: parent; text: "✓"; color: "white"; font.pixelSize: 15; font.bold: true; visible: c.checked }
    MouseArea {
        id: area
        anchors.fill: parent
        anchors.margins: -6
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: c.toggled()
    }
}
