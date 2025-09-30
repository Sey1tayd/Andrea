# Andrea AI Chat Project

Bu proje, OpenRouter API kullanarak GPT-5 ile sohbet edebileceğiniz bir Django uygulamasıdır.

## Kurulum

1. Sanal ortamı etkinleştirin:
```bash
.\venv\Scripts\Activate.ps1
```

2. Gerekli paketleri yükleyin:
```bash
pip install -r requirements.txt
```

3. `.env` dosyasını düzenleyin ve OpenRouter API anahtarınızı ekleyin:
```env
OPENROUTER_API_KEY=your_actual_api_key_here
```

4. Veritabanı migrasyonlarını çalıştırın:
```bash
python manage.py migrate
```

5. Sunucuyu başlatın:
```bash
python manage.py runserver
```

## Özellikler

- OpenRouter API ile GPT-5 entegrasyonu
- Kullanıcı kayıt sistemi
- Sohbet geçmişi
- Gerçek zamanlı mesajlaşma
- Türkçe dil desteği

## API Yapılandırması

`.env` dosyasında aşağıdaki değişkenleri ayarlayabilirsiniz:

- `OPENROUTER_API_KEY`: OpenRouter API anahtarınız
- `OPENROUTER_BASE_URL`: OpenRouter API URL'i (varsayılan: https://openrouter.ai/api/v1)
- `OPENROUTER_MODEL`: Kullanılacak model (varsayılan: openai/gpt-5)

## Kullanım

1. Uygulamayı başlattıktan sonra `http://127.0.0.1:8000` adresine gidin
2. Kayıt olun veya giriş yapın
3. Ana sayfada yeni bir sohbet başlatın
4. GPT-5 ile sohbet edin!
