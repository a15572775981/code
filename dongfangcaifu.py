from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
import time
import os
from lxml import etree
import re
from urllib.request import urlretrieve
from PIL import Image
import random
from selenium.webdriver import ActionChains


class DongFangCF:
    def __init__(self):
        self.browser = webdriver.Chrome()
        self.url = 'https://passport2.eastmoney.com/pub/login?backurl=http%3A//www.eastmoney.com/'
        self.wait = WebDriverWait(self.browser, 10)

    def mkdir_file(self):
        """
        创建存储图片的文件夹
        :return:
        """
        if not os.path.exists('TongHuasCode'):
            os.mkdir('TongHuasCode')

    def first_click(self):
        """
        第一次点击激活弹出验证码对话框，并且得到带缺口和不带缺口的图片X,Y值
        :return:X,Y值
        """
        try:
            self.browser.get(self.url)
            self.browser.switch_to_frame("frame_login")   # 切换到内部frame里面
            login_email = self.wait.until(EC.presence_of_element_located((By.ID, 'txt_account')))
            login_password = self.wait.until(EC.presence_of_element_located((By.ID, 'txt_pwd')))
            btn_login = self.wait.until(EC.presence_of_element_located((By.ID, 'btn_login')))
            login_email.click()
            login_email.send_keys('a348524844')
            login_password.click()
            login_password.send_keys('77921')
            btn_login.click()
            em_init_icon = self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'em_init_icon')))
            em_init_icon.click()
            time.sleep(1)
            html = etree.HTML(self.browser.page_source)
            result_bg = html.xpath('//div[@class="em_cut_fullbg_slice"]')
            result_fullbg = html.xpath('//div[@class="em_cut_bg_slice"]')
            bg_url = re.findall('url\("(.*?)"\);', result_bg[0].get('style'))[0]  #  不带缺口
            fullbg_url = re.findall('url\("(.*?)"\);', result_fullbg[0].get('style'))[0]  #  带缺口

            bg_list = []    # 带缺口的 xy 值
            for bg in result_bg:
                bg_dict = {}
                bg_dict['x'] = int(re.findall('background-position: (.*?)px (.*?)px;', bg.get('style'))[0][0])
                bg_dict['y'] = int(re.findall('background-position: (.*?)px (.*?)px;', bg.get('style'))[0][1])
                # print(bg_dict)
                bg_list.append(bg_dict)

            fullbg_list = []  # 不带缺口的 xy 值
            for bg in result_fullbg:
                fullbg_dict = {}
                fullbg_dict['x'] = int(re.findall('background-position: (.*?)px (.*?)px;', bg.get('style'))[0][0])
                fullbg_dict['y'] = int(re.findall('background-position: (.*?)px (.*?)px;', bg.get('style'))[0][1])
                fullbg_list.append(fullbg_dict)

            self.mkdir_file()
            urlretrieve(url=bg_url, filename=r'TongHuasCode/bg_img.jpg')  # 下载保存无序的带缺口图片
            print('无序的缺口图片保存完成')
            urlretrieve(url=fullbg_url, filename=r'TongHuasCode/fullbg_img.jpg')  # 下载保存无序的不带缺口图片
            print('无序的完整图片保存完成')
            return bg_list, fullbg_list
        except Exception:
            print('不是极验滑动验证,重新run一下程序')
            self.browser.close()

    def deal_img(self, filename, value):
        """
        处理完整图片
        :return:完整的图片
        """
        img = Image.open(filename)
        new_img = Image.new('RGB', (260, 160))    # 创建个新的图片
        img_upper = []   # 保存上部分
        img_lower = []   # 保存下部分
        for v in value:  # 裁剪10*80的图片， crop（）：里面是对应的坐标
            if v['y'] == -80:
                img_upper.append(img.crop((abs(v['x']), 80, abs(v['x'])+10, 160)))
            if v['y'] == 0:
                img_lower.append(img.crop((abs(v['x']), 0, abs(v['x']) + 10, 80)))
        # 拼接上半部分
        offset = 0
        for l in img_upper:
            new_img.paste(l, (offset, 80))
            offset += l.size[0]
        # 拼接下半部分
        x_offset = 0
        for u in img_lower:
            new_img.paste(u, (x_offset, 0))   # 将 x 坐标 粘贴到  new_img 上面的 （x_offset, o）的位置
            x_offset += u.size[0]

        new_img.save(r'TongHuasCode/' + re.split('[./]', filename)[1] + '1.jpg')
        print('完整的%s保存完成' % (re.split('[/]', filename)[1]+'1.jpg'))
        return new_img

    def is_pixel_equal(self, image1, image2, x, y):
        """
        判断两个像素是否相同
        :param image1: 图片1
        :param image2: 图片2
        :return: 位置是否相同
        """
        # 获取两个图片的像素点
        pixel1 = image1.load()[x, y]
        pixel2 = image2.load()[x, y]
        threshold = 60
        if abs(pixel1[0] - pixel2[0]) < threshold and abs(pixel1[1] - pixel2[1]) < threshold and abs(pixel1[2] - pixel2[2]) < threshold:
            return True
        else:
            return False

    def get_gap(self, image1, image2):
        """
        获取缺口偏移量
        :param image1:  带缺口
        :param image2:  不带缺口
        :return:
        """
        left = 60   # 定义一个阈值，用来比较大小，如果在这个值之内就代表像素相同，否则不相同即为缺口位置
        for i in range(left, image1.size[0]):
            for j in range(image1.size[1]):
                if not self.is_pixel_equal(image1, image2, i, j):
                    left = i
                    return left
        return left

    def get_track(self, distance):
        """
        根据偏移量和手动操作模拟计算移动轨迹
        :param distance: 偏移量
        :return: 移动轨迹
        """
        # 移动轨迹
        tracks = []
        # 当前位移
        current = 0
        # 减速阈值
        mid = distance * 4 / 5
        # 时间间隔
        t = 0.2
        # 初始速度
        v = 0

        while current < distance:
            if current < mid:
                a = random.uniform(2, 5)
            else:
                a = -(random.uniform(12.5, 13.5))
            v0 = v
            v = v0 + a * t
            x = v0 * t + 1 / 2 * a * t * t
            current += x

            if 0.6 < current - distance < 1:
                x = x - 0.53
                tracks.append(round(x, 2))

            elif 1 < current - distance < 1.5:
                x = x - 1.4
                tracks.append(round(x, 2))
            elif 1.5 < current - distance < 3:
                x = x - 1.8
                tracks.append(round(x, 2))

            else:
                tracks.append(round(x, 2))

        return tracks

    def get_slider(self):
        """
        获取滑块的位置
        :return:
        """
        slider = self.wait.until(EC.presence_of_element_located((By.XPATH, '//div[@class="em_slider"]/div[2]')))
        return slider

    def move_to_gap(self, slider, tracks):
        """
        将滑块移动至偏移量处
        :param slider: 滑块的节点位置
        :param tracks: 移动轨迹
        :return:
        """
        action = ActionChains(self.browser)
        action.click_and_hold(slider).perform()  # click_and_hold() 执行点击鼠标不松开click_and_hold（）
        for t in tracks:
            action.move_by_offset(xoffset=t, yoffset=-1).perform()   # move_by_offset()：鼠标从当前位置移动到某个坐标
            action = ActionChains(self.browser)
        time.sleep(0.6)
        action.release().perform()  # release()在松开鼠标

def main():
    try:
        login = DongFangCF()
        bg_value, fullbg_value = login.first_click()
        image1 = login.deal_img('TongHuasCode/fullbg_img.jpg', fullbg_value)  # 处理不带缺口的图片
        image2 = login.deal_img('TongHuasCode/bg_img.jpg', bg_value)  # 处理带缺口的图片
        distance = login.get_gap(image1, image2) * 1.135
        slider = login.get_slider()  # 滑块的节点
        tracks = login.get_track(distance)  # 偏移量的移动轨迹方法
        login.move_to_gap(slider, tracks)
        time.sleep(0.5)
        login.browser.close()
    except Exception:
        print('程序出错')

if __name__ == '__main__':
    main()

