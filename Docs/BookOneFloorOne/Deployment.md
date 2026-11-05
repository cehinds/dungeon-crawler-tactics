# Publishing a tested dev revision

The existing Pages workflow accepts an explicit `pages-dev-*` tag, as well as main-branch pushes and manual dispatch. After the final dev revision passes review and browser checks, push one tag pointing to that exact commit:

```sh
git tag pages-dev-YYYYMMDD-HHMMSS <tested-dev-commit>
git push origin refs/tags/pages-dev-YYYYMMDD-HHMMSS
```

The tag runs the complete existing validation, pinned-art restoration, browser publish and Pages deployment pipeline. It leaves `main` unchanged and replaces the current Pages site only after those jobs succeed. Ordinary dev pushes do not deploy.

The intended playable entry is <https://cehinds.github.io/dungeon-crawler-tactics/index.html?book1=start>. A pushed tag or successful local build does not establish a live deployment; verify the workflow deployment and the served game before reporting it live.

Pages preparation removes the authoring-only whole-object pack. Runtime component URLs must therefore use their immutable published art revision, while the existing ground kit remains in the compact game artifact.
