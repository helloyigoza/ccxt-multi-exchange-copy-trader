#!/usr/bin/env python3
"""
Temel Kullanım Örneği
CCXT Multi-Exchange Copy Trading System

Bu örnek, sistemin temel kullanımını gösterir.
"""

import asyncio
import logging
from exchange import ExchangeManager, ReplicationService
from exchange.models import Order

# Logging ayarları
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def basic_replication_example():
    """
    Temel kopyalama işlemi örneği
    """
    print("🚀 CCXT Multi-Exchange Copy Trading System")
    print("=" * 50)

    # 1. Exchange Manager oluştur
    exchange_manager = ExchangeManager()

    # 2. Lider API bilgilerini ayarla
    leader_info = {
        "user_id": "leader_trader",
        "exchange_id": "binance",
        "api_key": "YOUR_LEADER_API_KEY",
        "api_secret": "YOUR_LEADER_API_SECRET"
    }
    exchange_manager.set_leader_api_info(leader_info)

    # 3. Replication Service oluştur
    replication = ReplicationService(exchange_manager)

    # 4. Örnek emir oluştur (normalde borsa API'sinden gelir)
    sample_order = Order(
        id="1234567890",
        symbol="BTC/USDT",
        type="market",
        side="buy",
        amount=0.001,
        filled=0.001,
        price=50000.0,
        status="closed",
        timestamp_ms=1640995200000,
        raw_data={
            'info': {},
            'params': {}
        }
    )

    # 5. Kopyalama işlemini gerçekleştir
    print("📊 Kopyalama işlemi başlatılıyor...")
    result = await replication.replicate_action(leader_info, sample_order)

    # 6. Sonuçları göster
    print("📈 Kopyalama Sonuçları:")
    print(f"   Toplam takipçi: {result.get('total_followers', 0)}")
    print(f"   Başarılı: {result.get('successful', 0)}")
    print(f"   Hatalı: {result.get('failed', 0)}")
    print(f"   Atlanan: {result.get('skipped', 0)}")

    # 7. Detaylı sonuçları göster
    if result.get('details'):
        print("\n📋 Takipçi Detayları:")
        for detail in result['details']:
            user_id = detail.get('user_id', 'Unknown')
            status = detail.get('status', 'unknown')
            print(f"   {user_id}: {status}")

    return result

async def position_sync_example():
    """
    Pozisyon senkronizasyonu örneği
    """
    print("\n🔄 Pozisyon Senkronizasyonu Örneği")
    print("=" * 40)

    exchange_manager = ExchangeManager()

    # Takipçi adaptörü al
    follower_info = {
        "user_id": "follower_1",
        "exchange_id": "binance",
        "api_key": "YOUR_FOLLOWER_API_KEY",
        "api_secret": "YOUR_FOLLOWER_API_SECRET"
    }

    adapter = await exchange_manager.get_adapter(follower_info)
    if adapter:
        # Pozisyonları al
        positions = await adapter.get_positions()
        print(f"📊 Mevcut pozisyon sayısı: {len(positions)}")

        for position in positions:
            print(f"   {position.symbol}: {position.side} {position.contracts} @ {position.entry_price}")

        # Bağlantıyı kapat
        await adapter.close()
    else:
        print("❌ Adaptör oluşturulamadı")

async def main():
    """
    Ana fonksiyon - tüm örnekleri çalıştırır
    """
    try:
        # Temel kopyalama örneği
        await basic_replication_example()

        # Pozisyon senkronizasyonu örneği
        await position_sync_example()

        print("\n✅ Tüm örnekler başarıyla tamamlandı!")

    except Exception as e:
        print(f"❌ Hata oluştu: {e}")
        logging.exception("Örnek çalıştırılırken hata")

    finally:
        # Tüm bağlantıları kapat
        print("\n🔌 Bağlantılar kapatılıyor...")
        # exchange_manager.close_all_adapters()  # Eğer exchange_manager global olsaydı

if __name__ == "__main__":
    asyncio.run(main())
