using DccRebuild;
using Microsoft.AspNetCore.Components.WebAssembly.Hosting;
using Microsoft.JSInterop;
var builder=WebAssemblyHostBuilder.CreateDefault(args);
await builder.Build().RunAsync();
public static class GameBridge {
 static Game game;
 [JSInvokable] public static string Initialize(string contentJson,int seed=1){game=new Game(contentJson,seed);return Codec.Write(game.GetView());}
 [JSInvokable] public static string Dispatch(string commandJson){try{return Codec.Write(game.Handle(Codec.Read<Command>(commandJson)));}catch{return Codec.Write(game.GetView());}}
 [JSInvokable] public static string GetSave()=>game.GetSave();
 [JSInvokable] public static string LoadSave(string saveJson)=>Codec.Write(game.LoadSave(saveJson));
}
