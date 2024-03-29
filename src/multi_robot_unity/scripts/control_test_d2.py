#!/usr/bin/env python

import os
import sys
import tempfile
import csv
import tf
import rospy
import math
import message_filters
from std_msgs.msg import String
from gazebo_msgs.msg import ModelStates
from gazebo_msgs.msg import ModelState
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Point, Quaternion
from geometry_msgs.msg import Twist, Vector3
import numpy as np

import configparser

import cv2, cv_bridge
from sensor_msgs.msg import Image, CameraInfo

def get_idx():
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
    idx = [d1,d2,d3,d4]
    return idx
idx = get_idx()
print(idx)

def calc_attractive_potential(x, y, tx, ty):
    dist = 0.5*math.sqrt((x-tx)**2 + (y-ty)**2)
    if(dist<=3):
        return 0, 0
    else: 
        return dist*(tx-x), dist*(ty-y)
    
def calc_repulsive_potential(x1, y1, x2, y2):
    dist = math.sqrt((x1-x2)**2 + (y1-y2)**2)
    if(dist<=2.5): # 2.5
        force_x = -1.5*(math.sqrt((x1-x2)**2))-7.5 #dist*gain
        force_y = -1.5*(math.sqrt((y1-y2)**2))-7.5
        if(x2>x1):
	    force_x = -force_x
        if(y2>y1):
	    force_y = -force_y
    else:
	force_x=0.0 
	force_y=0.0

    return force_x, force_y

class Follower:
    def __init__(self):
        
        self.bridge = cv_bridge.CvBridge()
        #cv2.namedWindow("window", 1)
        self.image_sub = rospy.Subscriber('drone02/downward_cam/camera/image', Image, self.image_callback)
        self.pos_sub = rospy.Subscriber('/gazebo/model_states', ModelStates, self.callback)
        self.cmd_vel_pub = rospy.Publisher('drone02/cmd_vel',Twist, queue_size=10)
        self.twist = Twist()
        
        
    def image_callback(self, msg):
        data = ModelState()
        data.model_name = 'drone02'
        drone = data.pose
        drone_vel = data.twist
        posX = drone.position.x
        posY = drone.position.y
        posZ = drone.position.z
        velX = drone_vel.linear.x
        velY = drone_vel.linear.y
        
        #print(d01_posZ)
        
        image = self.bridge.imgmsg_to_cv2(msg,desired_encoding='bgr8') #bgr8
        image = image[:, 30:image.shape[1]-30, :]
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        lower_flood = np.array([0, 100, 100])#np.array([100, 100, 0]) #yellow #np.array([0, 100, 100])
        upper_flood = np.array([150, 255, 255])#np.array([255, 255, 120]) #yellow #np.array([100, 255, 255])
        lower_ground = np.array([0, 0, 0])
        upper_ground = np.array([110, 110, 110])
        mask_flood = cv2.inRange(hsv, lower_flood, upper_flood)
        mask_ground = cv2.inRange(hsv, lower_ground, upper_ground)
        
        h, w, d = image.shape
        #print(h,w)
        
        search_top = 0#3*h/4
        search_bot = h#3*h/4 + 20
        mask_flood[0:search_top, 0:w] = 0
        mask_flood[search_bot:h, 0:w] = 0
        mask_ground[0:search_top, 0:w] = 0
        mask_ground[search_bot:h, 0:w] = 0
        M_flood = cv2.moments(mask_flood)
        M_ground = cv2.moments(mask_ground)
        
        if M_flood['m00'] > 0 and M_ground['m00'] > 0:
            print('fine')
            cx_flood = int(M_flood['m10']/M_flood['m00'])
            cy_flood = int(M_flood['m01']/M_flood['m00'])
            cv2.circle(image, (cx_flood, cy_flood), 10, (0,0,255), -1)
            cx_ground = int(M_ground['m10']/M_ground['m00'])
            cy_ground = int(M_ground['m01']/M_ground['m00'])
            cv2.circle(image, (cx_ground, cy_ground), 10, (255,0,0), -1)

            cx_middle = min(cx_flood, cx_ground) + int((max(cx_flood, cx_ground)-min(cx_flood, cx_ground))/2)
            cy_middle = min(cy_flood, cy_ground) + int((max(cy_flood, cy_ground)-min(cy_flood, cy_ground))/2)
            cv2.circle(image, (cx_middle, cy_middle), 10, (0,0,0), -1)
            cv2.line(image, (cx_flood, cy_flood), (cx_ground, cy_ground), (0,255,0), 1)

           
            
            # BEGIN CONTROL
            err_x = cx_middle - w/2
            err_y = cy_middle - h/2
            
            #print("err_x: ", err_x, "err_y: ", err_y)
            
            self.twist.linear.x = -float(err_y)/300.0 - 1.0
            self.twist.linear.y = -float(err_x)/85.0
            self.twist.linear.z = 0 #-1.1
            #vel_x = -float(err_y)/300.0 + 1.0
            #vel_y = -float(err_x)/85.0
            self.twist.angular.z = -float(math.atan2((cy_flood - cy_ground),(cx_flood - cx_ground)))*1.8
            
            self.cmd_vel_pub.publish(self.twist)

        elif M_flood['m00'] > 0 and M_ground['m00'] <= 0 and M_ground['m10'] <= 0:
            print('lost_ground')
            cx_flood = int(M_flood['m10']/M_flood['m00'])
            cy_flood = int(M_flood['m01']/M_flood['m00'])
            cv2.circle(image, (cx_flood, cy_flood), 10, (0,0,255), -1)
            self.twist.linear.x = 0.0
            self.twist.linear.y = 0.0
            self.twist.linear.z = 0.8
            self.cmd_vel_pub.publish(self.twist)
        elif M_flood['m00'] <= 0 and M_flood['m10'] <= 0 and M_ground['m00'] > 0:
            print('lost_flood')
            cx_ground = int(M_ground['m10']/M_ground['m00'])
            cy_ground = int(M_ground['m01']/M_ground['m00'])
            cv2.circle(image, (cx_ground, cy_ground), 10, (255,0,0), -1)
            self.twist.linear.x = 0.0
            self.twist.linear.y = 0.0
            self.twist.linear.z = 0.8
            self.cmd_vel_pub.publish(self.twist)

        else:
            self.twist.linear.x = 0.0
            self.twist.linear.y = 0.0
            self.twist.linear.z = 0.0
            self.twist.angular.z = 0.0
            self.cmd_vel_pub.publish(self.twist)
            print("else")
            
        #cv2.imshow("mask_flood",mask_flood)
        #cv2.imshow("mask_ground", mask_ground)
        cv2.imshow("d2", image)
        cv2.waitKey(3)
    

    def callback(self, data):
                
        drone01 = data.pose[idx[0]]
        drone01_vel = data.twist[idx[0]]
        d01_posX = drone01.position.x
        d01_posY = drone01.position.y
        d01_posZ = drone01.position.z
        d01_velX = drone01_vel.linear.x
        d01_velY = drone01_vel.linear.y

        drone02 = data.pose[idx[1]]
        drone02_vel = data.twist[idx[1]]
        d02_posX = drone02.position.x
        d02_posY = drone02.position.y
        d02_posZ = drone02.position.z
        d02_velX = drone02_vel.linear.x
        d02_velY = drone02_vel.linear.y


        if d01_posZ >= 2 and d02_posZ >= 2:
            dist = math.sqrt((d01_posX-d02_posX)**2 + (d01_posY-d02_posY)**2)
            if dist <= 2.5:
                new_velX = -2.0*d02_velX
                new_velY = -2.0*d02_velY
            else:
                new_velX = 0
                new_velY = 0
            '''
            repuls_x, repuls_y = calc_repulsive_potential(d02_posX, d02_posY, d01_posX, d01_posY)
            if 
            new_velX =  -repuls_x
            new_velY =  -repuls_y
            '''
        else:
            new_velX =  0
            new_velY =  0
        
        pub = self.cmd_vel_pub
        vel_msg_z = Twist()

        calc_odom_d02 = (Vector3(new_velX,new_velY,-3*(d02_posZ-3)))
        pub.publish(Twist(calc_odom_d02, Vector3(0,0,0)))
        
        print('position control now')
        rospy.Rate(1).sleep
    

def listener():
    rospy.init_node('d_2')
    follower = Follower()
    rospy.spin()

if __name__ == '__main__':
    try:
        listener()
    except rospy.ROSInterruptException:
        pass
# END ALL
