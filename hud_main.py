import asyncio
import base64
import json
import math
import os
import re
import socket
import sys
import threading
import time
import traceback
from pprint import pprint
from time import sleep
import cv2 as cv
import numpy as np
import redis
import requests
from PySide6.QtCore import QObject, Signal, QTimer, QPointF
from PySide6.QtWidgets import QApplication, QWidget, QLabel, QGraphicsEffect, QGraphicsOpacityEffect
from PySide6.QtGui import QFont, QFontDatabase, Qt, QPixmap, QImage, QPainter, QColor

def analyze_socket_dict(data):
    # 使用正则表达式按照}{进行分割，会得到类似 ["{"name": "ele100,ele75,ele50,ele25", "action": "show_label,hide_label,hide_label,hide_label"}", '{"image": "0", "name": "speed", "action": "update_label"}'] 这样的结果（字节串形式）
    parts = re.split(b'}(?={)', data)

    # 处理每个部分，将其转换为字典并添加到结果列表中
    result = []
    for part in parts:
        part_str = part.decode('utf-8').strip().rstrip('}').lstrip('{')  # 去除首尾多余的大括号并转换为字符串
        if part_str:  # 避免空字符串情况（如果存在）
            dict_obj = json.loads('{' + part_str + '}')  # 构造合法JSON字符串并解析为字典
            result.append(dict_obj)
    return result


class ServerSocket:
    def __init__(self, main_window):
        self.main_window = main_window
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
        path=os.path.join(os.getcwd(),"config/socket.json")
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
                response = json.dumps({"status": f"200"})
                while True:
                    data = await loop.sock_recv(client_socket, 1024)
                    if not data:
                        break
                    buffer += data
                    if b"}" in buffer:
                        messages_list=analyze_socket_dict(buffer)
                        for message in messages_list:
                            actions_list = message.get("action").split(",")  # 操作
                            names_list = message.get("name").split(",")
                            for index, action in enumerate(actions_list):
                                name = names_list[index]
                                message["name"] = name  # 更新name遍历
                                message["action"] = action  # 更新action遍历
                                # 创建
                                if action == "create_label":
                                    # 如果创建的已经存在，返回存在
                                    if name in self.main_window.dstc.data:
                                        response = json.dumps({"status": f"{name} already exist"})
                                    else:
                                        self.main_window.create_label_signal.emit(message)
                                        response = json.dumps({"status": f"{message} created"})
                                # 更新,不存在自动创建，可能由于emit问题，创建未完成就更新导致看不到，不影响后续更新
                                elif action == "update_label":
                                    if name not in self.main_window.dstc.data:
                                        self.main_window.create_label_signal.emit(message)
                                        sleep(0.05)  # 不存在新创建的等待创建成功
                                    else:
                                        self.main_window.update_label_signal.emit(message)
                                        response = json.dumps({"status": f"{message.get('name')} updated"})
                                # 删除
                                elif action == "delete_label":
                                    if name in self.main_window.dstc.data:
                                        self.main_window.delete_label_signal.emit(message.get("name"))
                                        response = json.dumps({"status": f"{name} deleted"})
                                    else:
                                        response = json.dumps({"status": f"{name} no exist"})
                                # 查询
                                elif action == "labels":
                                    response = json.dumps({"keys": ",".join(self.main_window.dstc.data.keys())})
                                # 显示
                                elif action == "show_label":
                                    self.main_window.show_label_signal.emit(message.get("name"))
                                    response = json.dumps({"status": f"{name} shown"})
                                # 隐藏
                                elif action == "hide_label":
                                    self.main_window.hide_label_signal.emit(name)
                                    response = json.dumps({"status": f"{name} hidden"})
                                # 视频
                                elif action == "video_label":
                                    print("正在播放视频")
                                    if message.get("name") in self.main_window.dstc.data:
                                        response = json.dumps({"status": f"{message.get('name')} already shown"})
                                    else:
                                        Video(self.main_window, message)

                                        message["image"] = ""  # 确保路径不会被显示出来
                                        self.main_window.create_label_signal.emit(message)

                                        response = json.dumps({"status": f"{message.get('name')} play successfully"})
                                # 无该操作
                                else:
                                    response = json.dumps({"status": f"400"})

                            # self.send(username, response)
                        buffer=b""
                    # try:
                    #     message = json.loads(buffer.decode('utf-8'))  # 反序列化 JSON 数据
                    #     break  # 如果成功反序列化，说明数据接收完整，跳出循环
                    # except json.JSONDecodeError:
                    #     continue  # 如果无法反序列化，继续接收数据
                    # except Exception as e:
                    #     print(f"错误:{e}")
                # print(f"收到用户:{username}的消息：{message}")  # 后面值被更改了

            except ConnectionResetError:
                print(f"{username} 连接断开")
                del self.clients[username]
                break
            except Exception as e:
                print(f"强制断开错误~{e}")
                del self.clients[username]

    # 发送消息给用户
    def send(self, username, message):
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

# 遍历列表中的每个字典，查找包含 "name": "bgImage" 的字典
def find_dicts_with_name(data_list, stats, name=None):
        """
        字典列表，返回字典里含有stats属性的字典，如果传了名字，就必须是属性的值是name的
        :param data_list: 字典列表
        :param stats: 属性
        :param name: 值
        :return:
        """
        results = []
        for item in data_list:
            if isinstance(item, dict):
                if name:
                    if item.get(stats) == name:
                        results.append(item)
                    else:
                        # 如果当前字典不符合条件，则查找其嵌套的字典
                        for value in item.values():
                            if isinstance(value, dict):
                                results.extend(find_dicts_with_name([value], name))
                else:
                    if item.get(stats):
                        results.append(item)
                    else:
                        # 如果当前字典不符合条件，则查找其嵌套的字典
                        for value in item.values():
                            if isinstance(value, dict):
                                results.extend(find_dicts_with_name([value], name))
        return results
# 动态数据缓存
class DynamicStateDataCace:
    data = {}


class CustomTextLabel(QLabel):
    def __init__(self, name="", parent=None):
        super().__init__(parent)
        self.styles = {
            "name": name,
            "image": "",
            "x": 0,
            "y": 0,
            "width": 100,
            "height": 100,
            "font_size": 25,
            "color": "rgba(255, 0, 0, 1)",
            "font_family": "Arial",
            "font_file": "TTF/微软雅黑.ttf",
            "bold": False,
            "italic": False,
            "underline": False,
            "strikethrough": False,
            "show": True,
            # "background-color": "green",  #
            "opacity": 1
        }
        # 设置文本居中
        self.setAlignment(Qt.AlignCenter)
        self.setScaledContents(True)  # 设置图片为拉伸
        self.apply_styles(self.styles)
        self.show()

    def set_image_transparency(self, value):
        opacity_effect = QGraphicsOpacityEffect()
        # 设置透明度，取值范围是0.0（完全透明）到1.0（完全不透明）
        opacity_effect.setOpacity(value)
        self.setGraphicsEffect(opacity_effect)
        self.graphicsEffect()

    def apply_styles(self, new_styles):
        self.styles.update(new_styles)
        image = self.styles.get("image")
        if image is None:
            return
        # 设置位置
        self.setGeometry(
            self.styles.get("x"),
            self.styles.get("y"),
            self.styles.get("width"),
            self.styles.get("height")
        )
        # 是不是np.ndarray格式
        if type(image)==np.ndarray:
            image=np.array(image)
            pixmap = self._numpy_array_to_pixmap(image)
            self.set_image_transparency(self.styles.get("opacity", 1))
            self.setPixmap(pixmap)

        # base64格式图片
        elif image.startswith("data:image"):
            image_data = base64.b64decode(image.split(",")[1])
            pixmap = QPixmap()
            pixmap.loadFromData(image_data)
            self.set_image_transparency(self.styles.get("opacity", 1))
            self.setPixmap(pixmap)
        # 网络图片
        elif image.startswith("http") or image.startswith("https"):
            response = requests.get(image)
            if response.status_code == 200:
                image_data = response.content
                pixmap = QPixmap.fromImage(QImage.fromData(image_data))
                self.set_image_transparency(self.styles.get("opacity", 1))
                self.setPixmap(pixmap)
        # 本地图片
        elif image.endswith((".png", ".jpg", ".jpeg", ".bmp", ".tif", ".svg", ".pcd", ".ai", ".webp")):
            pixmap = QPixmap(image)
            # pixmap = self._set_pixmap_transparency(pixmap, self.styles.get("opacity", 1))
            self.set_image_transparency(self.styles.get("opacity", 1))
            self.setPixmap(pixmap)
        # 文本
        else:
            # 重新计算字体大小
            font_size=self.adjust_font_size()
            # 设置样式
            style_string = (
                f"font-size: {int(font_size)}px;"
                f"color: {self.styles.get('color', 'rgb(255, 0, 0, 1)')};"
                f"background-color: {self.styles.get('background-color', 'None')};"
            )
            self.setStyleSheet(style_string)

            # 设置字体
            font_family = self.styles.get("font_family")
            font_file = self.styles.get("font_file")
            if font_file:
                font_id = QFontDatabase.addApplicationFont(font_file)
                if font_id!= -1:
                    font_families = QFontDatabase.applicationFontFamilies(font_id)
                    if font_families:
                        font_family = font_families[0]
            font = QFont(font_family)
            # font.setStretch(100)
            font.setBold(self.styles.get("bold", False))  # 粗体
            font.setItalic(self.styles.get("italic", False))  # 斜体
            font.setUnderline(self.styles.get("underline", False))  # 下划线
            font.setStrikeOut(self.styles.get("strikethrough", False))  # 删除线
            self.setFont(font)
            # 设置内容
            self.setText(self.styles.get("image", ""))

    def _numpy_array_to_pixmap(self, image_array):
        height, width, channels = image_array.shape
        bytes_per_line = channels * width

        # 如果图像是 BGR 格式，转换为 RGB
        if channels == 3 and image_array.shape[2] == 3:
            image_array = cv.cvtColor(image_array, cv.COLOR_BGR2RGB)

        # 确保图像数据类型是 np.uint8
        if image_array.dtype != np.uint8:
            image_array = image_array.astype(np.uint8)

        q_image = QImage(image_array.data, width, height, bytes_per_line, QImage.Format_RGB888)
        return QPixmap.fromImage(q_image)

    def adjust_font_size(self):
        # 获取当前标签的宽度和高度
        width = self.width()
        height = self.height()
        # 初始字体大小
        font_size = width/max(len(self.styles.get("image")), 1)
        font_size=min((height, font_size))*1.2
        return font_size


    # pixmap格式图片修改透明度
    def _set_pixmap_transparency(self, pixmap, transparency_value):
        new_pixmap = QPixmap(pixmap.size())
        new_pixmap.fill(Qt.transparent)
        painter = QPainter(new_pixmap)
        painter.setOpacity(transparency_value)
        painter.drawPixmap(0, 0, pixmap)
        painter.end()
        return new_pixmap

class MainWindow(QWidget):
    create_label_signal = Signal(dict)
    update_label_signal = Signal(dict)
    delete_label_signal = Signal(str)
    show_label_signal = Signal(str)
    hide_label_signal = Signal(str)
    clear_label_signal = Signal()

    def __init__(self, dstc: DynamicStateDataCace, show_pos_number=0):
        super().__init__()
        self.dstc = dstc
        self.show_pos_number = show_pos_number  # 显示在第几块屏幕

        self.width, self.height = self._init_screen()  # 最大化屏幕和窗口设置

        self.create_label_signal.connect(self.create_label)  # 创建
        self.update_label_signal.connect(self.update_label)  # 更新
        self.delete_label_signal.connect(self.delete_label)  # 删除
        self.show_label_signal.connect(self.show_label)  # 显示
        self.hide_label_signal.connect(self.hide_label)  # 隐藏
        self.clear_label_signal.connect(self.clear_label)  # 清空
        # 加载本地hud
        self.load_data()
        self.show()

    def _init_screen(self):
        # 设置窗口为无边框和透明
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.screen_object = QApplication.screens()[self.show_pos_number]
        pos_size = self.screen_object.geometry()

        # 设置窗口大小
        self.resize(pos_size.width(), pos_size.height())

        # 移动屏幕(到第几块屏幕)
        window_rect = self.frameGeometry()
        window_rect.moveCenter(pos_size.center())
        self.move(window_rect.topLeft())
        return pos_size.width(), pos_size.height()
    def load_data(self):
        with open("config/data.json", "r") as f:
            message = json.load(f)
        # print(message)
        canvas_width, canvas_height = message.get("objects")[1].get("width") * message.get("objects")[1].get("scaleX"), message.get("objects")[1].get("height") * \
                                      message.get("objects")[1].get("scaleY")
        images = find_dicts_with_name(message.get("objects"), "name", "image")
        for i in images:
            data = {
                "image": i.get("src"),
                "x": self.width * i.get("percentageX"),
                "y": self.height * i.get("percentageY"),
                "width": i.get("width") * i.get("scaleX") * (self.width / canvas_width),
                "height": i.get("height") * i.get("scaleY") * (self.height / canvas_height),
                "opacity": i.get("opacity"),
                "name": i.get("customTypeName")
            }
            self.create_label(data)
        texts = find_dicts_with_name(message.get("objects"), "type", "textbox")
        for i in texts:
            data = {
                "image": i.get("text"),
                "color": i.get("fill"),
                "x": self.width * i.get("percentageX"),
                "y": self.height * i.get("percentageY"),
                "width": i.get("width") * i.get("scaleX") * (self.width / canvas_width),
                "height": i.get("fontSize") * i.get("scaleY") * (self.height / canvas_height),
                "opacity": i.get("opacity"),
                "font_file": f'TTF/{i.get("fontFamily")}.ttf',  # 初始时没有 TTF 字体文件
                "name": i.get("customTypeName")
            }
            self.create_label(data)
    def show_label(self, name):
        if self.dstc.data.get(name):
            self.dstc.data.get(name).get("label").show()
    def hide_label(self, name):
        if self.dstc.data.get(name):
            self.dstc.data.get(name).get("label").hide()
    def delete_label(self, name):
        if self.dstc.data.get(name):
            self.dstc.data[name].get("label").deleteLater()
            del self.dstc.data[name]


    def create_label(self, data):
        names=data.get("name")
        for name in names.split(","):
            if name!="" and name in self.dstc.data:
                continue
            label = CustomTextLabel(name, self)
            self.dstc.data[name] = label.styles  # 继承原有label属性
            self.dstc.data[name].update(data)  # 更新属性
            self.dstc.data[name]["label"] = label  # 添加label
            self.update_label_signal.emit(self.dstc.data[name])  # 更新画面

    def update_label(self, data):
        if self.dstc.data.get(data["name"]):
            self.dstc.data.get(data["name"]).update(data)
            self.dstc.data.get(data["name"])["label"].apply_styles(data)

    def clear_label(self):
        labels = self.findChildren(QLabel)
        for label in labels:
            label.deleteLater()
        self.dstc.data.clear()

class Video:
    def __init__(self,main_window: MainWindow, partial_data):
        self.main_window = main_window

        self.video_play(partial_data)

    def video_play(self, partial_data):
        data={}
        def play():
            video_path = partial_data.get("image")
            data["name"]=partial_data.get("name")
            current_video = cv.VideoCapture(video_path)
            print(video_path)
            # fps = max(int(1000 / current_video.get(cv.CAP_PROP_FPS)), 1)
            fps=1
            while True:
                # 读取视频
                ret,frame = current_video.read()
                # print(ret)
                # 循环播放
                if not ret:
                    current_video.set(cv.CAP_PROP_POS_FRAMES, 0)
                    continue
                # 更新界面
                data["image"]=frame
                self.main_window.update_label_signal.emit(data)
                # 木有改控件，被删除了
                if partial_data.get("name") not in self.main_window.dstc.data:
                    print("Unmodified control")
                    break
                sleep(0.05)

        threading.Thread(target=play,daemon=True).start()

    def _numpy_array_to_pixmap(self, image_array):
        height, width, channels = image_array.shape
        bytes_per_line = channels * width

        # 如果图像是 BGR 格式，转换为 RGB
        if channels == 3 and image_array.shape[2] == 3:
            image_array = cv.cvtColor(image_array, cv.COLOR_BGR2RGB)

        # 确保图像数据类型是 np.uint8
        if image_array.dtype != np.uint8:
            image_array = image_array.astype(np.uint8)

        q_image = QImage(image_array.data, width, height, bytes_per_line, QImage.Format_RGB888)
        return QPixmap.fromImage(q_image)

# redis订阅
class SubRedis(QObject):
    def __init__(self, main_window: MainWindow, server_socket: ServerSocket):
        super().__init__()
        self.main_window = main_window  # 窗口类
        self.server_socket = server_socket  # 服务器类
        self.p = None  # redis连接对象
        self._connect_redis()  # 连接redis
        self.listen()

    def _connect_redis(self):  # 读取本地配置文件，链接redis
        with open('config/socket.json', 'r') as json_file:
            config_data = json.load(json_file)
        host = config_data["server"]["host"]
        port = config_data["server"]["port"]
        password = config_data["server"]["password"]
        channel_name = config_data["server"]["channel_name"]
        r = redis.StrictRedis(host=host, port=port, password=password, decode_responses=True)
        # 创建一个 Pub/Sub 对象
        self.p = r.pubsub()
        self.p.subscribe(channel_name)

    def listen(self):  # 监听
        def l():
            for message in self.p.listen():
                if message['type'] == 'message':
                    message = eval(message['data'].replace("true", "True").replace("false", "False").replace("null", "None"))
                    # 传输是否绘制框的
                    self.server_socket.send("user1", message)

                    # 更新hud的
                    print("hud界面更新")
                    self.main_window.clear_label_signal.emit()  # 清空画布
                    canvas_width, canvas_height = message.get("objects")[1].get("width") * message.get("objects")[1].get("scaleX"), message.get("objects")[1].get("height") * \
                                                  message.get("objects")[1].get("scaleY")
                    images = find_dicts_with_name(message.get("objects"), "type", "image")
                    for i in images:
                        data = {
                            "image": i.get("src"),
                            "x": self.main_window.width * i.get("percentageX"),
                            "y": self.main_window.height * i.get("percentageY"),
                            "width": i.get("width") * i.get("scaleX") * (self.main_window.width / canvas_width),
                            "height": i.get("height") * i.get("scaleY") * (self.main_window.height / canvas_height),
                            "opacity": i.get("opacity"),
                            "name": i.get("customTypeName")
                        }
                        print(canvas_width,canvas_height)
                        self.main_window.create_label_signal.emit(data)

                    texts = find_dicts_with_name(message.get("objects"), "type", "textbox")
                    for i in texts:
                        data = {
                            "image": i.get("text"),
                            "color": i.get("fill"),
                            "x": self.main_window.width * i.get("percentageX"),
                            "y": self.main_window.height * i.get("percentageY"),
                            "width": i.get("width") * i.get("scaleX") * (self.main_window.width / canvas_width),
                            "height": i.get("fontSize") * i.get("scaleY") * (self.main_window.height / canvas_height),
                            "opacity": i.get("opacity"),
                            "font_file": f'TTF/{i.get("fontFamily")}.ttf',  # 初始时没有 TTF 字体文件
                            "name": i.get("customTypeName")
                        }

                        self.main_window.create_label_signal.emit(data)
                    with open("config/data.json", "w") as f:
                        f.write(json.dumps(message, indent=4))

        threading.Thread(target=l, daemon=True).start()

def main():
    dstc = DynamicStateDataCace()

    app = QApplication(sys.argv)
    main_window = MainWindow(dstc)

    # 启动本地服务器
    server_socket=ServerSocket(main_window)
    server_socket.start()

    # hud网页
    # SubRedis(main_window, server_socket)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()