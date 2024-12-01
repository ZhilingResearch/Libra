import asyncio
import json
import socket
import threading
import os


class ServerSocket:
    def __init__(self):
        host, port = self._get_address()

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((host, port))
        self.server_socket.listen(5)
        self.server_socket.setblocking(False)

        print(f"Server listening on {(host, port)}")

        self.clients = {}  # 用来存储用户标识和对应的客户端 socket

    @staticmethod
    def _get_address():
        path=os.path.join(os.getcwd(),"socket.json")
        with open(path,"r",encoding="utf-8") as f:
            data=json.load(f)

        return data.get("LocalSocket").get("host"),data.get("LocalSocket").get("port")

    def get_users(self):
        return self.clients.keys()


    async def handle_client(self, client_socket, client_address):
        # 获取事件循环
        loop=asyncio.get_event_loop()
        # 先等待接收字节数据
        username = client_socket.recv(1024).decode('utf-8')
        print(f"用户：{username}，地址：{client_address}连接成功")
        self.clients[username] = client_socket  # 添加用户
        while True:
            try:
                buffer = b""  # 用于存储接收到的数据片段的缓冲区
                message=""  # 反序列化后的数据
                while True:
                    data = await loop.sock_recv(client_socket, 1024)
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
                print(f"收到用户:{username}的消息：{message}")
                self.send(username, {"status": "200"})  # 回复
            except ConnectionResetError:
                print(f"{username} 连接断开")
                del self.clients[username]
                break

    # 发送消息给用户
    def send(self, username, message):
        print("所有用户：",self.get_users())
        """主动向指定用户发送消息"""
        if username in self.clients:
            try:
                self.clients[username].send(json.dumps(message).encode('utf-8'))
            except:
                print(f"回复用户失败")
                del self.clients[username]
        else:
            print(f"没有该用户：{username}")

    # 启动服务
    def start(self):
        async def run():
            loop = asyncio.get_event_loop()
            while True:
                client_socket, client_address = await loop.sock_accept(self.server_socket)
                asyncio.create_task(self.handle_client(client_socket, client_address))

        threading.Thread(target=asyncio.run,args=(run(),),daemon=True).start()

def main():
    server = ServerSocket()
    server.start()

    while True:
        username = input("请输入你要发送给的用户名：")
        content = input("请输入你要发送的内容：")
        server.send_to_user(username, {"content": content})

if __name__ == '__main__':
    main()