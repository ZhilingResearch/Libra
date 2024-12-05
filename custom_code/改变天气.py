#!/usr/bin/env python

# Copyright (c) 2019 Computer Vision Center (CVC) at the Universitat Autonoma de
# Barcelona (UAB).
#
# This work is licensed under the terms of the MIT license.
# For a copy, see <https://opensource.org/licenses/MIT>.

"""
CARLA Dynamic Weather:

Connect to a CARLA Simulator instance and control the weather. Change Sun
position smoothly with time and generate storms occasionally.
"""
import sys
import random
from time import sleep

import carla


class Weather(object):
    def __init__(self, weather: carla.WeatherParameters):
        self.weather = weather

    # 值类型都是float
    def tick(self):
        self.weather.cloudiness = 15  # 云量0~100,100表示完全被云覆盖
        self.weather.precipitation = 0  # 降水量0~100
        self.weather.precipitation_deposits = 0  # 地面雨的湿度0~100，水坑总是在同位置
        self.weather.wind_intensity = 100  # 风强度0~100
        self.weather.sun_azimuth_angle = 300  # 太阳方位角0~360
        self.weather.sun_altitude_angle = 5  # 太阳高度角-90~90
        self.weather.fog_density = 0  # 雾的密度0~无穷
        self.weather.fog_distance  = 1  # 雾之间的间距0~无穷
        self.weather.wetness = 0  # 湿度0~100

        # 下面的一般不修改
        self.weather.fog_falloff  = 0  # 雾的密度（如比质量）从0到无穷大。该值越大，雾的密度和重量就越大，雾的高度就越小。对应于UE文档中的雾高衰减。 如果该值为0，则雾将比空气轻，并将覆盖整个场景。 值为1的密度近似于空气的密度，并达到正常大小的建筑物。 当数值大于5时，空气的密度会大到在地面上被压缩。
        self.weather.scattering_intensity  = 0  # 控制多少光将有助于体积雾。当设置为0时，没有贡献。
        self.weather.mie_scattering_scale   = 0  # 控制光与花粉等大颗粒或空气污染的相互作用，导致光源周围有朦胧的光晕。当设置为0时，没有贡献。
        # self.weather.rayleigh_scattering_scale    = 0.0331  # 控制光与空气分子等小粒子的相互作用。取决于光的波长，造成白天的天空是蓝色的，晚上的天空是红色的。
        self.weather.dust_storm     = 0  # 决定了沙尘暴天气的强弱。取值范围为0 ~ 100。

    # 值类型都是float
    def tick2(self):
        self.weather.cloudiness = random.uniform(0,100) # 云量0~100,100表示完全被云覆盖
        self.weather.precipitation = random.uniform(0,100)  # 降水量0~100
        self.weather.precipitation_deposits = random.uniform(0,100)  # 地面雨的湿度0~100，水坑总是在同位置
        self.weather.wind_intensity = random.uniform(0,100)  # 风强度0~100
        self.weather.sun_azimuth_angle = random.uniform(0,360)  # 太阳方位角0~360
        self.weather.sun_altitude_angle = random.uniform(-90,90)  # 太阳高度角-90~90
        self.weather.wetness = random.uniform(0,100)  # 湿度0~100

        self.weather.fog_density = random.uniform(0,1000)  # 雾的密度0~无穷
        self.weather.fog_distance = random.uniform(0,1000)  # 雾之间的间距0~无穷

        # 下面的一般不修改
        self.weather.fog_falloff = 0  # 雾的密度（如比质量）从0到无穷大。该值越大，雾的密度和重量就越大，雾的高度就越小。对应于UE文档中的雾高衰减。 如果该值为0，则雾将比空气轻，并将覆盖整个场景。 值为1的密度近似于空气的密度，并达到正常大小的建筑物。 当数值大于5时，空气的密度会大到在地面上被压缩。
        self.weather.scattering_intensity = 0  # 控制多少光将有助于体积雾。当设置为0时，没有贡献。
        self.weather.mie_scattering_scale = 0  # 控制光与花粉等大颗粒或空气污染的相互作用，导致光源周围有朦胧的光晕。当设置为0时，没有贡献。
        # self.weather.rayleigh_scattering_scale    = 0.0331  # 控制光与空气分子等小粒子的相互作用。取决于光的波长，造成白天的天空是蓝色的，晚上的天空是红色的。
        self.weather.dust_storm = 0  # 决定了沙尘暴天气的强弱。取值范围为0 ~ 100。

        for key, value in self.__dict__.items():
            print(f"{key}: {value}")

def main():
    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(20.0)
    world = client.get_world()

    weather = Weather(world.get_weather())

    weather.tick()
    # weather.tick2()
    world.set_weather(weather.weather)
    # flag=True
    # while True:
    #     print(weather.weather.sun_altitude_angle)
    #     sleep(0.05)
    #     world.set_weather(weather.weather)
    #     if flag:
    #         weather.weather.sun_altitude_angle-=0.1
    #         if weather.weather.sun_altitude_angle < 0:
    #             flag=False
    #     else:
    #         weather.weather.sun_altitude_angle+=0.1
    #         if weather.weather.sun_altitude_angle > 40:
    #             flag=True




if __name__ == '__main__':

    main()
