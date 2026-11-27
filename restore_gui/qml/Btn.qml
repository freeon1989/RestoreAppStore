// Кнопка Ink. kind: primary, second, ghost, danger. lock — блокировать при backend.busy.
import QtQuick
import QtQuick.Controls

Button {
    id: b
    property string kind: "second"
    property bool lock: true
    property real radius: 12
    enabled: !(lock && backend.busy)
    implicitHeight: 40
    leftPadding: 16; rightPadding: 16
    hoverEnabled: true
    font.family: backend.pal.font
    font.pixelSize: 15
    font.weight: kind === "primary" ? Font.Bold : Font.DemiBold
    scale: down ? 0.97 : 1
    Behavior on scale { NumberAnimation { duration: 80 } }

    contentItem: Text {
        text: b.text
        font: b.font
        elide: Text.ElideRight
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        color: !b.enabled ? backend.pal.disabled
             : b.kind === "primary" ? "white"
             : b.kind === "ghost" ? backend.pal.accentText
             : b.kind === "danger" ? backend.pal.danger : backend.pal.text
    }
    background: Rectangle {
        readonly property color soft: b.kind === "danger" ? backend.pal.dangerBg : backend.pal.accentSoft
        radius: b.radius
        color: b.kind === "primary" ? (!b.enabled ? backend.pal.second : b.hovered ? backend.pal.accentHover : backend.pal.accent)
             : b.kind === "second" ? (b.hovered ? backend.pal.secondHover : backend.pal.second)
             : b.hovered ? soft : Qt.rgba(soft.r, soft.g, soft.b, 0)
        Behavior on color { ColorAnimation { duration: 120 } }
    }
    HoverHandler { cursorShape: b.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor }
}
