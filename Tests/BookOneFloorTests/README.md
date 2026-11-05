# Book 1 continuous-floor integration checks

From the repository root, with restored art assets, Node.js and .NET 8:

```sh
node Tools/test_book_one_entry.mjs
node Tools/test_exploration_controls.mjs
node Tools/test_book_one_playable_floor.mjs --fixture
dotnet run --project Tests/BookOneFloorTests/BookOneFloorTests.csproj -- /tmp/book-one-floor-plan.json
```

The Node test generates three seeds and checks exact packet reproducibility, actor and objective connectivity after whole-object collision, valid cache item references, group ownership and hostile-free safe rooms. `--fixture` writes the final realized floor for the C# test.

The C# test imports that exact 40×32 floor into `GameSession`, checks the canonical collision, saves and reloads it, tests a locked exit while standing directly at it, rejects corrupt references transactionally, walks the real corridor into the first encounter, wins that encounter through existing movement and ability commands, chooses a reward, and reloads the party and floor after returning to exploration.

The entry tests also check fresh starts, exact resume decisions, seed validation, safe-room transitions, stable-ID mode detection, and confirmation before replacing unrelated or malformed saves. The held-control tests cover cardinal input sequencing.

These checks exercise the actual shared C# engine. They do not establish a browser WASM build, browser handoff, Unity Editor execution, victory in all five encounters, or complete-floor victory. The browser handoff separately verifies the map and entire floor plan before replacing local storage.
