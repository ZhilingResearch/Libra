import os
import socket
import threading
import json
from time import sleep


class ClientSocket:
    def __init__(self, username):
        host, port = self._get_address()

        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((host, port))
        self.username = username

        # 发送用户名到服务器,客户连接首先发送一个用户名过去
        self.client_socket.send(self.username.encode('utf-8'))

    @staticmethod
    def _get_address():
        path = os.path.join(os.getcwd(), "socket.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return data.get("LocalSocket").get("host"), data.get("LocalSocket").get("port")

    def handle_client(self):
        while True:
            try:
                buffer = b""  # 用于存储接收到的数据片段的缓冲区
                message = ""  # 反序列化后的数据
                while True:
                    data = self.client_socket.recv(1024)
                    if not data:
                        break
                    buffer += data
                    try:
                        message = json.loads(buffer.decode('utf-8'))  # 反序列化 JSON 数据
                        break  # 如果成功反序列化，说明数据接收完整，跳出循环
                    except json.JSONDecodeError:
                        continue  # 如果无法反序列化，继续接收数据
                    except Exception as e:
                        print(f"错误:{e}")

                print(message)
            except Exception as e:
                print(f"Disconnected from server: {e}")
                break

    def send_message(self, message):
        """将消息转换为 JSON 格式并发送"""
        json_message = json.dumps(message)
        self.client_socket.send(json_message.encode('utf-8'))

    def start(self):
        # 启动接收消息的线程
        threading.Thread(target=self.handle_client, daemon=True).start()

        # with open("data.json", "r", encoding="utf-8") as f:
        #     data = json.load(f)
        # self.send_message(data)

def main():
    # 启动客户端
    client_socket = ClientSocket("xg1")
    client_socket.start()

    while True:
        client_socket.send_message({"cc":"wwww1"})
        sleep(0.01)


if __name__ == "__main__":
    main()