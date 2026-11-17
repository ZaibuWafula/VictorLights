"""
seo.py — crawlable pages for search engines.

The storefront (public/index.html) renders products with JavaScript, which
Google can handle but indexes slowly and which gives each product no URL of
its own. This module adds, all server-rendered:

  /                        homepage HTML with meta tags, JSON-LD, product links, FAQ
  /products/{slug}         one indexable page per product (Product schema)
  /guides/ , /guides/{x}   keyword-targeted buying/installation guides
  /sitemap.xml, /robots.txt

Routes here must be registered BEFORE the StaticFiles mount in main.py.
"""
import json
import os
from html import escape
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse, Response

from app.db import db_cursor
from app.routers.products import row_to_product
from app import content as C

router = APIRouter()

PUBLIC_DIR = Path(__file__).resolve().parent.parent / "public"


def site_url() -> str:
    return os.getenv("SITE_URL", "https://victorlights.co.ke").rstrip("/")


def abs_url(u: str) -> str:
    if u.startswith("http"):
        return u
    return site_url() + "/" + u.lstrip("/")


def wa_link(text: str) -> str:
    n = "".join(ch for ch in os.getenv("WHATSAPP_NUMBER", "") if ch.isdigit())
    return f"https://wa.me/{n}?text={quote(text)}" if n else "#"


def jsonld(obj) -> str:
    # "</" is escaped so product text can never close the script tag.
    return '<script type="application/ld+json">' + json.dumps(obj, ensure_ascii=False).replace("</", "<\\/") + "</script>"


def get_products():
    with db_cursor() as cur:
        cur.execute(
            """SELECT id, slug, name, description, details, images_json,
                      price, compare_price, tag, stock
               FROM products WHERE active = 1 ORDER BY id ASC"""
        )
        return [row_to_product(r) for r in cur.fetchall()]


def trim(text: str, n: int = 158) -> str:
    text = " ".join(text.split())
    return text if len(text) <= n else text[: n - 1].rsplit(" ", 1)[0] + "…"


def business_schema() -> dict:
    base = site_url()
    return {
        "@context": "https://schema.org",
        "@type": "Store",
        "@id": base + "/#business",
        "name": C.SITE_NAME,
        "url": base + "/",
        "description": C.HOME_DESCRIPTION,
        "email": "info@victorlights.co.ke",
        "areaServed": {"@type": "Country", "name": "Kenya"},
        "address": {
            "@type": "PostalAddress",
            "streetAddress": "Industrial Area",
            "addressLocality": "Nairobi",
            "addressCountry": "KE",
        },
        "paymentAccepted": "M-Pesa, Bank transfer, Cash on delivery",
        "currenciesAccepted": "KES",
    }


def product_schema(p: dict) -> dict:
    base = site_url()
    url = f"{base}/products/{p['slug']}"
    offer = {
        "@type": "Offer",
        "url": url,
        "priceCurrency": "KES",
        "price": str(p["price"]),
        "availability": "https://schema.org/InStock" if p["stock"] > 0 else "https://schema.org/OutOfStock",
        "itemCondition": "https://schema.org/NewCondition",
        "seller": {"@id": base + "/#business"},
    }
    d = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": p["name"],
        "description": p["description"],
        "sku": p["slug"],
        "brand": {"@type": "Brand", "name": C.SITE_NAME},
        "offers": offer,
    }
    if p["images"]:
        d["image"] = [abs_url(i) for i in p["images"]]
    return d


# ---------------------------------------------------------------- homepage

HOME_CSS = """<style>
.seo-block{max-width:860px;margin:0 auto;padding:3rem 1.25rem;line-height:1.7}
.seo-block h2{font-family:var(--font-display);margin-bottom:.75rem}
.seo-block p{margin-bottom:1rem}.seo-block a{color:var(--amber-dim);text-decoration:underline}
.seo-faq details{border-bottom:1px solid var(--line-light);padding:.9rem 0}
.seo-faq summary{cursor:pointer;font-weight:600}.seo-faq details p{margin:.6rem 0 0}
.seo-links a{display:inline-block;margin:0 1rem .5rem 0}
.product-title-link{color:inherit;text-decoration:none}
</style>"""


def static_cards(products) -> str:
    out = []
    for p in products:
        img = (f'<img src="{escape(p["images"][0])}" alt="{escape(p["name"])} motorcycle auxiliary light Kenya" '
               f'loading="lazy" width="800" height="600">') if p["images"] else ""
        out.append(
            f'<div class="product-card"><div class="product-image">{img}</div>'
            f'<div class="product-info"><h3><a class="product-title-link" href="/products/{escape(p["slug"])}">{escape(p["name"])}</a></h3>'
            f'<p>{escape(p["description"])}</p>'
            f'<div class="price-row"><span class="price-tag"><span class="ccy">KES</span>{int(p["price"]):,}</span></div></div></div>'
        )
    return "".join(out)


def build_home() -> str:
    html = (PUBLIC_DIR / "index.html").read_text(encoding="utf-8")
    base = site_url()
    products = get_products()

    head = f"""
    <link rel="canonical" href="{base}/">
    <meta name="robots" content="index, follow, max-image-preview:large">
    <meta name="theme-color" content="#12141a">
    <meta property="og:type" content="website">
    <meta property="og:site_name" content="{C.SITE_NAME}">
    <meta property="og:locale" content="en_KE">
    <meta property="og:title" content="{escape(C.HOME_TITLE)}">
    <meta property="og:description" content="{escape(C.HOME_DESCRIPTION)}">
    <meta property="og:url" content="{base}/">
    {('<meta property="og:image" content="%s">' % escape(abs_url(products[0]["images"][0]))) if products and products[0]["images"] else ""}
    <meta name="twitter:card" content="summary_large_image">
    {jsonld(business_schema())}
    {jsonld({"@context": "https://schema.org", "@type": "WebSite", "name": C.SITE_NAME, "url": base + "/"})}
    {jsonld({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in C.HOME_FAQ]})}
    {jsonld({"@context": "https://schema.org", "@type": "ItemList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "url": f"{base}/products/{p['slug']}", "name": p["name"]}
        for i, p in enumerate(products)]})}
    {HOME_CSS}
"""
    import re
    html = re.sub(r"<title>.*?</title>", f"<title>{escape(C.HOME_TITLE)}</title>", html, count=1, flags=re.S)
    html = re.sub(r'<meta name="description"[^>]*>', f'<meta name="description" content="{escape(C.HOME_DESCRIPTION)}">', html, count=1)
    html = html.replace("</head>", head + "</head>", 1)

    # Server-rendered product cards (JS replaces them with the interactive version).
    html = html.replace('<p style="color:var(--steel);">Loading products…</p>', static_cards(products), 1)

    faq = "".join(f"<details><summary>{escape(q)}</summary><p>{escape(a)}</p></details>" for q, a in C.HOME_FAQ)
    guides = "".join(f'<a href="/guides/{k}">{escape(v["h1"])}</a>' for k, v in C.GUIDES.items())
    extra = f"""
    <section class="on-paper"><div class="seo-block">{C.HOME_INTRO_HTML}
      <h2>Frequently asked questions</h2><div class="seo-faq">{faq}</div>
      <h2 style="margin-top:2rem">Guides for riders</h2><div class="seo-links">{guides}</div>
    </div></section>
"""
    html = html.replace("</main>", extra + "</main>", 1)
    return html


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def home():
    return HTMLResponse(build_home())


# ---------------------------------------------------------------- shared page shell

PAGE_CSS = """
:root{--ink:#12141a;--amber:#ffb627;--amber-dim:#a56f0c;--paper:#eef0f2;--steel:#5b626c}
*{box-sizing:border-box}body{margin:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:var(--paper);color:var(--ink);line-height:1.7}
header{background:var(--ink);padding:1rem 1.25rem}header a{color:#fff;text-decoration:none;font-weight:700;letter-spacing:.08em}header span{color:var(--amber)}
nav.crumbs{max-width:900px;margin:1rem auto 0;padding:0 1.25rem;font-size:.9rem;color:var(--steel)}nav.crumbs a{color:var(--steel)}
main{max-width:900px;margin:0 auto;padding:1.25rem}h1{line-height:1.2;margin:.5rem 0 1rem}h2{margin-top:2rem}
a{color:var(--amber-dim)}img{max-width:100%;height:auto;border-radius:12px}
.price{font-size:1.8rem;font-weight:700}.compare{color:var(--steel);text-decoration:line-through;font-size:1rem;margin-left:.5rem}
.btn{display:inline-block;background:#25d366;color:#04230f;padding:.8rem 1.4rem;border-radius:10px;font-weight:700;text-decoration:none;margin:.5rem .5rem .5rem 0}
.btn.alt{background:var(--amber);color:var(--ink)}
.thumbs{display:flex;gap:.5rem;flex-wrap:wrap;margin:.5rem 0}.thumbs img{width:110px}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:1rem;list-style:none;padding:0}
.cards li{background:#fff;border-radius:12px;padding:1rem}
footer{text-align:center;color:var(--steel);padding:2rem 1rem;font-size:.9rem}
"""


def shell(title, description, canonical, body, schemas=(), og_image=None) -> str:
    base = site_url()
    og = f'<meta property="og:image" content="{escape(og_image)}">' if og_image else ""
    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{escape(title)}</title>
<meta name="description" content="{escape(description)}">
<link rel="canonical" href="{escape(canonical)}">
<meta name="robots" content="index, follow, max-image-preview:large">
<meta property="og:type" content="website"><meta property="og:site_name" content="{C.SITE_NAME}">
<meta property="og:locale" content="en_KE"><meta property="og:title" content="{escape(title)}">
<meta property="og:description" content="{escape(description)}"><meta property="og:url" content="{escape(canonical)}">{og}
<meta name="twitter:card" content="summary_large_image">
{''.join(jsonld(s) for s in schemas)}
<style>{PAGE_CSS}</style></head><body>
<header><a href="/">VICTOR<span>·LIGHTS</span></a></header>
{body}
<footer>© 2026 {C.SITE_NAME} · Motorcycle auxiliary lights, Nairobi, Kenya · <a href="/">Home</a> · <a href="/guides/">Guides</a></footer>
</body></html>"""


def breadcrumb(items) -> dict:
    return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": u} for i, (n, u) in enumerate(items)]}


# ---------------------------------------------------------------- product pages

@router.get("/products/{slug}", response_class=HTMLResponse, include_in_schema=False)
def product_page(slug: str):
    p = next((x for x in get_products() if x["slug"] == slug), None)
    if not p:
        raise HTTPException(status_code=404, detail="Not found")
    base = site_url()
    url = f"{base}/products/{slug}"
    name = escape(p["name"])
    imgs = p["images"]
    gallery = ""
    if imgs:
        gallery = (f'<img src="{escape(imgs[0])}" alt="{name} – motorcycle auxiliary light in Kenya" width="800" height="600">'
                   + ('<div class="thumbs">' + "".join(
                       f'<img src="{escape(i)}" alt="{name} view {n + 2}" loading="lazy" width="110" height="82">'
                       for n, i in enumerate(imgs[1:])) + "</div>" if len(imgs) > 1 else ""))
    compare = f'<span class="compare">KES {int(p["compare_price"]):,}</span>' if p.get("compare_price") else ""
    stock = "In stock" if p["stock"] > 0 else "Out of stock"
    others = "".join(f'<li><a href="/products/{escape(o["slug"])}">{escape(o["name"])}</a><br>KES {int(o["price"]):,}</li>'
                     for o in get_products() if o["slug"] != slug)
    body = f"""
<nav class="crumbs"><a href="/">Home</a> › <a href="/#products">Motorcycle lights</a> › {name}</nav>
<main>
<h1>{name} – Motorcycle Auxiliary Light in Kenya</h1>
{gallery}
<p class="price">KES {int(p["price"]):,}{compare}</p>
<p><strong>{stock}</strong> · 12-month warranty · M-Pesa, bank transfer &amp; cash on delivery · Nationwide delivery from Nairobi</p>
<p>{escape(p["description"])}</p>
<h2>Details</h2>
<p>{escape(p.get("details") or "")}</p>
<p><a class="btn" href="{escape(wa_link('Hi Victor Lights, I want to order the ' + p['name'] + ' (KES ' + format(int(p['price']), ',') + ')'))}" rel="noopener">Order on WhatsApp</a>
<a class="btn alt" href="/#products">Add to basket on the shop page</a></p>
<h2>More motorcycle lights</h2><ul class="cards">{others}</ul>
<p>Need help choosing? Read <a href="/guides/driving-vs-fog-vs-drl-motorcycle-lights">driving vs fog vs DRL lights</a>
or see <a href="/guides/install-motorcycle-auxiliary-lights">how to install auxiliary lights</a>.</p>
</main>"""
    title = f"{p['name']} – Motorcycle Auxiliary Lights Kenya | KES {int(p['price']):,} | Victor Lights"
    desc = trim(f"Buy the {p['name']} in Kenya for KES {int(p['price']):,}. {p['description']}")
    return HTMLResponse(shell(
        title, desc, url, body,
        schemas=[business_schema(), product_schema(p),
                 breadcrumb([("Home", base + "/"), ("Motorcycle lights", base + "/#products"), (p["name"], url)])],
        og_image=abs_url(imgs[0]) if imgs else None))


# ---------------------------------------------------------------- guides

@router.get("/guides/", response_class=HTMLResponse, include_in_schema=False)
@router.get("/guides", response_class=HTMLResponse, include_in_schema=False)
def guides_index():
    base = site_url()
    items = "".join(f'<li><a href="/guides/{k}"><strong>{escape(v["h1"])}</strong></a><br>{escape(v["description"])}</li>'
                    for k, v in C.GUIDES.items())
    body = f'<main><h1>Motorcycle light guides for Kenyan riders</h1><ul class="cards">{items}</ul></main>'
    return HTMLResponse(shell("Motorcycle Light Guides for Kenya | Victor Lights",
                              "Buying, installation and safety guides for motorcycle auxiliary lights in Kenya.",
                              base + "/guides/", body,
                              schemas=[breadcrumb([("Home", base + "/"), ("Guides", base + "/guides/")])]))


@router.get("/guides/{slug}", response_class=HTMLResponse, include_in_schema=False)
def guide_page(slug: str):
    g = C.GUIDES.get(slug)
    if not g:
        raise HTTPException(status_code=404, detail="Not found")
    base = site_url()
    url = f"{base}/guides/{slug}"
    body = (f'<nav class="crumbs"><a href="/">Home</a> › <a href="/guides/">Guides</a></nav>'
            f'<main><h1>{escape(g["h1"])}</h1>{g["body"]}'
            f'<p><a class="btn alt" href="/#products">See motorcycle lights</a></p></main>')
    article = {"@context": "https://schema.org", "@type": "Article", "headline": g["h1"],
               "description": g["description"], "mainEntityOfPage": url,
               "author": {"@type": "Organization", "name": C.SITE_NAME},
               "publisher": {"@type": "Organization", "name": C.SITE_NAME}}
    return HTMLResponse(shell(g["title"], g["description"], url, body,
                              schemas=[article, breadcrumb([("Home", base + "/"), ("Guides", base + "/guides/"), (g["h1"], url)])]))


# ---------------------------------------------------------------- sitemap / robots

@router.get("/sitemap.xml", include_in_schema=False)
def sitemap():
    base = site_url()
    urls = [base + "/", base + "/guides/"]
    urls += [f"{base}/guides/{k}" for k in C.GUIDES]
    urls += [f"{base}/products/{p['slug']}" for p in get_products()]
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           + "".join(f"<url><loc>{escape(u)}</loc></url>\n" for u in urls) + "</urlset>\n")
    return Response(xml, media_type="application/xml")


@router.get("/robots.txt", include_in_schema=False)
def robots():
    base = site_url()
    return PlainTextResponse(
        f"User-agent: *\nAllow: /\nDisallow: /api/\n\nSitemap: {base}/sitemap.xml\n")
