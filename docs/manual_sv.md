# Transcribbler — Handbok

## Vad är Transcribbler?

Transcribbler är ett verktyg för kvalitativ dataanalys (QDA). Du kan transkribera intervjuer, koda textpassager, bygga en kodbok och analysera dina data — allt i en enda applikation. Programmet kör lokalt på din dator, ingen data lämnar din maskin.

---

## 1. Kom igång

### 1.1 Skapa ett projekt

1. Starta Transcribbler.
2. Välj fliken **Nytt projekt**.
3. Välj en mapp där projektet ska sparas.
4. Ge projektet ett namn (t.ex. "Min intervjustudie").
5. Skriv ditt namn i fältet **Ditt namn (kodare)** — detta identifierar vem som kodar.
6. Klicka **Skapa projekt**.

### 1.2 Öppna ett befintligt projekt

1. Välj fliken **Öppna projekt**.
2. Välj projektmappen eller klicka på ett projekt under **Senaste projekt**.
3. Skriv ditt kodarnamn och klicka **Öppna**.

---

## 2. Lägga till material

### 2.1 Textfiler

Klicka **+ Transkript** i toppfältet. Dra in eller välj filer:
- **.txt**, **.md** — ren text
- **.docx**, **.odt** — formaterad text (fet/kursiv bevaras vid import)

### 2.2 Ljudfiler (automatisk transkribering)

Dra in ljudfiler (.mp3, .wav, .m4a, .ogg, .flac m.fl.). Transcribbler transkriberar automatiskt med Whisper:

- **Svenska**: KB-Whisper (rekommenderas)
- **Engelska**: OpenAI Whisper
- **Övriga språk**: Whisper med autodetect

**Talaridentifiering (diarization)**: Kryssa i rutan om du vill att programmet ska skilja på talare. Du kan ange antal talare eller låta programmet upptäcka det automatiskt.

> Tips: Första gången du använder diarization krävs ett Hugging Face-token. Programmet guidar dig.

### 2.3 Bilder (OCR)

Dra in bilder (.jpg, .png, .heic m.fl.). Transcribbler kan extrahera text ur bilder (OCR). På macOS används Apple Vision, på Windows/Linux används EasyOCR.

### 2.4 Notescribbler-import

Filer från Notescribbler (.scribbler, .nsenc) kan importeras direkt. Du behöver exportlösenordet från Notescribbler.

### 2.5 Batchimport

Du kan dra in flera filer samtidigt — de läggs till som separata transkript.

---

## 3. Hantera transkript

- **Byta namn**: Högerklicka på transkriptet i listan, välj "Byt namn".
- **Kategorisera**: Högerklicka, välj "Kategorisera" för att gruppera transkript.
- **Memo**: Längst ner i redigeraren finns ett memofält för anteckningar om transkriptet.
- **Redigera text**: Klicka i texten och skriv för att redigera.
- **Formatering**: Markera text och använd Ctrl+B (fet) eller Ctrl+I (kursiv).
- **Ta bort**: Högerklicka och bekräfta borttagning.

---

## 4. Bygga en kodbok

### 4.1 Skapa koder

1. Klicka **+**-knappen bredvid "Kodbok" i sidofältet.
2. Ge koden ett namn (t.ex. "Samarbete").
3. Välj en färg.
4. Valfritt: välj en överordnad kod (tema) för att skapa en hierarki.
5. Valfritt: skriv en beskrivning.
6. Klicka **Spara**.

### 4.2 Hierarkisk kodbok

Koder kan ordnas i träd: t.ex. "Organisation" som överkod med "Resultat" och "Ambition" som underkoder. Numreringen (1, 2, 2.1, 2.2) är automatisk om du slår på den under inställningar.

### 4.3 Redigera och ta bort koder

Klicka på en kod i kodboken för att redigera namn, färg, överordnad kod eller beskrivning. Du kan även ta bort koden — notera att kodningar kopplade till den förlorar sin kod.

### 4.4 Slå ihop koder

Via kodbokens meny kan du slå ihop två koder. Alla kodningar från källkoden flyttas till målkoden, och källkoden tas bort.

### 4.5 Filtrera koder

Använd sökfältet ovanför kodboken för att snabbt hitta koder i stora kodböcker.

---

## 5. Koda text

### 5.1 Grundläggande kodning

1. Öppna ett transkript.
2. Markera en textpassage med musen.
3. En popup visas — sök eller välj en kod.
4. Valfritt: skriv ett memo, sätt vikt (0–100) eller markera som nyckelpassage.
5. Klicka **Koda**.

Kodade passager visas med färgmarkering i texten.

### 5.2 Redigera en kodning

Klicka på en färgmarkerad passage för att öppna detaljvyn. Där kan du:
- Ändra memo
- Ändra vikt
- Toggla nyckelpassage
- Byta kod (klicka på kodnamnet)
- Ta bort kodningen

### 5.3 Ångra/Gör om

Använd Ctrl+Z / Ctrl+Shift+Z (Cmd på macOS) för att ångra eller göra om kodningar. Historiken rymmer 200 steg.

### 5.4 Koda bilder (pins)

För bildtranskript: aktivera "Placera kodpins" och klicka på bilden för att placera en kodpin. Dra en pin för att flytta den.

---

## 6. Sök

### 6.1 Sök i transkript

Tryck **Cmd+F** (macOS) eller **Ctrl+F** (Windows/Linux) för att öppna sökfältet. Navigera mellan träffar med pilknapparna.

### 6.2 Projektsök

Klicka **Projektsök** i toppfältet för att söka i alla transkript samtidigt. Klicka på en träff för att hoppa direkt till rätt ställe.

---

## 7. Analysvy

### 7.1 Öppna analysvyn

Klicka på **Analysvy** i toppfältet (bredvid Kodningsvy) för att byta vy.

### 7.2 Välja koder

I kodboken till vänster: kryssa i de koder vars utdrag du vill se. Siffran bredvid varje kod visar antal kodade utdrag. Använd **Alla** / **Inga** för att snabbt välja/avvälja.

### 7.3 Visningsläge

- **Separat**: Utdrag grupperas per kod, sedan per transkript, i kronologisk ordning.
- **Kod-i-kod**: Utdrag med överlappande koder visas med kodetiketter inline.

### 7.4 Filter och sökning

- **Sök i utdrag**: Filtrera utdrag med fritext.
- **Memos**: Toggla för att visa/dölja memon under utdragen.
- **Nyckelpassage**: Visa enbart utdrag markerade som nyckelpassager.

### 7.5 Exportera från analysvyn

1. Välj koder i kodboken.
2. Klicka **Exportera** och välj format:
   - **.docx** — Word-dokument med färgade kodrubriker
   - **.odt** — OpenDocument-format
   - **.md** — Markdown
   - **.csv** — För vidare analys i R/Python/Excel
   - **.png** — Bild

Du kan exportera alla valda koder eller aktivera **Exportläge** för att välja enskilda utdrag.

---

## 8. Statistik och matriser

### 8.1 Statistik

Klicka **Verktyg > Statistik**. Visar antal kodningar och tecken per kod, för hela projektet eller ett enskilt transkript.

### 8.2 Kodmatris

**Verktyg > Kodmatris**: en tabell med transkript som rader och koder som kolumner. Exporteras som CSV.

### 8.3 Kodöverlapp

**Verktyg > Kodöverlapp**: visar vilka koder som överlappar varandra (co-occurrence). Exporteras som CSV.

---

## 9. Samarbete

### 9.1 Flera kodare

Varje kodare arbetar med sitt eget kodarnamn. Kodningar lagras separat per kodare och transkript.

### 9.2 Importera kollegas kodningar

Klicka **Verktyg > Slå ihop filer** och klistra in sökvägen till kollegans .json-kodningsfil.

### 9.3 Inter-rater reliability (IRR)

> *Denna funktion är under utveckling och ännu inte tillgänglig i gränssnittet.*

Beräkning av Cohens kappa mellan två kodare planeras för en kommande version.

---

## 10. Exportera hela projektet

Klicka **Exportera** i toppfältet. Välj destinationsmapp och ett eller flera format:

| Format | Innehåll |
|--------|----------|
| CSV (alla) | Alla kodningar med metadata |
| CSV tidy | Format optimerat för R/Python |
| Markdown — citat per kod | Alla kodade utdrag grupperade per kod |
| Markdown — kodbok | Kodbokens struktur med antal kodningar |
| Markdown — detta transkript | Aktuellt transkript med kodmarkeringar |
| QDPX (REFI-QDA) | För import i NVivo, ATLAS.ti m.fl. |

Exporterade filer namnges automatiskt med projektnamn, datum och tid.

---

## 11. Inställningar

Klicka på kugghjulet i toppfältet:

- **Numrering av koder**: Automatisk hierarkisk numrering (1, 2, 2.1 ...)
- **Alfabetisk ordning**: Sortera transkript alfabetiskt
- **Segmentvikt**: Aktivera viktfält (0–100) vid kodning
- **Vågform**: Visa ljudvågform för ljudfiler
- **Språk**: Svenska / Engelska
- **Tema**: Mörkt / Ljust (kan även bytas på startskärmen)

---

## Föreslaget arbetsflöde

### Fas 1: Förberedelse
1. Skapa ett nytt projekt.
2. Bygg en initial kodbok baserat på forskningsfrågorna (deduktiva koder), eller börja utan koder (induktivt).

### Fas 2: Import och transkribering
3. Dra in ljudfiler — låt Whisper transkribera.
4. Namnge talare efter transkriberingen.
5. Granska och korrekturläs transkripten.
6. Importera eventuella textfiler, bilder eller Notescribbler-material.

### Fas 3: Kodning (omgång 1)
7. Öppna första transkriptet och läs igenom det.
8. Börja koda — markera text, välj eller skapa koder.
9. Skriv memon för viktiga insikter.
10. Markera särskilt talande passager som **nyckelpassager**.
11. Upprepa för alla transkript.

### Fas 4: Kodbok-revidering
12. Granska kodboken — slå ihop överflödiga koder, skapa hierarkier.
13. Kolla **Kodöverlapp** för att hitta koder som ofta överlappar.
14. Kolla **Statistik** för att se fördelning av koder.

### Fas 5: Kodning (omgång 2)
15. Gå igenom transkripten igen med den reviderade kodboken.
16. Finjustera kodningar och memon.

### Fas 6: Analys
17. Byt till **Analysvyn**.
18. Välj koder och studera utdragen — jämför teman över transkript.
19. Använd **Kod-i-kod** för att se överlappningar.
20. Filtrera på **Nyckelpassager** för att samla de starkaste citaten.
21. Exportera analys i valt format.

### Fas 7: Samarbete (valfritt)
22. Låt en kollega koda samma material med eget kodarnamn.
23. Importera kollegans kodningar.

### Fas 8: Slutexport
24. Exportera hela projektet som CSV (för statistisk analys) eller QDPX (för NVivo/ATLAS.ti).
25. Exportera utvalda analyser som .docx för rapporten.

---

## Kortkommandon

| Kommando | Funktion |
|----------|----------|
| Cmd/Ctrl + Z | Ångra |
| Cmd/Ctrl + Shift + Z | Gör om |
| Cmd/Ctrl + F | Sök i transkript |
| Cmd/Ctrl + B | Fet stil |
| Cmd/Ctrl + I | Kursiv stil |
| A+ / A- | Ändra textstorlek |

---

*Transcribbler — fri att använda och dela, även i yrkesarbete. Vidaredistribution kräver samma licens.*
