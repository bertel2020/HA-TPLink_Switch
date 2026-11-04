# TP-Link Switch (SNMP)

Liest einen TP-Link JetStream-Switch (getestet mit **TL-SG3424**) lokal per SNMP aus: Link-Status, Geschwindigkeit, Datenrate, Fehler und die gelernten MAC-Adressen pro Port.

## Voraussetzung am Switch

SNMP einschalten (*SNMP → Global Config*), unter *SNMP → Community* eine Community mit Lesezugriff anlegen und die Konfiguration speichern (*System Tools → Save Config*).

## Installation

1. HACS → *Benutzerdefinierte Repositories* → `https://github.com/bertel2020/HA-TPLink_Switch` als *Integration* hinzufügen.
2. Home Assistant neu starten.
3. *Einstellungen → Geräte & Dienste → Integration hinzufügen → TP-Link Switch (SNMP)*, Host und Community eintragen.

Manuell: den Ordner `custom_components/tplink_switch_snmp` nach `config/custom_components/` kopieren.

## Seitenleisten-Panel

Die Integration legt in der Seitenleiste (nur für Administratoren) den Eintrag **Switch** an:

- **Übersicht:** Frontplatte mit allen Ports nach Link-Geschwindigkeit eingefärbt, dazu Port-Detail mit Verlauf der letzten 24 Stunden (aus der Historie von Home Assistant), die Ports mit der meisten Last und Hinweise zu Fehlern und Ports mit nur 100 Mbit/s.
- **Ports:** Tabelle mit Filtern und Suche.
- **Geräte:** die gelernten MAC-Adressen pro Port; Namen und Hersteller kommen von Geräten, die Home Assistant über ihre MAC-Adresse kennt (z. B. aus „FRITZ!Box Netzwerk“).
- **Diagnose:** Fehlerzähler und Datenvolumen pro Port.

Ports lassen sich im Panel umbenennen (Stift neben dem Port-Namen); der Name wird an der Integration gespeichert. Der Verlauf braucht den Recorder und die Sensoren „Empfang“ und „Senden“ des Ports.

Ohne Home Assistant lässt sich das Panel mit Beispieldaten ansehen: `python3 -m http.server 8765` im Repo-Ordner starten und `/scripts/panel-preview/index.html` öffnen (`?dark=1`, `?lang=en`, `?narrow=1`).

## Entitäten

Pro Port: **Link** (binary_sensor), **Empfang**/**Senden** in Mbit/s, **Geschwindigkeit**, **MAC-Adressen** (Anzahl, die Liste steht im Attribut `mac_addresses`). Standardmäßig deaktiviert: Gesamtvolumen und Fehlerzähler. Am Gerät: **Laufzeit**.

Die Datenraten werden aus den 64-Bit-Zählern des Switches berechnet (Abfrage alle 30 Sekunden); nach einem Neustart des Switches fehlt ein Messwert.

## Grenzen

- Es wird nur gelesen (SNMP v1/v2c), nichts am Switch geändert.
- Ports werden an ihrem Namen `port N: …` erkannt, wie ihn die JetStream-Firmware liefert. Switches mit anderer Benennung zeigen keine Ports.
- LLDP-Nachbarn stellt dieser Switch per SNMP nicht bereit.
