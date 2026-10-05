# Transcribbler — Handbok

## Vad är Transcribbler?

Transcribbler är ett verktyg för kvalitativ dataanalys (QDA). Du importerar transkript, kodar textpassager, bygger en kodbok och analyserar materialet — allt i ett program. Programmet körs lokalt på din dator och projektdata skickas inte någonstans. (Undantag: PNG-export hämtar ett hjälpbibliotek från internet, men inga projektdata skickas.)

Automatisk transkribering av ljud finns som tillval men är avstängd som standard (se avsnitt 2.3).

### Språk

Programmet startar på svenska om datorns språk är svenska och annars på engelska. Byt språk när som helst med knappen **EN**/**SV** uppe till höger (finns även på startskärmen). Valet sparas. Språkvalet styr också felmeddelanden, rubriker i exporterade dokument och filnamn.

---

## Installation

Ladda ner den senaste versionen från GitHub:

https://github.com/JonasBaath/transcribbler/releases

Välj filen för ditt operativsystem under **Assets**. Allt som behövs ingår i appen; du behöver inte installera Python eller något annat. Installerad tar appen ungefär 2,5 GB på Windows och 1,7 GB på macOS.

| System | Fil |
|--------|-----|
| macOS med Apple Silicon (M1–M4) | `Transcribbler-<version>-arm64.dmg` |
| macOS med Intel-processor | `Transcribbler-<version>.dmg` (utan `arm64`) |
| Windows 10/11 | `Transcribbler.Setup.<version>.exe` |
| Linux | `Transcribbler-<version>.AppImage` |

Osäker på vilken Mac du har? Välj  → **Om den här datorn**. Står det "Chip: Apple M…" har du Apple Silicon.

Appen är inte signerad av Apple eller Microsoft. Därför varnar systemet första gången du öppnar den. Det är väntat; följ stegen nedan.

### macOS

1. Dubbelklicka på .dmg-filen och dra **Transcribbler** till mappen **Program** (Applications).
2. Öppna Transcribbler från mappen **Program**. Ett meddelande säger att Apple inte kan kontrollera appen. Klicka **Klar** (eller **Avbryt**).
3. Öppna **Systeminställningar → Integritet och säkerhet**, rulla ner och klicka **Öppna ändå** vid Transcribbler. Bekräfta med ditt lösenord.
4. Därefter startar appen som vanligt.

På macOS 14 och äldre räcker det i stället att högerklicka på appen, välja **Öppna** och klicka **Öppna** i dialogen.

Säger macOS att appen är "skadad", öppna Terminal och kör `xattr -cr /Applications/Transcribbler.app`. Starta sedan appen igen.

### Windows

1. Varnar webbläsaren att filen inte laddas ned ofta, behåll den. I Edge: välj **…** vid filen, sedan **Behåll**, **Visa mer** och **Behåll ändå**.
2. Dubbelklicka på .exe-filen.
3. Visas "Windows skyddade datorn", klicka **Mer information** och sedan **Kör ändå**.
4. Installationen sker automatiskt och appen startar när den är klar. Den finns sedan i Start-menyn.

### Linux

1. Gör filen körbar: högerklicka → **Egenskaper** → tillåt körning som program, eller kör `chmod +x Transcribbler-*.AppImage` i terminalen.
2. Starta filen med dubbelklick eller `./Transcribbler-<version>.AppImage`.

Startar den inte på Ubuntu 22.04 eller senare behövs FUSE: `sudo apt install libfuse2` (på Ubuntu 24.04: `libfuse2t64`).

### Första start

Det kan ta några sekunder innan startskärmen visas. Programmet visas på samma språk som datorn om det är svenska, annars på engelska; byt med **EN**/**SV** uppe till höger.

På Windows kan den allra första starten ta flera minuter medan datorn kontrollerar programmets filer. Visas "Kunde inte starta Flask-servern", klicka **OK** och starta Transcribbler igen; nästa start går fortare.

---

## 1. Kom igång

### 1.1 Skapa ett projekt

1. Starta Transcribbler och välj fliken **Nytt projekt**.
2. Välj en mapp där projektet ska sparas.
3. Ge projektet ett namn under **Projektnamn**.
4. Skriv ditt namn i **Ditt namn (kodare)**. Namnet identifierar dina kodningar och får bara innehålla bokstäver, siffror, mellanslag, bindestreck och understreck (inga punkter).
5. Valfritt: kryssa i **Kryptera projekt** och välj **Standardlösenord** (minst 8 tecken) eller **Starkt lösenord** (en genererad fras; **Ny fras** ger en ny, **Kopiera** kopierar den). Spara lösenordet — det kan inte återställas.
6. Klicka **Skapa projekt**.

### 1.2 Öppna ett befintligt projekt

1. Välj fliken **Öppna projekt**.
2. Välj projektmappen, eller klicka på ett projekt under **Senaste projekt**.
3. Skriv ditt kodarnamn och klicka **Öppna**. Är projektet krypterat anger du **Projektlösenord**.

### 1.3 Listan Senaste projekt

Krysset (✕) vid ett projekt öppnar en dialog med två val:

- **Ta bort ur listan** — projektet försvinner bara ur listan. Inga filer tas bort.
- **Radera projektet permanent** — tar bort projektfilen, transkript och kodningar. Kräver att du kryssar i **Jag förstår att detta inte kan ångras**. Exporterade filer i mappen behålls.

### 1.4 Byta projekt och projektnamn

- **Byt projekt** i toppfältet tar dig tillbaka till startskärmen.
- Dubbelklicka på projektnamnet i toppfältet för att byta namn på projektet.

---

## 2. Lägga till material

Klicka **Import** överst i sidofältet **Transkript** till vänster. Dialogen **Lägg till transkript** öppnas. Dra filer till dialogen eller klicka för att välja dem, och klicka **Lägg till**. Du kan lägga till flera filer på en gång; de blir separata transkript. Fältet **Namn** används bara om du väljer en enda fil.

### 2.1 Textfiler

- **.txt** — ren text.
- **.md** — Markdown. Markeringar (rubriker, fetstil, länkar) tas bort så att ren text återstår. YAML-huvudet läses: `title` (och `date`) blir transkriptets namn, `category` blir kategori och `tags` blir taggar (se 3.4).
- **.docx**, **.odt** — fet och kursiv stil bevaras. Text i tabeller importeras rad för rad, med cellerna åtskilda av tabb, så att talare och yttrande hamnar på samma rad.

### 2.2 Bilder (OCR)

Bilder (.jpg, .png, .heic m.fl.) kan importeras. Med **Läs av text i bild (OCR)** ikryssat (standard) läses texten av: på macOS med Apple Vision, på Windows och Linux med EasyOCR. Utan krysset importeras bilden bara för kodning med kodpins (se 5.5).

### 2.3 Ljudfiler

Automatisk transkribering är avstängd som standard, eftersom kursen arbetar med färdiga transkript. Ljudfiler kan då inte läggas till. Transkript som redan har ett ljud (till exempel sådana som kursledaren har förberett) kan spelas upp: klicka i texten för att spela från det stället, och mellanslag spelar/pausar.

*För kursledare: transkriberingen slås på med `"enable_whisper": true` i `~/.transcribbler_config.json` (eller miljövariabeln `TRANSCRIBBLER_ENABLE_WHISPER=1`). Första körningen laddar ner en taligenkänningsmodell på ca 3 GB.*

### 2.4 Notescribbler

Filer från Notescribbler kan importeras: **.scribbler** och **.nsenc** (krypterade; du behöver exportlösenordet) samt **.zip** (okrypterad export, importeras som klartext).

---

## 3. Hantera transkript

Klicka på ett transkript i listan för att öppna det. Cmd/Ctrl-klicka för att markera flera (för kategorisering och taggning).

### 3.1 Byta namn, memo och sökning

- **Byta namn**: klicka ✎ bredvid transkriptets titel i redigeraren.
- **Memo**: högerklicka på transkriptet i listan och välj **📝 Memo**. Anteckningen hör till hela transkriptet.
- **Sök**: högerklicka och välj **🔍 Sök** för att öppna transkriptet med sökfältet.

### 3.2 Redigera text och formatering

- **Redigera text**: klicka ✎ **Redigera text** i verktygsfältet. Texten öppnas i ett redigeringsfält med **Spara**/**Avbryt**. Om transkriptet redan har kodningar varnar programmet för att deras positioner kan förskjutas.
- **Fet/kursiv**: markera text och klicka **B** eller **I** i verktygsfältet. Klicka på formaterad text för att ta bort formateringen.
- **Läsbarhet**: **A−**/**A+** ändrar textstorleken och **Sans**/**Serif** typsnittet.

### 3.3 Kategorisera

Högerklicka och välj **📁 Kategorisera**. Transkript med samma kategori grupperas i listan. **Ta bort kategori** tar bort grupperingen.

### 3.4 Tagga

Taggar beskriver egenskaper hos transkripten, till exempel "lärare", "elev" eller "skola A". Ett transkript kan ha flera taggar.

1. Markera ett eller flera transkript, högerklicka och välj **🏷️ Tagga**.
2. Skriv en tagg under **Lägg till tagg…** och klicka **Lägg till** (eller tryck Enter). Befintliga taggar föreslås medan du skriver.
3. Ta bort en tagg med ✕ på taggen. **(delvis)** betyder att bara några av de markerade transkripten har taggen.
4. Klicka **Klar**.

Taggarna visas i transkriptlistan och används för att filtrera analysvyn (se 7.3).

### 3.5 Ordning och ta bort

- Dra i handtaget ⋮⋮ för att ändra ordning.
- **Bokstavsetiketter för transkript** (Inställningar) sätter A., B., C. … framför namnen. Etiketterna följer ordningen och används i analysvyn och exporter.
- Ta bort ett transkript med ✕ på raden. Transkriptet och alla kodningar av det raderas, för samtliga kodare. Det går inte att ångra.

---

## 4. Bygga en kodbok

Kodboken finns i sidofältet till höger.

### 4.1 Skapa koder

1. Klicka **+** (**Ny kod**) i sidofältet **Kodbok**.
2. Ge koden ett namn och välj en färg.
3. Valfritt: välj en **Överordnad kod (tema)** för att bygga en hierarki.
4. Valfritt: skriv en **Beskrivning**. Den visas när du håller muspekaren över koden.
5. Klicka **Spara**.

Du kan också skapa en kod direkt när du kodar (se 5.1).

### 4.2 Hierarki och numrering

Koder kan ordnas i ett träd, till exempel "Organisation" med underkoderna "Resultat" och "Ambition". Med **Numrering av koder** påslaget i Inställningar numreras koderna automatiskt (1, 2, 2.1, 2.2 …).

### 4.3 Redigera, byta namn och ta bort

- Klicka ✎ på kodens rad för att öppna **Redigera kod** (namn, färg, överordnad kod, beskrivning).
- Högerklicka på en kod och välj **✏️ Byt namn** för att bara byta namn.
- **Ta bort kod** (i **Redigera kod**) raderar koden **och alla kodningar med koden, för samtliga kodare**. Underkoder flyttas upp en nivå. Det går inte att ångra.

### 4.4 Slå ihop koder

**Verktyg ▾ → Kodbok → Slå ihop koder**. Välj **Källkod (tas bort)** och **Målkod (behålls)** och klicka **Slå ihop**. Alla kodningar flyttas till målkoden för samtliga kodare, källkodens underkoder flyttas till målkoden, och källkoden tas bort. Det går inte att ångra.

### 4.5 Filtrera koder

Skriv i **Filtrera koder…** ovanför kodboken för att hitta koder i en stor kodbok.

### 4.6 Kodboks- och kodträdsverktygen

- **Verktyg ▾ → Kodbok** visar alla koder med antal kodningar och markerar koder som har nyckelpassager (◆). Kodboken kan exporteras som CSV, MD, DOCX och ODT.
- **Verktyg ▾ → Kodträd** visar hierarkin grafiskt och kan exporteras som PNG, PDF, MD, DOCX och ODT.

---

## 5. Koda text

### 5.1 Grundläggande kodning

1. Öppna ett transkript.
2. Markera en textpassage med musen.
3. En ruta visas. Sök efter en kod och välj den. Finns koden inte, skriv ett nytt namn och klicka **+ Skapa "…"** — koden skapas och används direkt.
4. Valfritt: skriv ett memo, kryssa i **Nyckelpassage** eller ange **Vikt** (0–100; visas bara om **Segmentvikt** är påslaget i Inställningar).
5. Klicka **Koda**.

Kodade passager visas med färgmarkering. När flera koder överlappar visas en färgad understrykning per kod.

### 5.2 Ändra en kodning

Klicka på en färgmarkerad passage för att öppna detaljvyn. Där kan du ändra memo, vikt, nyckelpassage och kod. Klicka **Uppdatera** för att spara ändringarna, **Ta bort** för att ta bort kodningen, eller **Stäng**.

### 5.3 Ångra och gör om

Cmd/Ctrl+Z ångrar och Cmd/Ctrl+Shift+Z (eller Ctrl+Y) gör om. Det gäller att lägga till och ta bort kodningar i det öppna transkriptet, upp till 200 steg. Ändringar av koder, text, memon och vikter kan inte ångras.

### 5.4 Vad du ser

I kodningsvyn ser du bara **dina egna** kodningar. Analysvyn, statistiken, matriserna och exporterna omfattar alla kodare i projektet.

### 5.5 Koda bilder (kodpins)

För bildtranskript: klicka 📍 **Placera kodpins** i bildpanelens rubrik och klicka sedan i bilden för att placera en kodpin. Dra en pin för att flytta den. **Visa igenkänd text** visar var OCR hittade text.

---

## 6. Sök

### 6.1 Sök i ett transkript

Tryck Cmd+F (macOS) eller Ctrl+F (Windows/Linux). Enter går till nästa träff, Shift+Enter till föregående och Esc stänger sökfältet.

### 6.2 Projektsök

Klicka **Projektsök** i toppfältet för att söka i alla transkript. Klicka på en träff för att öppna transkriptet vid träffen.

---

## 7. Analysvy

### 7.1 Öppna analysvyn

Klicka **Analysvy** i toppfältet (bredvid **Kodningsvy**).

### 7.2 Välja koder

Kryssa i koderna vars utdrag du vill se. En överordnad kod kryssar även i sina underkoder. Siffran bredvid varje kod är antalet utdrag från alla kodare, efter taggfiltret. **Alla**/**Inga** väljer eller avväljer alla koder.

### 7.3 Taggfilter

Med knappen **🏷️ Alla transkript** begränsar du analysen till transkript med vissa taggar (se 3.4).

1. Kryssa i en eller flera taggar.
2. Välj **Matcha någon** (transkriptet har minst en av taggarna) eller **Matcha alla** (transkriptet har samtliga).
3. Klicka **Använd**. **Rensa filter** visar alla transkript igen.

Knappen visar sedan till exempel "2 tagg(ar) · 3/8 transkript". Filtret påverkar utdragen, siffrorna i kodboken och all export från analysvyn.

### 7.4 Visningslägen

- **Separat**: utdragen grupperas per kod (med kodhierarkin som rubriker) och ordnas efter transkriptets bokstavsetikett och sedan i den ordning de förekommer i texten.
- **Kod-i-kod**: utdragen grupperas per transkript, och överlappande passager slås ihop till ett kort med färgade markeringar per kod.

### 7.5 Sök och filter

- **Sök i utdrag…** söker i utdragens text, memon och transkriptnamn. Cmd/Ctrl+F i analysvyn flyttar markören hit.
- **Memos** visar eller döljer memon.
- **Nyckelpassage** visar bara utdrag markerade som nyckelpassager.

### 7.6 Hoppa till utdraget

Klicka på ett utdrag för att öppna transkriptet i kodningsvyn vid passagen. Om du har markerat text i kortet, eller om **Välj utdrag** är påslaget, hoppar programmet inte. Är utdraget kodat av en annan kodare markeras passagen tillfälligt, och ett meddelande talar om vem som kodade det.

### 7.7 Exportera från analysvyn

Klicka **Exportera** i analysvyn. I **Exportera analys** väljer du först omfattning:

- **Exportera valda koder**
- **Exportera markerade utdrag** — kräver att **Välj utdrag** är påslaget så att du kan kryssa i enskilda utdrag
- **Exportera nyckelpassager**
- **Exportera allt**

Välj sedan format: **DOCX** (Word, med färgade kodrubriker), **ODT**, **MD** (Markdown), **CSV** (för R, Python eller kalkylprogram), **PDF** eller **PNG**.

Bra att veta:

- Taggfiltret gäller alla format.
- DOCX, ODT, MD och CSV grupperas alltid per kod och innehåller alltid memon, oavsett visningsläge och memoknapp.
- PDF och PNG avbildar vyn så som den ser ut på skärmen.

---

## 8. Statistik och matriser

### 8.1 Statistik

**Verktyg ▾ → Statistik** visar antal kodningar och kodade tecken per kod, för **Hela projektet** eller **Detta transkript**. Alla kodare räknas, och kodpins ingår.

### 8.2 Kodmatris

**Verktyg ▾ → Kodmatris**: transkript som rader och koder som kolumner. Koder utan kodningar visas inte. Kan exporteras som CSV.

### 8.3 Kodöverlapp

**Verktyg ▾ → Kodöverlapp**: hur ofta två koder överlappar i texten (co-occurrence). Bara överlapp inom samma kodares kodningar räknas; kodpins ingår inte. Kan exporteras som CSV.

---

## 9. Samarbete

### 9.1 Flera kodare

Varje kodare öppnar projektet med sitt eget kodarnamn. Kodningarna sparas separat per kodare och transkript, så kodare skriver aldrig över varandras kodningar.

### 9.2 Arbetsflöde i en kurs

1. **Kursledaren** skapar ett projekt, importerar transkripten, taggar dem och bygger eventuellt en startkodbok.
2. Kursledaren delar ut **en kopia av projektmappen** till varje student (eller grupp). Låt inte flera personer arbeta samtidigt i samma mapp: projektfilen (med kodboken) kan då skrivas över.
3. Varje student öppnar sin kopia med **sitt eget kodarnamn** och kodar.
4. Studenten väljer **Verktyg ▾ → Exportera mina kodningar** och lämnar in den .json-fil som skapas.
5. Kursledaren väljer **Verktyg ▾ → Importera kodningar…** i sitt projekt och väljer filen. Upprepa för varje student.

### 9.3 Importera kodningar

Vid import:

- Transkript matchas på id. Saknas id:t i projektet matchas transkriptet på identisk text. Därför fungerar import även om transkripten har importerats separat, så länge texten är densamma.
- Koder matchas på id och annars på namn. Koder som saknas (till exempel koder som studenten har skapat själv) skapas, med sin plats i hierarkin.
- Kodningar som redan finns hoppas över, så samma fil kan importeras två gånger utan dubbletter.

Efter importen redovisas vad som hände: antal importerade kodningar, nya koder, transkript som inte hittades, och transkript vars text skiljer sig från kodarens version (där kan positionerna vara förskjutna).

*Obs: kodningsfilen är okrypterad och innehåller de kodade textutdragen, även när projektet är krypterat.*

### 9.4 Interbedömarreliabilitet (IRR)

Beräkning av Cohens kappa mellan två kodare per transkript finns i programmet, men knappen är ännu dold i gränssnittet. I skrivbordsappen nås funktionen via menyn **Verktyg → IRR**. Tolkningen av kappa följer Landis & Koch (1977).

---

## 10. Exportera projektet

Klicka **Exportera** i toppfältet. Välj **Destinationsmapp**, **Omfattning** och ett eller flera format.

**Omfattning** gäller CSV-formaten, Markdown per kod och kodade transkript:

- **Hela projektet** (standard)
- **Bara öppet transkript** (kan bara väljas när ett transkript är öppet)

| Format | Innehåll |
|--------|----------|
| CSV (alla) | Alla kodningar med metadata |
| CSV tidy (R/Python) | En rad per kodning, anpassat för R och Python |
| Markdown – utdrag per kod | Kodade utdrag grupperade per kod |
| Markdown – kodbok | Kodbokens struktur med antal kodningar (alltid hela projektet) |
| Markdown – kodade transkript | Alla transkript som har kodningar, i en fil: hela texten med koderna markerade (även överlappande) och en sammanfattning med memon. Lämpligt för att granska kodningen |
| QDPX (REFI-QDA) | Utbytesformat för andra QDA-program (alltid hela projektet) |

Om något format inte kan skapas skrivs övriga format ändå, och dialogen visar vad som misslyckades.

Filerna namnges med projektnamn, datum och tid. Filnamn och rubriker följer det valda språket.

QDPX innehåller texter, koder och kodningar med memon. Kodpins, transkriptmemon, taggar, vikter och nyckelpassager följer inte med. Kompatibiliteten med NVivo och ATLAS.ti är inte verifierad.

---

## 11. Inställningar

Klicka ⚙ (**Inställningar**) i toppfältet:

- **Numrering av koder** — automatisk hierarkisk numrering (1, 2, 2.1 …).
- **Bokstavsetiketter för transkript (A., B., …)** — etiketter framför transkriptnamnen (se 3.5).
- **Segmentvikt (0–100)** — visar ett viktreglage när du kodar.

Med transkribering påslagen finns även **Identifiera mig automatiskt**, **Vågform (ljudfiler)** och **🎤 Röstprofil**.

Språk (**EN**/**SV**) och tema (**Ljust**/**Mörkt**) byts med knapparna i toppfältet och på startskärmen.

---

## Föreslaget arbetsflöde

### Fas 1: Förberedelse
1. Skapa eller öppna projektet.
2. Bygg en första kodbok utifrån forskningsfrågorna (deduktiv ansats), eller börja utan koder (induktiv ansats).

### Fas 2: Import
3. Importera transkripten (text, bilder eller Notescribbler-material).
4. Tagga transkripten efter de jämförelser du vill göra (till exempel grupp eller plats).
5. Läs igenom transkripten och rätta eventuella fel med **Redigera text** innan du börjar koda.

### Fas 3: Kodning (omgång 1)
6. Öppna första transkriptet och läs igenom det.
7. Koda — markera text, välj eller skapa koder.
8. Skriv memon om viktiga iakttagelser.
9. Markera särskilt talande passager som **nyckelpassager**.
10. Upprepa för alla transkript.

### Fas 4: Revidera kodboken
11. Granska kodboken — slå ihop överflödiga koder och bygg hierarkier.
12. Använd **Kodöverlapp** för att hitta koder som ofta överlappar.
13. Använd **Statistik** för att se hur koderna fördelar sig.

### Fas 5: Kodning (omgång 2)
14. Gå igenom transkripten igen med den reviderade kodboken.
15. Justera kodningar och memon.

### Fas 6: Analys
16. Byt till **Analysvy**.
17. Välj koder och läs utdragen — jämför teman mellan transkript.
18. Använd taggfiltret för att jämföra grupper.
19. Använd **Kod-i-kod** för att se överlapp.
20. Filtrera på **Nyckelpassage** för att samla de starkaste citaten.
21. Exportera analysen i valt format.

### Fas 7: Samarbete (valfritt)
22. Låt en annan kodare koda samma material i en kopia av projektet (se 9.2).
23. Importera kodningarna med **Importera kodningar…**.

### Fas 8: Slutexport
24. Exportera projektet som CSV (för statistisk analys) eller QDPX (för andra QDA-program).
25. Exportera utvalda analyser som DOCX till rapporten.

---

## Kortkommandon

| Kommando | Åtgärd |
|----------|--------|
| Cmd/Ctrl + Z | Ångra (lägga till/ta bort kodning) |
| Cmd/Ctrl + Shift + Z, Ctrl + Y | Gör om |
| Cmd/Ctrl + F | Sök i transkriptet (i analysvyn: sök i utdrag) |
| Enter / Shift + Enter | Nästa / föregående sökträff |
| Esc | Stäng sökfält och rutor |
| Mellanslag | Spela/pausa ljud (om påslaget i ljudspelaren) |

Fet och kursiv stil samt textstorlek styrs med knapparna **B**, **I** och **A−**/**A+** i verktygsfältet.

---

*Transcribbler är fri programvara under licensen AGPL-3.0: fri att använda och dela, även i yrkesarbete. Vidaredistribuerade versioner måste ha samma licens.*
