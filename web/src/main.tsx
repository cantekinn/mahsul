import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

/**
 * Servis iscisi kaydi. Ne yaptigi ve nelere DOKUNMADIGI public/sw.js
 * basliginda yaziyor.
 *
 * SADECE URETIMDE: gelistirmede Vite modulleri tek tek servis ediyor ve
 * araya giren bir onbellek, kaynagi degistirdigimizde tarayicinin eski
 * dosyayi vermesine yol acar. Bu tuzaga bir kez dusuldu; sebebini bulmak,
 * kazandirdigi her seyden uzun surdu.
 *
 * DEV DALINDA SILME ISLEMI VAR cunku ayni tarayicida once uretim derlemesi
 * acilmis olabilir. O kayit silinmezse gelistirme sunucusunun onune gecmeye
 * devam eder; kaydi birakip "neden guncellenmiyor" diye aramak gerekirdi.
 *
 * load OLAYINI BEKLIYOR: kayit ilk yuklemeyle ayni anda baslasaydi, tarayici
 * sayfayi cizmek icin kullandigi bant genisligini iscinin kurulumuyla
 * paylasirdi. Isci ilk ziyaretin hizini artirmiyor, ikinci ziyaretinkini
 * artiriyor; o yuzden sirada sonra geliyor.
 */
if ("serviceWorker" in navigator) {
  if (import.meta.env.PROD) {
    window.addEventListener("load", () => {
      // Hata yutuluyor: isci kaydedilemezse (ornek: tarayici gizli kip)
      // uygulama tamamen calisiyor, sadece onbellek yok. Kullaniciya
      // gosterilecek bir sorun degil.
      navigator.serviceWorker.register("/sw.js").catch(() => {})
    })
  } else {
    navigator.serviceWorker
      .getRegistrations()
      .then((kayitlar) => kayitlar.forEach((k) => k.unregister()))
      .catch(() => {})
  }
}
