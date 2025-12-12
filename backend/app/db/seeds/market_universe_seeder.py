"""
Market Universe Seeder

Populates the market_universe table with ~900 curated symbols from major indices.
Run once during initial setup, then use API to manage additions/removals.
"""
from typing import List, Dict
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from loguru import logger

from app.db.models.market_universe import MarketUniverse, MarketRegion, AssetType


# =============================================================================
# CURATED SYMBOL LISTS BY INDEX
# =============================================================================

# S&P 500 - Top 200 by market cap (the most significant)
SP500_TOP = [
    "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "NVDA", "META", "TSLA", "BRK.B", "UNH",
    "XOM", "JNJ", "JPM", "V", "PG", "MA", "HD", "CVX", "MRK", "ABBV",
    "LLY", "PEP", "KO", "COST", "AVGO", "WMT", "MCD", "CSCO", "TMO", "ACN",
    "ABT", "DHR", "NEE", "WFC", "VZ", "DIS", "ADBE", "PM", "TXN", "CMCSA",
    "NKE", "CRM", "RTX", "BMY", "UPS", "HON", "QCOM", "COP", "LOW", "ORCL",
    "T", "INTC", "IBM", "CAT", "GE", "SPGI", "BA", "INTU", "AMD", "AMGN",
    "DE", "AMAT", "GS", "SBUX", "PLD", "AXP", "BLK", "MS", "ISRG", "ELV",
    "MDT", "GILD", "LMT", "ADI", "MDLZ", "BKNG", "SYK", "REGN", "CB", "VRTX",
    "CI", "ADP", "TMUS", "SCHW", "MO", "CVS", "SO", "ZTS", "TJX", "CME",
    "PGR", "DUK", "EOG", "BDX", "C", "ETN", "CL", "BSX", "SLB", "LRCX",
    "NOC", "ITW", "EQIX", "MU", "FI", "PNC", "SHW", "APD", "MMC", "HUM",
    "ICE", "WM", "AON", "MCO", "EMR", "TGT", "SNPS", "ATVI", "CDNS", "KLAC",
    "CSX", "MAR", "ORLY", "USB", "FCX", "GD", "AZO", "NSC", "NXPI", "APH",
    "HCA", "ADSK", "PSA", "TFC", "MCK", "AEP", "PXD", "EW", "MCHP", "MPC",
    "PCAR", "DXCM", "GM", "F", "OXY", "SRE", "ECL", "VLO", "CCI", "CARR",
    "MSCI", "MNST", "KMB", "TEL", "AIG", "PAYX", "GIS", "DVN", "HSY", "A",
    "CTAS", "AFL", "TRV", "JCI", "D", "ROST", "HES", "STZ", "IDXX", "ALL",
    "WELL", "IQV", "PRU", "FTNT", "CMG", "YUM", "KHC", "CTSH", "PSX", "DOW",
    "BIIB", "ROP", "O", "ILMN", "GPN", "VRSK", "AME", "PEG", "BK", "EXC",
    "WEC", "DLR", "KDP", "FAST", "CMI", "XEL", "OTIS", "NEM", "FIS", "DD",
]

# NASDAQ 100 additions (not in S&P 500 top 200)
NASDAQ100_ADDITIONS = [
    "ASML", "MELI", "AEP", "TEAM", "PANW", "CRWD", "WDAY", "ZS", "DDOG", "ABNB",
    "MRVL", "LULU", "CPRT", "SIRI", "RIVN", "LCID", "OKTA", "ROKU", "ZM", "DOCU",
    "SPLK", "PTON", "COIN", "HOOD", "SNAP", "PINS", "TTD", "DASH", "PLTR", "U",
]

# FTSE 100 (UK) - Full index
FTSE100 = [
    "SHEL.L", "AZN.L", "HSBA.L", "ULVR.L", "BP.L", "GSK.L", "RIO.L", "DGE.L", 
    "BATS.L", "REL.L", "LSEG.L", "NG.L", "VOD.L", "PRU.L", "CPG.L", "RKT.L",
    "BA.L", "LLOY.L", "GLEN.L", "AAL.L", "EXPN.L", "III.L", "CRH.L", "SSE.L",
    "ABF.L", "IMB.L", "AHT.L", "BT.A.L", "WPP.L", "STAN.L", "SBRY.L", "SGE.L",
    "NWG.L", "BNZL.L", "INF.L", "TSCO.L", "JMAT.L", "SMT.L", "IHG.L", "RR.L",
    "SKG.L", "ENT.L", "MNDI.L", "HIK.L", "SMIN.L", "LAND.L", "AV.L", "PSON.L",
    "BRBY.L", "SGRO.L", "HLMA.L", "PSN.L", "FRAS.L", "JET.L", "EDV.L", "WEIR.L",
    "AUTO.L", "DCC.L", "ADM.L", "ITRK.L", "SN.L", "MRO.L", "BDEV.L", "RTO.L",
    "SVT.L", "ANTO.L", "SDR.L", "CCH.L", "MGGT.L", "KGF.L", "FLTR.L", "WTB.L",
    "DARK.L", "BME.L", "OCDO.L", "SPX.L", "RS1.L", "AVST.L", "SMDS.L", "TW.L",
    "FERG.L", "ICAG.L", "EVR.L", "CRDA.L", "UU.L", "STJ.L", "RSA.L", "PHNX.L",
    "HSX.L", "BARC.L", "LGEN.L", "CTEC.L", "SLA.L", "AVV.L", "HLN.L", "BATS.L",
]

# DAX 40 (Germany)
DAX40 = [
    "SAP.DE", "SIE.DE", "ALV.DE", "DTE.DE", "AIR.DE", "MBG.DE", "BAS.DE", "MUV2.DE",
    "BMW.DE", "BAYN.DE", "IFX.DE", "ADS.DE", "DB1.DE", "VOW3.DE", "RWE.DE", "DHL.DE",
    "HEN3.DE", "MRK.DE", "CON.DE", "EOAN.DE", "SRT3.DE", "HEI.DE", "BEI.DE", "VNA.DE",
    "FRE.DE", "SY1.DE", "DBK.DE", "ENR.DE", "MTX.DE", "QIA.DE", "ZAL.DE", "PAH3.DE",
    "PUM.DE", "RHM.DE", "HNR1.DE", "1COV.DE", "FME.DE", "LHA.DE", "SHL.DE", "BNR.DE",
]

# CAC 40 (France)
CAC40 = [
    "MC.PA", "OR.PA", "TTE.PA", "SAN.PA", "AI.PA", "SU.PA", "AIR.PA", "BNP.PA",
    "KER.PA", "CS.PA", "DG.PA", "RI.PA", "SAF.PA", "DSY.PA", "HO.PA", "EL.PA",
    "VIE.PA", "ENGI.PA", "CA.PA", "SGO.PA", "ORA.PA", "BN.PA", "ACA.PA", "CAP.PA",
    "PUB.PA", "LR.PA", "ML.PA", "VIV.PA", "GLE.PA", "EN.PA", "STM.PA", "RMS.PA",
    "WLN.PA", "ERF.PA", "ATO.PA", "TEP.PA", "URW.PA", "RNO.PA", "SW.PA", "UBI.PA",
]

# FTSE MIB (Italy)
FTSE_MIB = [
    "ENEL.MI", "ENI.MI", "ISP.MI", "UCG.MI", "STLA.MI", "RACE.MI", "G.MI", "TEN.MI",
    "STMMI.MI", "CNHI.MI", "SRG.MI", "TIT.MI", "PRY.MI", "CPR.MI", "MONC.MI", "AMP.MI",
    "BAMI.MI", "PST.MI", "A2A.MI", "REC.MI", "HER.MI", "LDO.MI", "NEXI.MI", "BMED.MI",
    "BMPS.MI", "DIA.MI", "FBK.MI", "IGD.MI", "INW.MI", "IP.MI", "IRE.MI", "MB.MI",
    "PIRC.MI", "SPM.MI", "SFER.MI", "TRN.MI", "UNI.MI", "US.MI", "BPSO.MI", "IREN.MI",
]

# IBEX 35 (Spain)
IBEX35 = [
    "ITX.MC", "SAN.MC", "IBE.MC", "BBVA.MC", "TEF.MC", "REP.MC", "AMS.MC", "FER.MC",
    "ENG.MC", "REE.MC", "CLNX.MC", "GRF.MC", "MAP.MC", "ACS.MC", "CABK.MC", "IAG.MC",
    "ELE.MC", "AENA.MC", "COL.MC", "MTS.MC", "SAB.MC", "MEL.MC", "ACX.MC", "NTGY.MC",
    "BKT.MC", "FCC.MC", "LOG.MC", "MRL.MC", "PHM.MC", "ROVI.MC", "SLR.MC", "SGRE.MC",
    "VIS.MC", "ALM.MC", "CIE.MC",
]

# SMI 20 (Switzerland)
SMI20 = [
    "NESN.SW", "ROG.SW", "NOVN.SW", "UBSG.SW", "CSGN.SW", "ABBN.SW", "ZURN.SW", 
    "SREN.SW", "GIVN.SW", "CFR.SW", "SIKA.SW", "LONN.SW", "GEBN.SW", "SCMN.SW",
    "SLHN.SW", "PGHN.SW", "ALC.SW", "HOLN.SW", "SOON.SW", "BALN.SW",
]

# Nikkei 225 - Top 50
NIKKEI_TOP50 = [
    "7203.T", "6758.T", "6861.T", "9984.T", "8306.T", "9432.T", "6902.T", "6501.T",
    "4503.T", "6954.T", "7267.T", "8035.T", "9433.T", "6367.T", "4568.T", "7751.T",
    "6594.T", "8058.T", "6098.T", "7974.T", "3382.T", "4063.T", "6506.T", "8411.T",
    "8316.T", "4502.T", "9434.T", "6326.T", "2914.T", "7733.T", "4519.T", "8031.T",
    "6702.T", "8801.T", "9022.T", "6857.T", "4507.T", "8766.T", "6273.T", "7011.T",
    "6301.T", "7201.T", "4661.T", "4901.T", "5108.T", "7269.T", "6752.T", "9020.T",
    "4911.T", "6503.T",
]

# Hang Seng - Top 30
HANG_SENG_TOP30 = [
    "0700.HK", "9988.HK", "0941.HK", "1299.HK", "0005.HK", "1398.HK", "2318.HK",
    "0388.HK", "0939.HK", "3690.HK", "1810.HK", "2020.HK", "0027.HK", "0883.HK",
    "0016.HK", "0011.HK", "1928.HK", "0002.HK", "0003.HK", "0006.HK", "0012.HK",
    "0017.HK", "0066.HK", "0101.HK", "0175.HK", "0267.HK", "0288.HK", "0386.HK",
    "0688.HK", "0762.HK",
]

# Major Global ETFs
MAJOR_ETFS = [
    # US Market
    "SPY", "QQQ", "IWM", "DIA", "VOO", "VTI", "VTV", "VUG", "SCHD", "VYM",
    # Sector
    "XLF", "XLK", "XLE", "XLV", "XLI", "XLY", "XLP", "XLU", "XLB", "XLRE",
    # International
    "EFA", "EEM", "VEA", "VWO", "IEFA", "IEMG",
    # Bonds
    "BND", "AGG", "TLT", "IEF", "SHY", "LQD", "HYG",
    # Commodities
    "GLD", "SLV", "USO", "UNG", "DBA",
    # Volatility
    "VXX", "UVXY",
    # Leveraged (use with caution)
    "TQQQ", "SQQQ", "SPXL", "SPXS",
]


def get_all_symbols() -> List[Dict]:
    """
    Get all curated symbols with metadata.
    Uses a dict to automatically deduplicate symbols.
    
    Returns list of dicts with:
    - symbol
    - region
    - indices
    - asset_type
    - exchange
    - currency
    """
    # Use dict to avoid duplicates - key is symbol
    symbols_dict = {}
    
    def add_symbol(sym, region, indices, asset_type, exchange, currency, priority):
        """Helper to add/update symbol, merging indices if duplicate"""
        if sym in symbols_dict:
            # Merge indices
            existing = symbols_dict[sym]
            existing["indices"] = list(set(existing["indices"] + indices))
        else:
            symbols_dict[sym] = {
                "symbol": sym,
                "region": region,
                "indices": indices,
                "asset_type": asset_type,
                "exchange": exchange,
                "currency": currency,
                "priority": priority,
            }
    
    # S&P 500 Top 200
    for sym in SP500_TOP:
        add_symbol(
            sym=sym,
            region=MarketRegion.US,
            indices=["SP500"],
            asset_type=AssetType.STOCK,
            exchange="NYSE" if sym in ["BRK.B", "JPM", "JNJ", "V", "WMT", "PG", "UNH", "HD", "CVX", "MRK"] else "NASDAQ",
            currency="USD",
            priority=1,
        )
    
    # NASDAQ 100 additions
    for sym in NASDAQ100_ADDITIONS:
        add_symbol(
            sym=sym,
            region=MarketRegion.US,
            indices=["NASDAQ100"],
            asset_type=AssetType.STOCK,
            exchange="NASDAQ",
            currency="USD",
            priority=1,
        )
    
    # FTSE 100 (deduplicated set)
    for sym in set(FTSE100):
        add_symbol(
            sym=sym,
            region=MarketRegion.UK,
            indices=["FTSE100"],
            asset_type=AssetType.STOCK,
            exchange="LSE",
            currency="GBP",
            priority=2,
        )
    
    # DAX 40
    for sym in DAX40:
        add_symbol(
            sym=sym,
            region=MarketRegion.EU,
            indices=["DAX40"],
            asset_type=AssetType.STOCK,
            exchange="XETRA",
            currency="EUR",
            priority=2,
        )
    
    # CAC 40
    for sym in CAC40:
        add_symbol(
            sym=sym,
            region=MarketRegion.EU,
            indices=["CAC40"],
            asset_type=AssetType.STOCK,
            exchange="EURONEXT",
            currency="EUR",
            priority=2,
        )
    
    # FTSE MIB
    for sym in FTSE_MIB:
        add_symbol(
            sym=sym,
            region=MarketRegion.EU,
            indices=["FTSE_MIB"],
            asset_type=AssetType.STOCK,
            exchange="BIT",
            currency="EUR",
            priority=2,
        )
    
    # IBEX 35
    for sym in IBEX35:
        add_symbol(
            sym=sym,
            region=MarketRegion.EU,
            indices=["IBEX35"],
            asset_type=AssetType.STOCK,
            exchange="BME",
            currency="EUR",
            priority=2,
        )
    
    # SMI 20
    for sym in SMI20:
        add_symbol(
            sym=sym,
            region=MarketRegion.EU,
            indices=["SMI20"],
            asset_type=AssetType.STOCK,
            exchange="SIX",
            currency="CHF",
            priority=2,
        )
    
    # Nikkei Top 50
    for sym in NIKKEI_TOP50:
        add_symbol(
            sym=sym,
            region=MarketRegion.ASIA,
            indices=["NIKKEI225"],
            asset_type=AssetType.STOCK,
            exchange="TSE",
            currency="JPY",
            priority=2,
        )
    
    # Hang Seng Top 30
    for sym in HANG_SENG_TOP30:
        add_symbol(
            sym=sym,
            region=MarketRegion.ASIA,
            indices=["HANGSENG"],
            asset_type=AssetType.STOCK,
            exchange="HKEX",
            currency="HKD",
            priority=2,
        )
    
    # ETFs
    for sym in MAJOR_ETFS:
        add_symbol(
            sym=sym,
            region=MarketRegion.US,
            indices=["ETF"],
            asset_type=AssetType.ETF,
            exchange="NYSE" if sym in ["SPY", "DIA", "GLD", "SLV"] else "NASDAQ",
            currency="USD",
            priority=1,
        )
    
    return list(symbols_dict.values())


async def seed_market_universe(db: AsyncSession, force: bool = False) -> Dict:
    """
    Seed the market_universe table with curated symbols.
    
    Args:
        db: Database session
        force: If True, truncate and reseed. If False, only add missing.
        
    Returns:
        Stats dict with counts
    """
    stats = {
        "total_symbols": 0,
        "inserted": 0,
        "skipped": 0,
        "errors": 0,
    }
    
    all_symbols = get_all_symbols()
    stats["total_symbols"] = len(all_symbols)
    
    logger.info(f"Seeding market universe with {len(all_symbols)} symbols...")
    
    # Check existing count
    existing_count = await db.scalar(
        select(func.count()).select_from(MarketUniverse)
    )
    
    if existing_count > 0 and not force:
        logger.info(f"Market universe already has {existing_count} symbols. Use force=True to reseed.")
        # Just add missing symbols
        existing_symbols = set()
        result = await db.execute(select(MarketUniverse.symbol))
        existing_symbols = {row[0] for row in result.fetchall()}
        
        for sym_data in all_symbols:
            if sym_data["symbol"] not in existing_symbols:
                try:
                    universe_entry = MarketUniverse(
                        symbol=sym_data["symbol"],
                        region=sym_data["region"],
                        indices=sym_data["indices"],
                        asset_type=sym_data["asset_type"],
                        exchange=sym_data["exchange"],
                        currency=sym_data["currency"],
                        priority=sym_data["priority"],
                        is_active=True,
                    )
                    db.add(universe_entry)
                    stats["inserted"] += 1
                except Exception as e:
                    logger.error(f"Error adding {sym_data['symbol']}: {e}")
                    stats["errors"] += 1
            else:
                stats["skipped"] += 1
    else:
        # Full seed
        for sym_data in all_symbols:
            try:
                universe_entry = MarketUniverse(
                    symbol=sym_data["symbol"],
                    region=sym_data["region"],
                    indices=sym_data["indices"],
                    asset_type=sym_data["asset_type"],
                    exchange=sym_data["exchange"],
                    currency=sym_data["currency"],
                    priority=sym_data["priority"],
                    is_active=True,
                )
                db.add(universe_entry)
                stats["inserted"] += 1
            except Exception as e:
                logger.error(f"Error adding {sym_data['symbol']}: {e}")
                stats["errors"] += 1
    
    await db.commit()
    
    logger.info(
        f"Market universe seeded: {stats['inserted']} inserted, "
        f"{stats['skipped']} skipped, {stats['errors']} errors"
    )
    
    return stats


async def get_universe_stats(db: AsyncSession) -> Dict:
    """Get statistics about the market universe."""
    
    # Total count
    total = await db.scalar(
        select(func.count()).select_from(MarketUniverse)
    )
    
    # By region
    region_counts = {}
    for region in MarketRegion:
        count = await db.scalar(
            select(func.count()).select_from(MarketUniverse)
            .where(MarketUniverse.region == region)
        )
        region_counts[region.value] = count
    
    # Active vs inactive
    active = await db.scalar(
        select(func.count()).select_from(MarketUniverse)
        .where(MarketUniverse.is_active == True)
    )
    
    return {
        "total": total,
        "active": active,
        "inactive": total - active,
        "by_region": region_counts,
    }
