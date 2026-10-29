using System.Text.Json;
using DungeonCrawlerTactics;
using Microsoft.AspNetCore.Components.WebAssembly.Hosting;
using Microsoft.JSInterop;

var builder = WebAssemblyHostBuilder.CreateDefault(args);
await builder.Build().RunAsync();

public static class GameBridge
{
    private static readonly JsonSerializerOptions Json = new() { IncludeFields = true, PropertyNameCaseInsensitive = false };
    private static GameSession session;

    [JSInvokable]
    public static string Initialize(string combatJson, string gameJson)
    {
        var combat = JsonSerializer.Deserialize<Content>(combatJson, Json) ?? throw new ArgumentException("Missing combat content.");
        var game = JsonSerializer.Deserialize<GameData>(gameJson, Json) ?? throw new ArgumentException("Missing game content.");
        session = new GameSession(combat, game);
        return Serialize(session.GetView());
    }

    [JSInvokable]
    public static string Dispatch(string commandJson)
    {
        if (session == null) throw new InvalidOperationException("Game not initialized.");
        return Serialize(session.Handle(JsonSerializer.Deserialize<GameCommand>(commandJson, Json) ?? throw new ArgumentException("Missing command.")));
    }

    [JSInvokable]
    public static string DispatchMovement(string commandJson)
    {
        if (session == null) throw new InvalidOperationException("Game not initialized.");
        var command = JsonSerializer.Deserialize<GameCommand>(commandJson, Json) ?? throw new ArgumentException("Missing command.");
        return JsonSerializer.Serialize(session.HandleExplorationMovement(command), Json);
    }

    [JSInvokable]
    public static string GetSave()
    {
        if (session == null) throw new InvalidOperationException("Game not initialized.");
        return JsonSerializer.Serialize(session.ExportSave(), Json);
    }

    [JSInvokable]
    public static string LoadSave(string saveJson)
    {
        if (session == null) throw new InvalidOperationException("Game not initialized.");
        return Serialize(session.ImportSave(JsonSerializer.Deserialize<GameSave>(saveJson, Json) ?? throw new ArgumentException("Empty save file.")));
    }

    private static string Serialize(GameView view) => JsonSerializer.Serialize(view, Json);
}
