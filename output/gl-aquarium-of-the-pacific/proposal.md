# Optimization Proposal

## Executive summary
This page leaks conversion in three ways: (1) the title promises 'Up to 33% Off' but the displayed prices ($29.95 after-3pm and $44.95 general) match the aquarium's own gate prices — the '33% off' is just the math of after-3pm vs. general, not an actual Groupon discount, which will erode trust the moment a buyer cross-checks aquariumofpacific.org. (2) The highlights and fine print are effectively empty ('Need To Know Info', 'Where To Redeem' as bullets), so the most-asked visitor questions — parking, stroller policy, accessibility, what's inside, how long it takes — are answered nowhere. (3) The single biggest competitive insight from reviews is being ignored: the #1 complaint is overcrowding ('fight your way through masses of people'), and the After-3pm ticket is literally the solution — but the page never frames it that way. The fastest wins are reframing the After-3pm ticket as the 'beat the crowds + save $15' option, filling the empty highlights/fine print with real visitor info, and either securing a true discount from the merchant or rewording the title to stop implying one that isn't there.

## Competitive positioning
The merchant's own site sells the same tickets at the same prices ($44.95 adult general, $29.95-tier twilight), so on raw price this Groupon offers no advantage over booking direct. The page therefore needs to win on two non-price levers: (a) the After-3pm ticket as a crowd-avoidance hack — directly addressing the dominant negative review theme ('Great but CROWDED') — and (b) Groupon-specific convenience (one-tap mobile voucher, Groupon's refund/satisfaction backing, 25,000+ already bought as social proof). Against multi-attraction passes (Go City, iVenture), this deal wins for the customer who only wants the aquarium and doesn't want to commit to a $100+ pass. The page should stop pretending to be a discount play and start being the 'smartest way to do the aquarium' play.

## Recommendations
### 1. [highlights] (priority 1)
**Current:** ['Need To Know Info', 'Where To Redeem']

**Proposed:** • Self-guided access to 5 acres of indoor + outdoor exhibits — typical visit ~3 hours
• Hands-on touch tanks including moon jellies and stingrays
• 'After 3pm' ticket = same full access for $15 less and far smaller crowds
• Mobile voucher — show your phone at the gate, no printing
• Backed by Groupon's satisfaction guarantee
• 25,000+ already bought • 4.7★ from 1,600+ Groupon customers

**Why:** The current 'highlights' are section labels, not benefits. The page has zero scannable reasons to buy above the fold. Reviews consistently call out specific experiences ('moon jelly and stingray touch tanks', 'stamp stations for the booklets') and the 3-hour visit length is already in the description body — surface them. The After-3pm crowd-avoidance angle directly answers the #1 negative theme.

**Evidence:** Audit shows highlights = ['Need To Know Info', 'Where To Redeem']. Review quotes: 'My favorite exhibits are the moon jelly and stingray touch tanks'; 'Three hours went by quickly'; 'pick the after 3pm option as it balances price and actual time there'.

**Expected impact:** Largest single conversion lever — turns an empty above-the-fold into 6 concrete reasons to buy and reframes After-3pm as a feature, not a downgrade.

### 2. [competitive_positioning] (priority 1)
**Current:** Generic 'exclusive discount offer delivers savings you won't find elsewhere' line in description.

**Proposed:** Add a callout block: 'Going on a weekend? Pick the After-3pm ticket. Same exhibits, same access — just $29.95 instead of $44.95, and reviewers say crowds thin out noticeably in the late afternoon.'

**Why:** The most consistent negative review theme is overcrowding. The After-3pm ticket is a built-in solution but the page sells it as a cheaper/lesser option rather than a smarter one. A reviewer literally validated this: 'went after 3 pm and the aquarium was not crowded which allowed me to move at my own place.'

**Evidence:** TripAdvisor: 'Great but CROWDED ... fight your way through masses of people'. Yelp: 'it can get quite crowded, especially as we were there on a Sunday'. Groupon review: 'I went after 3 pm and the aquarium was not crowded'.

**Expected impact:** Converts the deal's weakness (no real $-discount on adult general) into a strength (smart-shopper crowd hack), and likely shifts mix toward higher-margin After-3pm units.

### 3. [title] (priority 1)
**Current:** Aquarium of the Pacific Admission Deals – Up to 33% Off Tickets

**Proposed:** Aquarium of the Pacific Tickets — Long Beach | After-3pm Admission $29.95, Skip the Crowds

**Why:** Both displayed prices ($29.95 and $44.95) match the aquarium's own gate prices per aquariumofpacific.org and Instagram listings — the '33% Off' is the delta between after-3pm and general admission, not a real Groupon discount. Customers who price-check (most of them, for a known attraction) will lose trust. Lead with the strongest honest hook instead: a concrete after-3pm price plus the crowd-skip benefit.

**Evidence:** Audit prices: General $44.95 original=deal, After-3pm $29.95 original=deal, both discount_pct = null. Research: 'General Admission Prices (typical tickets)... Adults (12+): about $44.95'. Math: (44.95-29.95)/44.95 = 33.4%, i.e., the '33% off' is After-3pm vs General, not a Groupon savings.

**Expected impact:** Removes a refund/complaint risk from misleading discount framing and improves CTR with a concrete price + a differentiated benefit.

### 4. [pricing_display] (priority 2)
**Current:** Two ticket rows shown with original_price = deal_price; no struck-through price, no visible savings, but title claims 'Up to 33% Off'.

**Proposed:** Either (a) negotiate a real $3–5 markdown with the merchant and display 'Was $44.95 / Now $X' truthfully; or (b) remove the strike-through/savings UI entirely and reframe the After-3pm row as: 'After 3pm Admission — $29.95 (Save $15 vs. General Admission, same full access)'. Add a small line under the General row: 'Same price as the gate — buy here for instant mobile voucher + Groupon's satisfaction guarantee.'

**Why:** The current pricing display promises a discount the data doesn't show. Either make it real or stop implying it. Option (b) keeps the deal honest and still gives customers a reason to buy through Groupon (mobile voucher + guarantee).

**Evidence:** Audit: both rows show original_price == deal_price, discount_pct = null. Trust signals show has_guarantee_text = false despite Groupon's standard guarantee.

**Expected impact:** Reduces post-purchase 'I could have gotten this at the gate' complaints and aligns the on-page promise with reality.

### 5. [missing_content] (priority 2)
**Current:** No info on parking, stroller policy, accessibility, re-entry, or what to bring.

**Proposed:** Add a 'Plan Your Visit' block with: 'Parking: Aquarium parking structure across Shoreline Drive, ~$8/day; get your hand stamped on exit to validate. Strollers: not provided — bring your own. Wheelchairs: complimentary at the info desk, first come first served. Re-entry: allowed same day with hand stamp. Plan ~3 hours; service animals welcome.'

**Why:** These are the highest-frequency questions in the merchant's own FAQ — meaning customers ask them before purchasing. Surfacing them on the deal page reduces pre-purchase abandonment and post-purchase confusion.

**Evidence:** aquariumofpacific.org/visit/parking and /faq pages exist specifically for these questions. TripAdvisor: '$8 for all day seemed very reasonable'. Califoreigners blog: 'As long as you get your hands stamped on the way out, you can reenter... get your parking ticket validated.' Aquarium FAQ: 'Wheelchairs are complimentary... We do not offer strollers.'

**Expected impact:** Reduces pre-purchase drop-off from customers searching elsewhere for logistics, and cuts CS contacts post-purchase.

### 6. [fine_print] (priority 2)
**Current:** "" (empty)

**Proposed:** • Valid for one (1) admission per voucher on the date and ticket type purchased. • Child Admission: ages 3–11; under 3 free at the gate. Adult Admission: ages 12+. • After-3pm ticket valid for entry from 3:00pm until close (typically 6:00pm); same full access as General Admission. • Voucher expires [DATE]. Not valid on certain blackout/event dates — check aquariumofpacific.org/calendar before visiting. • Mobile voucher accepted — no print needed. • Subject to Groupon's standard refund policy.

**Why:** Empty fine print is a top driver of disputes and 1-star reviews on attraction deals. Specifying age bands, what After-3pm actually means (entry window), and blackout-date language pre-empts the most common complaints.

**Evidence:** Audit: fine_print = ''. Description hints at age bands ('Ages 3–11', 'Ages 12+') but they're not in fine print. Aquarium hosts events ('Stars of the Sea and Whale's Tail After Party') which typically create blackout dates.

**Expected impact:** Materially reduces refund requests and 1-star 'didn't work on the day I went' reviews.

### 7. [seo_meta_description] (priority 3)
**Current:** Aquarium of the Pacific Admission Deals – Up to 33% Off Tickets

**Proposed:** Aquarium of the Pacific tickets in Long Beach: General Admission $44.95 or After-3pm $29.95 (skip the crowds). 4.7★ from 1,600+ Groupon buyers, 25,000+ sold. Mobile voucher, instant delivery.

**Why:** Current meta is a duplicate of the H1 and contains the same misleading '33% Off' claim. A meta description should answer 'what is this and why click' in the SERP. Concrete prices + social proof + ticket types = higher SERP CTR.

**Evidence:** Audit shows meta_description == title. Research shows aquarium ticket queries are heavily price-driven ('Aquarium of the Pacific Long Beach ticket prices').

**Expected impact:** Higher organic CTR from Google for branded + price queries.

### 8. [images] (priority 3)
**Current:** 74 images (count only; content unknown).

**Proposed:** Ensure the first 4 hero images are: (1) the moon jelly tank, (2) the stingray/touch tank with a hand interacting, (3) a wide shot of the indoor exhibit hall showing scale, (4) the outdoor lorikeet/seabird area showing the indoor+outdoor footprint. Avoid generic stock fish.

**Why:** Reviews repeatedly cite specific named exhibits as the highlight ('moon jelly and stingray touch tanks'). Image carousel should match the language reviewers use to recommend the place to friends.

**Evidence:** Yelp: 'My favorite exhibits are the moon jelly and stingray touch tanks.' Yelp: 'large with exhibits indoors and outdoors.'

**Expected impact:** Improves above-the-fold engagement and matches imagery to the social-proof narrative.

### 9. [trust_signals] (priority 3)
**Current:** has_rating: true, has_review_count: true, has_bought_label: true, has_guarantee_text: false

**Proposed:** Add a small badge near the buy button: 'Groupon Guarantee — full refund if you're not satisfied.' Keep the existing '25,000+ bought' and 4.7★ prominent.

**Why:** Since this deal doesn't beat the gate price on adult general admission, the rational reason to buy through Groupon (vs. the merchant site) is the guarantee + mobile voucher convenience. That has to be visible.

**Evidence:** Audit: has_guarantee_text = false. Pricing audit shows no actual price advantage on General Admission.

**Expected impact:** Reduces 'why would I buy here vs. the aquarium site' bounce.

### 10. [seo_headings] (priority 4)
**Current:** H2 list duplicates 'Admission Ticket Deals', 'What To Expect During Your Visit', 'Why Grab These Ticket Savings Today' twice each.

**Proposed:** De-dupe to a single instance of each. Replace 'Why Grab These Ticket Savings Today' with 'Why Buy on Groupon' and add a new H2 'Tips to Avoid the Crowds' housing the After-3pm reframe.

**Why:** Duplicated H2s are an SEO smell and create a messy reading flow. The 'Why Grab These Ticket Savings' header reads like ad copy from 2012 and overstates savings that don't exist.

**Evidence:** Audit h2 array contains 'Admission Ticket Deals', 'What To Expect During Your Visit', 'Why Grab These Ticket Savings Today' each listed twice.

**Expected impact:** Cleaner page structure, mild SEO benefit, removes a credibility tell.

### 11. [urgency] (priority 4)
**Current:** ['limited time']

**Proposed:** Replace generic 'limited time' with truthful, specific urgency only if data supports it: e.g., 'Voucher prices locked through [date]' or remove entirely. Do NOT add fake countdowns.

**Why:** For a non-discounted attraction ticket sold year-round, generic 'limited time' urgency is the kind of signal that erodes trust without lifting conversion. If there's no real deadline, drop it.

**Evidence:** Audit shows the only urgency signal is the generic phrase 'limited time' with no scarcity data. Pricing data shows no temporary markdown to anchor urgency to.

**Expected impact:** Small trust improvement; avoids regulatory/marketing-claim risk.

## Open questions for the merchant / ops
- Is there an actual negotiated discount off gate price available from the merchant, or is this purely a distribution deal at gate price? This determines whether we fix the title by adding real savings or by removing the savings claim.
- What is the precise voucher expiration window and are there blackout dates tied to ticketed events like 'Stars of the Sea' / 'Whale's Tail After Party'? Needed for the fine print rewrite.
- Is parking validation actually offered for Groupon ticket holders (the merchant's site implies hand-stamp re-entry validates parking)? Confirming this would let us add a concrete 'parking validated with hand stamp' bullet, which is a known purchase driver.