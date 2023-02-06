# Deriving Angle Value by using High-precision amplitude evaluation device
# logging part

import numpy as np
import pandas as pd

class FovLogging():
    @classmethod
    def data_save_init(self):
        cols =["Time", "-x", "+x", "2x", "-y", "+y", "2y"]
        df = pd.DataFrame(columns=cols, dtype=object)
        return df

    @classmethod
    def data_save_add(self, df, dt_now, data):
        df.loc[len(df)] = np.append(dt_now, data)
        return df

    @classmethod
    def data_save_to_file(self, df, file_name="FOV_data.csv"):
        try:
            df.to_csv(file_name)
        except PermissionError as e:
            print(e)
            print(type(e))