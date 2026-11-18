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
:root{--ink:#12141a;--ink-soft:#1b1e26;--panel:#21242d;--amber:#ffb627;--amber-dim:#a56f0c;--paper:#eef0f2;--steel:#5b626c;--line:rgba(18,20,26,.1);--success:#1f9d5b;--danger:#e4572e;
--display:'Space Grotesk',system-ui,-apple-system,sans-serif}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:var(--paper);color:var(--ink);line-height:1.65}
h1,h2,h3{font-family:var(--display);line-height:1.15;letter-spacing:-.01em}
a{color:var(--amber-dim)}img{max-width:100%;height:auto;display:block}
.wrap{max-width:1100px;margin:0 auto;padding:0 1.25rem}
header.top{background:var(--ink);border-bottom:1px solid rgba(255,255,255,.08);position:sticky;top:0;z-index:20}
header.top .wrap{display:flex;align-items:center;justify-content:space-between;height:60px}
header.top .logo{font-family:var(--display);color:#fff;text-decoration:none;font-weight:700;letter-spacing:.08em}
header.top .logo span{color:var(--amber)}
header.top nav a{color:#c9ced6;text-decoration:none;margin-left:1.25rem;font-size:.95rem}header.top nav a:hover{color:var(--amber)}
.crumbs{padding:1rem 0 .25rem;font-size:.88rem;color:var(--steel)}.crumbs a{color:var(--steel);text-decoration:none}.crumbs a:hover{text-decoration:underline}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:.5rem;padding:.9rem 1.5rem;border-radius:12px;font-weight:700;text-decoration:none;border:0;cursor:pointer;font-size:1rem;transition:transform .15s,box-shadow .15s}
.btn:hover{transform:translateY(-1px);box-shadow:0 6px 18px rgba(0,0,0,.18)}
.btn.wa{background:#25d366;color:#04230f}.btn.amber{background:var(--amber);color:var(--ink)}.btn.ghost{background:#fff;color:var(--ink);border:1px solid var(--line)}
/* product layout */
.product{display:grid;grid-template-columns:minmax(0,1.1fr) minmax(0,1fr);gap:2.5rem;padding:1rem 0 2.5rem;align-items:start}
.gallery{position:sticky;top:76px}
.g-main{position:relative;background:#fff;border-radius:18px;overflow:hidden;border:1px solid var(--line);aspect-ratio:4/3;cursor:zoom-in}
.g-main img{width:100%;height:100%;object-fit:contain;transition:opacity .2s}
.g-arrow{position:absolute;top:50%;transform:translateY(-50%);width:44px;height:44px;border-radius:50%;border:0;background:rgba(18,20,26,.75);color:#fff;font-size:1.3rem;cursor:pointer;display:flex;align-items:center;justify-content:center}
.g-arrow:hover{background:var(--amber);color:var(--ink)}.g-prev{left:.75rem}.g-next{right:.75rem}
.g-count{position:absolute;right:.75rem;bottom:.75rem;background:rgba(18,20,26,.75);color:#fff;font-size:.8rem;padding:.2rem .6rem;border-radius:999px}
.g-badge{position:absolute;left:.75rem;top:.75rem;background:var(--amber);color:var(--ink);font-weight:700;font-size:.78rem;padding:.3rem .7rem;border-radius:999px;letter-spacing:.04em;text-transform:uppercase}
.g-thumbs{display:flex;gap:.6rem;margin-top:.75rem;overflow-x:auto;padding-bottom:.25rem}
.g-thumb{flex:0 0 84px;height:64px;border-radius:10px;border:2px solid transparent;padding:0;background:#fff;cursor:pointer;overflow:hidden;opacity:.7}
.g-thumb img{width:100%;height:100%;object-fit:cover}.g-thumb.on{border-color:var(--amber);opacity:1}.g-thumb:hover{opacity:1}
.info h1{font-size:clamp(1.6rem,3.5vw,2.3rem);margin:.2rem 0 .6rem}
.eyebrow{font-size:.78rem;letter-spacing:.14em;text-transform:uppercase;color:var(--amber-dim);font-weight:700}
.pricebox{display:flex;align-items:baseline;flex-wrap:wrap;gap:.75rem;margin:.5rem 0}
.price{font-family:var(--display);font-size:2.2rem;font-weight:700}.price small{font-size:1rem;color:var(--steel);margin-right:.25rem}
.compare{color:var(--steel);text-decoration:line-through}.save{background:#fdeede;color:#a14a00;font-weight:700;font-size:.8rem;padding:.2rem .6rem;border-radius:999px}
.stock{display:inline-flex;align-items:center;gap:.4rem;font-size:.9rem;font-weight:600}.stock::before{content:"";width:9px;height:9px;border-radius:50%;background:var(--success)}
.stock.out::before{background:var(--danger)}.stock.low::before{background:var(--amber)}
.lead{font-size:1.05rem;color:#3a3f48;margin:1rem 0}
.cta{display:flex;flex-wrap:wrap;gap:.75rem;margin:1.25rem 0}
.trust{display:grid;grid-template-columns:repeat(2,1fr);gap:.6rem;margin:1.25rem 0;padding:0;list-style:none}
.trust li{background:#fff;border:1px solid var(--line);border-radius:12px;padding:.7rem .9rem;font-size:.9rem;display:flex;gap:.6rem;align-items:center}
.trust b{display:block;font-size:.95rem}.trust i{font-style:normal;font-size:1.3rem}
.card{background:#fff;border:1px solid var(--line);border-radius:16px;padding:1.5rem;margin-bottom:1.25rem}
.card h2{margin:0 0 .75rem;font-size:1.3rem}
.dark{background:var(--ink);color:#e8eaee;border-radius:18px;padding:1.75rem;margin:1rem 0 2rem}.dark h2{color:#fff;margin-top:0}.dark a{color:var(--amber)}
.related{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:1rem;list-style:none;padding:0;margin:0}
.related a{display:block;background:#fff;border:1px solid var(--line);border-radius:14px;overflow:hidden;text-decoration:none;color:var(--ink);transition:transform .15s,box-shadow .15s}
.related a:hover{transform:translateY(-3px);box-shadow:0 10px 24px rgba(0,0,0,.12)}
.related img{width:100%;aspect-ratio:4/3;object-fit:cover}.related div{padding:.8rem 1rem}.related strong{display:block}.related span{color:var(--steel);font-size:.92rem}
/* text pages */
main.article{max-width:780px;margin:0 auto;padding:1rem 1.25rem 3rem}main.article h1{font-size:clamp(1.7rem,4vw,2.5rem)}main.article h2{margin-top:2rem}
.guide-list{list-style:none;padding:0;display:grid;gap:1rem}.guide-list li{background:#fff;border:1px solid var(--line);border-radius:14px;padding:1.1rem 1.25rem}
footer.foot{background:var(--ink);color:#9aa1ab;text-align:center;padding:2rem 1rem;font-size:.9rem;margin-top:2rem}footer.foot a{color:var(--amber)}
.lightbox{position:fixed;inset:0;background:rgba(10,11,14,.94);z-index:50;display:none;align-items:center;justify-content:center;padding:1rem}
.lightbox.open{display:flex}.lightbox img{max-height:92vh;max-width:96vw;object-fit:contain;border-radius:8px}
.lightbox button{position:absolute;top:1rem;right:1rem;background:#fff;border:0;border-radius:999px;width:42px;height:42px;font-size:1.2rem;cursor:pointer}
.sticky-cta{display:none}
@media(max-width:820px){.product{grid-template-columns:1fr;gap:1.25rem}.gallery{position:static}
.sticky-cta{display:flex;position:fixed;bottom:0;left:0;right:0;z-index:15;background:var(--ink);padding:.7rem 1rem;gap:.75rem;align-items:center;justify-content:space-between}
.sticky-cta .price{color:#fff;font-size:1.3rem}.sticky-cta .btn{padding:.7rem 1.2rem}body{padding-bottom:70px}header.top nav a:not(:last-child){display:none}}
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
<link rel="icon" href="/favicon.ico" sizes="48x48"><link rel="icon" href="/favicon.svg" type="image/svg+xml"><link rel="apple-touch-icon" href="/apple-touch-icon.png"><link rel="manifest" href="/site.webmanifest">
<meta name="robots" content="index, follow, max-image-preview:large">
<meta property="og:type" content="website"><meta property="og:site_name" content="{C.SITE_NAME}">
<meta property="og:locale" content="en_KE"><meta property="og:title" content="{escape(title)}">
<meta property="og:description" content="{escape(description)}"><meta property="og:url" content="{escape(canonical)}">{og}
<meta name="twitter:card" content="summary_large_image">
{''.join(jsonld(s) for s in schemas)}
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&display=swap" rel="stylesheet">
<style>{PAGE_CSS}</style></head><body>
<header class="top"><div class="wrap"><a class="logo" href="/">VICTOR<span>·LIGHTS</span></a><nav><a href="/#products">Shop</a><a href="/guides/">Guides</a><a href="/#contact">Contact</a></nav></div></header>
{body}
<footer class="foot">© 2026 {C.SITE_NAME} · Motorcycle auxiliary lights, Nairobi, Kenya · <a href="/">Home</a> · <a href="/guides/">Guides</a></footer>
</body></html>"""


def breadcrumb(items) -> dict:
    return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": u} for i, (n, u) in enumerate(items)]}


# ---------------------------------------------------------------- product pages

@router.get("/products/{slug}", response_class=HTMLResponse, include_in_schema=False)
def product_page(slug: str):
    allp = get_products()
    p = next((x for x in allp if x["slug"] == slug), None)
    if not p:
        raise HTTPException(status_code=404, detail="Not found")
    base = site_url()
    url = f"{base}/products/{slug}"
    name = escape(p["name"])
    imgs = p["images"]
    price = int(p["price"])
    cmp_ = int(p["compare_price"]) if p.get("compare_price") else 0
    save = round((cmp_ - price) * 100 / cmp_) if cmp_ > price else 0

    if imgs:
        thumbs = "".join(
            f'<button type="button" class="g-thumb{" on" if n == 0 else ""}" data-src="{escape(i)}" '
            f'data-alt="{name} - view {n + 1}" aria-label="Show image {n + 1}">'
            f'<img src="{escape(i)}" alt="{name} thumbnail {n + 1}" loading="lazy" width="84" height="64"></button>'
            for n, i in enumerate(imgs))
        arrows = ('<button type="button" class="g-arrow g-prev" aria-label="Previous image">&#8249;</button>'
                  '<button type="button" class="g-arrow g-next" aria-label="Next image">&#8250;</button>'
                  f'<span class="g-count"><span id="gIdx">1</span> / {len(imgs)}</span>') if len(imgs) > 1 else ""
        badge = f'<span class="g-badge">{escape(p["tag"])}</span>' if p.get("tag") else ""
        gallery = (f'<div class="gallery" id="gallery"><div class="g-main" id="gMain">{badge}'
                   f'<img id="gImg" src="{escape(imgs[0])}" alt="{name} - motorcycle auxiliary light in Kenya" width="800" height="600">{arrows}</div>'
                   + (f'<div class="g-thumbs">{thumbs}</div>' if len(imgs) > 1 else "") + '</div>')
    else:
        gallery = '<div class="gallery"><div class="g-main"></div></div>'

    if p["stock"] <= 0:
        stock = '<span class="stock out">Out of stock</span>'
    elif p["stock"] <= 5:
        stock = f'<span class="stock low">Only {p["stock"]} left</span>'
    else:
        stock = '<span class="stock">In stock</span>'

    wa = escape(wa_link(f"Hi Victor Lights, I want to order the {p['name']} (KES {price:,})"))
    others = "".join(
        f'<li><a href="/products/{escape(o["slug"])}">'
        + (f'<img src="{escape(o["images"][0])}" alt="{escape(o["name"])}" loading="lazy" width="400" height="300">' if o["images"] else "")
        + f'<div><strong>{escape(o["name"])}</strong><span>KES {int(o["price"]):,}</span></div></a></li>'
        for o in allp if o["slug"] != slug)
    details = "".join(f"<p>{escape(x)}</p>" for x in (p.get("details") or "").split("\n") if x.strip())

    body = f"""
<div class="wrap">
<nav class="crumbs"><a href="/">Home</a> &rsaquo; <a href="/#products">Motorcycle lights</a> &rsaquo; {name}</nav>
<section class="product">
  {gallery}
  <div class="info">
    <span class="eyebrow">Motorcycle auxiliary light</span>
    <h1>{name}</h1>
    <div class="pricebox"><span class="price"><small>KES</small>{price:,}</span>
      {f'<span class="compare">KES {cmp_:,}</span><span class="save">Save {save}%</span>' if save else ''}</div>
    {stock}
    <p class="lead">{escape(p["description"])}</p>
    <div class="cta"><a class="btn wa" href="{wa}" rel="noopener">Order on WhatsApp</a>
      <a class="btn ghost" href="/#products">Back to catalogue</a></div>
    <ul class="trust">
      <li><i>&#128737;</i><span><b>Warranty</b>12-month replacement</span></li>
      <li><i>&#128666;</i><span><b>Delivery</b>Nairobi &amp; countrywide</span></li>
      <li><i>&#128179;</i><span><b>Pay with</b>M-Pesa, bank, COD</span></li>
      <li><i>&#128167;</i><span><b>Built for rain</b>Waterproof housing</span></li>
    </ul>
  </div>
</section>
<div class="card"><h2>About the {name}</h2>{details or "<p>" + escape(p["description"]) + "</p>"}</div>
<div class="dark"><h2>Not sure it fits your bike?</h2>
<p>Message us your motorcycle model on WhatsApp and we will confirm fitment and wiring. Or read our
<a href="/guides/install-motorcycle-auxiliary-lights">installation guide</a> and
<a href="/guides/driving-vs-fog-vs-drl-motorcycle-lights">driving vs fog vs DRL comparison</a>.</p>
<a class="btn wa" href="{wa}" rel="noopener">Ask on WhatsApp</a></div>
{f'<h2>More motorcycle lights</h2><ul class="related">{others}</ul>' if others else ''}
</div>
<div class="sticky-cta"><span class="price">KES {price:,}</span><a class="btn wa" href="{wa}" rel="noopener">Order on WhatsApp</a></div>
<div class="lightbox" id="lb"><button type="button" aria-label="Close">&#10005;</button><img alt=""></div>
<script>
(function(){{
 var img=document.getElementById('gImg'); if(!img) return;
 var th=[].slice.call(document.querySelectorAll('.g-thumb')), n=th.length, i=0, idx=document.getElementById('gIdx');
 function go(k){{ if(!n) return; i=(k+n)%n; img.style.opacity=.3;
   img.src=th[i].dataset.src; img.alt=th[i].dataset.alt; img.onload=function(){{img.style.opacity=1}};
   th.forEach(function(t,j){{t.classList.toggle('on',j===i)}}); if(idx) idx.textContent=i+1;
   th[i].scrollIntoView({{block:'nearest',inline:'center',behavior:'smooth'}}); }}
 th.forEach(function(t,j){{t.addEventListener('click',function(){{go(j)}})}});
 var pv=document.querySelector('.g-prev'), nx=document.querySelector('.g-next');
 if(pv) pv.addEventListener('click',function(e){{e.stopPropagation();go(i-1)}});
 if(nx) nx.addEventListener('click',function(e){{e.stopPropagation();go(i+1)}});
 var lb=document.getElementById('lb'), lbi=lb.querySelector('img');
 document.getElementById('gMain').addEventListener('click',function(){{lbi.src=img.src;lb.classList.add('open')}});
 lb.addEventListener('click',function(){{lb.classList.remove('open')}});
 document.addEventListener('keydown',function(e){{
   if(e.key==='ArrowLeft')go(i-1); else if(e.key==='ArrowRight')go(i+1); else if(e.key==='Escape')lb.classList.remove('open');}});
 var x0=null, m=document.getElementById('gMain');
 m.addEventListener('touchstart',function(e){{x0=e.touches[0].clientX}},{{passive:true}});
 m.addEventListener('touchend',function(e){{ if(x0===null)return; var dx=e.changedTouches[0].clientX-x0;
   if(Math.abs(dx)>40) go(dx<0?i+1:i-1); x0=null; }});
}})();
</script>"""
    title = f"{p['name']} – Motorcycle Auxiliary Lights Kenya | KES {price:,} | Victor Lights"
    desc = trim(f"Buy the {p['name']} in Kenya for KES {price:,}. {p['description']}")
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
    body = f'<main class="article"><h1>Motorcycle light guides for Kenyan riders</h1><ul class="guide-list">{items}</ul></main>'
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
    body = (f'<div class="wrap"><nav class="crumbs"><a href="/">Home</a> &rsaquo; <a href="/guides/">Guides</a></nav></div>'
            f'<main class="article"><h1>{escape(g["h1"])}</h1>{g["body"]}'
            f'<p><a class="btn amber" href="/#products">See motorcycle lights</a></p></main>')
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
