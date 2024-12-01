import threading
import time
from configparser import ConfigParser

import pygame
from time import sleep


class SteeringWheel:
    steer = 0  # 方向盘
    throttle = 0  # 油门
    brake = 0  # 刹车
    reverse = False  # 倒车
    auto_manual = False  # 自动驾驶
    low_high_light=0  # 近远光灯,0无灯,1近光,2远光

    def __init__(self, steer_name="G29 Racing Wheel", file_ini='config/wheel_config.ini'):
        self.steer_name = steer_name
        self.file_ini = file_ini
        self.pre_time = time.time()  # 当前按钮按下的时间
        self.between_time = 0.25  # 按钮防抖
        pygame.init()
        self.joysticks = {}
        self.init_config()

    def init_config(self):
        # 获取配置
        parser = ConfigParser()
        parser.read(self.file_ini)
        self.steer_idx = int(parser.get(self.steer_name, "steer"))
        self.throttle_idx = int(parser.get(self.steer_name, "throttle"))
        self.brake_idx = int(parser.get(self.steer_name, "brake"))
        self.reverse_idx = int(parser.get(self.steer_name, "reverse"))
        self.auto_manual_idx = int(parser.get(self.steer_name, "auto_manual"))
        self.low_high_light_idx = int(parser.get(self.steer_name, "low_high_light"))
        # print(f"方向盘id：{self.steer_idx},"
        #       f"油门id：{self.throttle_idx},"
        #       f"刹车id：{self.brake_idx},"
        #       f"倒车id：{self.reverse_idx}",
        #       f"自动切换id：{self.auto_manual_idx}",
        #       f"灯光切换id：{self.low_high_light_idx}", )

    def parse(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()

                if event.type == pygame.JOYDEVICEADDED:
                    joy = pygame.joystick.Joystick(event.device_index)
                    self.joysticks[joy.get_instance_id()] = joy
            # 这里才是判断你的关键
            for joystick in self.joysticks.values():
                # 按钮
                buttons = joystick.get_numbuttons()
                for _id in range(buttons):
                    # 倒车按钮
                    if _id == self.reverse_idx and joystick.get_button(_id):
                        if time.time() - self.pre_time > self.between_time:
                            self.pre_time = time.time()
                            self.reverse = not self.reverse
                    # 自动驾驶切换按钮
                    if _id == self.auto_manual_idx and joystick.get_button(_id):
                        if time.time() - self.pre_time > self.between_time:
                            self.pre_time = time.time()
                            self.auto_manual = not self.auto_manual
                    # 灯光切换按钮
                    if _id == self.low_high_light_idx and joystick.get_button(_id):
                        if time.time() - self.pre_time > self.between_time:
                            self.pre_time = time.time()
                            self.low_high_light += 1
                            if self.low_high_light > 2:
                                self.low_high_light=0
                # 轮子
                axes = joystick.get_numaxes()
                for _id in range(axes):
                    if _id == self.steer_idx:
                        self.steer = joystick.get_axis(_id)
                    if _id == self.throttle_idx:
                        self.throttle = (-joystick.get_axis(_id)+1)/2
                    if _id == self.brake_idx:
                        self.brake = (-joystick.get_axis(_id)+1)/2
                sleep(0.01)
                break

    def get_data(self):
        """

        :return:方向盘，油门，刹车，倒车，驾驶状态
        """
        return self.steer, self.throttle, self.brake, self.reverse, self.auto_manual


if __name__ == '__main__':
    s = SteeringWheel("MOZA R5 Base", file_ini=r"C:\Users\dai\Desktop\ce\util\config\wheel_config.ini")
    threading.Thread(target=s.parse).start()
    while True:
        print(s.get_data())
        sleep(1)
