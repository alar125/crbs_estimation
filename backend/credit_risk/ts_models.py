from enum import Enum


class ModelType(str, Enum):
    arima = 'ARIMA'
    varmax = 'VARMAX'
