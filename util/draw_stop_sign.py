import carla

from disposition import *
def draw_stop():
    stops = world.get_actors().filter("*stop*")
    for stop_sign in stops:
        stop_bb=stop_sign.bounding_box
        stop_bb.location = stop_sign.get_location()
        stop_bb.location.z+=1

        # world.debug.draw_box(stop_bb, stop_sign.get_transform().rotation,life_time=10,color=carla.Color(r=255,g=0,b=0,a=255))
        rotation=stop_sign.get_transform().rotation
        # rotation.yaw-=180
        world.debug.draw_box(stop_bb, rotation, color=carla.Color(r=255,g=0,b=0,a=255))
def draw_traffic_light():
    debug = world.debug
    world_snapshot = world.get_snapshot()

    for actor_snapshot in world_snapshot:
        actual_actor = world.get_actor(actor_snapshot.id)
        print(actual_actor)
        if actual_actor.type_id == 'traffic.traffic_light':
            debug.draw_box(carla.BoundingBox(actor_snapshot.get_location(), carla.Vector3D(0.5, 0.5, 10)), actor_snapshot.get_transform().rotation, 0.05,
                           carla.Color(255, 0, 0, 0), 0)
if __name__ == '__main__':
    draw_stop()
    # stops=world.get_actors().filter("*stop*")
    # stops=world.get_actors().filter("*light*")
    # for stop_sign in stops:
    #     stop_bb=stop_sign.bounding_box
    #
    #     stop_bb.location+=stop_sign.get_location()
    #
    #
    #     world.debug.draw_box(stop_bb,carla.Rotation())