# Testplan — Transcribbler Electron

## Förberedelser (alla plattformar)
- [ ] Ladda ned artefakt från GitHub Actions
- [ ] Kontrollera att Python + venv är installerat i rätt mapp
- [ ] Installera appen (se plattformsspecifikt nedan)

---

## macOS

### Installation
- [ ] Öppna `.dmg`, dra Transcribbler till Applications
- [ ] Starta från Applications (inte från .dmg)

### Start
- [ ] Appen öppnas utan terminal eller webbläsare
- [ ] Menyraden visar **transcribbler** (fetstil), inte "Electron"
- [ ] Menyerna Arkiv / Redigera / Verktyg / Visa / Fönster / Hjälp syns
- [ ] Trafikljusen (röd/gul/grön) överlappar topbar utan att täcka logotyp eller kodarbadge

### Splash-skärm
- [ ] Öppna projekt: mappväljaren öppnar Electron-native dialog (inte webbläsaren)
- [ ] Nytt projekt: mappväljaren fungerar
- [ ] Enter i kodarnamn-fältet öppnar/skapar projektet

### Verktyg-menyn
- [ ] Statistik öppnar rätt modal
- [ ] IRR öppnar rätt modal
- [ ] Kodbok öppnar rätt modal
- [ ] Kodträd öppnar rätt modal
- [ ] Kodmatris öppnar rätt modal
- [ ] Kodöverlapp öppnar rätt modal
- [ ] Slå ihop filer öppnar rätt modal

### Språk
- [ ] Klicka EN → menyraden byter till engelska (Tools, File, Edit…)
- [ ] Klicka SV → menyraden byter tillbaka till svenska

### Avslut
- [ ] Stäng fönster → appen avslutas, Flask-processen dör (inga zombie-processer)
- [ ] Arkiv → Stäng fönster (Cmd+W) fungerar

---

## Windows

### Installation
- [ ] Kör `.exe`-installern, godkänn UAC-prompt
- [ ] Starta från Start-menyn eller skrivbordsgenvägen

### Start
- [ ] Appen öppnas utan terminal eller webbläsare
- [ ] Fönstrets titelrad visar "Transcribbler"
- [ ] Menyerna Arkiv / Redigera / Verktyg / Visa / Hjälp syns

### Splash-skärm
- [ ] Öppna projekt: mappväljaren öppnar Windows-native dialog
- [ ] Nytt projekt: mappväljaren fungerar
- [ ] Enter i kodarnamn-fältet öppnar/skapar projektet

### Verktyg-menyn
- [ ] Samtliga verktyg (Statistik, IRR, Kodbok, Kodträd, Kodmatris, Kodöverlapp, Slå ihop filer) öppnar rätt modal

### Språk
- [ ] Klicka EN → menyraden byter till engelska
- [ ] Klicka SV → menyraden byter tillbaka till svenska

### Avslut
- [ ] Stäng fönster (Alt+F4) → appen avslutas, inga Python-processer kvar i Task Manager
- [ ] Arkiv → Avsluta fungerar

---

## Linux (USB-boot)

### Förberedelser
- [ ] USB-stickan har Python 3 installerat (`python3 --version`)
- [ ] Kör `pip install -r requirements.txt` i projektmappen

### Installation
- [ ] Gör `.AppImage` körbar: `chmod +x Transcribbler-*.AppImage`
- [ ] Starta: `./Transcribbler-*.AppImage`

### Start
- [ ] Appen öppnas utan terminal eller webbläsare
- [ ] Fönstrets titelrad visar "Transcribbler"
- [ ] Menyerna Arkiv / Redigera / Verktyg / Visa / Hjälp syns

### Splash-skärm
- [ ] Öppna projekt: mappväljaren öppnar native dialog
- [ ] Nytt projekt: mappväljaren fungerar
- [ ] Enter i kodarnamn-fältet öppnar/skapar projektet

### Verktyg-menyn
- [ ] Samtliga verktyg öppnar rätt modal

### Språk
- [ ] Klicka EN → menyraden byter till engelska
- [ ] Klicka SV → menyraden byter tillbaka till svenska

### Avslut
- [ ] Stäng fönster → inga Python-processer kvar (`ps aux | grep python`)
- [ ] Arkiv → Avsluta fungerar
