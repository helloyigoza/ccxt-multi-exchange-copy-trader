#!/usr/bin/env python3
"""
Command Line Interface for CCXT Multi-Exchange Copy Trading System
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

from . import ExchangeManager, ReplicationService
from .utils import load_api_keys_from_file

def setup_logging(level: str = "INFO"):
    """Logging yapılandırması"""
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {level}")

    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

def create_parser() -> argparse.ArgumentParser:
    """Komut satırı argümanlarını oluştur"""
    parser = argparse.ArgumentParser(
        description="CCXT Multi-Exchange Copy Trading System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Örnekler:
  %(prog)s --config config/api_keys.json --log-level DEBUG
  %(prog)s --exchange binance --sync-positions
  %(prog)s --test-connection --user-id leader_trader
        """
    )

    parser.add_argument(
        "--config",
        type=str,
        default="config/api_keys.json",
        help="Konfigürasyon dosyası yolu (varsayılan: config/api_keys.json)"
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Log seviyesi (varsayılan: INFO)"
    )

    parser.add_argument(
        "--exchange",
        type=str,
        choices=["binance", "bybit"],
        help="Sadece belirli bir borsa için işlem yap"
    )

    parser.add_argument(
        "--user-id",
        type=str,
        help="Belirli bir kullanıcı için işlem yap"
    )

    # Komutlar
    subparsers = parser.add_subparsers(dest="command", help="Komutlar")

    # Test bağlantısı komutu
    test_parser = subparsers.add_parser("test", help="Bağlantıyı test et")
    test_parser.add_argument("--user-id", required=True, help="Test edilecek kullanıcı ID")

    # Pozisyon senkronizasyonu komutu
    sync_parser = subparsers.add_parser("sync", help="Pozisyonları senkronize et")
    sync_parser.add_argument("--dry-run", action="store_true", help="Gerçek işlem yapmadan simülasyon")

    # Durum kontrolü komutu
    status_parser = subparsers.add_parser("status", help="Sistem durumunu göster")

    # Konfigürasyon doğrulama komutu
    validate_parser = subparsers.add_parser("validate", help="Konfigürasyonu doğrula")

    return parser

async def test_connection(args, config_path: str):
    """Bağlantıyı test et"""
    print(f"🔍 {args.user_id} için bağlantı testi başlatılıyor...")

    try:
        # Konfigürasyonu yükle
        users = load_api_keys_from_file()
        user_config = next((u for u in users if u['user_id'] == args.user_id), None)

        if not user_config:
            print(f"❌ Kullanıcı bulunamadı: {args.user_id}")
            return False

        # Exchange Manager oluştur
        exchange_manager = ExchangeManager()

        # Adaptör al
        adapter = await exchange_manager.get_adapter(user_config)
        if not adapter:
            print("❌ Adaptör oluşturulamadı")
            return False

        # Temel testler
        print("✅ Adaptör oluşturuldu")

        # Hesap değeri kontrolü
        account_value = await adapter.get_total_account_value_usdt()
        if account_value:
            print(f"✅ Hesap değeri: ${account_value:.2f} USDT")
        else:
            print("⚠️  Hesap değeri alınamadı")

        # Pozisyon kontrolü
        positions = await adapter.get_positions()
        print(f"✅ Açık pozisyon sayısı: {len(positions)}")

        # Ticker kontrolü
        ticker = await adapter.get_ticker("BTC/USDT")
        if ticker:
            print(f"✅ BTC/USDT fiyatı: ${ticker.get('last', 'N/A')}")
        else:
            print("⚠️  Ticker bilgisi alınamadı")

        # Bağlantıyı kapat
        await adapter.close()
        await exchange_manager.close_all_adapters()

        print("✅ Bağlantı testi başarılı!")
        return True

    except Exception as e:
        print(f"❌ Bağlantı testi başarısız: {e}")
        logging.exception("Bağlantı testi hatası")
        return False

async def sync_positions(args, config_path: str):
    """Pozisyonları senkronize et"""
    print("🔄 Pozisyon senkronizasyonu başlatılıyor...")

    if args.dry_run:
        print("🔍 Dry-run modu aktif - gerçek işlem yapılmayacak")

    try:
        # Konfigürasyonu yükle
        users = load_api_keys_from_file(only_copy_trade_enabled=True)

        if not users:
            print("❌ Aktif takipçi bulunamadı")
            return False

        print(f"📊 {len(users)} takipçi bulundu")

        # Exchange Manager oluştur
        exchange_manager = ExchangeManager()

        # Her takipçi için pozisyon kontrolü
        for user in users:
            print(f"\n👤 {user['user_id']} kontrol ediliyor...")

            adapter = await exchange_manager.get_adapter(user)
            if not adapter:
                print(f"❌ {user['user_id']} için adaptör oluşturulamadı")
                continue

            positions = await adapter.get_positions()
            print(f"   Pozisyon sayısı: {len(positions)}")

            for pos in positions:
                print(".6f"
            await adapter.close()

        await exchange_manager.close_all_adapters()
        print("✅ Pozisyon senkronizasyonu tamamlandı!")
        return True

    except Exception as e:
        print(f"❌ Senkronizasyon başarısız: {e}")
        logging.exception("Pozisyon senkronizasyonu hatası")
        return False

async def show_status(args, config_path: str):
    """Sistem durumunu göster"""
    print("📊 Sistem Durumu")
    print("=" * 30)

    try:
        # Konfigürasyon kontrolü
        config_file = Path(config_path)
        if config_file.exists():
            print(f"✅ Konfigürasyon dosyası: {config_path}")
        else:
            print(f"❌ Konfigürasyon dosyası bulunamadı: {config_path}")
            return False

        # API anahtarlarını yükle
        users = load_api_keys_from_file()
        if users:
            print(f"✅ Toplam kullanıcı: {len(users)}")

            leaders = [u for u in users if not u.get('copy_trade_enabled', True)]
            followers = [u for u in users if u.get('copy_trade_enabled', False)]

            print(f"   👑 Lider: {len(leaders)}")
            print(f"   👥 Takipçi: {len(followers)}")
        else:
            print("❌ Kullanıcı bulunamadı")

        print("\n✅ Sistem durumu kontrolü tamamlandı!")
        return True

    except Exception as e:
        print(f"❌ Durum kontrolü başarısız: {e}")
        logging.exception("Durum kontrolü hatası")
        return False

async def validate_config(args, config_path: str):
    """Konfigürasyonu doğrula"""
    print("🔍 Konfigürasyon doğrulama başlatılıyor...")

    try:
        # Konfigürasyon dosyasını kontrol et
        config_file = Path(config_path)
        if not config_file.exists():
            print(f"❌ Konfigürasyon dosyası bulunamadı: {config_path}")
            return False

        # API anahtarlarını yükle ve doğrula
        users = load_api_keys_from_file()

        if not users:
            print("❌ Geçerli kullanıcı bulunamadı")
            return False

        print(f"✅ {len(users)} kullanıcı bulundu")

        # Her kullanıcıyı doğrula
        valid_users = 0
        for user in users:
            required_fields = ['user_id', 'exchange_id', 'api_key', 'api_secret']
            missing_fields = [f for f in required_fields if f not in user or not user[f]]

            if missing_fields:
                print(f"❌ {user.get('user_id', 'Unknown')}: Eksik alanlar - {missing_fields}")
            else:
                print(f"✅ {user['user_id']}: Geçerli")
                valid_users += 1

        if valid_users == len(users):
            print(f"\n✅ Tüm {valid_users} kullanıcı konfigürasyonu geçerli!")
            return True
        else:
            print(f"\n⚠️  {valid_users}/{len(users)} kullanıcı konfigürasyonu geçerli")
            return False

    except Exception as e:
        print(f"❌ Konfigürasyon doğrulama başarısız: {e}")
        logging.exception("Konfigürasyon doğrulama hatası")
        return False

async def main():
    """Ana fonksiyon"""
    parser = create_parser()
    args = parser.parse_args()

    # Logging ayarları
    setup_logging(args.log_level)

    print("🚀 CCXT Multi-Exchange Copy Trading System CLI")
    print("=" * 50)

    # Konfigürasyon dosyasını kontrol et
    config_path = args.config

    # Komutları işle
    if args.command == "test":
        success = await test_connection(args, config_path)
    elif args.command == "sync":
        success = await sync_positions(args, config_path)
    elif args.command == "status":
        success = await show_status(args, config_path)
    elif args.command == "validate":
        success = await validate_config(args, config_path)
    else:
        # Komut satırı argümanları olmadan çalıştırılırsa
        if not any([args.exchange, args.user_id]):
            parser.print_help()
            return

        # Varsayılan olarak durum göster
        success = await show_status(args, config_path)

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())
