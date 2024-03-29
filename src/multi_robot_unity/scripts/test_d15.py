#!/usr/bin/env python

import os
import sys
import tempfile
import csv
import tf
import rospy
import math
import message_filters
from std_msgs.msg import Float64MultiArray, String
from gazebo_msgs.msg import ModelStates
from gazebo_msgs.msg import ModelState
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Point, Quaternion
from geometry_msgs.msg import Twist, Vector3
import numpy as np

import cv2, cv_bridge
from sensor_msgs.msg import Image, CameraInfo

import configparser
import time

MAX_DIST = 30

global control
control = [0,0,0]
targets, centroid, key = [], [], []
global targets, centroid, key

def get_params():
    config = configparser.ConfigParser()
    config.read('index.txt')
    item_list = config.items('index')

    for item in item_list:
        key = item[0]
        value = item[1]

        if key == 'drone01':
            d1 = int(value)
        if key == 'drone02':
            d2 = int(value)    
        if key == 'drone03':
            d3 = int(value)
        if key == 'drone04':
            d4 = int(value)
        if key == 'drone05':
            d5 = int(value)
        if key == 'drone06':
            d6 = int(value)
        if key == 'drone07':
            d7 = int(value)
        if key == 'drone08':
            d8 = int(value)
        if key == 'drone09':
            d9 = int(value)
        if key == 'drone10':
            d10 = int(value)
        if key == 'drone11':
            d11 = int(value)
        if key == 'drone12':
            d12 = int(value)
        if key == 'drone13':
            d13 = int(value)
        if key == 'drone14':
            d14 = int(value)
        if key == 'drone15':
            d15 = int(value)


    params = [d1,d2,d3,d4,d5,d6,d7,d8,d9,d10,d11,d12,d13,d14,d15]
    return params


idx = get_params()

print(idx)

class Follower:
    def __init__(self):
    
        self.bridge = cv_bridge.CvBridge()
        image = rospy.Subscriber('/unity_image/compressed_d15', Image, self.image_callback)
        self.pos = rospy.Subscriber("controler", Float64MultiArray, self.pos_callback)
        self.centroid = rospy.Subscriber("centroid", Float64MultiArray, self.centroid_callback)
        self.key = rospy.Subscriber("key", String,self.key_callback)
        self.data = rospy.Subscriber('/gazebo/model_states', ModelStates, self.callback)
        self.cmd_vel_pub = rospy.Publisher('drone15/cmd_vel',Twist, queue_size=10)
        self.twist = Twist()
     
    def pos_callback(self, data):
        #print(data.data)
        targets = np.array(data.data)
        global targets
        targets = targets.reshape([-1,2])   
    
    def centroid_callback(self, data):
        #print(data.data)
        centroid = np.array(data.data)
        global centroid
              
    def key_callback(self, data):
        #print(data.data)
        key = data.data 
        global key

    def image_callback(self, msg):

        image = self.bridge.imgmsg_to_cv2(msg,desired_encoding='bgr8') #bgr8
        image = image[:, 30:image.shape[1]-30, :]
    
        # cv2.imshow("d13", image)
        # cv2.waitKey(3)
    

    def callback(self, data):
        global key

        drone15 = data.pose[idx[14]]
        drone15_vel = data.twist[idx[14]]
        d15_posX = drone15.position.x
        d15_posY = drone15.position.y
        d15_posZ = drone15.position.z
        d15_velX = drone15_vel.linear.x
        d15_velY = drone15_vel.linear.y

        if key == 'd':
            global targets
            target = targets[5]
            posX = target[0]
            posY = target[1]
            errX = posX - d15_posX
            errY = posY - d15_posY

            print("target: ", target, "Err: ", (errX, errY))

            ####################    
            ## POSITION BASED ##
            ####################

            # def my_callback(event):
            #     print 'Timer called at ' + str(event.current_real)
                
            # rospy.Timer(rospy.Duration(1), my_callback)
            

            calc_odom = (Vector3(-0.3*(d15_posX-posX), -0.3*(d15_posY-posY),-3*(d15_posZ-15)))
            pub = self.cmd_vel_pub
            pub.publish(Twist(calc_odom, Vector3(0,0,0)))
            #print('position control now')

        else:
            global centroid
            if len(centroid)>0:
                cX, cY = centroid
                #print("centroid: ", cX, cY)
                 
                calc_odom = (Vector3(-0.2*(d15_posX-(cX-2)), -0.2*(d15_posY-cY),-3*(d15_posZ-15)))
                pub = self.cmd_vel_pub
                pub.publish(Twist(calc_odom, Vector3(0,0,0)))
        rospy.Rate(1).sleep
           

    
def listener():
    rospy.init_node('d_15')
    follower = Follower()
    rospy.spin()

if __name__ == '__main__':
    start = time.time()
    try:
        listener()
    except rospy.ROSInterruptException:
        pass
# END ALL
