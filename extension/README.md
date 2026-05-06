# all-my-favs — Firefox extension

Manifest V3 popup that saves the current tab to your all-my-favs instance.

For installation, configuration, and development workflow, see:

→ **[How-to: install the Firefox extension](../docs/how-to/install-the-firefox-extension.md)**

## Files

| File              | Purpose                                                        |
|-------------------|----------------------------------------------------------------|
| `manifest.json`   | MV3 manifest, action + options page, host permissions          |
| `popup.html/js/css` | Save form (toolbar popup)                                    |
| `options.html/js` | Stores `baseUrl` + `apiKey` in `browser.storage.local`         |
| `icons/icon.svg`  | Single SVG used at every size                                  |
| `package.json`    | `web-ext` build/run/lint scripts                               |
| `.web-extrc.js`   | `web-ext` config (sourceDir, ignored files)                    |
