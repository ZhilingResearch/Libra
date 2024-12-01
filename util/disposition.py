import carla
import pygame


client = carla.Client("127.0.0.1", 2000)  # 连接carla
client.set_timeout(10)  # 设置超时
world = client.get_world()  # 获取世界对象
env_map = world.get_map()  # 获取地图对象

spectator = world.get_spectator()  # ue4中观察者对象
blueprint_library = world.get_blueprint_library()  # 获取蓝图，可以拿到可创建的对象
vehicle_transform = env_map.get_spawn_points()  # 拿到世界中所有可绘制车辆的点坐标transform
vehicle_models = blueprint_library.filter('*vehicle*')  # 拿到所有可绘制的车辆模型
prop_model = blueprint_library.filter('*prop*')  # 拿到所有可绘制的交通标志模型

