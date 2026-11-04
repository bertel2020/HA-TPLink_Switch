# Änderungsverlauf

Alle nennenswerten Änderungen an dieser Integration werden hier festgehalten.

## 0.3.0 – 2026-11-04

### Neu

- **Neu konfigurieren:** Adresse, Community und Port eines eingerichteten Switches lassen sich ändern, ohne ihn zu löschen. Antwortet unter der neuen Adresse ein anderer Switch, bricht der Dialog ab.

### Geändert

- Hersteller und Modell des Geräts kommen aus dem Switch (Enterprise-Nummer und Gerätebeschreibung) und sind nicht mehr fest auf „TL-SG3424“ gesetzt. Das Panel zeigt sie in den Details.
- Als Ports gelten die Ports der Bridge-Tabelle des Switches, nicht mehr die Schnittstellen, deren Name mit „port“ beginnt. Damit werden auch Modelle mit anderer Benennung erkannt, und die VLAN-Schnittstelle zählt nie als Port. Beim TL-SG3424 bleiben Port-Nummern und Entitäts-IDs gleich.

### Behoben

- Die Laufzeit läuft weiter, wenn der Zähler des Switches nach 497 Tagen überläuft, und beginnt nur nach einem echten Neustart von vorn.
- Die Namen von Geräten im Panel nutzen die aktuelle Abfrage der Geräte-Registry von Home Assistant, die ältere ist seit 2026.10 veraltet.
- Das README nannte SNMP v1/v2c; unterstützt wird nur v2c.

## 0.2.0 – 2026-11-04

### Neu

- Seitenleisten-Panel **Switch** (nur für Administratoren) im Look der EnOcean-Eltako-Integration, hell und dunkel nach Home Assistant, Deutsch und Englisch. **Übersicht** mit Frontplatte (Ports nach Link-Geschwindigkeit eingefärbt, Punkt bei Fehlern), Port-Detail mit Verlauf der letzten 24 Stunden, den Ports mit der meisten Last und Hinweisen zu Fehlern und Ports mit nur 100 Mbit/s. **Ports** als Tabelle mit Filtern und Suche, **Geräte** mit den gelernten MAC-Adressen pro Port, **Diagnose** mit Fehlerzählern und Datenvolumen.
- Ports lassen sich im Panel umbenennen; der Name wird an der Integration gespeichert.
- Namen und Hersteller der Geräte kommen von Geräten, die Home Assistant über ihre MAC-Adresse kennt, zum Beispiel aus „FRITZ!Box Netzwerk“.
- Neue Websocket-Befehle `tplink_switch_snmp/snapshot` und `tplink_switch_snmp/set_port_name`, beide nur für Administratoren.
- Vorschau des Panels ohne Home Assistant unter `scripts/panel-preview/`.

### Bekannte Grenzen

- Das Panel wurde bisher nur in der Vorschau mit Beispieldaten geprüft, nicht in einer laufenden Home-Assistant-Instanz.

## 0.1.0 – 2026-11-04

### Neu

- Erste Fassung: liest einen TP-Link JetStream-Switch (getestet mit TL-SG3424) lokal per SNMP v2c aus. Pro Port **Link**, **Geschwindigkeit**, **Empfang** und **Senden** in Mbit/s, **Anzahl der MAC-Adressen** (die Liste steht im Attribut `mac_addresses`); standardmäßig ausgeschaltet sind Gesamtvolumen und Fehlerzähler. Am Gerät die **Laufzeit**.
- Einrichtung im Dialog mit Host, Community und Port; der Switch wird an seiner MAC-Adresse erkannt.
