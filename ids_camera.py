# -*- coding: utf-8 -*-
"""IDS社のカメラのpythonバインディング ueyeのラッパーです。

Todo:

 * multi AOIは未実装
 * ドキュメントが未整備

Notes:
    https://github.com/jkokorian/ids-pyueye/blob/master/pyueye/ueye.py

"""
 
from pyueye import ueye
import numpy as np
import copy
import ctypes
import time

class IDS_Camera():
    """ IDSカメラドライバ

    IDS社の産業用カメラのpythonラッパーです。
    公式のpyueyeクラスをモジュール化しています。

    Attributes:
        hCam (ueye.HIDS): カメラのC++ハンドラです。 
        x(int): 撮影の開始x座標
        y(int): 撮影の開始y座標

    Notes:
        https://jp.ids-imaging.com/manuals/ids-software-suite/ueye-manual/4.95/ja/index.html

    """

    @classmethod
    def get_number_of_cameras(cls):
        """接続されているカメラの台数

        PC に接続している uEye カメラの台数を返します。
        Args:
            なし
        Returns:
            int : IDS_Cameraの台数

        Examples:

            >>> IDS_Camera.get_number_cameras()
               1

        Note:
               https://jp.ids-imaging.com/manuals/ids-software-suite/ueye-manual/4.95/ja/is_getnumberofcameras.html
         """
        num_cameras = ueye.int()
        n_ret = ueye.is_GetNumberOfCameras(num_cameras)
        return num_cameras.value

    @classmethod
    def find_cameras(cls):
        """接続されているカメラ

        接続されいているすべてのカメラのインスタンスを返します。
        クラスメソッドなのでインスタンス化する必要はありません。

        Args:
            なし
        Returns:
            IDS_Cameraのインスタンスの配列

        Examples:

            >>> IDS_Camera.find_cameras()
               [<ids_camera.IDS_Camera object at 0x000001912ABD0040>]

        Note:
            ueye.is_GetCameraList()を使えばカメラリストの情報がとれるはずですが、未実装です。

        """
        return [IDS_Camera(i) for i in range(cls.get_number_of_cameras())]
        # pucl = ueye.UEYE_CAMERA_LIST()
        # ueye.is_GetCameraList(pucl)
        # for i in range(pucl.dwCount.value):
        #     print('camera', i)# FIXME
        # return pucl

    def __init__(self, camera_id):
        """
        # self.hCam = ueye.HIDS(camera_id)             
        # 0: first available camera;
        # 1-254: The camera with the specified camera ID
        """
        camera_id += 1
        hCam = ueye.HIDS(camera_id) # Camera handler
        n_ret = ueye.is_InitCamera(hCam, None)
        self._check(n_ret, "is_InitCamera ERROR")
        self.hCam = hCam
        self.camera_id = camera_id
        self.pitch = ueye.INT()
        self._s_info = None
        self._cam_info = None
        self.x = 0
        self.y = 0
        self.max_w, self.max_h = self.max_image_size
        self.width = ueye.int(self.max_w)
        self.height = ueye.int(self.max_h)
        self._sensor_color_mode = None

    @property
    def fps(self):
        """fps (frame per second)
        実際にキャプチャされた 1 秒毎のフレーム数を返します。
        propertyであるため呼び出しにかっこは不要です。

        Args:
            なし

        Returns:
            float : カメラの実際のfps
IDSCamera

            >>> camera.fps
                35.400862
        """
        fps = ueye.double()
        n_ret = ueye.is_GetFramesPerSecond(self.hCam, fps)
        self._check(n_ret, "is_GetFramesPerSecond")
        return fps.value

    @fps.setter
    def fps(self, _fps):
        """
         フレームレートの変更
        カメラのフレームレート目標を設定します。
        露光時間やメモリへの転送速度によりフレームレートは設定どおりにならないことがあります。
        実際にキャプチャされた 1 秒毎のフレーム数を返します。

        Args:
            なし

        Raises:
            uEyeException: 送信したパラメータのうちいずれかが有効な範囲外であるか、
                           このセンサーに対応していないか、あるいはこのモードでは使用できません。

        Returns:
            float : カメラの実際のfps

        Examples:

            >>> camera.fps = 80
                35.400862
        """
        new_fps = ctypes.c_double()
        n_ret = ueye.is_SetFrameRate(self.hCam, ueye.double(_fps), new_fps)
        self._check(n_ret, "fps setter")
        return new_fps.value
    
    @property
    def exposure(self):
        """
        Args:
            なし

        Returns:
            float : 露光時間(mili seconds)

        Examples:

            >>> camera.exposure
               ? 
        Notes:

            https://jp.ids-imaging.com/manuals/ids-software-suite/ueye-manual/4.95/ja/is_exposure.html
        """
        n_ret = ueye.is_Exposure(self.hCam,
                                 ueye.IS_EXPOSURE_CMD_GET_EXPOSURE,
                                 None,
                                 0
                                 )

    @exposure.setter
    def exposure(self, exp_time):
        """
        露出時間の変更
        Args:
            露光時間

        Returns:
            なし

        Examples:

            >>> camera.exposure = 10
               ? 
        Notes:

            https://jp.ids-imaging.com/manuals/ids-software-suite/ueye-manual/4.95/ja/is_exposure.html
        """
        ms = ctypes.c_double(exp_time)

        n_ret = ueye.is_Exposure(self.hCam,
                                 ueye.IS_EXPOSURE_CMD_SET_EXPOSURE,
                                 ms,
                                 ueye.sizeof(ms))
        self._check(n_ret, "error in is_exposure")
        return ms.value
    
    def set_auto_parameter(self):
        """
        自動露光シャッター、オートゲイン、ブラックレベルといった自動制御の設定を行います。

        Examples:
            >>> camera.set_auto_parameter()

        Notes:

            https://jp.ids-imaging.com/manuals/ids-software-suite/ueye-manual/4.95/ja/is_autoparameterautowhite.html

        # nSupportedTypesの値が"3"？ : 仕様に無い。。。
        # nRet = ueye.is_AutoParameter(self.hCam, ueye.IS_AWB_CMD_GET_SUPPORTED_TYPES, nSupportedTypes, ctypes.sizeof(ctypes.create_string_buffer(4)))
        # nRet = ueye.is_AutoParameter(self.hCam, ueye.IS_AWB_CMD_GET_TYPE, nSupportedTypes, ctypes.sizeof(ctypes.create_string_buffer(4)))
        """
        nEnable = ctypes.c_uint(ueye.IS_AUTOPARAMETER_DISABLE)
        nRet1 = ueye.is_AutoParameter(self.hCam,
                                      ueye.IS_AWB_CMD_SET_ENABLE,
                                      nEnable,
                                      ctypes.sizeof(nEnable))

        nSupportedTypes = ctypes.c_uint()
        nRet2 = ueye.is_AutoParameter(self.hCam,
                                      ueye.IS_AWB_CMD_GET_ENABLE,
                                      nSupportedTypes,
                                      ctypes.sizeof(ctypes.create_string_buffer(4)))
        if nRet1==0 & nRet2==0 & nSupportedTypes.value==0:
            print("is_AutoParameter OK")

    def cam_autofocus(self):
        """
        UI-3080CP : オートフォーカス非対応 : CheckCode

        Notes:

            # print("autofocus_is_none", nRet, uiCaps, ueye.FOC_CAP_AUTOFOCUS_SUPPORTED.value)
        """
        uiCaps = ctypes.c_uint()
        n_ret = ueye.is_Focus(self.hCam,
                              ueye.FOC_CMD_GET_CAPABILITIES,
                              uiCaps,
                              ctypes.sizeof(ctypes.create_string_buffer(4)))
        self._check(n_ret, "auto_focus mode")

    @property
    def cam_info(self):
        """
        
        Examples:
            >>> c_info = camera.cam_info.get_caminfo()
            >>> c_info.SerNo # returns serial number in bytes
                b'4104043710'
            >>> c_info.Date
                b'16.08.2021'
        
        Notes:
            
            Reads out the data hard-coded in the non-volatile camera memory and writes it to the data structure that cInfo points to
            [HP] カメラの固定 ID、カメラのタイプ、またはセンサー ID で識別することをお勧めします - is_getcameralist()
            https://jp.ids-imaging.com/manuals/ids-software-suite/ueye-manual/5.95/ja/is_getcamerainfo.html?q=getcamerainfo
        """
        if self._cam_info == None:
            self._cam_info = ueye.CAMINFO()
            n_ret = ueye.is_GetCameraInfo(self.hCam, self._cam_info)
            self._check(n_ret, "is_GetCameraInfo ERROR")
        return self._cam_info
    
    @property
    def sensor_info(self):
        """

        Examples:
            >>> camera.sensor_info
                struct SENSORINFO {
                    SensorID [c_ushort] = 561;
                    strSensorName [c_char_Array_32] = b'UI308xCP-C';
                    nColorMode [c_char] = b'\x02';
                    nMaxWidth [c_uint] = 2456;
                    nMaxHeight [c_uint] = 2054;
                    bMasterGain [c_int] = 1;
                    bRGain [c_int] = 1;
                    bGGain [c_int] = 1;
                    bBGain [c_int] = 1;
                    bGlobShutter [c_int] = 1;
                    wPixelSize [c_ushort] = 345;
                    nUpperLeftBayerPixel [c_char] = b'\x00';
                    Reserved [c_char_Array_13] = b'';
                };
            >>> camera.sensor_info.nMaxWidth.value
                2456

        Notes:

        # You can query additional information about the sensor type used in the camera
        # https://jp.ids-imaging.com/manuals/ids-software-suite/ueye-manual/4.95/ja/is_getsensorinfo.html?q=getsensorinfo
        # print("Camera model:\t\t", self.sensor_info.strSensorName.decode('utf-8'))
        """
        if self._s_info == None:
            self._s_info = ueye.SENSORINFO()
            n_ret = ueye.is_GetSensorInfo(self.hCam, self._s_info)
            self._check(n_ret, "is_GetSensorInfo ERROR")
        return self._s_info
    
    def set_default(self):
        """
            すべてのパラメータを、ドライバで指定されているカメラ用のデフォルトにリセット
        Examples:
            >>> camera.set_default()

        Notes:

            # https://jp.ids-imaging.com/manuals/ids-software-suite/ueye-manual/4.95/ja/is_resettodefault.html?q=resettodefault
        """
        n_ret = ueye.is_ResetToDefault(self.hCam)
        self._check(n_ret, "is_ResetToDefault ERROR")
    
    def set_displaymode(self, dm_mode = ueye.IS_GET_DISPLAY_MODE):
        """
        メンテしていない
        画像の画面での表示方法を設定します。
        オーバーレイを含むライブビデオでは Direct3D または OpenGL モードが使用できます。
        グラフィックスカードによっては、これらのモードに対応していないものがあります。
        また、オーバーレイモードは現在のスクリーン解像度に必要なサイズまでの追加メモリが
        必要になるため、グラフィックスカードには十分な拡張メモリが必要になります。

        Examples:
            >>> camera.set_displaymode()
        Notes:

            Set display mode to DIB
            画像の画面での表示方法を設定する。
            ueye.IS_SET_DM_DIB : システムメモリに書き込む
            ueye.IS_GET_DISPLAY_MODE : 現在の設定を返す
            https://jp.ids-imaging.com/manuals/ids-software-suite/ueye-manual/4.95/ja/is_setdisplaymode.html?q=setdisplaymode
        """
        
        n_ret = ueye.is_SetDisplayMode(self.hCam, dm_mode)
        # self._check(n_ret, "is_SetDisplayMode ERROR")
        if dm_mode == ueye.IS_GET_DISPLAY_MODE:
            return n_ret

    def set_default_color_mode(self):
        """
        カメラのカラーモード（RGB、白黒）をもとに、メモリのカラーモードを設定します。

        Examples:
            >>> camera.set_default_color_mode()
        
        Set the right color mode
        """
        color_mode = self.sensor_color_mode
        if color_mode == ueye.IS_COLORMODE_BAYER:
            self.m_nColorMode = ueye.IS_CM_BGR8_PACKED
        elif color_mode == ueye.IS_COLORMODE_CBYCRY:
            self.m_nColorMode = ueye.IS_CM_BGR8_PACKED
        elif color_mode == ueye.IS_COLORMODE_MONOCHROME:
            self.m_nColorMode = ueye.IS_CM_MONO8
        else:
            self.m_nColorMode = ueye.IS_CM_MONO8
        self.nBitsPerPixel = ueye.INT(IDS_Camera.COLOR_MODE[self.m_nColorMode])
        self.bytes_per_pixel = int(self.nBitsPerPixel / 8)

    def set_hardware_trigger(self):
        """
        このモードが有効になると、カメラは is_FreezeVideo() (スナップ) の呼び出しで
        一回だけのトリガを待機します。カメラがトリガ信号を受信すると、画像を一枚だけキャプチャして転送します。
        https://jp.ids-imaging.com/manuals/ids-software-suite/ueye-manual/4.95/ja/hw_triggermodus.html
        """
        nTriggerMode = ueye.IS_SET_TRIGGER_LO_HI
        n_ret = ueye.is_SetExternalTrigger(self.hCam, nTriggerMode)
        self._check(n_ret, "is_SetExternalTrigger ERROR")

    def set_trigger(self): 
        """
        Set Trigger Mode
        Notes:
            https://jp.ids-imaging.com/manuals/ids-software-suite/ueye-manual/4.95/ja/is_setexternaltrigger.html
        """

        nTriggerMode = ueye.IS_SET_TRIGGER_LO_HI
        n_ret = ueye.is_SetExternalTrigger(self.hCam, nTriggerMode)
        self._check(n_ret, "is_SetExternalTrigger ERROR")

    def get_aoi(self):
        rect_aoi = ueye.IS_RECT()
        n_ret = ueye.is_AOI(self.hCam, 
                           ueye.IS_AOI_IMAGE_GET_AOI, 
                           rect_aoi, 
                           ueye.sizeof(rect_aoi))
        self._check(n_ret, "max_image_size AOI error")

        return rect_aoi

    @property
    def max_image_size(self):
        # Can be used to set the size and position of an "area of interest"(AOI) within an image
        max_w = self.sensor_info.nMaxWidth.value
        max_h = self.sensor_info.nMaxHeight.value
        # aoi = self.get_aoi()
        # width_full  = copy.copy(aoi.s32Width.value)
        # height_full = copy.copy(aoi.s32Height.value)
        return max_w, max_h

    def set_aoi(self, x, y, w, h):
        """
        画像 AOI の位置とサイズに対するグリッドの幅は、センサーによって異なります。
        画像 AOI の位置とサイズを定義する値は、必ず許容されたグリッド幅の整数の倍数
        である必要があります。個々のカメラモデルの AOI グリッドに関する詳細は、
        こちらで確認できます
        https://jp.ids-imaging.com/manuals/ids-software-suite/ueye-manual/4.95/ja/hw_sensoren.html

        たとえば、UI-308xの場合は、
        画像幅は256～2456でグリッド幅は8
        画像高さは2～2054でグリッド幅は2
        となります。
        https://jp.ids-imaging.com/manuals/ids-software-suite/ueye-manual/4.95/ja/camera-data-ui-308x.html

        """
        self.x = x
        self.y = y
        self.width = w
        self.height = h
        rect_aoi = self.get_aoi()
        rect_aoi.s32X = x
        rect_aoi.s32Y = y
        rect_aoi.s32Width = w
        rect_aoi.s32Height = h
        n_ret = ueye.is_AOI(self.hCam,
                            ueye.IS_AOI_IMAGE_SET_AOI,
                            rect_aoi,
                            ueye.sizeof(rect_aoi))
        self._check(n_ret, "is_AOI_2 ERROR")

        print("Camera serial no.:\t", self.cam_info.SerNo.decode('utf-8'))
        print("Set image [width, height]:\t", [rect_aoi.s32Width.value, rect_aoi.s32Height.value])

    def cam_aoi(self):
        if self.width > self.max_w:
            raise uEyeException("width(aoi) is larger than max : ", self.max_w)
        if self.height > self.max_h:
            raise uEyeException("height(aoi) is larger than max : ", self.max_h)
        self.set_aoi(
                     self.x,
                     self.y,
                     self.width,
                     self.height
        )


    def _gain_factor(self, cmd, factor):
        return ueye.is_SetHWGainFactor(self.hCam, cmd, factor)

    def get_gain_factor(self):
        return (self._gain_factor(ueye.IS_GET_MASTER_GAIN_FACTOR, 0),
                self._gain_factor(ueye.IS_GET_RED_GAIN_FACTOR, 0),
                self._gain_factor(ueye.IS_GET_GREEN_GAIN_FACTOR, 0),
                self._gain_factor(ueye.IS_GET_BLUE_GAIN_FACTOR, 0)
        )

    def inquire_gain_factor(self):
        return (self._gain_factor(ueye.IS_INQUIRE_MASTER_GAIN_FACTOR, 0),
                self._gain_factor(ueye.IS_INQUIRE_RED_GAIN_FACTOR, 0),
                self._gain_factor(ueye.IS_INQUIRE_GREEN_GAIN_FACTOR, 0),
                self._gain_factor(ueye.IS_INQUIRE_BLUE_GAIN_FACTOR, 0)
        )
    
    def set_gain_factor(self, master, red, green, blue):
        """IS_SET_..._GAIN_FACTOR でゲインを設定するには、
        nFactor パラメータを 100～最大値までの間の整数値で設定する必要があります。
        IS_INQUIRE_x_FACTOR を呼び出して nFactor に 100 の値を指定すると、
        最大値の問い合わせができます。100 という値はゲインなしを意味するので、
        例えばゲイン値が 200 であれば倍レベル (係数 2) だと分ります。
        https://jp.ids-imaging.com/manuals/ids-software-suite/ueye-manual/4.95/ja/is_sethwgainfactor.html
        """
        print('master', ueye.is_SetHWGainFactor(self.hCam, ueye.IS_SET_MASTER_GAIN_FACTOR, master))
        ueye.is_SetHWGainFactor(self.hCam, ueye.IS_SET_RED_GAIN_FACTOR, red)
        ueye.is_SetHWGainFactor(self.hCam, ueye.IS_SET_GREEN_GAIN_FACTOR, green)
        ueye.is_SetHWGainFactor(self.hCam, ueye.IS_SET_BLUE_GAIN_FACTOR, blue)

                    
    def set_rgb_gain(self, gain_r, gain_g, gain_b):
        # n_ret = ueye.is_SetHWGainFactor(self.hCam, ueye.IS_SET_RED_GAIN_FACTOR, gain_r)
        n_ret = ueye.is_SetHardwareGain(self.hCam,
                                        ueye.IS_IGNORE_PARAMETER,
                                        gain_r,
                                        gain_g,
                                        gain_b)
        self._check(n_ret, 'is_SetHardwareGain')

    def _get_gain(self, gain_param):
        n_ret = ueye.is_SetHardwareGain(self.hCam,
                                        gain_param,
                                        ueye.IS_IGNORE_PARAMETER,
                                        ueye.IS_IGNORE_PARAMETER,
                                        ueye.IS_IGNORE_PARAMETER)
        return n_ret
    
    def set_auto_gain(self):
        """オートゲイン機能を有効にします (is_SetAutoParameter() も参照)。
        オートゲイン機能を無効にするには、nMaster の値を設定します。
        """
        return self._get_gain(ueye.IS_SET_ENABLE_AUTO_GAIN)

    @property
    def default_master_gain(self):
        """デフォルトのマスターゲイン係数を返します。
        """
        return self._get_gain(ueye.IS_GET_DEFAULT_MASTER)

    @property
    def default_rgb_gain(self):
        """デフォルトのRGBゲイン係数を返します。
        """
        return (self._get_gain(ueye.IS_GET_DEFAULT_RED),
                self._get_gain(ueye.IS_GET_DEFAULT_GREEN),
                self._get_gain(ueye.IS_GET_DEFAULT_BLUE))

    @property
    def master_gain(self):
        return self._get_gain(ueye.IS_GET_MASTER_GAIN)
    
    @master_gain.setter
    def master_gain(self, gain):
        n_ret = ueye.is_SetHardwareGain(self.hCam,
                                        gain,
                                        ueye.IS_IGNORE_PARAMETER,
                                        ueye.IS_IGNORE_PARAMETER,
                                        ueye.IS_IGNORE_PARAMETER
                                        )
        self._check(n_ret, "master_gain setter")
    
    def get_rgb_gain(self):
        return (self._get_gain(ueye.IS_GET_RED_GAIN),
                self._get_gain(ueye.IS_GET_GREEN_GAIN),
                self._get_gain(ueye.IS_GET_BLUE_GAIN))

    def cam_imgmemory(self):
        """
        Allocates an image memory for an image having its dimensions defined by width and height
        and its color depth defined by nBitsPerPixel
        """
        self.pcImageMemory = ueye.c_mem_p()
        self.MemID = ueye.int()
        n_ret = ueye.is_AllocImageMem(self.hCam,
                                      self.width,
                                      self.height,
                                    #   self.rectAOI.s32Width,
                                    #   self.rectAOI.s32Height,
                                      self.nBitsPerPixel,
                                      self.pcImageMemory,
                                      self.MemID)
        self._check(n_ret, "is_AllocImageMem ERROR")
        # Makes the specified image memory the active memory
        n_ret = ueye.is_SetImageMem(self.hCam, self.pcImageMemory, self.MemID)
        self._check(n_ret, "cam_imgmemory")
        # if n_ret != ueye.IS_SUCCESS:
        #     print("is_SetImageMem ERROR")
        # else:
        n_ret = ueye.is_SetColorMode(self.hCam, self.m_nColorMode)
    
    SENSOR_COLOR_MODE = {
        ueye.IS_COLORMODE_MONOCHROME:1,
        ueye.IS_COLORMODE_BAYER:2,
        ueye.IS_COLORMODE_CBYCRY:4,
        ueye.IS_COLORMODE_JPEG:8,
        ueye.IS_COLORMODE_INVALID:0,
    }
    @property
    def sensor_color_mode(self):
        """
        センサーのカラーモードを返します。
        メモリに保存されるカラーモードとは別です。
        """
        if self._sensor_color_mode is None:
            color_mode = self.sensor_info.nColorMode.value
            self._sensor_color_mode = int.from_bytes(color_mode,
                                                     byteorder='big')
        return self._sensor_color_mode

    COLOR_MODE = {
        ueye.IS_CM_SENSOR_RAW8: 8,
        ueye.IS_CM_SENSOR_RAW10: 16,
        ueye.IS_CM_SENSOR_RAW12: 16,
        ueye.IS_CM_SENSOR_RAW16: 16,
        ueye.IS_CM_MONO8: 8,
        ueye.IS_CM_RGB8_PACKED: 24,
        ueye.IS_CM_BGR8_PACKED: 24,
        ueye.IS_CM_RGBA8_PACKED: 32,
        ueye.IS_CM_BGRA8_PACKED: 32,
        ueye.IS_CM_BGR10_PACKED: 32,
        ueye.IS_CM_RGB10_PACKED: 32,
        ueye.IS_CM_BGRA12_UNPACKED: 64,
        ueye.IS_CM_BGR12_UNPACKED: 48,
        ueye.IS_CM_BGRY8_PACKED: 32,
        ueye.IS_CM_BGR565_PACKED: 16,
        ueye.IS_CM_BGR5_PACKED: 16,
        ueye.IS_CM_UYVY_PACKED: 16,
        ueye.IS_CM_UYVY_MONO_PACKED: 16,
        ueye.IS_CM_UYVY_BAYER_PACKED: 16,
        ueye.IS_CM_CBYCRY_PACKED: 16,        
    }
    @property
    def color_mode(self):
        """
        is_SetColorMode() はグラフィックスカードで画像データを保存、
        または表示する際に使用するカラーモードを設定します。その際、
        必ず選択したカラーモードに対応するだけの、十分な容量の画像メモリを
        割り当ててください。画像を直接グラフィックスカードのメモリに転送する場合は、
        表示設定とカラーモードの設定に食い違いがないことを確認してください。
        これらがマッチしていないと、表示される画像の色が違っていたり、
        鮮明に見えなくなってしまいます。

        https://jp.ids-imaging.com/manuals/ids-software-suite/ueye-manual/4.95/ja/is_setcolormode.html

        """
        n_ret = ueye.is_SetColorMode(self.hCam, ueye.IS_GET_COLOR_MODE)
        return n_ret
    
    @color_mode.setter
    def color_mode(self, c_mode):
        n_ret = ueye.is_SetColorMode(self.hCam, c_mode)
        return n_ret

    def livemode(self, wait = False):
        """
        Notes:

        カメラのライブビデオモード (フリーランモード) を有効にします。ドライバーは画像を割り当てた画像メモリ、
        または Direct3D/OpenG を使用している場合はグラフィックスカードに転送します。
        画像データ (DIB モードは) is_AllocImageMem() を使って作成されたメモリに保存され、
        is_SetImageMem() でアクティブな画像メモリとして指定されます。メモリのアドレスを問い合わせるには 
        is_GetImageMem() を使います。
        リングバッファを使用している場合、画像キャプチャリング機能はキャプチャシーケンスにおいて画像の保存に使う、
        すべての画像メモリをエンドレスに循環します。is_LockSeqBuf() でロックしたシーケンスメモリはスキップします。
        最後のシーケンスメモリがいっぱいになると、シーケンスイベントまたはメッセージがトリガされます。
        キャプチャは常にシーケンス先頭のエレメントで開始します。
        トリガモードで is_CaptureVideo() を呼び出すと、連続トリガモードの待機状態に入ります。
        トリガ信号のたびに画像が記録され、次のトリガの待機状態に入ります。
        画像キャプチャモードに関する詳しい説明は、操作手順:画像キャプチャ をご覧ください。
         Activates the camera's live video mode (free run mode)
         nRet = ueye.is_CaptureVideo(self.hCam, ueye.IS_DONT_WAIT)
         nRet = ueye.is_CaptureVideo(self.hCam, ueye.IS_WAIT)
        """
        if wait:
            n_ret = ueye.is_CaptureVideo(self.hCam, ueye.IS_WAIT)
        else:
            n_ret = ueye.is_CaptureVideo(self.hCam, ueye.IS_DONT_WAIT)
        self._check(n_ret, "is_CaptureVideo ERROR")

    def inquire_img_mem(self):
        """
        Enables the queue mode for existing image memory sequences
        Args:
            None

        Returns:
            None

        Examples:
            関数の使い方

            >>> camera.cam_quemode()
        """
        width  = ueye.int()
        height = ueye.int()
        n_bits_per_pixel = ueye.int()
        n_ret = ueye.is_InquireImageMem(self.hCam, 
                                        self.pcImageMemory,
                                        self.MemID,#FIXME 
                                        width, 
                                        height, 
                                        n_bits_per_pixel, 
                                        self.pitch)
        self._check(n_ret, "is_InquireImageMem ERROR")
        return (width.value, height.value, n_bits_per_pixel.value, self.pitch.value)

    def cam_quemode(self):
        print("Unknown??")#FIXME

    def setup_all(self):
        """
        カメラの性能に対して、もっとも大きな値を設定します。
        カラーモード:RGBであればBGR8bit、モノクロであればmono
        AOC:画素数全体
        イメージメモリ:カラーモードと画素数から必要な画像一枚分
        """
        self.set_default_color_mode()
        # self.cam_aoi()
        self.cam_imgmemory()
        self.inquire_img_mem()
        # self.cam_quemode()
        # self.counter = 0

    def triggered_capture(self):
        n_ret = ueye.is_FreezeVideo(self.hCam, ueye.IS_WAIT)
        self._check(n_ret, 'ueye.is_FreezeVideo(self.hCam, ueye.IS_WAIT) error')

        array = ueye.get_data(self.pcImageMemory,
                              self.width,
                              self.height,
                              self.nBitsPerPixel,
                              self.pitch,
                              copy=False)
        frame = np.reshape(array,(self.height,
                                  self.width,
                                  self.bytes_per_pixel))
        return frame
    
    # def trigger(self):

    def capture(self):
        
        array = ueye.get_data(self.pcImageMemory,
                            self.width,
                            self.height,
                            self.nBitsPerPixel,
                            self.pitch,
                            copy=False)
        frame = np.reshape(array,(self.height,
                                self.width,
                                self.bytes_per_pixel))
        return frame
    
    def stop(self):
        ueye.is_FreeImageMem(self.hCam, self.pcImageMemory, self.MemID)
        ueye.is_ExitCamera(self.hCam)
    
    #FIXME
    def __exit__(self):
        self.stop()

    RETURN_MSG = {
        ueye.IS_NO_SUCCESS:"(-1)一般的なエラーメッセージ",
        #ueye.IS_SUCCESS:"(0)機能が正常に実行されました",
        ueye.IS_INVALID_CAMERA_HANDLE:"(1)無効なカメラハンドルです",
        ueye.IS_IO_REQUEST_FAILED:"(2)uEye ドライバーからの入出力要求に失敗しました。ueye_api.dll (API) のバージョンとドライバーファイル (ueye_usb.sys または ueye_eth.sys) が合っていない可能性があります。",
        ueye.IS_CANT_OPEN_DEVICE:"(3)カメラの初期化または選択の試行に失敗しました (カメラが接続されていないか、初期化エラー)。",
        ueye.IS_CANT_OPEN_REGISTRY:"(11)Windows レジストリキーを開けません",
        ueye.IS_CANT_READ_REGISTRY:"(12)Windows レジストリからの設定読み取りエラー",
        ueye.IS_NO_IMAGE_MEM_ALLOCATED:"(15)>ドライバーがメモリを割り当てられませんでした。",
        ueye.IS_CANT_CLEANUP_MEMORY:"(16)ドライバーが割り当てられたメモリを解放できませんでした。",
        ueye.IS_CANT_COMMUNICATE_WITH_DRIVER:"(17)ドライバーがロードされていないため、ドライバーとの通信に失敗しました。",
        ueye.IS_FUNCTION_NOT_SUPPORTED_YET:"(18)この機能にはまだ対応していません。",
        ueye.IS_INVALID_IMAGE_SIZE:"(30)無効な画像サイズ",
        ueye.IS_INVALID_CAPTURE_MODE:"(32)現在のカメラの操作モード (フリーラン、トリガー、スタンバイ) では、この機能を実行できません。",
        ueye.IS_INVALID_MEMORY_POINTER:"(49)無効なポインターまたは無効なメモリ ID",
        ueye.IS_FILE_WRITE_OPEN_ERROR:"(50)書込みまたは読み取りを行うためにファイルを開くことができません。",
        ueye.IS_FILE_READ_OPEN_ERROR:"(51)ファイルを開くことができません。",
        ueye.IS_FILE_READ_INVALID_BMP_ID:"(52)無効なビットマップファイルが指定されました。",
        ueye.IS_FILE_READ_INVALID_BMP_SIZE:"(53)ビットマップサイズに誤りがあります (サイズ超過)。",
        ueye.IS_NO_ACTIVE_IMG_MEM:"(108)有効な画像メモリがありません。is_SetImageMem() 機能でメモリーを有効にするか、is_AddToSequence() 機能でシーケンスを作成する必要があります。",
        ueye.IS_SEQUENCE_LIST_EMPTY:"(112)シーケンスリストが空のため、削除できません。",
        ueye.IS_CANT_ADD_TO_SEQUENCE:"(113)このシーケンスには既に画像メモリが入っているため、追加することができません。",
        ueye.IS_SEQUENCE_BUF_ALREADY_LOCKED:"(117)メモリをロックできませんでした。バッファへのポインタが無効です。",
        ueye.IS_INVALID_DEVICE_ID:"(118)無効なデバイス ID です。有効な ID は USB カメラでは 1 から、GigE カメラでは 1001 から始まります。",
        ueye.IS_INVALID_BOARD_ID:"(119)無効なボード ID です。ID の有効値は 1～255 までです。",
        ueye.IS_ALL_DEVICES_BUSY:"(120)全てのカメラが使用中です。",
        ueye.IS_TIMED_OUT:"(122)タイムアウトが発生しました。一定の時間内に画像のキャプチャリング処理が完了しませんでした。",
        ueye.IS_NULL_POINTER:"(123)無効な配列",
        ueye.IS_INVALID_PARAMETER:"(125)送信したパラメータのうちいずれかが有効な範囲外であるか、このセンサーに対応していないか、あるいはこのモードでは使用できません。",
        ueye.IS_OUT_OF_MEMORY:"(127)メモリが割り当てられませんでした。",
        ueye.IS_ACCESS_VIOLATION:"(129)アクセス違反が発生しました。",
        ueye.IS_NO_USB20:"(139)USB 2.0 High Speed 非対応のポートにカメラが接続されています。 メモリボードを搭載していないカメラは USB 1.1 ポートで操作できません。",
        ueye.IS_CAPTURE_RUNNING:"(140)現在の処理中のキャプチャ操作を、先に終わらせてください。",
        ueye.IS_IMAGE_NOT_PRESENT:"(145)要求した画像はカメラのメモリに存在しないか、既に無効になっています。",
        ueye.IS_TRIGGER_ACTIVATED:"(148)カメラがトリガ信号の待機中のため、この機能は使用できません。",
        ueye.IS_CRC_ERROR:"(151)設定の読み取り中に CRC エラーの修復で問題が発生しました。",
        ueye.IS_NOT_YET_RELEASED:"(152)この機能は、このバージョンではまだ有効になっていません。",
        ueye.IS_NOT_CALIBRATED:"(153)このカメラにはキャリブレーションデータが入っていません。",
        ueye.IS_WAITING_FOR_KERNEL:"(154)システムはカーネルドライバの応答を待っています。",
        ueye.IS_NOT_SUPPORTED:"(155)ここで使用されたカメラのモデルは、この機能または設定に対応していません。",
        ueye.IS_TRIGGER_NOT_ACTIVATED:"(156)トリガが無効になっているため、この機能は実行できません。",
        ueye.IS_OPERATION_ABORTED:"(157)処理はキャンセルされました。",
        ueye.IS_BAD_STRUCTURE_SIZE:"(158)内部構造体にサイズエラーがあります。",
        ueye.IS_INVALID_BUFFER_SIZE:"(159)画像メモリのサイズが合っていないため、指定された形式では画像を保存できません。",
        ueye.IS_INVALID_PIXEL_CLOCK:"(160)現在設定されているピクセルクロック周波数では、この設定が使用できません。",
        ueye.IS_INVALID_EXPOSURE_TIME:"(161)現在設定されている露出時間では、この設定が使用できません。",
        ueye.IS_AUTO_EXPOSURE_RUNNING:"(162)自動露出時間制御が有効になっている時は、設定変更ができません。",
        ueye.IS_CANNOT_CREATE_BB_SURF:"(163)バックバッファサーフェスを作成できません。",
        ueye.IS_CANNOT_CREATE_BB_MIX:"(164)バックバッファ複合サーフェスを作成できません。",
        ueye.IS_BB_OVLMEM_NULL:"(165)バックバッファのオーバーレイメモリをロックできません。",
        ueye.IS_CANNOT_CREATE_BB_OVL:"(166)バックバッファのオーバーレイメモリを作成できません。",
        ueye.IS_NOT_SUPP_IN_OVL_SURF_MODE:"(167)バックバッファオーバーレイモードに対応していません。",
        ueye.IS_INVALID_SURFACE:"(168)無効なバックバッファサーフェスです。",
        ueye.IS_SURFACE_LOST:"(169)バックバッファサーフェスが見つかりません。",
        ueye.IS_RELEASE_BB_OVL_DC:"(170)オーバーレイのデバイスコンテキスト解放でエラーが発生しました。",
        ueye.IS_BB_TIMER_NOT_CREATED:"(171)バックバッファタイマーを作成できませんでした。",
        ueye.IS_BB_OVL_NOT_EN:"(172)バックバッファオーバーレイを有効にできませんでした。",
        ueye.IS_ONLY_IN_BB_MODE:"(173)バックバッファモードにのみ対応しています。",
        ueye.IS_INVALID_COLOR_FORMAT:"(174)無効なカラー形式です",
        ueye.IS_INVALID_WB_BINNING_MODE:"(175)モノビニング/モノサブサンプリングは自動ホワイトバランスに対応していません。",
        ueye.IS_INVALID_I2C_DEVICE_ADDRESS:"(176)無効な I2C デバイスアドレス",
        ueye.IS_COULD_NOT_CONVERT:"(177)現在の画像処理が完了しませんでした。",
        ueye.IS_TRANSFER_ERROR:"(178)転送エラー。殆どの場合はピクセルレートを下げることで、転送エラーの頻発を抑えることができます。",
        ueye.IS_PARAMETER_SET_NOT_PRESENT:"(179)パラメータセットがありません。",
        ueye.IS_INVALID_CAMERA_TYPE:"(180)ファイルで定義したカメラのタイプと現在のカメラのモデルが合っていません。",
        ueye.IS_INVALID_HOST_IP_HIBYTE:"(181)ホストアドレスの HIBYTE が無効です",
        ueye.IS_CM_NOT_SUPP_IN_CURR_DISPLAYMODE:"(182)このカラーモードは現在の表示モードに対応していません。",
        ueye.IS_NO_IR_FILTER:"(183)IR フィルターがありません",
        ueye.IS_STARTER_FW_UPLOAD_NEEDED:"(184)カメラのスターターファームウェアとドライバーに互換性がありません。アップデートを行ってください。",
        ueye.IS_DR_LIBRARY_NOT_FOUND:"(185)DirectRenderer のライブラリが見つかりませんでした。",
        ueye.IS_DR_DEVICE_OUT_OF_MEMORY:"(186)十分なグラフィックスメモリがありません。",
        ueye.IS_DR_CANNOT_CREATE_SURFACE:"(187)イメージサーフェスまたはオーバーレイサーフェスが作成できませんでした。",
        ueye.IS_DR_CANNOT_CREATE_VERTEX_BUFFER:"(188)頂点バッファ (vertex buffer) を作成できませんでした。",
        ueye.IS_DR_CANNOT_CREATE_TEXTURE:"(189)テクスチャを作成できませんでした。",
        ueye.IS_DR_CANNOT_LOCK_OVERLAY_SURFACE:"(190)オーバーレイサーフェスがロックできませんでした。",
        ueye.IS_DR_CANNOT_UNLOCK_OVERLAY_SURFACE:"(191)オーバーレイサーフェスのロックを解除できませんでした。",
        ueye.IS_DR_CANNOT_GET_OVERLAY_DC:"(192)オーバーレイのデバイスコンテキストのハンドルが取得できませんでした。",
        ueye.IS_DR_CANNOT_RELEASE_OVERLAY_DC:"(193)オーバーレイのデバイスコンテキストハンドルを解放できませんでした。",
        ueye.IS_DR_DEVICE_CAPS_INSUFFICIENT:"(194)このグラフィクスハードウェアは関数に対応していません。",
        ueye.IS_INCOMPATIBLE_SETTING:"(195)互換性がない設定が他にあるため、この関数は使用できません。",
        ueye.IS_DR_NOT_ALLOWED_WHILE_DC_IS_ACTIVE:"(196)デバイスのコンテキストハンドルがアプリケーションで開いたままになっています。",
        ueye.IS_DEVICE_ALREADY_PAIRED:"(197)デバイスは、システムで使用中か、別のシステムによって使用されています。(カメラが開かれていてデバイスとペアリングされています)。",
        ueye.IS_SUBNETMASK_MISMATCH:"(198)カメラのサブネットマスクと PC のネットワークカードが異なります。",
        ueye.IS_SUBNET_MISMATCH:"(199)カメラのサブネットと PC のネットワークカードが異なります。",
        ueye.IS_INVALID_IP_CONFIGURATION:"(200)無効な IP アドレス設定です。",
        ueye.IS_DEVICE_NOT_COMPATIBLE:"(201)このデバイスとドライバーは互換性がありません。",
        ueye.IS_NETWORK_FRAME_SIZE_INCOMPATIBLE:"(202)カメラの画像サイズ設定と PC のネットワークカードに互換性がありません。",
        ueye.IS_NETWORK_CONFIGURATION_INVALID:"(203)無効なネットワークカード設定です。",
        ueye.IS_ERROR_CPU_IDLE_STATES_CONFIGURATION:"(204)CPU のアイドル設定に失敗しました。",
        ueye.IS_DEVICE_BUSY:"(205)カメラはビジー状態です。要求された画像を送信できません。",
        ueye.IS_SENSOR_INITIALIZATION_FAILED:"(206)センサーの初期化に失敗しました。",
        ueye.IS_IMAGE_BUFFER_NOT_DWORD_ALIGNED:"(207)画像バッファがDWORDにアラインされていません。",
        ueye.IS_SEQ_BUFFER_IS_LOCKED:"(208)画像メモリはロックされています。",
        ueye.IS_FILE_PATH_DOES_NOT_EXIST:"(209)存在しないファイルパスです。",
        ueye.IS_INVALID_WINDOW_HANDLE:"(210)無効なウィンドウハンドルです",
        ueye.IS_INVALID_IMAGE_PARAMETER:"(211)無効な画像パラメータ (位置またはサイズ)",
    }
    def _check(self, ret, message):
        if ret != ueye.IS_SUCCESS:
            if ret in IDS_Camera.RETURN_MSG :
                raise uEyeException(IDS_Camera.RETURN_MSG[ret])
            else:
                raise uEyeException(message)

class uEyeException(Exception):
    def __init__(self, error_code):
        self.error_code = error_code
    def __str__(self):
        return "UEye Err: " + str(self.error_code)

if __name__ == "__main__":

    from cv2 import NORM_RELATIVE
    import cv2

    # print()

    # camera_id = 1
    for camera in IDS_Camera.find_cameras():
        print("gain factor", camera.get_gain_factor())
        print('inquire gain factor', camera.inquire_gain_factor())
        # camera.set_gain_factor(300, 300, 300, 300)
        # frame = camera.capture()
        # cv2.imwrite("./UI3080C_%d_default.png" % i, frame)
        # camera.master_gain = 50 # 1.92x
        # camera.set_rgb_gain(17, 0, 34)
        camera.set_aoi(0, 0, 2456, 320)
        # camera.setup_all()
        camera.set_default_color_mode()
        # self.cam_aoi()
        camera.cam_imgmemory()
        print(camera.inquire_img_mem())
        # camera.fps = 120
        # camera.exposure = 10
        camera.set_trigger()
        camera.livemode(wait=True)
        # ueye.is_CaptureVideo(camera.hCam, ueye.IS_DONT_WAIT)
        import time
        _n = time.time()
        for i in range(1000):# True:
        # while True:
            frame2 = camera.capture()
            cv2.imshow("SimpleLive_Python_uEye_OpenCV", frame2)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        print("image  fps : ", 1000.0 / (time.time() - _n))
        print("camera fps : ", camera.fps)
        print('color mode : ', camera.color_mode)
        print('rgb gain    : ', camera.get_rgb_gain())
        print('inquire gain factor', camera.inquire_gain_factor())
        camera.exposure = 5
        frame = camera.capture()
        cv2.imwrite("./img_%d.png" % 2, frame)
        print("fps : %f" % camera.fps)

        # aoi : Area Of Interest
        # (x, y, width, height)
    exit(0)
    if False:
        camera.set_aoi(300, 300, 1000, 1000)
        camera.master_gain = 300
        camera.set_rgb_gain(1000, 1000, 1000)
        print("FPS : %f" % camera.fps)
        if False:
            camera.set_rgb_gain(20, 20, 20)
            print("display mode : ", camera.set_displaymode())
            camera.cam_livemode()
            camera.cam_autofocus()
            # camera.cam_awb()
            # camera.cam_fps(cam_fps)

        frame = camera.capture()
        print(camera.cam_info.SerNo)

        # aoi : Area Of Interest
        # (x, y, width, height)
        print("aoi : ", camera.get_aoi())
        cv2.imwrite("./UI3080C_%d.png" % i, frame)
        print(frame.shape)
        camera.stop()


    # if cInfo.SerNo==b'4104035607':    mono_id = i_hCam
    # elif cInfo.SerNo==b'4104043710':  color_id = i_hCam


