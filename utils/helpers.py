# exchange/utils/helpers.py
import logging
import json
import os
from typing import List, Dict, Any, Optional

# Projenin crypto_utils modülünün doğru yolda olduğunu varsayıyoruz.
# Eğer yol farklıysa, bu import'un güncellenmesi gerekir.
try:
    from database.crypto_utils import decrypt_data
except ImportError:
    logging.critical("Kripto yardımcı fonksiyonları (database/crypto_utils) yüklenemedi!")
    # Uygulamanın çökmemesi için sahte bir fonksiyon tanımla
    def decrypt_data(data):
        logging.error("decrypt_data fonksiyonu yüklenemediği için çağrılamıyor!")
        return data  # Şifrelenmiş veriyi geri döndürerek hatanın fark edilmesini sağla

def format_symbol_for_ccxt(symbol: str) -> str:
    """
    Bir sembolü CCXT kütüphanesinin genel olarak kullandığı formata (örn. BTC/USDT) dönüştürür.
    Bu güncellenmiş versiyon, sembol sonundaki '-' gibi istenmeyen karakterleri temizler ve
    yalnızca base currency verildiğinde (örn. 'HFT') varsayılan olarak '/USDT' ekler.
    
    Örnekler:
    'BTCUSDT' -> 'BTC/USDT'
    'ETHUSDT:USDT' -> 'ETH/USDT'
    'HFT-' -> 'HFT/USDT'
    'FRAG' -> 'FRAG/USDT'
    """
    if not isinstance(symbol, str) or not symbol:
        return ""
        
    # ':USDT' gibi ekleri ve baştaki/sondaki boşlukları temizle
    symbol = symbol.split(':')[0].strip()

    # YENİ EKLENEN KISIM: Sembol sonundaki '-' karakterini temizle
    # Bu, 'HFT-' gibi girdileri 'HFT' haline getirir.
    symbol = symbol.rstrip('-')

    # Zaten formatlıysa (örn. 'BTC/USDT') dokunma, sadece büyük harfe çevir
    if "/" in symbol:
        return symbol.upper()

    # Yaygın quote para birimlerini dene
    # En uzun olanlar (örn. 'FDUSD') daha kısa olanlardan (örn. 'USD') önce denenmeli
    quote_currencies = ["USDT", "USDC", "BUSD", "FDUSD", "TUSD", "DAI", "TRY", "BTC", "ETH"]
    upper_symbol = symbol.upper()

    for quote in quote_currencies:
        if upper_symbol.endswith(quote):
            base_currency_len = len(upper_symbol) - len(quote)
            if base_currency_len > 0:
                base = upper_symbol[:base_currency_len]
                # Base'in sonunda hala tire kalmış olabilir diye tekrar kontrol et
                base = base.rstrip('-')
                return f"{base}/{quote}"
    
    # YENİ EKLENEN MANTIK: Eğer yukarıdaki döngü bir eşleşme bulamazsa,
    # girdinin sadece bir base currency olduğunu varsay (örn. 'HFT', 'FRAG').
    # Bu durumda en yaygın quote olan USDT'yi ekle.
    # Hata loglarındaki 'H-', 'HFT-', 'FRAG-' gibi tüm girdiler bu bloğa düşecektir.
    if upper_symbol: # Sembolün boş olmadığından emin ol
        logging.debug(f"'{symbol}' için quote para birimi bulunamadı. Varsayılan olarak USDT kullanılıyor.")
        return f"{upper_symbol}/USDT"
    
    logging.warning(f"Sembol '{symbol}' CCXT formatına dönüştürülemedi ve boş olarak döndürüldü.")
    return "" # Hiçbir koşul sağlanmazsa boş string döndürerek hatalı API isteğini önle


async def load_api_keys_from_file(
    file_path: str = "database/api_keys.json",
    only_copy_trade_enabled: bool = False
) -> List[Dict[str, Any]]:
    """
    API anahtarlarını JSON dosyasından yükler, şifrelerini çözer ve bir liste olarak döndürür.

    Args:
        file_path (str): API anahtarlarının bulunduğu JSON dosyasının yolu.
        only_copy_trade_enabled (bool): True ise sadece kopya ticareti aktif
                                        olan kullanıcıları döndürür.

    Returns:
        List[Dict[str, Any]]: Her bir kullanıcı için API bilgilerini içeren sözlük listesi.
    """
    active_apis: List[Dict[str, Any]] = []
    
    if not os.path.exists(file_path):
        logging.warning(f"API anahtar dosyası bulunamadı: {file_path}")
        return []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            all_api_data = json.load(f)

        for user_id, exchanges in all_api_data.items():
            for exchange_id, api_info in exchanges.items():
                
                is_active = api_info.get("status") == "active"
                passes_filter = not only_copy_trade_enabled or api_info.get("copy_trade_enabled") is True

                if is_active and passes_filter:
                    decrypted_key = decrypt_data(api_info.get("api_key"))
                    decrypted_secret = decrypt_data(api_info.get("api_secret"))
                    decrypted_pass = decrypt_data(api_info.get("api_passphrase")) if "api_passphrase" in api_info else None

                    if not decrypted_key or not decrypted_secret:
                        logging.error(f"Kullanıcı {user_id} ({exchange_id}) için API anahtarları çözülemedi.")
                        continue
                    
                    user_api_info = {
                        "user_id": user_id,
                        "exchange_id": exchange_id.lower(),
                        "api_key": decrypted_key,
                        "api_secret": decrypted_secret,
                    }
                    if decrypted_pass:
                        user_api_info["api_passphrase"] = decrypted_pass
                    
                    active_apis.append(user_api_info)

    except json.JSONDecodeError:
        logging.error(f"API anahtar dosyası ({file_path}) geçerli bir JSON formatında değil.")
    except Exception as e:
        logging.error(f"API anahtarları yüklenirken hata: {e}", exc_info=False)
        
    filter_text = "sadece kopyalama aktif" if only_copy_trade_enabled else "tümü"
    return active_apis