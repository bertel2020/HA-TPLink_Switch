# TP-Link Switch (SNMP)

Liest einen TP-Link JetStream-Switch (getestet mit **TL-SG3424**) lokal per SNMP aus: Link-Status, Geschwindigkeit, Datenrate, Fehler und die gelernten MAC-Adressen pro Port.

## Voraussetzung am Switch

SNMP einschalten (*SNMP → Global Config*), unter *SNMP → Community* eine Community mit Lesezugriff anlegen und die Konfiguration speichern (*System Tools → Save Config*).

## Installation

1. HACS → *Benutzerdefinierte Repositories* → `https://github.com/bertel2020/HA-TPLink_Switch` als *Integration* hinzufügen.
2. Home Assistant neu starten.
3. *Einstellungen → Geräte & Dienste → Integration hinzufügen → TP-Link Switch (SNMP)*, Host und Community eintragen.

Manuell: den Ordner `custom_components/tplink_switch_snmp` nach `config/custom_components/` kopieren.

## Entitäten

Pro Port: **Link** (binary_sensor), **Empfang**/**Senden** in Mbit/s, **Geschwindigkeit**, **MAC-Adressen** (Anzahl, die Liste steht im Attribut `mac_addresses`). Standardmäßig deaktiviert: Gesamtvolumen und Fehlerzähler. Am Gerät: **Laufzeit**.

Die Datenraten werden aus den 64-Bit-Zählern des Switches berechnet (Abfrage alle 30 Sekunden); nach einem Neustart des Switches fehlt ein Messwert.

## Grenzen

- Es wird nur gelesen (SNMP v1/v2c), nichts am Switch geändert.
- Ports werden an ihrem Namen `port N: …` erkannt, wie ihn die JetStream-Firmware liefert. Switches mit anderer Benennung zeigen keine Ports.
- LLDP-Nachbarn stellt dieser Switch per SNMP nicht bereit.
