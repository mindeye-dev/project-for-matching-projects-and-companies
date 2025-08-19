import pandas as pd


def export_excel(filename, data_array):
    df = pd.DataFrame(data_array)
    df.to_excel(filename, index=False)
