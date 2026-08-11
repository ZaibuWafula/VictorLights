"""
seed.py — one-off script that loads the 5 original products into the DB.
Run with: python -m app.seed
Safe to re-run: it upserts by slug instead of duplicating rows.

Images: seeded here with placeholder photos (picsum.photos, deterministic by
slug so they don't change on re-seed) so the site looks right immediately.
Swap these for real product photos before going live — see README "Images".
"""
import json
from dotenv import load_dotenv
load_dotenv()

from app.db import init_db, db_cursor

PRODUCTS = [
    dict(
        slug="victor-beam-x1",
        name="Victor Beam X1",
        description="High-power LED driving lights. 60W output, spot+flood combo beam. Perfect for long distance visibility.",
        details=(
            "The Beam X1 pairs a 60W LED array with a combo spot+flood lens, so you get a "
            "tight, punchy throw down the centre of the road plus wide peripheral fill — "
            "useful on unlit highway stretches and for spotting hazards at the road's edge. "
            "Housing is CNC-machined aluminium with a sealed IP68 gasket, rated for full "
            "submersion, not just splash resistance. Includes wiring harness, relay, "
            "handlebar switch, and mounting brackets sized for most fork diameters. "
            "Typical install time is 20–30 minutes with basic hand tools."
        ),
        images=[
            "https://picsum.photos/seed/victor-beam-x1-1/800/600",
            "https://picsum.photos/seed/victor-beam-x1-2/800/600",
            "https://picsum.photos/seed/victor-beam-x1-3/800/600",
        ],
        price=4500, compare_price=5500, tag="BESTSELLER", stock=25,
    ),
    dict(
        slug="victor-drl-pro",
        name="Victor DRL Pro",
        description="Daytime Running Lights in white and amber. Dual intensity, waterproof, increases your visibility to other motorists.",
        details=(
            "Dual-colour running lights: steady white for daytime visibility, switches to "
            "amber for a more traditional look at dusk or as a turn-signal accent depending "
            "on how you wire them. Ultra-thin 8mm profile fits into fairings and fork legs "
            "where bulkier lights won't. Waterproof to IP67, with a 2-year-rated LED chipset. "
            "Comes as a pair with a shared control box — no separate driver per light."
        ),
        images=[
            "https://picsum.photos/seed/victor-drl-pro-1/800/600",
            "https://picsum.photos/seed/victor-drl-pro-2/800/600",
        ],
        price=2800, compare_price=3500, tag="POPULAR", stock=40,
    ),
    dict(
        slug="victor-fog-mini",
        name="Victor Fog Mini",
        description="Compact 27W fog light kit. Wide beam pattern for bad weather riding. Includes wiring harness and switch.",
        details=(
            "A wide, low-mounted flood pattern designed to sit beneath the worst of fog and "
            "rain glare rather than bouncing your own headlight back at you. 27W per unit, "
            "6000K white output. Compact enough to mount low on crash bars or fork lowers "
            "without looking bolted-on. Kit includes both lights, wiring harness, inline "
            "fuse, and a handlebar-mount switch."
        ),
        images=[
            "https://picsum.photos/seed/victor-fog-mini-1/800/600",
            "https://picsum.photos/seed/victor-fog-mini-2/800/600",
        ],
        price=3200, compare_price=4000, tag=None, stock=30,
    ),
    dict(
        slug="victor-amber-guard",
        name="Victor Amber Guard",
        description="Crash bar mounted amber safety lights. Creates a light triangle for maximum conspicuity. Strobe and steady modes.",
        details=(
            "Mounts directly to most crash bars to create a low, wide amber light triangle — "
            "aimed at making the bike's width and presence more obvious to other drivers at "
            "junctions and roundabouts, not at lighting the road itself. Switchable between "
            "steady-on and a slow strobe pattern. Weatherproof housing, low current draw "
            "designed to run continuously off the bike's electrical system without draining "
            "the battery on short trips."
        ),
        images=[
            "https://picsum.photos/seed/victor-amber-guard-1/800/600",
        ],
        price=3500, compare_price=4200, tag="SAFETY", stock=20,
    ),
    dict(
        slug="victor-mount-pro",
        name="Victor Mount Pro",
        description="Universal mounting kit. Fork clamps, crash bar mounts, fender brackets. Fits most motorcycle models.",
        details=(
            "The mounting kit sold separately from the lights themselves, for riders who "
            "want to plan their own layout or add a second set of lights later. Includes "
            "fork clamps (33–43mm), crash bar U-bolts, and fender brackets, all in "
            "powder-coated steel. One kit covers most common mounting points on a single "
            "bike; buy two if you're mounting lights front and rear."
        ),
        images=[
            "https://picsum.photos/seed/victor-mount-pro-1/800/600",
        ],
        price=1500, compare_price=2000, tag=None, stock=60,
    ),
]


def seed():
    init_db()
    with db_cursor() as cur:
        for p in PRODUCTS:
            row = dict(p)
            row["images_json"] = json.dumps(row.pop("images"))
            cur.execute(
                """
                INSERT INTO products
                    (slug, name, description, details, images_json, price, compare_price, tag, stock)
                VALUES (:slug, :name, :description, :details, :images_json,
                        :price, :compare_price, :tag, :stock)
                ON CONFLICT(slug) DO UPDATE SET
                    name = excluded.name,
                    description = excluded.description,
                    details = excluded.details,
                    images_json = excluded.images_json,
                    price = excluded.price,
                    compare_price = excluded.compare_price,
                    tag = excluded.tag
                """,
                row,
            )
    print(f"Seeded {len(PRODUCTS)} products into the database.")


if __name__ == "__main__":
    seed()
