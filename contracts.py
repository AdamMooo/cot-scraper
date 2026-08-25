"""
Canonical commodity definitions: which CFTC market names are the *same*
contract over time, and which price series each maps to.

Why this file exists: CFTC market names change when an exchange is renamed
or a contract is re-specced, and the naive approach (treat every distinct
name as its own market) silently shatters a 40-year history into fragments.
That is not cosmetic -- it corrupts any percentile or ranking computed
against "its own history". Real examples found in this data on 2026-08-25:

  - Copper's history split at Feb 2022 ("COPPER-GRADE #1" -> "COPPER- #1"),
    so a 33-year series looked like a 205-week one and every reading looked
    like an all-time extreme.
  - Cocoa/coffee/sugar were split SIX ways by successive renamings of the
    Coffee, Sugar & Cocoa Exchange -> NYBOT -> ICE.
  - Crude was being read off "CRUDE OIL, LIGHT SWEET-WTI - ICE FUTURES
    EUROPE" (a secondary ICE listing) while being priced against NYMEX WTI.
    The real NYMEX chain is CRUDE OIL, LIGHT 'SWEET' -> CRUDE OIL, LIGHT
    SWEET -> WTI-PHYSICAL.

CHAINS are ordered oldest-first and are stitched by date with de-duplication,
so a transition month where CFTC reported both names does not double-count.

Two kinds of name collision must NOT be stitched, and are deliberately absent:
  - Genuinely co-trading contracts on different exchanges (CORN - CHICAGO
    BOARD OF TRADE vs CORN - MIDAMERICA COMMODITY EXCHANGE, which overlap
    1986-2000). Only the flagship contract is listed.
  - Size variants of a live contract (MICRO GOLD alongside GOLD), which
    would double-count the same underlying exposure.

Caveat worth knowing when reading results: two chains splice across a
contract *re-specification*, not just a rename -- LIVE HOGS -> LEAN HOGS
(1996, changed from liveweight to carcass basis) and UNLEADED GASOLINE ->
RBOB (2006, changed to an ethanol-blendable blendstock). Positioning in
contract counts is comparable across those breaks; the underlying deliverable
is not identical.

Public interface:
    COMMODITIES                      -- {canonical name: Commodity}
    stitch(by_market, commodity)     -> [(as_of, net_noncommercial)]
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Commodity:
    ticker: str  # Yahoo Finance continuous-future symbol
    sector: str
    chain: list[str] = field(default_factory=list)  # exact CFTC names, oldest first


COMMODITIES: dict[str, Commodity] = {
    "Corn": Commodity("ZC=F", "Grains", ["CORN - CHICAGO BOARD OF TRADE"]),
    "Soybeans": Commodity("ZS=F", "Grains", ["SOYBEANS - CHICAGO BOARD OF TRADE"]),
    "Soybean Oil": Commodity("ZL=F", "Grains", ["SOYBEAN OIL - CHICAGO BOARD OF TRADE"]),
    "Soybean Meal": Commodity("ZM=F", "Grains", ["SOYBEAN MEAL - CHICAGO BOARD OF TRADE"]),
    "Wheat (SRW)": Commodity("ZW=F", "Grains", [
        "WHEAT - CHICAGO BOARD OF TRADE",
        "WHEAT-SRW - CHICAGO BOARD OF TRADE",
    ]),
    "Wheat (HRW)": Commodity("KE=F", "Grains", [
        # KCBT's hard red winter contract moved to CBOT after CME bought KCBT.
        "WHEAT - KANSAS CITY BOARD OF TRADE",
        "WHEAT-HRW - CHICAGO BOARD OF TRADE",
    ]),
    "Rough Rice": Commodity("ZR=F", "Grains", [
        "ROUGH RICE - CHICAGO RICE AND COTTON EXCHANGE",
        "ROUGH RICE - MIDAMERICA COMMODITY EXCHANGE",
        "ROUGH RICE - CHICAGO BOARD OF TRADE",
    ]),
    "Cotton": Commodity("CT=F", "Softs", [
        "COTTON NO. 2 - NEW YORK COTTON EXCHANGE",
        "COTTON NO. 2 - NEW YORK BOARD OF TRADE",
        "COTTON NO. 2 - ICE FUTURES U.S.",
    ]),
    "Sugar": Commodity("SB=F", "Softs", [
        "SUGAR NO. 11 - COFFEE, SUGAR & COCOA EXCHANGE",
        "SUGAR NO. 11 - COFFEE,SUGAR AND COCOA EXCHANG",
        "SUGAR NO. 11 - COFFEE,SUGAR AND COCOA EXCHANGE",
        "SUGAR NO. 11 - COFFEE, SUGAR AND COCOA EXCHANGE",
        "SUGAR NO. 11 - NEW YORK BOARD OF TRADE",
        "SUGAR NO. 11 - ICE FUTURES U.S.",
    ]),
    "Coffee": Commodity("KC=F", "Softs", [
        "COFFEE C - COFFEE, SUGAR & COCOA EXCHANGE",
        "COFFEE C - COFFEE,SUGAR AND COCOA EXCHANG",
        "COFFEE C - COFFEE,SUGAR AND COCOA EXCHANGE",
        "COFFEE C - COFFEE, SUGAR AND COCOA EXCHANGE",
        "COFFEE C - NEW YORK BOARD OF TRADE",
        "COFFEE C - ICE FUTURES U.S.",
    ]),
    "Cocoa": Commodity("CC=F", "Softs", [
        "COCOA - COFFEE, SUGAR & COCOA EXCHANGE",
        "COCOA - COFFEE,COCOA AND SUGAR EXCHANG",
        "COCOA - COFFEE,SUGAR AND COCOA EXCHANG",
        "COCOA - COFFEE,SUGAR AND COCOA EXCHANGE",
        "COCOA - COFFEE, SUGAR AND COCOA EXCHANGE",
        "COCOA - NEW YORK BOARD OF TRADE",
        "COCOA - ICE FUTURES U.S.",
    ]),
    "Live Cattle": Commodity("LE=F", "Livestock", ["LIVE CATTLE - CHICAGO MERCANTILE EXCHANGE"]),
    "Feeder Cattle": Commodity("GF=F", "Livestock", ["FEEDER CATTLE - CHICAGO MERCANTILE EXCHANGE"]),
    "Lean Hogs": Commodity("HE=F", "Livestock", [
        # Re-spec, not just a rename: liveweight -> carcass basis in 1996.
        "LIVE HOGS - CHICAGO MERCANTILE EXCHANGE",
        "LEAN HOGS - CHICAGO MERCANTILE EXCHANGE",
    ]),
    "Class III Milk": Commodity("DC=F", "Livestock", [
        "MILK - CHICAGO MERCANTILE EXCHANGE",
        "MILK, Class III - CHICAGO MERCANTILE EXCHANGE",
    ]),
    "WTI Crude": Commodity("CL=F", "Energy", [
        "CRUDE OIL, LIGHT 'SWEET' - NEW YORK MERCANTILE EXCHANGE",
        "CRUDE OIL, LIGHT SWEET - NEW YORK MERCANTILE EXCHANGE",
        "WTI-PHYSICAL - NEW YORK MERCANTILE EXCHANGE",
    ]),
    "Natural Gas": Commodity("NG=F", "Energy", [
        "NATURAL GAS - NEW YORK MERCANTILE EXCHANGE",
        "NAT GAS NYME - NEW YORK MERCANTILE EXCHANGE",
    ]),
    "NY Harbor ULSD": Commodity("HO=F", "Energy", [
        "NO. 2 HEATING OIL, N.Y. HARBOR - NEW YORK MERCANTILE EXCHANGE",
        "#2 HEATING OIL, NY HARBOR-ULSD - NEW YORK MERCANTILE EXCHANGE",
        "#2 HEATING OIL- NY HARBOR-ULSD - NEW YORK MERCANTILE EXCHANGE",
        "NY HARBOR ULSD - NEW YORK MERCANTILE EXCHANGE",
    ]),
    "RBOB Gasoline": Commodity("RB=F", "Energy", [
        # Re-spec, not just a rename: unleaded -> ethanol-blendable RBOB, 2006.
        "UNLEADED GASOLINE, N.Y. HARBOR - NEW YORK MERCANTILE EXCHANGE",
        "GASOLINE BLENDSTOCK (RBOB) - NEW YORK MERCANTILE EXCHANGE",
        "GASOLINE RBOB - NEW YORK MERCANTILE EXCHANGE",
    ]),
    "Gold": Commodity("GC=F", "Metals", ["GOLD - COMMODITY EXCHANGE INC."]),
    "Silver": Commodity("SI=F", "Metals", ["SILVER - COMMODITY EXCHANGE INC."]),
    "Copper": Commodity("HG=F", "Metals", [
        "COPPER - COMMODITY EXCHANGE INC.",
        "COPPER-GRADE #1 - COMMODITY EXCHANGE INC.",
        "COPPER- #1 - COMMODITY EXCHANGE INC.",
    ]),
    "Platinum": Commodity("PL=F", "Metals", ["PLATINUM - NEW YORK MERCANTILE EXCHANGE"]),
    "Palladium": Commodity("PA=F", "Metals", ["PALLADIUM - NEW YORK MERCANTILE EXCHANGE"]),
}


def stitch(by_market: dict, commodity: Commodity) -> list[tuple[str, int]]:
    """Splice a commodity's rename chain into one (as_of, net) series.

    Walks the chain oldest-first and keeps the first observation seen for
    any given date, so a transition period where CFTC published both the
    old and new name contributes one row rather than two.
    """
    seen: dict[str, int] = {}
    for name in commodity.chain:
        for as_of, net, _oi in by_market.get(name, []):
            if as_of not in seen:
                seen[as_of] = net
    return sorted(seen.items())
