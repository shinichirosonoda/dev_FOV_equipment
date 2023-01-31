from ids_camera import *
import cv2
import argparse
from get_fov import Get_Angle_data, data_save_init,\
                    data_save_add, data_save_to_file,\
                    Get_Angle
import time

# draw_ch setting
parser = argparse.ArgumentParser(description='draw option')
parser.add_argument('-draw_ch', help='draw ch', default='-1') 
args = parser.parse_args()

# camera setting
def camera_set(camera_list):
    def camera_set():
        camera.setup_all()
        camera.set_default_color_mode()
        camera.cam_imgmemory()
        cam_param = camera.inquire_img_mem()
        print(cam_param)
        camera.set_aoi(0, 0, cam_param[0], cam_param[1])
        camera.fps = 30
        camera.exposure = 100
        #camera.set_trigger()
        camera.set_rgb_gain(100, 100, 100)
        camera.set_gain_factor(2400, 100, 100, 100)
        camera.master_gain = 100# 1.92x

        print("gain factor", camera.get_gain_factor())
        print('inquire gain factor', camera.inquire_gain_factor())
        print("camera fps : ", camera.fps)
        print('color mode : ', camera.color_mode)
        print('rgb gain    : ', camera.get_rgb_gain())
        print('inquire gain factor', camera.inquire_gain_factor())
    
        camera.exposure = 100

        camera.livemode(wait=True)

    for camera in camera_list:
        if camera.camera_id == 5:
            camera_set()

# capture and files create
def freeze_capture(camera_list, iter = 1):
    sample_name = input("Sample Name ? ")
    for i in range(iter):
        for camera in camera_list:
            if camera.camera_id == 5:
                 #frame = camera.triggered_capture()
                 frame = np.copy(camera.capture())
                 frame, _ = Get_Angle_data(frame)
                 cv2.imwrite("./data/img_%d_%d_%s.png" % (camera.camera_id, i, str(sample_name)), frame)
                 camera.stop()

def video_capture(camera_list):
    for camera in camera_list:
        while camera.camera_id == int(args.draw_ch) and int(args.draw_ch) == 5:
            #frame = camera.triggered_capture()
            frame = np.copy(camera.capture())
            frame, _, _, _ = Get_Angle_data(frame)
            dst = cv2.resize(frame, dsize=None, fx=0.5, fy=0.5)
            cv2.imshow("draw_ch="+args.draw_ch, dst)

            if cv2.waitKey(100) & 0xFF == ord('q'):
                sample_name = input("Sample Name ? ")
                cv2.imwrite("./data/img_%d_%s.png" % (camera.camera_id, str(sample_name)), frame)
                camera.stop()
                exit

def video_capture_logging(camera_list, interval = 1):
    for camera in camera_list:
        df = data_save_init()    # save data initialize
        dt_now = time.time()
        dt_now_ref = dt_now
        i = 0
        while camera.camera_id == int(args.draw_ch) and int(args.draw_ch) == 5:
            #frame = camera.triggered_capture()
            frame = np.copy(camera.capture())
            frame, flag ,x_data, y_data  = Get_Angle_data(frame)
            dst = cv2.resize(frame, dsize=None, fx=0.5, fy=0.5)
            cv2.imshow("draw_ch="+args.draw_ch, dst)
            print (x_data, y_data)

            if time.time() > dt_now_ref + interval:
                if flag == True:
                    V = np.concatenate([x_data, y_data], 0)    # get data
                else:
                    V = np.zeros(6)    # data is zero

                df = data_save_add(df, i, dt_now, V, max_num=190)    # save data add
                i += 1
                dt_now_ref = time.time()

            if cv2.waitKey(100) & 0xFF == ord('q'):
                sample_name = input("Sample Name ? ")
                # save image data to file
                cv2.imwrite("./data/img_%d_%s.png" % (camera.camera_id, str(sample_name)), frame)
                # save data to file
                data_save_to_file(df,file_name="./data/img_%d_%s.csv" % (camera.camera_id, str(sample_name))) 
                camera.stop()
                cv2.destroyAllWindows()
                exit()

def video_capture_logging2(camera_list, interval = 1):
    for camera in camera_list:
        df, dt_now_ref, dt_now, i = camera_1st_step()

        while camera.camera_id == int(args.draw_ch) and int(args.draw_ch) == 5:
            frame , df, i = camera_2nd_step(camera, df, dt_now_ref, dt_now, i, interval)

            if cv2.waitKey(100) & 0xFF == ord('q'):
                camera_3rd_step(camera, frame, df)
                cv2.destroyAllWindows()
                exit()

def camera_1st_step():
    df = data_save_init()    # save data initialize
    dt_now = time.time()
    dt_now_ref = dt_now
    i = 0
    return df, dt_now_ref, dt_now, i

def camera_2nd_step(camera, df, dt_now_ref, dt_now, i, interval):
    frame = np.copy(camera.capture())
    frame, flag ,x_data, y_data  = Get_Angle_data(frame)
    dst = cv2.resize(frame, dsize=None, fx=0.5, fy=0.5)
    cv2.imshow("draw_ch="+args.draw_ch, dst)
    print (x_data, y_data)

    if time.time() > dt_now_ref + interval:
        if flag == True:
            V = np.concatenate([x_data, y_data], 0)    # get data
        else:
            V = np.zeros(6)    # data is zero

        df = data_save_add(df, i, dt_now, V, max_num=190)    # save data add
        i += 1
        dt_now_ref = time.time()
    return  frame , df, i

def camera_3rd_step(camera, frame, df):
    sample_name = input("Sample Name ? ")
    # save image data to file
    cv2.imwrite("./data/img_%d_%s.png" % (camera.camera_id, str(sample_name)), frame)
    # save data to file
    data_save_to_file(df,file_name="./data/img_%d_%s.csv" % (camera.camera_id, str(sample_name))) 
    camera.stop()

if __name__ == "__main__":
    camera_list = IDS_Camera.find_cameras()
    print(camera_list)
        
    camera_set(camera_list)
    #video_capture_logging(camera_list)
    video_capture_logging2(camera_list)
    #video_capture(camera_list)
    #freeze_capture(camera_list)
