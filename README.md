# AnimLoid Web

AnimLoid provider yapısını Vercel serverless fonksiyonlarına taşıyan sade anime keşif arayüzü.

## Local

```bash
npm install
npm run dev
```

Ardından `http://localhost:3000` adresini açın. VS Code Live Server (`127.0.0.1:5500`) yalnızca statik dosyaları sunar ve `/api` fonksiyonlarını çalıştırmaz. Vercel dashboard üzerinden repo’yu import etmek yeterlidir; build command gerekmez.

## Not

Provider yanıtları kaynak sitelerin erişilebilirliğine bağlıdır. Uygulama yayın içeriklerini kendi sunucusunda barındırmaz; bölüm bağlantılarını ilgili provider’dan alıp yeni sekmede açar.
