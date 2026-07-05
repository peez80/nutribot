# Spezifikation: KI-Ernährungstagebuch Web-App

## 1. Einleitung
Die Anwendung ist ein KI-gestütztes Ernährungstagebuch. Ziel ist es, dem Benutzer eine einfache und intuitive Möglichkeit zu bieten, seine Mahlzeiten und eventuell auftretende Symptome zu erfassen. Die Erfassung erfolgt über ein Chat-Interface, das eine natürliche Interaktion ermöglicht.

## 2. Hauptfunktionen

### 2.1 Chat-Interface
- Die zentrale Benutzeroberfläche der Anwendung ist ein Chat.
- Der Benutzer kann hier wie in einer Messenger-App Eingaben tätigen und sieht den Verlauf.
- **Responsive Layout:** Die Chat-Oberfläche muss sowohl auf Desktop-Rechnern als auch auf mobilen Endgeräten (Smartphones, Tablets) optimal dargestellt werden und nutzbar sein.

### 2.2 Eingabe von Mahlzeiten
- **Texteingabe:** Der Benutzer kann in natürlicher Sprache eingeben, was er gegessen oder getrunken hat (z. B. "Ich habe heute Morgen zwei Brötchen mit Marmelade und einen Kaffee mit Milch gehabt").
- **Kamera-Integration (Smartphone):** Öffnet der Benutzer die Web-App auf dem Smartphone, kann er direkt über die Kamerafunktion des Geräts Fotos der Mahlzeiten aufnehmen.
- **Foto-Upload (Galerie/Dateisystem):** Zusätzlich können bereits vorhandene Fotos direkt in den Chat hochgeladen werden.
- Bei Bildeingaben wird die KI genutzt, um die Fotos zu analysieren und die Mahlzeiten automatisch zu extrahieren.

### 2.3 Eingabe von Symptomen
- Der Benutzer kann über den Chat auch körperliche Symptome erfassen (z. B. "Ich habe seit einer Stunde Bauchschmerzen" oder "Mir ist etwas übel").
- Ziel ist es, diese Symptome später mit den aufgenommenen Mahlzeiten korrelieren zu können.

### 2.4 KI-Backend (`antigravity-cli`)
- Die Verarbeitung der Eingaben (Textverständnis, Bilderkennung und Antwortgenerierung) erfolgt über das Kommandozeilen-Tool `antigravity-cli` (Kommando: `agy`).
- Die Python Web-App ruft das Tool lokal via Shell / Subprocess (`subprocess.run` o.ä.) auf, übergibt den Kontext (Text oder Dateipfad zum Bild) und wertet die Ausgabe aus.
- Das Backend muss die Eingaben in strukturierte Daten (Lebensmittel, Symptome) umwandeln und eine freundliche Antwort für den Chat generieren.

## 3. Technische Anforderungen

### 3.1 Technologie-Stack
- **Backend:** FastAPI (Python).
- **Frontend:** Unkompliziertes Setup, z. B. Vanilla HTML/JS/CSS (ggf. mit Jinja2-Templates), um die Komplexität gering zu halten.
- **KI-Integration:** Ausführen von Shell-Kommandos (`agy`) aus dem Backend heraus.

### 3.2 Infrastruktur & Deployment (Full-Docker Setup)
- Die gesamte Anwendung wird per Docker deployed.
- **Entwicklung & Administration:** Es handelt sich um ein Full-Docker Setup. Alle administrativen oder entwicklungsbezogenen lokalen Aktivitäten werden im Docker-Container ausgeführt. Auf dem Host-System (Entwickler-Laptop) muss kein spezielles Python installiert werden.

### 3.3 Datenhaltung
- **Speicherort:** Der Docker-Container erhält ein Volume-Mount sowie eine zugehörige Environment-Variable (z. B. `DATA_DIR`), in der der Speicherpfad definiert ist.
- **Format & Struktur:** Pro Eintrag (jede Mahlzeit, jedes Symptom) wird eine eigene JSON-Datei angelegt.
- **Ordnerstruktur:** Die JSON-Dateien werden nach Monat gruppiert in Unterverzeichnissen abgelegt (Format: `YYYY-MM`).
- **Dateinamen:** Zur sauberen Sortierung erhält jede JSON-Datei als Präfix einen ISO-Timestamp (z. B. `2026-07-05T21:20:45Z_symptom.json`).

## 4. Gelöste Architektur-Entscheidungen
- **Docker Setup:** Ein einzelner FastAPI-Container wird genutzt, um sowohl die API-Endpunkte bereitzustellen als auch die statischen Frontend-Dateien (HTML/JS/CSS) auszuliefern.
- **JSON Schema:** Es wird ein einheitliches Schema verwendet: `{"type": "meal|symptom", "timestamp": "...", "raw_input": "...", "data": {...}}`.
- **Chat Kontext:** Das Backend pflegt die Chat-Historie und übergibt die letzten N Nachrichten (z.B. 5) als Kontext im Prompt an `agy`.
- **Bildverarbeitung:** Hochgeladene Bilder werden temporär im Container gespeichert (z.B. `/tmp`), der absolute Dateipfad wird an `agy` übergeben und anschließend wird das Bild gelöscht.
- **agy Parameter:** Es wird von Standardparametern (`--prompt` und `--image`) ausgegangen. Der Aufruf wird in einer eigenen Python-Klasse gekapselt, um ihn später leicht anpassen zu können.
