using System;
using System.Diagnostics;
using System.IO;
using System.Text;

internal static class Program
{
    private static int Main(string[] args)
    {
        string root = AppDomain.CurrentDomain.BaseDirectory;
        string script = Path.Combine(root, "bg2hd", "tools", "Install-BG2HD.ps1");
        if (!File.Exists(script))
        {
            Console.Error.WriteLine("BG2HD bootstrap script not found: " + script);
            return 2;
        }

        string powershell = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.System), "WindowsPowerShell", "v1.0", "powershell.exe");
        if (!File.Exists(powershell))
        {
            Console.Error.WriteLine("Windows PowerShell was not found: " + powershell);
            return 3;
        }

        string[] effectiveArgs = args;
        if (args.Length == 0 && string.Equals(Path.GetFileNameWithoutExtension(AppDomain.CurrentDomain.FriendlyName), "Uninstall-BG2HD", StringComparison.OrdinalIgnoreCase))
        {
            effectiveArgs = new string[] { "-Action", "Uninstall" };
        }

        ProcessStartInfo startInfo = new ProcessStartInfo();
        startInfo.FileName = powershell;
        // The default path is started from Explorer. Keep a visible console alive so
        // consent prompts and failures cannot disappear before the player can read them.
        string keepConsoleOpen = args.Length == 0 ? "-NoExit " : "";
        startInfo.Arguments = "-NoLogo -NoProfile " + keepConsoleOpen + "-ExecutionPolicy Bypass -File " + Quote(script) + JoinArguments(effectiveArgs);
        startInfo.WorkingDirectory = root;
        startInfo.UseShellExecute = true;

        using (Process child = Process.Start(startInfo))
        {
            child.WaitForExit();
            return child.ExitCode;
        }
    }

    private static string JoinArguments(string[] args)
    {
        StringBuilder commandLine = new StringBuilder();
        foreach (string arg in args)
        {
            commandLine.Append(' ');
            commandLine.Append(Quote(arg));
        }
        return commandLine.ToString();
    }

    // Windows command-line quoting compatible with CommandLineToArgvW.
    private static string Quote(string value)
    {
        if (value.Length == 0)
        {
            return "\"\"";
        }

        bool needsQuotes = false;
        foreach (char character in value)
        {
            if (char.IsWhiteSpace(character) || character == '"')
            {
                needsQuotes = true;
                break;
            }
        }
        if (!needsQuotes)
        {
            return value;
        }

        StringBuilder quoted = new StringBuilder();
        quoted.Append('"');
        int slashCount = 0;
        foreach (char character in value)
        {
            if (character == '\\')
            {
                slashCount++;
                continue;
            }
            if (character == '"')
            {
                quoted.Append('\\', slashCount * 2 + 1);
                quoted.Append(character);
                slashCount = 0;
                continue;
            }
            quoted.Append('\\', slashCount);
            slashCount = 0;
            quoted.Append(character);
        }
        quoted.Append('\\', slashCount * 2);
        quoted.Append('"');
        return quoted.ToString();
    }
}
