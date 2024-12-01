# 车辆控制类
import math
import threading
import time
from typing import Optional
import carla
import numpy as np
import pygame
import open3d as o3d


# 子线程装饰器，函数帧率默认60
def control_fps(fps=60):
    """
    装饰器：控制函数的执行帧率，并在子线程中运行。
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            def run():
                frame_duration = 1 / fps  # 每帧的持续时间（秒）
                start_time = time.perf_counter()
                while True:
                    func(*args, **kwargs)  # 执行目标函数
                    elapsed_time = time.perf_counter() - start_time
                    time_to_sleep = max(frame_duration - elapsed_time, 0)
                    time.sleep(time_to_sleep)
                    start_time = time.perf_counter()

            thread = threading.Thread(target=run)
            thread.daemon = True  # 设置为守护线程
            thread.start()

        return wrapper

    return decorator


class VehicleControl:
    def __init__(self, vehicle):
        self.vehicle = vehicle

        self.steer = 0  # 方向盘
        self.throttle = 0  # 油门
        self.brake = 0  # 刹车
        self.reverse = False  # 倒车
        self.auto_flag = False  # 自动驾驶

        self.args_lateral_dict = {'K_P': 1.95, 'K_D': 0.2, 'K_I': 0.07, 'dt': 1.0 / 10.0}
        self.args_long_dict = {'K_P': 1, 'K_D': 0.0, 'K_I': 0.75, 'dt': 1.0 / 10.0}

    def run_control(self, steer, throttle, brake, reverse=False):
        if self.auto_flag:
            self.vehicle.set_autopilot(True)
        else:
            self.vehicle.set_autopilot(False)
            result = carla.VehicleControl(steer=round(steer, 3), throttle=round(throttle, 3), brake=round(brake, 3),
                                          reverse=reverse)
            self.vehicle.apply_control(result)


def destroy_all_vehicles_traffics(world: carla.World, vehicles=None, vehicle_flag=True, traffic_flag=True, people_flag=True):
    """
    销毁世界中的所有车辆，交通标志，人
    :param world: 世界对象
    :param vehicles:需要排除的车辆列表
    :param vehicle_flag: 是否销毁车辆，默认销毁
    :param traffic_flag: 是否销毁交通标志，默认销毁
    :param people_flag: 是否销毁人，默认销毁
    :param people_flag: 是否销毁人，默认销毁
    :return:
    """
    actors = []
    if vehicle_flag:
        actors += list(world.get_actors().filter('*vehicle*'))
    if traffic_flag:
        actors += list(world.get_actors().filter("*prop*"))
    if people_flag:
        actors += list(world.get_actors().filter("*walker*"))
    if vehicles:
        if isinstance(vehicles, list):
            car_id = [car.id for car in vehicles]
        else:
            car_id = [vehicles.id]
        actors = [car for car in actors if car.id not in car_id]
    # 销毁每个车辆
    for actor in actors:
        actor.destroy()


# 控制摄像头视角
class KeyboardControlCameraMove:
    def __init__(self, camera: carla.Sensor):
        pygame.init()
        self.camera = camera  # 摄像头对象
        self.transform = self.camera.get_transform()  # 摄像头位置

        self.sensor_offset_speed = 0.05  # 控制摄像机旋转的速度
        self.sensor_move_speed = 0.05  # 控制摄像机移动的速度
        self.roll_yaw = False  # 用于roll和yaw的切换控制
        self.mouse_look_active = False

    def parse_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:  # 窗口关闭
                pygame.quit()

        # 检测鼠标右键是否按下
        mouse_buttons = pygame.mouse.get_pressed()
        if mouse_buttons[2]:  # 右键被按下
            if not self.mouse_look_active:
                pygame.mouse.set_visible(False)  # 隐藏鼠标光标
                pygame.event.set_grab(True)  # 锁定鼠标到窗口
                pygame.mouse.get_rel()  # 重置鼠标相对移动量
                self.mouse_look_active = True

            # 获取鼠标相对移动
            mouse_rel = pygame.mouse.get_rel()

            # 鼠标水平移动调整yaw（视角水平旋转）
            self.transform.rotation.yaw += mouse_rel[0] * self.sensor_offset_speed

            # 鼠标垂直移动调整pitch（视角上下移动）
            self.transform.rotation.pitch -= mouse_rel[1] * self.sensor_offset_speed

        else:
            if self.mouse_look_active:
                pygame.mouse.set_visible(True)  # 显示鼠标光标
                pygame.event.set_grab(False)  # 解除鼠标锁定
                self.mouse_look_active = False

        # 获取键盘的状态，用于长按的监听
        key_down = pygame.key.get_pressed()
        # 摄像机的移动
        # 上下
        if key_down[pygame.K_e]:
            self._move_up(self.transform, self.sensor_move_speed)
        if key_down[pygame.K_q]:
            self._move_up(self.transform, -self.sensor_move_speed)
        # 前进后退
        if key_down[pygame.K_w]:
            self._move_next(self.transform, self.sensor_move_speed)
        if key_down[pygame.K_s]:
            self._move_next(self.transform, -self.sensor_move_speed)
        # 左右
        if key_down[pygame.K_a]:
            self._move_left(self.transform, self.sensor_move_speed)
        if key_down[pygame.K_d]:
            self._move_left(self.transform, -self.sensor_move_speed)

        # 设置摄像头视角以及位置
        self.camera.set_transform(self.transform)

    def _move_next(self, transform, distance):
        # 提取yaw和pitch角度，并转换为弧度
        yaw = math.radians(transform.rotation.yaw)
        pitch = math.radians(transform.rotation.pitch)

        # 计算方向向量
        direction = carla.Vector3D(
            math.cos(yaw) * math.cos(pitch),
            math.sin(yaw) * math.cos(pitch),
            math.sin(pitch)
        )

        # 计算新的位置
        new_location = transform.location + direction * distance

        # 创建新的Transform对象，保持原始的旋转
        new_transform = carla.Transform(new_location, transform.rotation)

        self.transform = new_transform

    def _move_left(self, transform, distance):
        # 当前的yaw角度转换为弧度
        yaw = math.radians(transform.rotation.yaw)

        # 左转90度 (yaw - 90°)
        yaw_left = yaw - math.radians(90)

        # 计算新的方向向量
        direction = carla.Vector3D(
            math.cos(yaw_left),
            math.sin(yaw_left),
            0  # 水平移动，不改变z坐标
        )

        # 计算新的位置
        new_location = transform.location + direction * distance

        # 创建新的Transform对象，保持原始的旋转
        new_transform = carla.Transform(new_location, transform.rotation)

        self.transform = new_transform

    def _move_up(self, transform, distance):
        # 计算向上的方向向量
        direction = carla.Vector3D(
            0,  # 水平不变
            0,  # 水平不变
            1  # 向上移动
        )

        # 计算新的位置
        new_location = transform.location + direction * distance

        # 创建新的Transform对象，保持原始的旋转
        new_transform = carla.Transform(new_location, transform.rotation)

        self.transform = new_transform


class Window:
    def __init__(self, world, vehicle: carla.Vehicle, screen_size=(1920, 1080)):
        """
        创建车子的pygame窗口显示
        :param vehicle: 车子对象
        """
        self.world = world
        self.vehicle = vehicle
        self.width, self.height = screen_size  # 屏幕大小
        self.cameras = {}  # 摄像头对象：数据data
        self.sensor_list = []

        pygame.init()  # 初始化pygame
        # 初始化窗口
        pygame.display.set_caption("pygame模拟场景")
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.HWSURFACE | pygame.DOUBLEBUF, 32)
        # 初始化窗口设置
        self.clock = pygame.time.Clock()
        # 初始化传感器
        # rgb_sensor_transform=carla.Transform(carla.Location(x=1.5, y=-0.28, z=1.3),carla.Rotation(pitch=0, yaw=0, roll=0))
        # rgb_sensor_transform = carla.Transform(carla.Location(x=0.5, y=-.35, z=1.15), carla.Rotation())  # 特斯拉
        rgb_sensor_transform = carla.Transform(carla.Location(x=0.15, y=-.35, z=1.3), carla.Rotation())  # 问界第一视角
        # rgb_sensor_transform = carla.Transform(carla.Location(x=0.15, y=-3, z=1.3), carla.Rotation(yaw=90))  # 问界侧视角
        self.init_sensor(rgb_sensor_transform)  # 传感器相对车子的位置设置)

    def init_sensor(self, spawn_transform: carla.Transform, sensor_type='sensor.camera.rgb'):
        if sensor_type == "sensor.camera.rgb":
            blueprint_camera = self.world.get_blueprint_library().find(sensor_type)  # 选择一个传感器蓝图
            blueprint_camera.set_attribute('image_size_x', f'{self.width}')  # 传感器获得的图片高度
            blueprint_camera.set_attribute('image_size_y', f'{self.height}')  # 传感器获得的图片宽度
            blueprint_camera.set_attribute('fov', '110')  # 水平方向上能看到的视角度数

            sensor = self.world.spawn_actor(blueprint_camera, spawn_transform, attach_to=self.vehicle)  # 添加传感器
            sensor.listen(lambda image: self.process_rgb_img(sensor, image))
            self.sensor_list.append(sensor)

    # 更新画面信息
    def render(self):  # 显示窗口
        for camera in self.cameras:
            # rgb摄像头
            if camera.attributes.get("ros_name") == 'sensor.camera.rgb':
                surface = self.cameras[camera]
                if surface:
                    self.screen.blit(surface, (0, 0))

    # 加载rgb图像
    def process_rgb_img(self, sensor, image):
        array = np.array(image.raw_data)
        array = np.reshape(array, (self.height, self.width, 4))
        array = array[:, :, :3]
        array = array[:, :, ::-1]
        surface = pygame.surfarray.make_surface(array.swapaxes(0, 1))
        self.cameras[sensor] = surface


def get_vehicle_attributes(world: carla.World, name: str) -> Optional[carla.Actor]:
    actors = world.get_actors()
    for actor in actors:
        if actor.attributes.get('role_name') == name:
            return actor
    return None

def get_map(xodr_path,name="test"):
    with open(xodr_path, encoding="utf-8") as f:
        xodr_str = f.read()
    env_map = carla.Map(name, xodr_str)
    return env_map

# 可视化点云
def visual_point_cloud(env_map, distance=10):
    waypoints = env_map.generate_waypoints(distance)
    locations = [waypoint.transform.location for waypoint in waypoints]

    # 将locations中的坐标信息转换为适合Open3D绘制的格式
    points = np.array([[loc.x, loc.y, loc.z] for loc in locations])
    # # 创建一个点云对象
    point_cloud = o3d.geometry.PointCloud()
    point_cloud.points = o3d.utility.Vector3dVector(points)

    # 可视化点云
    o3d.visualization.draw_geometries([point_cloud])

def visual_direction(world:carla.World, env_map:carla.Map, distance=10, life_time=30):
    waypoints = env_map.generate_waypoints(distance)
    for waypoint in waypoints:
        start_location=waypoint.transform.location
        end_waypoint=env_map.get_waypoint(start_location).next(distance/2)
        if not end_waypoint:
            continue
        end_location=end_waypoint[0].transform.location

        start_location.z+=0.5
        end_location.z+=0.5

        world.debug.draw_arrow(start_location, end_location,life_time=life_time)

def draw_lane_line(world, env_map, vehicle):
    location = vehicle.get_location()  # 获取车子坐标
    start_waypoint = env_map.get_waypoint(location).next(5)  # 车子前方五米waypoint
    if start_waypoint:
        start_waypoint = start_waypoint[0]
        for i in range(1, 6):
            # 起点
            start_transform = start_waypoint.transform
            start_yaw = start_transform.rotation.yaw
            start_location = start_transform.location
            start_width = start_waypoint.lane_width / 2
            start_angle = math.radians(start_yaw)

            # 右
            right_x1 = start_location.x - start_width * np.sin(start_angle)
            right_y1 = start_location.y + start_width * np.cos(start_angle)
            right_z1 = start_location.z

            # 左
            left_x1 = start_location.x + start_width * np.sin(start_angle)
            left_y1 = start_location.y - start_width * np.cos(start_angle)
            left_z1 = start_location.z

            # 下一个点
            next_waypoint = env_map.get_waypoint(start_location).next(i + 1)  # 前方的waypoint
            if next_waypoint:
                next_waypoint = next_waypoint[0]
                next_transform = next_waypoint.transform
                next_yaw = next_transform.rotation.yaw
                next_location = next_transform.location
                next_width = next_waypoint.lane_width / 2
                next_angle = math.radians(next_yaw)
                # 右
                right_x2 = next_location.x - next_width * np.sin(next_angle)
                right_y2 = next_location.y + next_width * np.cos(next_angle)
                right_z2 = next_location.z
                # 左
                left_x2 = next_location.x + next_width * np.sin(next_angle)
                left_y2 = next_location.y - next_width * np.cos(next_angle)
                left_z2 = next_location.z
                world.debug.draw_line(
                    carla.Location(x=right_x1, y=right_y1, z=right_z1),
                    carla.Location(x=right_x2, y=right_y2, z=right_z2),
                    thickness=0.1,
                    life_time=0.05,
                    color=carla.Color(0, 255, 0)
                )
                world.debug.draw_line(
                    carla.Location(x=left_x1, y=left_y1, z=left_z1),
                    carla.Location(x=left_x2, y=left_y2, z=left_z2),
                    thickness=0.1,
                    life_time=0.05,
                    color=carla.Color(0, 255, 0)
                )
                start_waypoint = next_waypoint