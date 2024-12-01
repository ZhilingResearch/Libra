from turtledemo.penrose import start

import carla

client = carla.Client('localhost', 2000)
client.set_timeout(10.0)
world = client.get_world()
world.unload_map_layer(carla.MapLayer.All)
blueprint_library = world.get_blueprint_library()


# 画字符
def draw_waypoints(waypoints, road_id):
    for waypoint in waypoints:
        if waypoint.road_id == road_id:
            # world.debug.draw_string(waypoint.transform.location,
            #                         text,
            #                         draw_shadow=False,
            #                         color=carla.Color(r=0, g=255, b=0),
            #                         life_time=30.0)
            start_location=waypoint.transform.location
            start_location.z+=0.2

            end_waypoint=world.get_map().get_waypoint(start_location).next(1)
            if not end_waypoint:
                return
            end_location=end_waypoint[0].transform.location
            end_location.z+=0.2

            # world.debug.draw_arrow(start_location,end_location,life_time=10, color=carla.Color(r=0, g=255, b=0))
            world.debug.draw_arrow(start_location,end_location, color=carla.Color(r=0, g=255, b=0))

# 以1cm的间距取点
waypoints = world.get_map().generate_waypoints(distance=2.0)

# 道路标记
road_waypoints = []
for i in range(0, 100):
    for waypoint in waypoints:
        if waypoint.road_id == i:
            road_waypoints.append(waypoint)
    draw_waypoints(road_waypoints, road_id=i)
    road_waypoints.clear()

# 获取道路id为39的点
road_id_39_waypoints = []
for waypoint in waypoints:
    if (waypoint.road_id == 39):
        road_id_39_waypoints.append(waypoint)

# 在道路id为39的路上放置车辆
vehicle1_bp = blueprint_library.filter('model3')[0]
vehicle1_bp.set_attribute('color', '255, 0, 0')
vehicle1_spawn_point = road_id_39_waypoints[0].transform
vehicle1_spawn_point.location.z += 2
vehicle1 = world.spawn_actor(vehicle1_bp, vehicle1_spawn_point)

vehicle2_bp = blueprint_library.filter('model3')[0]
vehicle2_bp.set_attribute('color', '0, 0, 255')
vehicle2_spawn_point = road_id_39_waypoints[-1].transform
vehicle2_spawn_point.location.z += 2
vehicle2 = world.spawn_actor(vehicle2_bp, vehicle2_spawn_point)