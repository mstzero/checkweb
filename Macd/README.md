# Market Signal Hub Prototype

Bu klasör, Market Signal Hub için ilk çalışan statik web prototipini içerir.

## Çalıştırma

Yahoo Finance proxy destekli sürüm:

```bash
python3 server.py
```

Sonra tarayıcıda aç:

```text
http://127.0.0.1:4174/
```

## Bu prototipte olanlar

- Moving Now dashboard
- Bloomberg tarzı kayan fiyat bandı
- Ticker'a tıklayınca açılan yaratıcı "Piyasa Nabzı" grafiği
- Sol tarafta satıcı baskısı, sağ tarafta alıcı baskısı, ortada likidite/fiyat dalgası
- Alıcı gücü, satıcı gücü, net bias ve kısa akış yorumu
- Yahoo Finance chart endpoint proxy denemesi, başarısız olursa mock fallback
- Periyodik mock fiyat güncellemesi
- Türkçe / İngilizce arayüz seçimi
- Sol altta currency pariteleri
- Genişletilmiş varlık sınıfları: kripto, emtia, makro/FX, hisseler, global endeksler, tahvil/faiz, ETF'ler, Türkiye
- Ana ekranda yatırımcı odaklı global favoriler / en çok izlenen piyasalar paneli
- Sağ panelde Bugün / Yarın / Bu Hafta sekmeli önemli olaylar ve ekonomik takvim paneli
- Asset class, zaman penceresi, confidence ve watchlist filtreleri
- GOLD, BTC, OIL, SPY, USDTRY, ETH, NVDA, DAX, BIST100 ve NATGAS için mock hareket kartları
- "Why is it moving?" detay paneli
- Driver ranking
- Timeline
- High Impact Feed
- Haber kartına tıklayınca açılan detay balonu
- Watchlist

## Mock olanlar

- Fiyat verisi
- Yahoo verisi alınamazsa grafik verisi
- Haberler
- Ekonomik takvim olayları
- Driver skorları
- AI açıklamaları
- Watchlist state

## Sonraki doğru adım

Bir sonraki sprintte bunu Next.js + FastAPI mimarisine taşımak mantıklı:

- `GET /moving-now`
- `GET /movements/{id}`
- `GET /news`
- CoinGecko/CoinMarketCap market data ingestion
- RSS haber ingestion
- OpenAI summary, sentiment ve impact analysis
