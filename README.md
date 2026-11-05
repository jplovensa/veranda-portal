# Veranda portal — SECHA Studio+

A client presentation for the Veranda two bedroom furnishing proposal. Built with plain HTML, CSS and JavaScript, with bundled concept films, imagery and the Inter variable font.

## Complete project assets

All 26 media and font files are included in `veranda-assets.zip`. `npm run dev` or `npm start` automatically verifies the archive SHA-256 and extracts `assets/` before starting the server. There are no external browser media downloads. Three.js is installed during setup and bundled locally during the build. Keep extracted files out of commits; update the canonical archive and checksum deliberately when replacing media.

## Develop in Codex

Open this repository in Codex. Use Node.js 18+ and install the locked dependency before running the project.

```sh
npm ci
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
- `layout.js`, `layout-software.js`, `layout.css`: dimensioned 3D model, accessible controls and compatible rendering
- `prepare-viewer.mjs`: bundles Three.js, OrbitControls and the MIT licence locally
- `build.mjs`: creates and verifies the complete `_site/` production output
- `prepare-assets.mjs`: verifies and unpacks the media archive into `assets/`
- `server.mjs`: dependency-free development server
- `AGENTS.md`: project constraints for Codex

## Commercial baseline — revision 04

All amounts include VAT. Planned package: IDR 180 million. Controlled reserve: IDR 10 million. Maximum cap: IDR 190 million. Kitchen and dining: IDR 27 million, including the full IDR 7 million transfer from the bathroom. The complete Veranda-provided bathroom stays untouched and has IDR 0 allocated. The proposed EPS partition is optional and unpriced; fund it through approved offsets or reserve within the existing cap.

Films and renders are illustrative, not measured drawings or completed-project photographs. A survey, product selection and supplier-backed final quotation are required before ordering.

## Data and access

Review notes stay in browser localStorage and can be downloaded as text. There is no server submission, customer database, approval workflow or order placement. The live portal is https://jplovensa.github.io/veranda-portal/ . GitHub changes publish through GitHub Actions. The older Sites publication is separate and is not automatically updated.

## Assets and licensing

Project images, films and branding are supplied for this presentation and are not licensed for public redistribution. Inter is bundled under the SIL Open Font License 1.1; see `assets/fonts/OFL.txt`.

## Interactive 3D layout

Open `#layout` for orbit and plan views, room selection, a guided camera tour, dimension and furniture toggles, an optional EPS screen and PNG export of the current view. WebGL uses Three.js materials and lighting; browsers without graphics acceleration use a compatible projected mesh renderer. No external runtime CDN is required.

The model follows the uploaded `2BR.pdf` plan. Printed bottom and left dimension chains span 8.5 m each; these are datums, not a floor-area calculation. The balcony is labelled 1 × 3 m. The second-bedroom width (approximately 3.7 m) is traced. Ceiling height (2.7 m), wall thickness and furniture sizes are planning assumptions. Shared lift/lobby geometry is outside the unit. This is a concept planning model requiring an on-site survey before manufacture or installation. The bathroom is existing context only; its scope remains IDR 0. EPS is optional and unpriced.

Three.js is distributed under the MIT licence, copied to `vendor/THREE-LICENSE.txt` during preparation. Vendor files and extracted assets are build outputs.
