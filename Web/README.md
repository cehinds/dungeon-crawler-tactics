# Playable browser build

This is a standalone Blazor WebAssembly presentation of the pure C# game in `UnityPackage/Runtime/Core/`. The browser runs those exact C# sources through the .NET WebAssembly runtime. JavaScript handles rendering, input, downloads and local storage; it contains no combat resolver, enemy AI or movement rules.

The Unity 6 source project is provided separately. This browser build is **not a Unity Web export**.

## Play the included build

From the repository root, with Python 3 installed:

```sh
python3 -m http.server 5173 --directory Web/publish/wwwroot
```

Open <http://localhost:5173>. Serve over HTTP rather than opening `index.html` directly. The first load downloads the .NET runtime; subsequent loads use the browser cache. No API key, server process beyond static hosting, account, or external network service is required to play.

The browser saves after commands. **Save & options** supports JSON export, import, local save recovery and a new run. A rejected import keeps the live session intact. Preview and cancel do not spend resources or persist an unfinished forecast.

## Rebuild

Requires a .NET 8 SDK and access to NuGet for the first restore:

```sh
dotnet publish Web/DungeonCrawlerTactics.Web.csproj -c Release -o Web/publish
```

No AOT compiler or `wasm-tools` workload is required. This build uses interpreted WebAssembly and disables trimming to preserve the public-field JSON/JavaScript boundary. Published files total roughly 43 MB before hosting compression. A production host can enable Brotli/gzip and long-lived caching for fingerprinted framework files.

Combat and game JSON are linked from the canonical `UnityPackage/Runtime/Data/` directory at build time. The presentation uses original pixel sprites from `UnityPackage/Runtime/Resources/Art/` copied into `wwwroot/assets/`.

## Controls

- Camp: select a crawler, change class, deploy or reserve, then enter with exactly four crawlers.
- Battle: select an ally; click a blue outlined tile to move. Choose an ability or open **Shared consumables**, then click the required enemy, ally or terrain tile. Review the forecast and confirm or cancel.
- Each crawler can move once and act once in a round. Acting ends that crawler’s activation. **Wait crawler** spends that activation. **End party turn** lets enemies act.
- Defeat every enemy, choose one sponsor reward, and continue. Three encounters complete the floor. Defeat offers retry or a new run.
- **Esc** cancels a forecast or target selection. **?** opens help.

## Integration boundary

`Program.cs` exposes four `JSInvokable` methods: `Initialize`, `Dispatch`, `GetSave` and `LoadSave`. DTOs serialize with `IncludeFields = true`, matching the public fields consumed by Unity `JsonUtility`. All commands go through `GameSession.Handle`; all forecasts and committed actions use the shared C# resolver.

`wwwroot/game.js` renders the returned view. `window.dungeon` exposes the same bridge to browser verification scripts after boot. It does not bypass the command rules.
