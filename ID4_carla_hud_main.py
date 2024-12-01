import time
from turtledemo.penrose import start

from sympy import total_degree

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
from util.vehicle_method import destroy_all_vehicles_traffics, VehicleControl, Window, draw_lane_line
from util.hud_socket import SocketClient
from util.steering import SteeringWheel

time_68=time.time()

# 天晖路终点
judgment_distance_flag=False
sunshine_road_start_point=carla.Location(x=4678.50,y=-158.85,z=0.1)
sunshine_road_end_point=carla.Location(x=4489.75,y=-239.95,z=0.1)
distance=sunshine_road_start_point.distance(sunshine_road_end_point)


# 转角
right_corner=carla.Location(x=4526.25,y=-171.15,z=0.1)
corner_flag=False
arrow_x=1823.2268749999998
arrow_y=670.4599999999999
arrow_width=94.76124999999999
arrow_height=34.4
opacity=1
expand_speed=0.3


def main():
    global time_68, judgment_distance_flag,arrow_x,arrow_y,arrow_width,arrow_height,opacity
    # width, height = 1920, 1080
    width, height = 3440,1300
    vehicle_list = []
    sensor_list = []
    dt_location=carla.Location(x=4350.70,y=-160.80,z=0)  # 目的地到达时间

    # 风险
    danger_opacity=0  # 风险的透明度变量
    danger_flag=True  # 风险的加减方向变量
    danger_speed=20  # 风险变化的速度变量
    red_alert_image = pygame.image.load("images/red_alert.png")
    red_alert_image = pygame.transform.scale(red_alert_image, (500, 500))

    # socket
    socket_client = SocketClient()
    # 初始化图标
    socket_client.send_image_text({
        "name":"white_68,green_68",
        "action":"hide_label,show_label"
    })
    socket_client.send_image_text({
        "name":"elec,sunshine,sunshine_500,sunshine_400,sunshine_300,right_warn",
        "action":"show_label,hide_label,hide_label,hide_label,hide_label,hide_label"
    })
    socket_client.send_image_text({
        "name": "right_arrow",
        "action": "hide_label"
    })
    try:
        # 销毁世界中的所有车
        destroy_all_vehicles_traffics(world)
        # 创建车流和交通标志
        # for i in range(150):
        #     a=world.try_spawn_actor(vehicle_models[0],random.choice(vehicle_transform))
        #     vehicle_list.append(a)
        #     if a:
        #         a.set_autopilot(True)

        # 创建主车
        vehicle_bp = blueprint_library.filter('*id4*')[0]
        vehicle_bp.set_attribute("role_name", "hero")
        ego_vehicle = world.try_spawn_actor(vehicle_bp, carla.Transform(carla.Location(x=4768.90,y=-146.90,z=0.1),carla.Rotation(yaw=180)))  # hud录制
        # ego_vehicle = world.try_spawn_actor(vehicle_bp, carla.Transform(carla.Location(x=4379.95,y=-479.95,z=0.1),carla.Rotation(yaw=30)))  # 停车场
        # ego_vehicle = world.try_spawn_actor(vehicle_bp, random.choice(vehicle_transform))
        world.wait_for_tick(10)
        now_pos = ego_vehicle.get_location()
        if not ego_vehicle:
            print("Failed to spawn ego vehicle")
            os._exit(0)
        vehicle_list.append(ego_vehicle)

        # 车辆控制器
        vehicle_control = VehicleControl(ego_vehicle)
        steering_wheel = SteeringWheel("G29 Racing Wheel", file_ini=os.path.join(os.getcwd(),"config/wheel_config.ini"))
        threading.Thread(target=steering_wheel.parse).start()

        # 窗口
        window = Window(world, ego_vehicle, (width, height))
        sensor_list += window.sensor_list
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    os._exit(0)

            # 车辆控制
            steer, throttle, brake, reverse, auto_manual = steering_wheel.get_data()
            # print(f"方向盘:{steer:.2f},油门:{throttle:.2f},刹车:{brake:.2f},倒车:{reverse},自动驾驶:{auto_manual}")
            vehicle_control.run_control(steer, throttle, brake, reverse)
            vehicle_control.auto_flag = auto_manual

            # 标线
            if 5<time.time()-time_68<15:
                draw_lane_line(world, env_map, ego_vehicle)

            # 68显示
            judgment_68_value=16
            check_68_time=(time.time()-time_68)%judgment_68_value
            if check_68_time<judgment_68_value/2:
                socket_client.send_image_text({
                    "name": "white_68,green_68",
                    "action": "show_label,hide_label"
                })
            else:
                socket_client.send_image_text({
                    "name": "white_68,green_68",
                    "action": "hide_label,show_label"
                })
            # 速度显示
            socket_client.send_image_text({
                'image': str(int(get_speed(ego_vehicle))),
                "name":"speed",
                "action": "update_label",
                "color":"#d9e3f0",
                "x":1612.849375,
                "y":782.57999,
                "width":153.96795,
                "height":70.08,
                "opacity":1
            })
            # 距离以及提醒
            if ego_vehicle.get_location().distance(sunshine_road_start_point)<10:
                judgment_distance_flag=True
            if judgment_distance_flag:
                if ego_vehicle.get_location().distance(sunshine_road_end_point)>distance*0.8:  # 500
                    socket_client.send_image_text({
                        "name": "elec,sunshine,sunshine_500,sunshine_400,sunshine_300,right_warn",
                        "action": "hide_label,hide_label,show_label,hide_label,hide_label,show_label"
                    })
                elif distance*0.6<ego_vehicle.get_location().distance(sunshine_road_end_point)<distance*0.8:  # 400
                    socket_client.send_image_text({
                        "name": "elec,sunshine,sunshine_500,sunshine_400,sunshine_300,right_warn",
                        "action": "hide_label,hide_label,hide_label,show_label,hide_label,show_label"
                    })
                elif distance*0.4<ego_vehicle.get_location().distance(sunshine_road_end_point)<distance*0.6:  # 300
                    socket_client.send_image_text({
                        "name": "elec,sunshine,sunshine_500,sunshine_400,sunshine_300,right_warn",
                        "action": "hide_label,show_label,hide_label,hide_label,show_label,hide_label"
                    })
                elif distance * 0.2 < ego_vehicle.get_location().distance(sunshine_road_end_point) < distance * 0.4:  # 到
                    socket_client.send_image_text({
                        "name": "elec,sunshine,sunshine_500,sunshine_400,sunshine_300,right_warn",
                        "action": "hide_label,show_label,hide_label,hide_label,hide_label,hide_label"
                    })
            # 转角
            if ego_vehicle.get_location().distance(right_corner)<20:
                # print(arrow_x,arrow_y,arrow_width,arrow_height)
                arrow_x = arrow_x-expand_speed
                arrow_y = arrow_y-expand_speed
                arrow_width = arrow_width+expand_speed*2
                arrow_height = arrow_height+expand_speed*2
                opacity-=0.001
                socket_client.send_image_text({
                    "name": "right_arrow",
                    "action": "show_label",
                })
                socket_client.send_image_text({
                    "name": "right_arrow",
                    "action": "update_label",
                    "x": arrow_x,
                    "y": arrow_y,
                    "width": arrow_width,
                    "height": arrow_height,
                    "opacity":opacity
                })
            else:
                socket_client.send_image_text({
                    "name": "right_arrow",
                    "action": "hide_label"
                })

            # 画面更新
            window.render()
            red_alert_image.set_alpha(danger_opacity)
            window.screen.blit(red_alert_image, (0,0))

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
