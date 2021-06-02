import numpy as np
from .ts_models import ModelType
from statsmodels.tsa.stattools import adfuller
from statsmodels.regression.linear_model import OLS


def check_if_stationary(time_series: np.ndarray):
    res = adfuller(time_series, autolag='AIC')
    return res[0] > res[4]['5%']


def make_stationary(data: np.ndarray):
    data_copy = np.copy(data)
    counts = np.zeros(shape=data_copy.shape[0])
    limit = 0

    for i, x in enumerate(data_copy):
        while not check_if_stationary(x) and limit < 50:
            limit += 1
            if (data_copy == 0).all():
                break

            data_copy[i] = np.concatenate(([0], np.diff(x)))
            counts[i] += 1

    return data_copy, counts


def check_cointegration(portfolio: np.ndarray, macro_params: np.ndarray,
                        names: list):
    res = []
    for macro_param, macro_name in zip(macro_params, names):
        model = OLS(endog=portfolio[0], exog=macro_param)
        results = model.fit()
        if check_if_stationary(results.resid):
            res.append(macro_name)

    return res


def check_correlation(x: np.ndarray, y: np.ndarray, y_names: list):
    exog = [[]] * len(x)

    for i, ix in enumerate(x):
        for iy, name in zip(y, y_names):
            corr = np.corrcoef(
                np.concatenate((iy, ix)).reshape(-1, len(iy))
            )

            if (np.abs(corr) >= 0.7).all():
                exog[i].append(name)

    return exog


def check_data(portfolios: np.ndarray,
               scenarios: np.ndarray,
               scenario_names: list):
    # Do stationary checks
    s_portfolios, p_counts = make_stationary(portfolios)
    s_scenarios, s_counts = make_stationary(scenarios)

    # Check cointegration
    cointegration_checks = check_cointegration(portfolios, scenarios,
                                               scenario_names)

    # Check correlation
    correlation_checks = check_correlation(portfolios, scenarios,
                                           scenario_names)

    intersection = set.intersection(set(cointegration_checks),
                                    set(correlation_checks[0]))
    if len(intersection) > 1:
        target_macros = list(intersection)
        model_type = ModelType.varmax

    else:
        target_macros = correlation_checks[0]
        model_type = ModelType.arima

    return (s_portfolios, s_scenarios,
            p_counts, s_counts,
            target_macros,
            model_type)
