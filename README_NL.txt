Dynamik • AeonCore (NL)
=======================
Een mobiele chat-app (Expo) met een eigen backend (FastAPI) die met Claude praat.
De Claude-sleutel staat alleen op de server, nooit in de app.

Snelstart
---------
1) Render.com: New → Web Service → kies deze repo.
   - Root Directory: backend-cloud-nl
   - Build: pip install -r requirements.txt
   - Start: uvicorn main:app --host 0.0.0.0 --port $PORT
   - Environment:
       ANTHROPIC_API_KEY = je sleutel van console.anthropic.com
       SHARED_SECRET     = een lang willekeurig wachtwoord (VERPLICHT)
       CLAUDE_MODEL      = claude-opus-5-5  (of claude-sonnet-5-5: goedkoper)
   (Of gebruik render/render.yaml als Blueprint.)
2) Test: open https://<jouw-render-url>/health → {"ok": true}
3) Zet je Render-URL en hetzelfde SHARED_SECRET in mobile-expo-stream-nl/app/api.js.
4) Expo Go: cd mobile-expo-stream-nl && npm install && npm run start → QR scannen.
5) APK: cd mobile-expo-stream-nl && eas login && eas build -p android --profile preview

Knoppen: Spec (specificaties), Code (startercode), Visual (Mermaid-diagram).

Let op
------
- Zet een BESTEDINGSLIMIET in de Anthropic Console.
- Het SHARED_SECRET zit ook in de app. Deel de APK dus niet met onbekenden:
  wie de app heeft, kan op jouw kosten chatten.
- Render free plan slaapt na een tijdje; de eerste vraag kan ~30 sec duren.
