using System;
using System.Diagnostics;

class RunAsAdmin
{
    static void Main()
    {
        string filePath = @"C:\path\to\yourfile.bat"; // file to run

        var psi = new ProcessStartInfo(filePath)
        {
            UseShellExecute = true,
            Verb = "runas" // this triggers elevation
        };

        try
        {
            Process.Start(psi);
        }
        catch (Exception ex)
        {
            Console.WriteLine("Failed to launch: " + ex.Message);
        }
    }
}