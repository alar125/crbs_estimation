import numpy as np
from .ts_validation import (check_data, check_cointegration)
from .ts_models import ModelType
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.statespace.varmax import VARMAX
from datetime import date
from dateutil.relativedelta import relativedelta


def calc_portfolio_predictions(portfolios: np.ndarray,
                               m_horizon: int,
                               h_macro_parameters: np.ndarray = None,
                               m_macro_parameters: np.ndarray = None,
                               order=(1, 0, 1)):
    if h_macro_parameters.shape[0] == 1:
        h_macro = h_macro_parameters[0].reshape(-1, 1)
    elif h_macro_parameters.shape[0] == 0:
        h_macro = None
    else:
        h_macro = np.transpose(h_macro_parameters)

    model = ARIMA(endog=portfolios.reshape(-1, 1),
                  exog=h_macro,
                  order=order)
    res = model.fit()
    values = res.predict(end=m_horizon - 1, exog=m_macro_parameters)

    return values


def calc_rvps(portfolios: np.ndarray,
              ratio: float) -> np.ndarray:
    return portfolios * ratio


def calc_repay(portfolios: np.ndarray,
               icreds: np.ndarray) -> np.ndarray:
    return portfolios * icreds / 100


def calc_rvps_repay(rvps: np.ndarray,
                    repay: np.ndarray,
                    pl: np.ndarray) -> np.ndarray:
    return rvps.sum() * repay.sum() / pl.sum()


def calc_credit_loss(rvps_npl,
                     rvps_repay) -> float:
    return rvps_npl - rvps_repay


def get_varmax_predictions(portfolios: dict,
                           target: str,
                           endog: list,
                           m_horizon: int):
    p = [portfolios[target]['values']]

    for portfolio, val in portfolios.items():
        if portfolio in endog:
            p.append(val['values'])

    p = np.asarray(p)

    model = VARMAX(endog=np.transpose(p).astype('float64'),
                   exog=np.transpose(portfolios[target]['correlation_values']))
    res = model.fit()
    values = res.predict(end=m_horizon - 1,
                         exog=portfolios[target]['m_correlation_values'])
    portfolios[target]['predictions'] = values


def get_predictions(portfolios: dict, m_horizon: int):
    for bank_id, formulas in portfolios.items():
        for formula, d in formulas.items():
            if d['model_type'] == ModelType.arima:
                d['predictions'] = calc_portfolio_predictions(
                    d['values'],
                    m_horizon,
                    order=(1, d['stationary_counts'], 1),
                    h_macro_parameters=d['correlation_values'],
                    m_macro_parameters=d['m_correlation_values']
                )


# Get calculation dates range
def get_dates(h_horizon,
              calc_date: date):
    dates = [calc_date]
    t_date = calc_date

    if type(h_horizon) == date:
        delta = relativedelta(calc_date, h_horizon)
        h_horizon = (delta.months + delta.years * 12) // 3

    for i in range(h_horizon):
        t_date += relativedelta(months=-3)
        dates.append(t_date)

    dates = dates[::-1]
    return dates


# Modeling horizon dates
def get_modeling_dates(m_horizon: int,
                       calc_date: date):
    m_dates = []
    t_date = calc_date
    for i in range(m_horizon):
        t_date += relativedelta(months=3)
        m_dates.append(t_date)
    return m_dates


def make_predictions(portfolios: dict, dates: list, m_dates: list,
                     scenario_id: int,
                     m_horizon: int, get_indicator_values: callable):
    # Check all candidates for VARMAX
    for bank_id, formulas in portfolios.items():
        for formula, val in formulas.items():
            if val['model_type'] != ModelType.varmax:
                continue

            # Check cointegration with all other portfolios
            portfolios_to_check = []
            portfolios_names = []

            for portfolio, p_val in formulas.items():
                if portfolio == formula:
                    continue

                portfolios_to_check.append(p_val['values'])
                portfolios_names.append(portfolio)

            coint_portfolios = check_cointegration(
                np.asarray([val['values']]),
                np.asarray(portfolios_to_check),
                portfolios_names
            )

            if len(coint_portfolios) <= 1:
                val['model_type'] = ModelType.arima
                continue

            exogs = [val['correlations']]
            for portfolio, p_val in formulas.items():
                if portfolio in coint_portfolios:
                    exogs.append(p_val['correlations'])

            intersect = set.intersection(*[set(s) for s in exogs])
            if len(intersect) <= 1:
                val['model_type'] = ModelType.arima
                continue

            corr_indicators = get_indicator_values(
                dates=dates,
                indicator_names=list(intersect),
                scenario_id=1
            )
            m_corr_indicators = get_indicator_values(
                dates=m_dates,
                indicator_names=list(intersect),
                scenario_id=scenario_id
            )
            val['correlation_values'] = corr_indicators
            val['m_correlation_values'] = m_corr_indicators

            get_varmax_predictions(formulas, formula, coint_portfolios,
                                   m_horizon)
    get_predictions(portfolios, m_horizon)


def convert_arrays_to_lists(d: dict):
    for item_id, item in d.items():
        if type(item) == np.ndarray:
            d[item_id] = item.tolist()
        elif type(item) == dict:
            convert_arrays_to_lists(item)


def make_checks_and_correlations(portfolios: dict, h_indicators: np.ndarray,
                                 macro_list: list, dates: list, m_dates: list,
                                 scenario_id: int,
                                 get_indicator_values: callable):
    for bank_id, formulas in portfolios.items():
        for formula, val in formulas.items():

            (s_portfolios, s_scenarios,
             p_counts, s_counts,
             target_macros, model_type) = check_data(
                portfolios=np.array([val['values']]),
                scenarios=h_indicators,
                scenario_names=macro_list
            )
            val['correlations'] = target_macros

            corr_indicators = get_indicator_values(
                dates=dates,
                indicator_names=target_macros,
                scenario_id=1
            )
            m_corr_indicators = get_indicator_values(
                dates=m_dates,
                indicator_names=target_macros,
                scenario_id=scenario_id
            )
            val['correlation_values'] = corr_indicators
            val['m_correlation_values'] = m_corr_indicators
            val['model_type'] = model_type


def get_bank_stats(portfolios: dict, m_horizon: int,
                   icreds_p: np.ndarray, icreds_le: np.ndarray) -> dict:
    bank_stats = {}

    for bank_id, formulas in portfolios.items():
        bank_stats[bank_id] = {}
        bank_stats[bank_id]['credit_loss_npl'] = np.zeros(shape=(m_horizon,))
        bank_stats[bank_id]['repay'] = np.zeros(shape=(m_horizon,))
        bank_stats[bank_id]['rvps_pl'] = np.zeros(shape=(m_horizon,))
        bank_stats[bank_id]['credit_loss_npl'] = np.zeros(shape=(m_horizon,))
        bank_stats[bank_id]['pl_sum'] = np.zeros(shape=(m_horizon,))
        bank_stats[bank_id]['predictions'] = {}

        for formula, d in formulas.items():
            bank_stats[bank_id]['predictions'][formula] = d['predictions']

            if formula.startswith('npl_'):
                d['rvps'] = d['predictions']
                bank_stats[bank_id]['credit_loss_npl'] += d['rvps']
            else:
                d['rvps'] = calc_rvps(d['predictions'], 0.2)
                bank_stats[bank_id]['pl_sum'] += d['predictions']
                bank_stats[bank_id]['rvps_pl'] += d['rvps']

                if 'ind' in formula:
                    bank_stats[bank_id]['repay'] += calc_repay(d['predictions'],
                                                               icreds_p)
                else:
                    bank_stats[bank_id]['repay'] += calc_repay(d['predictions'],
                                                               icreds_le)

        bank_stats[bank_id]['rvps_repay'] = \
            bank_stats[bank_id]['rvps_pl'] * \
            bank_stats[bank_id]['repay'] / \
            bank_stats[bank_id]['pl_sum']
        bank_stats[bank_id]['credit_loss'] = calc_credit_loss(
            bank_stats[bank_id]['credit_loss_npl'],
            bank_stats[bank_id]['rvps_repay']
        )

    return bank_stats
