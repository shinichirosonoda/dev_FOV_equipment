# Deriving Angle Value by using High-precision amplitude evaluation device
# logging part

import numpy as np
import pandas as pd

def data_save_init():
    cols =["Time", "-x", "+x", "2x", "-y", "+y", "2y"]
    df = pd.DataFrame(columns=cols, dtype=object)
    return df

def data_save_add(df, dt_now, data):
    df.loc[len(df)] = np.append(dt_now, data)
    return df

def data_save_to_file(df, file_name="FOV_data.csv"):
    df.to_csv(file_name)