"""
content.py — all SEO copy lives here so you can edit wording without touching
routing code. Keep claims TRUE (warranty, install time, delivery): Google and
customers both punish exaggeration.
"""

SITE_NAME = "Victor Lights"

HOME_TITLE = "Motorcycle Auxiliary Lights Kenya | LED Fog, Driving & DRL Lights – Victor Lights Nairobi"
HOME_DESCRIPTION = (
    "Buy motorcycle auxiliary lights in Kenya: LED spotlights, fog lights, DRL and mounting kits. "
    "IP67/IP68 waterproof, 12-month warranty, M-Pesa & cash on delivery. Nairobi, nationwide delivery."
)

# Visible, crawlable copy for the homepage (server-injected so it is in the
# HTML Google receives, not only added by JavaScript).
HOME_INTRO_HTML = """
<h2>Motorcycle auxiliary lights built for Kenyan roads</h2>
<p>Victor Lights supplies <strong>LED motorcycle auxiliary lights in Kenya</strong> for boda boda riders,
commuters, touring and adventure riders. Our range covers <strong>LED spotlights and driving lights</strong>
for unlit highways, <strong>motorcycle fog lights</strong> for rain and dust, <strong>DRL (daytime running) lights</strong>
for visibility in traffic, and <strong>mounting kits</strong> that fit most bikes.</p>
<p>Based in Nairobi, we deliver countrywide and accept M-Pesa, bank transfer and cash on delivery.
Not sure what suits your bike? Read our <a href="/guides/">buying and installation guides</a> or
message us on WhatsApp.</p>
"""

HOME_FAQ = [
    ("Which auxiliary lights are best for a motorcycle in Kenya?",
     "It depends on where you ride. For unlit highways and long distance, a spot/flood combo LED driving light "
     "gives the most reach. For rain, dust and mist, a wide, low-mounted fog light is better. For being seen in "
     "city traffic, add DRL lights. See our guide to choosing between driving, fog and DRL lights."),
    ("Are LED auxiliary lights for motorcycles legal in Kenya?",
     "Auxiliary lights are commonly fitted, but the rules are about not dazzling other road users. Aim them low, "
     "switch them off in oncoming traffic, and use a separate handlebar switch. For official requirements, check "
     "with the National Transport and Safety Authority (NTSA)."),
    ("How long does installation take?",
     "Most of our kits are plug-and-play with a harness, relay and handlebar switch, and typically take 20–30 minutes "
     "with basic hand tools."),
    ("Are your lights waterproof?",
     "Our lights are rated IP67 or IP68 depending on the model, so they handle rain, mud and river crossings. "
     "Check the rating listed on each product page."),
    ("Do you deliver outside Nairobi?",
     "Yes, we deliver countrywide by courier. You can pay by M-Pesa, bank transfer, or cash on delivery."),
    ("Will auxiliary lights drain my motorcycle battery?",
     "LED lights draw far less current than halogen lamps. A 27W–60W LED set with a relay is fine on most bikes "
     "with a healthy charging system. Ask us on WhatsApp if you are unsure about your model."),
    ("Do the lights come with a warranty?",
     "Yes, our products carry a 12-month replacement warranty."),
]

# ---- Guides: informational pages that target "how to / which / is it legal" searches ----
GUIDES = {
    "driving-vs-fog-vs-drl-motorcycle-lights": {
        "title": "Driving Lights vs Fog Lights vs DRL: Which Motorcycle Auxiliary Lights to Buy in Kenya",
        "h1": "Driving lights vs fog lights vs DRL: which should you buy?",
        "description": "Spotlights, fog lights or DRL? A plain-English guide to choosing motorcycle auxiliary lights for Kenyan highways, city traffic and rain.",
        "body": """
<p>Most riders searching for <strong>motorcycle auxiliary lights in Kenya</strong> are really choosing between three
things. Here is how they differ and when each makes sense.</p>
<h2>LED driving lights (spotlights)</h2>
<p>Built for distance. A spot or spot/flood combo beam throws light far down the road, which helps on unlit
highways such as long night stretches between towns. Best for touring, adventure riding and anyone who rides after dark outside the city.</p>
<h2>Motorcycle fog lights</h2>
<p>Built for bad conditions. A wide, low beam sits under rain, mist and dust glare instead of reflecting it back at you.
Amber or yellow light is often preferred in heavy rain and dust. Best for wet-season riding and dusty roads.</p>
<h2>DRL (daytime running lights)</h2>
<p>Built to be seen. DRLs make you visible to matatus, trucks and cars in daytime traffic, which is where many
motorcycle collisions start. Low power, slim, and easy to fit. Best for daily commuters and boda boda riders.</p>
<h2>Quick recommendation</h2>
<ul>
<li><strong>Highway / touring:</strong> LED driving lights, plus a fog light for rain.</li>
<li><strong>City commuting:</strong> DRL lights.</li>
<li><strong>Rain and dust:</strong> fog lights in a wide pattern.</li>
<li><strong>Everything:</strong> a driving pair, a DRL pair and a proper mounting kit.</li>
</ul>
<p>See our <a href="/#products">motorcycle light catalogue</a> or ask on WhatsApp which fits your bike.</p>
""",
    },
    "install-motorcycle-auxiliary-lights": {
        "title": "How to Install Auxiliary Lights on a Motorcycle (Wiring, Relay & Switch)",
        "h1": "How to install auxiliary lights on your motorcycle",
        "description": "Step-by-step guide to fitting LED auxiliary lights: mounting, relay wiring, handlebar switch and aiming. Takes about 20-30 minutes.",
        "body": """
<p>Most LED auxiliary light kits take <strong>20–30 minutes</strong> with basic hand tools. Always disconnect the battery first.</p>
<h2>What you need</h2>
<ul><li>The lights, bracket set, wiring harness, relay and handlebar switch (included in our kits)</li>
<li>Spanners or Allen keys, zip ties, electrical tape</li></ul>
<h2>Steps</h2>
<ol>
<li><strong>Mount the lights</strong> on crash bars, fork brackets or a mounting bar, so they sit firmly and do not block the headlight.</li>
<li><strong>Run the harness</strong> from the lights toward the battery and handlebar, keeping it away from the exhaust and moving parts.</li>
<li><strong>Connect the relay:</strong> the relay takes power straight from the battery so the switch only carries a small current. The harness is colour-coded; follow the diagram in the box.</li>
<li><strong>Fit the handlebar switch</strong> and route its wire to the relay.</li>
<li><strong>Aim the beam</strong> low enough not to dazzle oncoming riders. Test on a wall at night before the first ride.</li>
<li><strong>Tidy and seal:</strong> zip-tie the cable, cover connectors and reconnect the battery.</li>
</ol>
<p>Unsure about your bike's wiring? Message us on WhatsApp and we will advise. Browse the <a href="/#products">catalogue</a>.</p>
""",
    },
    "are-motorcycle-auxiliary-lights-legal-in-kenya": {
        "title": "Are Motorcycle Auxiliary Lights Legal in Kenya? Aiming, Brightness & Safety Tips",
        "h1": "Are motorcycle auxiliary lights legal in Kenya?",
        "description": "What Kenyan riders should know about fitting auxiliary spotlights and fog lights: aiming, glare, separate switches, and checking NTSA rules.",
        "body": """
<p>Many Kenyan riders fit auxiliary lights, but the main rule of thumb is simple: <strong>do not dazzle other road users</strong>.
This is general guidance, not legal advice. For official requirements, check with the
National Transport and Safety Authority (NTSA) or the Traffic Act.</p>
<h2>Good practice</h2>
<ul>
<li>Aim the lights low and slightly toward the road edge.</li>
<li>Fit a separate handlebar switch so you can turn them off when traffic approaches.</li>
<li>Use spot/flood auxiliary lights for unlit roads, not in town.</li>
<li>Prefer DRL for daytime visibility.</li>
<li>Keep wiring protected and waterproof to avoid electrical faults.</li>
</ul>
<p>Ready to choose? Browse our <a href="/#products">motorcycle auxiliary lights</a> or read the guide on
<a href="/guides/driving-vs-fog-vs-drl-motorcycle-lights">driving vs fog vs DRL lights</a>.</p>
""",
    },
}
