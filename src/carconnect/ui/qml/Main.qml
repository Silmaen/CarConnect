import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts

ApplicationWindow {
    id: win

    visible: true
    width: 1100
    height: 760
    minimumWidth: 900
    minimumHeight: 600
    title: "CarConnect"
    color: "#0f1218"

    Material.theme: Material.Dark
    Material.accent: "#00c2ff"

    Connections {
        target: backend
        function onDevicesFound() { devicePopup.open() }
    }

    header: Rectangle {
        height: 64
        color: "#161b24"

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 20
            anchors.rightMargin: 20
            spacing: 12

            Text {
                text: "CarConnect"
                color: "white"
                font.pixelSize: 22
                font.bold: true
            }
            Text {
                text: backend.status
                color: backend.connected ? "#3ddc84" : "#8a93a6"
                font.pixelSize: 14
                Layout.fillWidth: true
                elide: Text.ElideRight
            }
            Button {
                text: backend.scanning ? "Recherche…" : "Rechercher"
                visible: !backend.connected
                enabled: !backend.scanning
                onClicked: backend.autoConnect()
            }
            Button {
                text: "Simulateur"
                visible: !backend.connected
                onClicked: backend.connectSimulator()
            }
            Button {
                text: "Déconnecter"
                visible: backend.connected
                onClicked: backend.disconnectDevice()
            }
        }
    }

    Popup {
        id: devicePopup
        modal: true
        anchors.centerIn: Overlay.overlay
        width: 560
        height: 460
        padding: 16

        ColumnLayout {
            anchors.fill: parent
            spacing: 10

            Text {
                text: backend.scanning ? "Recherche…" : "Appareils Bluetooth détectés"
                color: "white"
                font.pixelSize: 18
                font.bold: true
            }
            ListView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                model: backend.devices
                delegate: ItemDelegate {
                    width: ListView.view.width
                    text: modelData.name + "  ·  " + modelData.address + "  ·  " + modelData.rssi + " dBm"
                          + (modelData.likely ? "   ★ adaptateur probable" : "")
                    onClicked: {
                        devicePopup.close()
                        backend.connectBluetooth(modelData.address)
                    }
                }
            }
            RowLayout {
                Layout.fillWidth: true

                TextField {
                    id: manualAddress
                    placeholderText: "Adresse manuelle AA:BB:CC:DD:EE:FF"
                    Layout.fillWidth: true
                }
                Button {
                    text: "Connecter"
                    enabled: manualAddress.text.length > 0
                    onClicked: {
                        devicePopup.close()
                        backend.connectBluetooth(manualAddress.text)
                    }
                }
                Button {
                    text: "Relancer"
                    enabled: !backend.scanning
                    onClicked: backend.scan()
                }
            }
        }
    }

    Dialog {
        id: confirmClear
        title: "Effacer les codes défaut ?"
        modal: true
        anchors.centerIn: Overlay.overlay
        standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: backend.clearDtcs()

        Label {
            text: "Efface les codes mémorisés et réinitialise les moniteurs de préparation.\nLe voyant moteur peut se rallumer si le défaut persiste."
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        TabBar {
            id: tabs
            Layout.fillWidth: true

            TabButton { text: "Tableau de bord" }
            TabButton { text: "Mesures" }
            TabButton { text: "Bilan" }
            TabButton { text: "Défauts" }
            TabButton { text: "Calculateurs" }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: tabs.currentIndex

            // -- Tableau de bord ------------------------------------------
            Item {
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 20
                    spacing: 16

                    RowLayout {
                        Layout.alignment: Qt.AlignHCenter
                        spacing: 40

                        Gauge {
                            value: backend.values.rpm
                            maxValue: 7000
                            unit: "tr/min"
                            label: "Régime"
                        }
                        Gauge {
                            value: backend.values.speed
                            maxValue: 220
                            unit: "km/h"
                            label: "Vitesse"
                            accent: "#3ddc84"
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 12

                        Tile { label: "Liquide de refroidissement"; value: backend.values.coolant.toFixed(0); unit: "°C" }
                        Tile { label: "Papillon"; value: backend.values.throttle.toFixed(0); unit: "%" }
                        Tile { label: "Charge moteur"; value: backend.values.load.toFixed(0); unit: "%" }
                        Tile { label: "Tension"; value: backend.values.voltage.toFixed(1); unit: "V" }
                    }

                    Text {
                        Layout.fillWidth: true
                        color: "#8a93a6"
                        font.pixelSize: 14
                        text: "VIN : " + (backend.info.vin || "—") + "     ·     Protocole : " + (backend.info.protocol || "—")
                              + "     ·     Voyant moteur : "
                              + (backend.connected ? (backend.info.mil ? "allumé" : "éteint") : "—")
                              + (backend.info.dtcCount ? " (" + backend.info.dtcCount + " code(s))" : "")
                    }

                    Item { Layout.fillHeight: true }
                }
            }

            // -- Mesures -----------------------------------------------------
            Item {
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 20
                    spacing: 10

                    RowLayout {
                        Layout.fillWidth: true

                        Button {
                            text: backend.recording ? "■ Arrêter l'enregistrement" : "● Enregistrer en CSV"
                            enabled: backend.connected
                            onClicked: backend.recording ? backend.stopRecording() : backend.startRecording()
                        }
                        Text {
                            text: backend.recording ? backend.recordingPath : ""
                            color: "#8a93a6"
                            Layout.fillWidth: true
                            elide: Text.ElideMiddle
                        }
                    }

                    ListView {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        spacing: 4
                        model: backend.info.pids
                        delegate: Rectangle {
                            width: ListView.view.width
                            height: 40
                            radius: 8
                            color: "#161b24"

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 14
                                anchors.rightMargin: 14

                                Text {
                                    text: modelData.name
                                    color: "#c9d1e0"
                                    font.pixelSize: 15
                                    Layout.fillWidth: true
                                }
                                Text {
                                    text: (backend.values[modelData.key] !== undefined
                                           ? backend.values[modelData.key].toFixed(1) : "—") + " " + modelData.unit
                                    color: "white"
                                    font.pixelSize: 15
                                    font.bold: true
                                }
                            }
                        }
                    }
                }
            }

            // -- Bilan : moniteurs de préparation et données figées -------------
            Item {
                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 20
                    spacing: 16

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        radius: 12
                        color: "#161b24"

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 8

                            RowLayout {
                                Layout.fillWidth: true
                                Text {
                                    text: "Moniteurs de préparation"
                                    color: "white"
                                    font.pixelSize: 16
                                    font.bold: true
                                    Layout.fillWidth: true
                                }
                                Button { text: "Lire"; enabled: backend.connected; onClicked: backend.readReadiness() }
                            }
                            ListView {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                clip: true
                                model: backend.readiness
                                delegate: RowLayout {
                                    width: ListView.view.width
                                    Text { text: modelData.name; color: "#c9d1e0"; font.pixelSize: 15; Layout.fillWidth: true }
                                    Text {
                                        text: modelData.complete ? "prêt" : "non prêt"
                                        color: modelData.complete ? "#3ddc84" : "#ffb454"
                                        font.pixelSize: 15
                                        font.bold: true
                                    }
                                }
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        radius: 12
                        color: "#161b24"

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 8

                            RowLayout {
                                Layout.fillWidth: true
                                Text {
                                    text: "Données figées"
                                    color: "white"
                                    font.pixelSize: 16
                                    font.bold: true
                                    Layout.fillWidth: true
                                }
                                Button { text: "Lire"; enabled: backend.connected; onClicked: backend.readFreezeFrame() }
                            }
                            Text {
                                Layout.fillWidth: true
                                wrapMode: Text.Wrap
                                color: "#ffb454"
                                text: backend.freeze.empty ? "Aucune donnée figée (pas de défaut mémorisé)"
                                      : (backend.freeze.dtc ? backend.freeze.dtc + " — " + backend.freeze.dtcText : "")
                            }
                            ListView {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                clip: true
                                model: backend.freeze.items
                                delegate: RowLayout {
                                    width: ListView.view.width
                                    Text { text: modelData.name; color: "#c9d1e0"; font.pixelSize: 15; Layout.fillWidth: true }
                                    Text { text: modelData.value + " " + modelData.unit; color: "white"; font.pixelSize: 15; font.bold: true }
                                }
                            }
                        }
                    }
                }
            }

            // -- Défauts -----------------------------------------------------
            Item {
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 20
                    spacing: 12

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        Button { text: "Mémorisés"; enabled: backend.connected; onClicked: backend.readDtcs("stored") }
                        Button { text: "En attente"; enabled: backend.connected; onClicked: backend.readDtcs("pending") }
                        Button { text: "Permanents"; enabled: backend.connected; onClicked: backend.readDtcs("permanent") }
                        Item { Layout.fillWidth: true }
                        Button { text: "Effacer"; enabled: backend.connected; onClicked: confirmClear.open() }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        radius: 12
                        color: "#161b24"

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 8

                            Text {
                                text: "Codes défaut — " + backend.dtcInfo
                                color: "white"
                                font.pixelSize: 16
                                font.bold: true
                            }
                            ListView {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                clip: true
                                spacing: 6
                                model: backend.dtcs
                                delegate: RowLayout {
                                    width: ListView.view.width
                                    spacing: 16

                                    Text {
                                        text: modelData.code
                                        color: "#ffb454"
                                        font.pixelSize: 16
                                        font.family: "monospace"
                                        font.bold: true
                                    }
                                    Text {
                                        text: modelData.text
                                        color: "#c9d1e0"
                                        font.pixelSize: 15
                                        wrapMode: Text.Wrap
                                        Layout.fillWidth: true
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // -- Calculateurs (UDS, lecture seule) -----------------------
            Item {
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 20
                    spacing: 12

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 12

                        Button { text: "Rechercher les calculateurs"; enabled: backend.connected; onClicked: backend.scanModules() }
                        Text { text: backend.scanStatus; color: "#8a93a6"; Layout.fillWidth: true }
                        Text { text: "Lecture seule : aucune écriture, aucun effacement"; color: "#8a93a6" }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: 16

                        Rectangle {
                            Layout.preferredWidth: 280
                            Layout.fillHeight: true
                            radius: 12
                            color: "#161b24"

                            ListView {
                                anchors.fill: parent
                                anchors.margins: 8
                                clip: true
                                model: backend.modules
                                delegate: ItemDelegate {
                                    width: ListView.view.width
                                    text: modelData.label
                                    onClicked: backend.readModule(modelData.tx)
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            radius: 12
                            color: "#161b24"

                            ScrollView {
                                anchors.fill: parent
                                anchors.margins: 16

                                Text {
                                    width: parent.width
                                    text: backend.moduleReport || "Choisis un calculateur dans la liste."
                                    color: "#c9d1e0"
                                    font.pixelSize: 14
                                    font.family: "monospace"
                                    wrapMode: Text.Wrap
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
