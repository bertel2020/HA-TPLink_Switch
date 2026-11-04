# TP-Link Switch (SNMP)

<p align="center"><em><a href="README.en.md">English version</a></em></p>

Liest einen TP-Link JetStream-Switch (getestet mit **TL-SG3424**) lokal per SNMP aus: Link-Status, Geschwindigkeit, Datenrate, Auslastung, Fehler, verworfene Pakete und die gelernten MAC-Adressen pro Port. Dazu kommen ein Seitenleisten-Panel, Ereignisse für Link- und Port-Wechsel und auf Wunsch SNMP-Traps für sofortige Meldungen.

## Voraussetzung am Switch

SNMP einschalten (*SNMP → Global Config*) und die Konfiguration speichern (*System Tools → Save Config*). Je nach SNMP-Version:

- **v1 / v2c:** unter *SNMP → Community* eine Community mit Lesezugriff anlegen.
- **v3:** einen Benutzer mit Gruppe, Authentifizierung und, wenn gewünscht, Verschlüsselung anlegen.

## Installation

### Über HACS (empfohlen)

[![HACS-Repository in My Home Assistant öffnen](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=bertel2020&repository=HA-TPLink_Switch&category=integration)
[![TP-Link Switch (SNMP) zu My Home Assistant hinzufügen](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=tplink_switch_snmp)

1. Über den ersten Button das TP-Link-Switch-Repository in HACS öffnen.
2. **TP-Link Switch (SNMP)** herunterladen und Home Assistant neu starten.
3. Über den zweiten Button die Integration hinzufügen. Alternativ in Home
   Assistant **Einstellungen → Geräte & Dienste → Integration hinzufügen →
   TP-Link Switch (SNMP)** öffnen.

Falls der erste Button nicht funktioniert, in HACS unter **Integrationen →
Benutzerdefinierte Repositories** `https://github.com/bertel2020/HA-TPLink_Switch`
als Kategorie **Integration** eintragen.

### Manuell

Das Verzeichnis `custom_components/tplink_switch_snmp` nach
`/config/custom_components/tplink_switch_snmp` kopieren und Home Assistant neu
starten.

## Einrichtung

Im Dialog zuerst **Host**, **Port** (Standard 161) und die **SNMP-Version** wählen, dann je nach Version die **Community** (v1, v2c) oder den **Benutzer** mit Authentifizierung und Verschlüsselung (v3, Schlüssel mit mindestens 8 Zeichen). Der Switch wird an seiner MAC-Adresse erkannt; derselbe Switch lässt sich nicht zweimal einrichten.

Später ändern: **Geräte & Dienste → TP-Link Switch (SNMP) → ⋮ → Neu konfigurieren** für Adresse, Version und Zugangsdaten (es muss derselbe Switch antworten), **Konfigurieren** für die Optionen:

- **Abfrageintervall** (10 bis 3600 Sekunden, Standard 30). Kürzere Abstände geben genauere Datenraten, belasten aber den Switch stärker.
- **Trap-Port** (0 = aus), siehe unten.

## Fehlersuche

- **„Der Switch antwortet nicht“ bei der Einrichtung:** Adresse, Version und Community prüfen, und ob SNMP am Switch eingeschaltet **und gespeichert** ist. Mit `snmpget -v2c -c <Community> <Adresse> 1.3.6.1.2.1.1.1.0` auf dem Rechner mit Home Assistant lässt sich das prüfen. Bei einer falschen Community meldet SNMP nichts zurück, es sieht aus wie ein ausgeschalteter Switch.
- **Entitäten „nicht verfügbar“:** Der Switch hat in zwei Abfragen nacheinander nicht geantwortet. Home Assistant meldet das einmal im Log und fragt weiter.
- **Datenraten fehlen nach dem Start:** Die erste Abfrage hat nichts zum Vergleichen, die Rate erscheint nach der zweiten.
- **Fehler melden:** Diagnosedaten herunterladen (siehe unten) und das Log mit `tplink_switch_snmp` anhängen.

## Anwendungsfälle

- Eine Meldung aufs Handy, wenn die Wallbox oder die Kamera den Link verliert (Ereignis `tplink_switch_snmp_link_changed`).
- Sehen, an welchem Port ein Gerät hängt, und eine Meldung, wenn es den Port wechselt (z. B. ein Access Point, der umgesteckt wurde).
- Ein langsam gewordener Link: Ports mit nur 100 Mbit/s und Fehlerzähler zeigen ein schlechtes Kabel.
- Auslastung eines Uplinks über die Zeit, ohne den Switch selbst zu öffnen.

## Entfernen

*Geräte & Dienste → TP-Link Switch (SNMP) → ⋮ → Löschen.* Der gespeicherte Verlauf wird mit gelöscht. Am Switch ändert sich nichts; SNMP und die Community bleiben dort eingerichtet. Die Dateien der Integration lassen sich danach in HACS entfernen.

## Seitenleisten-Panel

Die Integration legt in der Seitenleiste (nur für Administratoren) den Eintrag **Switch** an:

- **Übersicht:** Frontplatte mit allen Ports nach Link-Geschwindigkeit eingefärbt (beim Überfahren eines Ports eine Karte mit Geschwindigkeit, Datenrate, Fehlern und Geräten), dazu Port-Detail mit Verlauf der letzten 24 Stunden, Zeit des letzten Link-Wechsels und Auslastung, die Ports mit der meisten Last und Hinweise zu Fehlern, Ports mit nur 100 Mbit/s und Link-Wechseln in den letzten 24 Stunden.
- **Ports:** Tabelle mit Filtern, Suche und Auslastung in Prozent.
- **Geräte:** die gelernten MAC-Adressen pro Port; Namen kommen von Geräten, die Home Assistant über ihre MAC-Adresse kennt (z. B. aus „FRITZ!Box Netzwerk“); der Hersteller von dort oder sonst aus der MAC-Adresse (Herstellerliste von Home Assistant, ohne Internet; zufällige Adressen von Handys haben keinen).
- **Diagnose:** Fehler, verworfene Pakete und Datenvolumen pro Port.

Die **Darstellung** (Palette in der Kopfzeile) bietet drei Farbschemen (Ozean, Wald, Graphit), hell, dunkel oder wie Home Assistant, und drei Schriftgrößen; die Wahl gilt pro Benutzer. Das Panel bekommt nach jeder Abfrage des Switches einen neuen Stand geschickt und fragt nicht selbst nach.

Ports lassen sich im Panel umbenennen (Stift neben dem Port-Namen); der Name wird an der Integration gespeichert. Der Verlauf kommt aus einem eigenen Puffer der Integration (24 Stunden in 5-Minuten-Werten und 7 Tage in Stundenwerten, im `.storage` gesichert), er braucht also weder den Recorder noch die Sensoren; er beginnt mit dem Start der Integration und wird mit dem Switch gelöscht.

Ohne Home Assistant lässt sich das Panel mit Beispieldaten ansehen: `python3 -m http.server 8765` im Repo-Ordner starten und `/scripts/panel-preview/index.html` öffnen (`?dark=1`, `?lang=en`, `?narrow=1`).

## Dashboard-Karte

Die Integration bringt die Karte **TP-Link Switch** mit: die Frontplatte des Switches, nach Link-Geschwindigkeit eingefärbt, und darunter pro aktivem Port die Geräte, die Home Assistant kennt, samt Datenrate. Ein Klick auf einen Port oder ein Gerät öffnet die zugehörige Entität. Anders als das Panel sieht sie jeder Benutzer.

```yaml
type: custom:tplink-switch-card
title: Switch Keller      # optional
device_id: abc123         # optional, nur bei mehreren Switches
show_devices: true        # Geräte pro Port (Standard: an)
show_rates: true          # Datenrate pro Port (Standard: an)
```

Die Karte liest die Entitäten der Integration; die Geräte pro Port sind die Sensoren **Port von …**. Eine Vorschau ohne Home Assistant: `/scripts/panel-preview/card.html`.

## Entitäten

Pro Port:

| Entität | Standard | Hinweis |
| --- | --- | --- |
| **Link** (binary_sensor) | an | |
| **Empfang**, **Senden** (Mbit/s) | an | aus den Zählern des Switches berechnet |
| **Geschwindigkeit** | an | |
| **MAC-Adressen** | an | Anzahl; die Liste steht im Attribut `mac_addresses` |
| **Auslastung Empfang/Senden** (%) | aus | Datenrate im Verhältnis zur Link-Geschwindigkeit |
| **Empfangen/Gesendet gesamt** | aus | Datenvolumen |
| **Empfangsfehler/Sendefehler** | aus | |
| **Empfang/Senden verworfen** | aus | verworfene Pakete |
| **Link geändert** (Zeitstempel) | aus | Zeitpunkt des letzten Link-Wechsels |
| **Pakete/s Empfang/Senden**, **Broadcast/Multicast Empfang** | aus | aus den Paketzählern |
| **Port N aktiv** (switch) | nur mit Schreiben | schaltet den Port ein oder aus |

Am Gerät: **Laufzeit**. Für jedes Gerät, das Home Assistant über seine MAC-Adresse kennt und das am Switch gelernt wurde, kommt ein Sensor **Port von …** dazu: Er zeigt die Port-Nummer, im Attribut `port_name` den Namen des Ports. Der Sensor gehört zum Switch, nicht zum Gerät der anderen Integration, denn ein Gerät gehört in Home Assistant genau einer Integration.

### Welche Entitäten angelegt werden

Unter **Konfigurieren** wählst du, welche Gruppen von Entitäten es gibt (Link, Datenraten, Geschwindigkeit, Datenmenge, Fehler, Pakete, Auslastung, Link-Wechsel, MAC-Adressen, Laufzeit, Port von Geräten) und für welche Ports (leer = alle). Was du abwählst, wird nicht angelegt und aus der Entitäten-Liste entfernt; dabei werden auch deren Verlaufsdaten in Home Assistant nicht mehr fortgeschrieben. Das Panel ist nicht betroffen, es liest direkt vom Switch.

## Ereignisse und Logbuch

Beide Ereignisse erscheinen im Logbuch und lassen sich in Automationen als Auslöser verwenden:

- `tplink_switch_snmp_link_changed`: Ein Link hat gewechselt. Daten: `port`, `port_name`, `up`, `speed`, `flap` (der Link fiel zwischen zwei Abfragen aus und kam wieder), `switch`, `entry_id`, `entity_id`. Nach einem Neustart des Switches gibt es keine Ereignisse.
- `tplink_switch_snmp_device_moved`: Ein Gerät, das Home Assistant kennt, taucht an einem anderen Port auf. Daten: `mac`, `name`, `device_id`, `from_port`, `from_port_name`, `to_port`, `to_port_name`, `switch`, `entry_id`.

```yaml
triggers:
  - trigger: event
    event_type: tplink_switch_snmp_link_changed
    event_data:
      port: 12
      up: false
```

## Schreiben am Switch (optional)

Standardmäßig liest die Integration nur. In den Optionen lässt sich **Schreiben am Switch erlauben** einschalten; dann gibt es:

- einen Schalter **Port N aktiv** pro Port (`ifAdminStatus`): Aus bedeutet kein Link, egal was angesteckt ist.
- im Panel in der Port-Ansicht der Knopf **Port ausschalten / einschalten** (mit Rückfrage; bei geschützten Ports gesperrt).
- im Panel beim Umbenennen eines Ports das Kästchen **Auch am Switch speichern** (`ifAlias`). Die Namen, die am Switch schon an den Ports stehen, zeigt die Integration ohnehin als Vorgabe; ein Name aus dem Panel hat Vorrang.

Voraussetzungen und Schutz:

- **v1 und v2c** brauchen eine **eigene Community mit Schreibrecht** (am Switch unter *SNMP → Community*, Zugriff *read-write*), die in den Optionen eingetragen wird. **v3** schreibt mit demselben Benutzer, wenn er Schreibrecht hat. Ein Switch antwortet auf einen Schreibversuch einer nur lesenden Community gar nicht; die Integration meldet das als Fehler.
- **Geschützte Ports** schaltet Home Assistant nie aus: die in den Optionen gewählten und immer die, an denen mindestens 10 MAC-Adressen gelernt wurden (meist Uplinks). Wer den Port ausschaltet, über den Home Assistant am Switch hängt, sperrt sich aus. Einschalten geht immer.
- Änderungen gelten am Switch **bis zu seinem Neustart**, wenn du die Konfiguration dort nicht speicherst (*System Tools → Save Config*). Die Integration speichert sie nicht.
- Mit dem Switch aus dem Test (TL-SG3424, Firmware 1.11.10) ist das Schreiben **nicht** ausprobiert: Die dort vorhandene Community darf nur lesen. Getestet ist es gegen einen gefälschten Switch.

## SNMP-Traps für sofortige Meldungen

Standardmäßig fragt Home Assistant den Switch im eingestellten Intervall ab, ein Link-Wechsel zeigt sich also erst bei der nächsten Abfrage. Mit **Trap-Port** in den Optionen empfängt Home Assistant zusätzlich SNMP-Traps (nur v1 und v2c): Sobald ein Trap des Switches eintrifft, folgt sofort eine Abfrage. Der Inhalt des Traps wird nicht ausgewertet.

1. Einen freien UDP-Port wählen, z. B. `1162` (Ports unter 1024 brauchen Rechte), und ihn in den Optionen eintragen. In Docker muss der UDP-Port freigegeben sein.
2. Am Switch unter *SNMP → Notification* die Adresse von Home Assistant mit diesem Port und **derselben Community** als Ziel eintragen.

Ein Trap gilt nur, wenn er von der Adresse des Switches kommt, die beim Start der Integration aufgelöst wurde, und die Community stimmt. Lässt sich der Port nicht öffnen, steht eine Warnung im Log; die Abfrage läuft trotzdem weiter.

## Diagnosedaten

*Geräte & Dienste → TP-Link Switch (SNMP) → ⋮ → Diagnose herunterladen.* Die Datei enthält Version, Zähler, Intervall und den Zustand der Ports, aber keine Adresse, keine Zugangsdaten, keine MAC-Adressen und keine Port-Namen.

## Entwicklung

Mit Python 3.14: `pip install -r requirements-dev.txt`, dann `ruff check .`, `mypy`, `pytest --cov=custom_components/tplink_switch_snmp` (die Abdeckung liegt bei 100 %, die CI verlangt mindestens 98 %) und `node --test tests/js/*.test.mjs`. Die Tests laufen gegen einen gefälschten Switch (`tests/conftest.py`) und das Test-Plugin von Home Assistant.

## Grenzen

- Ohne die Option „Schreiben erlauben“ wird nur gelesen, nichts am Switch geändert.
- **SNMP v1** kennt keine 64-Bit-Zähler: Die Datenraten kommen dann aus 32-Bit-Zählern, die bei 1 Gbit/s alle 34 Sekunden überlaufen, und das Datenvolumen (standardmäßig ausgeschaltet) ist ungenau. Bei einem Intervall über 34 Sekunden geht bei voller Auslastung ein Überlauf verloren, und die Rate fällt zu niedrig aus. Für genaue Werte v2c oder v3 nehmen.
- **SNMP v1 und v2c** schicken die Community im Klartext. v3 ist am echten Switch nur bis zur Anmeldung geprüft (er antwortet), nicht mit einem eingerichteten Benutzer.
- Als Ports gelten die Ports der Bridge-Tabelle des Switches (die Nummer ist die Bridge-Port-Nummer), unabhängig von ihrer Benennung. VLAN-, Loopback- und Management-Schnittstellen sind keine Ports. Getestet ist das nur mit einem TL-SG3424; andere JetStream-Modelle sind nicht geprüft.
- Hersteller und Modell stehen nicht eindeutig im Switch: Der Hersteller kommt aus der Enterprise-Nummer, als Modell dient die Gerätebeschreibung des Switches.
- Die Laufzeit läuft über die 497 Tage hinaus, nach denen der Zähler des Switches überläuft. Startet Home Assistant danach neu, beginnt sie mit dem Wert des Zählers.
- Ein Gerät am Uplink-Port erscheint an dem Port, an dem der Switch seine MAC-Adresse gelernt hat. Wechselt ein Gerät zwischen dem Uplink und einem anderen Port, gilt das als Port-Wechsel.
- LLDP-Nachbarn stellt dieser Switch per SNMP nicht bereit.
