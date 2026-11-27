import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    spacing: 12

    RowLayout {
        Layout.fillWidth: true
        spacing: 12
        PageTitle {
            Layout.fillWidth: true
            title: "Каталог"
            sub: "Поиск по названию, App ID или ссылке App Store. Витрина задаёт страну каталога."
        }
        ComboBox {
            id: storefront
            implicitWidth: 200; implicitHeight: 38
            model: backend.storefronts
            textRole: "title"
            currentIndex: backend.storefrontIndex
            onActivated: backend.setStorefrontIndex(currentIndex)
            font.family: backend.pal.font; font.pixelSize: 13
        }
    }

    TextField {
        id: search
        Layout.fillWidth: true
        Layout.topMargin: 4
        implicitHeight: 46
        leftPadding: 44
        placeholderText: "Например: Сбербанк, 492224193 или ссылка apps.apple.com"
        placeholderTextColor: backend.pal.muted
        color: backend.pal.text
        selectionColor: backend.pal.accent
        font.family: backend.pal.font; font.pixelSize: 16
        onTextChanged: debounce.restart()
        Timer { id: debounce; interval: 180; onTriggered: { backend.setQuery(search.text); list.positionViewAtBeginning() } }
        background: Rectangle {
            radius: 10; color: backend.pal.card
            border.color: search.activeFocus ? backend.pal.accent : backend.pal.border
            border.width: search.activeFocus ? 2 : 1
            Behavior on border.color { ColorAnimation { duration: 150 } }
            Text { text: "⌕"; color: backend.pal.muted; font.pixelSize: 18; x: 16; anchors.verticalCenter: parent.verticalCenter }
            Text {
                visible: search.text !== ""
                text: "✕"; color: clearHover.hovered ? backend.pal.text : backend.pal.muted; font.pixelSize: 16
                anchors.right: parent.right; anchors.rightMargin: 16; anchors.verticalCenter: parent.verticalCenter
                HoverHandler { id: clearHover; cursorShape: Qt.PointingHandCursor }
                TapHandler { onTapped: search.clear() }
            }
        }
    }

    Item {
        Layout.fillWidth: true
        implicitHeight: 36
        clip: true
        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: backend.pal.border }
        ListView {
            anchors.fill: parent
            orientation: ListView.Horizontal
            spacing: 22
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            flickableDirection: Flickable.HorizontalFlick
            interactive: true
            model: backend.categories
            ScrollBar.horizontal: ScrollBar {
                policy: parent.contentWidth > parent.width ? ScrollBar.AsNeeded : ScrollBar.AlwaysOff
                height: 4
            }
            delegate: Item {
                id: cat
                required property string modelData
                readonly property bool on: modelData === backend.category
                height: 36
                width: catText.implicitWidth
                Text { id: catText; anchors.verticalCenter: parent.verticalCenter; anchors.verticalCenterOffset: -2
                       text: cat.modelData; font.family: backend.pal.font; font.pixelSize: 15
                       font.weight: cat.on ? Font.Bold : Font.Medium
                       color: cat.on ? backend.pal.text : (catHover.hovered ? backend.pal.text : backend.pal.muted) }
                Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 2; radius: 1
                            color: backend.pal.accent; visible: cat.on }
                HoverHandler { id: catHover; cursorShape: Qt.PointingHandCursor }
                TapHandler { onTapped: { backend.setCategory(cat.modelData); list.positionViewAtBeginning() } }
            }
        }
    }

    RowLayout {
        Layout.fillWidth: true
        Layout.topMargin: 2
        spacing: 8
        BusyIndicator { visible: backend.catalogLoading; running: visible; implicitWidth: 16; implicitHeight: 16 }
        Text {
            text: backend.catalogLoading ? "Загружаю каталог…"
                : (backend.catalogError !== "" ? backend.catalogError : ("Найдено: " + list.count))
            color: backend.catalogError !== "" ? backend.pal.warn : backend.pal.muted
            font.family: backend.pal.font; font.pixelSize: 13
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }
    }

    AppsList {
        id: list
        Layout.fillWidth: true
        Layout.fillHeight: true
        listName: "apps"
        model: backend.apps
        emptyTitle: backend.catalogLoading ? "Загружаю…" : (backend.catalogError !== "" ? "Каталог недоступен" : "Ничего не нашлось")
        emptySub: backend.catalogLoading ? "Запрашиваю приложения в App Store."
                : (backend.catalogError !== "" ? backend.catalogError : "Попробуйте App ID или ссылку App Store.")
    }
}
