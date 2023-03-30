import pandas as pd
import numpy as np


def make_line(gamma):
    coef = np.random.normal(0)
    p = min(np.random.gamma(gamma), 1)
    p = max(p, 1-abs(coef))
    return dict(p=p, coef=coef)


def make_test_data(gamma):
    for i in range(2):
        df = pd.DataFrame([make_line(gamma) for _ in range(1000)])
        df = df.assign(label=[
            f"result {i + 1}"
            for i in range(df.shape[0])
        ])
        df.to_csv(f"test_data_{i+1}.csv", index=None)


if __name__ == "__main__":
    make_test_data(0.5)
