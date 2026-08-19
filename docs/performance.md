# Measurements

Every number in this repository comes from one script sitting next to it: `tools/measure.js`. It serves the static files on a local port, drives Chromium over them through Playwright, counts the bytes of every response and reads the DOM size. Nothing here is eyeballed.

[← back to the overview](../README.md)

---

## Running it

```bash
npm i -D playwright        # once
node tools/measure.js      # external hosts blocked
node tools/measure.js --keep-external   # with the font and the map
```

By default requests to `fonts.googleapis.com`, `fonts.gstatic.com`, `unpkg.com` and the CARTO tiles are blocked. That measures the weight of what this repository serves, not what the internet adds to it.

---

## Before

The first version, per visit:

```
 3936 KB  image     logo.png
  156 KB  document  index.html
────────────────────────────────
 4093 KB  total across 2 requests
  750     DOM nodes
```

The logo was a 2048×2048 PNG loaded twice: in the hero for a 220 CSS pixel render and in the header for a 38 pixel icon. Both times the browser pulled the full file and decoded four megapixels to paint a circle the size of a fingernail. A byte-identical copy, `logo.png.png`, sat next to it in the repository — another 3.8 MB that nothing ever referenced.

## After

```
  157 KB  document  index.html
   17 KB  image     logo.webp
────────────────────────────────
  174 KB  total across 2 requests
  755     DOM nodes, 2 images
```

| Metric | Before | After | Delta |
|---|---|---|---|
| First visit weight | 4093 KB | 174 KB | −96% |
| Logo | 3936 KB | 17 KB | −99.6% |
| `index.html` | 156.2 KB | 157.1 KB | +0.9 KB |
| `index.html` gzipped | 31.4 KB | 31.8 KB | +0.4 KB |
| Requests | 2 | 2 | — |
| DOM nodes | 750 | 755 | +5 |

On top of that comes the font from Google Fonts: the latin subset of Bebas Neue is 13.4 KB, plus 210 bytes of CSS and two requests to a third-party domain. It is deliberately not in the table, because the repository does not serve it.

---

## What was actually done

The logo was rebuilt at 640×640. The largest render on the page is 220 CSS pixels, so 640 covers even 3× density screens. The alpha channel in the source turned out to be fully opaque, so transparency is dropped without any loss — the circular shape comes from `border-radius` and `object-fit: cover` anyway.

WebP is served, PNG stays as the fallback:

```html
<picture>
  <source srcset="logo.webp" type="image/webp">
  <img class="hero-logo" src="logo.png" alt="Sushi Clan logo"
       width="220" height="220" fetchpriority="high" decoding="async">
</picture>
```

`width` and `height` remove the layout shift on load. `fetchpriority="high"` and `<link rel="preload" as="image" type="image/webp">` in `head` raise the priority of the LCP element; browsers without WebP support skip that preload because of the `type` attribute, so nobody pays extra bytes.

WebP came out at 17 KB, the PNG fallback at 30 KB. The `logo.png.png` duplicate is gone from the repository.

---

## One subtlety only a screenshot diff caught

After switching to `<picture>` I compared hero screenshots before and after, pixel by pixel. Almost everything matched, except the header: the logo and the wordmark had moved 12 pixels to the right.

The cause is `picture { display: contents }`. The rule removes the element itself from the flow, but its children become flex items of the parent — and `<source>` is one of them. An empty invisible `<source>` was eating exactly one `gap: 0.75rem` in the navigation.

A one-line fix:

```css
picture { display: contents; }
picture > source { display: none; }
```

Verified afterwards: `nav-logo-icon` sits at X 168, the same as before the change.

The lesson is that the eye cannot catch this, and a diff of two screenshots catches it in a second.

---

## What is still on the font

In an offline run, with `fonts.googleapis.com` unreachable, `DOMContentLoaded` fired after 13 seconds: the browser dutifully waited out the network timeout on a render-blocking `<link>`. With a working network that is a fraction of a second, but the dependency on somebody else's domain stays on the critical path.

The fix is self-hosting: put `bebas-neue-latin.woff2` (13.4 KB) in the repository, declare `@font-face` in the same inline CSS, drop both `preconnect` hints and the `<link>`. One external domain fewer, two requests fewer, and the first paint depends only on our own server. Bebas Neue ships under OFL 1.1, so the licence text goes into the repository along with the file.

It is the first item on the [roadmap](roadmap.md).

---

## What these measurements do not show

The script counts bytes and nodes, not user experience. I have not captured real Core Web Vitals from the live domain, on Georgian mobile networks, with the actual font and map: I do not have access to this site's production analytics. Once that exists, LCP, INP and CLS from the field will live here too, instead of lab numbers.

---

[← back to the overview](../README.md) · [decisions](decisions.md) · [architecture](architecture.md) · [roadmap](roadmap.md)
