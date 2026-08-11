# Victor Lights — backend (FastAPI edition)

Same design as the Node/Express version: one Python process serves both the
JSON API and the storefront itself, backed by a single SQLite file, using
Python's built-in `sqlite3` module — no ORM, so the dependency list stays
short: `fastapi`, `uvicorn`, `pydantic`, `python-dotenv`. That's the whole
runtime footprint, comparable in weight to the Node version and noticeably
lighter than Django.

Bonus over the Node version: FastAPI auto-generates interactive API docs at
`/api/docs` — useful for testing admin endpoints without curl.

## What it does

- Serves the site (`public/index.html`) and a JSON API from the same server.
- `GET /api/products` — the live product catalog (price, stock, description).
- `POST /api/orders` — customer places an order. Prices and stock are looked
  up server-side (the browser is never trusted with prices), stock is
  decremented, and an order number like `VL-260808-2521` comes back.
- `GET /api/orders/{order_number}?phone=...` — a customer can check their
  own order status.
- `/api/*/admin/...` (products & orders) — protected by a single shared
  `x-admin-key` header, for the shop owner to update stock/prices and see
  incoming orders without touching code or redeploying.
- A simple in-memory rate limiter (no Redis) caps API calls generally and
  order creation specifically, tuned for a single small instance.
- WhatsApp stays the confirmation/payment channel — the order form gives
  you a real record of what was ordered and automatic stock tracking, then
  hands the customer a pre-filled WhatsApp message with their order number.

## Run it locally

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # edit ADMIN_KEY at minimum
python3 -m app.seed               # loads the 5 starter products into SQLite
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Visit `http://localhost:8000` for the site, `http://localhost:8000/api/docs`
for interactive API docs.

Generate a real admin key:
```bash
python3 -c "import secrets; print(secrets.token_hex(24))"
```

## Deploying somewhere cheap

Same shape as the Node version: one process, one SQLite file. The file
**must** live on a persistent disk, or your catalog/orders vanish on every
redeploy.

### Option A — Fly.io (recommended for a persistent SQLite file)
```bash
fly launch          # accept defaults, don't add a Postgres DB
fly volumes create data --size 1
```
In `fly.toml`:
```toml
[mounts]
  source = "data"
  destination = "/data"
```
```bash
fly secrets set ADMIN_KEY=your-real-key DB_PATH=/data/victorlights.db WHATSAPP_NUMBER=254712345678
fly deploy
```
Make sure your `Dockerfile`/start command runs:
`uvicorn app.main:app --host 0.0.0.0 --port 8080` (or whatever port Fly expects).

### Option B — Render.com
Add a persistent disk (a few dollars/month) mounted at `/data`, set
`DB_PATH=/data/victorlights.db` and the other env vars under Environment.
Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.

### Option C — Railway.app
Railway is billed usage-based with a $5/month Hobby minimum (no permanent
free tier as of 2026 — a one-time trial credit, then Hobby or Pro). The repo
already includes a `Dockerfile` and `railway.json` so Railway builds it
predictably instead of relying on autodetection.

1. Push this project to a GitHub repo.
2. In Railway: **New Project → Deploy from GitHub repo**, pick the repo.
   It detects `railway.json` and builds the `Dockerfile` directly.
3. **Add a volume**: right-click the canvas (or ⌘K) → New Volume. Mount it
   at `/data`. Without this, the SQLite file lives in the container's
   ephemeral filesystem and resets on every redeploy.
4. Under the service's **Variables** tab, set:
   ```
   ADMIN_KEY=your-real-key
   DB_PATH=/data/victorlights.db
   WHATSAPP_NUMBER=254712345678
   CORS_ORIGIN=*
   ```
   Don't set `PORT` yourself — Railway injects it, and the Dockerfile's
   `CMD` already reads `$PORT`.
5. Deploy. Once it's live, seed the database **once** via the Railway CLI
   (`npm i -g @railway/cli`, then `railway login` and `railway link`):
   ```bash
   railway run python -m app.seed
   ```
   Don't wire seeding into every container start — `seed.py` upserts by
   slug, so a repeat run is safe, but it would silently overwrite any price
   or stock changes you'd made through the admin API since the last deploy.
6. Generate a public domain under **Settings → Networking → Generate Domain**,
   or attach your own.

### Option D — a Kenya-local VPS (e.g. HOSTAFRICA)

Any self-managed KVM VPS with root access works — this section uses
[HOSTAFRICA's Linux VPS](https://www.hostafrica.ke/servers/linux-vps-servers/)
as a concrete example, since it's locally hosted in Kenya (lower latency to
your actual customers than a US/EU-based platform) and bills in KES. Their
cheapest tier, **C1 (~KSh 960–969/mo)** — 1 vCPU, 1GB RAM, 20GB NVMe SSD —
is enough for this app; **C2 (~KSh 1,600/mo, 2GB RAM)** gives more headroom.
Any similarly-specced Ubuntu/Debian VPS from another provider works the
same way.

The repo includes ready-to-use `deploy/victor-lights.service` (systemd) and
`deploy/Caddyfile` (automatic HTTPS) for this path.

1. **Order the VPS**, choosing Ubuntu (22.04 or 24.04) as the OS. You'll get
   root SSH access and a static IP.
2. **SSH in and create a non-root deploy user** (running as root day-to-day
   is avoidable risk):
   ```bash
   ssh root@your-server-ip
   adduser deploy && usermod -aG sudo deploy
   su - deploy
   ```
3. **Install Python and clone the repo**:
   ```bash
   sudo apt update && sudo apt install -y python3-venv python3-pip git
   git clone <your-repo-url> victor-lights-fastapi
   cd victor-lights-fastapi
   python3 -m venv venv
   venv/bin/pip install -r requirements.txt gunicorn
   cp .env.example .env
   nano .env   # set ADMIN_KEY, DB_PATH=./data/victorlights.db, WHATSAPP_NUMBER, CORS_ORIGIN
   venv/bin/python -m app.seed
   ```
4. **Install and start the systemd service** (keeps the app running and
   restarts it after crashes or reboots):
   ```bash
   sudo cp deploy/victor-lights.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now victor-lights
   sudo systemctl status victor-lights   # confirm it's active (running)
   ```
5. **Point your domain at the server**: in your domain registrar's DNS
   settings, add an A record for your domain pointing to the VPS's static
   IP. (If you register the `.co.ke` domain through the same host, they'll
   often set this up for you.)
6. **Install Caddy for automatic HTTPS** — see the instructions at the top
   of `deploy/Caddyfile`, then:
   ```bash
   sudo cp deploy/Caddyfile /etc/caddy/Caddyfile
   # edit the domain in that file first
   sudo systemctl reload caddy
   ```
   Caddy handles certificate issuance and renewal automatically; there's no
   manual certbot step.

Unlike Fly/Render/Railway, a VPS's disk is inherently persistent — there's
no separate "volume" concept to configure, and the weekly automatic backups
most VPS providers include cover the SQLite file along with everything
else. To deploy an update later: `git pull`, `venv/bin/pip install -r
requirements.txt` if dependencies changed, then `sudo systemctl restart
victor-lights`.

## Managing the shop day-to-day

No admin UI beyond `/api/docs` (which does let you try requests from the
browser, including setting the `x-admin-key` header via "Try it out" — but
you'll need to type the header manually each time since it's not a login).
Otherwise, the same curl-based flow as before:

```bash
# Update Victor Beam X1's price and stock
curl -X PATCH http://yoursite.com/api/products/admin/1 \
  -H "x-admin-key: YOUR_ADMIN_KEY" -H "Content-Type: application/json" \
  -d '{"price": 4800, "stock": 15}'

# See today's new orders
curl "http://yoursite.com/api/orders/admin/all?status=new" \
  -H "x-admin-key: YOUR_ADMIN_KEY"

# Mark an order shipped
curl -X PATCH http://yoursite.com/api/orders/admin/1 \
  -H "x-admin-key: YOUR_ADMIN_KEY" -H "Content-Type: application/json" \
  -d '{"status": "shipped"}'
```

If you want a proper point-and-click admin dashboard instead of curl calls,
that's exactly the case where Django's free built-in admin panel is worth
the extra weight — worth a rebuild if this becomes a pain point.

## Product images and detail pages

Clicking any product card opens a detail view with a larger image, an image
gallery (if you gave it more than one photo), and a longer `details` field
separate from the short card description.

Each product has:
- `images` — an ordered list of image URLs; the first is used as the card
  cover photo, and all of them appear as a gallery on the detail view.
- `details` — a longer free-text field (plain text with line breaks; there's
  no rich text/HTML support) for full specs, install notes, etc., shown
  below the short `description` on the detail view.

The seed data ships with placeholder photos from picsum.photos so the site
looks right immediately — replace them with real product photos before
going live. Two ways to do that:

**Option A — host images elsewhere, use URLs (simplest).** Upload photos to
any free image host or object storage (Cloudflare R2, Backblaze B2, or even
a Google Drive/Imgur direct link) and set the `images` field to those URLs
via the admin API:
```bash
curl -X PATCH http://localhost:8000/api/products/admin/1 \
  -H "x-admin-key: YOUR_ADMIN_KEY" -H "Content-Type: application/json" \
  -d '{"images": ["https://yourcdn.com/beam-x1-front.jpg", "https://yourcdn.com/beam-x1-mounted.jpg"]}'
```

**Option B — serve images from this same app.** Drop image files into
`public/images/` (create the folder) and reference them with a relative
path instead of a full URL, e.g. `"/images/beam-x1-front.jpg"` — since
`public/` is already served as static files, no extra code is needed. This
keeps everything in one deploy, but remember: on hosts with an ephemeral
filesystem (see "Deploying somewhere cheap" above), files dropped in after
deploy won't survive a redeploy unless they're on the same persistent disk
as the database — commit them to your repo instead so they're rebuilt every
deploy.

Update `details` the same way:
```bash
curl -X PATCH http://localhost:8000/api/products/admin/1 \
  -H "x-admin-key: YOUR_ADMIN_KEY" -H "Content-Type: application/json" \
  -d '{"details": "Full spec sheet and install notes go here..."}'
```

## M-Pesa (optional, not wired up)

Same approach as the Node version: customers pay via Till/Paybill/Send Money
and confirm on WhatsApp — zero integration needed, and how most small
Kenyan shops actually operate. `.env.example` reserves the `MPESA_*` fields
for later; adding STK Push means a Safaricom Daraja developer account, a
paybill/till number, and a public HTTPS callback URL. The natural place to
add it is a new `app/routers/mpesa.py` calling Daraja's OAuth + STK Push
endpoints and updating the matching order's `status` on callback.

## Notes on the trade-offs made here

- **Plain `sqlite3`, not SQLAlchemy/SQLModel**: fewer dependencies, plain
  SQL you can read top to bottom. Fine for a small shop's order volume;
  moving to Postgres later (Supabase/Neon free tiers) would mean swapping
  `db.py`'s connection logic and adjusting a few queries — not a rewrite.
- **In-memory rate limiter, not Redis-backed**: works correctly for one
  instance. If you ever run multiple instances behind a load balancer,
  limits would be counted per-instance rather than globally — swap in
  Redis at that point.
- **Single shared admin key, not user accounts**: no login system to build
  or secure. Rotate the key if it ever leaks.
- **No image uploads**: same as the Node version — add real product photos
  via Cloudflare R2 or Backblaze B2 (free tiers) rather than local disk.
