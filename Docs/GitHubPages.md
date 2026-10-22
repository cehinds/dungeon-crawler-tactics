# Host the browser game on GitHub Pages

The intended public source repository is `cehinds/dungeon-crawler-tactics`, with `main` as its default branch. Once that repository exists and deployment succeeds, the expected game URL is:

<https://cehinds.github.io/dungeon-crawler-tactics/>

This URL is a deployment target, not evidence that publication has completed. Repository creation, pushing the source and a successful Pages workflow run are required before it is live.

## First deployment

1. Create the public GitHub repository `cehinds/dungeon-crawler-tactics` and push this project's source to `main`. If GitHub creates an initial README, incorporate that commit before pushing rather than replacing remote history.
2. In the repository, open **Settings → Pages → Build and deployment** and set **Source** to **GitHub Actions**. This prerequisite must be completed before the workflow deploys; the workflow does not enable Pages automatically.
3. Open **Actions → Deploy browser game to GitHub Pages** and choose **Run workflow** on `main`, or push another commit to `main`.
4. Wait for both `build` and `deploy` to succeed. The `github-pages` environment and deployment step show the actual published URL. Open it and verify that camp loads, an encounter starts, and a forecast can be confirmed or cancelled.

GitHub Actions must be enabled for the repository. If environment protection rules require approval, approve the `github-pages` deployment in Actions. A source push alone does not establish a live deployment.

## What the workflow publishes

[The workflow](../.github/workflows/deploy-pages.yml) runs on pushes to `main` and on manual dispatch. It installs .NET 8 and the Python validation dependencies, validates both JSON catalogs, runs the Python validation tests and both C# test harnesses, and checks the shared core's compatibility build. A failed check stops publication.

It then runs:

```sh
dotnet publish Web/DungeonCrawlerTactics.Web.csproj -c Release -o Web/publish
```

Only `Web/publish/wwwroot` becomes the Pages artifact. A `.nojekyll` marker preserves the `_framework` runtime directory. The deployment uses GitHub's Pages artifact and deployment actions, with repository read access confined to the build job and Pages/OIDC permissions confined to deployment.

The published application is the actual shared-C# game presented through Blazor WebAssembly. It runs the same C# game session and rules as the Unity source. It is **not a Unity Web export** and does not require Unity to build this Pages delivery. See [PlayableGame.md](PlayableGame.md) for the separate Unity workflow.

## Updates and troubleshooting

Push source changes to `main`; the workflow rebuilds and replaces the hosted game after validation. Do not upload the repository root or a Unity project directory as the website.

- A Pages configuration error usually means **Settings → Pages → Source** has not been set to **GitHub Actions**.
- A missing `_framework` file means the wrong artifact directory was published; the workflow uses `Web/publish/wwwroot`.
- If a deployment succeeds but the browser shows stale files, reload with the browser cache disabled and inspect the failing request in its developer tools.
- Browser saves are local to the browser and origin. Export a save from the local game before importing it into the hosted game; local saves do not move automatically.

The GitHub Actions run is the authoritative build/deployment result. Local checks do not prove that GitHub Pages has been configured or that the public URL is reachable.
