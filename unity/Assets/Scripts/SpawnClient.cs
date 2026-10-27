using System;
using System.Threading.Tasks;
using GLTFast;
using NativeWebSocket;
using UnityEngine;

/// <summary>Pythonサーバーから受け取った配置コマンドをUnityで実行する。</summary>
public class SpawnClient : MonoBehaviour
{
    [Serializable]
    private class Command
    {
        public string command;
        public string id;
        public string model_path;
        public float[] position;
        public float[] rotation;
        public float[] scale;
        public float target_height_m;
        public float mass;
    }

    [Serializable]
    private class Ack
    {
        public string type = "ack";
        public string id;
        public bool ok;
        public string message;
    }

    private WebSocket ws;
    private bool stopping;

    private void Start()
    {
        Application.runInBackground = true;
        _ = ConnectionLoop();
    }

    private async Task ConnectionLoop()
    {
        while (!stopping)
        {
            var closed = new TaskCompletionSource<bool>();
            try
            {
                ws = new WebSocket("ws://localhost:8765");
                ws.OnOpen += () => Debug.Log("Pythonサーバーに接続しました");
                ws.OnError += error => Debug.LogWarning($"WebSocketエラー: {error}");
                ws.OnClose += code => closed.TrySetResult(true);
                ws.OnMessage += bytes => HandleMessage(System.Text.Encoding.UTF8.GetString(bytes));

                await ws.Connect();
                // NativeWebSocketのConnectは接続確立時に完了するため、切断通知まで待つ。
                if (ws.State == WebSocketState.Open)
                    await closed.Task;
            }
            catch (Exception exception)
            {
                Debug.LogWarning($"WebSocket接続に失敗しました: {exception.Message}");
            }

            if (stopping)
                break;

            try
            {
                await Task.Delay(2000);
            }
            catch (Exception exception)
            {
                Debug.LogWarning($"再接続待機に失敗しました: {exception.Message}");
            }
        }
    }

    private void HandleMessage(string json)
    {
        try
        {
            var command = JsonUtility.FromJson<Command>(json);
            if (command != null && command.command == "spawn_item")
                _ = SpawnItem(command);
        }
        catch (Exception exception)
        {
            Debug.LogWarning($"受信メッセージの処理に失敗しました: {exception.Message}");
        }
    }

    private async Task SpawnItem(Command command)
    {
        var gltf = new GltfImport();
        GameObject root = null;
        try
        {
            if (!await gltf.Load(new Uri(command.model_path).AbsoluteUri))
            {
                SendAck(command.id, false, "load failed");
                return;
            }

            root = new GameObject($"Item_{command.id}");
            if (!await gltf.InstantiateMainSceneAsync(root.transform))
            {
                Destroy(root);
                SendAck(command.id, false, "instantiate failed");
                return;
            }

            // 子Renderer全体の高さを基準に縮尺を調整し、指定スケールを掛ける。
            var renderers = root.GetComponentsInChildren<Renderer>();
            if (renderers.Length > 0)
            {
                var bounds = renderers[0].bounds;
                for (var i = 1; i < renderers.Length; i++)
                    bounds.Encapsulate(renderers[i].bounds);

                if (command.target_height_m > 0f && bounds.size.y > 0f)
                {
                    var factor = command.target_height_m / bounds.size.y;
                    root.transform.localScale = Vector3.one * factor;
                }
            }

            var requestedScale = ToVector(command.scale, Vector3.one);
            root.transform.localScale = Vector3.Scale(root.transform.localScale, requestedScale);

            // スケール適用後のバウンズをルートローカル座標のBoxColliderに変換する。
            renderers = root.GetComponentsInChildren<Renderer>();
            if (renderers.Length > 0)
            {
                var bounds = renderers[0].bounds;
                for (var i = 1; i < renderers.Length; i++)
                    bounds.Encapsulate(renderers[i].bounds);

                var collider = root.AddComponent<BoxCollider>();
                collider.center = root.transform.InverseTransformPoint(bounds.center);
                var s = root.transform.localScale;
                collider.size = new Vector3(
                    bounds.size.x / s.x,
                    bounds.size.y / s.y,
                    bounds.size.z / s.z);
            }
            else
            {
                root.AddComponent<BoxCollider>();
            }

            root.transform.position = ToVector(command.position, Vector3.zero);
            root.transform.rotation = Quaternion.Euler(ToVector(command.rotation, Vector3.zero));

            var body = root.AddComponent<Rigidbody>();
            body.mass = command.mass;
            SendAck(command.id, true, "spawned");
        }
        catch (Exception exception)
        {
            Debug.LogWarning($"アイテム配置に失敗しました: {exception.Message}");
            if (root != null)
                Destroy(root);
            SendAck(command.id, false, "spawn failed");
        }
    }

    private static Vector3 ToVector(float[] values, Vector3 fallback)
    {
        return values != null && values.Length >= 3
            ? new Vector3(values[0], values[1], values[2])
            : fallback;
    }

    private void SendAck(string id, bool ok, string message)
    {
        if (ws != null && ws.State == WebSocketState.Open)
        {
            var ack = new Ack { id = id, ok = ok, message = message };
            _ = ws.SendText(JsonUtility.ToJson(ack));
        }
    }

    private void Update()
    {
#if !UNITY_WEBGL || UNITY_EDITOR
        ws?.DispatchMessageQueue();
#endif
    }

    private void OnDestroy()
    {
        stopping = true;
        if (ws != null)
            _ = ws.Close();
    }
}
