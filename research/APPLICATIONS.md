# What COT positioning data is actually for

Written 2026-08-27, from a three-lane literature and practice survey (academic
return-prediction literature; positioning-as-risk literature; documented
practitioner usage), synthesised against this repo's own measured results.
Hand-written synthesis, not script output — no script regenerates this file.

The question this answers: given that three studies here found no directional
signal (FINDINGS.md, CROSS-SECTION.md, MM-FLOW.md), what are the legitimate
uses of this data, and which claims in the wild are folklore?

Evidence grades used below: **[measured here]** = this repo's own results;
**[PR]** = peer-reviewed; **[Staff]** = regulator/central-bank staff work;
**[Prac]** = documented practitioner usage; **[folklore]** = widely repeated,
no independent validation.

---

## 1. Where this repo's findings sit in the literature

The three nulls were not bad luck; they reproduce the post-2015 academic
consensus, reached here independently:

- **Positions do not lead prices; prices lead positions.** Granger-causality
  tests across agricultural markets (Sanders, Irwin & Merrin 2009, *JARE*,
  "Smart Money?"), energy (Sanders, Boris & Manfredo 2004, *Energy
  Economics*; Büyükşahin & Harris 2011, *Energy Journal*, with non-public
  daily CFTC data) all conclude the same thing. Our +0.133 same-week
  flow/return correlation with a dead next-week IC is that fact, measured
  from a different angle. [PR, measured here]
- **Positions add nothing once fundamentals are controlled.** Gorton,
  Hayashi & Rouwenhorst 2013 (*Review of Finance*): across 31 commodities,
  1969-2006, positions correlate with inventories and past prices but carry
  no independent premium; basis and inventories do. [PR]
- **The raw hedging-pressure level does not predict.** Kang, Rouwenhorst &
  Tang 2020 (*JF*, "A Tale of Two Premiums") run the traditional predictive
  regression on lagged hedging-pressure levels, 26 commodities, 1994-2014:
  t = -0.43. [PR]
- **The one classic positive result is fragile and probably dead.** The
  Bessembinder 1992 → De Roon-Nijman-Veld 2000 → Basu & Miffre 2013 chain
  (hedging-pressure risk premia, Sharpe 0.27-0.93) is real and published —
  but it sorts on *smoothed commercial levels* (52-week MA / 12-month
  averages), monthly rebalance, on pre-2010-heavy samples. Maréchal 2023
  (*JFM*) replicates KRT with proper risk adjustment and a financialization
  split: **the insurance premium loses significance post-2004** — exactly
  the era our data covers. Daskalaki, Kostakis & Skiadopoulos 2014 (*JBF*)
  find no commodity factor priced at all, hedging pressure included. [PR]

**The KRT resolution is the single most useful idea from the survey.** Raw
net positioning conflates two premia with opposite signs: a *short-horizon
liquidity-provision premium* (hedgers get paid for accommodating
momentum-chasing speculators — position *changes*, front-loaded in days
1-10 after the as-of date) and a *long-horizon insurance premium*
(smoothed position *levels*). Mixed together they push the unconditional
predictive coefficient toward zero, which is why every naive test — ours
and the literature's — finds nothing. Note what this repo's head-to-head
adds: KRT's liquidity premium *is* short-term reversal harvested through a
positioning proxy. Ranked on identical weeks, pure lagged return printed
+20.6%/yr while MM flow printed zero — so at least for Managed Money flow
with a realistic publication lag, the positioning column is a *noisy proxy
for the reversal factor*, not an independent source of it. Two honest
caveats keep this from being a refutation of KRT: they sort on *commercial*
flow (not Managed Money) over 1994-2014, and their effect is front-loaded
in days 1-10, which a 1-week entry lag mostly consumes. Maréchal finds the
liquidity premium (unlike the insurance premium) still robust post-2004 —
that is the one genuine open tension, and §5 turns it into a test.

## 2. Application: attribution — who drove this week's move

**The best-supported use, and the cheapest to adopt.**

- [measured here] MM flow vs same-week return: +0.133, the strongest number
  in the panel. Specs demonstrably buy what just went up, sell what fell.
- [PR] This is the documented mechanism (noncommercials are trend-followers:
  Sanders-Irwin-Merrin 2009; Moskowitz-Ooi-Pedersen 2012 momentum), and the
  KRT framework formalises whose demand is being accommodated.
- [Prac] It is also the actual product of the best practitioner work: John
  Kemp's energy notes (positioning percentiles in physical units, tied to
  inventories), Saxo/Ole Hansen's weekly ("managed money tends to
  anticipate, accelerate, and amplify moves set in motion by fundamentals"),
  and Peak Trading Research (ex-Cargill quants) whose commercial product
  leads with exactly this flow-vs-same-week-move framing.

Reading a week: price up + specs bought = spec-driven rally (momentum money
holding the bag if it turns). Price up + specs sold = the buying came from
elsewhere — commercial short-covering, physical demand — a structurally
different rally with different holders at the end of it. This never says
what happens next; it says what the move that already happened *was made of*.

## 3. Application: crowding as fragility, not as signal

- [measured here] The vol tilt: low crowding percentile coincides with
  elevated trailing vol (+0.37pp/wk leg gap, p=0.000). Positioning is loudly
  informative about the *risk state* while silent on direction.
- [PR] The mechanism has a name: **convective risk flows** (Cheng, Kirilenko
  & Xiong 2015, *Review of Finance*, with CFTC's internal trader-level
  data). In calm times financial traders absorb hedging demand; in distress
  they shed it and hedgers take the risk back as prices fall. Our vol-tilt
  finding is the public-data shadow of that result. Crowding→tail-risk is
  formalised in equities (Brown, Howard & Lundblad 2022, *RFS*, hedge-fund
  13F crowdedness predicts drawdown severity); the futures version with
  COT-style measures does not exist in print.
- [Prac] Bank positioning weeklies use exactly this framing: "stretched
  positioning" as *reversal risk*, a magnitude-not-direction statement.

**The episode record is a warning against over-trusting net length.** In
the three famous fragility events, COT-visible spec extremes were neither
necessary nor sufficient: LME nickel 2022 — ~80% of the fatal short sat in
OTC bilateral trades invisible to any exchange report (Oliver Wyman
review); cocoa 2024 — managed-money length *peaked before* the vertical
leg, and the blow-off announced itself as **collapsing open interest**
(industry short-covering into vanishing liquidity), not spec length; WTI
April 2020 — an expiry-microstructure event weekly data cannot see (CFTC
Interim Staff Report 2020). Practical consequence: fragility monitoring
should watch **open interest and its rate of change** alongside net
length. A one-sided market with *falling* OI is the historically dangerous
shape.

## 4. Application: structural monitoring

- [PR] **Who trades predicts the joint return distribution.** Büyükşahin &
  Robe 2014 (*JIMF*, internal CFTC data): equity-commodity correlation
  rises with hedge-fund participation, specifically funds active in both
  asset classes. Tang & Xiong 2012 (*FAJ*): the post-2004 rise in
  cross-commodity correlation was concentrated in indexed commodities —
  the financialization fact. Positioning composition is the public gauge
  of this regime.
- [Staff] Official bodies use the data this way and only this way: OFR's
  Hedge Fund Monitor ingests TFF for stability surveillance (and
  consolidates fungible contract variants — standard/e-mini/micro — a
  discipline worth copying; our `contracts.py` chains are the same idea
  applied to renames). The ECB's 2024 oil/gas box uses Managed Money
  positioning plus **Working's T** — the classic speculation-to-hedging-need
  ratio, T = 1 + (spec shorts)/(total hedging) when hedgers are net short —
  to ask whether speculation exceeds what hedgers require. CFTC's own
  economists (Haigh et al. 2005) concluded managed money mainly provides
  liquidity.
- [PR] **The Masters hypothesis (index flows drove 2008 prices) is
  rejected** in the peer-reviewed record (Irwin & Sanders 2012 *Energy
  Economics*, 2013 *Agricultural Economics*), and the popular Masters
  algorithm for inferring index positions from COT was shown to be off by
  ~142k contracts on WTI — a standing warning against clever derived
  metrics on this data.

## 5. What was worth testing next — and what happened when it ran

Every entry respects the repo's hard-won rules: point-in-time everything,
entry lag, orthogonalise against the thing the signal is known to proxy,
and count effective observations before believing anything. Items 1, 2 and
4 were executed the same day this file was written (2026-08-27); results
recorded inline.

1. **Does crowding forecast future realized vol, incrementally to vol's own
   persistence?** The survey found *no published commodity version* of this
   test. The identification trap is documented in our own results: specs
   cut length after vol rises, so crowding is partly a *lagged* vol proxy —
   hence incremental R² over a HAR-style baseline (Corsi 2009), never a raw
   correlation. **RAN — null** (`vol_forecast.py`,
   `research/VOL-FORECAST.md`): partial correlation of crowding with the
   HAR residual −0.0013, pooled p=0.85, mean ΔR² +0.002 against HAR's
   0.223. Instructive detail: within-commodity, crowding vs its own week's
   vol is only +0.011 — the cross-sectional vol tilt is a *between*-
   commodity fact, which is why it cannot forecast within a market's own
   timeline. The pre-specified extremeness secondary printed p=0.004 but at
   ~0.02 partial correlation, positive in only 15/24 commodities (sign test
   p=0.31): flagged, not promoted.
2. **Resolve the KRT tension: commercial flow, not MM flow.** KRT's
   liquidity premium uses *commercial* position changes, and Maréchal finds
   it robust post-2004. **RAN — null** (`hedger_flow.py`,
   `research/HEDGER-FLOW.md`): 1,080 portfolio-weeks 2005–2025, hedger flow
   +1.4%/yr p=0.71, IC −0.0008, orthogonalised +0.2%/yr p=0.96. The
   strongest surviving positioning claim in the literature does not survive
   a 1-week publication lag in this universe. Also learned: the reversal
   benchmark itself is sample-dependent (+8.4%/yr p=0.073 here vs +20.6%
   p=0.000 on 2015+), one more reason not to chase it.
3. **Hong & Yogo 2012 aggregate OI growth** — the one unrefuted
   positioning-adjacent predictor (+0.73%/mo per SD, monthly, index-level,
   macro-timing). A different question (timing the asset class, not picking
   commodities), needs a monthly aggregate frame, and prices here only
   start in 2000 — but the OI column is already in every file. **Not run** —
   the only remaining open item on this list.
4. **Email upgrades (not research).** **DONE** (analysis.py, 2026-08-27):
   attribution phrasing in the headline and bullets (`_flow_read`), an
   "OI (wk)" column, and a "Fragility watch" section that fires on
   positioning extreme + bottom-decile OI contraction (self-calibrated per
   market). Working's T deliberately deferred: slow-moving structural
   metric, adds table width without changing any weekly decision — revisit
   if the structural lane ever becomes the point. All descriptive, all
   consistent with the no-forecast footer.

## 6. What is settled and should stay settled

- No directional use of net positioning levels, percentiles, or MM flow at
  the weekly horizon. Three studies here, and the peer-reviewed consensus,
  agree. [measured here, PR]
- The retail tradition — Briese's COT Index (min-max stochastic of net
  commercial position, >90 bullish / <10 bearish), Larry Williams' WILLCO —
  has never survived an independent test and is directly contradicted by
  the Granger-causality literature. [folklore]
- No practitioner desk credibly claims validated directional forecasting
  from this data; the documented sell-side form is percentiles, z-scores,
  week-over-week flows, and "stretched positioning" risk language. Our
  weekly email is already at that state of the art. [Prac]

## Reading list

Core: Kang, Rouwenhorst & Tang 2020 (*JF*) — the two-premium decomposition;
Cheng, Kirilenko & Xiong 2015 (*RoF*) — convective risk flows; Gorton,
Hayashi & Rouwenhorst 2013 (*RoF*) — fundamentals beat positions; Sanders,
Irwin & Merrin 2009 (*JARE*) — the smart-money debunk; Hong & Yogo 2012
(*JFE*) — open interest as the informative aggregate; Cheng & Xiong 2014
(*ARFE*) — financialization review.

Second ring: Bessembinder 1992 (*RFS*); De Roon-Nijman-Veld 2000 (*JF*);
Basu & Miffre 2013 (*JBF*); Maréchal 2023 (*JFM*) — the post-2004
replication; Fan, Fernandez-Perez, Fuertes & Miffre 2020 (*JFM*,
"Speculative Pressure"); Daskalaki-Kostakis-Skiadopoulos 2014 (*JBF*);
Tang & Xiong 2012 (*FAJ*); Büyükşahin & Robe 2014 (*JIMF*); Brunnermeier &
Pedersen 2009 (*RFS*); Brown, Howard & Lundblad 2022 (*RFS*); Brunetti,
Büyükşahin & Harris 2016 (*JFQA*); Wang 2001/2002 (*JFM*); Irwin & Sanders
2012/2013 (Masters hypothesis); Bessembinder & Seguin 1993 (*JFQA*); Corsi
2009 (HAR model, for next-test #1). Staff/episode: CFTC Interim Staff
Report on WTI April 2020; Oliver Wyman LME nickel review 2023; ECB Economic
Bulletin 2/2024 box; OFR Hedge Fund Monitor (TFF); CFTC Explanatory Notes
(the pitfalls: self-reported Form 40 classification, predominant-purpose
categories, spreading excludes inter-market spreads, CIT imprecision).

Flagged as unverified by the survey (do not cite without checking): the
Hollstein-Prokopczuk-Tharann 2021 factor-audit's exact treatment of hedging
pressure (paywalled); Lou & Polk "Comomentum" publication venue; one 2024
MDPI paper on vol-regime transitions (fetch blocked).
