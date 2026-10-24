using System;
using System.IO.Pipes;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

public static class RouterPipeHttp {
    public static string Send(string pipeName, string method, string route, string body, string secret, int seconds) {
        return SendAsync(pipeName, method, route, body, secret, seconds).GetAwaiter().GetResult();
    }
    private static async Task<string> SendAsync(string pipeName, string method, string route, string body, string secret, int seconds) {
        using var handler = new SocketsHttpHandler { UseProxy = false };
        handler.ConnectCallback = async (context, cancellation) => {
            var pipe = new NamedPipeClientStream(".", pipeName, PipeDirection.InOut, PipeOptions.Asynchronous);
            try { await pipe.ConnectAsync(cancellation); return pipe; }
            catch { pipe.Dispose(); throw; }
        };
        using var client = new HttpClient(handler) { Timeout = TimeSpan.FromSeconds(seconds) };
        using var request = new HttpRequestMessage(new HttpMethod(method), "http://localhost" + route);
        if (!string.IsNullOrEmpty(secret)) request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", secret);
        if (body != null) request.Content = new StringContent(body, Encoding.UTF8, "application/json");
        using var response = await client.SendAsync(request);
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadAsStringAsync();
    }
}
