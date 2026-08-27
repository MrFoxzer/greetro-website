#!/usr/bin/env python3
"""
Greetro programmatic-SEO location page generator.

Builds:
  locations/<state-slug>.html        (50 US states)
  locations/<city-slug>-<st>.html    (25 major rental-market cities)
  locations/index.html               (hub page)
  sitemap.xml                        (site root)
  robots.txt                         (site root)

Design: every page reuses the existing brand shell (css/style.css, js/main.js,
aurora background, glass nav + footer copied from index.html). Content is
assembled from rotating template variants selected deterministically by
hashing the location name, so pages are regenerable and no two read alike.

Honesty rules baked in: no invented statistics, no "our <city> office"
claims, no fabricated customers. These are service-area pages for a cloud
product available in each location.

Usage:
  python3 tools/generate_locations.py          # generate + validate
  python3 tools/generate_locations.py --check  # validate only
"""

import hashlib
import json
import os
import sys
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "locations")
DOMAIN = "https://greetro.com"
TODAY = "2026-08-26"

# Blog pages (authored by hand in blog/, not generated here) — listed so the
# sitemap stays complete and regenerable from this one script.
BLOG_LASTMOD = "2026-08-27"
BLOG_SLUGS = [
    "answering-service-cost",
    "cost-of-a-missed-call",
    "ai-receptionist-vs-human-receptionist-vs-voicemail",
]

# ---------------------------------------------------------------------------
# DATA — 50 states: (name, abbr, slug, [major real cities], [neighbor slugs
# rendered as names below], one honest hand-written market-color sentence)
# ---------------------------------------------------------------------------

STATES = [
    ("Alabama", "AL", "alabama",
     ["Birmingham", "Huntsville", "Montgomery", "Mobile"],
     ["Georgia", "Florida", "Tennessee", "Mississippi"],
     "From Birmingham's medical district to Huntsville's aerospace and research corridor, Alabama mixes big-city practices with hometown shops that still answer their own phones."),
    ("Alaska", "AK", "alaska",
     ["Anchorage", "Fairbanks", "Juneau", "Wasilla"],
     ["Washington", "Oregon", "California", "Hawaii"],
     "Distances are long and hours are odd in Alaska — clinics in Anchorage, outfitters on the Kenai, and trades in Fairbanks all field calls far outside nine-to-five."),
    ("Arizona", "AZ", "arizona",
     ["Phoenix", "Tucson", "Mesa", "Scottsdale"],
     ["California", "Nevada", "Utah", "New Mexico"],
     "Snowbird season, year-round growth in the Valley, and busy corridors from Tucson to Scottsdale keep Arizona phones ringing — often in more than one language."),
    ("Arkansas", "AR", "arkansas",
     ["Little Rock", "Fayetteville", "Fort Smith", "Springdale"],
     ["Texas", "Oklahoma", "Missouri", "Tennessee"],
     "Between Little Rock's medical offices and the fast-growing Northwest Arkansas corridor around Fayetteville and Springdale, Arkansas businesses juggle growth with small front-desk teams."),
    ("California", "CA", "california",
     ["Los Angeles", "San Diego", "San Francisco", "San Jose", "Sacramento"],
     ["Oregon", "Nevada", "Arizona", "Washington"],
     "From storefront salons in San Diego to law firms in San Francisco and auto shops across the Central Valley, California's sheer scale means the phone never really stops."),
    ("Colorado", "CO", "colorado",
     ["Denver", "Colorado Springs", "Aurora", "Fort Collins"],
     ["Utah", "Wyoming", "Kansas", "New Mexico"],
     "Front Range growth from Denver to Fort Collins keeps service calendars full, while mountain-town businesses deal with seasonal surges no fixed front desk can flex around."),
    ("Connecticut", "CT", "connecticut",
     ["Hartford", "New Haven", "Stamford", "Bridgeport"],
     ["New York", "Massachusetts", "Rhode Island", "New Jersey"],
     "Between commuter towns serving New York and the office corridors of Hartford and Stamford, Connecticut callers expect a fast, professional pickup."),
    ("Delaware", "DE", "delaware",
     ["Wilmington", "Dover", "Newark", "Middletown"],
     ["Maryland", "Pennsylvania", "New Jersey", "Virginia"],
     "Wilmington's legal and financial offices, beach-season businesses in Sussex County, and Dover's steady local trade all lean hard on the phone."),
    ("Florida", "FL", "florida",
     ["Miami", "Tampa", "Orlando", "Jacksonville"],
     ["Georgia", "Alabama", "South Carolina", "Tennessee"],
     "Year-round tourism, huge retiree communities, and bilingual metros from Miami to Tampa make Florida a state where after-hours and Spanish-language calls are everyday business."),
    ("Georgia", "GA", "georgia",
     ["Atlanta", "Savannah", "Augusta", "Columbus"],
     ["Florida", "Alabama", "Tennessee", "South Carolina"],
     "Metro Atlanta's sprawl — Buckhead offices, Marietta trades, Decatur clinics — plus steady port-city commerce in Savannah keeps Georgia's lines busy well past closing."),
    ("Hawaii", "HI", "hawaii",
     ["Honolulu", "Hilo", "Kailua", "Pearl City"],
     ["California", "Washington", "Oregon", "Nevada"],
     "Time zones work against Hawaii businesses — mainland callers ring before you open — and visitor-driven trade means the phone matters seven days a week."),
    ("Idaho", "ID", "idaho",
     ["Boise", "Meridian", "Nampa", "Idaho Falls"],
     ["Washington", "Oregon", "Montana", "Utah"],
     "Boise's rapid growth and the Treasure Valley's building boom mean Idaho clinics, firms, and contractors are fielding more calls with the same small teams."),
    ("Illinois", "IL", "illinois",
     ["Chicago", "Aurora", "Naperville", "Springfield"],
     ["Wisconsin", "Indiana", "Missouri", "Iowa"],
     "From Chicago's neighborhood clinics and law offices to ag-country dealerships downstate, Illinois covers both big-city call volume and small-town relationships."),
    ("Indiana", "IN", "indiana",
     ["Indianapolis", "Fort Wayne", "Evansville", "South Bend"],
     ["Illinois", "Ohio", "Michigan", "Kentucky"],
     "Indianapolis' growing metro, college-town rushes in Bloomington and West Lafayette, and manufacturing towns across the state keep Indiana's phones — and schedules — full."),
    ("Iowa", "IA", "iowa",
     ["Des Moines", "Cedar Rapids", "Davenport", "Iowa City"],
     ["Minnesota", "Illinois", "Missouri", "Nebraska"],
     "Des Moines' insurance and medical offices, college towns like Iowa City and Ames, and farm-country trades give Iowa a phone culture where every call is a neighbor."),
    ("Kansas", "KS", "kansas",
     ["Wichita", "Overland Park", "Kansas City", "Topeka"],
     ["Missouri", "Nebraska", "Oklahoma", "Colorado"],
     "From Wichita's shops and clinics to the fast-growing Johnson County suburbs, Kansas businesses compete on responsiveness as much as price."),
    ("Kentucky", "KY", "kentucky",
     ["Louisville", "Lexington", "Bowling Green", "Owensboro"],
     ["Tennessee", "Ohio", "Indiana", "Virginia"],
     "Louisville's medical corridors, Lexington's clinics and horse-country trades, and small-town firms across Kentucky all lose real money to unanswered rings."),
    ("Louisiana", "LA", "louisiana",
     ["New Orleans", "Baton Rouge", "Shreveport", "Lafayette"],
     ["Texas", "Mississippi", "Arkansas", "Alabama"],
     "New Orleans' service and hospitality economy, Baton Rouge's clinics and firms, and storm-season surges make Louisiana a state where after-hours calls are routine."),
    ("Maine", "ME", "maine",
     ["Portland", "Lewiston", "Bangor", "Augusta"],
     ["New Hampshire", "Vermont", "Massachusetts", "Connecticut"],
     "Seasonal swings are the story in Maine — summer visitors flood Portland and the coast, and year-round trades keep answering straight through the winter."),
    ("Maryland", "MD", "maryland",
     ["Baltimore", "Columbia", "Germantown", "Annapolis"],
     ["Virginia", "Pennsylvania", "Delaware", "West Virginia"],
     "Packed between Baltimore and the D.C. suburbs, Maryland practices and firms serve some of the busiest, most time-pressed callers in the country."),
    ("Massachusetts", "MA", "massachusetts",
     ["Boston", "Worcester", "Springfield", "Cambridge"],
     ["New York", "Connecticut", "Rhode Island", "New Hampshire"],
     "Boston's medical and legal density, college-driven September surges, and year-round trades across the Commonwealth keep Massachusetts front desks stretched."),
    ("Michigan", "MI", "michigan",
     ["Detroit", "Grand Rapids", "Ann Arbor", "Lansing"],
     ["Ohio", "Indiana", "Wisconsin", "Illinois"],
     "From Detroit's rebuilding neighborhoods to Grand Rapids' medical corridors and Up North seasonal trades, Michigan businesses field calls that swing with the seasons."),
    ("Minnesota", "MN", "minnesota",
     ["Minneapolis", "St. Paul", "Rochester", "St. Cloud"],
     ["Wisconsin", "Iowa", "North Dakota", "South Dakota"],
     "From the Twin Cities' clinics and firms to lake-country contractors and Rochester's medical economy, Minnesota businesses answer for callers who expect Midwestern promptness."),
    ("Mississippi", "MS", "mississippi",
     ["Jackson", "Gulfport", "Hattiesburg", "Biloxi"],
     ["Louisiana", "Alabama", "Tennessee", "Arkansas"],
     "Gulf Coast seasonal trade, Jackson's medical offices, and small-town firms across Mississippi all depend on catching the call the first time."),
    ("Missouri", "MO", "missouri",
     ["Kansas City", "St. Louis", "Springfield", "Columbia"],
     ["Kansas", "Illinois", "Iowa", "Arkansas"],
     "Kansas City and St. Louis anchor two busy metros, while Ozark tourism and college towns like Columbia add seasonal spikes to Missouri's call traffic."),
    ("Montana", "MT", "montana",
     ["Billings", "Missoula", "Bozeman", "Great Falls"],
     ["North Dakota", "South Dakota", "Wyoming", "Idaho"],
     "Bozeman and Missoula are growing fast, Billings anchors the east, and Montana's trades cover enormous service areas where a missed call means a long drive wasted."),
    ("Nebraska", "NE", "nebraska",
     ["Omaha", "Lincoln", "Bellevue", "Grand Island"],
     ["Iowa", "Kansas", "South Dakota", "Colorado"],
     "Omaha's insurance and medical employers and Lincoln's steady growth keep Nebraska's metros busy, while rural trades cover wide territories by phone."),
    ("Nevada", "NV", "nevada",
     ["Las Vegas", "Henderson", "Reno", "North Las Vegas"],
     ["California", "Arizona", "Utah", "Oregon"],
     "A 24-hour economy in Las Vegas and fast growth in Reno and Henderson mean Nevada businesses get calls at hours most states sleep through."),
    ("New Hampshire", "NH", "new-hampshire",
     ["Manchester", "Nashua", "Concord", "Dover"],
     ["Maine", "Vermont", "Massachusetts", "Connecticut"],
     "Between Manchester's clinics, Seacoast trades, and White Mountains tourism, New Hampshire businesses handle seasonal surges with famously lean teams."),
    ("New Jersey", "NJ", "new-jersey",
     ["Newark", "Jersey City", "Paterson", "Trenton"],
     ["New York", "Pennsylvania", "Delaware", "Connecticut"],
     "Dense suburbs, commuter schedules, and multilingual communities from Newark to Cherry Hill make New Jersey callers quick to dial the next number if you don't pick up."),
    ("New Mexico", "NM", "new-mexico",
     ["Albuquerque", "Las Cruces", "Santa Fe", "Rio Rancho"],
     ["Arizona", "Texas", "Colorado", "Oklahoma"],
     "Albuquerque and Santa Fe mix medical, legal, and gallery-district trade, and bilingual service is simply expected across much of New Mexico."),
    ("New York", "NY", "new-york",
     ["New York City", "Buffalo", "Rochester", "Syracuse", "Albany"],
     ["New Jersey", "Connecticut", "Pennsylvania", "Massachusetts"],
     "From Manhattan firms to Buffalo clinics and Hudson Valley trades, New York packs the widest range of call volume — and caller expectations — in the country."),
    ("North Carolina", "NC", "north-carolina",
     ["Charlotte", "Raleigh", "Durham", "Greensboro"],
     ["South Carolina", "Virginia", "Tennessee", "Georgia"],
     "Charlotte's banking metro, the Research Triangle's clinics and firms, and mountain and coastal tourism give North Carolina steady growth and steady ringing."),
    ("North Dakota", "ND", "north-dakota",
     ["Fargo", "Bismarck", "Grand Forks", "Minot"],
     ["Minnesota", "South Dakota", "Montana", "Wyoming"],
     "Fargo's growing metro, energy-country trades in the west, and winters that break furnaces at 2 a.m. make North Dakota a genuinely 24/7 phone state."),
    ("Ohio", "OH", "ohio",
     ["Columbus", "Cleveland", "Cincinnati", "Toledo"],
     ["Michigan", "Indiana", "Pennsylvania", "Kentucky"],
     "Columbus, Cleveland, and Cincinnati anchor three distinct metros, each with clinic corridors, law offices, and trades competing on who answers first."),
    ("Oklahoma", "OK", "oklahoma",
     ["Oklahoma City", "Tulsa", "Norman", "Broken Arrow"],
     ["Texas", "Kansas", "Arkansas", "Missouri"],
     "Oklahoma City and Tulsa keep growing, storm season keeps roofers and adjusters slammed, and rural practices cover big distances by phone."),
    ("Oregon", "OR", "oregon",
     ["Portland", "Eugene", "Salem", "Bend"],
     ["Washington", "California", "Idaho", "Nevada"],
     "Portland's neighborhood clinics and studios, Willamette Valley trades, and coastal seasonal businesses give Oregon a mix of steady and surging call traffic."),
    ("Pennsylvania", "PA", "pennsylvania",
     ["Philadelphia", "Pittsburgh", "Allentown", "Erie"],
     ["New York", "New Jersey", "Ohio", "Maryland"],
     "Philadelphia and Pittsburgh bookend a state full of borough main streets where the local clinic, firm, or garage lives and dies by its phone."),
    ("Rhode Island", "RI", "rhode-island",
     ["Providence", "Warwick", "Cranston", "Pawtucket"],
     ["Massachusetts", "Connecticut", "New York", "New Hampshire"],
     "Rhode Island is small enough that reputation travels fast — Providence practices and coastal seasonal businesses can't afford unanswered calls."),
    ("South Carolina", "SC", "south-carolina",
     ["Charleston", "Columbia", "Greenville", "Myrtle Beach"],
     ["North Carolina", "Georgia", "Tennessee", "Virginia"],
     "Charleston's boom, Greenville's growth, and Myrtle Beach's seasonal flood give South Carolina call patterns that swing hard by month."),
    ("South Dakota", "SD", "south-dakota",
     ["Sioux Falls", "Rapid City", "Aberdeen", "Brookings"],
     ["North Dakota", "Minnesota", "Nebraska", "Montana"],
     "Sioux Falls' medical and financial economy and Black Hills tourism around Rapid City keep South Dakota busier by phone than outsiders expect."),
    ("Tennessee", "TN", "tennessee",
     ["Nashville", "Memphis", "Knoxville", "Chattanooga"],
     ["Kentucky", "Georgia", "Alabama", "North Carolina"],
     "Nashville's surge, Memphis logistics and medicine, and Smoky Mountain tourism make Tennessee a state of fast growth and full calendars."),
    ("Texas", "TX", "texas",
     ["Houston", "Dallas", "Austin", "San Antonio", "Fort Worth"],
     ["Oklahoma", "New Mexico", "Arkansas", "Louisiana"],
     "From Houston's medical center orbit to DFW's sprawl and the Hill Country's trades, Texas runs on volume — of everything, calls included."),
    ("Utah", "UT", "utah",
     ["Salt Lake City", "Provo", "West Valley City", "St. George"],
     ["Colorado", "Arizona", "Nevada", "Idaho"],
     "The Wasatch Front from Provo to Ogden is one of the fastest-growing corridors in the country, and Utah's small teams feel it first on the phone."),
    ("Vermont", "VT", "vermont",
     ["Burlington", "Montpelier", "Rutland", "Barre"],
     ["New Hampshire", "New York", "Massachusetts", "Maine"],
     "Ski-season surges, Burlington's steady year-round trade, and small teams wearing many hats define Vermont's relationship with the phone."),
    ("Virginia", "VA", "virginia",
     ["Virginia Beach", "Richmond", "Norfolk", "Arlington"],
     ["Maryland", "North Carolina", "Tennessee", "West Virginia"],
     "Northern Virginia's professional density, Richmond's medical and legal offices, and Hampton Roads' trades give Virginia three busy markets in one."),
    ("Washington", "WA", "washington",
     ["Seattle", "Spokane", "Tacoma", "Bellevue"],
     ["Oregon", "Idaho", "Montana", "California"],
     "Seattle's tech-adjacent service economy, Spokane's regional draw, and trades across the Sound keep Washington phones busy in several languages."),
    ("West Virginia", "WV", "west-virginia",
     ["Charleston", "Huntington", "Morgantown", "Wheeling"],
     ["Virginia", "Ohio", "Pennsylvania", "Kentucky"],
     "Mountain distances and tight-knit towns mean West Virginia businesses win on being reachable — the practice that answers is the practice that grows."),
    ("Wisconsin", "WI", "wisconsin",
     ["Milwaukee", "Madison", "Green Bay", "Kenosha"],
     ["Minnesota", "Illinois", "Michigan", "Iowa"],
     "Milwaukee's clinics and firms, Madison's growth, and Northwoods seasonal trades give Wisconsin call patterns as varied as its seasons."),
    ("Wyoming", "WY", "wyoming",
     ["Cheyenne", "Casper", "Laramie", "Gillette"],
     ["Montana", "Colorado", "Utah", "Nebraska"],
     "Huge service areas, energy-cycle swings, and tourist-season surges around Jackson and Cody mean Wyoming businesses take calls from everywhere, anytime."),
]

# ---------------------------------------------------------------------------
# DATA — 25 cities: (name, ST, state name, slug, [real well-known areas],
# one honest hand-written market-color sentence)
# ---------------------------------------------------------------------------

CITIES = [
    ("Minneapolis", "MN", "Minnesota", "minneapolis-mn",
     ["the North Loop", "Uptown", "Northeast", "Dinkytown"],
     "Minneapolis packs clinics, firms, and studios from the North Loop to Uptown, with skyway-connected downtown offices and a metro that expects things to run on time."),
    ("St. Paul", "MN", "Minnesota", "st-paul-mn",
     ["Grand Avenue", "Lowertown", "Highland Park", "Como"],
     "St. Paul's business life runs along Grand Avenue storefronts, Lowertown offices, and neighborhood clinics from Highland Park to Como — steady, loyal, and phone-first."),
    ("St. Cloud", "MN", "Minnesota", "st-cloud-mn",
     ["downtown St. Cloud", "Waite Park", "Sartell", "Sauk Rapids"],
     "St. Cloud anchors Central Minnesota — clinics, law offices, and trades serving Waite Park, Sartell, and Sauk Rapids — where word-of-mouth still wins the work."),
    ("Rochester", "MN", "Minnesota", "rochester-mn",
     ["downtown Rochester", "the Mayo Clinic district", "northwest Rochester", "south Broadway"],
     "Rochester's economy orbits the Mayo Clinic — hotels, practices, and services downtown all serve visitors and patients on tight, unforgiving schedules."),
    ("Fargo", "ND", "North Dakota", "fargo-nd",
     ["downtown Broadway", "West Fargo", "the NDSU area", "south Fargo"],
     "Fargo pairs a fast-growing metro with genuine winter urgency — Broadway offices, West Fargo trades, and NDSU-area businesses all know a 2 a.m. no-heat call is real."),
    ("Chicago", "IL", "Illinois", "chicago-il",
     ["the Loop", "Lincoln Park", "Wicker Park", "River North", "Hyde Park"],
     "From Loop law firms to Wicker Park salons and neighborhood clinics on the North and South Sides, Chicago is a city of storefront businesses competing block by block."),
    ("New York", "NY", "New York", "new-york-ny",
     ["Manhattan", "Brooklyn", "Queens", "the Bronx"],
     "Across Manhattan, Brooklyn, Queens, and the Bronx, New York callers are the least patient on earth — the business that picks up first usually wins."),
    ("Los Angeles", "CA", "California", "los-angeles-ca",
     ["Santa Monica", "Silver Lake", "Downtown LA", "the Valley"],
     "Los Angeles sprawls from Santa Monica studios to Valley auto shops and Downtown firms — a market where drive time makes the phone the real front door."),
    ("Houston", "TX", "Texas", "houston-tx",
     ["the Heights", "Montrose", "the Galleria area", "the Katy corridor"],
     "Houston's scale — the Medical Center orbit, the Heights, the Galleria, the Katy corridor — means every practice competes with a dozen more a few exits away."),
    ("Dallas", "TX", "Texas", "dallas-tx",
     ["Uptown", "Deep Ellum", "Oak Lawn", "the Plano and Frisco suburbs"],
     "Dallas moves fast, from Uptown firms to Deep Ellum studios and the booming northern suburbs around Plano and Frisco — callers rarely leave voicemails twice."),
    ("Austin", "TX", "Texas", "austin-tx",
     ["South Congress", "East Austin", "The Domain", "Round Rock"],
     "Austin's growth from South Congress to The Domain keeps clinics, salons, and firms slammed — and new arrivals pick their providers by who answers."),
    ("San Antonio", "TX", "Texas", "san-antonio-tx",
     ["the Pearl district", "Alamo Heights", "Stone Oak", "the Medical Center"],
     "San Antonio blends Pearl-district polish with neighborhood loyalty across Alamo Heights and the Medical Center — and bilingual service is simply expected."),
    ("Phoenix", "AZ", "Arizona", "phoenix-az",
     ["Scottsdale", "Tempe", "Arcadia", "Chandler"],
     "Metro Phoenix runs from Scottsdale practices to Tempe shops and Chandler suburbs, with snowbird season swelling call volume for months at a stretch."),
    ("Denver", "CO", "Colorado", "denver-co",
     ["LoDo", "RiNo", "Capitol Hill", "Cherry Creek"],
     "Denver's LoDo and RiNo offices, Cherry Creek practices, and Highlands storefronts serve a young, mobile population that books everything by phone or text."),
    ("Seattle", "WA", "Washington", "seattle-wa",
     ["Capitol Hill", "Ballard", "South Lake Union", "Fremont"],
     "From Capitol Hill clinics to Ballard trades and South Lake Union offices, Seattle expects competence — and its multilingual neighborhoods expect to be understood."),
    ("Atlanta", "GA", "Georgia", "atlanta-ga",
     ["Buckhead", "Midtown", "Decatur", "the Old Fourth Ward"],
     "Atlanta's sprawl from Buckhead to Decatur and Sandy Springs means callers ring from the car — and if you miss them, Midtown has alternatives."),
    ("Miami", "FL", "Florida", "miami-fl",
     ["Brickell", "Wynwood", "Coral Gables", "Little Havana"],
     "Brickell offices, Coral Gables practices, Wynwood studios — Miami does business in two languages by default, and the phone is where that shows first."),
    ("Tampa", "FL", "Florida", "tampa-fl",
     ["Ybor City", "Hyde Park", "Westshore", "Seminole Heights"],
     "Tampa's Westshore offices, Hyde Park storefronts, and Ybor character — plus St. Pete across the bay — make a fast-growing, phone-heavy service market."),
    ("Orlando", "FL", "Florida", "orlando-fl",
     ["Winter Park", "Lake Nona", "College Park", "Dr. Phillips"],
     "Orlando's economy serves both a world of visitors and fast-growing neighborhoods from Winter Park to Lake Nona — schedules churn, and calls come at all hours."),
    ("Charlotte", "NC", "North Carolina", "charlotte-nc",
     ["Uptown", "South End", "NoDa", "Ballantyne"],
     "Charlotte's Uptown banks anchor a metro of South End studios, NoDa storefronts, and Ballantyne practices, all growing faster than their front desks."),
    ("Nashville", "TN", "Tennessee", "nashville-tn",
     ["The Gulch", "East Nashville", "Green Hills", "Franklin"],
     "Nashville's boom runs from The Gulch to East Nashville and out to Franklin — new residents pick clinics, salons, and firms by who picks up."),
    ("Las Vegas", "NV", "Nevada", "las-vegas-nv",
     ["Summerlin", "Henderson", "the Fremont district", "Spring Valley"],
     "Las Vegas works around the clock — Summerlin practices, Henderson trades, and Fremont-district shops all field calls at hours other cities sleep through."),
    ("Columbus", "OH", "Ohio", "columbus-oh",
     ["the Short North", "German Village", "Clintonville", "Dublin"],
     "Columbus grows quietly and fast — Short North studios, German Village storefronts, Dublin and Easton offices — a big-city market with Midwest manners."),
    ("Indianapolis", "IN", "Indiana", "indianapolis-in",
     ["Broad Ripple", "Mass Ave", "Fountain Square", "Carmel"],
     "Indianapolis spreads from Mass Ave and Fountain Square out to Carmel and Fishers, where growing practices answer for some of the Midwest's fastest-growing suburbs."),
    ("Kansas City", "MO", "Missouri", "kansas-city-mo",
     ["the Country Club Plaza", "the Crossroads", "Westport", "the River Market"],
     "Kansas City spans two states — Plaza and Crossroads offices, Westport storefronts, Northland trades — and callers don't care which side of State Line you're on."),
]

STATE_BY_NAME = {s[0]: s for s in STATES}
CITY_SLUGS_BY_STATE = {}
for c in CITIES:
    CITY_SLUGS_BY_STATE.setdefault(c[2], []).append(c)

VERTICALS = [
    "dental and medical clinics",
    "law firms",
    "salons and spas",
    "veterinary clinics",
    "auto repair shops",
    "real-estate offices",
]

# ---------------------------------------------------------------------------
# Deterministic variant selection
# ---------------------------------------------------------------------------

def _h(key, salt):
    return int(hashlib.md5(("%s:%s" % (key, salt)).encode("utf-8")).hexdigest(), 16)

def pick(key, salt, options):
    return options[_h(key, salt) % len(options)]

def rotate(key, salt, items):
    k = _h(key, salt) % len(items)
    return items[k:] + items[:k]

def join_and(items):
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + ", and " + items[-1]

# ---------------------------------------------------------------------------
# Content variants (>=4 per section)
# ---------------------------------------------------------------------------

TITLE_CONCEPTS = ["AI Receptionist", "AI Phone Receptionist",
                  "24/7 AI Receptionist", "AI Answering Service"]

META_DESCRIPTIONS = [
    "Greetro answers {loc} business calls in 2 rings, 24/7, in 30+ languages — booking appointments, texting follow-ups, and transferring urgent calls. Free 14-day trial.",
    "An AI receptionist for {loc} businesses: every call answered in 2 rings, day or night, in 30+ languages. Bookings, messages, SMS follow-ups. Try it free for 14 days.",
    "Never miss a call in {loc} again. Greetro's AI receptionist answers 24/7 in 30+ languages, books into your calendar, and texts confirmations. 14-day free trial.",
    "24/7 AI phone answering for {loc} clinics, firms, salons, and shops. Two-ring pickup, 30+ languages, calendar booking, SMS follow-ups. Start free — no card needed.",
]

H1_PATTERNS = [
    "An AI receptionist for <span class=\"grad-text\">{loc}</span> businesses",
    "{loc}&rsquo;s calls, <span class=\"grad-text\">answered — every time</span>",
    "Every {loc} call, <span class=\"grad-text\">answered in two rings</span>",
    "The AI front desk for <span class=\"grad-text\">{loc}</span> businesses",
]

INTROS = [
    "Greetro is an AI voice receptionist for {loc} {v1}, {v2}, {v3}, and every other business that lives on its phone. It answers within two rings — days, nights, weekends, holidays — in 30+ languages, books appointments straight into your calendar, texts follow-ups, and transfers genuinely urgent calls to a human.",
    "Every missed call in {loc} is a customer calling your competitor. Greetro picks up within two rings, 24/7, in 30+ languages — booking appointments for {v1}, capturing intake for {v2}, and taking clean messages for {v3} — then texts callers their confirmations before they even hang up.",
    "{loc} businesses don&rsquo;t lose customers on quality — they lose them to unanswered phones. Greetro answers every call in two rings, around the clock, in 30+ languages: booking for {v1}, intake for {v2}, messages and callbacks for {v3}. Genuinely urgent calls still reach a human — instantly.",
    "Meet the front desk that never closes. Greetro answers your {loc} line within two rings, any hour, in 30+ languages. It books appointments with two-way calendar sync, answers questions from your own knowledge base, texts follow-up links, and transfers emergencies to your on-call number — built for {v1}, {v2}, and {v3} alike.",
]

STATE_WHY = [
    "<p>{color} From {cities}, the pattern repeats: small teams, busy lines, and callers who dial the next listing when nobody picks up.</p>"
    "<p>Greetro is a cloud service, not a local staffing agency — there&rsquo;s no office to visit and nothing to install. If your business answers a {name} phone number, Greetro can answer it for you, starting this week.</p>",
    "<p>Talk to owners in {cities} and you hear the same thing: the phone rings hardest exactly when the team is busiest. {color}</p>"
    "<p>Greetro works anywhere in {name} because it lives in the cloud — your existing number forwards to it in one setting, and turning it off is just as easy. No hardware, no new phone system, no IT project.</p>",
    "<p>{color} That&rsquo;s a lot of calls landing on front desks that are already stretched — or on nobody at all after close.</p>"
    "<p>Because Greetro is cloud-based, it serves every corner of {name} equally — {cities}, and every town in between. Keep your local number; Greetro answers it with your greeting, your rules, and your calendar.</p>",
    "<p>What does a missed call cost in {name}? For a clinic, a filled slot; for a firm, a signed client; for a shop, a repair order. {color}</p>"
    "<p>Greetro answers for businesses across {name} — {cities} included — as a cloud service running on your existing number. Setup takes an afternoon, and the 14-day trial doesn&rsquo;t ask for a card.</p>",
]

CITY_WHY = [
    "<p>{color} Wherever your callers come from — {areas} — they expect a fast pickup and a real answer, not a voicemail greeting.</p>"
    "<p>Greetro is a cloud service available to any business with a {name} phone line. There&rsquo;s no office visit and nothing to install: forward your existing number and it starts answering with your greeting, your rules, and your calendar.</p>",
    "<p>Ask around {areas}: the phone rings hardest exactly when the chair, the exam room, or the job site needs you most. {color}</p>"
    "<p>Because Greetro runs in the cloud, it covers every part of {name} — and the rest of {state} — equally. Keep the number your customers already know; Greetro picks it up in two rings.</p>",
    "<p>{color} It&rsquo;s a market that rewards whoever answers first — and quietly punishes voicemail.</p>"
    "<p>Greetro serves {name} businesses as a cloud service on your existing line — from {areas} — with nothing to install and a 14-day free trial that never asks for a card.</p>",
    "<p>What&rsquo;s a missed call worth in {name}? A booked cleaning, a signed client, a scheduled repair, a showing that actually happens. {color}</p>"
    "<p>Across {areas}, Greetro answers on your existing number — cloud-based, live in an afternoon, and switched off again in one setting if you ever want it gone.</p>",
]

FEATURE_HEADS = [
    ("What Greetro does for {loc} businesses",
     "The full front-desk job — answering, booking, messaging, triaging — running 24/7 on your existing line."),
    ("A full front desk for your {loc} line",
     "Everything a great receptionist does, minus the desk — and it never calls in sick."),
    ("Built for how {loc} answers the phone",
     "Real product features mapped to the calls your business actually gets."),
    ("Six ways Greetro earns its keep in {loc}",
     "From two-ring pickup to structured messages — the features doing the work."),
]

ICONS = {
    "clock": "<svg width=\"22\" height=\"22\" viewBox=\"0 0 24 24\" fill=\"none\" aria-hidden=\"true\"><circle cx=\"12\" cy=\"12\" r=\"9\" stroke=\"currentColor\" stroke-width=\"1.8\"/><path d=\"M12 7v5l3.5 2\" stroke=\"currentColor\" stroke-width=\"1.8\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/></svg>",
    "globe": "<svg width=\"22\" height=\"22\" viewBox=\"0 0 24 24\" fill=\"none\" aria-hidden=\"true\"><circle cx=\"12\" cy=\"12\" r=\"9\" stroke=\"currentColor\" stroke-width=\"1.8\"/><path d=\"M3.5 12h17M12 3c2.5 2.6 3.8 5.6 3.8 9S14.5 18.4 12 21c-2.5-2.6-3.8-5.6-3.8-9S9.5 5.6 12 3Z\" stroke=\"currentColor\" stroke-width=\"1.8\"/></svg>",
    "calendar": "<svg width=\"22\" height=\"22\" viewBox=\"0 0 24 24\" fill=\"none\" aria-hidden=\"true\"><rect x=\"3\" y=\"4\" width=\"18\" height=\"17\" rx=\"3\" stroke=\"currentColor\" stroke-width=\"1.8\"/><path d=\"M3 9h18M8 2.5V6M16 2.5V6\" stroke=\"currentColor\" stroke-width=\"1.8\" stroke-linecap=\"round\"/><path d=\"m9 14.5 2 2 4-4\" stroke=\"currentColor\" stroke-width=\"1.8\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/></svg>",
    "sms": "<svg width=\"22\" height=\"22\" viewBox=\"0 0 24 24\" fill=\"none\" aria-hidden=\"true\"><path d=\"M21 12a8 8 0 0 1-11.6 7.1L4 21l1.9-5.4A8 8 0 1 1 21 12Z\" stroke=\"currentColor\" stroke-width=\"1.8\" stroke-linejoin=\"round\"/><path d=\"M8.5 12h.01M12 12h.01M15.5 12h.01\" stroke=\"currentColor\" stroke-width=\"2.5\" stroke-linecap=\"round\"/></svg>",
    "transfer": "<svg width=\"22\" height=\"22\" viewBox=\"0 0 24 24\" fill=\"none\" aria-hidden=\"true\"><path d=\"M12 3v18M12 3l-4 4m4-4 4 4\" stroke=\"currentColor\" stroke-width=\"1.8\" stroke-linecap=\"round\" stroke-linejoin=\"round\" transform=\"rotate(90 12 12)\"/><circle cx=\"5\" cy=\"12\" r=\"2.5\" stroke=\"currentColor\" stroke-width=\"1.8\"/><circle cx=\"19\" cy=\"12\" r=\"2.5\" stroke=\"currentColor\" stroke-width=\"1.8\"/></svg>",
    "log": "<svg width=\"22\" height=\"22\" viewBox=\"0 0 24 24\" fill=\"none\" aria-hidden=\"true\"><rect x=\"3\" y=\"4\" width=\"18\" height=\"16\" rx=\"2.5\" stroke=\"currentColor\" stroke-width=\"1.8\"/><path d=\"M7 14.5 10 11l2.5 2.5L17 8.5\" stroke=\"currentColor\" stroke-width=\"1.8\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/></svg>",
    "book": "<svg width=\"22\" height=\"22\" viewBox=\"0 0 24 24\" fill=\"none\" aria-hidden=\"true\"><path d=\"M4 19V6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v13\" stroke=\"currentColor\" stroke-width=\"1.8\" stroke-linecap=\"round\"/><path d=\"M4 19a2 2 0 0 0 2 2h14M8 8h8M8 12h5\" stroke=\"currentColor\" stroke-width=\"1.8\" stroke-linecap=\"round\"/></svg>",
    "note": "<svg width=\"22\" height=\"22\" viewBox=\"0 0 24 24\" fill=\"none\" aria-hidden=\"true\"><rect x=\"3\" y=\"5\" width=\"18\" height=\"14\" rx=\"2.5\" stroke=\"currentColor\" stroke-width=\"1.8\"/><path d=\"M7 10h6M7 14h10\" stroke=\"currentColor\" stroke-width=\"1.8\" stroke-linecap=\"round\"/></svg>",
}

# (icon, [title variants], [3 blurb variants]) — real product features, local framing.
FEATURES = [
    ("clock", ["Answered in two rings, 24/7", "Two-ring pickup, day and night",
               "Always answered — nights, weekends, holidays", "24/7 pickup within two rings"], [
        "Lunch rush, snow day, Sunday night — every call to your {loc} line is picked up within two rings, greeted by your business name, and handled like a calm, trained receptionist would handle it.",
        "Callers in {loc} never hear voicemail. Greetro answers within two rings, 24/7/365, and sounds like a friendly member of your team — because to your callers, it is.",
        "Whether it&rsquo;s 2 p.m. or 2 a.m. in {loc}, Greetro picks up in two rings, greets callers by your business name, and gets to work booking, answering, or routing.",
    ]),
    ("globe", ["30+ languages, detected automatically", "Fluent in 30+ languages",
               "Every caller&rsquo;s language, automatically", "One receptionist, 30+ languages"], [
        "Greetro detects a caller&rsquo;s language and answers in it — more than 30 supported — so every {loc} caller is served in the language they opened with, without being put on hold.",
        "{loc} doesn&rsquo;t call in just one language. Greetro speaks 30+ fluently, switching the moment a caller does — no transfers, no &ldquo;press 2.&rdquo;",
        "From English and Spanish to 30+ more, Greetro serves {loc} callers in their own language automatically — one receptionist for everyone who dials.",
    ]),
    ("calendar", ["Books straight into your calendar", "Real bookings, real calendar sync",
                  "Appointments booked while callers wait", "Calendar-synced appointment booking"], [
        "Two-way Google and Outlook sync means Greetro offers {loc} callers only genuinely open slots, then books, reschedules, or cancels — no double bookings, no phone tag.",
        "While a {loc} caller is still on the line, Greetro checks your real availability, offers open times, and books the appointment — synced two-way with Google and Outlook.",
        "Bookings from {loc} callers land straight on your Google or Outlook calendar, with conflicts impossible — Greetro only ever offers slots that are actually free.",
    ]),
    ("sms", ["Texts follow-ups before hang-up", "SMS confirmations and links",
             "Follow-up texts, sent instantly", "Confirmations texted on the spot"], [
        "Confirmations, intake forms, directions, payment links — Greetro texts them to {loc} callers while they&rsquo;re still on the line, so no-shows drop and paperwork starts early.",
        "Every {loc} booking gets an instant SMS confirmation, and Greetro can text directions, forms, or payment links on request — sent before the caller hangs up.",
        "Greetro follows up {loc} calls by text automatically — confirmations, reminders, intake links — the kind of follow-through callers remember and mention.",
    ]),
    ("transfer", ["Urgent calls reach a human, fast", "Smart handoff for emergencies",
                  "Knows when to transfer to you", "Emergencies routed to your on-call line"], [
        "A real emergency in {loc} — a burst pipe, an urgent legal matter, a pet in distress — is transferred to your on-call number immediately, with a one-line summary whispered first.",
        "You define what counts as urgent for your {loc} business. Greetro transfers those calls to a human instantly and turns everything else into bookings and clean messages.",
        "Greetro triages every {loc} call: urgent ones ring through to your on-call line with context, routine ones get booked or captured — nothing falls through the cracks.",
    ]),
    ("log", ["Every call logged and summarized", "Transcripts and AI summaries",
             "Your whole day&rsquo;s calls, at a glance", "A dashboard for every call"], [
        "Every {loc} call lands in your dashboard with a full transcript and a two-line AI summary — skim an entire day of phone traffic in under a minute.",
        "No more &ldquo;who called?&rdquo; Your dashboard logs every {loc} call with who, what, and what happened — transcript included, summary on top.",
        "Each call to your {loc} number is logged, transcribed, and summarized automatically, so the whole team sees exactly what the phone did today.",
    ]),
    ("book", ["Answers from your knowledge base", "Real answers, from your own info",
              "Trained on your business, not guesses", "Your hours, prices, and policies — answered"], [
        "Train Greetro on your services, prices, hours, parking, and policies, and it answers {loc} callers accurately — saying &ldquo;I&rsquo;ll have someone confirm&rdquo; instead of guessing.",
        "Greetro learns your {loc} business from your website and your notes — so questions about hours, pricing, and directions get real answers, not hold music.",
        "Hours, insurance questions, service areas, prices — Greetro answers what {loc} callers actually ask, from a knowledge base you control and can edit anytime.",
    ]),
    ("note", ["Structured messages, never voicemail", "Clean messages instead of voicemail",
              "Every message captured, structured", "No more voicemail roulette"], [
        "When there&rsquo;s nothing to book, Greetro captures a structured message from your {loc} caller — name, number, reason, urgency — never a garbled voicemail.",
        "Missed-call mysteries end here: every non-booking {loc} call becomes a clean, structured message with callback details and urgency flagged.",
        "Instead of voicemail roulette, {loc} callers leave structured messages — name, number, need, urgency — ready for a one-tap callback.",
    ]),
]

PRICING_LEADS = [
    "Simple monthly plans for {loc} businesses — a fraction of a receptionist&rsquo;s salary, live in an afternoon.",
    "Every plan answers 24/7 within two rings. Pick the size that fits your {loc} call volume.",
    "No contracts, no hardware, no setup fees — just a monthly plan sized to your {loc} line.",
    "Start free for 14 days, no card required, and see exactly what Greetro catches on your {loc} line.",
]

CTA_VARIANTS = [
    ("Never miss another <span class=\"grad-text\">{loc} call</span>",
     "Greetro is rolling out region by region. Join the waitlist and your {loc} business gets hands-on onboarding and a 14-day free trial — no card required."),
    ("Your {loc} line, <span class=\"grad-text\">answered from day one</span>",
     "Join the waitlist to be first in line when your region opens. Every early {loc} business gets hands-on onboarding and 14 days free — no card required."),
    ("Put your {loc} phones <span class=\"grad-text\">on autopilot</span>",
     "Keep your number, keep your greeting, stop missing calls. Join the waitlist for hands-on onboarding and a 14-day free trial for your {loc} business."),
    ("The next {loc} caller <span class=\"grad-text\">gets answered</span>",
     "Be first when your region opens: join the waitlist and start a 14-day free trial for your {loc} business — hands-on onboarding included, no card required."),
]

# ---------------------------------------------------------------------------
# Shared page shell
# ---------------------------------------------------------------------------

EXTRA_CSS = """
    .crumbs{display:flex;flex-wrap:wrap;gap:.45rem;align-items:center;font-size:.85rem;color:var(--text-2,#9aa0b4);padding-top:1.6rem}
    .crumbs a{color:inherit;text-decoration:none}
    .crumbs a:hover{color:var(--text,#fff)}
    .crumbs .sep{opacity:.5}
    .loc-hero{padding-block:clamp(2.5rem,6vh,4.5rem) clamp(1rem,3vh,2rem)}
    .loc-hero h1{font-size:clamp(2.1rem,5vw,3.3rem)}
    .loc-ctas{display:flex;gap:.9rem;justify-content:center;flex-wrap:wrap;margin-top:1.8rem}
    .loc-facts{display:flex;gap:2.4rem;justify-content:center;flex-wrap:wrap;margin-top:2.2rem;list-style:none;padding:0}
    .loc-facts li{display:grid;gap:.1rem;text-align:center}
    .loc-facts strong{font-family:'Space Grotesk',Inter,sans-serif;font-size:1.35rem;background:linear-gradient(120deg,#a29bfe,#00f0ff);-webkit-background-clip:text;background-clip:text;color:transparent}
    .loc-facts span{font-size:.82rem;color:var(--text-2,#9aa0b4)}
    .loc-card{padding:clamp(1.6rem,4vw,2.4rem);border-radius:22px;max-width:860px;margin:0 auto}
    .loc-card p{color:var(--text-2,#c6cadb);line-height:1.75}
    .loc-card p+p{margin-top:1rem}
    .loc-links{display:flex;flex-wrap:wrap;gap:.6rem;justify-content:center;max-width:900px;margin:0 auto}
    .loc-links a{padding:.55rem 1.05rem;border:1px solid rgba(255,255,255,.14);border-radius:999px;font-size:.88rem;color:var(--text-2,#c6cadb);text-decoration:none;transition:border-color .2s,color .2s;background:rgba(255,255,255,.03)}
    .loc-links a:hover{color:var(--text,#fff);border-color:rgba(162,155,254,.65)}
    .loc-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(175px,1fr));gap:.6rem;max-width:1000px;margin:0 auto}
    .loc-grid a{padding:.7rem .95rem;border:1px solid rgba(255,255,255,.12);border-radius:14px;font-size:.9rem;color:var(--text-2,#c6cadb);text-decoration:none;transition:border-color .2s,color .2s;background:rgba(255,255,255,.03)}
    .loc-grid a:hover{color:var(--text,#fff);border-color:rgba(0,240,255,.5)}
    .loc-group-title{margin:2.4rem 0 1rem;text-align:center;font-size:1.1rem}
"""

FAVICON = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Cdefs%3E%3ClinearGradient id='g' x1='0' y1='0' x2='1' y2='1'%3E%3Cstop offset='0' stop-color='%23a29bfe'/%3E%3Cstop offset='1' stop-color='%2300f0ff'/%3E%3C/linearGradient%3E%3C/defs%3E%3Crect width='64' height='64' rx='15' fill='%23070714'/%3E%3Cg stroke='url(%23g)' stroke-width='6' stroke-linecap='round'%3E%3Cline x1='14' y1='27' x2='14' y2='37'/%3E%3Cline x1='26' y1='18' x2='26' y2='46'/%3E%3Cline x1='38' y1='23' x2='38' y2='41'/%3E%3Cline x1='50' y1='28' x2='50' y2='36'/%3E%3C/g%3E%3C/svg%3E"

LOGO_SVG = """<svg class="logo-mark" width="34" height="34" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <defs>
            <linearGradient id="{gid}" x1="0" y1="0" x2="64" y2="64" gradientUnits="userSpaceOnUse">
              <stop offset="0" stop-color="#a29bfe"/>
              <stop offset="1" stop-color="#00f0ff"/>
            </linearGradient>
          </defs>
          <rect width="64" height="64" rx="15" fill="rgba(255,255,255,0.05)" stroke="rgba(255,255,255,0.12)"/>
          <g stroke="url(#{gid})" stroke-width="6" stroke-linecap="round">
            <line x1="14" y1="27" x2="14" y2="37"/>
            <line x1="26" y1="18" x2="26" y2="46"/>
            <line x1="38" y1="23" x2="38" y2="41"/>
            <line x1="50" y1="28" x2="50" y2="36"/>
          </g>
        </svg>"""


def nav_html():
    return """  <!-- Aurora background -->
  <div class="aurora" aria-hidden="true">
    <div class="aurora-blob aurora-violet"></div>
    <div class="aurora-blob aurora-cyan"></div>
    <div class="aurora-blob aurora-pink"></div>
  </div>

  <!-- ===================== NAV ===================== -->
  <header class="nav" id="top">
    <nav class="nav-inner container" aria-label="Main navigation">
      <a class="logo" href="/" aria-label="Greetro — home">
        """ + LOGO_SVG.format(gid="logoGrad") + """
        <span class="logo-word">Greetro</span>
      </a>

      <button class="nav-toggle" type="button" aria-expanded="false" aria-controls="navLinks" aria-label="Toggle menu">
        <span></span><span></span><span></span>
      </button>

      <div class="nav-links" id="navLinks">
        <a href="/#features">Features</a>
        <a href="/#how">How it works</a>
        <a href="/#use-cases">Who it&rsquo;s for</a>
        <a href="/#pricing">Pricing</a>
        <a href="/locations/">Locations</a>
        <a class="btn btn-primary btn-sm nav-cta" href="/#waitlist">Start free trial</a>
      </div>
    </nav>
  </header>
"""


def footer_html():
    return """  <!-- ===================== FOOTER ===================== -->
  <footer class="footer">
    <div class="container footer-inner">
      <div class="footer-brand">
        <a class="logo" href="/" aria-label="Greetro — home">
          """ + LOGO_SVG.format(gid="logoGradFooter").replace('width="34" height="34"', 'width="30" height="30"') + """
          <span class="logo-word">Greetro</span>
        </a>
        <p class="footer-tag">The AI voice receptionist that answers every call — 24/7, in 30+ languages.</p>
      </div>

      <nav class="footer-links" aria-label="Footer navigation">
        <a href="/#features">Features</a>
        <a href="/#how">How it works</a>
        <a href="/#use-cases">Who it&rsquo;s for</a>
        <a href="/#pricing">Pricing</a>
        <a href="/#faq">FAQ</a>
        <a href="/locations/">Locations</a>
        <a href="/#waitlist">Join the waitlist</a>
      </nav>
    </div>
    <div class="container footer-bottom">
      <p>&copy; 2026 Greetro. All rights reserved.</p>
      <p>Designed &amp; Built by <a href="https://stylemarking.com" rel="noopener">StyleMarking.com</a></p>
    </div>
  </footer>

  <script src="../js/main.js" defer></script>
</body>
</html>
"""


def head_html(title, description, canonical, jsonld):
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="theme-color" content="#050510">
  <title>""" + title + """</title>
  <meta name="description" content=\"""" + description + """\">
  <link rel="canonical" href=\"""" + canonical + """\">

  <!-- Open Graph -->
  <meta property="og:type" content="website">
  <meta property="og:url" content=\"""" + canonical + """\">
  <meta property="og:site_name" content="Greetro">
  <meta property="og:title" content=\"""" + title + """\">
  <meta property="og:description" content=\"""" + description + """\">
  <meta property="og:image" content=\"""" + DOMAIN + """/images/og-default.png">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">

  <!-- Twitter -->
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content=\"""" + title + """\">
  <meta name="twitter:description" content=\"""" + description + """\">
  <meta name="twitter:image" content=\"""" + DOMAIN + """/images/og-default.png">

  <link rel="icon" type="image/svg+xml" href=\"""" + FAVICON + """\">

  <!-- Fonts -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap" rel="stylesheet">

  <link rel="stylesheet" href="../css/style.css">
  <style>""" + EXTRA_CSS + """  </style>

  <!-- Structured data -->
  <script type="application/ld+json">
""" + jsonld + """
  </script>
</head>
<body>
"""


def offers_jsonld():
    return [
        {"@type": "Offer", "name": "Starter", "price": "49", "priceCurrency": "USD",
         "description": "1 business number, 250 call minutes per month, 24/7 answering, appointment booking, full transcripts."},
        {"@type": "Offer", "name": "Pro", "price": "149", "priceCurrency": "USD",
         "description": "3 business numbers, 1,000 call minutes per month, Google and Outlook calendar sync, 30+ languages, SMS follow-ups."},
        {"@type": "Offer", "name": "Scale", "price": "399", "priceCurrency": "USD",
         "description": "10 business numbers, 4,000 call minutes per month, CRM integrations and API, priority support."},
    ]


def location_jsonld(display, canonical, description, area):
    graph = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Home", "item": DOMAIN + "/"},
                    {"@type": "ListItem", "position": 2, "name": "Locations", "item": DOMAIN + "/locations/"},
                    {"@type": "ListItem", "position": 3, "name": display, "item": canonical},
                ],
            },
            {
                "@type": "Service",
                "name": "AI Voice Receptionist in " + display,
                "serviceType": "AI phone answering and virtual receptionist service",
                "url": canonical,
                "description": description,
                "provider": {"@type": "Organization", "name": "Greetro", "url": DOMAIN + "/"},
                "areaServed": area,
                "offers": offers_jsonld(),
            },
        ],
    }
    return json.dumps(graph, ensure_ascii=False, indent=2)


STARTER_TAGS = [
    "For a single line that can&rsquo;t miss calls.",
    "One number, zero missed calls.",
    "For solo shops and single-line offices.",
    "The essentials for one busy line.",
]
PRO_TAGS = [
    "For busy offices and multi-line teams.",
    "For teams whose phones never sit still.",
    "The plan most growing offices land on.",
    "For offices juggling several lines at once.",
]
SCALE_TAGS = [
    "For multi-location businesses and franchises.",
    "For franchises and multi-site operators.",
    "When every location needs the same front desk.",
    "Built for businesses with many doors.",
]
PRICING_NOTES = [
    "14-day free trial on every plan &middot; no card required &middot; cancel anytime",
    "Every plan starts with 14 days free &middot; no card up front &middot; cancel anytime",
    "Try any plan free for 14 days &middot; no card needed &middot; cancel whenever",
    "All plans: 14-day free trial, no card required, cancel anytime",
]


def pricing_html(key):
    return """      <div class="pricing">
        <article class="price-card glass reveal">
          <h3>Starter</h3>
          <p class="price"><span class="price-num">$49</span><span class="price-per">/mo</span></p>
          <p class="price-tag">""" + pick(key, "tag-starter", STARTER_TAGS) + """</p>
          <ul class="price-features">
            <li>1 business number</li>
            <li>250 call minutes / month</li>
            <li>24/7 answering within 2 rings</li>
            <li>Appointment booking</li>
          </ul>
          <a class="btn btn-ghost btn-block" href="/#waitlist">Start free trial</a>
        </article>

        <article class="price-card price-featured glass reveal delay-1">
          <p class="popular-badge">Most popular</p>
          <h3>Pro</h3>
          <p class="price"><span class="price-num">$149</span><span class="price-per">/mo</span></p>
          <p class="price-tag">""" + pick(key, "tag-pro", PRO_TAGS) + """</p>
          <ul class="price-features">
            <li>3 business numbers</li>
            <li>1,000 call minutes / month</li>
            <li>Google &amp; Outlook calendar sync</li>
            <li>30+ languages &amp; SMS follow-ups</li>
          </ul>
          <a class="btn btn-primary btn-block" href="/#waitlist">Start free trial</a>
        </article>

        <article class="price-card glass reveal delay-2">
          <h3>Scale</h3>
          <p class="price"><span class="price-num">$399</span><span class="price-per">/mo</span></p>
          <p class="price-tag">""" + pick(key, "tag-scale", SCALE_TAGS) + """</p>
          <ul class="price-features">
            <li>10 business numbers</li>
            <li>4,000 call minutes / month</li>
            <li>CRM integrations + API</li>
            <li>Priority support</li>
          </ul>
          <a class="btn btn-ghost btn-block" href="/#waitlist">Start free trial</a>
        </article>
      </div>

      <p class="pricing-note reveal">""" + pick(key, "pricing-note", PRICING_NOTES) + """</p>
"""


def build_features_section(key, loc, heading_loc):
    head, sub = pick(key, "feat-head", FEATURE_HEADS)
    cards = []
    rotated = rotate(key, "feat-rot", FEATURES)[:6]
    for i, (icon, titles, blurbs) in enumerate(rotated):
        title = pick(key, "feat-title-" + titles[0], titles)
        blurb = pick(key, "feat-blurb-" + titles[0], blurbs).format(loc=loc)
        delay = "" if i % 3 == 0 else (" delay-1" if i % 3 == 1 else " delay-2")
        cards.append(
            "        <div class=\"use-case glass reveal" + delay + "\">\n"
            "          " + ICONS[icon] + "\n"
            "          <h3>" + title + "</h3>\n"
            "          <p>" + blurb + "</p>\n"
            "        </div>"
        )
    return (
        "    <section class=\"section container\" id=\"features-local\">\n"
        "      <div class=\"section-head reveal\">\n"
        "        <p class=\"eyebrow\">Features</p>\n"
        "        <h2>" + head.format(loc=heading_loc) + "</h2>\n"
        "        <p class=\"section-sub\">" + sub + "</p>\n"
        "      </div>\n\n"
        "      <div class=\"use-cases\">\n" + "\n".join(cards) + "\n      </div>\n"
        "    </section>\n"
    )


def build_common_sections(key, loc_short, why_heading, why_html, links_heading, links_html):
    """Sections shared by state + city pages: why, features, pricing, CTA, links."""
    pricing_lead = pick(key, "pricing", PRICING_LEADS).format(loc=loc_short)
    cta_h, cta_p = pick(key, "cta", CTA_VARIANTS)
    parts = []

    parts.append(
        "    <section class=\"section container\" id=\"why\">\n"
        "      <div class=\"section-head reveal\">\n"
        "        <p class=\"eyebrow\">The local picture</p>\n"
        "        <h2>" + why_heading + "</h2>\n"
        "      </div>\n"
        "      <div class=\"loc-card glass reveal\">\n        " + why_html + "\n      </div>\n"
        "    </section>\n"
    )

    parts.append(build_features_section(key, loc_short, loc_short))

    parts.append(
        "    <section class=\"section container\" id=\"pricing-local\">\n"
        "      <div class=\"section-head reveal\">\n"
        "        <p class=\"eyebrow\">Pricing</p>\n"
        "        <h2>Plans that cost less than <span class=\"grad-text\">missed calls</span></h2>\n"
        "        <p class=\"section-sub\">" + pricing_lead + "</p>\n"
        "      </div>\n" + pricing_html(key) + "    </section>\n"
    )

    parts.append(
        "    <section class=\"section container\" id=\"cta\">\n"
        "      <div class=\"cta-panel glass reveal\" style=\"grid-template-columns:1fr;text-align:center\">\n"
        "        <div class=\"cta-copy\">\n"
        "          <h2>" + cta_h.format(loc=loc_short) + "</h2>\n"
        "          <p>" + cta_p.format(loc=loc_short) + "</p>\n"
        "          <div class=\"loc-ctas\">\n"
        "            <a class=\"btn btn-primary\" href=\"/#waitlist\">Start your 14-day free trial</a>\n"
        "            <a class=\"btn btn-ghost\" href=\"/#how\">See how it works</a>\n"
        "          </div>\n"
        "        </div>\n"
        "      </div>\n"
        "    </section>\n"
    )

    parts.append(
        "    <section class=\"section container\" id=\"nearby\">\n"
        "      <div class=\"section-head reveal\">\n"
        "        <p class=\"eyebrow\">Keep exploring</p>\n"
        "        <h2>" + links_heading + "</h2>\n"
        "      </div>\n"
        "      <div class=\"loc-links reveal\">\n" + links_html + "\n      </div>\n"
        "    </section>\n"
    )
    return "\n".join(parts)


def build_hero(key, display, loc_short, breadcrumb_name):
    verts = rotate(key, "verts", VERTICALS)
    intro = pick(key, "intro", INTROS).format(
        loc=loc_short, v1=verts[0], v2=verts[1], v3=verts[2])
    h1 = pick(key, "h1", H1_PATTERNS).format(loc=loc_short)
    return (
        "    <nav class=\"container crumbs\" aria-label=\"Breadcrumb\">\n"
        "      <a href=\"/\">Home</a><span class=\"sep\">/</span>"
        "<a href=\"/locations/\">Locations</a><span class=\"sep\">/</span>"
        "<span>" + breadcrumb_name + "</span>\n"
        "    </nav>\n\n"
        "    <section class=\"section container loc-hero\">\n"
        "      <div class=\"section-head\">\n"
        "        <p class=\"eyebrow reveal\">\n"
        "          <svg width=\"14\" height=\"14\" viewBox=\"0 0 24 24\" fill=\"none\" aria-hidden=\"true\"><path d=\"M6.6 3.2c.6-.6 1.6-.5 2.1.2l1.6 2.3c.4.6.4 1.4-.1 2L9 9.1c1 2.1 2.7 3.8 4.8 4.8l1.4-1.2c.6-.5 1.4-.5 2-.1l2.3 1.6c.7.5.8 1.5.2 2.1l-1.4 1.4c-.7.7-1.7 1-2.6.8C9.6 17.1 5.7 13.2 4.4 7.1c-.2-.9.1-1.9.8-2.6l1.4-1.3Z\" fill=\"currentColor\"/></svg>\n"
        "          AI Voice Receptionist &middot; " + display + "\n"
        "        </p>\n"
        "        <h1 class=\"reveal delay-1\">" + h1 + "</h1>\n"
        "        <p class=\"section-sub reveal delay-2\">" + intro + "</p>\n"
        "        <div class=\"loc-ctas reveal delay-3\">\n"
        "          <a class=\"btn btn-primary\" href=\"/#waitlist\">Start your 14-day free trial</a>\n"
        "          <a class=\"btn btn-ghost\" href=\"/#pricing\">See pricing</a>\n"
        "        </div>\n"
        "        <ul class=\"loc-facts reveal delay-4\">\n"
        "          <li><strong>2 rings</strong><span>pickup, every call</span></li>\n"
        "          <li><strong>24/7/365</strong><span>always on</span></li>\n"
        "          <li><strong>30+</strong><span>languages</span></li>\n"
        "        </ul>\n"
        "      </div>\n"
        "    </section>\n"
    )


# ---------------------------------------------------------------------------
# Page builders
# ---------------------------------------------------------------------------

def build_state_page(state):
    name, abbr, slug, cities, neighbors, color = state
    key = name
    canonical = DOMAIN + "/locations/" + slug
    concept = pick(key, "title", TITLE_CONCEPTS)
    title = concept + " in " + name + " — Greetro"
    description = pick(key, "meta", META_DESCRIPTIONS).format(loc=name)

    jsonld = location_jsonld(
        name, canonical, description,
        {"@type": "State", "name": name, "containedInPlace": {"@type": "Country", "name": "United States"}})

    cities_list = join_and(cities)
    why = pick(key, "why", STATE_WHY).format(color=color, cities=cities_list, name=name)
    why_heading = "Why " + name + " businesses <span class=\"grad-text\">stop missing calls</span>"

    # Internal links: our city pages in this state + 4 neighboring states
    link_items = []
    for c in CITY_SLUGS_BY_STATE.get(name, []):
        link_items.append("        <a href=\"/locations/" + c[3] + "\">" + c[0] + ", " + c[1] + "</a>")
    for n in neighbors:
        nslug = STATE_BY_NAME[n][2]
        link_items.append("        <a href=\"/locations/" + nslug + "\">" + n + "</a>")
    link_items.append("        <a href=\"/locations/\">All locations</a>")
    links_heading = "Greetro in and <span class=\"grad-text\">around " + name + "</span>"

    body = (nav_html() + "\n  <main>\n\n"
            + build_hero(key, name, name, name) + "\n"
            + build_common_sections(key, name, why_heading, why, links_heading, "\n".join(link_items))
            + "\n  </main>\n\n")
    return head_html(title, description, canonical, jsonld) + "\n" + body + footer_html()


def build_city_page(idx, city):
    name, st, state_name, slug, areas, color = city
    display = name + ", " + st
    key = display
    canonical = DOMAIN + "/locations/" + slug
    concept = pick(key, "title", TITLE_CONCEPTS)
    title = concept + " in " + display + " — Greetro"
    description = pick(key, "meta", META_DESCRIPTIONS).format(loc=display)

    jsonld = location_jsonld(
        display, canonical, description,
        {"@type": "City", "name": name, "containedInPlace": {"@type": "State", "name": state_name}})

    areas_list = join_and(areas)
    why = pick(key, "city-why", CITY_WHY).format(
        color=color, areas=areas_list, name=name, state=state_name)
    why_heading = "Why " + name + " businesses <span class=\"grad-text\">stop missing calls</span>"

    # Internal links: state page + 5 other cities (deterministic rotation)
    state_slug = STATE_BY_NAME[state_name][2]
    link_items = ["        <a href=\"/locations/" + state_slug + "\">All of " + state_name + "</a>"]
    n = len(CITIES)
    for j in range(1, 6):
        other = CITIES[(idx + j) % n]
        link_items.append("        <a href=\"/locations/" + other[3] + "\">" + other[0] + ", " + other[1] + "</a>")
    link_items.append("        <a href=\"/locations/\">All locations</a>")
    links_heading = "Greetro <span class=\"grad-text\">beyond " + name + "</span>"

    body = (nav_html() + "\n  <main>\n\n"
            + build_hero(key, display, name, display) + "\n"
            + build_common_sections(key, name, why_heading, why, links_heading, "\n".join(link_items))
            + "\n  </main>\n\n")
    return head_html(title, description, canonical, jsonld) + "\n" + body + footer_html()


def build_hub_page():
    canonical = DOMAIN + "/locations/"
    title = "AI Receptionist Locations — Greetro"
    description = ("Greetro's AI voice receptionist answers business calls 24/7 in 30+ languages across all 50 states. "
                   "Find your state or metro and start a 14-day free trial — no card required.")
    graph = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Home", "item": DOMAIN + "/"},
                    {"@type": "ListItem", "position": 2, "name": "Locations", "item": canonical},
                ],
            },
            {
                "@type": "CollectionPage",
                "name": "Greetro Locations",
                "url": canonical,
                "description": description,
                "isPartOf": {"@type": "WebSite", "name": "Greetro", "url": DOMAIN + "/"},
            },
        ],
    }
    jsonld = json.dumps(graph, ensure_ascii=False, indent=2)

    city_links = []
    for c in CITIES:
        city_links.append("        <a href=\"/locations/" + c[3] + "\">" + c[0] + ", " + c[1] + "</a>")
    state_links = []
    for s in sorted(STATES, key=lambda x: x[0]):
        state_links.append("        <a href=\"/locations/" + s[2] + "\">" + s[0] + "</a>")

    body = nav_html() + """
  <main>

    <nav class="container crumbs" aria-label="Breadcrumb">
      <a href="/">Home</a><span class="sep">/</span><span>Locations</span>
    </nav>

    <section class="section container loc-hero">
      <div class="section-head">
        <p class="eyebrow reveal">Locations</p>
        <h1 class="reveal delay-1">One receptionist, <span class="grad-text">every ZIP code</span></h1>
        <p class="section-sub reveal delay-2">Greetro is a cloud service — it answers any US business line, from Manhattan law firms to lake-country contractors. There&rsquo;s no local office to visit and nothing to install: forward your existing number, and Greetro picks up within two rings, 24/7, in 30+ languages. Pick your state or metro below to see how it fits your market.</p>
        <div class="loc-ctas reveal delay-3">
          <a class="btn btn-primary" href="/#waitlist">Start your 14-day free trial</a>
          <a class="btn btn-ghost" href="/#pricing">See pricing</a>
        </div>
      </div>
    </section>

    <section class="section container" id="metros">
      <div class="section-head reveal">
        <p class="eyebrow">Major metros</p>
        <h2>City <span class="grad-text">guides</span></h2>
        <p class="section-sub">Deep dives on the metros where missed calls cost the most.</p>
      </div>
      <div class="loc-grid reveal">
""" + "\n".join(city_links) + """
      </div>
    </section>

    <section class="section container" id="states">
      <div class="section-head reveal">
        <p class="eyebrow">All 50 states</p>
        <h2>Find <span class="grad-text">your state</span></h2>
        <p class="section-sub">Every state, every area code — the same two-ring pickup.</p>
      </div>
      <div class="loc-grid reveal">
""" + "\n".join(state_links) + """
      </div>
    </section>

  </main>

"""
    return head_html(title, description, canonical, jsonld) + body + footer_html()


# ---------------------------------------------------------------------------
# Root files
# ---------------------------------------------------------------------------

def build_sitemap():
    entries = [(DOMAIN + "/", TODAY),
               (DOMAIN + "/blog/", BLOG_LASTMOD)]
    entries += [(DOMAIN + "/blog/" + slug, BLOG_LASTMOD) for slug in BLOG_SLUGS]
    entries += [(DOMAIN + "/locations/", TODAY)]
    entries += [(DOMAIN + "/locations/" + s[2], TODAY) for s in STATES]
    entries += [(DOMAIN + "/locations/" + c[3], TODAY) for c in CITIES]
    lines = ["<?xml version=\"1.0\" encoding=\"UTF-8\"?>",
             "<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">"]
    for u, lastmod in entries:
        lines.append("  <url><loc>" + u + "</loc><lastmod>" + lastmod + "</lastmod></url>")
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def build_robots():
    return "User-agent: *\nAllow: /\n\nSitemap: " + DOMAIN + "/sitemap.xml\n"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class PageAudit(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.h1_count = 0
        self.jsonld = []
        self.hrefs = []
        self._in_jsonld = False
        self._jsonld_buf = []
        self._in_main = 0
        self._main_text = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "h1":
            self.h1_count += 1
        if tag == "script" and d.get("type") == "application/ld+json":
            self._in_jsonld = True
            self._jsonld_buf = []
        if tag == "main":
            self._in_main += 1
        if tag in ("script", "style", "svg") and tag != "script":
            pass
        if tag in ("style", "svg"):
            self._skip += 1
        if tag == "a" and "href" in d:
            self.hrefs.append(d["href"])

    def handle_endtag(self, tag):
        if tag == "script" and self._in_jsonld:
            self._in_jsonld = False
            self.jsonld.append("".join(self._jsonld_buf))
        if tag == "main":
            self._in_main -= 1
        if tag in ("style", "svg") and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if self._in_jsonld:
            self._jsonld_buf.append(data)
        elif self._in_main > 0 and not self._skip:
            self._main_text.append(data)

    @property
    def word_count(self):
        return len(" ".join(self._main_text).split())


def validate():
    errors = []
    warnings = []
    files = sorted(f for f in os.listdir(OUT_DIR) if f.endswith(".html"))
    existing = set(files)

    for fname in files:
        path = os.path.join(OUT_DIR, fname)
        with open(path, encoding="utf-8") as fh:
            html = fh.read()
        audit = PageAudit()
        try:
            audit.feed(html)
            audit.close()
        except Exception as exc:  # pragma: no cover
            errors.append("%s: parse error: %s" % (fname, exc))
            continue

        if audit.h1_count != 1:
            errors.append("%s: expected exactly 1 <h1>, found %d" % (fname, audit.h1_count))
        if not audit.jsonld:
            errors.append("%s: no JSON-LD block found" % fname)
        for block in audit.jsonld:
            try:
                json.loads(block)
            except ValueError as exc:
                errors.append("%s: invalid JSON-LD: %s" % (fname, exc))

        for href in audit.hrefs:
            if href.startswith(DOMAIN + "/locations/"):
                href = href[len(DOMAIN):]
            if href.startswith("/locations/"):
                target = href[len("/locations/"):].split("#")[0]
                if target == "":
                    resolved = "index.html"
                elif target.endswith(".html"):
                    resolved = target
                else:
                    resolved = target + ".html"
                if resolved not in existing:
                    errors.append("%s: broken internal link %s" % (fname, href))
            elif href.startswith("../"):
                if not os.path.exists(os.path.join(OUT_DIR, href.split("#")[0])):
                    errors.append("%s: missing asset %s" % (fname, href))

        if fname != "index.html":
            wc = audit.word_count
            if wc < 480 or wc > 780:
                warnings.append("%s: word count %d outside 500-700 target band" % (fname, wc))

    # Sitemap URLs must correspond to generated files
    sm_path = os.path.join(ROOT, "sitemap.xml")
    if os.path.exists(sm_path):
        with open(sm_path, encoding="utf-8") as fh:
            sm = fh.read()
        import re as _re
        for loc in _re.findall(r"<loc>(.*?)</loc>", sm):
            if "/locations/" in loc:
                tail = loc.split("/locations/", 1)[1]
                resolved = "index.html" if tail == "" else tail + ".html"
                if resolved not in existing:
                    errors.append("sitemap.xml: URL without file: %s" % loc)
    else:
        errors.append("sitemap.xml missing")
    if not os.path.exists(os.path.join(ROOT, "robots.txt")):
        errors.append("robots.txt missing")

    print("Validated %d pages in locations/" % len(files))
    for w in warnings:
        print("  WARN  " + w)
    for e in errors:
        print("  ERROR " + e)
    if not errors and not warnings:
        print("  All checks passed: 1 h1/page, valid JSON-LD, all internal links resolve.")
    return len(errors)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def generate():
    os.makedirs(OUT_DIR, exist_ok=True)
    count = 0
    for state in STATES:
        path = os.path.join(OUT_DIR, state[2] + ".html")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(build_state_page(state))
        count += 1
    for idx, city in enumerate(CITIES):
        path = os.path.join(OUT_DIR, city[3] + ".html")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(build_city_page(idx, city))
        count += 1
    with open(os.path.join(OUT_DIR, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(build_hub_page())
    with open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8") as fh:
        fh.write(build_sitemap())
    with open(os.path.join(ROOT, "robots.txt"), "w", encoding="utf-8") as fh:
        fh.write(build_robots())
    print("Generated %d location pages + hub + sitemap.xml + robots.txt" % count)


if __name__ == "__main__":
    if "--check" not in sys.argv:
        generate()
    sys.exit(1 if validate() else 0)
