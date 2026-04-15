# Transcribbler — Betatest (macOS)

**Version:** v0.1.0-beta
**Plattform:** macOS 12 Monterey eller nyare, Apple Silicon (M1/M2/M3/M4)
**Repo:** https://github.com/JonasBaath/transcribbler

Tack för att du testar Transcribbler! Följ stegen nedan i ordning. För varje steg: notera om det gick OK eller FAIL, och skriv kort vad som hände om något krånglade. Du behöver inte installera Python, Node eller något annat — allt ligger bundlat i appen.

**Tidsåtgång:** ca 20–30 minuter.

**Observera:** Denna betaversion innehåller INTE ML-funktioner (bildimport med OCR, ljudtranskription med Whisper, talardiarization, röstprofil). Hoppa över de stegen — de markeras tydligt nedan.

---

## DEL 1 — Installation

### 1.1 Ladda ner

Gå till https://github.com/JonasBaath/transcribbler/releases och ladda ner den senaste filen som slutar på `-arm64.dmg`.

### 1.2 Installera

1. Dubbelklicka på `.dmg`-filen i Hämtade filer.
2. Dra ikonen **Transcribbler** till mappen **Applications** i fönstret som öppnas.
3. Mata ut DMG:en (högerklicka på skrivbordsikonen → "Mata ut").

### 1.3 Första start (viktigt — osignerad app)

Eftersom appen inte är signerad med Apple Developer-certifikat måste du tillåta den första gången:

1. Öppna **Finder** → **Applications**.
2. **Högerklicka** (eller Ctrl-klicka) på **Transcribbler** → välj **Öppna**.
3. En dialog dyker upp: "macOS kunde inte verifiera utvecklaren". Klicka **Öppna** igen.
4. Nästa gång räcker dubbelklick.

**Förväntat:** Ett fönster öppnas med Transcribblers startskärm (mörk bakgrund, logotyp, knapp för att skapa/öppna projekt).

**Rapportera om:**
- Inget fönster dyker upp
- Fel om "skadad", "kan inte öppnas" eller liknande
- Gatekeeper blockerar trots högerklick → Öppna

---

## DEL 2 — Kärnflöde (obligatoriskt)

### 2.1 Skapa nytt projekt

1. Klicka **Nytt projekt**.
2. Ange ett projektnamn (t.ex. "Test1").
3. Välj en projektmapp (t.ex. skrivbordet).
4. Ange ett lösenord (minst 8 tecken).
5. Bekräfta.

**Förväntat:** Projektet skapas och öppnas. En ny mapp har dykt upp på valda platsen.

### 2.2 Importera transkript (.docx)

1. Förbered en liten .docx-fil med minst 3 stycken text. (Om du inte har en: öppna Pages/Word, skriv några meningar, exportera som .docx.)
2. Klicka **Importera transkript** (eller motsvarande knapp).
3. Välj din .docx-fil.

**Förväntat:** Texten visas i transkript-vyn i appen.

### 2.3 Importera transkript (.txt) — valfritt

Upprepa 2.2 men med en enkel .txt-fil.

### 2.4 Importera transkript (.odt) — valfritt

Upprepa 2.2 med en .odt-fil (LibreOffice).

### 2.5 Skapa koder

1. Öppna kodboken (knapp eller meny **Verktyg → Kodbok**).
2. Skapa minst 2 koder med olika namn och färger (t.ex. "Positivt" i grönt, "Negativt" i rött).

**Förväntat:** Koderna listas i kodboken.

### 2.6 Koda textsegment

1. Markera en textbit i transkriptet med musen.
2. Applicera en av dina koder.

**Förväntat:** Det markerade textsegmentet får en visuell markering (färg eller understrykning) som motsvarar koden.

### 2.7 Koda ytterligare segment

Upprepa 2.6 med minst 3 olika kodningar, gärna med olika koder.

### 2.8 Redigera en kodning

1. Klicka på en befintlig kodning.
2. Ändra dess kod (t.ex. byt från "Positivt" till "Negativt").

**Förväntat:** Färg/markering uppdateras.

### 2.9 Ta bort en kodning

Radera en av kodningarna.

**Förväntat:** Markeringen försvinner men texten finns kvar.

### 2.10 Kodbok-vy

Öppna kodboken igen.

**Förväntat:** Antalet kodningar per kod stämmer med vad du gjort.

### 2.11 Export — CSV

**Arkiv → Exportera → CSV** (eller motsvarande).

**Förväntat:** CSV-fil skapas. Öppna den i Numbers/Excel och verifiera att dina kodningar finns med.

### 2.12 Export — Markdown

Upprepa med Markdown-export. Öppna .md-filen i TextEdit och verifiera att innehållet är rimligt.

### 2.13 Export — QDPX

Exportera som QDPX (REFI-QDA). En `.qdpx`-fil ska skapas (det är en zip-fil — du behöver inte öppna den, bara bekräfta att den skapades).

### 2.14 Stäng och öppna projektet igen

1. Stäng appen helt (Transcribbler → Avsluta, eller Cmd+Q).
2. Starta Transcribbler igen.
3. Välj **Öppna projekt** → peka på projektmappen.
4. Ange lösenordet.

**Förväntat:** Alla transkript, koder och kodningar finns kvar.

### 2.15 Fel lösenord

Stäng projektet, öppna igen, ange FEL lösenord.

**Förväntat:** Tydligt felmeddelande. Ingen krasch.

### 2.16 Två instanser samtidigt (port-kollision)

1. Starta Transcribbler igen medan den redan är öppen (dubbelklicka i Applications).

**Förväntat:** En andra instans startar utan fel. Båda fönster fungerar parallellt (var och en ska få sin egen port).

---

## DEL 3 — Hoppa över (ML-funktioner ej i denna beta)

Följande knappar/menyval kommer INTE fungera i denna betaversion. Om du provar dem kan du få felmeddelanden — det är förväntat, inte en bugg:

- **Bildimport med OCR** (tolka tidningssidor, fotografier av text)
- **Ljudtranskription** (Whisper — omvandla .wav/.m4a till text)
- **Röstprofil-inspelning**
- **Talardiarization** (identifiera olika talare)

Om du är nyfiken får du gärna prova och rapportera vad felmeddelandet säger — men det blockerar inte testet.

---

## DEL 4 — Rapportera

Skicka en sammanställning till jonas.baath@slu.se med följande:

**Systeminfo:**
- macOS-version (Äpplemenyn → Om den här datorn)
- Modell (t.ex. MacBook Air M2)

**Resultat per steg** — markera OK eller FAIL:

```
1.3 Första start: OK / FAIL — [kommentar]
2.1 Skapa projekt: OK / FAIL — [kommentar]
2.2 Importera .docx: OK / FAIL — [kommentar]
2.3 Importera .txt: OK / FAIL / Ej testat — [kommentar]
2.4 Importera .odt: OK / FAIL / Ej testat — [kommentar]
2.5 Skapa koder: OK / FAIL — [kommentar]
2.6 Koda segment: OK / FAIL — [kommentar]
2.7 Fler kodningar: OK / FAIL — [kommentar]
2.8 Redigera kodning: OK / FAIL — [kommentar]
2.9 Ta bort kodning: OK / FAIL — [kommentar]
2.10 Kodbok-vy: OK / FAIL — [kommentar]
2.11 Export CSV: OK / FAIL — [kommentar]
2.12 Export Markdown: OK / FAIL — [kommentar]
2.13 Export QDPX: OK / FAIL — [kommentar]
2.14 Stäng + öppna igen: OK / FAIL — [kommentar]
2.15 Fel lösenord: OK / FAIL — [kommentar]
2.16 Två instanser: OK / FAIL — [kommentar]
```

**Allmänt intryck:**
- Vad fungerade bra?
- Vad var förvirrande eller långsamt?
- Krascher eller hängningar? (Beskriv vad du gjorde strax innan.)
- Saknade funktioner du förväntade dig?

**Skärmdumpar uppskattas** vid fel.

Tack för din hjälp!
