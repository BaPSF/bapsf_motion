'''
Motor_Control_2D controls two motors (x and y), using Single_Motor_Control
In this case, the x motor moves in x direction and y motor moves in y direction.

Modified by: Yuchen Qian
Oct 2017
Modified by: Rishabh Singh
Nov 2021
'''

import math
from Single_Motor_Control import Motor_Control
import time
import numpy as np
from scipy.optimize import fsolve

#############################################################################################
#############################################################################################


class Motor_Control_2D:

    def __init__(self, x_ip_addr = None, y_ip_addr = None):

        self.x_mc = Motor_Control(verbose=True, server_ip_addr= x_ip_addr)
        self.y_mc = Motor_Control(verbose=True, server_ip_addr= y_ip_addr)

        self.steps_per_cm = 39370.0787402 #velmex e02 has 0.02 in/rev .

        self.motor_moving = False

        self.d_outside = 124.4 #cm distance from the ball valve to the motor's motion channel
        #measured dec 14, 2metre stick
        self.d_inside = 64.0 #cm distance from the ball valve to the center of the chamber (0,0) point
        self.d_offset = 20.7 #cm
        self.alpha = -0.9*np.pi/180 #rad
        self.x_mc.steps_per_rev(20000)
        self.y_mc.steps_per_rev(20000)


    def move_to_position(self, x, y):
        # Directly move the motor to their absolute position
        a = self.d_outside
        b = self.d_inside
        
        alpha = self.alpha
        #dy = P*L^3/(E*3/2*pi*r^4) for load (castigliano's method) P, = KL^4/(E*8/2*pi*r^4) for self weight. K = density*A*g
       #self-weight deflection from cns.gatech.edu/~predrag/GTcourses/PHYS-4421-04/lautrup/2.8/rods.pdf [pg 166]
        #r =1.9cm E = 195*10^9 Pa, density = 7970 kg/m^3
        c = np.sqrt(x**2  + y**2)
        # deflection differential  from cns.gatech.edu/~predrag/GTcourses/PHYS-4421-04/lautrup/2.8/rods.pdf [pg 166]
         # E = 205*10^9 Pa, density = 7970 kg/m^3
        P = 0.040*9.81 #kg load at end
        E = 190*(10**9) #Pa
        r = 0.0046625 #m
        r2 = 0.00394
        density = 7990 #kg/m^3
        g = 9.81 #m/s^2
        K = density*np.pi*(r**2)*g
        I = np.pi*(r**4 - r2**4)/2

        if x == 0:
             phi = np.pi/2
        elif x<0:
            phi = math.atan(y/x) + np.pi
        else:
             phi = math.atan(y/x)

        l2 = (b**2 +c**2 + 2*b*c*math.cos(phi))**0.5
        L = l2/100 
        
        # dy_selfweight = 100*K*(L**4)/(E*8*I) - 100*K*((b/100)**4)/(E*8*I)
        # dy_weight = 100*P*(L**3)/(E*1.5*np.pi*(r**4-r2**4)) -100*P*((b/100)**3)/(E*1.5*np.pi*(r**4-r2**4))
        
        if y>=0:
             theta = math.atan( np.abs(y)/(b+x) )
        else:
             theta = math.atan( np.abs(y)/(b+x) ) 
             
        L = L*np.cos(theta)

        dy_total = 100*(  
            
            (  (L**3)/(4*E*I) )*(2*P + K*L) + (L**3/(6*E*I))*(-P-K*L) + K*(L**4)/(24*E*I) 
           
            -(
                        
            (  ((b/100)**3)/(4*E*I) )*(2*P + K*((b/100)) ) + ((b/100)**3/(6*E*I))*(-P-K*(b/100)) + K*((b/100)**4)/(24*E*I) 
           
              )
                    
                      )



        ########y-corr.
        y = y + 1*(dy_total)
        
        
        if x == 0:
            phi = np.pi/2
        elif x<0:
            phi = math.atan(y/x) + np.pi
        else:
            phi = math.atan(y/x)

        c = np.sqrt(x**2  + y**2)
        if y>=0:
            theta = math.atan( np.abs(y)/(b+x) ) + alpha + math.atan(0.005*(np.abs(y)**0.9)/184.4)
        else:
            theta = math.atan( np.abs(y)/(b+x) ) - alpha + math.atan(0.051*(np.abs(y)**0.8)/184.4)


        l2 = (b**2 +c**2 + 2*b*c*math.cos(phi))**0.5

        l1 = a/math.cos(theta)

        # x_new = l1 + l2 - a/math.cos(alpha) -b - (a)*(1/math.cos(theta) -1/math.cos(alpha)) #+ (math.tan(theta))

        if y>=0:
            y_new = -1*(l1*math.sin(theta)- self.d_offset*(1/math.cos(alpha)-1/math.cos(theta)) - a*math.tan(alpha))
            x_new = l1 + l2 - a/math.cos(alpha) -b - (a)*(1/math.cos(theta) -1/math.cos(alpha)) + 0.7*(math.tan(theta -alpha))
        else:
            y_new = l1*math.sin(theta) + self.d_offset*(1/math.cos(alpha)-1/math.cos(theta)) +a*math.tan(alpha)
            x_new = l1 + l2 - a/math.cos(alpha) -b - (a)*(1/math.cos(theta) -1/math.cos(alpha)) - 0.7*(math.tan(theta - alpha))
        
        x_step = self.cm_to_steps(x_new)
        y_step = self.cm_to_steps(y_new)
        self.x_mc.set_position(x_step)
        self.y_mc.set_position(y_step)
        self.motor_moving = True
        self.wait_for_motion_complete()


#--------------------------------------------------------------------------------------------------


    def stop_now(self):
        # Stop motor movement now
        self.x_mc.stop_now()
        self.y_mc.stop_now()


    def set_zero(self):
        self.x_mc.set_zero()
        self.y_mc.set_zero()


    def reset_motor(self):
        self.x_mc.reset_motor()
        self.y_mc.reset_motor()


#--------------------------------------------------------------------------------------------------


    def ask_velocity(self):
        self.speedx = self.x_mc.motor_velocity()
        self.speedy = self.y_mc.motor_velocity()
        return self.speedx, self.speedy

    def set_velocity(self, vx, vy):
        self.x_mc.set_speed(vx)
        self.y_mc.set_speed(vy)


#-------------------------------------------------------------------------------------------



    def cm_to_steps(self, d:float) -> int:
        # convert distance d in cm to motor position
        return int(d * self.steps_per_cm)

    # def degree_to_steps(self, d:float) -> int: # This feature applies to Z-Th probe drive
    #     # convert angle d in degree to motor position
    #     return int(d * self.steps_per_degree)

#-------------------------------------------------------------------------------------------



    def current_probe_position(self):
        # Obtain encoder feedback and calculate probe position
        """ Might need a encoder_unit_per_step, if encoder feedback != input step """
        mx_pos = self.x_mc.current_position() / self.steps_per_cm *5
        my_pos = self.y_mc.current_position() / self.steps_per_cm *5 #Seems that 1 encoder unit = 5 motor step unit
        a = self.d_outside
        b = self.d_inside
        
        if my_pos <0:
            C = np.abs(my_pos) - a*np.tan(self.alpha) - self.offset/np.cos(self.alpha)
        
        
            def func(x):
                return a*np.tan(x) + self.offset/np.cos(x) - 50
        
            theta = fsolve(func, 0)
            x = (b+mx_pos)*np.cos(theta)
            y = (b+mx_pos)*np.sin(theta)
        
            return x, y
        
        else: 
            C = np.abs(my_pos) + a*np.tan(self.alpha) + self.offset/np.cos(self.alpha)
        
        
            def func(x):
                return a*np.tan(x) - self.offset/np.cos(x) - 50
        
            theta = fsolve(func, 0)
            x = (b+mx_pos)*np.cos(theta)
            y = (b+mx_pos)*np.sin(theta)
        
            return x, y
        

#-------------------------------------------------------------------------------------------


    def wait_for_motion_complete(self):

        timeout = time.time() + 300

        while True :

            x_stat = self.x_mc.check_status()
            y_stat = self.y_mc.check_status()
            time.sleep(0.2)

            x_not_moving = x_stat.find('M') == -1
            y_not_moving = y_stat.find('M') == -1


#                print ('x:', x_stat)
#                print ('y:', y_stat)
#                print ('z:', z_stat)
#                print (x_not_moving, y_not_moving, z_not_moving)

            if x_not_moving and y_not_moving:
                break
            elif time.time() > timeout:
                raise TimeoutError("Motor has been moving for over 5min???")
        self.motor_moving = False
        print ("Motor stopped")


#-------------------------------------------------------------------------------------------
    #def translate_Coord(self,x,y):


    def disable(self):
        self.x_mc.inhibit()
        self.y_mc.inhibit()

    def enable(self):
        self.x_mc.enable()
        self.y_mc.enable()

    def set_input_usage(self, usage):
        self.x_mc.set_input_usage(usage)
        self.y_mc.set_input_usage(usage)



########################################################################################################
# standalone testing:

if __name__ == '__main__':
    pass
    # mc = Motor_Control_2D(x_ip_addr = "192.168.0.50", y_ip_addr = "192.168.0.40")
    # mc.current_probe_position()
    # mc.reset_motor()
#    mc.move_to_position(0,0,0)
#    mc.move(0,0,0)
#    print (mc.motor_to_probe)
#    mc.set_zero()

#    mc.calculate_motor(-5,5,-11)
