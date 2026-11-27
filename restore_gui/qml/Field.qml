import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

TextField {
    id: f
    Layout.fillWidth: true
    implicitHeight: 46
    leftPadding: 14; rightPadding: 14
    color: backend.pal.text
    placeholderTextColor: backend.pal.muted
    selectionColor: backend.pal.accent
    font.family: backend.pal.font; font.pixelSize: 16
    background: Rectangle {
        radius: 10; color: f.activeFocus ? backend.pal.card : backend.pal.rail
        border.color: f.activeFocus ? backend.pal.accent : backend.pal.border
        border.width: f.activeFocus ? 2 : 1
        Behavior on border.color { ColorAnimation { duration: 150 } }
    }
}
