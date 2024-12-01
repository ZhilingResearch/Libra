import json
import math
import os
import random
import threading
import time
import carla
import numpy as np
from pyglet import window

from disposition import *
from steering import SteeringWheel
from vehicle_method import Window


def get_speed(vehicle):
    """
    Compute speed of a vehicle in Km/h.

        :param vehicle: the vehicle for which speed is calculated
        :return: speed as a float in Km/h
    """
    vel = vehicle.get_velocity()

    return 3.6 * math.sqrt(vel.x ** 2 + vel.y ** 2 + vel.z ** 2)


class Info:
    def __init__(self,env_map,  main_car: carla.Vehicle, vice_cars):
        self.env_map = env_map
        self.main_car = main_car  # 主车
        self.vice_cars = vice_cars  # 副车列表
        self.info_flag = True  # 是否继续采集数据

        self.data = {}  # 存放数据

        if not os.path.exists("info"):
            os.makedirs("info")
        files = os.listdir("info")  # 所有表列表
        self.name = "table"  # 表名
        self.number = (lambda lst: 1 if not [int(i.split(".")[-2][-1]) for i in lst] else max(
            [int(i.split(".")[-2][-1]) for i in lst]) + 1)(files)  # 获取最大表数
        self.save_file = f"info/{self.name}{self.number}.json"  # 保存路径

        self.init_data()

    def init_data(self):
        # 初始化副车
        vice_dt = {}
        for index, vice in enumerate(self.vice_cars):
            vice_dt[f"vice_car{index + 1}"] = {
                "id": index + 2,
                "speed_x": [],  # 横向速率
                "speed_y": [],  # 纵向速率
                "acceleration_x": [],  # 横向加速度
                "acceleration_y": [],  # 纵向加速度
                "x": [],  # 坐标x
                "y": [],  # 坐标y
                "z": [],  # 坐标z
            }

        self.data = {
            "table_name": f"{self.name}{self.number}",
            "start_timestamp": f"{int(time.time() * 1000)}",
            "timestamp": [],
            "main_car": {
                "id": 1,
                "speed_x": [],  # 横向速率
                "speed_y": [],  # 纵向速率
                "acceleration_x": [],  # 横向加速度
                "acceleration_y": [],  # 纵向加速度
                "distance_left": [],  # 车辆中心线到左侧标线的距离
                "distance_right": [],  # 车辆中心线到右侧标线的距离
                "distance_center": [],  # 车辆中心线到标线中心的距离
                "steer": [],  # 方向盘
                "throttle": [],  # 油门
                "brake": [],  # 刹车
                "x": [],  # 坐标x
                "y": [],  # 坐标y
                "z": [],  # 坐标z
                "collision_time": [],  # 碰撞时间
            },
            "vice_car": vice_dt  # 副车列表
        }

    def get_info(self):
        def d():
            while self.info_flag:
                # 主车
                main_car_transform = self.main_car.get_transform()  # 主车transform
                main_car_location = main_car_transform.location  # 主车location
                main_car_waypoint = self.env_map.get_waypoint(main_car_location)  # 主车waypoint
                main_car_speed = get_speed(self.main_car)  # 主车速度
                main_car_acceleration = self.main_car.get_acceleration()  # 主车加速度
                yaw_offset = main_car_transform.rotation.yaw - main_car_waypoint.transform.rotation.yaw  # 道路方向与车子方向差
                angle = math.radians(yaw_offset)  # yaw转弧度制
                self.data["timestamp"].append(int(time.time() * 1000))
                self.data["main_car"]["speed_x"].append(main_car_speed * np.sin(angle))
                self.data["main_car"]["speed_y"].append(main_car_speed * np.cos(angle))
                self.data["main_car"]["acceleration_x"].append(main_car_acceleration.x)
                self.data["main_car"]["acceleration_y"].append(main_car_acceleration.y)

                left_x, left_y = self.get_offset(main_car_waypoint)  # 获取车子离左边标线的坐标
                right_x, right_y = self.get_offset(main_car_waypoint, "right")  # 获取车子右边标线的坐标
                point = np.array([main_car_location.x, main_car_location.y])  # 车子坐标
                point_left = np.array([left_x, left_y])  # 左边标线坐标
                point_right = np.array([right_x, right_y])  # 右边标线坐标
                main_car_center_location = main_car_waypoint.transform.location  # 车道中心location
                point_center = np.array([main_car_center_location.x, main_car_center_location.y])  # 车道中心坐标

                distance_left = np.linalg.norm(point - point_left)  # 距离左边
                distance_right = np.linalg.norm(point - point_right)  # 距离右边
                distance_center = np.linalg.norm(point - point_center)  # 距离中心
                self.data["main_car"]["distance_left"].append(distance_left)
                self.data["main_car"]["distance_right"].append(distance_right)
                self.data["main_car"]["distance_center"].append(distance_center)
                control = self.main_car.get_control()
                steer = control.steer
                throttle = control.throttle
                brake = control.brake
                if throttle == 0.5:
                    throttle = 0
                if brake == 0.5:
                    brake = 0
                self.data["main_car"]["steer"].append(steer)
                self.data["main_car"]["throttle"].append(throttle)
                self.data["main_car"]["brake"].append(brake)
                self.data["main_car"]["x"].append(main_car_location.x)
                self.data["main_car"]["y"].append(main_car_location.y)
                self.data["main_car"]["z"].append(main_car_location.z)

                car_position = self.judge_car_position(env_map, self.main_car, self.vice_cars, distance=100)
                next_car = car_position.get("next_car")
                if next_car:
                    ds = next_car[0].get_location().distance(self.main_car.get_location())
                    main_car_speed = get_speed(self.main_car)
                    next_car_speed = get_speed(next_car[0])
                    if main_car_speed > next_car_speed + 1:
                        ttc = ds / ((main_car_speed - next_car_speed) / 3.6)
                        self.data["main_car"]["collision_time"].append(ttc)
                    else:
                        self.data["main_car"]["collision_time"].append(-1)
                else:
                    self.data["main_car"]["collision_time"].append(None)

                # 副车
                for index, vice in enumerate(self.vice_cars):
                    if not vice.is_active:
                        continue
                    vice_location = vice.get_location()
                    vice_speed = vice.get_velocity()  # 速度
                    vice_acceleration = vice.get_acceleration()  # 加速度
                    self.data["vice_car"][f"vice_car{index + 1}"]["speed_x"].append(vice_speed.x)
                    self.data["vice_car"][f"vice_car{index + 1}"]["speed_y"].append(vice_speed.y)
                    self.data["vice_car"][f"vice_car{index + 1}"]["acceleration_x"].append(vice_acceleration.x)
                    self.data["vice_car"][f"vice_car{index + 1}"]["acceleration_y"].append(vice_acceleration.y)
                    self.data["vice_car"][f"vice_car{index + 1}"]["x"].append(vice_location.x)
                    self.data["vice_car"][f"vice_car{index + 1}"]["y"].append(vice_location.y)
                    self.data["vice_car"][f"vice_car{index + 1}"]["z"].append(vice_location.z)
                time.sleep(0.01)

        threading.Thread(target=d).start()

    def judge_car_position(self, e_map, main_car, vices_car, distance=50):
        car_position = {
            "right_next_car": [],
            "next_car": [],
            "left_next_car": [],
            "right_previous_car": [],
            "previous": [],
            "left_previous_car": []
        }

        for car in vices_car:
            if not car.is_active:
                continue
            reference_location = main_car.get_location()
            target_location = car.get_location()

            target_vector = np.array([
                reference_location.x - target_location.x,
                reference_location.y - target_location.y
            ])
            norm_target = np.linalg.norm(target_vector)  # 距离向量值
            if norm_target > distance:  # 超出距离的不要
                continue

            main_car_waypoint = e_map.get_waypoint(reference_location)  # 获取主车的waypoint
            main_car_road_id = main_car_waypoint.road_id
            main_car_lane_id = main_car_waypoint.lane_id

            right_lane = main_car_waypoint.get_right_lane()
            main_car_right_road_id = right_lane.road_id if right_lane else None
            main_car_right_lane_id = right_lane.lane_id if right_lane else None

            left_lane = main_car_waypoint.get_left_lane()
            main_car_left_road_id = left_lane.road_id if left_lane else None
            main_car_left_lane_id = left_lane.lane_id if left_lane else None

            car_waypoint = e_map.get_waypoint(target_location)
            car_road_id = car_waypoint.road_id
            car_lane_id = car_waypoint.lane_id

            # print(main_car_lane_id,car_lane_id)
            next_waypoint = e_map.get_waypoint(reference_location).next(1)[0]  # 前方一米waypoint
            # 前进后的距离新的距离
            next_new_vector = np.array([next_waypoint.transform.location.x - target_location.x,
                                        next_waypoint.transform.location.y - target_location.y])  # 前进后的新向量
            next_new_norm = np.linalg.norm(next_new_vector)  # 新距离

            if next_new_norm < norm_target:  # 前进的距离变短，前进一米可能会前进多,注意
                if main_car_road_id == car_road_id and main_car_lane_id == car_lane_id:  # 同一道路前,同一根路
                    car_position.get("next_car").append(car)
                elif main_car_right_road_id == car_road_id and main_car_right_lane_id == car_lane_id:  # 右边道路前
                    car_position.get("right_next_car").append(car)
                elif main_car_left_road_id == car_road_id and main_car_left_lane_id == car_lane_id:  # 左边道路前
                    car_position.get("left_next_car").append(car)
            else:
                if main_car_road_id == car_road_id and main_car_lane_id == car_lane_id:  # 同一道路
                    car_position.get("previous").append(car)
                elif main_car_right_road_id == car_road_id and main_car_right_lane_id == car_lane_id:  # 右边道路
                    car_position.get("right_previous_car").append(car)
                elif main_car_left_road_id == car_road_id and main_car_left_lane_id == car_lane_id:  # 左边道路
                    car_position.get("left_previous_car").append(car)
        return car_position

    @staticmethod
    def get_offset(waypoint, direction="left"):
        # 计算偏移量
        transform = waypoint.transform  # 前方transform
        location = transform.location
        yaw = transform.rotation.yaw + 180  # 前方yaw
        angle = math.radians(yaw)  # yaw转弧度制
        width = waypoint.lane_width / 2  # 宽度的一半
        if direction == "left":
            x = location.x - width * np.sin(angle)
            y = location.y + width * np.cos(angle)
            return x, y
        elif direction == "right":
            x = location.x + width * np.sin(angle)
            y = location.y - width * np.cos(angle)
            return x, y

    def save(self):
        time.sleep(1)  # 保证停止时所有数据一样长
        with open(self.save_file, 'w') as f:
            json.dump(self.data, f, indent=4, ensure_ascii=False)
        print(f"保存：{self.save_file}成功")


if __name__ == '__main__':
    # destroy_all_vehicles_traffics()

    ego_vehicle=world.try_spawn_actor( random.choice(blueprint_library.filter('*mini*')),random.choice(vehicle_transform))
    world.tick(10)
    ego_vehicle.set_autopilot(True)

    vice_list=[]
    for i in range(50):
        a= world.try_spawn_actor(random.choice(vehicle_models), random.choice(vehicle_transform))
        if a:
            a.set_autopilot(True)
            vice_list.append(a)

    info = Info(env_map, ego_vehicle, vice_list)
    info.get_info()

    window=Window(world, ego_vehicle)

    t = time.time()
    while time.time() - t < 10:
        print(int(time.time() - t))
        window.render()
        window.clock.tick(60)
        pygame.display.update()
    info.info_flag = False
    info.save()
