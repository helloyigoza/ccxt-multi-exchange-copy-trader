# CCXT Multi-Exchange Copy Trading System

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CCXT](https://img.shields.io/badge/CCXT-4.0+-green.svg)](https://github.com/ccxt/ccxt)

> **Türkçe**: Çoklu borsa kopya trading sistemi - Lider işlemlerini takipçilere anında kopyalar
> **English**: Multi-exchange copy trading system - Instantly replicates leader trades to followers

## 🚀 Features / Özellikler

### ⭐ Core Features / Temel Özellikler
- **Multi-Exchange Support / Çoklu Borsa Desteği**: Binance, Bybit and more (modular adapter system)
- **Real-Time Replication / Gerçek Zamanlı Kopyalama**: Instantly replicates leader trades to followers in milliseconds
- **Risk Management / Risk Yönetimi**: Optimizes position sizes based on account values
- **Leverage Management / Kaldıraç Yönetimi**: Automatic leverage settings and synchronization
- **Position Management / Pozisyon Yönetimi**: Full support for opening, closing, and partial operations
- **Error Tolerance / Hata Toleransı**: Automatic retry mechanisms for network issues and API limits

### 🔧 Technical Features / Teknik Özellikler
- **Asynchronous Architecture / Asenkron Mimar**: High-performance async/await structure
- **Modular Design / Modüler Tasarım**: Easy expansion for new exchange integration
- **Type Safety / Tip Güvenliği**: Full type hint support
- **Comprehensive Logging / Geniş Loglama**: Detailed transaction records and error tracking
- **Configuration Management / Konfigürasyon Yönetimi**: JSON-based API key management

## 📋 Requirements / Gereksinimler

- Python 3.8+
- CCXT library
- AsyncIO support

## 🛠️ Installation / Kurulum

### 1. Clone the Project / Projeyi Klonlayın
```bash
git clone https://github.com/yigoza/ccxt-multi-exchange-copy-trader.git
cd ccxt-multi-exchange-copy-trader
```

### 2. Create Virtual Environment / Sanal Ortam Oluşturun
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or / veya
venv\Scripts\activate     # Windows
```

### 3. Install Dependencies / Bağımlılıkları Yükleyin
```bash
pip install -r requirements.txt
```

### 4. Configure Files / Konfigürasyon Dosyalarını Ayarlayın
```bash
cp config/api_keys_example.json config/api_keys.json
# Edit api_keys.json and add your API keys
# api_keys.json dosyasını düzenleyin ve API anahtarlarınızı ekleyin
```

## ⚙️ Configuration / Konfigürasyon

### API Keys Configuration / API Anahtarları Yapılandırması

Create `config/api_keys.json` file / `config/api_keys.json` dosyası oluşturun:

```json
{
  "leader": {
    "user_id": "leader_user",
    "exchange_id": "binance",
    "api_key": "your_leader_api_key",
    "api_secret": "your_leader_api_secret",
    "copy_trade_enabled": false
  },
  "followers": [
    {
      "user_id": "follower_1",
      "exchange_id": "binance",
      "api_key": "your_follower1_api_key",
      "api_secret": "your_follower1_api_secret",
      "copy_trade_enabled": true,
      "risk_multiplier": 0.5
    },
    {
      "user_id": "follower_2",
      "exchange_id": "binance",
      "api_key": "your_follower2_api_key",
      "api_secret": "your_follower2_api_secret",
      "copy_trade_enabled": true,
      "risk_multiplier": 1.0
    }
  ]
}
```

### Environment Variables / Çevre Değişkenleri

```bash
export LOG_LEVEL=INFO
export MAX_RETRIES=3
export RETRY_DELAY=1.0
```

## 🚀 Usage / Kullanım

### Basic Usage / Temel Kullanım

```python
from exchange import ExchangeManager, ReplicationService
import asyncio

async def main():
    # Initialize Exchange Manager / Exchange Manager başlat
    manager = ExchangeManager()

    # Set leader API info / Lider API bilgilerini ayarla
    leader_info = {
        "user_id": "leader_user",
        "exchange_id": "binance",
        "api_key": "your_api_key",
        "api_secret": "your_api_secret"
    }
    manager.set_leader_api_info(leader_info)

    # Initialize Replication Service / Replication Service başlat
    replication = ReplicationService(manager)

    # Example order replication / Örnek emir kopyalama
    order = Order(
        id="12345",
        symbol="BTC/USDT",
        type="market",
        side="buy",
        amount=0.001,
        filled=0.001,
        status="closed"
    )

    result = await replication.replicate_action(leader_info, order)
    print(f"Replication result: {result}")
    # print(f"Kopyalama sonucu: {result}")

asyncio.run(main())
```

### Command Line Interface / Komut Satırı Arayüzü

```bash
# Start the system / Sistemi başlat
python -m exchange

# For specific exchange only / Sadece belirli bir borsa için
python -m exchange --exchange binance

# With debug mode / Debug modu ile
python -m exchange --log-level DEBUG
```

## 📊 Architecture / Mimari

```
ccxt-multi-exchange-copy-trader/
├── core/                    # Core system components / Çekirdek sistem bileşenleri
│   └── exchange_manager.py  # Exchange connection management / Borsa bağlantı yönetimi
├── interfaces/             # Abstract interfaces / Soyut arayüzler
│   └── exchange_adapter_interface.py
├── adapters/               # Exchange adapters / Borsa adaptörleri
│   └── binance_adapter.py
├── services/               # Business logic services / İş mantığı servisleri
│   ├── replication_service.py
│   ├── sync_service.py
│   └── command_executor.py
├── models/                 # Data models / Veri modelleri
│   ├── order.py
│   └── position.py
├── utils/                  # Helper tools / Yardımcı araçlar
│   ├── calculator.py
│   ├── helpers.py
│   └── post_only_orders.py
└── config/                 # Configuration files / Konfigürasyon dosyaları
    └── api_keys.json
```

## 🔌 Supported Exchanges / Desteklenen Borsalar

| Exchange / Borsa | Status / Durum | Features / Özellikler |
|------------------|----------------|----------------------|
| Binance | ✅ Full Support / Tam Destek | Spot, Futures, Leverage / Spot, Futures, Kaldıraç |
| Bybit | 🚧 Planned / Planlandı | Futures, Spot |
| KuCoin | 📋 Future / Gelecek | - |
| OKX | 📋 Future / Gelecek | - |

## 📈 Risk Management / Risk Yönetimi

### Position Calculation / Pozisyon Hesaplama
- **Account Value Based / Hesap Değeri Bazlı**: Follower positions are optimized based on account sizes
- **Risk Multiplier / Risk Çarpanı**: Customizable risk level for each follower
- **Min/Max Limits / Minimum/Maksimum Limitler**: Position limits for security

### Leverage Management / Kaldıraç Yönetimi
- **Auto Synchronization / Otomatik Senkronizasyon**: Leader leverage settings are copied to followers
- **Margin Mode / Marjin Modu**: Isolated/Cross margin support
- **Risk Controls / Risk Kontrolleri**: Liquidation protection

## 🔍 Monitoring and Logging / İzleme ve Loglama

### Log Levels / Log Seviyeleri
- **DEBUG**: Detailed transaction information
- **INFO**: General transaction summaries
- **WARNING**: Warnings and potential issues
- **ERROR**: Errors and failed transactions
- **CRITICAL**: Critical system errors

### Metrics / Metrikler
- Success/failure replication rates
- Average response times
- API usage statistics
- Error distribution analysis

## 🧪 Testing / Test

```bash
# Run all tests / Tüm testleri çalıştır
pytest

# Run specific test modules / Belirli test modüllerini çalıştır
pytest tests/test_replication.py
pytest tests/test_exchange_manager.py

# With coverage report / Kapsam raporu ile
pytest --cov=exchange --cov-report=html
```

## 📚 API Documentation / API Dokümantasyonu

### ExchangeManager

```python
class ExchangeManager:
    async def get_adapter(api_info: Dict[str, Any]) -> ExchangeAdapterInterface
    async def close_all_adapters() -> None
    def set_leader_api_info(leader_info: Dict[str, Any]) -> None
```

### ReplicationService

```python
class ReplicationService:
    async def replicate_action(leader_api_info: Dict[str, Any], leader_order: Order) -> Dict[str, Any]
```

### ExchangeAdapterInterface

```python
class ExchangeAdapterInterface(ABC):
    async def connect() -> None
    async def close() -> None
    async def get_positions() -> List[Position]
    async def place_order(symbol: str, order_type: str, side: str, amount: float, ...) -> Order
    async def set_leverage(symbol: str, leverage: int, margin_mode: str = 'isolated') -> bool
    async def get_total_account_value_usdt() -> Optional[float]
```

## 🤝 Contributing / Katkıda Bulunma

1. Fork the project / Fork edin
2. Create feature branch / Feature branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Commit your changes / Commit edin (`git commit -m 'Add amazing feature'`)
4. Push to the branch / Push edin (`git push origin feature/amazing-feature`)
5. Create Pull Request / Pull Request oluşturun

### Development Standards / Geliştirme Standartları
- **Code Style / Kod Stili**: PEP 8
- **Type Hints / Type Hints**: Required / Zorunlu
- **Documentation / Dokümantasyon**: For all public functions / Tüm public fonksiyonlar için
- **Tests / Testler**: Unit tests for new features / Yeni özellikler için unit testler

## 📄 License / Lisans

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
Bu proje MIT lisansı altında lisanslanmıştır. Detaylar için [LICENSE](LICENSE) dosyasına bakın.

## ⚠️ Warnings / Uyarılar

- **Real Money Risk / Gerçek Para Riski**: This software performs real cryptocurrency transactions
- **API Limits / API Limitleri**: Pay attention to exchange API limits
- **Security / Güvenlik**: Store your API keys securely
- **Test Environment / Test Ortamı**: Try on testnet first

## 📞 Contact / İletişim

- **GitHub Issues**: [Report Issues / Sorun Bildir](https://github.com/yigoza/ccxt-multi-exchange-copy-trader/issues)
- **Discussions**: [Discussions / Tartışmalar](https://github.com/yigoza/ccxt-multi-exchange-copy-trader/discussions)

## 🙏 Acknowledgments / Teşekkürler

- [CCXT](https://github.com/ccxt/ccxt) - For cryptocurrency exchange APIs
- [Python](https://python.org) - Amazing programming language
- All [contributors](https://github.com/yigoza/ccxt-multi-exchange-copy-trader/graphs/contributors)

---

**Author / Yazar**: [yigoza](https://github.com/yigoza)
**License / Lisans**: MIT
**Version / Versiyon**: 1.0.0
