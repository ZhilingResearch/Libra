import re
import carla

def main():
    client = carla.Client("127.0.0.1", 2000)  # 连接carla
    client.set_timeout(10)  # 设置超时s
    world = client.get_world()  # 获取世界对象
    spectator = world.get_spectator()  # ue4中观察者对象

    # xodr_path=r"D:\carla\Unreal\CarlaUE4\Content\Custom\Maps\OpenDrive\QingyiBridge1129.xodr"
    # with open(xodr_path, encoding="utf-8") as f:
    #     xodr_str=f.read()
    # env_map = carla.Map(xodr_path.split("\\")[-1].split(".")[0],xodr_str)
    env_map=world.get_map()

    waypoints = env_map.generate_waypoints(20)
    spectator.set_transform(waypoints[0].transform)
    for waypoint in waypoints:
        start_location = waypoint.transform.location
        end_waypoint = env_map.get_waypoint(start_location).next(20 / 2)
        if not end_waypoint:
            continue
        end_location = end_waypoint[0].transform.location

        start_location.z += 0.5
        end_location.z += 0.5

        world.debug.draw_arrow(start_location, end_location,life_time=100)


if __name__ == '__main__':
    main()