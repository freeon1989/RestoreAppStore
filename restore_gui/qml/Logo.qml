// Знак Ink: скруглённый квадрат и стрелка в лоток.
import QtQuick

Rectangle {
    id: logo
    property int size: 40
    width: size; height: size
    radius: Math.round(size * 0.28)
    color: backend.pal.accent
    Canvas {
        id: canvas
        anchors.fill: parent
        onPaint: {
            const c = getContext("2d"), s = width
            c.clearRect(0, 0, s, s)
            c.strokeStyle = "white"
            c.lineWidth = Math.max(2, s * 0.08)
            c.lineCap = "round"
            c.lineJoin = "round"
            c.beginPath()
            c.moveTo(s * 0.5, s * 0.22)
            c.lineTo(s * 0.5, s * 0.55)
            c.moveTo(s * 0.34, s * 0.42)
            c.lineTo(s * 0.5, s * 0.58)
            c.lineTo(s * 0.66, s * 0.42)
            c.moveTo(s * 0.28, s * 0.70)
            c.quadraticCurveTo(s * 0.28, s * 0.80, s * 0.38, s * 0.80)
            c.lineTo(s * 0.62, s * 0.80)
            c.quadraticCurveTo(s * 0.72, s * 0.80, s * 0.72, s * 0.70)
            c.stroke()
        }
        Connections { target: logo; function onColorChanged() { canvas.requestPaint() } }
        Component.onCompleted: requestPaint()
    }
}
