# exchange/utils/calculator.py
import logging
from typing import Dict, Any, Optional

# ExchangeAdapterInterface'i döngüsel importu önlemek için string olarak belirtiyoruz
from ..models.position import Position

async def calculate_follower_amount(
    follower_adapter: "ExchangeAdapterInterface",
    leader_position: Position,
    follower_total_value: float,
    leader_total_value: float,
    leader_intended_leverage: int, # ### YENİ ### Liderin AI komutundan gelen gerçek kaldıracı
) -> Optional[Dict[str, Any]]:
    """
    Takipçinin işlem miktarını ve kaldıracını, tarif edilen mantığa göre hesaplar.

    1. Liderin pozisyon marjının toplam bakiyesine oranına göre takipçi için orantısal marjin hesaplanır.
    2. Bu marjinle açılabilecek pozisyon miktarı (kontrat) hesaplanır.
    3. Hesaplanan miktar, borsanın minimum miktar (min_amount) ve minimum maliyet (min_cost) limitlerinden küçükse, bu limitleri karşılayacak şekilde artırılır.
    4. Bu yeni "etkin miktar" için gereken marjin, takipçinin bakiyesini aşıyorsa, işlemi mümkün kılmak için kaldıraç artırılır.
    5. Bakiye yine de yetmezse (veya gereken kaldıraç maksimum limiti aşarsa) işlem iptal edilir.

    Args:
        follower_adapter: Takipçinin borsa adaptörü.
        leader_position: Kopyalanacak lider pozisyonu.
        follower_total_value: Takipçinin toplam hesap değeri (USDT).
        leader_total_value: Liderin toplam hesap değeri (USDT).
        leader_intended_leverage: Liderin işlemi açarken kullandığı asıl kaldıraç.

    Returns:
        Optional[Dict[str, Any]]: {'amount': float, 'leverage': int} içeren bir sözlük veya None.
    """
    log_prefix = f"CALCULATE-AMOUNT ({follower_adapter.api_info.get('user_id')} - {leader_position.symbol})"
    FOLLOWER_MAX_LEVERAGE = 50  # Takipçi için izin verilen maksimum kaldıraç
    FOLLOWER_BUDGET_USAGE_PERCENT = 0.90 # Takipçinin cüzdanının en fazla %95'ini kullan

    try:
        if leader_total_value <= 1.0 or follower_total_value <= 1.0:
            logging.warning(f"{log_prefix}: Lider ({leader_total_value}) veya takipçi ({follower_total_value}) değeri çok düşük.")
            return None

        # --- 1. Gerekli Piyasa Bilgilerini ve Fiyatı Al ---
        market_info = await follower_adapter.get_market_info(leader_position.symbol)
        if not market_info:
            logging.error(f"{log_prefix}: Piyasa bilgileri (limitler) alınamadı.")
            return None
            
        min_cost = market_info.get('cost', {}).get('min')
        min_amount = market_info.get('amount', {}).get('min')

        ticker = await follower_adapter.get_ticker(leader_position.symbol)
        # 'last' fiyatı yoksa 'markPrice' kullan, o da yoksa hata ver
        calc_price = float(ticker.get('last') or leader_position.mark_price)
        if not calc_price or calc_price <= 0:
            logging.error(f"{log_prefix}: Hesaplama için geçerli bir fiyat bulunamadı.")
            return None

        # --- 2. Orantısal Miktarı Hesapla ---
        # Liderin pozisyonu için kullandığı marjini hesapla
        # Pozisyon objesindeki kaldıraç yerine AI'dan gelen gerçek niyeti kullanıyoruz.
        leader_position_notional = leader_position.contracts * leader_position.entry_price
        leader_margin_used = leader_position_notional / leader_intended_leverage
        
        # Liderin marjininin toplam bakiyesine oranını bul
        leader_margin_ratio = leader_margin_used / leader_total_value if leader_total_value > 0 else 0
        
        # Bu oranı takipçiye uygula
        proportional_follower_margin = follower_total_value * leader_margin_ratio
        
        # Takipçinin orantısal pozisyon büyüklüğünü (notional) ve miktarını (kontrat) hesapla
        proportional_follower_notional = proportional_follower_margin * leader_intended_leverage
        proportional_amount = proportional_follower_notional / calc_price if calc_price > 0 else 0
        
        logging.debug(f"{log_prefix}: Orantısal miktar: {proportional_amount:.8f}")

        # --- 3. Borsa Limitlerine Göre Miktarı Ayarla (İsteğinizin 1. Kısmı) ---
        amount_for_min_cost = (min_cost / calc_price) * 1.05 if min_cost and calc_price > 0 else 0 # %1 pay bırak
        
        effective_amount = proportional_amount
        if min_amount and effective_amount < min_amount:
            logging.info(f"{log_prefix}: Miktar ({effective_amount:.8f}), min_amount limitinin ({min_amount}) altında. Miktar artırılıyor.")
            effective_amount = min_amount

        if min_cost and (effective_amount * calc_price) < min_cost:
            logging.info(f"{log_prefix}: Pozisyon değeri ({effective_amount * calc_price:.2f} USDT), min_cost limitinin ({min_cost} USDT) altında. Miktar artırılıyor.")
            effective_amount = amount_for_min_cost
        
        if effective_amount > proportional_amount:
             logging.info(f"{log_prefix}: Orantılı miktar borsa limit(ler)i nedeniyle {effective_amount:.8f} olarak güncellendi.")

        # --- 4. Kaldıracı Ayarla ve Bakiye Kontrolü Yap (İsteğinizin 2. Kısmı) ---
        position_notional_value = effective_amount * calc_price
        follower_safety_budget = follower_total_value * FOLLOWER_BUDGET_USAGE_PERCENT
        
        effective_leverage = abs(int(leader_intended_leverage))

        # Bu pozisyonu açmak için gereken marjini hesapla
        required_margin = position_notional_value / effective_leverage
        
        # Eğer marjin, takipçinin güvenli bütçesini aşıyorsa, kaldıracı artırmayı dene
        if required_margin > follower_safety_budget:
            logging.warning(
                f"{log_prefix}: Liderin kaldıracı ({effective_leverage}x) ile marjin ({required_margin:.2f} USDT) yetersiz "
                f"(Bütçe: {follower_safety_budget:.2f} USDT). Kaldıraç artırımı deneniyor."
            )
            
            # Bu pozisyonu açabilmek için gereken minimum kaldıracı hesapla
            min_leverage_needed = position_notional_value / follower_safety_budget if follower_safety_budget > 0 else float('inf')
            
            if min_leverage_needed > FOLLOWER_MAX_LEVERAGE:
                logging.error(
                    f"{log_prefix}: İŞLEM İPTAL. "
                    f"Gereken min. kaldıraç ({min_leverage_needed:.1f}x) > İzin verilen maks. kaldıraç ({FOLLOWER_MAX_LEVERAGE}x)."
                )
                return None
            
            # Yeni etkin kaldıracı belirle (gerekli olanın biraz üstü ve tam sayı)
            effective_leverage = abs(int(min(FOLLOWER_MAX_LEVERAGE, int(min_leverage_needed) + 2)))
            logging.info(
                f"{log_prefix}: Takipçi için etkin kaldıraç {effective_leverage}x olarak ayarlandı. "
                f"(Pozisyon Değeri: {position_notional_value:.2f} USDT)"
            )

        # --- 5. Son Kontroller ve Dönüş ---
        final_required_margin = position_notional_value / effective_leverage
        if final_required_margin > follower_safety_budget:
             logging.error(
                 f"{log_prefix}: Nihai marjin kontrolü BAŞARISIZ. "
                 f"Gereken marjin ({final_required_margin:.2f} USDT) > Güvenlik Limiti ({follower_safety_budget:.2f} USDT)"
             )
             return None

        final_amount = await follower_adapter.normalize_amount(leader_position.symbol, effective_amount)
        if final_amount is None or final_amount <= 0:
            logging.error(f"{log_prefix}: Nihai miktar ({effective_amount:.8f}) borsa hassasiyetine göre ayarlanamadı.")
            return None

        logging.info(f"{log_prefix}: BAŞARILI. Nihai emir: Miktar={final_amount}, Kaldıraç={effective_leverage}x")
        return {"amount": final_amount, "leverage": abs(int(effective_leverage))}

    except Exception as e:
        logging.error(f"{log_prefix}: Miktar hesaplama sırasında beklenmedik hata: {e}", exc_info=True)
        return None

async def adjust_amount_for_limits(
    adapter: "ExchangeAdapterInterface",
    symbol: str,
    amount: float
) -> Optional[float]:
    """
    Verilen bir miktarı, ilgili borsanın minimum miktar, minimum maliyet, hassasiyet ve adım limitlerine göre normalleştirir.

    Args:
        adapter: Ayarlama yapılacak borsanın adaptörü.
        symbol: İşlem yapılacak sembol.
        amount: Ayarlanacak miktar.

    Returns:
        float: Borsa limitlerine uygun, normalleştirilmiş nihai miktar veya None.
    """
    log_prefix = f"ADJUST-AMOUNT ({adapter.api_info.get('user_id')} - {symbol})"
    try:
        # --- 1. Gerekli Piyasa Bilgilerini ve Fiyatı Al ---
        market_info = await adapter.get_market_info(symbol)
        if not market_info:
            logging.error(f"{log_prefix}: Piyasa bilgileri (limitler) alınamadı.")
            return None

        min_cost = market_info.get('cost', {}).get('min')
        min_amount = market_info.get('amount', {}).get('min')

        ticker = await adapter.get_ticker(symbol)
        calc_price = float(ticker.get('last') or ticker.get('markPrice'))
        if not calc_price or calc_price <= 0:
            logging.error(f"{log_prefix}: Hesaplama için geçerli bir fiyat bulunamadı.")
            return None

        # --- 2. Borsa Limitlerine Göre Miktarı Ayarla ---
        effective_amount = amount
        
        # Minimum miktar kontrolü
        if min_amount and effective_amount < min_amount:
            logging.info(f"{log_prefix}: Miktar ({effective_amount:.8f}) min_amount limitinin ({min_amount}) altında. Miktar artırılıyor.")
            effective_amount = min_amount

        # Minimum maliyet kontrolü
        if min_cost and (effective_amount * calc_price) < min_cost:
            # Gerekli miktarı %1 marj ile hesapla
            amount_for_min_cost = (min_cost / calc_price) * 1.01 
            logging.info(f"{log_prefix}: Pozisyon değeri ({effective_amount * calc_price:.2f} USDT) min_cost limitinin ({min_cost} USDT) altında. Miktar {amount_for_min_cost:.8f}'a yükseltiliyor.")
            effective_amount = amount_for_min_cost
        
        if effective_amount > amount:
             logging.info(f"{log_prefix}: Orantılı miktar borsa limit(ler)i nedeniyle {effective_amount:.8f} olarak güncellendi.")

        # --- 3. Hassasiyete Göre Normalleştir ---
        final_amount = await adapter.normalize_amount(symbol, effective_amount)
        if final_amount is None:
            logging.error(f"{log_prefix}: Miktar ({effective_amount}) hassasiyet ayarlaması sırasında hata oluştu.")
            return None
            
        return final_amount

    except Exception as e:
        logging.error(f"{log_prefix}: Miktar ayarlama sırasında beklenmedik hata: {e}", exc_info=True)
        return None