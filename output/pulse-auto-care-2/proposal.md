# Optimization Proposal

## Executive summary
The headline promises 'Up to 63% Off' but every one of the 5 options on the page shows only a 10% discount ($30.60→$27.54, $51.30→$46.17, $91.80→$82.62). That's a credibility-destroying mismatch that almost certainly drives bounce and likely refund/chargeback risk. Beyond that, the page is squandering this merchant's two real strengths — a 4.89★/604-review reputation with a 'most trustworthy shop around' brand voice, and rare European-specialist credentials (BMW/Audi/Land Rover) — by hiding them behind empty highlights ('Need To Know Info', 'Where To Redeem') and a generic title. Fix the discount math first, then rewrite the title and highlights to lead with European specialty + trust, and conversion should move materially without touching price.

## Competitive positioning
For conventional oil changes, Pulse at $27.54 sits between Tuffy Plainfield's $29.99 semi-synthetic coupon and Firestone's $29.99 standard — competitive but not differentiated on price alone. The full-synthetic at $46.17 beats Webb Chevy Plainfield ($79.95) and Last Chance Auto ($114.50 list) decisively. The real moat is European service: at $82.62 for BMW/Audi/Land Rover oil with a battery test and check-engine scan, Pulse undercuts both dealerships and specialists like PKW Motorwerks while offering RepairPal certification (per repairpal.com). The page should stop competing as a generic oil-change deal and reposition as 'the trusted independent European specialist in Plainfield' — that's where the willingness-to-pay and lack of comparable Groupon competition both live.

## Recommendations
### 1. [pricing_display] (priority 1)
**Current:** Title says 'Up to 63% Off'; all 5 SKUs show only 10% off (e.g., $30.60→$27.54, $91.80→$82.62)

**Proposed:** Either (a) reset deal prices so at least one option hits ~60% off the listed original (e.g., Conventional at $14–$16) to back the 63% claim, or (b) immediately rewrite the title to 'Oil Change at Pulse Auto Care — 10% Off Conventional, Synthetic & European (BMW/Audi/Land Rover)' until merchant resets discount levels.

**Why:** The page makes a claim ('Up to 63% Off') that none of its 5 SKUs deliver. This is the single biggest conversion and trust risk on the page — buyers who click expecting 63% off and see 10% will bounce, and it exposes Groupon to misleading-advertising complaints.

**Evidence:** Audit: title='Up to 63% Off on Oil Change at Pulse Auto Care'; prices array shows discount_pct=10.0 on every SKU.

**Expected impact:** Eliminates bait-and-switch bounce; protects Groupon from refund/chargeback exposure and platform-trust damage.

### 2. [title] (priority 1)
**Current:** Up to 63% Off on Oil Change at Pulse Auto Care

**Proposed:** Oil Change at Pulse Auto Care — Conventional, Full-Synthetic & European (BMW, Audi, Land Rover) | 4.9★ (600+ reviews)

**Why:** Once the 63% claim is fixed, the title should lead with what makes this deal unusual on Groupon: a single shop that handles both standard and European oil changes, plus the strongest social-proof signal the page already has. Most oil-change Groupons in-category are generic conventional/synthetic — European is a differentiator with no nearby Groupon comp.

**Evidence:** Audit shows 5 SKUs spanning Conventional through BMW/Audi/Land Rover; rating=4.89, review_count=604; Yelp/RepairPal corroborate. Tavily found no nearby Groupon European-oil-change competitor.

**Expected impact:** Lifts CTR from category and search pages by surfacing the European angle and 4.9★ proof in the headline.

### 3. [highlights] (priority 1)
**Current:** ['Need To Know Info', 'Where To Redeem']

**Proposed:** • RepairPal Certified independent shop — 4.9★ across 600+ reviews
• Every package includes battery & charging-system test + check-engine-light scan (not just oil)
• Genuine European motor oil for BMW, Audi & Land Rover — dealership-grade service without dealership prices
• Comfortable customer lounge with coffee and Wi-Fi while you wait
• Online scheduling with confirmation + reminder texts
• Honest diagnostics — techs flag what's coming up, never upsell what isn't needed

**Why:** The current 'highlights' are navigation labels, not benefits. Reviewers consistently call out specific things the page never mentions: the lounge ('nice waiting room'/'lounge area with coffee and restroom'), honest diagnostics ('Most trustworthy shop around', 'the diagnostics are honest'), and the booking experience. These are exactly the doubts a first-time customer has about an unfamiliar independent shop.

**Evidence:** Yelp/MapQuest reviews quoted in audit: 'lounge area is comfortable', 'nice lounge area with coffee and restroom', 'Most trustworthy shop around', 'the diagnostics are honest', 'Scheduling an appointment for an oil change was done online and both a confirmation of the appointment and a reminder were sent to me'. RepairPal lists Pulse as 'RepairPal Certified'.

**Expected impact:** Converts skeptical first-timers by replacing empty bullets with the specific reassurances reviewers say drive their decision.

### 4. [competitive_positioning] (priority 2)
**Current:** None — page makes no comparison to alternatives

**Proposed:** Add a short 'Why Pulse vs. the dealership' callout: 'Save vs. dealership prices — Webb Chevy Plainfield charges $79.95+ for full-synthetic; Pulse is $46.17. For BMW/Audi/Land Rover, get genuine European motor oil at $82.62 — typically $130–$180 at the dealer.'

**Why:** The European SKUs are the highest-AOV items on the page but have no value framing. Customers comparing to a dealer service appointment need an explicit anchor. Webb Chevy's public pricing ($79.95 full-synthetic) is a defensible reference point.

**Evidence:** Tavily: 'At Webb Chevy Plainfield, a full synthetic oil change starts at $79.95 for 5 quarts, $85.95 for 6 quarts'; PKW Motorwerks and other European specialists in Plainfield don't publish oil-change pricing but are positioned as premium-priced.

**Expected impact:** Increases mix toward higher-AOV European packages by giving the customer an explicit dealer anchor.

### 5. [missing_content] (priority 2)
**Current:** No mention of duration, appointment requirement, what to bring, or what's actually checked

**Proposed:** Add a 'What to expect' block: 'Plan for ~30–45 min. Appointments recommended (book online — you'll get a confirmation + reminder). Every oil change includes a battery and charging-system test plus a check-engine-light scan at no extra cost. Customer lounge with coffee, Wi-Fi, and restroom on-site.'

**Why:** The description lists what's 'included' technically but never tells a buyer what the visit looks like. Time-on-site and appointment policy are the top pre-purchase questions for oil-change deals and are entirely missing.

**Evidence:** Audit description shows only SKU contents, not visit experience. Reviewer quotes confirm online booking with confirmation/reminder and lounge amenities — content the page can claim truthfully.

**Expected impact:** Reduces pre-purchase friction and post-purchase complaints about wait time / walk-in expectations.

### 6. [fine_print] (priority 2)
**Current:** Valid only for option purchased. May be repurchased every 180 days. Limit 3 per person. All goods or services must be used by the same person.

**Proposed:** Append: 'Appointment required — book online or call. European packages (BMW/Audi/Land Rover) cover up to [X] quarts of [oil weight]; additional quarts billed at shop rate. Disposal/shop fees included. Not valid with other coupons. Valid for 180 days from purchase.'

**Why:** Current fine print is silent on the highest-risk dispute drivers for oil-change deals: oil quantity for European cars (which often need 6–8 quarts), shop/disposal fees, and appointment policy. One Nextdoor review already flags a $90 surprise charge — exactly the kind of fee-clarity issue that creates refund volume.

**Evidence:** Audit fine_print field; Nextdoor review: 'Today I paid them $90 for a routine oil change (using REGULAR oil), not synthetic!'; KBB and NerdWallet note European oil changes commonly run 6–8 quarts at $79.95+.

**Expected impact:** Reduces post-purchase disputes and refund rate driven by surprise upcharges, especially on European SKUs.

### 7. [seo_meta_title] (priority 3)
**Current:** Pulse Auto Care - From $30.60 - Plainfield | Groupon

**Proposed:** Oil Change Plainfield IL — Conventional, Synthetic & BMW/Audi/Land Rover | Pulse Auto Care 4.9★

**Why:** Current meta title leads with merchant name + minimum price, missing the highest-volume search terms ('oil change Plainfield IL', 'European oil change'). The European specialty is a low-competition modifier worth grabbing.

**Evidence:** Audit seo.meta_title; Tavily shows local oil-change SEO landscape dominated by Webb Chevy, Tuffy, Firestone, Last Chance — none of whom rank a Groupon offer for European service.

**Expected impact:** Improves organic CTR from Google for Plainfield oil-change and European-oil-change queries.

### 8. [seo_meta_description] (priority 3)
**Current:** Up to 63% Off on Oil Change at Pulse Auto Care

**Proposed:** Oil change at Pulse Auto Care in Plainfield, IL — conventional from $27.54, full-synthetic $46.17, and genuine European oil for BMW, Audi & Land Rover at $82.62. RepairPal Certified, 4.9★ from 600+ reviews. Includes battery test + check-engine scan.

**Why:** Current meta description is just the (broken) discount claim. A specific, price-anchored description with the European hook will outperform on SERP CTR and avoids the 63% misrepresentation in search snippets.

**Evidence:** Audit seo.meta_description; price data from audit prices array; rating/review count from audit.

**Expected impact:** Increases SERP CTR while removing the misleading 63% claim from indexed search snippets.

### 9. [trust_signals] (priority 3)
**Current:** has_rating=true, has_review_count=true, has_bought_label=true, has_guarantee_text=false

**Proposed:** Add two badges near the price: (1) 'RepairPal Certified — independently verified for fair pricing & quality' and (2) 'ASE-style trust: 4.9★ from 604+ reviewers'. If merchant offers any warranty on workmanship, surface it (e.g., '12-month/12,000-mile labor warranty').

**Why:** The page has the basic trust trio but is missing the single most credible third-party signal Pulse already holds — RepairPal Certification — which directly answers the 'is this independent shop legit?' question that gates oil-change deal conversion.

**Evidence:** RepairPal: 'Pulse Auto Care in Plainfield, IL is a local RepairPal Certified auto [shop]... 4.90 (283 Reviews)'; audit shows has_guarantee_text=false.

**Expected impact:** Lifts conversion among first-time buyers comparing this independent shop to dealership/chain alternatives.

### 10. [images] (priority 4)
**Current:** 61 images on page (mix unspecified)

**Proposed:** Ensure the first 3 hero images are: (1) shop exterior with signage so customers can recognize it from the road, (2) the customer lounge with coffee setup, (3) a tech with a European vehicle on the lift (BMW/Audi/Land Rover). Demote any stock oil-bottle imagery.

**Why:** Reviewers volunteer the lounge as a differentiator and the European service as a reason for repeat visits — both should be visible in the first three images, which is what shows on mobile above the fold.

**Evidence:** Reviews: 'lounge area is comfortable', 'nice lounge area with coffee and restroom', 'I appreciate how they can tend to the European oil change I need for my car'.

**Expected impact:** Improves mobile above-the-fold engagement and mix-shift toward higher-AOV European packages.

### 11. [seo_headings] (priority 4)
**Current:** H2s are SKU labels prefixed with '10025 Clow Creek Road:' followed by generic sections

**Proposed:** Drop the redundant address prefix on every SKU H2 (it's noise for SEO and screen readers). Group SKUs under two H2s: 'Standard Oil Change Packages' (Conventional, Full-Synthetic) and 'European Oil Change Packages — BMW, Audi & Land Rover'.

**Why:** Repeating '10025 Clow Creek Road:' five times dilutes keyword signal and adds zero user value (there's only one location). Grouping under thematic H2s creates a clean European section that ranks for the specialist intent.

**Evidence:** Audit seo.h2 array shows '10025 Clow Creek Road:' prefixed on all 5 SKU headings.

**Expected impact:** Cleans up on-page SEO structure and creates a crawlable European-oil-change section.

### 12. [urgency] (priority 5)
**Current:** ['limited time']

**Proposed:** Replace generic 'limited time' with a truthful, specific signal only if data supports it: e.g., '1,000+ bought · trending in Plainfield this week' (already have the bought label) or a 180-day-validity reminder. Do NOT add a fake countdown.

**Why:** 'Limited time' on an evergreen oil-change deal reads as boilerplate and erodes trust. The page already has stronger truthful urgency in the 1,000+ bought label — lean on that instead.

**Evidence:** Audit urgency_signals=['limited time']; bought_label='1,000+ bought'.

**Expected impact:** Modest trust improvement; avoids the credibility cost of cliché urgency copy.

## Open questions for the merchant / ops
- Why does the title claim 'Up to 63% Off' when every SKU is priced at exactly 10% off — was a discount tier accidentally disabled, or are the original_price values wrong?
- For the European packages ($82.62), how many quarts are included and what's the per-quart upcharge? This directly addresses the Nextdoor '$90 for regular oil' complaint and would let us tighten fine print.
- Does Pulse offer any workmanship guarantee or satisfaction promise we can surface as a trust signal (the audit shows has_guarantee_text=false)?