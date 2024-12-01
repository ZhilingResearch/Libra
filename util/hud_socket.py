import json
import os
import socket


class SocketClient:
    def __init__(self):
        self.init_client()
        self.is_connected = True

    def init_client(self):
        # hud_socket_path = os.path.join(os.getcwd(), 'config/hud_socket.json')
        # print(hud_socket_path)
        hud_socket_path = os.path.join(os.getcwd(), "config/hud_socket.json")
        with open(hud_socket_path, 'r') as f:
            socket_data = json.load(f)
        host = socket_data.get("socket").get('host')
        port = socket_data.get("socket").get('port')
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((host, port))

    def send_image_text(self, d):
        if not self.is_connected:
            return
        update_data = json.dumps(d)
        try:
            self.client_socket.send(update_data.encode())
            response = self.client_socket.recv(1024).decode()
            response = response.strip('"\\')  # 去除两端引号
            response = response.replace("\\", "")  # 去除\
            return response
            # print(f"服务器响应：{response}")
        except socket.error:
            self.is_connected = False

    def disconnect(self):
        if self.is_connected:
            self.client_socket.close()
            self.is_connected = False


if __name__ == '__main__':
    socket_client = SocketClient()
    i = 100

    # sleep(3)
    # socket_client.send({
    #     "action": "labels"
    # })

    # "name"与"dynamic"必须同时传
    socket_client.send_image_text({
        "image": r"60",  # 文本，本地图片，网络图片，base64
        'name': "img3",
        "action": "create_label",  # update,delete,create,show,hide
        'x': 3000,
        'y': 900,
        'width': 300,
        'height': 300,
        "opacity": 1,
        "color": (255, 0, 0),
        "dynamic": True
    })
