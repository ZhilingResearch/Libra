import json
import socket
import time
from util.disposition import *
import math
import os
import random
import threading
import traceback
from time import sleep
import carla
import numpy as np
from agents.tools.misc import get_speed
from util.vehicle_method import destroy_all_vehicles_traffics, VehicleControl, Window
from util.steering import SteeringWheel


class HudShow:
    # 车灯映射
    light_actions = {
        0: (carla.VehicleLightState.NONE, "hide_label,hide_label"),
        1: (carla.VehicleLightState.LowBeam, "hide_label,show_label"),
        2: (carla.VehicleLightState.HighBeam, "show_label,hide_label")
    }

    # 交通信号action映射
    traffic_actions = {
        carla.TrafficLightState.Red: "show_label,hide_label,hide_label",
        carla.TrafficLightState.Yellow: "hide_label,show_label,hide_label",
        carla.TrafficLightState.Green: "hide_label,hide_label,show_label",
    }

    # 自动驾驶信号映射
    auto_actions = {
        True: "show_label,hide_label,hide_label,show_label",
        False: "hide_label,show_label,show_label,hide_label"
    }

    # 车辆可行驶里程km,即电量映射
    total__mileage = 1  # 满电时可行驶的里程
    remaining_mileage = total__mileage  # 剩余里程
    now_time = time.time()  # 当前时间，记得创建车子时更新
    now_pos = carla.Location()  # 当前位置，下方先更新一下车子坐标

    # 目的地坐标
    dt_location = carla.Location(x=-57, y=137.80, z=0)  # 目的地到达时间

    def __init__(self):
        pass

    @classmethod
    def get_power_from_mileage(cls):
        mileage_ranges = {
            (cls.total__mileage / 4 * 3, float('inf')): "show_label,hide_label,hide_label,hide_label",
            (cls.total__mileage / 2, cls.total__mileage / 4 * 3): "hide_label,show_label,hide_label,hide_label",
            (cls.total__mileage / 4, cls.total__mileage / 2): "hide_label,hide_label,show_label,hide_label",
            (0, cls.total__mileage / 4): "hide_label,hide_label,hide_label,show_label"
        }

        for range_start, range_end in mileage_ranges.keys():
            if range_start <= cls.remaining_mileage < range_end:
                return mileage_ranges[(range_start, range_end)]
        return "hide_label,hide_label,hide_label,hide_label"

class ArHudShow:
    # 风险预警显示
    car_bounding_box = False  # 车子框
    route = False  # 路线
    stop_sign = False  # stop标志牌
    object_bounding_box = False  # 物体框

    # 风险图标初始化
    danger_opacity = 0  # 风险的透明度变量
    danger_flag = True  # 是否绘制
    danger_direction=True  # 透明度值的方向0-1
    danger_speed = 20  # 风险变化的速度变量
    red_alert_image = pygame.image.load("images/red_alert.png")  # 加载风险的图标
    red_alert_image = pygame.transform.scale(red_alert_image, (500, 500))  # 图标大小

# 客户端
class ClientSocket:
    def __init__(self, username):
        host, port = self._get_address()

        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((host, port))

        # 发送用户名到服务器,客户连接首先发送一个用户名过去
        self.client_socket.send(username.encode('utf-8'))

        self.content={}  # 用于存储服务器发送过来的内容

    @staticmethod
    def _get_address():
        path = os.path.join(os.getcwd(), "config/socket.json")
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
                ArHudShow.car_bounding_box=message.get("前车风险提示")
                ArHudShow.route=message.get("实时路线导航")
                ArHudShow.stop_sign=message.get("标志牌增强显示")
                ArHudShow.object_bounding_box=message.get("风险物体提示")
                print(f"接收到的服务器内容:{message}")
            except Exception as e:
                print(f"Disconnected from server: {e}")
                break

    def send(self, message):
        """将消息转换为 JSON 格式并发送"""
        json_message = json.dumps(message)
        self.client_socket.send(json_message.encode('utf-8'))

    def start(self):
        # 启动接收消息的线程
        threading.Thread(target=self.handle_client, daemon=True).start()

        # with open("data.json", "r", encoding="utf-8") as f:
        #     data = json.load(f)
        # self.send_message(data)
    def disconnect(self):
        self.client_socket.close()

# 绘制竖线
class ActorDrawVerticalLine:

    def __init__(self, main_car):
        self.main_car = main_car

        self.draw_flag = True  # 是否绘制线
        self.point_number = 40  # 绘制点的个数
        self.space_between = 0.5  # 点的间距
        self.frequency = 0.1  # 绘制线的频率
        self.left_flag = True  # 左边
        self.right_flag = True  # 右边
        self.height = 2  # 高度
        self.thickness = 0.2  # 粗细

    def draw(self):
        def d():
            while True:
                if not self.draw_flag:
                    sleep(self.frequency)
                    continue
                location = self.main_car.get_location()  # 获取车子坐标
                z = location.z  # 高度
                location = env_map.get_waypoint(location).next(5)[0].transform.location
                for _ in range(self.point_number):
                    waypoint = env_map.get_waypoint(location).next(self.space_between)[0]  # 前方的waypoint
                    if not waypoint:
                        continue
                    transform = waypoint.transform  # 前方transform
                    yaw = transform.rotation.yaw + 180  # 前方yaw
                    location = transform.location  # 前方location
                    width = waypoint.lane_width / 2  # 宽度
                    angle = math.radians(yaw)
                    if self.right_flag:
                        # 右
                        x = location.x + width * np.sin(angle)
                        y = location.y - width * np.cos(angle)
                        world.debug.draw_line(carla.Location(x=x, y=y, z=z),
                                              carla.Location(x=x, y=y, z=z + self.height), thickness=self.thickness,
                                              life_time=self.frequency, color=carla.Color(255, 0, 0))
                    if self.left_flag:
                        # 左
                        x = location.x - width * np.sin(angle)
                        y = location.y + width * np.cos(angle)
                        world.debug.draw_line(carla.Location(x=x, y=y, z=z),
                                              carla.Location(x=x, y=y, z=z + self.height), thickness=self.thickness,
                                              life_time=self.frequency, color=carla.Color(255,0,0))
                sleep(self.frequency)

        threading.Thread(target=d).start()


# 绘制车道线
class ActorDrawLaneLine:
    def __init__(self, main_car):
        self.main_car = main_car

        self.draw_flag = True  # 是否绘制线
        self.point_number = 40  # 绘制点的个数
        self.space_between = 0.5  # 点的间距
        self.frequency = 0.1  # 绘制线的频率
        self.left_flag = True  # 左边
        self.right_flag = True  # 右边
        self.height = 2  # 高度
        self.thickness = 0.2  # 粗细

    def draw(self):
        def get_lan_line_location(start_location:carla.Location ,point_number=40,space_between=0.5, direction="left"):
            """
            start_location: carla.Location()  # 起点，这个是车道的中心坐标
            point_number: int  # 点的个数
            space_between: int  # 每个点之间的间距
            return: list(carla.Location())  # 车道线坐标
            """
            pass


        def d():
            while True:
                if not self.draw_flag:
                    sleep(self.frequency)
                    continue
                location = self.main_car.get_location()  # 获取车子坐标
                z = location.z  # 高度
                location = env_map.get_waypoint(location).next(5)[0].transform.location  # 车子前方五米location
                for _ in range(self.point_number):
                    waypoint = env_map.get_waypoint(location).next(self.space_between)[0]  # 前方的waypoint
                    if not waypoint:
                        continue
                    transform = waypoint.transform  # 前方transform
                    yaw = transform.rotation.yaw + 180  # 前方yaw
                    location = transform.location  # 前方location
                    width = waypoint.lane_width / 2  # 宽度
                    angle = math.radians(yaw)
                    if self.right_flag:
                        # 右
                        x = location.x + width * np.sin(angle)
                        y = location.y - width * np.cos(angle)
                        world.debug.draw_line(
                            carla.Location(x=x, y=y, z=z),
                            location,
                            thickness=self.thickness,
                            life_time=self.frequency,
                            color=carla.Color(255, 0, 0)
                        )
                    if self.left_flag:
                        # 左
                        x = location.x - width * np.sin(angle)
                        y = location.y + width * np.cos(angle)
                        world.debug.draw_line(
                            carla.Location(x=x, y=y, z=z),
                            location,
                            thickness=self.thickness,
                            life_time=self.frequency,
                            color=carla.Color(255,0,0)
                        )
                sleep(self.frequency)

        threading.Thread(target=d).start()


# 绘制箭头
class ActorDrawArrow:
    def __init__(self, main_car):
        self.main_car = main_car

        self.draw_flag = True
        self.frequency = 0.1  # 绘制箭头的频率
        self.height = 0.1  # 高度
        self.width = 0.5  # 道路宽度，这个是倍数
        self.long = 3  # 道路长度，这个是倍数
        self.thickness = 0.2  # 线的粗细
        self.color = (0,255,255)  # 颜色
        self.number = 4  # 数量
        self.distance = 2  # 每个箭头之间的距离

    def draw(self):
        def d():
            while True:
                if not self.draw_flag:
                    sleep(self.frequency)
                    continue
                location = env_map.get_waypoint(self.main_car.get_location()).next(3)[0].transform.location

                for i in range(self.number):
                    wpt_t = env_map.get_waypoint(location).next(self.distance * (i + 1))
                    if not wpt_t:
                        sleep(self.frequency)
                        continue
                    transform = wpt_t[0].transform
                    yaw = transform.rotation.yaw
                    location = transform.location

                    begin_location = location + carla.Location(z=0)
                    angle = math.radians(yaw)
                    end_location = begin_location - carla.Location(x=self.long * math.cos(angle),
                                                                   y=self.long * math.sin(angle))

                    # 左
                    x1 = end_location.x + self.width * np.sin(angle)
                    y1 = end_location.y - self.width * np.cos(angle)

                    # 右
                    x2 = end_location.x - self.width * np.sin(angle)
                    y2 = end_location.y + self.width * np.cos(angle)

                    world.debug.draw_line(begin_location, carla.Location(x=x1, y=y1),
                                          color=carla.Color(r=self.color[0], g=self.color[1], b=self.color[2]),
                                          life_time=self.frequency,
                                          thickness=self.thickness)
                    world.debug.draw_line(begin_location, carla.Location(x=x2, y=y2),
                                          color=carla.Color(r=self.color[0], g=self.color[1], b=self.color[2]),
                                          life_time=self.frequency,
                                          thickness=self.thickness)
                sleep(self.frequency)

        threading.Thread(target=d).start()


# 碰撞检测
def obstacle_callback(data):
    detection_actor=[]
    if ArHudShow.car_bounding_box:
        detection_actor.append("vehicle")
    if ArHudShow.object_bounding_box:
        detection_actor.append("prop")
    if not detection_actor:
        return
    other_actor=data.other_actor
    if other_actor.attributes:  # 如果检测到了物体
        ros_name=other_actor.attributes.get("ros_name")
        for i in detection_actor:
            if i in ros_name:
                bounding_box = other_actor.bounding_box
                bounding_box.location+=other_actor.get_location()
                world.debug.draw_box(bounding_box,other_actor.get_transform().rotation,life_time=0.1,color=carla.Color(0,255,255),thickness=0.1)
    else:
        pass
        # print("没有检测到障碍物")


def main():
    # width, height = 1920, 1080
    width, height = 3440,1300
    vehicle_list = []
    sensor_list = []

    # socket
    socket_client = ClientSocket("user1")
    socket_client.start()
    try:
        # 销毁世界中的所有车
        destroy_all_vehicles_traffics(world)
        # 创建车流和交通标志
        # for i in range(100):
        #     a=world.try_spawn_actor(random.choice(vehicle_models),random.choice(vehicle_transform))
        #     vehicle_list.append(a)
        #     if a:
        #         a.set_autopilot(True)
        # for i in range(20,30):
        #     transform=vehicle_transform[i+1]
        #     transform.location.z=0
        #     # print(type(blueprint_library.filter('*prop*')[58]))
        #     a=world.try_spawn_actor(blueprint_library.filter('*prop*')[42],transform)
        #     vehicle_list.append(a)

        # 创建主车
        vehicle_bp = blueprint_library.filter('*vehicle*')[0]
        vehicle_bp.set_attribute("role_name", "hero")
        # ego_vehicle = world.try_spawn_actor(vehicle_bp, carla.Transform(carla.Location(x=4768.90,y=-146.90,z=0.1),carla.Rotation(yaw=180)))  # hud录制
        # ego_vehicle = world.try_spawn_actor(vehicle_bp, carla.Transform(carla.Location(x=4379.95,y=-479.95,z=0.1),carla.Rotation(yaw=30)))  # 停车场
        ego_vehicle = world.try_spawn_actor(vehicle_bp, random.choice(vehicle_transform))
        world.tick(10)

        # 初始化车子信息
        HudShow.now_pos = ego_vehicle.get_location()
        HudShow.now_time = time.time()
        if not ego_vehicle:
            print("Failed to spawn ego vehicle")
            os._exit(0)
        vehicle_list.append(ego_vehicle)

        # 碰撞检测摄像头
        # obstacle_bp = world.get_blueprint_library().find('sensor.other.obstacle')
        # obstacle_bp.set_attribute('distance', '50')
        # # obstacle_bp.set_attribute('hit_radius', '2')
        # # obstacle_bp.set_attribute('debug_linetrace', 'True')
        # obstacle_bp.set_attribute('sensor_tick', '0.1')
        # obstacle_sensor = world.spawn_actor(obstacle_bp, carla.Transform(carla.Location(z=0.1)), attach_to=ego_vehicle)
        # obstacle_sensor.listen(lambda image:obstacle_callback(image))
        # sensor_list.append(obstacle_sensor)

        # 划竖线
        # actor_draw_vertical_line = ActorDrawLaneLine(ego_vehicle)
        # actor_draw_vertical_line.right_flag = False
        # # actor_draw_line.draw_flag = False
        # actor_draw_vertical_line.draw()

        # 画箭头
        actor_draw_arrow = ActorDrawArrow(ego_vehicle)
        # actor_draw_arrow.color = (255, 0, 0)  # 红色
        # actor_draw_arrow.color = (0,255,0)  # 绿色
        actor_draw_arrow.draw_flag = True
        actor_draw_arrow.draw()

        # 车辆控制器
        vehicle_control = VehicleControl(ego_vehicle)
        steering_wheel = SteeringWheel("G29 Racing Wheel", file_ini=os.path.join(os.getcwd(),"config/wheel_config.ini"))
        threading.Thread(target=steering_wheel.parse).start()

        # 窗口
        window = Window(world, ego_vehicle, (width, height))
        sensor_list += window.sensor_list
        speed_limit_number=0
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    os._exit(0)

            # 车辆控制
            steer, throttle, brake, reverse, auto_manual = steering_wheel.get_data()
            if HudShow.remaining_mileage<0.01:
                throttle=0
            # print(f"方向盘:{steer:.2f},油门:{throttle:.2f},刹车:{brake:.2f},倒车:{reverse},自动驾驶:{auto_manual}")
            vehicle_control.run_control(steer, throttle, brake, reverse)
            vehicle_control.auto_flag = auto_manual

            # 自动，人工驾驶图标的切换
            socket_client.send({
                'name': "auto_blue,auto_gray,manual_blue,manual_gray",
                "action": HudShow.auto_actions[auto_manual]
            })

            # 绘制路线指引
            # if ArHudShow.route:
            #     actor_draw_arrow.draw_flag = True
            # else:
            #     actor_draw_arrow.draw_flag = False

            # 绘制停止的交通标志牌
            if ArHudShow.stop_sign:
                stops = world.get_actors().filter("*stop*")
                for stop_sign in stops:
                    stop_bb = stop_sign.bounding_box
                    stop_bb.location = stop_sign.get_location()
                    stop_bb.location.z += 1

                    # world.debug.draw_box(stop_bb, stop_sign.get_transform().rotation,life_time=10,color=carla.Color(r=255,g=0,b=0,a=255))
                    rotation = stop_sign.get_transform().rotation
                    # rotation.yaw-=180
                    world.debug.draw_box(stop_bb, rotation, color=carla.Color(r=255, g=0, b=0, a=255), life_time=0.1, thickness=0.1)


            # 电量显示
            if time.time() - HudShow.now_time > 0.01:
                # 计算
                dis = ego_vehicle.get_location().distance(HudShow.now_pos)
                HudShow.remaining_mileage = max(HudShow.remaining_mileage - dis / 1000, 0)
                # 更新
                HudShow.now_pos = ego_vehicle.get_location()
                HudShow.now_time = time.time()

            action = HudShow.get_power_from_mileage()
            socket_client.send({
                "name": "ele100,ele75,ele50,ele25",
                "action": action
            })
            # 速度显示
            socket_client.send({
                'image': str(int(get_speed(ego_vehicle))),
                "name": "speed",
                "action": "update_label",
            })
            # 交通灯提醒
            # traffic_light = ego_vehicle.get_traffic_light()
            # if traffic_light:  # 如果有信号灯
            #     traffic_light_state = traffic_light.get_state()
            #     action = HudShow.traffic_actions.get(traffic_light_state, "hide_label,hide_label,hide_label")
            # else:
            #     action="hide_label,hide_label,hide_label"
            # socket_client.send({
            #     'name': "red_light,yellow_light,green_light",
            #     "action": action
            # })

            # 速度限制提醒
            # names=["limit_40","limit_60"]
            # if speed_limit_number>100:
            #     n=random.choice(names)
            #     socket_client.send({
            #         'name': n,
            #         "action": "show_label",
            #     })
            #     names.remove(n)
            #     socket_client.send({
            #         'name': names[0],
            #         "action": "hide_label",
            #     })
            #     speed_limit_number=0
            # speed_limit_number+=1



            # 车灯开启情况
            # light_state, action = HudShow.light_actions[steering_wheel.low_high_light]
            # ego_vehicle.set_light_state(light_state)
            # socket_client.send({
            #     "name": "high_beam,low_beam",
            #     "action": action
            # })

            # 目的地、距离和预计到达时间
            # distance=HudShow.dt_location.distance(ego_vehicle.get_location())  # 距离m
            # speed=get_speed(ego_vehicle)
            # if speed>0.01:
            #     t=int(distance/(max(get_speed(ego_vehicle)/3.6,0.01)))  # 预计到达时间
            #     if t>30:
            #         t=">30"
            # else:
            #     t=">30"
            # socket_client.send({
            #     'image': str(t),
            #     "name": "time",
            #     "action": "update_label",
            # })

            # 探头提示

            # AR实物导航,角度制
            # now_yaw=env_map.get_waypoint(ego_vehicle.get_location()).transform.rotation.yaw%360
            # later_waypoint=env_map.get_waypoint(ego_vehicle.get_location()).next(20)
            # if later_waypoint:
            #     later_yaw=later_waypoint[0].transform.rotation.yaw%360
            #
            #     difference=abs(now_yaw - later_yaw)
            #     angle=min(difference, 360 - difference)  # 夹角度数
            #
            #     if angle < 10:
            #         socket_client.send({
            #             "name": "turn_left,crastidrome,turn_right",
            #             "action": "hide_label,show_label,hide_label"
            #         })
            #     else:
            #         diff = (now_yaw - later_yaw)%360
            #         if diff < 180:
            #             socket_client.send({
            #                 "name": "turn_left,crastidrome,turn_right",
            #                 "action": "show_label,hide_label,hide_label"
            #             })
            #         else:
            #             socket_client.send({
            #                 "name": "turn_left,crastidrome,turn_right",
            #                 "action": "hide_label,hide_label,show_label"
            #             })

            # carla画面更新
            window.render()

            # 后车风险提示
            # if ArHudShow.danger_flag:  # 如果需要绘制
            #     if ArHudShow.danger_opacity > 255 - ArHudShow.danger_speed:  # 大于255
            #         ArHudShow.danger_direction = False  # 更改方向
            #     elif ArHudShow.danger_opacity<ArHudShow.danger_speed:  # 小于0
            #         ArHudShow.danger_direction = True  # 更改方向
            #
            #     if ArHudShow.danger_direction:
            #         ArHudShow.danger_opacity += ArHudShow.danger_speed
            #     else:
            #         ArHudShow.danger_opacity -= ArHudShow.danger_speed
            #
            # ArHudShow.red_alert_image.set_alpha(ArHudShow.danger_opacity)  # 设置透明度
            # window.screen.blit(ArHudShow.red_alert_image, (0,0))  # 绘制

            # 刷新画面
            pygame.display.flip()
            window.clock.tick(60)
    except Exception as e:
        print("错误：", e)
        traceback.print_exc()  # 抛出异常
    finally:
        socket_client.disconnect()
        for i in sensor_list:
            i.destroy()
        for i in vehicle_list:
            i.destroy()


if __name__ == '__main__':
    main()
