#!/usr/bin/env python3
"""
Gelişmiş Kullanım Örneği
CCXT Multi-Exchange Copy Trading System

Bu örnek, gelişmiş özellikleri gösterir:
- Çoklu borsa desteği
- Risk yönetimi
- Özel konfigürasyonlar
- Hata yönetimi
"""

import asyncio
import logging
import json
from typing import Dict, List, Any
from exchange import ExchangeManager, ReplicationService
from exchange.models import Order, Position
from exchange.utils import load_api_keys_from_file

# Logging ayarları
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('advanced_example.log'),
        logging.StreamHandler()
    ]
)

class AdvancedCopyTrader:
    """
    Gelişmiş kopya trading sınıfı
    """

    def __init__(self):
        self.exchange_manager = ExchangeManager()
        self.replication_service = ReplicationService(self.exchange_manager)
        self.active_followers = []

    async def initialize(self, config_path: str = "config/api_keys.json"):
        """
        Sistemi başlat ve konfigürasyonu yükle
        """
        print("🚀 Gelişmiş Copy Trading Sistemi başlatılıyor...")

        # Konfigürasyonu yükle
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except FileNotFoundError:
            print(f"❌ Konfigürasyon dosyası bulunamadı: {config_path}")
            return False

        # Lider bilgilerini ayarla
        if 'leader' in config:
            leader_info = config['leader']
            self.exchange_manager.set_leader_api_info(leader_info)
            print(f"✅ Lider ayarlandı: {leader_info.get('user_id')}")

        # Aktif takipçileri yükle
        self.active_followers = [
            follower for follower in config.get('followers', [])
            if follower.get('copy_trade_enabled', False)
        ]
        print(f"✅ {len(self.active_followers)} aktif takipçi bulundu")

        return True

    async def get_leader_positions(self) -> List[Position]:
        """
        Liderin açık pozisyonlarını al
        """
        leader_info = {
            "user_id": "leader",
            "exchange_id": "binance"
        }

        adapter = await self.exchange_manager.get_adapter(leader_info)
        if not adapter:
            print("❌ Lider adaptörü alınamadı")
            return []

        positions = await adapter.get_positions()
        await adapter.close()

        return positions

    async def replicate_leader_order(self, order: Order) -> Dict[str, Any]:
        """
        Lider emrini tüm takipçilere kopyala
        """
        leader_info = {
            "user_id": "leader_trader",
            "exchange_id": "binance",
            "api_key": "LEADER_API_KEY",
            "api_secret": "LEADER_API_SECRET"
        }

        print(f"📊 Emir kopyalanıyor: {order.symbol} {order.side} {order.amount}")

        result = await self.replication_service.replicate_action(leader_info, order)

        # Sonuçları detaylı logla
        successful = result.get('successful', 0)
        failed = result.get('failed', 0)
        skipped = result.get('skipped', 0)

        print("📈 Kopyalama İstatistikleri:"        print(f"   ✅ Başarılı: {successful}")
        print(f"   ❌ Hatalı: {failed}")
        print(f"   ⏭️  Atlanan: {skipped}")

        return result

    async def monitor_positions(self):
        """
        Tüm hesapların pozisyonlarını izle
        """
        print("\n📊 Pozisyon İzleme Başlatıldı")
        print("=" * 40)

        # Lider pozisyonları
        leader_positions = await self.get_leader_positions()
        print(f"👑 Lider pozisyonları ({len(leader_positions)}):")
        for pos in leader_positions:
            print(".6f"
        # Takipçi pozisyonları
        for follower in self.active_followers:
            adapter = await self.exchange_manager.get_adapter(follower)
            if adapter:
                positions = await adapter.get_positions()
                print(f"👤 {follower['user_id']} pozisyonları ({len(positions)}):")
                for pos in positions:
                    print(".6f"                await adapter.close()

    async def risk_check(self) -> Dict[str, Any]:
        """
        Risk kontrolü yap
        """
        print("\n⚠️  Risk Kontrolü")
        print("=" * 30)

        risk_report = {
            "total_exposure": 0,
            "high_risk_positions": [],
            "warnings": []
        }

        # Tüm pozisyonları kontrol et
        for follower in self.active_followers:
            adapter = await self.exchange_manager.get_adapter(follower)
            if adapter:
                account_value = await adapter.get_total_account_value_usdt()
                positions = await adapter.get_positions()

                for position in positions:
                    exposure = abs(position.unrealized_pnl)
                    risk_report["total_exposure"] += exposure

                    # Yüksek risk kontrolü
                    if position.leverage > 20:
                        risk_report["high_risk_positions"].append({
                            "user": follower["user_id"],
                            "symbol": position.symbol,
                            "leverage": position.leverage
                        })

                await adapter.close()

        # Uyarılar
        if risk_report["total_exposure"] > 1000:
            risk_report["warnings"].append("Toplam maruziyet yüksek!")

        if risk_report["high_risk_positions"]:
            risk_report["warnings"].append(f"{len(risk_report['high_risk_positions'])} yüksek kaldıraç pozisyonu var!")

        return risk_report

async def run_advanced_example():
    """
    Gelişmiş örnek senaryosu
    """
    trader = AdvancedCopyTrader()

    # Sistemi başlat
    if not await trader.initialize():
        return

    try:
        # Risk kontrolü
        risk_report = await trader.risk_check()
        if risk_report["warnings"]:
            print("⚠️  Risk Uyarıları:")
            for warning in risk_report["warnings"]:
                print(f"   - {warning}")

        # Pozisyon izleme
        await trader.monitor_positions()

        # Örnek emir kopyalama
        sample_order = Order(
            id="advanced_123",
            symbol="ETH/USDT",
            type="market",
            side="buy",
            amount=0.1,
            filled=0.1,
            price=3000.0,
            status="closed",
            timestamp_ms=1640995200000,
            raw_data={
                'info': {},
                'params': {},
                'command_details': {
                    'leverage': 5
                }
            }
        )

        await trader.replicate_leader_order(sample_order)

        # Final pozisyon kontrolü
        await trader.monitor_positions()

    except Exception as e:
        print(f"❌ Hata: {e}")
        logging.exception("Gelişmiş örnek çalıştırılırken hata")

    finally:
        # Temizlik
        await trader.exchange_manager.close_all_adapters()
        print("\n🧹 Sistem kapatıldı")

async def multi_exchange_example():
    """
    Çoklu borsa örneği
    """
    print("\n🌐 Çoklu Borsa Örneği")
    print("=" * 30)

    # Farklı borsalar için konfigürasyon
    exchanges = [
        {
            "user_id": "binance_trader",
            "exchange_id": "binance",
            "api_key": "BINANCE_API_KEY",
            "api_secret": "BINANCE_API_SECRET"
        },
        # Gelecekte eklenecek:
        # {
        #     "user_id": "bybit_trader",
        #     "exchange_id": "bybit",
        #     "api_key": "BYBIT_API_KEY",
        #     "api_secret": "BYBIT_API_SECRET"
        # }
    ]

    exchange_manager = ExchangeManager()

    for exchange_config in exchanges:
        adapter = await exchange_manager.get_adapter(exchange_config)
        if adapter:
            print(f"✅ {exchange_config['exchange_id']} bağlantısı başarılı")
            await adapter.close()
        else:
            print(f"❌ {exchange_config['exchange_id']} bağlantısı başarısız")

    await exchange_manager.close_all_adapters()

async def main():
    """
    Ana fonksiyon
    """
    print("🚀 CCXT Gelişmiş Copy Trading Örneği")
    print("=" * 50)

    # Gelişmiş örnek
    await run_advanced_example()

    # Çoklu borsa örneği
    await multi_exchange_example()

    print("\n✅ Gelişmiş örnek tamamlandı!")

if __name__ == "__main__":
    asyncio.run(main())
