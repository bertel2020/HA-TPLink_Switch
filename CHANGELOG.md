# Änderungsverlauf

Alle nennenswerten Änderungen an dieser Integration werden hier festgehalten.

## 0.9.0 – 2026-11-05

### Neu

- **Schleifenerkennung:** Pro Port, an dem die Schleifenerkennung des Switches eingeschaltet ist, gibt es einen Binärsensor **Port N Schleife** (Problem; Attribut `blocked`, wenn der Switch den Port gesperrt hat). Das Panel zeigt einen Hinweis und eine Markierung in der Karte des Ports. Die Werte stammen aus der TP-Link-MIB des TL-SG3424 und sind noch nicht an echter Hardware geprüft; fehlt die Tabelle, gibt es die Sensoren einfach nicht. Neue Gruppe „Schleife erkannt“ in den Optionen (wer die Auswahl schon gespeichert hat, wählt sie dort nach).
- **Port-Einstellung im Panel:** Das Panel liest aus der TP-Link-Tabelle, wie ein Port eingestellt ist (Auto-Aushandlung oder fest auf 10/100/1000 Mbit/s mit Duplex), die Flusssteuerung und den Trunk. Ein Port mit fester Einstellung bekommt in der Karte eine Markierung und einen Hinweis auf der Übersicht, denn die Gegenstelle muss dann genauso eingestellt sein. Ein Trunk wird ebenfalls markiert. Das erklärt oft Ports, die nur mit 100 Mbit/s laufen. Auch das ist noch nicht an echter Hardware geprüft.
- **MAC-Sicherheit:** Hat ein Port die Port-Security des Switches eingeschaltet und so viele MAC-Adressen gelernt, wie er darf, markiert das Panel ihn und zeigt einen Hinweis auf der Übersicht: Ein weiteres Gerät kommt an diesem Port nicht ins Netz. Noch nicht an echter Hardware geprüft.
- **Storm-Control und Einstellungen in der Port-Karte:** Die Karte beim Überfahren eines Ports zeigt zusätzlich die Storm-Control-Grenzen (Broadcast, Multicast, Unicast), die Flusssteuerung und die gelernten gegenüber den erlaubten MAC-Adressen, soweit der Switch sie meldet.
- **Alarme des Switches:** Mit eingeschaltetem Trap-Empfang löst ein Trap für CPU- oder Speicherlast über 80 %, eine Schleife oder ein Storm-Control-Limit das Ereignis `tplink_switch_snmp_alarm` aus (mit Text im Logbuch). Die Abfrage danach läuft wie bisher sofort.
- **Fehler im Detail:** Der Switch zählt über RMON (`etherStats`) CRC-Fehler, Kollisionen, zu kurze und zu lange Pakete, Fragmente und Jabber je Port. Sie gibt es als Diagnose-Sensoren (standardmäßig aus, nur an Ports, für die der Switch Werte meldet; neue Gruppe „Fehler im Detail“) und in der Port-Karte. Die Diagnose-Tabelle sagt dann genauer, was zu prüfen ist: Kollisionen deuten auf eine Duplex-Abweichung, CRC-Fehler und Fragmente auf das Kabel. Noch nicht an echter Hardware geprüft.
- **Spanning Tree:** Das Panel markiert Ports mit Link, die der Spanning Tree gerade nicht nutzt (blockiert, hört zu, lernt), und erklärt auf der Übersicht, dass das bei einem Reservekabel gewollt ist. Dazu gibt es den Diagnose-Sensor **STP-Topologieänderungen** (standardmäßig aus, neue Gruppe „STP“) und das Ereignis `tplink_switch_snmp_alarm` mit `stp_topology_change`, wenn der Zähler steigt. Gelesen wird die Standard-MIB `BRIDGE-MIB`, bei jedem Hersteller.
- **ARP-Schutz:** Hat der Switch die ARP-Erkennung eingeschaltet, gibt es pro Port den Diagnose-Sensor **Unzulässige ARP-Pakete** (standardmäßig aus, nur wo der Switch Werte meldet; neue Gruppe „ARP“). Das Panel zeigt die Zahl in der Port-Karte und warnt auf der Übersicht; steigt sie, löst das Ereignis `tplink_switch_snmp_alarm` mit `arp_illegal`, `port` und `count` aus. Noch nicht an echter Hardware geprüft.
- **VLANs:** Der Switch meldet über die Standard-MIB `Q-BRIDGE-MIB`, zu welchem VLAN ein Port gehört (PVID) und in welchen VLANs er mit und ohne Tag sendet. Es gibt pro Port den Diagnose-Sensor **PVID** mit den Attributen `untagged` und `tagged` (standardmäßig aus, neue Gruppe „VLAN“); das Panel zeigt die Zeile „VLAN“ in der Port-Karte, der Snapshot enthält die VLAN-Namen. Noch nicht an echter Hardware geprüft.
- **Aktionen:** Mit erlaubtem Schreiben gibt es bei einem TP-Link-Switch die Buttons **Konfiguration speichern** (schreibt die laufende Konfiguration in den Flash) und **Neustart** (standardmäßig aus, er trennt alle Geräte für etwa eine Minute). Schlägt die Aktion fehl, etwa weil die Community nur lesen darf, meldet Home Assistant den Fehler. Noch nicht an echter Hardware geprüft.
- **Sicherheitsfunktionen:** Die MIBs von DoS-Schutz, DHCP-Snooping und 802.1X haben keine Zähler, nur Einstellungen. Deshalb gibt es drei Diagnose-Binärsensoren, die zeigen, ob die Funktion am Switch eingeschaltet ist (standardmäßig aus, neue Gruppe „Sicherheit“). Ist DHCP-Snooping an, nennt die Port-Karte im Panel die vertrauenswürdigen Ports. Dazu melden weitere Traps das Ereignis `tplink_switch_snmp_alarm`: `ingress_rate` und `egress_rate` (Bandbreitengrenze überschritten) und `config_changed` (die Konfiguration wurde gespeichert). Noch nicht an echter Hardware geprüft.
- **Port-Spiegelung und Port-Isolation:** Der Diagnose-Binärsensor **Port-Spiegelung** ist an, wenn eine Spiegel-Gruppe läuft (standardmäßig aus, neue Gruppe „Port-Spiegelung“); das Attribut `groups` nennt Monitor-Port und gespiegelte Ports. Das Panel markiert den Monitor-Port und die gespiegelten Ports in der Karte und warnt auf der Übersicht, denn wer am Monitor-Port mitschneidet, sieht deren Verkehr. Ports, die nicht alle anderen erreichen dürfen, bekommen die Markierung „isoliert“. Die Port-Listen der Tabellen („1-5,9“) liest die Integration tolerant. Noch nicht an echter Hardware geprüft.
- **IGMP-Snooping:** Der Switch zählt je Port die IGMP-Pakete. Es gibt die Diagnose-Sensoren **IGMP-Queries**, **IGMP-Reports** (v1 bis v3 zusammen), **IGMP-Leaves** und **IGMP-Fehlerpakete** sowie den Binärsensor **IGMP-Snooping** (alle standardmäßig aus, nur wo der Switch Werte meldet; neue Gruppe „IGMP“). Ein Port mit Queries hängt an einem Multicast-Router; Fehlerpakete deuten auf ein Gerät, das IGMP falsch spricht. Die Zahlen stehen auch in der Port-Karte des Panels. Noch nicht an echter Hardware geprüft.
- **QoS:** Der Switch meldet die Priorität (CoS 0 bis 7), die ein Port seinen Paketen gibt, wie er seine Warteschlangen bedient (strikte Priorität, gewichtet, gemischt, gleichmäßig) und ob die DSCP-Priorisierung an ist. Das gibt es als Diagnose-Sensoren **QoS-Priorität** und **QoS-Scheduler** sowie als Binärsensor **DSCP-Priorisierung** (alle standardmäßig aus; neue Gruppe „QoS“). Das Panel nennt eine vom Standard abweichende Priorität in der Port-Karte. Noch nicht an echter Hardware geprüft.

## 0.8.0 – 2026-11-04

### Neu

- **Panel:** Beim Überfahren eines Ports erscheint eine Karte mit Link und Geschwindigkeit, Empfang und Senden samt Auslastung, Fehlern, letztem Link-Wechsel und den Geräten am Port. Sie erscheint auch bei Tastatur-Fokus und bleibt beim Aktualisieren stehen.
- **Entitäten wählbar:** In den Optionen legst du fest, welche Gruppen von Entitäten angelegt werden (Link, Datenraten, Geschwindigkeit, Datenmenge, Fehler, Pakete, Auslastung, Link-Wechsel, MAC-Adressen, Laufzeit, Port von Geräten) und für welche Ports. Abgewählte Entitäten werden aus der Registry entfernt. Ohne Auswahl bleibt alles wie bisher.

## 0.7.0 – 2026-11-04

### Neu

- **Reparaturmeldung:** Antwortet der Switch zehn Minuten lang nicht, meldet Home Assistant das unter *Einstellungen → Reparaturen*; die Meldung verschwindet, sobald er wieder antwortet.
- **Panel:** Ein Port lässt sich in der Port-Ansicht ein- und ausschalten (nur wenn das Schreiben in den Optionen erlaubt ist), mit Rückfrage vor dem Ausschalten. Geschützte Ports sind gesperrt und sagen warum. Neuer Websocket-Befehl `tplink_switch_snmp/set_port_enabled`, nur für Administratoren; der Snapshot enthält `protected` pro Port.

### Behoben

- Hinweise im Panel sagen „1 Port“ statt „1 Ports“, auf Deutsch und Englisch.
- Auf dem Handy bricht die Statistik in der Kopfkarte nicht mehr mit übrig gebliebenen Trennlinien um, sondern steht in zwei Spalten. Alle vier Reiter laufen bei allen drei Schriftgrößen ohne seitliches Überlaufen.
- Der Sensor **Port von …** eines Geräts, das in Home Assistant gelöscht wurde, wird entfernt, auch wenn das beim ausgeschalteten Switch geschah.

### Geändert

- Schemas nutzen `probatio` wie Home Assistant seit 2026.10 (vorher `voluptuous`; beide sind dort derselbe Code).
- Typprüfung mit `mypy` (streng) in der CI, Testabdeckung 100 % (die CI verlangt mindestens 98 %), `quality_scale.yaml` entsprechend aktualisiert. Typfehler, die das fand, sind behoben.

## 0.6.0 – 2026-11-04

### Neu

- **Dashboard-Karte** `custom:tplink-switch-card`: die Frontplatte des Switches nach Link-Geschwindigkeit eingefärbt und pro aktivem Port die Geräte, die Home Assistant kennt, mit Datenrate. Klicks öffnen die Entität. Die Karte liest die Entitäten der Integration, sie funktioniert also auch für Benutzer ohne Administratorrechte. Die Port-Entitäten haben dafür das Attribut `port`.
- **Schreiben am Switch** (Option, standardmäßig aus): ein Schalter **Port N aktiv** pro Port (`ifAdminStatus`) und die Möglichkeit, Port-Namen am Switch zu speichern (`ifAlias`). v1 und v2c brauchen eine Community mit Schreibrecht. Uplinks (mindestens 10 gelernte MAC-Adressen) und gewählte **geschützte Ports** werden nie ausgeschaltet. Nicht an echter Hardware getestet: Die Community des Test-Switches darf nur lesen.
- **Namen vom Switch:** Die Port-Namen, die am Switch stehen (`ifAlias`), sind die Vorgabe im Panel, in Ereignissen und Logbuch; ein Name aus dem Panel hat Vorrang. Das Panel zeigt „abgeschaltet“ für Ports, die am Switch ausgeschaltet sind.
- **Geräteinformationen vom Switch:** Modell, Hardware- und Firmware-Version sowie Standort und Ansprechpartner werden aus dem Switch gelesen (bei TP-Link aus der eigenen MIB) und am Gerät und in den Details des Panels gezeigt.
- **Mehr Zähler** (standardmäßig aus): Pakete pro Sekunde (Empfang, Senden) sowie Broadcast und Multicast im Empfang. Das Panel zeigt sie in der Diagnose und meldet viel Broadcast (ab 500 Pakete pro Sekunde) als Hinweis auf eine Schleife.
- **Hersteller aus der MAC-Adresse** in der Geräteliste, wenn kein bekanntes Gerät ihn nennt (Herstellerliste von Home Assistant, ohne Internet; zufällige Adressen haben keinen).
- **Panel:** sortierbare Spalten in der Port- und der Geräteliste, **CSV-Export** der angezeigten Auswahl (Semikolon, mit Markierung für Excel, Dezimalkomma auf Deutsch) und ein **Verlauf über 7 Tage** in Stundenwerten neben den 24 Stunden.
- Icons für alle Entitäten, eine `quality_scale.yaml` zur Einordnung, Erklärungen zu jedem Feld der Einrichtung und im README Abschnitte zu Fehlersuche, Anwendungsfällen und Entfernen.

### Behoben

- Die statischen Dateien des Panels und die Karte werden nur einmal registriert. Wurde der letzte Switch entfernt und wieder eingerichtet, hätte die zweite Registrierung scheitern können.

### Bekannte Grenzen

- Das Schreiben am Switch ist nur gegen einen gefälschten Switch geprüft. CPU, Speicher und Temperatur gibt es beim Test-Switch (Firmware 1.11.10) nicht, weder über Standard-MIBs noch in der TP-Link-MIB; die Integration zeigt sie deshalb nicht.

## 0.5.0 – 2026-11-04

### Neu

- Seitenpanel, **Darstellung** (Palette in der Kopfzeile): drei Farbschemen wie im EnOcean-Panel, **Ozean** (wie bisher), **Wald** und **Graphit**, jeweils hell und dunkel (hell oder dunkel folgt auf Wunsch Home Assistant, Standard), dazu drei Schriftgrößen (Klein 12,6 px, Normal 14 px, Groß 16 px; die kleinsten Schriften bleiben bei mindestens 10,5 px). Die Wahl gilt pro Home-Assistant-Benutzer und wird zusätzlich im Browser gemerkt.
- Seitenpanel, **Verlauf ohne Recorder**: Die Integration führt einen eigenen Puffer der Datenraten (24 Stunden in 5-Minuten-Mittelwerten pro Port) und sichert ihn im `.storage`, auch beim Herunterfahren; ein Neustart lässt keine Lücke. Der Verlauf braucht weder den Recorder noch die Sensoren „Empfang“ und „Senden“, beginnt mit dem Start der Integration und wird mit dem Switch gelöscht. Neuer Websocket-Befehl `tplink_switch_snmp/history`.

### Geändert

- Das Panel fragt nicht mehr alle 15 Sekunden nach: Die Integration schickt nach jeder Abfrage des Switches einen Stand an das offene Panel (neuer Websocket-Befehl `tplink_switch_snmp/subscribe`). Nur wenn das Abonnement ausfällt, fragt das Panel selten nach. Ein längeres Abfrageintervall bedeutet dadurch auch weniger Verkehr im Panel.
- `recorder` ist keine Abhängigkeit mehr, und der Snapshot enthält keine Entitäts-IDs der Datenraten mehr (`entities`).

## 0.4.0 – 2026-11-04

### Neu

- **SNMP v1, v2c und v3:** Die Version ist im Einrichtungsdialog wählbar. Bei v3 gibt es Benutzer, Authentifizierung (MD5, SHA, SHA-224/256/384/512) und Verschlüsselung (DES, AES-128/192/256). Beim Neu konfigurieren lässt sich die Version wechseln. Bestehende Einträge bleiben bei v2c. Bei v1 liest die Integration die 32-Bit-Zähler (v1 kennt keine 64-Bit-Zähler) und fragt mit GETNEXT ab.
- **Abfrageintervall** in den Optionen (10 bis 3600 Sekunden, Standard 30), ohne Neuladen übernommen.
- **Verworfene Pakete** (Empfang/Senden) und **Auslastung in Prozent** (Empfang/Senden) als Sensoren, beide standardmäßig ausgeschaltet. Das Panel zeigt die Auslastung in der Portliste und im Port-Detail, die Diagnose die verworfenen Pakete.
- **Link-Wechsel:** Ereignis `tplink_switch_snmp_link_changed` mit Logbuch-Eintrag („Port 12 (AP): link up at 1 Gbit/s“, „link down“, „link was lost and came back“), Sensor **Link geändert** (Zeitstempel, standardmäßig aus) und im Panel die Zeit des letzten Wechsels sowie ein Hinweis auf Ports mit Wechseln in den letzten 24 Stunden. Nach einem Neustart des Switches entstehen keine Ereignisse.
- **Geräte-Zuordnung:** Für jedes Gerät, das Home Assistant über seine MAC-Adresse kennt und das am Switch gelernt wurde, gibt es den Sensor **Port von …** (Port-Nummer, Port-Name im Attribut). Wechselt ein solches Gerät den Port, löst das Ereignis `tplink_switch_snmp_device_moved` aus, mit Logbuch-Eintrag.
- **SNMP-Traps** (v1 und v2c) auf einem Port der Optionen: Ein Trap des Switches löst sofort eine Abfrage aus. Ein Trap zählt nur mit der richtigen Community und von der Adresse des Switches.
- **Diagnosedaten** zum Herunterladen, ohne Adresse, Zugangsdaten, MAC-Adressen und Port-Namen.
- **Englisches README**; das deutsche README erklärt Einrichtung, Optionen, Ereignisse und Traps.

### Geändert

- Der Installationsabschnitt der READMEs mit den Buttons für HACS und die Einrichtung.

### Bekannte Grenzen

- Config-Flow, Optionen, Ereignisse, Traps und Diagnose sind mit einem gefälschten Switch und dem Test-Plugin von Home Assistant geprüft, nicht in einer laufenden Instanz. Gegen den echten Switch geprüft sind Abfragen mit v1 und v2c, die Port-Erkennung und der Trap-Empfang mit `snmptrap`; bei v3 antwortet der Switch, ein eingerichteter Benutzer wurde nicht getestet.

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
