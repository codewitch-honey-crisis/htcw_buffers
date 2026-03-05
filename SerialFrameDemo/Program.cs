using Htcw;

using System.Runtime.Versioning;
using System.Threading;
namespace SerialFrameDemo;

[SupportedOSPlatform("windows")]
internal class Program
{
    static bool _connected = false;

    static void Main(string[] args)
    {
        if (args.Length == 0) throw new ArgumentException("A serial port must be specified.");
        _connected = true;
        var session = new EspSerialSession(args[0]);
        Console.Error.WriteLine($"Connected to {args[0]}");
        session.Disconnected += Session_Disconnected;
        session.FrameReceived += Session_FrameReceived;
        session.FrameError += Session_FrameError;
        while (_connected && !Console.KeyAvailable) ;
        Console.Error.WriteLine($"Disconnected");
    }

    private static void Session_Disconnected(object? sender, EventArgs e)
    {
        _connected = false;
        Thread.MemoryBarrier();
    }

    private static void Session_FrameError(object? sender, FrameReceivedEventArgs e)
    {
        Console.Error.WriteLine("Frame error");
    }

    private static void Session_FrameReceived(object? sender, FrameReceivedEventArgs e)
    {
        
    }
}
