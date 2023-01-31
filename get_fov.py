# Deriving Angle Value by using High-precision amplitude evaluation device

import cv2
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime

from fov_logging import data_save_init, data_save_add, data_save_to_file

# edge detection module
def cal_edge(img, th, axis=0, min_value=15, print_flag=False):
    if axis == 0:
        x = np.array(range(img.shape[1]))
    elif axis == 1:
        x = np.array(range(img.shape[0]))
    else:
        return

    y = np.average(img, axis = axis)
    if np.max(y) > min_value:
        y = y/np.max(y)
    else:
        y = y * 0
    
    flag  = True
    
    edge0 = np.where((y > th[0]) & (y < th[1]))[0]
    edge1 = np.where((y > th[2]) & (y < th[3]))[0]

    if len(edge0) == 0 or len(edge1) == 0:
        flag = False
    else: 
        edge0 = edge0[0]
        edge1 = edge1[-1]

    if print_flag: 
        print(edge0, edge1)
    
    return (edge0, edge1), flag

# x,y edge detection
def detect_edge(img, th, area):
    img_x = img[area[0]:area[1],:]
    img_y = img[:,area[2]:area[3]]
    
    edge_x, flag0 = cal_edge(img_x, th, axis=0)
    edge_y, flag1 = cal_edge(img_y, th, axis=1)

    return {"edge_x":edge_x, "edge_y":edge_y}, flag0 * flag1

# camera calibration
def X_Pixel_To_Lx(px):
    return 5*10**-6 * px**2 + 0.3703 *px - 583.05

def Y_Pixel_To_Ly(px):
    return 0.3825 *px - 388.46

def Pixel_To_L(func, px):
    return func(px)

# distance between 
def L_To_Angle(L, Lz=400):
    return np.rad2deg(np.arctan(L/ Lz))    

# cal_func : calibration function length = func(px)
# Lz: distance between the screen and the MEMS mirror
# ignore: ignore area of ROI
# area: ROI for calculation
# th; threshold(xmin, xmax, ymin, ymax) 

processing_params = {"cal_func": (X_Pixel_To_Lx, Y_Pixel_To_Ly),\
                     "Lz": 400,\
                     "ignore": [900,1110,1410,1650],\
                     "area" : (1010,1020,1525,1535),\
                     "th": (0.2,0.8,0.2,0.8)}

# get angle
def Get_Angle(img, axis=0, params=processing_params):
    cal_func = params["cal_func"]
    Lz = params["Lz"]
    ignore = params["ignore"]
    area = params["area"]
    th = params["th"]
    
    img[ignore[0]:ignore[1], ignore[2]:ignore[3]] = 0
    data, flag = detect_edge(img, th, area)

    if axis == 0 and flag == True:
        Lx_low, Lx_high = Pixel_To_L(cal_func[0], data["edge_x"][0]),\
                          Pixel_To_L(cal_func[0], data["edge_x"][1])
        
        return (L_To_Angle(Lx_low, Lz=Lz),\
               L_To_Angle(Lx_high, Lz=Lz),\
               -L_To_Angle(Lx_low, Lz=Lz) + L_To_Angle(Lx_high, Lz=Lz)), flag

    elif axis == 1 and flag == True:
        Ly_low, Ly_high = Pixel_To_L(cal_func[1], data["edge_y"][0]),\
                          Pixel_To_L(cal_func[1], data["edge_y"][1])
        
        return (L_To_Angle(Ly_low, Lz=Lz),\
               L_To_Angle(Ly_high, Lz=Lz),\
               -L_To_Angle(Ly_low, Lz=Lz) + L_To_Angle(Ly_high, Lz=Lz)), flag

    else:
        return (0.0, 0.0, 0.0), flag

# get angle data
def Get_Angle_data(img, params=processing_params):
    data_x, flag0 = Get_Angle(img, axis=0, params=params)
    data_y, flag1 = Get_Angle(img, axis=1, params=params)

    
    str_x = "X_angle = {}, {}, {}".format(format(data_x[0], ".1f"),
                                              format(data_x[1], ".1f"), 
                                              format(data_x[2], ".1f"))
    str_y = "Y_angle = {}, {}, {}".format(format(data_y[0], ".1f"),
                                              format(data_y[1], ".1f"), 
                                              format(data_y[2], ".1f"))

    img = img.copy()
    
    cv2.putText(img,
                text= str_x,
                org=(100, 200),
                fontFace=cv2.FONT_HERSHEY_SIMPLEX,
                fontScale=4.0,
                color=(255, 255, 255),
                thickness=10,
                lineType=cv2.LINE_4)
    
    cv2.putText(img,
                text= str_y,
                org=(100, 400),
                fontFace=cv2.FONT_HERSHEY_SIMPLEX,
                fontScale=4.0,
                color=(255, 255, 255),
                thickness=10,
                lineType=cv2.LINE_4)
    
    return img, flag0 * flag1, data_x, data_y

def overlay(img, data):
    
    str_x = "X_angle = {}, {}, {}".format(format(data[0], ".1f"),
                                          format(data[1], ".1f"), 
                                          format(data[2], ".1f"))
    str_y = "Y_angle = {}, {}, {}".format(format(data[3], ".1f"),
                                          format(data[4], ".1f"), 
                                          format(data[5], ".1f"))
    
    img = img.copy()
    
    cv2.putText(img,
                text= str_x,
                org=(100, 200),
                fontFace=cv2.FONT_HERSHEY_SIMPLEX,
                fontScale=4.0,
                color=(255, 255, 255),
                thickness=10,
                lineType=cv2.LINE_4)
    
    cv2.putText(img,
                text= str_y,
                org=(100, 400),
                fontFace=cv2.FONT_HERSHEY_SIMPLEX,
                fontScale=4.0,
                color=(255, 255, 255),
                thickness=10,
                lineType=cv2.LINE_4)
    
    return img

def normal_test(file_name = "test.png", params=processing_params):
    # file
    file = "./data/" + file_name

    img0 = cv2.cvtColor(cv2.imread(file, 1), cv2.COLOR_BGR2GRAY)
    img1 = cv2.imread(file, 1)[:,:,::-1]

    # select filename
    plt.gray()
    plt.title("gray image")
    plt.imshow(img0)
    plt.show()
    
    # Overlay
    img1, flag, x, y = Get_Angle_data(img1, params=params)
    print("flag, x, y = ", flag, x, y)    
    plt.title("Overray")
    plt.imshow(img1)
    plt.show()

def average_test(file_name = "test.png"):
    # file load
    file = "./data/" + file_name
    img_array = []
    for i in range(10):
        img_array.append(cv2.imread(file, 1)[:,:,::-1])

    num_average = 5                                    # num_average
    M = np.zeros((num_average, 6))                     # data strage Matrix

    df = data_save_init()                              # save data initialize
    
    for i in range(10):
        dt_now = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
        M = np.roll(M, -1 ,axis=0)                     # data shift
        img = img_array[i]                             # image input
        x_data, flag0 = Get_Angle(img, axis=0)         # get x_data
        y_data, flag1 = Get_Angle(img, axis=1)         # get y_data
        
        if flag0 * flag1 == True:
            V_in = np.concatenate([x_data, y_data], 0) # get data
            M[-1][:] = V_in                            # data input
            V_out = np.average(M, axis=0)              # data average
        else:
            V_out = np.zeros(6)                        # data is zero

        df = data_save_add(df, i, dt_now, V_out)       # save data add
        img = overlay(img, V_out)                      # image overlay

        plt.title("Average Test")
        plt.imshow(img)
        plt.show()

    data_save_to_file(df)                              # save data to file

if __name__ == '__main__':
    processing_params = {"cal_func": (X_Pixel_To_Lx, Y_Pixel_To_Ly),\
                         "Lz": 400,\
                         "ignore": [900,1110,1410,1650],\
                         "area" : (1010,1020,1525,1535),\
                         "th": (0.2,0.8,0.2,0.8)}
    
    normal_test(params=processing_params)
    #average_test()