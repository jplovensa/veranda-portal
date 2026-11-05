# Veranda portal — SECHA Studio+

A private client presentation for the Veranda two bedroom furnishing proposal. Built with plain HTML, CSS and JavaScript, with bundled concept films, imagery and the Inter variable font.

## Complete project assets

All 26 media and font files are included in `veranda-assets.zip`. `npm run dev` or `npm start` automatically verifies the archive SHA-256 and extracts `assets/` before starting the server. There are no external media downloads or npm dependencies. Keep extracted files out of commits; update the canonical archive and checksum deliberately when replacing media.

## Develop in Codex

Open this repository in Codex. Node.js 18+ is enough; there are no npm dependencies to install.

```sh
npm run dev
```

Open http://localhost:3000. The development server is loopback-only by default. `npm run check` verifies JavaScript syntax. This GitHub repository serves the static portal from its root; the existing Sites publication uses the same three application files under `dist/` in its hosting checkout.

## Publish to GitHub Pages

Pages uses the `Deploy Veranda portal` GitHub Actions workflow. Every push to `main` runs the production build, verifies and extracts the archive, copies the application and all media into `_site/`, and publishes that complete artifact. Pages source must be GitHub Actions, rather than Deploy from a branch.

For another static host, set build command to `npm run build` and output directory to `_site`. Serving the repository root directly will omit the archived media.

## Files

- `index.html`: presentation sections and accessible markup
- `style.css`: responsive layout, Inter typography and print styles
- `app.js`: room tabs, film player, materials, budget and local review notes
- `veranda-assets.zip`: all original concept films, room renders, materials, branding and the bundled font
- `build.mjs`: creates and verifies the complete `_site/` production output
- `prepare-assets.mjs`: verifies and unpacks the media archive into `assets/`
- `server.mjs`: dependency-free development server
- `AGENTS.md`: project constraints for Codex

## Commercial baseline — revision 04

All amounts include VAT. Planned package: IDR 180 million. Controlled reserve: IDR 10 million. Maximum cap: IDR 190 million. Kitchen and dining: IDR 27 million, including the full IDR 7 million transfer from the bathroom. The complete Veranda-provided bathroom stays untouched and has IDR 0 allocated. The proposed EPS partition is optional and unpriced; fund it through approved offsets or reserve within the existing cap.

Films and renders are illustrative, not measured drawings or completed-project photographs. A survey, product selection and supplier-backed final quotation are required before ordering.

## Data and access

Review notes stay in browser localStorage and can be downloaded as text. There is no server submission, customer database, approval workflow or order placement. The repository is private. The current private preview is https://veranda-residences.jopelo16.chatgpt.site/ . GitHub changes do not automatically publish to that Site.

## Assets and licensing

Project images, films and branding are supplied for this presentation and are not licensed for public redistribution. Inter is bundled under the SIL Open Font License 1.1; see `assets/fonts/OFL.txt`.
